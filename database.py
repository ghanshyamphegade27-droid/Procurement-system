import psycopg2
import datetime
import streamlit as st
import secrets
from contextlib import contextmanager

# 1. Connect using the hidden vault we created!

@contextmanager
def get_db_connection():
    """Context manager that auto-commits on success, rolls back on error, and always closes."""
    connection = psycopg2.connect(st.secrets["SUPABASE_URL"])
    try:
        yield connection
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        connection.close()


def create_tables():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            # PostgreSQL uses 'SERIAL' instead of 'AUTOINCREMENT'
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendors (
                    id SERIAL PRIMARY KEY,
                    vendor_code TEXT UNIQUE NOT NULL,
                    vendor_name TEXT NOT NULL,
                    contact_person TEXT,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    tax_number TEXT,
                    category TEXT,
                    status TEXT DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS materials (
                    id SERIAL PRIMARY KEY,
                    material_code TEXT UNIQUE NOT NULL,
                    material_name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    unit TEXT,
                    standard_make TEXT,
                    status TEXT DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rfqs (
                    id SERIAL PRIMARY KEY,
                    rfq_number TEXT UNIQUE NOT NULL,
                    rfq_date TEXT,
                    product_details TEXT,
                    buyer TEXT,
                    department TEXT,
                    required_date TEXT,
                    category TEXT,
                    currency TEXT,
                    location TEXT,
                    status TEXT DEFAULT 'Open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotations (
                    id SERIAL PRIMARY KEY,
                    rfq_number TEXT NOT NULL,
                    vendor_code TEXT NOT NULL,
                    quotation_date TEXT,
                    payment_terms TEXT,
                    incoterms TEXT,
                    status TEXT DEFAULT 'Received',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotation_links (
                    id SERIAL PRIMARY KEY,
                    token TEXT UNIQUE NOT NULL,
                    rfq_number TEXT NOT NULL,
                    vendor_code TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_submitted_at TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotation_lines (
                    id SERIAL PRIMARY KEY,
                    rfq_number TEXT NOT NULL,
                    vendor_code TEXT NOT NULL,
                    material_code TEXT NOT NULL,
                    material_description TEXT,
                    quantity REAL,
                    basic_price REAL,
                    negotiated_price REAL,
                    delivery_days INTEGER,
                    make TEXT,
                    vendor_description TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS approvals (
                    id SERIAL PRIMARY KEY,
                    rfq_number TEXT NOT NULL,
                    vendor_code TEXT NOT NULL,
                    approver_name TEXT NOT NULL,
                    approval_status TEXT NOT NULL,
                    approval_reason TEXT,
                    deviation_reason TEXT,
                    approval_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_closures (
                    id SERIAL PRIMARY KEY,
                    rfq_number TEXT NOT NULL,
                    vendor_code TEXT NOT NULL,
                    gst_percentage REAL,
                    closure_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)


def add_vendor(vendor_code, vendor_name, contact_person, email, phone, address, tax_number, category, status):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            # Notice we use %s instead of ? for PostgreSQL
            cursor.execute("""
                INSERT INTO vendors (vendor_code, vendor_name, contact_person, email, phone, address, tax_number, category, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (vendor_code, vendor_name, contact_person, email, phone, address, tax_number, category, status))
    return True


def add_material(material_code, material_name, description, category, unit, standard_make, status):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO materials (material_code, material_name, description, category, unit, standard_make, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (material_code, material_name, description, category, unit, standard_make, status))
    return True


def add_rfq(rfq_number, rfq_date, product_details, buyer, department, required_date, category, currency, location, status):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO rfqs (rfq_number, rfq_date, product_details, buyer, department, required_date, category, currency, location, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (rfq_number, rfq_date, product_details, buyer, department, required_date, category, currency, location, status))
    return True


def add_quotation(rfq_number, vendor_code, quotation_date, payment_terms, incoterms, status):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO quotations (rfq_number, vendor_code, quotation_date, payment_terms, incoterms, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (rfq_number, vendor_code, quotation_date, payment_terms, incoterms, status))
    return True


def add_quotation_line(rfq_number, vendor_code, material_code, vendor_description, quantity, basic_price, negotiated_price, delivery_days, make):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO quotation_lines (rfq_number, vendor_code, material_code, vendor_description, quantity, basic_price, negotiated_price, delivery_days, make)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (rfq_number, vendor_code, material_code, vendor_description, quantity, basic_price, negotiated_price, delivery_days, make))
    return True


def get_comparative_data(rfq_number):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    q.vendor_code AS "Vendor Code",
                    v.vendor_name AS "Vendor Name",
                    ql.material_code AS "Material",
                    m.description AS "Our Req. Spec",
                    ql.vendor_description AS "Vendor's Quoted Spec",
                    ql.quantity AS "Qty",
                    ql.negotiated_price AS "Unit Price",
                    (ql.quantity * ql.negotiated_price) AS "Total Price",
                    ql.delivery_days AS "Delivery (Days)",
                    q.payment_terms AS "Payment Terms",
                    q.incoterms AS "Incoterms"
                FROM quotations q
                JOIN quotation_lines ql 
                    ON q.rfq_number = ql.rfq_number AND q.vendor_code = ql.vendor_code
                LEFT JOIN vendors v 
                    ON q.vendor_code = v.vendor_code
                LEFT JOIN materials m 
                    ON ql.material_code = m.material_code
                WHERE q.rfq_number = %s
            """, (rfq_number,))

            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def add_approval(rfq_number, vendor_code, approver_name, approval_status, approval_reason, deviation_reason):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO approvals (rfq_number, vendor_code, approver_name, approval_status, approval_reason, deviation_reason)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (rfq_number, vendor_code, approver_name, approval_status, approval_reason, deviation_reason))
    return True


def get_dashboard_metrics():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM rfqs")
            total_rfqs = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM quotations")
            total_quotations = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM approvals")
            total_approvals = cursor.fetchone()[0]
            return total_rfqs, total_quotations, total_approvals


def get_recent_approvals():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.rfq_number AS "RFQ Number", 
                    a.vendor_code AS "Vendor Code", 
                    v.vendor_name AS "Vendor Name", 
                    a.approval_status AS "Status", 
                    a.approval_date AS "Date"
                FROM approvals a
                LEFT JOIN vendors v ON a.vendor_code = v.vendor_code
                ORDER BY a.approval_date DESC LIMIT 5
            """)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_latest_material_price(search_term):
    search_pattern = f"%{search_term}%"
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            # We use ILIKE instead of LIKE so PostgreSQL ignores uppercase/lowercase letters when searching
            cursor.execute("""
                SELECT m.material_name, ql.material_code, ql.negotiated_price, q.vendor_code,v.vendor_name,ql.quantity, q.quotation_date
                FROM quotation_lines ql
                JOIN quotations q ON ql.rfq_number = q.rfq_number AND ql.vendor_code = q.vendor_code
                JOIN materials m ON ql.material_code = m.material_code
                LEFT JOIN vendors v ON q.vendor_code = v.vendor_code
                WHERE m.material_name ILIKE %s OR ql.material_code ILIKE %s
                ORDER BY q.quotation_date DESC LIMIT 1
            """, (search_pattern, search_pattern))
            result = cursor.fetchone()

    if result:
        return {
            "Material Name": result[0],
            "Material Code": result[1],
            "Latest Price": result[2],
            "Vendor Code": result[3],
            "Vendor Name": result[4],
            "Quantity": result[5],
            "Date": result[6]
        }
    return None


def generate_material_code(category):
    cat_prefix = "R" if category == "Raw Material" else "P" if category == "Packaging" else "I"
    current_year = datetime.datetime.now().year
    base_prefix = f"M{cat_prefix}{current_year}"

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT material_code FROM materials WHERE material_code LIKE %s ORDER BY id DESC LIMIT 1", (f"{base_prefix}%",))
            result = cursor.fetchone()

    next_number = int(result[0].replace(base_prefix, "")) + 1 if result else 1
    return f"{base_prefix}{next_number:02d}"


def generate_vendor_code(category):
    cat_prefix = "R" if category == "Raw Material" else "P" if category == "Packaging" else "S"
    current_year = datetime.datetime.now().year
    base_prefix = f"V{cat_prefix}{current_year}"

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendor_code FROM vendors WHERE vendor_code LIKE %s ORDER BY id DESC LIMIT 1", (f"{base_prefix}%",))
            result = cursor.fetchone()

    next_number = int(result[0].replace(base_prefix, "")) + 1 if result else 1
    return f"{base_prefix}{next_number:02d}"


def generate_rfq_number():
    current_year = datetime.datetime.now().year
    base_prefix = f"RFQ-{current_year}-"

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rfq_number FROM rfqs WHERE rfq_number LIKE %s ORDER BY id DESC LIMIT 1", (f"{base_prefix}%",))
            result = cursor.fetchone()

    next_number = int(result[0].split("-")[-1]) + 1 if result else 1
    return f"{base_prefix}{next_number:03d}"


def close_order(rfq_number, vendor_code, gst_percentage):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO order_closures (rfq_number, vendor_code, gst_percentage) VALUES (%s, %s, %s)",
                           (rfq_number, vendor_code, gst_percentage))
            cursor.execute(
                "UPDATE rfqs SET status = 'Closed - Delivered' WHERE rfq_number = %s", (rfq_number,))
    return True


def get_closed_orders_report():
    with get_db_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT 
                oc.rfq_number AS "Order No",
                v.vendor_name AS "Vendor",
                m.material_name AS "Material",
                ql.quantity AS "Quantity",
                m.unit AS "Unit",
                ql.basic_price AS "Unit Basic Price",
                ql.negotiated_price AS "Unit Negotiated Price",
                CASE 
                    WHEN ql.basic_price > 0 
                    THEN ROUND((((ql.basic_price - ql.negotiated_price) / ql.basic_price) * 100)::numeric, 2) 
                    ELSE 0 
                END AS "Discount (%)",
                ROUND((ql.quantity * ql.negotiated_price)::numeric, 2) AS "Total Negotiated Value (Excl. Tax)",
                oc.gst_percentage AS "GST (%)",
                ROUND(((ql.quantity * ql.negotiated_price) * (1 + oc.gst_percentage / 100.0))::numeric, 2) AS "Total Landed Price (Incl. Tax)"
            FROM order_closures oc
            JOIN quotation_lines ql 
              ON oc.rfq_number = ql.rfq_number AND oc.vendor_code = ql.vendor_code
            LEFT JOIN vendors v 
              ON oc.vendor_code = v.vendor_code
            LEFT JOIN materials m 
              ON ql.material_code = m.material_code
            ORDER BY oc.closure_date DESC
        """)

        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return results


def get_all_vendors():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT vendor_code AS "Vendor Code", vendor_name AS "Vendor Name", category AS "Category", contact_person AS "Contact Person", phone AS "Phone", status AS "Status" FROM vendors ORDER BY id DESC')
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_all_materials():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT material_code AS "Material Code", material_name AS "Material Name", category AS "Category", unit AS "Unit", standard_make AS "Make", status AS "Status" FROM materials ORDER BY id DESC')
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_all_rfqs():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT rfq_number FROM rfqs ORDER BY id DESC')
            return [row[0] for row in cursor.fetchall()]


def check_vendor_exists(vendor_name):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendor_code FROM vendors WHERE vendor_name ILIKE %s", (vendor_name,))
            result = cursor.fetchone()
    return result[0] if result else None


def check_material_exists(material_name):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT material_code FROM materials WHERE material_name ILIKE %s", (material_name,))
            result = cursor.fetchone()
    return result[0] if result else None


def get_approved_vendor_for_rfq(rfq_number):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendor_code FROM approvals WHERE rfq_number = %s AND approval_status = 'Approved' ORDER BY approval_date DESC LIMIT 1", (rfq_number,))
            result = cursor.fetchone()
    return result[0] if result else None


def is_order_closed(rfq_number):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM order_closures WHERE rfq_number = %s", (rfq_number,))
            result = cursor.fetchone()
    return True if result else False

def create_vendor_link(rfq_number, vendor_code, expires_in_days=14):
    """Generates a single unguessable link for one vendor to quote on one RFQ."""
    token = secrets.token_urlsafe(32)  # 256 bits of entropy — not brute-forceable
    expires_at = datetime.datetime.now() + datetime.timedelta(days=expires_in_days)
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO quotation_links (token, rfq_number, vendor_code, expires_at)
                VALUES (%s, %s, %s, %s)
            """, (token, rfq_number, vendor_code, expires_at))
    return token


def validate_vendor_link(token):
    """Returns scoped context for a token, or None if invalid/expired/RFQ no longer open."""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ql.rfq_number, ql.vendor_code, ql.expires_at,
                       r.status, r.product_details, v.vendor_name
                FROM quotation_links ql
                JOIN rfqs r ON ql.rfq_number = r.rfq_number
                JOIN vendors v ON ql.vendor_code = v.vendor_code
                WHERE ql.token = %s
            """, (token,))
            result = cursor.fetchone()

    if not result:
        return None
    rfq_number, vendor_code, expires_at, rfq_status, product_details, vendor_name = result

    if expires_at and expires_at < datetime.datetime.now():
        return None
    if rfq_status != "Open":  # locks the link automatically once you close/approve the RFQ
        return None

    return {
        "rfq_number": rfq_number,
        "vendor_code": vendor_code,
        "vendor_name": vendor_name,
        "product_details": product_details,
    }


def mark_link_submitted(token):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE quotation_links SET last_submitted_at = CURRENT_TIMESTAMP WHERE token = %s",
                (token,)
            )