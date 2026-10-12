# 📱 Apple Tech - Mobile Repair Enterprise POS & ERP

A professional, high-performance, completely offline Windows desktop ERP application designed specifically for mobile phone repairing shops, workshop service centers, and electronics retail.

Built with **Python 3.12+**, **PySide6 (Qt for Python)**, **SQLite**, **SQLAlchemy 2.x ORM**, and **PyInstaller**.

---

## 🌟 Key Enterprise Features

### 1. 🎨 Modern White & Blue ERP Interface
* Clean, high-contrast light ERP design system tailored for fast workshop operations.
* Crisp KPI stat cards, status pill badges, subtle borders, and smooth responsiveness.
* High readability for shop counters, repair workstations, and owner overview.

### 2. 🖨️ 3-Inch (80mm) Dual Slip Printing System (2-in-1 Combined Slips)
* **2-in-1 Dual Slip (Continuous Print with Cut Line)**:
  - Generates both Customer Slip AND Repairer / Technician To-Do Slip in one continuous printout separated by a dotted cut line.
* **Repairer / Technician To-Do Slip**:
  - Contains device passcode / lock pattern box (`🔑 Passcode: 1234`).
  - Technician To-Do hardware checklist (Display, Touch, Charging Port, Mic, Speaker, Camera, Wi-Fi, Battery, FaceID/TouchID).
  - Assigned technician name, target delivery promise date, and parts required notes.
  - Technician & Quality Check (QC) sign-off boxes.
* **Customer Receiving Slip**:
  - Official shop header, job barcode visual, customer contact, and device details.
  - Financial breakdown (Estimated Cost, Advance Paid, Balance Due).
  - Shop terms & warranty disclaimer with customer & authorized signatures.
* **Final Delivery & Warranty Invoice**:
  - 30-day warranty certificate slip issued upon job delivery.
* **Direct Printing & PDF Export**: Instant output to any standard 80mm thermal POS receipt printer or export to PDF.

### 3. 💰 Expense & Kharcha Management (Daily Soda / Shop Outflow)
* Dedicated **Expenses / Kharcha** module to track parts purchases, shop rent, electricity, refreshments/tea, and staff salaries.
* Track payment modes (Cash, Bank Transfer, EasyPaisa, JazzCash, Card) and invoice reference numbers.
* **Real-time Financial Calculations**:
  - Total Daily & Monthly Outflows.
  - Total Repair Revenue.
  - **Net Shop Profit (Total Revenue − Total Expenses)**.
* Filter expenses by date range (Today, This Week, This Month, All Time) and category.

### 4. 🔐 Authentication & Role-Based Access Control (RBAC)
* Secure login dialog on startup with PBKDF2-HMAC-SHA256 salted password hashing.
* **Role Permissions**:
  - **👑 Admin / Owner**: Full access to all modules, financial KPIs, profit/loss metrics, user management, and database backup/restore.
  - **💼 Cashier / Front Desk**: Job intake, customer & device registration, deliveries, balance collection, customer slip printing, and expense recording.
  - **🔧 Technician / Repairer**: Job queue, technician diagnosis, checklist updates, passcode lookup, and repairer To-Do slip printing.
* User account management tab in Settings (create, edit, reset passwords, activate/deactivate accounts).
* **Default Seed Accounts**:
  - Admin: `admin` / `admin123`
  - Cashier: `cashier` / `cashier123`
  - Technician: `technician` / `tech123`

### 5. 👥 Customer & Device Management
* Master-detail customer directory with complete repair history timeline.
* Device directory with IMEI, serial number, brand, model, and physical condition tracking.

### 6. 🗄️ Offline Database Persistence & Maintenance
* SQLite database with foreign keys and WAL mode for zero data corruption.
* Data stored safely in `%APPDATA%/AppleTechPOS/apple_tech.db`.
* Automatic schema migration and point-in-time database backups & restores.

---

## 🚀 Running the Application

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Locally
```bash
python main.py
```

### 3. Build Standalone Windows EXE
```bash
python build_exe.py
```
Executable will be generated in `dist/AppleTechPOS.exe`.
