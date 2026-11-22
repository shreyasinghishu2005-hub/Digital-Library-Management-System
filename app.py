"""
Digital Library Management System - Python Backend
A complete, elegant Flask REST API & Web Application
"""

import os
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, Response, make_response
from database import Database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "library-digital-system-secret-key-2026")
app.config["JSON_SORT_KEYS"] = False

# Initialize database
db = Database()


# ------------------ CORS & MIDDLEWARE ------------------

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Session-Token, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


# ------------------ AUTH HELPERS ------------------

def get_current_user():
    """Extract and validate user from X-Session-Token header or cookie."""
    token = request.headers.get("X-Session-Token") or request.cookies.get("session_token")
    if not token and request.headers.get("Authorization"):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if not token:
        return None
    return db.get_session_user(token)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return make_response("", 204)
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "message": "Authentication required. Invalid or expired session."}), 401
        return f(user, *args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return make_response("", 204)
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "message": "Authentication required."}), 401
        if user.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin privileges required for this action."}), 403
        return f(user, *args, **kwargs)
    return decorated


# ------------------ FRONTEND ROUTE ------------------

@app.route("/")
def index():
    """Serve the elegant white Digital Library interface."""
    # If client asks for JSON (e.g. API clients pinging root), return API status
    if request.headers.get("Accept") == "application/json" and not request.headers.get("Sec-Fetch-Dest") == "document":
        return jsonify({
            "success": True,
            "message": "Digital Library Management System API is running.",
            "version": "2.0.0 (Python Edition)"
        })
    return render_template("index.html")


@app.route("/api/ping", methods=["GET"])
def api_ping():
    return jsonify({
        "success": True,
        "message": "Library Management System API is active.",
        "version": "2.0.0",
        "timestamp": db.get_connection().execute("SELECT datetime('now')").fetchone()[0]
    })


# ------------------ AUTH ENDPOINTS ------------------

@app.route("/register", methods=["POST", "OPTIONS"])
def register():
    if request.method == "OPTIONS":
        return make_response("", 204)

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", "student")
    preferred_language = data.get("preferred_language", "en")

    success, message, user = db.create_user(name, email, password, role, preferred_language)
    if not success:
        return jsonify({"success": False, "message": message}), 400

    token = db.create_session(user["id"])
    resp = make_response(jsonify({
        "success": True,
        "message": "Registration successful.",
        "token": token,
        "user": user
    }), 201)
    resp.set_cookie("session_token", token, httponly=True, samesite="Lax")
    return resp


@app.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return make_response("", 204)

    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    success, message, user = db.authenticate_user(email, password)
    if not success:
        return jsonify({"success": False, "message": message}), 401

    token = db.create_session(user["id"])
    resp = make_response(jsonify({
        "success": True,
        "message": "Login successful.",
        "token": token,
        "user": user
    }))
    resp.set_cookie("session_token", token, httponly=True, samesite="Lax")
    return resp


@app.route("/session", methods=["GET", "OPTIONS"])
@require_auth
def get_session(current_user):
    return jsonify({
        "success": True,
        "user": current_user
    })


@app.route("/logout", methods=["POST", "OPTIONS"])
def logout():
    if request.method == "OPTIONS":
        return make_response("", 204)

    token = request.headers.get("X-Session-Token") or request.cookies.get("session_token")
    if token:
        db.delete_session(token)

    resp = make_response(jsonify({
        "success": True,
        "message": "Logged out successfully."
    }))
    resp.set_cookie("session_token", "", expires=0)
    return resp


# ------------------ BOOKS CATALOG ------------------

@app.route("/books", methods=["GET", "OPTIONS"])
def get_books():
    if request.method == "OPTIONS":
        return make_response("", 204)

    search = request.args.get("search", "")
    category = request.args.get("category", "")
    available_only = request.args.get("available_only", "").lower() in ("true", "1")

    books = db.get_books(search=search, category=category, available_only=available_only)
    return jsonify({
        "success": True,
        "count": len(books),
        "books": books
    })


