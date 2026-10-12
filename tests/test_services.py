"""
Unit and integration tests for Apple Tech POS Services, Auth & RBAC, Expenses, and Dual Printing.
"""
import os
import unittest
from pathlib import Path

from app.config import get_database_path, DEFAULT_SHOP_CONFIG
from app.database.connection import init_db, session_scope, reset_engine_connection
from app.database.models import Customer, Device, RepairJob, JobStatus, ShopSetting, UserRole, ExpenseCategory, PaymentMethod, Expense, User
from app.services.customer_service import CustomerService
from app.services.device_service import DeviceService
from app.services.job_service import JobService
from app.services.backup_service import BackupService, SettingsService
from app.services.print_service import ThermalSlipGenerator
from app.services.auth_service import AuthService
from app.services.expense_service import ExpenseService


class TestAppleTechPOS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize database with test tables and auto migrations
        init_db(seed_sample_data=False)

    def test_01_customer_crud(self):
        # Create
        customer = CustomerService.create(
            name="Tariq Mahmood",
            phone="0333-1122334",
            email="tariq@example.com",
            address="Gulshan-e-Iqbal, Block 13D, Karachi"
        )
        self.assertIsNotNone(customer.id)
        self.assertEqual(customer.name, "Tariq Mahmood")

        # Read
        fetched = CustomerService.get_by_id(customer.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.phone, "0333-1122334")

        # Update
        updated = CustomerService.update(
            customer_id=customer.id,
            name="Tariq Mahmood Updated",
            phone="0333-9988776",
            email="tariq.new@example.com",
            address="DHA Phase 5"
        )
        self.assertEqual(updated.name, "Tariq Mahmood Updated")
        self.assertEqual(updated.phone, "0333-9988776")

        # Search
        results = CustomerService.get_all(search_query="Tariq")
        self.assertTrue(any(c.id == customer.id for c in results))

    def test_02_device_crud(self):
        cust = CustomerService.create(name="Kamran Akmal", phone="0345-5544332")
        
        device = DeviceService.create(
            customer_id=cust.id,
            brand="Apple",
            model="iPhone 14 Pro Max",
            imei_serial="352341908765432",
            color="Deep Purple",
            accessories_received="Original Case",
            physical_condition="Screen has micro-scratches"
        )
        self.assertIsNotNone(device.id)
        self.assertEqual(device.brand, "Apple")
        self.assertEqual(device.model, "iPhone 14 Pro Max")

        dev_list = DeviceService.get_by_customer(cust.id)
        self.assertEqual(len(dev_list), 1)
        self.assertEqual(dev_list[0].id, device.id)

        updated_dev = DeviceService.update(
            device_id=device.id,
            brand="Apple",
            model="iPhone 14 Pro Max (256GB)",
            imei_serial="352341908765432",
            color="Space Black",
            accessories_received="Case + Box",
            physical_condition="Mint"
        )
        self.assertEqual(updated_dev.model, "iPhone 14 Pro Max (256GB)")
        self.assertEqual(updated_dev.color, "Space Black")

    def test_03_job_workflow_and_financials(self):
        cust = CustomerService.create(name="Babar Azam", phone="0301-7788990")
        dev = DeviceService.create(
            customer_id=cust.id,
            brand="Samsung",
            model="Galaxy S24 Ultra",
            imei_serial="359998877665544",
            color="Titanium Gray"
        )

        # 1. Intake Job with passcode
        job = JobService.create(
            customer_id=cust.id,
            device_id=dev.id,
            complaint="Camera focus sensor not locking",
            physical_condition="Clean condition",
            accessories_received="SIM Tray",
            passcode_lock="9988",
            estimated_cost=6000.0,
            advance_paid=2000.0
        )
        self.assertIsNotNone(job.id)
        self.assertTrue(job.job_number.startswith("AT-"))
        self.assertEqual(job.status, JobStatus.IN_PROGRESS)
        self.assertEqual(job.balance_due, 4000.0)
        self.assertEqual(job.passcode_lock, "9988")

        # 2. Update Diagnosis
        diag_job = JobService.update_diagnosis(
            job_id=job.id,
            technician_diagnosis="OIS sensor stabilized, camera module replaced.",
            technician_notes="Used OEM Samsung camera component.",
            actual_cost=5500.0,
            status=JobStatus.READY
        )
        self.assertEqual(diag_job.status, JobStatus.READY)
        self.assertEqual(diag_job.actual_cost, 5500.0)
        self.assertEqual(diag_job.balance_due, 3500.0)
        self.assertIsNotNone(diag_job.diagnosed_at)
        self.assertIsNotNone(diag_job.completed_at)

        # 3. Deliver Job
        delivered_job = JobService.update(
            job_id=job.id,
            complaint=job.complaint,
            status=JobStatus.DELIVERED,
            advance_paid=5500.0, # Fully paid on collection
            actual_cost=5500.0
        )
        self.assertEqual(delivered_job.status, JobStatus.DELIVERED)
        self.assertEqual(delivered_job.balance_due, 0.0)

    def test_04_auth_and_rbac(self):
        import time
        # 1. Password hashing & verification
        pw = "superSecret123!"
        hashed = AuthService.hash_password(pw)
        self.assertTrue(AuthService.verify_password(pw, hashed))
        self.assertFalse(AuthService.verify_password("wrongPass", hashed))

        # 2. Create custom user with unique timestamp
        u_name = f"tech_zain_{int(time.time()*1000)}"
        success, msg = AuthService.create_user(
            username=u_name,
            password="techPassword456",
            full_name="Zain Ul Abideen",
            role=UserRole.TECHNICIAN,
            phone="0312-3344556"
        )
        self.assertTrue(success)

        # 3. Authenticate
        auth_ok, user, auth_msg = AuthService.authenticate(u_name, "techPassword456")
        self.assertTrue(auth_ok)
        self.assertIsNotNone(user)
        self.assertEqual(user.role, UserRole.TECHNICIAN)

        # 4. Check RBAC permissions
        self.assertTrue(AuthService.is_technician())
        self.assertFalse(AuthService.is_admin())

    def test_05_expense_management_and_profits(self):
        # Record expenses
        ok, exp1, _ = ExpenseService.add_expense(
            title="S24 Ultra OEM Camera Part Hafeez Centre",
            amount=3200.0,
            category=ExpenseCategory.PARTS,
            payment_mode=PaymentMethod.CASH,
            reference_no="INV-2024-5"
        )
        self.assertTrue(ok)
        self.assertIsNotNone(exp1.id)

        ok, exp2, _ = ExpenseService.add_expense(
            title="Shop Tea & Biscuits",
            amount=250.0,
            category=ExpenseCategory.TEA_FOOD,
            payment_mode=PaymentMethod.CASH
        )
        self.assertTrue(ok)

        # Fetch expenses
        exp_list = ExpenseService.get_expenses(category=ExpenseCategory.PARTS)
        self.assertTrue(any(e.id == exp1.id for e in exp_list))

        # Financial Summary
        summary = ExpenseService.get_financial_summary()
        self.assertGreaterEqual(summary["total_expenses"], 3450.0)
        self.assertIn(ExpenseCategory.PARTS, summary["category_breakdown"])

    def test_06_thermal_slip_generation(self):
        cust = CustomerService.create(name="Fakhar Zaman", phone="0300-9988112")
        dev = DeviceService.create(customer_id=cust.id, brand="Apple", model="iPad Pro 11", imei_serial="DMPZ8912")
        job = JobService.create(
            customer_id=cust.id,
            device_id=dev.id,
            complaint="USB-C charging port loose",
            passcode_lock="112233",
            estimated_cost=4500.0,
            advance_paid=1000.0
        )

        # Customer Slip HTML
        cust_html = ThermalSlipGenerator.generate_customer_receiving_slip(job)
        self.assertIn("CUSTOMER RECEIPT", cust_html)
        self.assertIn(job.job_number, cust_html)
        self.assertIn("Fakhar Zaman", cust_html)

        # Technician Slip HTML
        tech_html = ThermalSlipGenerator.generate_technician_diagnosis_slip(job)
        self.assertIn("REPAIRER TO-DO &amp; JOB CARD", tech_html)
        self.assertIn("112233", tech_html)
        self.assertIn("Technician To-Do Checklist", tech_html)

        # Shopkeeper Box Slip HTML (3-Inch Small)
        shop_html = ThermalSlipGenerator.generate_shopkeeper_slip(job)
        self.assertIn("SHOPKEEPER SLIP", shop_html)
        self.assertIn(job.job_number, shop_html)
        self.assertIn("Fakhar Zaman", shop_html)

        # Dual (Customer + Shopkeeper) Slip HTML
        dual_html = ThermalSlipGenerator.generate_dual_slip(job)
        self.assertIn("CUSTOMER RECEIPT", dual_html)
        self.assertIn("CUT HERE", dual_html)
        self.assertIn("SHOPKEEPER SLIP", dual_html)

        # Dual split into two standalone parts (used for auto-cut between copies)
        dual_parts = ThermalSlipGenerator.generate_dual_parts(job)
        self.assertEqual(len(dual_parts), 2)
        self.assertIn("CUSTOMER RECEIPT", dual_parts[0])
        self.assertIn("SHOPKEEPER SLIP", dual_parts[1])

        # URL QR block: skipped when no URL, adds scheme, renders a PNG data-URI
        self.assertEqual(ThermalSlipGenerator._url_qr_block({}), "")
        self.assertEqual(ThermalSlipGenerator._url_qr_block({"shop_url": "   "}), "")
        block = ThermalSlipGenerator._url_qr_block({"shop_url": "appletech.pk"})
        self.assertIn("data:image/png;base64,", block)
        self.assertIn("https://appletech.pk", block)

        # Customer receipt shows the URL QR only when a URL is configured
        with_url = ThermalSlipGenerator.generate_customer_receiving_slip(
            job, {"shop_url": "https://www.appletech.com", "currency_symbol": "Rs."}
        )
        self.assertIn("https://www.appletech.com", with_url)
        without_url = ThermalSlipGenerator.generate_customer_receiving_slip(
            job, {"currency_symbol": "Rs."}
        )
        self.assertNotIn("https://www.appletech.com", without_url)

        # Paper usage: slips must stay short on an 80mm roll
        from PySide6.QtWidgets import QApplication
        from PySide6.QtPrintSupport import QPrinter
        from PySide6.QtGui import QPageSize
        from app.services.print_service import (
            slip_height_mm, render_slip_to_printer, send_cut_command
        )
        # Cut helper must fail safely (never raise) with no printer name.
        self.assertFalse(send_cut_command(""))
        QApplication.instance() or QApplication([])
        self.assertLess(slip_height_mm(shop_html), 90)
        self.assertLess(slip_height_mm(cust_html), 160)

        pdf_path = Path("test_shop_slip.pdf")
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(str(pdf_path))
            h = render_slip_to_printer(shop_html, printer)
            size = printer.pageLayout().pageSize().size(QPageSize.Unit.Millimeter)
            self.assertAlmostEqual(size.width(), 80, delta=1)
            self.assertAlmostEqual(size.height(), h, delta=1)
            self.assertGreater(pdf_path.stat().st_size, 0)
        finally:
            if pdf_path.exists():
                pdf_path.unlink()

    def test_07_backup_and_settings(self):
        SettingsService.save_settings({
            "shop_name": "APPLE TECH PREMIER LAB",
            "currency_symbol": "Rs."
        })
        s = SettingsService.get_all_settings()
        self.assertEqual(s.get("shop_name"), "APPLE TECH PREMIER LAB")

        backup_file = BackupService.create_backup()
        self.assertTrue(backup_file.exists())
        self.assertGreater(backup_file.stat().st_size, 0)

    def test_08_gui_views_initialization(self):
        from PySide6.QtWidgets import QApplication
        from app.ui.main_window import MainWindow

        app = QApplication.instance()
        if not app:
            app = QApplication([])

        # Authenticate as admin
        AuthService.authenticate("admin", "admin123")
        
        # Instantiate MainWindow and all its internal views
        window = MainWindow()
        window._refresh_all_views()

        # Test JobDialog and DiagnosisDialog status dropdown initialization
        from app.ui.dialogs.job_dialog import JobDialog
        from app.ui.dialogs.diagnosis_dialog import DiagnosisDialog
        job_dlg = JobDialog()
        self.assertIsNotNone(job_dlg.status_combo)
        self.assertEqual(job_dlg.status_combo.count(), len(JobStatus.ALL_STATUSES))
        job_dlg.close()

    def test_09_print_preview_and_pdf(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtPrintSupport import QPrinter
        from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout
        from PySide6.QtCore import QSizeF, QMarginsF
        from app.ui.components.print_preview_dialog import ThermalPrintPreviewDialog

        app = QApplication.instance() or QApplication([])

        cust = CustomerService.create(name="Print Test User", phone="0333-0000000")
        dev = DeviceService.create(customer_id=cust.id, brand="Apple", model="iPhone 15 Pro")
        job = JobService.create(customer_id=cust.id, device_id=dev.id, complaint="Speaker issue")

        # Test ThermalPrintPreviewDialog initialization
        dlg = ThermalPrintPreviewDialog(job)
        self.assertGreaterEqual(dlg.tab_widget.count(), 3)
        # Combined (customer + shopkeeper) slip is the default first tab
        self.assertIn("Customer + Shop", dlg.tab_widget.tabText(0))
        self.assertTrue(hasattr(dlg, "auto_cut_checkbox"))
        # The combined tab prints as two jobs (so the cutter can cut between)
        self.assertEqual(len(dlg._get_print_units()), 2)

        # Test PDF creation with QPageLayout and QMarginsF
        pdf_path = Path("test_slip_output.pdf")
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(str(pdf_path))

            page_size = QPageSize(QSizeF(80, 297), QPageSize.Unit.Millimeter)
            layout = QPageLayout(
                page_size,
                QPageLayout.Orientation.Portrait,
                QMarginsF(2, 2, 2, 2),
                QPageLayout.Unit.Millimeter
            )
            printer.setPageLayout(layout)

            doc = QTextDocument()
            doc.setHtml(dlg._get_current_html())
            doc.print_(printer)

            self.assertTrue(pdf_path.exists())
            self.assertGreater(pdf_path.stat().st_size, 0)
        finally:
            dlg.close()
            if pdf_path.exists():
                pdf_path.unlink()

    @classmethod
    def tearDownClass(cls):
        # Clean up test data so it doesn't pollute the user's DB
        with session_scope() as session:
            session.query(RepairJob).delete()
            session.query(Device).delete()
            session.query(Customer).delete()
            session.query(Expense).delete()
            session.query(User).filter(User.username != "admin").delete()


if __name__ == "__main__":
    unittest.main()

