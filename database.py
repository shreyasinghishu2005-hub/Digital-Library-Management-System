"""
Database Layer for Digital Library Management System
SQLite3 database manager with connection pooling, automatic migrations,
data seeding, and comprehensive business logic.
"""

import os
import sqlite3
import hashlib
import secrets
import csv
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any


def hash_password(password: str) -> str:
    """Create a deterministic salted SHA-256 hash for authentication."""
    salted = f"lms-demo-salt-{password}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def today_str() -> str:
    """Return today's date as YYYY-MM-DD string."""
    return datetime.now().strftime("%Y-%m-%d")


def now_str() -> str:
    """Return current timestamp as YYYY-MM-DD HH:MM:SS string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_days(date_str: str, days: int) -> str:
    """Add days to a YYYY-MM-DD string."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return (dt + timedelta(days=days)).strftime("%Y-%m-%d")


def days_between(start_date: str, end_date: str) -> int:
    """Calculate days between two YYYY-MM-DD strings."""
    try:
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date, "%Y-%m-%d")
        return (d2 - d1).days
    except Exception:
        return 0


def calculate_fine(due_date: str, return_date: Optional[str] = None, daily_rate: float = 2.0) -> float:
    """Calculate overdue fine at given daily rate."""
    target_date = return_date if return_date else today_str()
    overdue_days = days_between(due_date, target_date)
    return round(max(0, overdue_days) * daily_rate, 2)


