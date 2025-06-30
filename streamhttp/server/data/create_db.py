import sqlite3
import os

# Path to SQLite file (you can change this to your desired location)
# Path should be set in the .dotenv file or as an environment variable.
# If not set, default to a local path
if 'SQLITE_DB_PATH' not in os.environ:
    os.environ["SQLITE_DB_PATH"] ="../data/sqlite.db"

if 'SQLITE_DB_PATH' not in os.environ:
    raise ValueError("SQLITE_DB_PATH environment variable must be set")

db_path = os.environ["SQLITE_DB_PATH"]

# Remove existing DB file if rerunning
if os.path.exists(db_path):
    os.remove(db_path)

# Connect to SQLite (creates file if not exists)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create 3 tables
cursor.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);
""")

cursor.execute("""
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL
);
""")

cursor.execute("""
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id INTEGER,
    quantity INTEGER NOT NULL,
    order_date TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
""")

# Insert sample users
cursor.executemany("INSERT INTO users (name, email) VALUES (?, ?)", [
    ("Alice Johnson", "alice@example.com"),
    ("Bob Smith", "bob@example.com"),
    ("Charlie Lee", "charlie@example.com")
])

# Insert sample products
cursor.executemany("INSERT INTO products (name, price) VALUES (?, ?)", [
    ("Laptop", 999.99),
    ("Monitor", 199.99),
    ("Keyboard", 49.99)
])

# Insert sample orders
cursor.executemany("INSERT INTO orders (user_id, product_id, quantity, order_date) VALUES (?, ?, ?, ?)", [
    (1, 1, 1, "2025-06-25"),
    (2, 2, 2, "2025-06-24"),
    (3, 3, 1, "2025-06-23"),
    (1, 3, 1, "2025-06-22")
])

# Commit changes and close
conn.commit()
conn.close()

print(f"✅ SQLite database created at: {os.path.abspath(db_path)}")
