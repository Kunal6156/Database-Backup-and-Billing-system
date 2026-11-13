"""Creates the SQLite database from schema.sql with DUMMY sample data and two login accounts.

  python setup_db.py            # create (does nothing if the database already exists)
  python setup_db.py --reset    # delete and recreate (also resets passwords!)

Passwords: set GN_ADMIN_PASSWORD / GN_STAFF_PASSWORD to choose them; otherwise random ones are
generated and printed ONCE.
"""
import argparse
import os
import random
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path

import auth
import db as gndb

CATEGORIES = ["Hardware & Tools", "Electrical Fittings", "Office Supplies", "Safety Equipment", "Plumbing"]
CATEGORY_GST = [18, 18, 12, 18, 18]
SUPPLIERS = [("Delhi Tools Wholesale", "9810000001", "sales@delhitools.example"),
             ("Bright Electricals Pvt Ltd", "9810000002", "orders@brightelec.example"),
             ("Paper & Pen Distributors", "9810000003", "hello@paperpen.example"),
             ("SafeWorks Industrial", "9810000004", "support@safeworks.example")]
PRODUCTS = [  # (name, category index, price)
    ("M10 Hex Bolts (Box of 100)", 0, 450), ("Claw Hammer 500g", 0, 320), ("Adjustable Spanner 12in", 0, 380),
    ("Cordless Drill Bits Set", 0, 740), ("Measuring Tape 5m", 0, 150), ("Hacksaw with Blade", 0, 210),
    ("Copper Wire Coil (90m)", 1, 1850), ("Heavy Duty Switchboard", 1, 320), ("LED Bulb 12W (Pack of 4)", 1, 480),
    ("Extension Board 6-socket", 1, 590), ("MCB 32A Single Pole", 1, 260), ("PVC Insulation Tape (Pack of 10)", 1, 190),
    ("A4 Paper Ream 500 sheets", 2, 280), ("Ballpoint Pens (Box of 50)", 2, 240), ("Stapler with Pins", 2, 160),
    ("File Folders (Pack of 20)", 2, 340), ("Marker Set (12 colours)", 2, 220), ("Sticky Notes (Pack of 12)", 2, 130),
    ("Industrial Safety Gloves", 3, 150), ("Safety Helmet", 3, 350), ("Safety Goggles", 3, 120),
    ("Reflective Jacket", 3, 270), ("Steel Toe Boots", 3, 1450), ("Ear Plugs (Box of 50)", 3, 310),
    ("PVC Pipe 1in x 3m", 4, 240), ("Brass Tap 0.5in", 4, 360), ("Teflon Tape (Pack of 10)", 4, 90),
    ("Water Tank Float Valve", 4, 420), ("Pipe Wrench 14in", 4, 690), ("Shower Head Set", 4, 880),
]
FIRST = ["Aarav", "Vivaan", "Rohan", "Ishaan", "Karan", "Rahul", "Amit", "Neha", "Priya", "Sneha", "Pooja", "Anita",
         "Manoj", "Suresh", "Deepak", "Ritu", "Meena", "Sanjay", "Vikas", "Nitin", "Kavita", "Sunil", "Anil", "Geeta", "Mohit"]
BIZ = ["Traders", "Electricals", "Constructions", "Hardware", "Enterprises", "Suppliers", "Associates", "Stores"]
AREAS = ["Kalkaji, New Delhi", "Okhla Phase III, New Delhi", "Nehru Place, New Delhi", "Lajpat Nagar, New Delhi", "Govindpuri, New Delhi"]


