import os
import io
import sys
import base64
import logging
from html import escape
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from app.database.models import RepairJob
from app.services.backup_service import SettingsService

logger = logging.getLogger(__name__)

# ── Thermal paper geometry ────────────────────────────────────────────────
PAPER_WIDTH_MM = 80.0      # 3-inch roll
PRINT_WIDTH_MM = 72.0      # printable area of 80mm heads (576 dots @ 203dpi)
DOC_DPI = 96.0             # QTextDocument layout units (CSS px)
BOTTOM_FEED_MM = 5.0       # small tail so the cutter doesn't clip the last line
DOC_WIDTH_PX = PRINT_WIDTH_MM / 25.4 * DOC_DPI   # ~272px


def build_slip_document(html: str, width_mm: float = PRINT_WIDTH_MM):
    """Lay out slip HTML at the requested printable width (defaults to 72mm)."""
    from PySide6.QtGui import QTextDocument
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    doc.setHtml(html)
    doc.setTextWidth(width_mm / 25.4 * DOC_DPI)
    return doc


def slip_height_mm(html: str, width_mm: float = PRINT_WIDTH_MM) -> float:
    doc = build_slip_document(html, width_mm)
    return doc.size().height() / DOC_DPI * 25.4 + BOTTOM_FEED_MM


def render_slip_to_printer(html: str, printer) -> float:
    """
    Paint slip HTML onto a QPrinter (real printer or PDF).

    QTextDocument.print_() is NOT used on purpose: for auto-height documents it
    injects 2cm left/right margins, which on 80mm paper squeezes the slip into a
    ~38mm column and spreads it over a very long strip of paper.

    We ask for a nominal 80mm page sized to the content height, but then read
    back the geometry the driver *actually* accepted. Some thermal POS drivers
    reject custom sizes and keep a narrower head (e.g. 72mm), so centering the
    slip inside a hardcoded 80mm page clipped right-aligned columns. We now size
    the slip to the real printable width and centre it inside that.
    Returns the content height in mm.
    """
    from PySide6.QtGui import QPainter, QPageSize, QPageLayout
    from PySide6.QtCore import QSizeF, QMarginsF
    from PySide6.QtPrintSupport import QPrinter

    # 1) Ask the driver for an 80mm page at the slip's content height.
    probe = build_slip_document(html, PRINT_WIDTH_MM)
    height_mm = probe.size().height() / DOC_DPI * 25.4 + BOTTOM_FEED_MM

    printer.setFullPage(True)
    applied = printer.setPageLayout(QPageLayout(
        QPageSize(QSizeF(PAPER_WIDTH_MM, height_mm), QPageSize.Unit.Millimeter, "Thermal Slip"),
        QPageLayout.Orientation.Portrait,
        QMarginsF(0, 0, 0, 0),
        QPageLayout.Unit.Millimeter,
    ))
    if not applied:
        logger.warning(
            "Printer rejected the custom %.0fmm thermal page; falling back to "
            "its native paper size.", PAPER_WIDTH_MM
        )

    # 2) Derive geometry from what the printer really accepted so we never draw
    #    past the physical printable width.
    page_rect = printer.pageRect(QPrinter.Unit.Millimeter)
    printable_w_mm = page_rect.width() if page_rect.width() > 0 else float(PRINT_WIDTH_MM)
    content_mm = min(PRINT_WIDTH_MM, printable_w_mm)

    doc = build_slip_document(html, content_mm)
    content_height_mm = doc.size().height() / DOC_DPI * 25.4 + BOTTOM_FEED_MM

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("Could not start printing on the selected printer.")
    try:
        dpi = printer.resolution()
        scale = dpi / DOC_DPI
        x_mm = page_rect.x() + (printable_w_mm - content_mm) / 2.0
        y_mm = page_rect.y()
        painter.translate(x_mm / 25.4 * dpi, y_mm / 25.4 * dpi)
        painter.scale(scale, scale)
        doc.drawContents(painter)
    finally:
        painter.end()
    return content_height_mm