@app.route("/books/<int:book_id>", methods=["GET", "PUT", "DELETE", "OPTIONS"])
def handle_book(book_id):
    if request.method == "OPTIONS":
        return make_response("", 204)

    if request.method == "GET":
        book = db.get_book_by_id(book_id)
        if not book:
            return jsonify({"success": False, "message": "Book not found."}), 404
        return jsonify({"success": True, "book": book})

    # PUT and DELETE require admin
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Authentication required."}), 401
    if user.get("role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    if request.method == "PUT":
        data = request.get_json(silent=True) or {}
        success, message, updated_book = db.update_book(book_id, data)
        if not success:
            return jsonify({"success": False, "message": message}), 400
        return jsonify({
            "success": True,
            "message": message,
            "book": updated_book
        })

    if request.method == "DELETE":
        success, message = db.delete_book(book_id)
        if not success:
            return jsonify({"success": False, "message": message}), 400
        return jsonify({
            "success": True,
            "message": message
        })


@app.route("/add-book", methods=["POST", "OPTIONS"])
@require_admin
def add_book(current_user):
    data = request.get_json(silent=True) or {}
    success, message, book = db.add_book(data)
    if not success:
        return jsonify({"success": False, "message": message}), 400
    return jsonify({
        "success": True,
        "message": message,
        "book": book
    }), 201


@app.route("/search-suggestions", methods=["GET", "OPTIONS"])
def search_suggestions():
    if request.method == "OPTIONS":
        return make_response("", 204)

    query = request.args.get("q", "")
    suggestions = db.get_search_suggestions(query)
    return jsonify({
        "success": True,
        "suggestions": suggestions
    })


# ------------------ CIRCULATION (ISSUE & RETURN) ------------------

@app.route("/issue-book", methods=["POST", "OPTIONS"])
@require_auth
def issue_book(current_user):
    data = request.get_json(silent=True) or {}
    book_id = data.get("book_id")
    if not book_id:
        return jsonify({"success": False, "message": "Book ID is required."}), 400

    try:
        book_id = int(book_id)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid Book ID."}), 400

    user_id = current_user["id"]
    # Admin can issue on behalf of any user
    if current_user["role"] == "admin" and "user_id" in data:
        try:
            user_id = int(data["user_id"])
        except ValueError:
            return jsonify({"success": False, "message": "Invalid User ID."}), 400

    days = int(data.get("days", 14))
    success, message, transaction = db.issue_book(user_id, book_id, days)
    if not success:
        return jsonify({"success": False, "message": message}), 400

    return jsonify({
        "success": True,
        "message": message,
        "transaction": transaction
    })


@app.route("/return-book", methods=["POST", "OPTIONS"])
@require_auth
def return_book(current_user):
    data = request.get_json(silent=True) or {}
    tx_id = data.get("transaction_id")
    if not tx_id:
        return jsonify({"success": False, "message": "Transaction ID is required."}), 400

    try:
        tx_id = int(tx_id)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid Transaction ID."}), 400

    # If student, verify that the student owns this transaction
    if current_user["role"] != "admin":
        user_txs = db.get_transactions(user_id=current_user["id"])
        owns = any(t["id"] == tx_id for t in user_txs)
        if not owns:
            return jsonify({"success": False, "message": "You can only return books that were issued to your account."}), 403

    success, message, return_info = db.return_book(tx_id)
    if not success:
        return jsonify({"success": False, "message": message}), 400

    return jsonify({
        "success": True,
        "message": message,
        "return_info": return_info
    })


@app.route("/transactions", methods=["GET", "OPTIONS"])
@require_auth
def get_transactions(current_user):
    if current_user["role"] == "admin":
        user_filter = request.args.get("user_id")
        user_id = int(user_filter) if user_filter else None
        transactions = db.get_transactions(user_id=user_id)
    else:
        transactions = db.get_transactions(user_id=current_user["id"])

    return jsonify({
        "success": True,
        "count": len(transactions),
        "transactions": transactions
    })


# ------------------ FINES & PAYMENTS ------------------

@app.route("/pay-fine", methods=["POST", "OPTIONS"])
@require_auth
def pay_fine(current_user):
    data = request.get_json(silent=True) or {}
    tx_id = data.get("transaction_id")
    if not tx_id:
        return jsonify({"success": False, "message": "Transaction ID is required."}), 400

    try:
        tx_id = int(tx_id)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid Transaction ID."}), 400

    user_id = current_user["id"]
    if current_user["role"] == "admin":
        if "user_id" in data and data["user_id"]:
            try:
                user_id = int(data["user_id"])
            except ValueError:
                pass
        else:
            user_id = None

    payment_method = data.get("payment_method", "UPI")
    success, message, payment_info = db.pay_fine(tx_id, user_id, payment_method)
    if not success:
        return jsonify({"success": False, "message": message}), 400

    return jsonify({
        "success": True,
        "message": message,
        "payment": payment_info
    })


# ------------------ DASHBOARD, NOTIFICATIONS & RECOMMENDATIONS ------------------

@app.route("/dashboard", methods=["GET", "OPTIONS"])
@require_auth
def dashboard(current_user):
    stats = db.get_dashboard_stats(current_user["id"], current_user["role"])
    return jsonify({
        "success": True,
        "dashboard": stats,
        "user": current_user
    })


@app.route("/notifications", methods=["GET", "OPTIONS"])
@require_auth
def notifications(current_user):
    alerts = db.get_notifications(current_user["id"])
    return jsonify({
        "success": True,
        "notifications": alerts
    })


@app.route("/recommendations", methods=["GET", "OPTIONS"])
@require_auth
def recommendations(current_user):
    books = db.get_recommendations(current_user["id"])
    return jsonify({
        "success": True,
        "recommendations": books
    })


# ------------------ ADMIN ANALYTICS & EXPORTS ------------------

@app.route("/analytics", methods=["GET", "OPTIONS"])
@require_admin
def analytics(current_user):
    data = db.get_analytics()
    return jsonify({
        "success": True,
        "analytics": data
    })


@app.route("/export/books.csv", methods=["GET", "OPTIONS"])
@require_admin
def export_books_csv(current_user):
    csv_content = db.export_books_csv()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=books_inventory.csv"}
    )


@app.route("/export/users.csv", methods=["GET", "OPTIONS"])
@require_admin
def export_users_csv(current_user):
    csv_content = db.export_users_csv()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=library_members.csv"}
    )


@app.route("/users", methods=["GET", "OPTIONS"])
@require_admin
def get_users(current_user):
    users = db.get_all_users()
    return jsonify({
        "success": True,
        "users": users
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n=======================================================")
    print(f"  Digital Library Management System - Python Backend")
    print(f"  Web UI & REST API available at: http://localhost:{port}")
    print(f"  Demo Accounts:")
    print(f"    - Admin:   admin@lms.com   / admin123")
    print(f"    - Student: student@lms.com / student123")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