def gen_password(n=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def money(x):
    return round(x + 1e-9, 2)


def create_database(db_path, reset=False, seed=True, seed_value=42, admin_password=None, staff_password=None):
    """Create the database. Returns {'admin': pw, 'staff': pw}, or None if it already existed."""
    db_path = Path(db_path)
    if db_path.exists():
        if not reset:
            return None
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    creds = {"admin": admin_password or os.environ.get("GN_ADMIN_PASSWORD") or gen_password(),
             "staff": staff_password or os.environ.get("GN_STAFF_PASSWORD") or gen_password()}
    conn = gndb.get_conn(db_path)
    conn.executescript((gndb.BASE_DIR / "schema.sql").read_text(encoding="utf-8"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, pw in creds.items():
        conn.execute("INSERT INTO users(username, password_hash, role, created_at) VALUES (?,?,?,?)",
                     (name, auth.hash_password(pw), name, now))
    if seed:
        _seed(conn, random.Random(seed_value))
    conn.commit()
    conn.close()
    return creds


def _seed(conn, rnd):
    conn.executemany("INSERT INTO categories(category_name) VALUES (?)", [(c,) for c in CATEGORIES])
    conn.executemany("INSERT INTO suppliers(name, phone, email) VALUES (?,?,?)", SUPPLIERS)
    for i, (n, c, p) in enumerate(PRODUCTS):
        supplier = None if i == len(PRODUCTS) - 1 else (c % len(SUPPLIERS)) + 1  # last product has no supplier on purpose
        conn.execute("INSERT INTO products(product_name, category_id, supplier_id, unit_price, gst_rate, stock_quantity) "
                     "VALUES (?,?,?,?,?,0)", (n, c + 1, supplier, p, CATEGORY_GST[c]))
    for i, first in enumerate(FIRST):
        gstin = f"07{''.join(rnd.choices('ABCDE', k=5))}{rnd.randint(1000, 9999)}F1Z{rnd.randint(1, 9)}" if i % 5 < 2 else None
        conn.execute("INSERT INTO customers(name, phone, gstin, address) VALUES (?,?,?,?)",
                     (f"{first} {rnd.choice(BIZ)}", f"98{rnd.randint(10000000, 99999999)}", gstin, rnd.choice(AREAS)))
    n_prod, n_cust = len(PRODUCTS), len(FIRST)
    popularity = [rnd.lognormvariate(0, 0.8) for _ in range(n_prod)]
    now = datetime.now()
    for _ in range(400):
        days_ago = int(180 * rnd.random() ** 1.4)  # more invoices recently, so demand trends upward
        when = now - timedelta(days=days_ago, hours=rnd.randint(0, 9), minutes=rnd.randint(0, 59))
        status = rnd.choices(["Paid", "Pending", "Cancelled"], weights=[70, 20, 10])[0]
        cur = conn.execute("INSERT INTO invoices(customer_id, invoice_date, payment_status) VALUES (?,?,?)",
                           (rnd.randint(1, n_cust), when.strftime("%Y-%m-%d %H:%M:%S"), status))
        inv_id, sub, gst = cur.lastrowid, 0.0, 0.0
        chosen = set()
        while len(chosen) < rnd.randint(1, 4):
            chosen.add(rnd.choices(range(1, n_prod + 1), weights=popularity)[0])
        for pid in chosen:
            qty, price = rnd.randint(1, 8), PRODUCTS[pid - 1][2]
            rate = CATEGORY_GST[PRODUCTS[pid - 1][1]]
            line, tax = money(qty * price), money(qty * price * rate / 100)
            sub, gst = sub + line, gst + tax
            conn.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, unit_price, gst_rate, line_total, gst_amount) "
                         "VALUES (?,?,?,?,?,?,?)", (inv_id, pid, qty, price, rate, line, tax))
        conn.execute("UPDATE invoices SET invoice_no=?, subtotal=?, gst_total=?, total_amount=? WHERE invoice_id=?",
                     (f"GN/{gndb.fy_label(when)}/{inv_id:05d}", money(sub), money(gst), money(sub + gst), inv_id))
    for pid in range(1, n_prod + 1):  # current stock: a random amount per product (some end up low on purpose)
        conn.execute("UPDATE products SET stock_quantity=? WHERE product_id=?", (rnd.randint(2, 120), pid))
    fy = gndb.fy_label(now)
    for sid, status in ((1, "Received"), (2, "Ordered"), (3, "Draft")):
        cur = conn.execute("INSERT INTO purchase_orders(supplier_id, created_at, status, received_at) VALUES (?,?,?,?)",
                           (sid, (now - timedelta(days=10 * sid)).strftime("%Y-%m-%d %H:%M:%S"), status,
                            now.strftime("%Y-%m-%d %H:%M:%S") if status == "Received" else None))
        po = cur.lastrowid
        conn.execute("UPDATE purchase_orders SET po_no=? WHERE po_id=?", (f"PO/{fy}/{po:04d}", po))
        for pid, p in [(i + 1, x) for i, x in enumerate(PRODUCTS) if (x[1] % len(SUPPLIERS)) + 1 == sid][:3]:
            conn.execute("INSERT INTO purchase_order_items(po_id, product_id, quantity, unit_cost) VALUES (?,?,?,?)",
                         (po, pid, rnd.randint(20, 60), money(p[2] * 0.7)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete and recreate the database (resets passwords)")
    args = ap.parse_args()
    cfg = gndb.load_config()
    if cfg["database"]["type"] != "sqlite":
        raise SystemExit("setup_db.py creates the SQLite sample database only.")
    creds = create_database(cfg["database"]["path"], reset=args.reset)
    if creds is None:
        print("Already exists (use --reset to recreate):", cfg["database"]["path"])
    else:
        print("Created", cfg["database"]["path"])
        print("\nLOGIN ACCOUNTS (shown only once - note them down):")
        for user, pw in creds.items():
            print(f"  {user:<6} / {pw}")