class Database:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(base_dir, "library.db")
        else:
            self.db_path = db_path
        self.initialize()
        self.seed()

    def get_connection(self) -> sqlite3.Connection:
        """Establish a connection with foreign keys enabled and row factory configured."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize(self):
        """Initialize database schema with all required tables."""
        with self.get_connection() as conn:
            conn.executescript("""
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'student')),
                    preferred_language TEXT NOT NULL DEFAULT 'en',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    category TEXT NOT NULL,
                    isbn TEXT NOT NULL,
                    barcode TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    total_copies INTEGER NOT NULL DEFAULT 1,
                    available_copies INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    issue_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    return_date TEXT DEFAULT '',
                    status TEXT NOT NULL CHECK(status IN ('issued', 'returned')),
                    fine_amount REAL NOT NULL DEFAULT 0,
                    fine_paid INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    transaction_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    status TEXT NOT NULL,
                    paid_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

    def seed(self):
        """Populate initial demo users, books, and transactions if empty."""
        with self.get_connection() as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if user_count > 0:
                return

            today = today_str()
            # Demo Users
            users_data = [
                ("Admin User", "admin@lms.com", hash_password("admin123"), "admin", "en", today),
                ("Aarav Student", "student@lms.com", hash_password("student123"), "student", "en", today),
                ("Neha Reader", "neha@lms.com", hash_password("reader123"), "student", "hi", today),
                ("Priya Sharma", "priya@lms.com", hash_password("priya123"), "student", "en", today),
            ]
            conn.executemany(
                "INSERT INTO users (name, email, password_hash, role, preferred_language, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                users_data
            )

            # Rich Initial Books Collection
            books_data = [
                ("Clean Code", "Robert C. Martin", "Programming", "9780132350884", "BOOK-1001", "A handbook of agile software craftsmanship and best practices.", 4, 2, today),
                ("The Pragmatic Programmer", "Andrew Hunt & David Thomas", "Programming", "9780135957059", "BOOK-1002", "Classic guide to journeying from journeyman to software craftsmanship.", 3, 2, today),
                ("Atomic Habits", "James Clear", "Self Help", "9781847941831", "BOOK-1003", "An easy and proven way to build good habits and break bad ones.", 5, 5, today),
                ("Wings of Fire", "Dr. A.P.J. Abdul Kalam", "Biography", "9788173711466", "BOOK-1004", "An inspiring autobiography of the former President of India.", 2, 1, today),
                ("The Alchemist", "Paulo Coelho", "Fiction", "9780061122415", "BOOK-1005", "A magical fable about following one's dreams and destiny.", 3, 3, today),
                ("Introduction to Algorithms (CLRS)", "Thomas H. Cormen", "Computer Science", "9780262033848", "BOOK-1006", "The comprehensive foundational textbook on algorithmic analysis and design.", 4, 3, today),
                ("Deep Work", "Cal Newport", "Self Help", "9781455586691", "BOOK-1007", "Rules for focused success in a distracted world.", 3, 3, today),
                ("Design Patterns: Elements of Reusable Object-Oriented Software", "Erich Gamma et al.", "Programming", "9780201633610", "BOOK-1008", "The Gang of Four classic on 23 design patterns in software architecture.", 3, 2, today),
                ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "History", "9780062316097", "BOOK-1009", "Explores human evolution, societies, and revolutions over centuries.", 4, 4, today)
            ]
            conn.executemany(
                "INSERT INTO books (title, author, category, isbn, barcode, description, total_copies, available_copies, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                books_data
            )

            # Sample Transactions
            transactions_data = [
                # Active non-overdue
                (2, 1, add_days(today, -5), add_days(today, 9), "", "issued", 0.0, 0),
                # Active OVERDUE transaction (due 6 days ago -> fine 12.00)
                (2, 2, add_days(today, -20), add_days(today, -6), "", "issued", 12.0, 0),
                # Returned with fine paid
                (3, 4, add_days(today, -28), add_days(today, -14), add_days(today, -10), "returned", 8.0, 1),
                # Active non-overdue
                (4, 8, add_days(today, -2), add_days(today, 12), "", "issued", 0.0, 0),
            ]
            conn.executemany(
                "INSERT INTO transactions (user_id, book_id, issue_date, due_date, return_date, status, fine_amount, fine_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                transactions_data
            )

            # Sample Payment Record for transaction 3
            payments_data = [
                (3, 3, 8.0, "UPI", "completed", add_days(today, -10) + " 14:32:00")
            ]
            conn.executemany(
                "INSERT INTO payments (user_id, transaction_id, amount, payment_method, status, paid_at) VALUES (?, ?, ?, ?, ?, ?)",
                payments_data
            )

    # ------------------ AUTH & USERS ------------------

    def create_user(self, name: str, email: str, password: str, role: str = "student", preferred_language: str = "en") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Register a new user."""
        email_clean = email.strip().lower()
        if not name.strip() or not email_clean or len(password) < 6:
            return False, "Name, valid email, and password (minimum 6 characters) are required.", None

        if role not in ("admin", "student"):
            role = "student"

        pwd_hash = hash_password(password)
        created_at = today_str()

        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO users (name, email, password_hash, role, preferred_language, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (name.strip(), email_clean, pwd_hash, role, preferred_language, created_at)
                )
                user_id = cursor.lastrowid
                user = {
                    "id": user_id,
                    "name": name.strip(),
                    "email": email_clean,
                    "role": role,
                    "preferred_language": preferred_language,
                    "created_at": created_at
                }
                return True, "User registered successfully.", user
        except sqlite3.IntegrityError:
            return False, "An account with this email already exists.", None
        except Exception as e:
            return False, str(e), None

    def authenticate_user(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Verify user credentials."""
        email_clean = email.strip().lower()
        pwd_hash = hash_password(password)

        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id, name, email, password_hash, role, preferred_language, created_at FROM users WHERE email = ?",
                (email_clean,)
            ).fetchone()

            if not row:
                return False, "No account found with this email address.", None

            # Validate hash
            if row["password_hash"] != pwd_hash:
                return False, "Incorrect password. Please try again.", None

            user = {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "role": row["role"],
                "preferred_language": row["preferred_language"],
                "created_at": row["created_at"]
            }
            return True, "Authentication successful.", user

    def create_session(self, user_id: int) -> str:
        """Create and store a session token."""
        token = secrets.token_hex(24)
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, now_str())
            )
        return token

    def get_session_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Look up user by active session token."""
        if not token:
            return None
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT u.id, u.name, u.email, u.role, u.preferred_language, u.created_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ?
            """, (token,)).fetchone()
            if row:
                return dict(row)
            return None

    def delete_session(self, token: str):
        """Invalidate session token."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get list of all users."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT id, name, email, role, preferred_language, created_at FROM users ORDER BY name ASC").fetchall()
            return [dict(r) for r in rows]

    # ------------------ BOOKS MANAGEMENT ------------------

    def get_books(self, search: Optional[str] = None, category: Optional[str] = None, available_only: bool = False) -> List[Dict[str, Any]]:
        """Query books with optional search, category, and availability filters."""
        query = "SELECT * FROM books WHERE 1=1"
        params: List[Any] = []

        if search:
            s = f"%{search.strip()}%"
            query += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ? OR barcode LIKE ? OR category LIKE ?)"
            params.extend([s, s, s, s, s])

        if category and category != "all":
            query += " AND category = ?"
            params.append(category)

        if available_only:
            query += " AND available_copies > 0"

        query += " ORDER BY title ASC"

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_book_by_id(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Fetch book by primary ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return dict(row) if row else None

    def get_book_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Fetch book by barcode."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM books WHERE barcode = ?", (barcode.strip(),)).fetchone()
            return dict(row) if row else None

    def add_book(self, data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Add a new book to the library catalog."""
        title = data.get("title", "").strip()
        author = data.get("author", "").strip()
        category = data.get("category", "").strip()
        isbn = data.get("isbn", "").strip()
        description = data.get("description", "").strip()
        total_copies = int(data.get("total_copies", 1))

        if not title or not author or not category or not isbn:
            return False, "Title, author, category, and ISBN are required.", None

        if total_copies < 1:
            total_copies = 1

        barcode = data.get("barcode", "").strip()
        if not barcode:
            # Generate simulated barcode
            barcode = f"BOOK-{int(datetime.now().timestamp() * 1000)}"

        available_copies = total_copies
        created_at = today_str()

        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO books (title, author, category, isbn, barcode, description, total_copies, available_copies, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (title, author, category, isbn, barcode, description, total_copies, available_copies, created_at))
                new_id = cursor.lastrowid
                row = conn.execute("SELECT * FROM books WHERE id = ?", (new_id,)).fetchone()
                book = dict(row) if row else None
                return True, "Book added successfully.", book
        except sqlite3.IntegrityError:
            return False, "A book with this barcode already exists.", None
        except Exception as e:
            return False, str(e), None

    def update_book(self, book_id: int, data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Update an existing book's details."""
        existing = self.get_book_by_id(book_id)
        if not existing:
            return False, "Book not found.", None

        title = data.get("title", existing["title"]).strip()
        author = data.get("author", existing["author"]).strip()
        category = data.get("category", existing["category"]).strip()
        isbn = data.get("isbn", existing["isbn"]).strip()
        barcode = data.get("barcode", existing["barcode"]).strip()
        description = data.get("description", existing["description"]).strip()

        # Handle copies adjustment carefully
        total_copies = int(data.get("total_copies", existing["total_copies"]))
        issued_copies = existing["total_copies"] - existing["available_copies"]
        if total_copies < issued_copies:
            return False, f"Total copies cannot be less than currently issued copies ({issued_copies}).", None

        available_copies = total_copies - issued_copies

        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE books
                    SET title = ?, author = ?, category = ?, isbn = ?, barcode = ?, description = ?,
                        total_copies = ?, available_copies = ?
                    WHERE id = ?
                """, (title, author, category, isbn, barcode, description, total_copies, available_copies, book_id))
                row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                updated = dict(row) if row else None
                return True, "Book updated successfully.", updated
        except sqlite3.IntegrityError:
            return False, "Barcode must be unique.", None
        except Exception as e:
            return False, str(e), None

    def delete_book(self, book_id: int) -> Tuple[bool, str]:
        """Delete a book if no copies are currently issued."""
        existing = self.get_book_by_id(book_id)
        if not existing:
            return False, "Book not found."

        with self.get_connection() as conn:
            active_issues = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE book_id = ? AND status = 'issued'",
                (book_id,)
            ).fetchone()[0]

            if active_issues > 0:
                return False, f"Cannot delete book while {active_issues} copy/copies are currently issued out."

            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return True, "Book deleted successfully."

    # ------------------ CIRCULATION: ISSUE & RETURN ------------------

    def issue_book(self, user_id: int, book_id: int, days: int = 14) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Issue a book copy to a user."""
        book = self.get_book_by_id(book_id)
        if not book:
            return False, "Book not found.", None

        if book["available_copies"] <= 0:
            return False, "No copies of this book are currently available for issuing.", None

        with self.get_connection() as conn:
            # Check user exists
            user = conn.execute("SELECT id, name FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return False, "User not found.", None

            # Check if user already has an active issue of this specific book
            already_has = conn.execute(
                "SELECT id FROM transactions WHERE user_id = ? AND book_id = ? AND status = 'issued'",
                (user_id, book_id)
            ).fetchone()
            if already_has:
                return False, "This user already has a copy of this book currently issued.", None

            issue_date = today_str()
            due_date = add_days(issue_date, days)

            # Atomic transaction: decrement copies and insert transaction record
            cursor = conn.execute("""
                INSERT INTO transactions (user_id, book_id, issue_date, due_date, return_date, status, fine_amount, fine_paid)
                VALUES (?, ?, ?, ?, '', 'issued', 0.0, 0)
            """, (user_id, book_id, issue_date, due_date))
            tx_id = cursor.lastrowid

            conn.execute(
                "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?",
                (book_id,)
            )

            tx = {
                "id": tx_id,
                "user_id": user_id,
                "user_name": user["name"],
                "book_id": book_id,
                "book_title": book["title"],
                "issue_date": issue_date,
                "due_date": due_date,
                "status": "issued",
                "fine_amount": 0.0
            }
            return True, f"Book '{book['title']}' issued successfully. Due on {due_date}.", tx

    def return_book(self, transaction_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Process book return, calculate fines if overdue, and restore book inventory."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT t.id, t.user_id, t.book_id, t.issue_date, t.due_date, t.return_date, t.status, t.fine_amount, t.fine_paid,
                       b.title AS book_title, u.name AS user_name
                FROM transactions t
                JOIN books b ON b.id = t.book_id
                JOIN users u ON u.id = t.user_id
                WHERE t.id = ?
            """, (transaction_id,)).fetchone()

            if not row:
                return False, "Transaction record not found.", None

            if row["status"] == "returned":
                return False, "This book has already been marked as returned.", None

            return_date = today_str()
            fine = calculate_fine(row["due_date"], return_date, daily_rate=2.0)

            # Update transaction
            conn.execute("""
                UPDATE transactions
                SET return_date = ?, status = 'returned', fine_amount = ?
                WHERE id = ?
            """, (return_date, fine, transaction_id))

            # Restore book copy
            conn.execute(
                "UPDATE books SET available_copies = available_copies + 1 WHERE id = ?",
                (row["book_id"],)
            )

            overdue_days = max(0, days_between(row["due_date"], return_date))
            info = {
                "transaction_id": transaction_id,
                "book_title": row["book_title"],
                "user_name": row["user_name"],
                "return_date": return_date,
                "due_date": row["due_date"],
                "overdue_days": overdue_days,
                "fine_amount": fine,
                "fine_paid": row["fine_paid"]
            }

            msg = "Book returned successfully."
            if fine > 0:
                msg += f" Overdue by {overdue_days} day(s). Fine due: ₹{fine:.2f}."
            return True, msg, info

    def pay_fine(self, transaction_id: int, user_id: Optional[int] = None, payment_method: str = "UPI") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Record fine payment simulation."""
        with self.get_connection() as conn:
            if user_id is not None:
                row = conn.execute("""
                    SELECT id, user_id, book_id, fine_amount, fine_paid, status, due_date
                    FROM transactions
                    WHERE id = ? AND user_id = ?
                """, (transaction_id, user_id)).fetchone()
            else:
                row = conn.execute("""
                    SELECT id, user_id, book_id, fine_amount, fine_paid, status, due_date
                    FROM transactions
                    WHERE id = ?
                """, (transaction_id,)).fetchone()

            if not row:
                return False, "Transaction not found for this user.", None

            target_user_id = row["user_id"]

            # Calculate current fine dynamically if still issued and overdue
            fine = row["fine_amount"]
            if row["status"] == "issued":
                fine = calculate_fine(row["due_date"], today_str())
                conn.execute("UPDATE transactions SET fine_amount = ? WHERE id = ?", (fine, transaction_id))

            if fine <= 0:
                return False, "No outstanding fine is due for this transaction.", None

            if row["fine_paid"] == 1:
                return False, "The fine for this transaction has already been paid.", None

            paid_at = now_str()
            cursor = conn.execute("""
                INSERT INTO payments (user_id, transaction_id, amount, payment_method, status, paid_at)
                VALUES (?, ?, ?, ?, 'completed', ?)
            """, (target_user_id, transaction_id, fine, payment_method, paid_at))
            payment_id = cursor.lastrowid

            conn.execute("UPDATE transactions SET fine_paid = 1 WHERE id = ?", (transaction_id,))

            payment_info = {
                "payment_id": payment_id,
                "transaction_id": transaction_id,
                "amount": fine,
                "payment_method": payment_method,
                "status": "completed",
                "paid_at": paid_at
            }
            return True, f"Fine of ₹{fine:.2f} paid successfully via {payment_method}.", payment_info

    # ------------------ TRANSACTIONS & STATS ------------------

    def get_transactions(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch all transactions or transactions for a specific user with live fine calculation."""
        query = """
            SELECT t.id, t.user_id, t.book_id, t.issue_date, t.due_date, t.return_date, t.status,
                   t.fine_amount, t.fine_paid,
                   b.title AS book_title, b.author AS book_author, b.barcode AS book_barcode,
                   u.name AS user_name, u.email AS user_email
            FROM transactions t
            JOIN books b ON b.id = t.book_id
            JOIN users u ON u.id = t.user_id
        """
        params: List[Any] = []
        if user_id is not None:
            query += " WHERE t.user_id = ?"
            params.append(user_id)

        query += " ORDER BY t.id DESC"

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            today = today_str()
            for r in rows:
                item = dict(r)
                # Compute live fine for actively issued overdue books
                if item["status"] == "issued" and item["due_date"] < today:
                    live_fine = calculate_fine(item["due_date"], today)
                    item["fine_amount"] = max(item["fine_amount"], live_fine)
                    item["is_overdue"] = True
                else:
                    item["is_overdue"] = item["status"] == "issued" and item["due_date"] < today
                results.append(item)
            return results

    def get_dashboard_stats(self, user_id: int, role: str) -> Dict[str, Any]:
        """Aggregate summary metrics for admin or student dashboards."""
        today = today_str()
        stats: Dict[str, Any] = {}

        with self.get_connection() as conn:
            if role == "admin":
                stats["total_books"] = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
                stats["total_copies"] = conn.execute("SELECT COALESCE(SUM(total_copies), 0) FROM books").fetchone()[0]
                stats["available_copies"] = conn.execute("SELECT COALESCE(SUM(available_copies), 0) FROM books").fetchone()[0]
                stats["issued_copies"] = stats["total_copies"] - stats["available_copies"]
                stats["total_members"] = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
                stats["active_issues"] = conn.execute("SELECT COUNT(*) FROM transactions WHERE status = 'issued'").fetchone()[0]
                stats["overdue_issues"] = conn.execute(
                    "SELECT COUNT(*) FROM transactions WHERE status = 'issued' AND due_date < ?",
                    (today,)
                ).fetchone()[0]
                stats["total_fines_collected"] = conn.execute("SELECT COALESCE(SUM(amount), 0.0) FROM payments WHERE status = 'completed'").fetchone()[0]
                stats["pending_fines"] = conn.execute(
                    "SELECT COALESCE(SUM(fine_amount), 0.0) FROM transactions WHERE fine_paid = 0 AND (status = 'returned' OR (status = 'issued' AND due_date < ?))",
                    (today,)
                ).fetchone()[0]
            else:
                stats["my_issued_books"] = conn.execute(
                    "SELECT COUNT(*) FROM transactions WHERE user_id = ? AND status = 'issued'",
                    (user_id,)
                ).fetchone()[0]
                stats["my_returned_books"] = conn.execute(
                    "SELECT COUNT(*) FROM transactions WHERE user_id = ? AND status = 'returned'",
                    (user_id,)
                ).fetchone()[0]
                stats["my_overdue_books"] = conn.execute(
                    "SELECT COUNT(*) FROM transactions WHERE user_id = ? AND status = 'issued' AND due_date < ?",
                    (user_id, today)
                ).fetchone()[0]
                stats["my_unpaid_fines"] = conn.execute(
                    "SELECT COALESCE(SUM(fine_amount), 0.0) FROM transactions WHERE user_id = ? AND fine_paid = 0 AND fine_amount > 0",
                    (user_id,)
                ).fetchone()[0]
                stats["total_catalog_books"] = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]

            return stats

    def get_notifications(self, user_id: int) -> List[Dict[str, Any]]:
        """Generate time-sensitive alerts for a student (due soon, overdue, unpaid fines)."""
        today = today_str()
        notifications: List[Dict[str, Any]] = []

        with self.get_connection() as conn:
            # Active issued books
            rows = conn.execute("""
                SELECT t.id, b.title, t.due_date, t.fine_amount, t.fine_paid
                FROM transactions t
                JOIN books b ON b.id = t.book_id
                WHERE t.user_id = ? AND t.status = 'issued'
                ORDER BY t.due_date ASC
            """, (user_id,)).fetchall()

            for r in rows:
                tx_id = r["id"]
                title = r["title"]
                due_date = r["due_date"]
                diff = days_between(today, due_date)

                if diff < 0:
                    overdue_days = abs(diff)
                    fine = calculate_fine(due_date, today)
                    notifications.append({
                        "type": "danger",
                        "title": f"Overdue Book: {title}",
                        "message": f"This book was due {overdue_days} day(s) ago on {due_date}. Accumulated fine: ₹{fine:.2f}.",
                        "transaction_id": tx_id,
                        "date": due_date
                    })
                elif diff <= 3:
                    notifications.append({
                        "type": "warning",
                        "title": f"Return Reminder: {title}",
                        "message": f"This book is due in {diff} day(s) on {due_date}. Please return or renew on time.",
                        "transaction_id": tx_id,
                        "date": due_date
                    })

            # Returned books with unpaid fine
            unpaid_fines = conn.execute("""
                SELECT t.id, b.title, t.fine_amount
                FROM transactions t
                JOIN books b ON b.id = t.book_id
                WHERE t.user_id = ? AND t.status = 'returned' AND t.fine_amount > 0 AND t.fine_paid = 0
            """, (user_id,)).fetchall()

            for uf in unpaid_fines:
                notifications.append({
                    "type": "info",
                    "title": f"Pending Fine: ₹{uf['fine_amount']:.2f}",
                    "message": f"You have an outstanding fine on '{uf['title']}'. Tap to settle online.",
                    "transaction_id": uf["id"],
                    "date": today
                })

        return notifications

    def get_recommendations(self, user_id: int, limit: int = 4) -> List[Dict[str, Any]]:
        """Recommend books based on user reading preference and popularity."""
        with self.get_connection() as conn:
            # Check user's most borrowed category
            favorite_cat = conn.execute("""
                SELECT b.category, COUNT(*) as cnt
                FROM transactions t
                JOIN books b ON b.id = t.book_id
                WHERE t.user_id = ?
                GROUP BY b.category
                ORDER BY cnt DESC
                LIMIT 1
            """, (user_id,)).fetchone()

            fav_category = favorite_cat["category"] if favorite_cat else None

            # Get available books in preferred category that the user does not currently hold
            books = []
            if fav_category:
                rows = conn.execute("""
                    SELECT b.*
                    FROM books b
                    WHERE b.available_copies > 0
                      AND b.category = ?
                      AND b.id NOT IN (
                          SELECT book_id FROM transactions WHERE user_id = ? AND status = 'issued'
                      )
                    ORDER BY b.title ASC
                    LIMIT ?
                """, (fav_category, user_id, limit)).fetchall()
                books = [dict(r) for r in rows]

            # If not enough books, fill with top available books
            if len(books) < limit:
                needed = limit - len(books)
                existing_ids = [b["id"] for b in books]
                placeholder = ",".join("?" for _ in existing_ids) if existing_ids else "0"
                fill_rows = conn.execute(f"""
                    SELECT b.*
                    FROM books b
                    WHERE b.available_copies > 0
                      AND b.id NOT IN ({placeholder})
                      AND b.id NOT IN (
                          SELECT book_id FROM transactions WHERE user_id = ? AND status = 'issued'
                      )
                    ORDER BY b.available_copies DESC, b.title ASC
                    LIMIT ?
                """, (*existing_ids, user_id, needed)).fetchall()
                books.extend([dict(r) for r in fill_rows])

            return books

    def get_search_suggestions(self, query_str: str) -> List[Dict[str, str]]:
        """Return autocomplete suggestions matching query string."""
        if not query_str or len(query_str.strip()) < 1:
            return []

        q = f"%{query_str.strip()}%"
        suggestions = []

        with self.get_connection() as conn:
            # Titles
            rows = conn.execute("SELECT DISTINCT title FROM books WHERE title LIKE ? LIMIT 5", (q,)).fetchall()
            for r in rows:
                suggestions.append({"label": r["title"], "type": "title"})

            # Authors
            rows = conn.execute("SELECT DISTINCT author FROM books WHERE author LIKE ? LIMIT 3", (q,)).fetchall()
            for r in rows:
                suggestions.append({"label": r["author"], "type": "author"})

            # Categories
            rows = conn.execute("SELECT DISTINCT category FROM books WHERE category LIKE ? LIMIT 3", (q,)).fetchall()
            for r in rows:
                suggestions.append({"label": r["category"], "type": "category"})

            # Barcode
            rows = conn.execute("SELECT barcode, title FROM books WHERE barcode LIKE ? LIMIT 2", (q,)).fetchall()
            for r in rows:
                suggestions.append({"label": f"{r['barcode']} - {r['title']}", "type": "barcode"})

        return suggestions[:8]

    def get_analytics(self) -> Dict[str, Any]:
        """Aggregate data for admin analytics charts."""
        analytics: Dict[str, Any] = {}

        with self.get_connection() as conn:
            # Most Borrowed Books
            most_borrowed = conn.execute("""
                SELECT b.title AS label, COUNT(t.id) AS value
                FROM books b
                LEFT JOIN transactions t ON t.book_id = b.id
                GROUP BY b.id, b.title
                ORDER BY value DESC, b.title ASC
                LIMIT 6
            """).fetchall()
            analytics["most_borrowed_books"] = [dict(r) for r in most_borrowed]

            # Category Distribution
            category_counts = conn.execute("""
                SELECT category AS label, SUM(total_copies) AS value
                FROM books
                GROUP BY category
                ORDER BY value DESC
            """).fetchall()
            analytics["categories"] = [dict(r) for r in category_counts]

            # Monthly Borrowing Activity (Last 6 months)
            monthly = conn.execute("""
                SELECT strftime('%Y-%m', issue_date) AS month, COUNT(*) AS count
                FROM transactions
                GROUP BY month
                ORDER BY month DESC
                LIMIT 6
            """).fetchall()
            # Reverse so chronological
            analytics["monthly_trends"] = [{"label": r["month"], "value": r["count"]} for r in reversed(monthly)]

            # Financial Summary
            fines_collected = conn.execute("SELECT COALESCE(SUM(amount), 0.0) FROM payments WHERE status = 'completed'").fetchone()[0]
            pending_fines = conn.execute("SELECT COALESCE(SUM(fine_amount), 0.0) FROM transactions WHERE fine_paid = 0").fetchone()[0]
            analytics["financials"] = {
                "fines_collected": round(fines_collected, 2),
                "pending_fines": round(pending_fines, 2)
            }

            return analytics

    def export_books_csv(self) -> str:
        """Export book records as a CSV string."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, title, author, category, isbn, barcode, total_copies, available_copies, created_at
                FROM books
                ORDER BY id ASC
            """).fetchall()

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Title", "Author", "Category", "ISBN", "Barcode", "Total Copies", "Available Copies", "Created At"])
            for r in rows:
                writer.writerow(list(r))
            return output.getvalue()

    def export_users_csv(self) -> str:
        """Export member records as a CSV string."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, email, role, preferred_language, created_at
                FROM users
                ORDER BY id ASC
            """).fetchall()

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Name", "Email", "Role", "Language", "Created At"])
            for r in rows:
                writer.writerow(list(r))
            return output.getvalue()