def send_cut_command(printer_name: str, feed_lines: int = 3, full_cut: bool = True) -> bool:
    """
    Send an ESC/POS feed-and-cut command to a thermal printer via the Windows
    print spooler using the RAW datatype.

    Returns True on success; returns False (never raises) on non-Windows, when
    no printer name is given, or when the spooler/driver rejects the raw write,
    so a failed cut can never break normal printing.

    Bytes: optional line feeds, then GS V 0 (full cut) or GS V 1 (partial cut).
    """
    if sys.platform != "win32" or not printer_name:
        return False

    import ctypes
    from ctypes import wintypes

    class DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", wintypes.LPWSTR),
            ("pOutputFile", wintypes.LPWSTR),
            ("pDatatype", wintypes.LPWSTR),
        ]

    payload = b"\n" * max(0, feed_lines) + (b"\x1d\x56\x00" if full_cut else b"\x1d\x56\x01")

    try:
        winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
        winspool.OpenPrinterW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
        winspool.OpenPrinterW.restype = wintypes.BOOL
        winspool.StartDocPrinterW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(DOC_INFO_1)]
        winspool.StartDocPrinterW.restype = wintypes.DWORD
        winspool.StartPagePrinter.argtypes = [wintypes.HANDLE]
        winspool.StartPagePrinter.restype = wintypes.BOOL
        winspool.WritePrinter.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        winspool.WritePrinter.restype = wintypes.BOOL
        winspool.EndPagePrinter.argtypes = [wintypes.HANDLE]
        winspool.EndDocPrinter.argtypes = [wintypes.HANDLE]
        winspool.ClosePrinter.argtypes = [wintypes.HANDLE]

        h_printer = wintypes.HANDLE()
        if not winspool.OpenPrinterW(printer_name, ctypes.byref(h_printer), None):
            logger.warning("Cut command: could not open printer %r (err %s)",
                           printer_name, ctypes.get_last_error())
            return False

        try:
            doc_info = DOC_INFO_1("Thermal Cut", None, "RAW")
            if not winspool.StartDocPrinterW(h_printer, 1, ctypes.byref(doc_info)):
                logger.warning("Cut command: StartDocPrinter failed (err %s)", ctypes.get_last_error())
                return False
            try:
                winspool.StartPagePrinter(h_printer)
                written = wintypes.DWORD(0)
                buf = ctypes.create_string_buffer(payload)
                ok = winspool.WritePrinter(h_printer, buf, len(payload), ctypes.byref(written))
                winspool.EndPagePrinter(h_printer)
                if not ok or written.value != len(payload):
                    logger.warning("Cut command: wrote %s/%s bytes (err %s)",
                                   written.value, len(payload), ctypes.get_last_error())
                    return False
                return True
            finally:
                winspool.EndDocPrinter(h_printer)
        finally:
            winspool.ClosePrinter(h_printer)
    except Exception as e:
        logger.warning("Cut command failed: %s", e)
        return False


