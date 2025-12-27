from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Database connection
def get_db():
    conn = sqlite3.connect("expense.db")
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database with improved schema
def init_db():
    conn = get_db()
    
    # Create expenses table with timestamp and category
    conn.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        reason TEXT,
        category TEXT DEFAULT 'Other',
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create members table to track roommates
    conn.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"]
        amount = request.form["amount"]
        reason = request.form.get("reason", "")
        category = request.form.get("category", "Other")

        # Add member if not exists
        try:
            conn.execute("INSERT INTO members (name) VALUES (?)", (name,))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Member already exists

        # Add expense
        conn.execute(
            "INSERT INTO expenses (name, amount, reason, category) VALUES (?, ?, ?, ?)",
            (name, amount, reason, category)
        )
        conn.commit()

    # Get all expenses ordered by date
    expenses = conn.execute(
        "SELECT * FROM expenses ORDER BY date_added DESC"
    ).fetchall()
    
    # Get all members
    members = conn.execute("SELECT * FROM members").fetchall()
    
    # Calculate totals
    total = sum([e['amount'] for e in expenses])
    member_count = len(members) or 1
    split = total / member_count
    
    # Calculate per-person spending
    person_totals = {}
    for expense in expenses:
        person = expense['name']
        if person not in person_totals:
            person_totals[person] = 0
        person_totals[person] += expense['amount']

    conn.close()
    return render_template("index.html",
                           expenses=expenses,
                           total=total,
                           split=split,
                           members=members,
                           person_totals=person_totals)

# Delete expense route
@app.route("/delete/<int:expense_id>")
def delete_expense(expense_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    return redirect("/")

# API endpoint to get stats
@app.route("/api/stats")
def get_stats():
    conn = get_db()
    expenses = conn.execute("SELECT * FROM expenses").fetchall()
    members = conn.execute("SELECT * FROM members").fetchall()
    
    total = sum([e['amount'] for e in expenses])
    member_count = len(members) or 1
    
    stats = {
        "total_expenses": total,
        "total_count": len(expenses),
        "member_count": member_count,
        "split_amount": total / member_count
    }
    
    conn.close()
    return jsonify(stats)

if __name__ == "__main__":
    app.run(debug=True)