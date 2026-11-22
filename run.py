"""
Main entry point launcher for the Digital Library Management System.
Run with: python run.py
"""

import sys
import webbrowser
from threading import Timer
from app import app

def open_browser():
    webbrowser.open_new("http://localhost:8080")

if __name__ == "__main__":
    print("\n" + "=" * 62)
    print("  📚 Digital Library Management System (Python Edition)")
    print("  ✨ Elegant White Minimalist UI & UX")
    print("  🌐 Server running at: http://localhost:8080")
    print("=" * 62)
    print("  Demo Credentials:")
    print("    • Admin:   admin@lms.com   / admin123")
    print("    • Student: student@lms.com / student123")
    print("    • Student: neha@lms.com    / reader123")
    print("=" * 62 + "\n")

    # Optionally launch browser after 1 second
    if "--no-browser" not in sys.argv:
        Timer(1.2, open_browser).start()

    app.run(host="0.0.0.0", port=8080, debug=False)