class ThermalSlipGenerator:
    """
    Compact 3-inch (80mm) thermal slip HTML.
    Uses only the HTML subset Qt's rich-text engine supports (tables, <hr>,
    inline font styles) so what you see in preview is what prints.
    """

    # ── helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _fmt_dt(dt: Optional[datetime], fmt: str = "%d-%m-%Y %I:%M %p") -> str:
        """DB stores naive UTC timestamps; show them in local shop time."""
        if not dt:
            return datetime.now().strftime(fmt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime(fmt)

    @classmethod
    def _ensure_loaded_job(cls, job: RepairJob) -> RepairJob:
        if hasattr(job, "id") and job.id:
            try:
                _ = job.customer.name
                _ = job.device.brand
            except Exception:
                from app.services.job_service import JobService
                fresh = JobService.get_by_id(job.id)
                if fresh:
                    return fresh
        return job

    @staticmethod
    def _png_data_uri(img) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    @classmethod
    def _logo_uri(cls, settings: Dict[str, Any], size: int = 80) -> str:
        """Custom shop logo if set, else a simple phone+wrench mark."""
        try:
            from PIL import Image, ImageDraw
            path = settings.get("shop_logo_path")
            if path and os.path.exists(path):
                with Image.open(path) as im:
                    im = im.convert("RGBA")
                    im.thumbnail((size, size), Image.Resampling.LANCZOS)
                    bg = Image.new("RGB", im.size, "white")
                    bg.paste(im, mask=im.split()[3])
                    return cls._png_data_uri(bg)

            img = Image.new("RGB", (size, size), "white")
            d = ImageDraw.Draw(img)
            p = size // 10
            d.rounded_rectangle([p * 2, p, size - p * 2, size - p], radius=p * 2, outline="black", width=p)
            c = size // 2
            d.line([c - p * 2, c + p * 2, c + p, c - p], fill="black", width=p)
            d.ellipse([c, c - p * 3, c + p * 2 + p, c], outline="black", width=p)
            return cls._png_data_uri(img)
        except Exception as e:
            logger.warning(f"Logo generation failed: {e}")
            return ""

    @classmethod
    def _qr_uri(cls, data: str) -> str:
        try:
            import qrcode
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=1)
            qr.add_data(data)
            qr.make(fit=True)
            return cls._png_data_uri(qr.make_image(fill_color="black", back_color="white"))
        except Exception as e:
            logger.warning(f"QR generation failed: {e}")
            return ""

    @staticmethod
    def _wrap(title: str, body: str) -> str:
        # Qt's <hr> doesn't show up when painted via drawContents(); use a solid 1px cell instead.
        divider = ('<table width="100%" cellspacing="0" cellpadding="0" style="margin: 4px 0;">'
                   '<tr><td bgcolor="#000000" height="1" style="font-size: 1px;">&nbsp;</td></tr></table>')
        body = body.replace("<hr>", divider)
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{escape(title)}</title></head>
<body style="font-family: Arial, 'Segoe UI', sans-serif; font-size: 12px; color: #000;">
{body}
</body></html>"""

    @classmethod
    def _header(cls, settings: Dict[str, Any], show_phone: bool = True) -> str:
        name = escape(settings.get("shop_name", "Mobile Repair Shop"))
        tagline = escape(settings.get("shop_tagline", ""))
        phone = escape(settings.get("shop_phone", ""))
        logo = cls._logo_uri(settings)
        logo_cell = f'<td width="42" valign="middle"><img src="{logo}" width="40" height="40"></td>' if logo else ""
        sub = tagline
        if show_phone and phone:
            sub = f"{tagline}<br>{phone}" if tagline else phone
        return f"""
<table width="100%" cellspacing="0" cellpadding="0"><tr>
  {logo_cell}
  <td valign="middle" style="padding-left: 4px;">
    <span style="font-size: 15px; font-weight: bold;">{name}</span><br>
    <span style="font-size: 9px;">{sub}</span>
  </td>
</tr></table>"""

    @classmethod
    def _url_qr_block(cls, settings: Dict[str, Any]) -> str:
        """Centered QR code of the shop URL for customer-facing slips.

        A QR scan opens the site in a phone browser. (A 1D barcode can't encode a
        normal-length URL legibly at 80mm, so the URL is encoded as a QR.) The
        scheme is added automatically when missing so scans open as a link.
        """
        url = (settings.get("shop_url") or "").strip()
        if not url:
            return ""
        if "://" not in url:
            url = f"https://{url}"
        uri = cls._qr_uri(url)
        if not uri:
            return ""
        return f"""
<div align="center" style="margin: 3px 0 5px 0;">
  <img src="{uri}" width="84" height="84"><br>
  <span style="font-size: 8px;">{escape(url)}</span>
</div>"""

    @staticmethod
    def _title(text: str, inverted: bool = False) -> str:
        if inverted:
            return f"""
<table width="100%" cellspacing="0" cellpadding="3" style="margin-top: 4px;"><tr>
  <td align="center" bgcolor="#000000" style="color: #ffffff; font-size: 13px; font-weight: bold;">{escape(text)}</td>
