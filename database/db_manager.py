import os
import sqlite3
import json
import uuid
from datetime import datetime

import sys

# Resolve project root dynamically (handles PyInstaller temp directory)
DB_DIR_SOURCE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DB_DIR_SOURCE)

def get_db_path():
    """Returns a persistent database path, outside of the PyInstaller temporary extraction folder."""
    if getattr(sys, 'frozen', False):
        # Packaged executable environment - store DB next to the executable
        exe_dir = os.path.dirname(sys.executable)
        db_folder = os.path.join(exe_dir, "database")
    else:
        # Standard script environment - store in the database/ package folder
        db_folder = DB_DIR_SOURCE
        
    os.makedirs(db_folder, exist_ok=True)
    return os.path.join(db_folder, "pdv_store.db")

DB_PATH = get_db_path()
DB_DIR = os.path.dirname(DB_PATH)

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds it if empty."""
    os.makedirs(DB_DIR, exist_ok=True)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Create Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        price REAL NOT NULL
    );
    """)
    
    # 2. Create Sales History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales_history (
        sale_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL
    );
    """)
    
    # 3. Create Sales Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales_items (
        sale_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales_history (sale_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (id),
        PRIMARY KEY (sale_id, product_id)
    );
    """)
    
    # 4. Create Category Complements Table (Expert System Layer)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS category_complements (
        product_id TEXT NOT NULL,
        complement_id TEXT NOT NULL,
        reason TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products (id),
        FOREIGN KEY (complement_id) REFERENCES products (id),
        PRIMARY KEY (product_id, complement_id)
    );
    """)
    
    conn.commit()
    
    # Seed Products
    cursor.execute("SELECT COUNT(*) as count FROM products")
    if cursor.fetchone()["count"] == 0:
        seed_products(cursor)
        
    # Seed Sales History
    cursor.execute("SELECT COUNT(*) as count FROM sales_history")
    if cursor.fetchone()["count"] == 0:
        seed_history(cursor)
        
    # Seed Complements
    cursor.execute("SELECT COUNT(*) as count FROM category_complements")
    if cursor.fetchone()["count"] == 0:
        seed_complements(cursor)
        
    conn.commit()
    conn.close()

def seed_products(cursor):
    """Seeds products from the data/products.json file."""
    products_json_path = os.path.join(PROJECT_ROOT, "data", "products.json")
    if not os.path.exists(products_json_path):
        print(f"Products seed file not found at {products_json_path}")
        return
        
    with open(products_json_path, "r", encoding="utf-8") as f:
        products = json.load(f)
        
    for p in products:
        cursor.execute(
            "INSERT INTO products (id, name, category, subcategory, price) VALUES (?, ?, ?, ?, ?)",
            (p["id"], p["name"], p["category"], p["subcategory"], p["price"])
        )
    print(f"Seeded {len(products)} products.")

def seed_history(cursor):
    """Seeds sales history from data/local_history_seed.json."""
    history_json_path = os.path.join(PROJECT_ROOT, "data", "local_history_seed.json")
    if not os.path.exists(history_json_path):
        print(f"History seed file not found at {history_json_path}")
        return
        
    with open(history_json_path, "r", encoding="utf-8") as f:
        transactions = json.load(f)
        
    for i, t in enumerate(transactions):
        sale_id = f"sale_seed_{i+1}"
        # Set historical timestamps spreading over the last few days
        timestamp = datetime.now().isoformat()
        cursor.execute("INSERT INTO sales_history (sale_id, timestamp) VALUES (?, ?)", (sale_id, timestamp))
        
        # Count product frequencies within the transaction
        item_counts = {}
        for p_id in t["items"]:
            item_counts[p_id] = item_counts.get(p_id, 0) + 1
            
        for p_id, qty in item_counts.items():
            try:
                cursor.execute(
                    "INSERT INTO sales_items (sale_id, product_id, quantity) VALUES (?, ?, ?)",
                    (sale_id, p_id, qty)
                )
            except sqlite3.IntegrityError:
                # In case product seed missing or duplicate
                pass
    print(f"Seeded {len(transactions)} transactions.")

def seed_complements(cursor):
    """Seeds expert product complements rules."""
    complements = [
        # Bacia Sanitária complements
        ("3001", "3002", "Assento sanitário costuma ser adquirido em conjunto"),
        ("3001", "3003", "Necessário anel de vedação para instalação do vaso"),
        ("3001", "3004", "Engate flexível é necessário para alimentação de água"),
        
        # Cano PVC complements
        ("1001", "1002", "Geralmente necessita de luvas de emenda"),
        ("1001", "1003", "Necessário adesivo plástico para colagem"),
        ("1001", "1004", "Recomendado fita veda rosca para conexões de rosca"),
        
        # Cuba de pia complements
        ("4001", "4002", "Necessário sifão para escoamento"),
        ("4001", "4003", "Válvula de pia é necessária para montagem da cuba"),
        ("4001", "4004", "Torneira de cozinha gourmet para complementar a pia"),
        
        # Tinta complements
        ("5001", "5002", "Rolo de lã anti-respingo é indispensável para pintura"),
        ("5001", "5004", "Fita crepe é necessária para isolamento/acabamento"),
        ("5001", "5005", "Bandeja de pintura para dosar a tinta no rolo"),
        
        # Fios/Cabos complements
        ("2001", "2003", "Fita isolante é necessária para as emendas elétricas"),
        ("2001", "2004", "Caixa de luz 4x2 para embutir tomadas/interruptores"),
        ("2001", "2002", "Disjuntor correspondente para proteção do circuito")
    ]
    
    for prod_id, comp_id, reason in complements:
        try:
            cursor.execute(
                "INSERT INTO category_complements (product_id, complement_id, reason) VALUES (?, ?, ?)",
                (prod_id, comp_id, reason)
            )
        except sqlite3.IntegrityError:
            pass
    print(f"Seeded {len(complements)} expert complement rules.")

# --- Database API Operations ---

def get_product(product_id):
    """Fetches a single product details by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_all_products():
    """Fetches all products."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY category, name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_sale(product_ids):
    """
    Saves a completed sale transaction to the SQLite database.
    product_ids: list of product IDs (can contain duplicates for quantity)
    """
    if not product_ids:
        return None
        
    sale_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO sales_history (sale_id, timestamp) VALUES (?, ?)", (sale_id, timestamp))
        
        # Calculate item quantities
        item_counts = {}
        for p_id in product_ids:
            item_counts[p_id] = item_counts.get(p_id, 0) + 1
            
        for p_id, qty in item_counts.items():
            cursor.execute(
                "INSERT INTO sales_items (sale_id, product_id, quantity) VALUES (?, ?, ?)",
                (sale_id, p_id, qty)
            )
        conn.commit()
        print(f"Sale {sale_id} saved successfully with {len(item_counts)} distinct items.")
        return sale_id
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Failed to save sale: {e}")
        return None
    finally:
        conn.close()

def get_local_sales_history():
    """
    Returns the purchase history as a list of lists of product IDs.
    Used by Layer 1 recommendation system.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sale_id, product_id, quantity
        FROM sales_items
    """)
    rows = cursor.fetchall()
    conn.close()
    
    # Group by sale_id
    transactions = {}
    for r in rows:
        sale_id = r["sale_id"]
        prod_id = r["product_id"]
        qty = r["quantity"]
        if sale_id not in transactions:
            transactions[sale_id] = []
        # Add the product ID multiplied by quantity
        transactions[sale_id].extend([prod_id] * qty)
        
    return list(transactions.values())

def get_complements_for_product(product_id):
    """
    Retrieves expert system complements for a specific product ID.
    Returns list of dicts: {'complement_id': str, 'name': str, 'category': str, 'reason': str, 'price': float}
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cc.complement_id, cc.reason, p.name, p.category, p.price
        FROM category_complements cc
        JOIN products p ON cc.complement_id = p.id
        WHERE cc.product_id = ?
    """, (product_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    init_db()
    print("Database manager tests completed successfully.")
