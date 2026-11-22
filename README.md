# 📚 Digital Library Management System 

> A modern, full-featured **Digital Library Management System** ported into Python with an elegant, minimalist white aesthetic and responsive UI/UX.

---

## 🌟 Key Highlights & Features

- **Pristine White Aesthetic & Refined UX**: Modern Scandinavian and Apple-inspired minimalist design with crisp white surfaces, soft diffuse ambient shadows, and clear typography.
- **Full Python Backend Parity**: 100% feature and API parity with the original C++ system using a clean, asynchronous-capable Flask + SQLite3 architecture.
- **Role-Based Access Control**:
  - **Admin**: Catalog inventory CRUD, member management, cross-user book issuing, return approvals, fine waivers, live visual analytics, and CSV exports.
  - **Student / Reader**: Personalized reading dashboard, instant search, smart category recommendations, active loan tracker, overdue fine settlement, and return requests.
- **Circulation & Automated Late Fines**:
  - Automated loan duration scheduling (7, 14, 21, or 30 days).
  - Dynamic late fine calculation at **₹2.00 / day** past the due date.
  - Multi-channel simulated payment gateway (UPI QR Code, Debit/Credit Card, Counter Cash).
- **Barcode & QR Simulator**:
  - Live SVG barcode generation based on book IDs (`BOOK-1001` through `BOOK-1009`).
  - Interactive barcode scanner modal for rapid book lookup, issue, and return.
- **Smart Recommendations Engine**: Suggests books based on user borrow history and category popularity.
- **Bilingual Interface (English & हिंदी)**: Complete bilingual dictionary supporting live, instant language switching without page reloads.
- **Live Admin Analytics**: Chart.js data visualization displaying top borrowed titles, category breakdown, and monthly circulation volume.
- **Data Exporting**: Instant CSV download for Books Inventory (`/export/books.csv`) and Library Members (`/export/users.csv`).

---

## 📁 Project Structure

```text
digital_library_system/
│
├── app.py                  # Flask REST API backend & static file server
├── database.py             # SQLite database layer, migrations & circulation rules
├── run.py                  # Python launcher script with auto-browser launch
├── run.bat                 # 1-Click Windows execution script
├── test_system.py          # Automated test suite (8 test suites, 100% pass)
├── requirements.txt        # Python dependency manifest (Flask)
├── library.db              # SQLite3 database (auto-created & pre-seeded)
│
├── templates/
│   └── index.html          # Elegant White UI Digital Library interface
│
└── static/
    ├── css/
    │   └── style.css       # Clean white theme styling, responsive grid & animations
    └── js/
        ├── translations.js # Bilingual dictionary (English & Hindi)
        └── app.js          # Client state, Chart.js integrations & API handlers
```

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.8 or higher installed on your system.

### 2. Run with 1-Click (Windows)
Double-click `run.bat` or run in terminal:

```powershell
.\run.bat
```

### 3. Run Manually via Terminal

```powershell
# Navigate to the project directory
cd "d:\diaster management\digital_library_system"

# Run the system launcher
python run.py
```

The system will start on **`http://localhost:8080`** and automatically open in your default browser.

---

## 🔑 Demo Accounts

The database comes pre-seeded with sample books, members, active loans, and overdue fines for instant testing:

| Role | Email | Password | Description |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@lms.com` | `admin123` | Full access to catalog editing, analytics, and exports |
| **Student** | `student@lms.com` | `student123` | Active student with 1 active loan and 1 overdue fine |
| **Student** | `neha@lms.com` | `reader123` | Student reader with Hindi preference |

> **Pro Tip**: On the login screen, click the **"Quick Demo Login"** buttons to auto-fill and sign in with a single click.

---

## 📡 REST API Reference

The Python backend implements all original C++ endpoints with identical JSON schemas:

### Authentication & Sessions
- `POST /register`: Create a new member account (`name`, `email`, `password`, `role`, `preferred_language`).
- `POST /login`: Authenticate and receive a session token.
- `GET /session`: Verify active session (`X-Session-Token` header).
- `POST /logout`: Invalidate current session token.

### Books Catalog
- `GET /books`: List books with optional `?search=...`, `?category=...`, `?available_only=true`.
- `GET /books/<id>`: Get single book details.
- `POST /add-book`: Add new book title (Admin only).
- `PUT /books/<id>`: Update book information (Admin only).
- `DELETE /books/<id>`: Remove book from catalog (Admin only).
- `GET /search-suggestions?q=...`: Real-time autocomplete suggestions.

### Circulation & Fines
- `POST /issue-book`: Issue a book copy (`book_id`, `user_id` [optional for admin], `days`).
- `POST /return-book`: Process return, increment copies, and compute overdue fines.
- `GET /transactions`: Retrieve all loans (Admin) or user-specific loans (Student).
- `POST /pay-fine`: Settle fine (`transaction_id`, `payment_method`: UPI / Card / Cash).

### Insights, Reports & Data Export
- `GET /dashboard`: Aggregate metrics for stat cards.
- `GET /notifications`: Time-sensitive return reminders and overdue alerts.
- `GET /recommendations`: Personalized book suggestions.
- `GET /analytics`: Chart dataset for admin analytics.
- `GET /export/books.csv`: Download complete books inventory as CSV.
- `GET /export/users.csv`: Download member roster as CSV.

---

## 🧪 Automated Testing

An automated test suite is included in `test_system.py`:

```powershell
python test_system.py
```

Output:
```text
........
----------------------------------------------------------------------
Ran 8 tests in 1.169s

OK
```