</tr></table>"""
        return f'<hr><p align="center" style="margin: 0; font-size: 13px; font-weight: bold;">{escape(text)}</p><hr>'

    @staticmethod
    def _kv(rows: List[Tuple[str, str, bool]], key_width: int = 70) -> str:
        """rows: (label, value, bold). Values are escaped here. Empty values are skipped."""
        trs = []
        for k, v, b in rows:
            if v in (None, ""):
                continue
            style = ' style="font-weight: bold;"' if b else ""
            trs.append(
                f'<tr><td width="{key_width}" valign="top">{escape(k)}</td>'
                f'<td width="8" valign="top">:</td>'
                f'<td valign="top"{style}>{escape(str(v))}</td></tr>'
            )
        return f'<table width="100%" cellspacing="0" cellpadding="1" style="font-size: 12px;">{"".join(trs)}</table>'

    @staticmethod
    def _fmt_money(val: Optional[float], cur: str = "Rs.") -> str:
        if val is None:
            val = 0.0
        val = float(val)
        if val % 1 == 0:
            return f"{cur} {val:,.0f}"
        return f"{cur} {val:,.2f}"

    @staticmethod
    def _amounts(rows: List[Tuple[str, str, bool]]) -> str:
        trs = []
        for k, v, b in rows:
            if b:
                style = ' style="font-weight: bold; font-size: 13px; border-top: 1px solid #000; padding-top: 2px;"'
            else:
                style = ' style="font-size: 12px;"'
            trs.append(f'<tr><td{style}>{escape(k)}</td><td align="right"{style}>{escape(v)}</td></tr>')
        trs = "".join(trs)
        return f'<table width="100%" cellspacing="0" cellpadding="1" style="font-size: 12px; margin: 2px 0;">{trs}</table>'

    @staticmethod
    def _job_fields(job: RepairJob) -> Dict[str, str]:
        return {
            "cust_name": job.customer.name if job.customer else "Walk-in",
            "cust_phone": job.customer.phone if job.customer else "",
            "device": f"{job.device.brand} {job.device.model}".strip() if job.device else "Device",
            "imei": (job.device.imei_serial or "") if job.device else "",
            "complaint": job.complaint or "Repair Service",
            "status": job.status or "Received",
        }

    # ── slips ─────────────────────────────────────────────────────────────
    @classmethod
    def generate_shopkeeper_slip(cls, job: RepairJob, settings: Optional[Dict[str, Any]] = None, is_standalone: bool = True) -> str:
        """Small box/rack slip: essentials, QR, and complete price/balance summary."""
        job = cls._ensure_loaded_job(job)
        settings = settings or SettingsService.get_all_settings()
        f = cls._job_fields(job)
        qr = cls._qr_uri(job.job_number)
        cur = settings.get("currency_symbol") or "Rs."

        total = job.actual_cost if job.actual_cost > 0 else job.estimated_cost
        advance = job.advance_paid or 0.0
        balance = max(0.0, total - advance)

        total_str = cls._fmt_money(total, cur)
        adv_str = cls._fmt_money(advance, cur)
        bal_str = cls._fmt_money(balance, cur)

        details = cls._kv([
            ("Receipt No", job.job_number, True),
            ("Date", cls._fmt_dt(job.received_at), False),
            ("Customer", f["cust_name"], True),
            ("Phone", f["cust_phone"], False),
            ("Device", f["device"], True),
            ("Issue", f["complaint"], False),
            ("Status", f["status"], True),
        ], key_width=72)
        qr_cell = f'<td width="70" align="right" valign="top"><img src="{qr}" width="68" height="68"></td>' if qr else ""

        amounts_html = cls._amounts([
            ("Total Cost", total_str, False),
            ("Advance Paid", adv_str, False),
            ("BALANCE DUE", bal_str, True),
        ])

        body = f"""
{cls._header(settings, show_phone=False)}
{cls._title("SHOPKEEPER SLIP")}
<table width="100%" cellspacing="0" cellpadding="0"><tr>
  <td valign="top">{details}</td>
  {qr_cell}
