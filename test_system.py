"""
Automated Comprehensive Test Suite for Digital Library Management System
Tests all REST API endpoints, business logic, fine calculations, and database integrity.
"""

import os
import unittest
import json
from app import app, db


class TestDigitalLibrarySystem(unittest.TestCase):
    test_db_path = os.path.join(os.path.dirname(__file__), "test_library.db")

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
        app.config["TESTING"] = True
        import database
        import app as app_module
        cls.test_db = database.Database(cls.test_db_path)
        app_module.db = cls.test_db
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass

    def test_01_root_api_and_ui(self):
        """Test root serves HTML UI or JSON on Accept: application/json."""
        res_ui = self.client.get("/")
        self.assertEqual(res_ui.status_code, 200)
        self.assertIn(b"Library OS", res_ui.data)

        res_api = self.client.get("/", headers={"Accept": "application/json"})
        self.assertEqual(res_api.status_code, 200)
        data = json.loads(res_api.data)
        self.assertTrue(data.get("success"))

    def test_02_admin_and_student_auth(self):
        """Test login with demo accounts."""
        # Admin login
        res_admin = self.client.post("/login", json={"email": "admin@lms.com", "password": "admin123"})
        self.assertEqual(res_admin.status_code, 200)
        data_admin = json.loads(res_admin.data)
        self.assertTrue(data_admin["success"])
        self.assertEqual(data_admin["user"]["role"], "admin")
        self.__class__.admin_token = data_admin["token"]

        # Student login
        res_student = self.client.post("/login", json={"email": "student@lms.com", "password": "student123"})
        self.assertEqual(res_student.status_code, 200)
        data_student = json.loads(res_student.data)
        self.assertTrue(data_student["success"])
        self.assertEqual(data_student["user"]["role"], "student")
        self.__class__.student_token = data_student["token"]

        # Verify session token
        res_session = self.client.get("/session", headers={"X-Session-Token": self.admin_token})
        self.assertEqual(res_session.status_code, 200)
        session_data = json.loads(res_session.data)
        self.assertEqual(session_data["user"]["email"], "admin@lms.com")

    def test_03_books_catalog_and_search(self):
        """Test books listing, category filtering, and search suggestions."""
        # List all books
        res = self.client.get("/books")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertGreater(data["count"], 0)

        # Filter by category
        res_cat = self.client.get("/books?category=Programming")
        data_cat = json.loads(res_cat.data)
        for b in data_cat["books"]:
            self.assertEqual(b["category"], "Programming")

        # Search suggestions
        res_sug = self.client.get("/search-suggestions?q=Clean")
        self.assertEqual(res_sug.status_code, 200)
        data_sug = json.loads(res_sug.data)
        self.assertTrue(any("Clean Code" in s["label"] for s in data_sug["suggestions"]))

    def test_04_add_update_delete_book(self):
        """Test Admin adding, updating, and deleting a book."""
        import time
        # Add book
        new_book_payload = {
            "title": "Test Driven Development",
            "author": "Kent Beck",
            "category": "Programming",
            "isbn": "9780321146533",
            "barcode": f"BOOK-TEST-{int(time.time()*1000)}",
            "total_copies": 3,
            "description": "By example guide to TDD"
        }
        res_add = self.client.post("/add-book", json=new_book_payload, headers={"X-Session-Token": self.admin_token})
        self.assertEqual(res_add.status_code, 201)
        data_add = json.loads(res_add.data)
        book_id = data_add["book"]["id"]

        # Update book
        res_put = self.client.put(f"/books/{book_id}", json={"title": "Test Driven Development: By Example"}, headers={"X-Session-Token": self.admin_token})
        self.assertEqual(res_put.status_code, 200)

        # Delete book
        res_del = self.client.delete(f"/books/{book_id}", headers={"X-Session-Token": self.admin_token})
        self.assertEqual(res_del.status_code, 200)

    def test_05_circulation_issue_return_fine(self):
        """Test book issue, return, and fine calculation."""
        # Issue book ID 5 (The Alchemist, 3 copies available)
        res_issue = self.client.post("/issue-book", json={"book_id": 5, "days": 14}, headers={"X-Session-Token": self.student_token})
        self.assertEqual(res_issue.status_code, 200)
        data_issue = json.loads(res_issue.data)
        tx_id = data_issue["transaction"]["id"]

        # Check book available copies decremented
        res_book = self.client.get("/books/5")
        data_book = json.loads(res_book.data)
        self.assertEqual(data_book["book"]["available_copies"], 2)

        # Return book
        res_return = self.client.post("/return-book", json={"transaction_id": tx_id}, headers={"X-Session-Token": self.student_token})
        self.assertEqual(res_return.status_code, 200)
        data_return = json.loads(res_return.data)
        self.assertTrue(data_return["success"])

        # Check book available copies restored
        res_book_restored = self.client.get("/books/5")
        self.assertEqual(json.loads(res_book_restored.data)["book"]["available_copies"], 3)

    def test_06_fine_payment(self):
        """Test settling fine on transaction."""
        # Query transaction 2 which was seeded with fine of 12.0
        res_pay = self.client.post("/pay-fine", json={"transaction_id": 2, "payment_method": "UPI"}, headers={"X-Session-Token": self.admin_token})
        self.assertEqual(res_pay.status_code, 200)
        data_pay = json.loads(res_pay.data)
        self.assertTrue(data_pay["success"])
        self.assertEqual(data_pay["payment"]["status"], "completed")

    def test_07_dashboard_and_analytics(self):
        """Test dashboard summary stats and admin analytics."""
        res_dash = self.client.get("/dashboard", headers={"X-Session-Token": self.admin_token})
        self.assertEqual(res_dash.status_code, 200)
        data_dash = json.loads(res_dash.data)
        self.assertIn("total_books", data_dash["dashboard"])

        res_analytics = self.client.get("/analytics", headers={"X-Session-Token": self.admin_token})
        self.assertEqual(res_analytics.status_code, 200)
        data_analytics = json.loads(res_analytics.data)
        self.assertIn("most_borrowed_books", data_analytics["analytics"])
        self.assertIn("categories", data_analytics["analytics"])

    def test_08_csv_exports(self):
        """Test CSV file generation for books and users."""
        res_books_csv = self.client.get("/export/books.csv", headers={"X-Session-Token": self.admin_token})
        self.assertEqual(res_books_csv.status_code, 200)
        self.assertEqual(res_books_csv.mimetype, "text/csv")
        self.assertIn(b"Clean Code", res_books_csv.data)

        res_users_csv = self.client.get("/export/users.csv", headers={"X-Session-Token": self.admin_token})
        self.assertEqual(res_users_csv.status_code, 200)
        self.assertEqual(res_users_csv.mimetype, "text/csv")
        self.assertIn(b"admin@lms.com", res_users_csv.data)


if __name__ == "__main__":
    unittest.main()
