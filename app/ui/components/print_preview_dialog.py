import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextBrowser, QTextEdit, QFileDialog, QMessageBox, QTabWidget,
    QLabel, QFrame, QCheckBox, QApplication
)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo

from app.database.models import RepairJob, JobStatus
from app.services.backup_service import SettingsService
from app.services.print_service import (
    ThermalSlipGenerator, render_slip_to_printer, slip_height_mm,
    send_cut_command, DOC_WIDTH_PX
)

logger = logging.getLogger(__name__)


class ThermalPrintPreviewDialog(QDialog):
    """
    Preview and print compact 3-inch (80mm) thermal slips.
    Tabs: 0 Customer+Shop (dual, default), 1 Shopkeeper, 2 Customer,
    3 Repairer, 4 Delivery (only when the job is ready/delivered).
    """
    def __init__(self, job: RepairJob, parent=None, initial_tab: int = 0):
        super().__init__(parent)
        if job and hasattr(job, "id") and job.id:
            try:
                _ = job.customer.name
                _ = job.device.brand
            except Exception:
                from app.services.job_service import JobService
                fresh = JobService.get_by_id(job.id)
                if fresh:
                    job = fresh
        self.job = job
        self.setWindowTitle(f"3-Inch Thermal Slip Print - {job.job_number}")
        self.resize(540, 540)
        self.setMinimumSize(440, 460)
        self._init_ui(initial_tab)
        self._fit_to_screen()

    def _fit_to_screen(self):
        """Keep the window a compact square that always fits on screen."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        self.resize(
            min(self.width(), int(avail.width() * 0.9)),
            min(self.height(), int(avail.height() * 0.9)),
        )
        parent = self.parentWidget()
        if parent:
            self.move(parent.window().frameGeometry().center() - self.rect().center())
        else:
            self.move(avail.center() - self.rect().center())

    def _init_ui(self, initial_tab: int):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QFrame()
        header.setStyleSheet("background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 6, 12, 6)
        cust_name = self.job.customer.name if self.job.customer else "Walk-in"
        dev_text = f"{self.job.device.brand} {self.job.device.model}" if self.job.device else "Device"
        title = QLabel(f"Job: <b style='color:#1d4ed8;'>{self.job.job_number}</b> | {cust_name} | {dev_text}")
        title.setStyleSheet("color: #1e293b; font-size: 13px; border: none;")
        h_layout.addWidget(title)
        h_layout.addStretch()
        self.length_label = QLabel()
        self.length_label.setStyleSheet("color: #15803d; font-weight: 700; border: none;")
        h_layout.addWidget(self.length_label)
        layout.addWidget(header)

        self.tab_widget = QTabWidget()
        self.slips = []    # preview HTML per tab (index == tab index)
        self._duals = []   # True when a tab represents the 2-in-1 combined slip

        self._add_tab("📜 Customer + Shop", ThermalSlipGenerator.generate_dual_slip(self.job), dual=True)
        self._add_tab("🏷️ Shopkeeper", ThermalSlipGenerator.generate_shopkeeper_slip(self.job))
        self._add_tab("📄 Customer", ThermalSlipGenerator.generate_customer_receiving_slip(self.job))
        self._add_tab("🔧 Repairer", ThermalSlipGenerator.generate_technician_diagnosis_slip(self.job))
        if self.job.status in [JobStatus.READY, JobStatus.DELIVERED]:
            self._add_tab("🛡️ Delivery", ThermalSlipGenerator.generate_delivery_slip(self.job))

        self.tab_widget.currentChanged.connect(self._update_length_label)
        self.tab_widget.setCurrentIndex(initial_tab if 0 <= initial_tab < len(self.slips) else 0)
        self._update_length_label()
        layout.addWidget(self.tab_widget, 1)

        # Fixed bottom bar: action buttons are always visible, never scrolled away.
        btn_bar = QFrame()
        btn_bar.setStyleSheet("QFrame { background: #f8fafc; border: none; border-top: 1px solid #e2e8f0; }")
        btn_bar.setFixedHeight(52)
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(8, 8, 8, 4)
        btn_layout.setSpacing(8)

        self.btn_print_current = QPushButton("🖨️ Print")
        self.btn_print_current.setStyleSheet(
            "font-weight: 700; background-color: #2563eb; color: #ffffff; padding: 8px 16px; border-radius: 6px;"
        )
        self.btn_print_current.setToolTip("Print the current slip on the default printer")
        self.btn_print_current.clicked.connect(lambda: self._print_html(interactive=False))
        btn_layout.addWidget(self.btn_print_current)

        self.btn_choose_printer = QPushButton("⚙️ Printer...")
        self.btn_choose_printer.setToolTip("Choose a printer, then print the current slip")
        self.btn_choose_printer.clicked.connect(lambda: self._print_html(interactive=True))
        btn_layout.addWidget(self.btn_choose_printer)

        self.btn_save_pdf = QPushButton("💾 PDF")
        self.btn_save_pdf.setToolTip("Save the current slip as a PDF file")
        self.btn_save_pdf.clicked.connect(self._handle_save_pdf)
        btn_layout.addWidget(self.btn_save_pdf)

        self.auto_cut_checkbox = QCheckBox("✂️ Auto cut")
        self.auto_cut_checkbox.setToolTip(
            "Send an automatic cut command to the thermal printer after printing"
        )
        self.auto_cut_checkbox.setChecked(self._auto_cut_enabled())
        self.auto_cut_checkbox.toggled.connect(self._on_auto_cut_toggled)
        btn_layout.addWidget(self.auto_cut_checkbox)

        btn_layout.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addWidget(btn_bar)

    def _add_tab(self, label: str, html: str, dual: bool = False):
        browser = QTextBrowser()
        browser.setStyleSheet(
            "QTextBrowser { background-color: #ffffff; color: #000000; border: 1px solid #cbd5e1; padding: 8px; }"
        )
        # Wrap at the real printable width so preview == paper
        browser.setLineWrapMode(QTextEdit.LineWrapMode.FixedPixelWidth)
        browser.setLineWrapColumnOrWidth(int(DOC_WIDTH_PX))
        browser.document().setDocumentMargin(0)
        browser.setHtml(html)
        self.slips.append(html)
        self._duals.append(dual)
        self.tab_widget.addTab(browser, label)

    @staticmethod
    def _auto_cut_enabled() -> bool:
        try:
            val = str(SettingsService.get_all_settings().get("auto_cut_after_print", "1")).strip().lower()
            return val in ("1", "true", "yes", "on")
        except Exception:
            return True

    def _on_auto_cut_toggled(self, enabled: bool):
        try:
            SettingsService.save_settings({"auto_cut_after_print": "1" if enabled else "0"})
        except Exception as e:
            logger.warning(f"Could not persist auto-cut setting: {e}")

    def _get_current_html(self) -> str:
        idx = self.tab_widget.currentIndex()
        return self.slips[idx] if 0 <= idx < len(self.slips) else self.slips[0]

    def _get_print_units(self):
        """HTML chunks to print for the current tab.

        The combined slip is printed as two separate jobs so the cutter can cut
        between the customer and shopkeeper copies; every other tab is one job.
        """
        idx = self.tab_widget.currentIndex()
        if 0 <= idx < len(self._duals) and self._duals[idx]:
            return ThermalSlipGenerator.generate_dual_parts(self.job)
        return [self._get_current_html()]

    def _update_length_label(self, *_):
        try:
            self.length_label.setText(f"Paper: ~{slip_height_mm(self._get_current_html()):.0f} mm")
        except Exception:
            self.length_label.setText("")

    @staticmethod
    def _make_printer(name: str = "") -> QPrinter:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        if name:
            printer.setPrinterName(name)
        return printer

    def _print_html(self, interactive: bool = False):
        try:
            if not QPrinterInfo.availablePrinterNames() and not interactive:
                QMessageBox.warning(
                    self, "No Printer Installed",
                    "No printer was detected on this computer.\n\n"
                    "Please connect or install a printer, or use 'Save PDF'."
                )
                return

            first = self._make_printer()
            if interactive:
                dialog = QPrintDialog(first, self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return

            target_name = first.printerName()
            auto_cut = self.auto_cut_checkbox.isChecked()

            for i, html in enumerate(self._get_print_units()):
                printer = first if i == 0 else self._make_printer(target_name)
                render_slip_to_printer(html, printer)
                if auto_cut and printer.outputFormat() == QPrinter.OutputFormat.NativeFormat:
                    if not send_cut_command(printer.printerName()):
                        logger.warning("Auto-cut command was not sent for printer %r", printer.printerName())

            QMessageBox.information(self, "Print Sent", f"Slip for job {self.job.job_number} sent to printer.")
        except Exception as e:
            logger.error(f"Failed to print thermal slip: {e}")
            QMessageBox.critical(self, "Printing Error", f"Could not print slip: {e}\n\nYou can also export to PDF.")

    def _handle_save_pdf(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Thermal Slip as PDF", f"ThermalSlip_{self.job.job_number}.pdf", "PDF Files (*.pdf)"
            )
            if not file_path:
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            render_slip_to_printer(self._get_current_html(), printer)
            QMessageBox.information(self, "PDF Saved", f"Thermal slip saved to:\n{file_path}")
        except Exception as e:
            logger.error(f"Failed to save PDF: {e}")
            QMessageBox.critical(self, "Error Saving PDF", f"Could not save PDF: {e}")