</tr></table>
<hr>
{amounts_html}
<hr>
<p align="center" style="margin: 0; font-size: 9px;">Quality Parts &#8226; Expert Technicians &#8226; On-Time Service</p>
"""
        return cls._wrap(f"Shopkeeper Slip - {job.job_number}", body) if is_standalone else body

    @classmethod
    def generate_customer_receiving_slip(cls, job: RepairJob, settings: Optional[Dict[str, Any]] = None, is_standalone: bool = True) -> str:
        """Customer receipt: details, service breakdown, payment & balance, short terms, QR."""
        job = cls._ensure_loaded_job(job)
        settings = settings or SettingsService.get_all_settings()
        f = cls._job_fields(job)
        cur = settings.get("currency_symbol") or "Rs."

        total = job.actual_cost if job.actual_cost > 0 else job.estimated_cost
        advance = job.advance_paid or 0.0
        balance = max(0.0, total - advance)

        total_str = cls._fmt_money(total, cur)
        adv_str = cls._fmt_money(advance, cur)
        bal_str = cls._fmt_money(balance, cur)

        terms = escape(settings.get("terms_conditions", "")).replace("\n", "<br>")
        qr = cls._qr_uri(job.job_number)
        qr_cell = f'<td width="62" valign="top"><img src="{qr}" width="58" height="58"></td>' if qr else ""
        delivery = cls._fmt_dt(job.estimated_delivery_date, "%d-%m-%Y") if job.estimated_delivery_date else ""

        body = f"""
{cls._header(settings)}
{cls._url_qr_block(settings)}
{cls._title("CUSTOMER RECEIPT", inverted=True)}
{cls._kv([
    ("Receipt No", job.job_number, True),
    ("Date", cls._fmt_dt(job.received_at), False),
    ("Customer", f["cust_name"], True),
    ("Phone", f["cust_phone"], False),
    ("Device", f["device"], True),
    ("IMEI/SN", f["imei"], False),
    ("Issue", f["complaint"], False),
    ("Delivery", delivery, False),
])}
<hr>
<table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 2px;">
  <tr>
    <td style="font-weight: bold; font-size: 12px;">Service Details</td>
    <td align="right" style="font-size: 10px; color: #555;">Amount ({escape(cur)})</td>
  </tr>
</table>
<table width="100%" cellspacing="0" cellpadding="1" style="font-size: 12px;">
  <tr>
    <td valign="top">{escape(f['complaint'])}</td>
    <td align="right" valign="top">{escape(total_str)}</td>
  </tr>
  <tr style="font-weight: bold; font-size: 13px;">
    <td style="border-top: 1px solid #000; padding-top: 2px;">Total Charges</td>
    <td align="right" style="border-top: 1px solid #000; padding-top: 2px;">{escape(total_str)}</td>
  </tr>
</table>
<hr>
<table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 2px;">
  <tr>
    <td style="font-weight: bold; font-size: 12px;">Payment Details</td>
  </tr>
</table>
{cls._amounts([
    ("Advance Paid", adv_str, False),
    ("BALANCE DUE", bal_str, True),
    ("Payment Method", "Cash / JazzCash", False),
])}
<hr>
<table width="100%" cellspacing="0" cellpadding="0"><tr>
  {qr_cell}
  <td valign="top" style="padding-left: 4px; font-size: 8px;">{terms}</td>
</tr></table>
<hr>
<p align="center" style="margin: 0; font-size: 10px;">Thank you for choosing <b>{escape(settings.get("shop_name", ""))}</b>!</p>
"""
        return cls._wrap(f"Customer Receipt - {job.job_number}", body) if is_standalone else body

    @classmethod
    def generate_technician_diagnosis_slip(cls, job: RepairJob, settings: Optional[Dict[str, Any]] = None, is_standalone: bool = True) -> str:
        """Internal job card for the repairer."""
        job = cls._ensure_loaded_job(job)
        settings = settings or SettingsService.get_all_settings()
        f = cls._job_fields(job)
        cur = settings.get("currency_symbol") or "Rs."
        tech = job.technician.full_name if job.technician else "Unassigned"

        total = job.actual_cost if job.actual_cost > 0 else job.estimated_cost
        advance = job.advance_paid or 0.0
        balance = max(0.0, total - advance)

        total_str = cls._fmt_money(total, cur)
        adv_str = cls._fmt_money(advance, cur)
        bal_str = cls._fmt_money(balance, cur)

        body = f"""
<p align="center" style="margin: 0; font-size: 13px; font-weight: bold;">{escape(settings.get("shop_name", ""))}</p>
{cls._title("REPAIRER TO-DO & JOB CARD")}
{cls._kv([
    ("Job No", job.job_number, True),
    ("Received", cls._fmt_dt(job.received_at), False),
    ("Device", f["device"], True),
    ("IMEI/SN", f["imei"], False),
    ("Passcode", job.passcode_lock or "None", True),
    ("Customer", f"{f['cust_name']} {f['cust_phone']}".strip(), False),
    ("Technician", tech, True),
    ("Fault", f["complaint"], True),
    ("Condition", job.physical_condition or "", False),
    ("Accessories", job.accessories_received or "", False),
])}
<hr>
<p style="margin: 0; font-size: 11px; font-weight: bold;">Technician To-Do Checklist</p>
<table width="100%" cellspacing="0" cellpadding="0" style="font-size: 10px;">
  <tr><td>[ ] Display/Touch</td><td>[ ] Mic/Earpiece</td></tr>
  <tr><td>[ ] Charging</td><td>[ ] Cameras</td></tr>
  <tr><td>[ ] Battery</td><td>[ ] Speaker</td></tr>
</table>
<p style="margin: 2px 0 0 0; font-size: 11px;"><b>Notes:</b> {escape(job.technician_diagnosis or "")}</p>
<hr>
{cls._amounts([
    ("Quoted Cost", total_str, False),
    ("Advance Paid", adv_str, False),
    ("BALANCE DUE", bal_str, True),
])}
"""
        return cls._wrap(f"Technician Slip - {job.job_number}", body) if is_standalone else body

    @classmethod
    def generate_dual_slip(cls, job: RepairJob, settings: Optional[Dict[str, Any]] = None) -> str:
        """Customer receipt + shopkeeper slip on one strip with a cut line."""
        job = cls._ensure_loaded_job(job)
        settings = settings or SettingsService.get_all_settings()
        cust = cls.generate_customer_receiving_slip(job, settings, is_standalone=False)
        shop = cls.generate_shopkeeper_slip(job, settings, is_standalone=False)
        body = f"""
{cust}
<p align="center" style="margin: 8px 0; font-size: 10px;">- - - - - - - - CUT HERE - - - - - - - -</p>
{shop}
"""
        return cls._wrap(f"Dual Slips - {job.job_number}", body)

    @classmethod
    def generate_dual_parts(cls, job: RepairJob, settings: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Customer receipt and shopkeeper slip as two standalone slips.

        Used by the print dialog to render each copy as its own print job so the
        thermal cutter can cut between them (auto-cut). The combined single-strip
        preview still uses generate_dual_slip().
        """
        job = cls._ensure_loaded_job(job)
        settings = settings or SettingsService.get_all_settings()
        return [
            cls.generate_customer_receiving_slip(job, settings, is_standalone=True),
            cls.generate_shopkeeper_slip(job, settings, is_standalone=True),
        ]

    @classmethod
    def generate_delivery_slip(cls, job: RepairJob, settings: Optional[Dict[str, Any]] = None) -> str:
        """Final delivery + warranty invoice."""
        job = cls._ensure_loaded_job(job)
        settings = settings or SettingsService.get_all_settings()
        f = cls._job_fields(job)
        cur = settings.get("currency_symbol") or "Rs."
        warranty_days = settings.get("repair_warranty_days", "30")

        total = job.actual_cost if job.actual_cost > 0 else job.estimated_cost
        advance = job.advance_paid or 0.0
        balance = max(0.0, total - advance)

        total_str = cls._fmt_money(total, cur)
        adv_str = cls._fmt_money(advance, cur)
        bal_str = cls._fmt_money(balance, cur)

        body = f"""
{cls._header(settings)}
{cls._url_qr_block(settings)}
{cls._title("DELIVERY & WARRANTY INVOICE", inverted=True)}
{cls._kv([
    ("Job No", job.job_number, True),
    ("Delivered", cls._fmt_dt(job.delivered_at), False),
    ("Customer", f"{f['cust_name']} {f['cust_phone']}".strip(), True),
    ("Device", f["device"], True),
    ("IMEI/SN", f["imei"], False),
    ("Issue", f["complaint"], False),
    ("Work Done", job.technician_diagnosis or "Repaired & tested", False),
])}
<hr>
{cls._amounts([
    ("Total Charges", total_str, False),
    ("Advance Paid", adv_str, False),
    ("FINAL PAID / BALANCE", bal_str, True),
])}
<hr>
<p align="center" style="margin: 0; font-size: 11px; font-weight: bold;">{escape(str(warranty_days))} DAYS WARRANTY</p>
<p align="center" style="margin: 0; font-size: 8px;">On replaced parts only. Physical/water damage voids warranty.</p>
<hr>
<p align="center" style="margin: 0; font-size: 10px;">Thank you for trusting <b>{escape(settings.get("shop_name", ""))}</b>!</p>
"""
        return cls._wrap(f"Delivery Invoice - {job.job_number}", body)
