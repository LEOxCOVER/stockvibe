import os
import csv
import sys
from datetime import datetime

import db_backend

sqlite3 = db_backend  # compatibilidad con referencias sqlite3.IntegrityError
IntegrityError = db_backend.IntegrityError
OperationalError = db_backend.OperationalError

DATABASE_NAME = db_backend.SQLITE_PATH


def _data_dir():
    try:
        from kivy.utils import platform as kivy_platform
        if kivy_platform == "android":
            from android.storage import app_storage_path
            path = app_storage_path()
            os.makedirs(path, exist_ok=True)
            return path
    except Exception:
        pass
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


if not db_backend.IS_POSTGRES:
    db_backend.SQLITE_PATH = os.path.join(_data_dir(), "inventory.db")
    DATABASE_NAME = db_backend.SQLITE_PATH


def get_db_connection():
    return db_backend.get_db_connection()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    if db_backend.IS_POSTGRES:
        for ddl in db_backend.get_postgres_ddl():
            cursor.execute(ddl)
        conn.commit()
    else:
        # Crear tabla de categorías
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
        """)

        # Crear tabla de productos (Precios almacenados en DÓLARES USD como base estable)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE,
            category_id INTEGER,
            description TEXT,
            purchase_price REAL NOT NULL,
            sale_price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            min_stock INTEGER NOT NULL DEFAULT 5,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
        """)

        # Crear tabla de configuración global (tasa de cambio, etc.)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)

        # Crear tabla de ventas
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_amount REAL NOT NULL,
            total_cost REAL NOT NULL,
            total_profit REAL NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'contado',
            customer_name TEXT,
            amount_paid REAL NOT NULL DEFAULT 0.0
        )
        """)

        # Crear tabla de detalles de venta
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            purchase_price REAL NOT NULL,
            sale_price REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        )
        """)

        # --- FASE 3: Tabla de Clientes Recurrentes ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            phone TEXT DEFAULT ''
        )
        """)

        # --- FASE 3: Historial de Abonos (para el Balance Diario) ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE
        )
        """)

        # --- MIGRACIÓN ACTIVA DE BASE DE DATOS ---
        try:
            cursor.execute("ALTER TABLE sales ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'contado'")
        except OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE sales ADD COLUMN customer_name TEXT")
        except OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE sales ADD COLUMN amount_paid REAL NOT NULL DEFAULT 0.0")
        except OperationalError:
            pass
        
    # Inicializar la tasa de cambio por defecto si no existe (45.0 Bs por Dólar)
    cursor.execute("SELECT COUNT(*) FROM settings WHERE key = 'exchange_rate'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO settings (key, value) VALUES ('exchange_rate', '45.0')")
        conn.commit()
    
    # Insertar categorías por defecto si está vacía
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ("General", "Categoría para productos en general"),
            ("Electrónica", "Dispositivos electrónicos, cargadores y accesorios"),
            ("Alimentos y Bebidas", "Productos de consumo diario"),
            ("Hogar", "Artículos para el hogar y limpieza"),
            ("Otros", "Artículos que no entran en otras categorías")
        ]
        cursor.executemany("INSERT INTO categories (name, description) VALUES (?, ?)", default_categories)
        conn.commit()
        
    # Insertar algunos productos semilla si la tabla de productos está vacía para dar una gran primera impresión
    # Los precios base se guardan en DÓLARES (USD)
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        default_products = [
            ("Mouse Inalámbrico RGB", "M-RGB-01", 2, "Mouse óptico de 2.4Ghz recargable", 8.50, 15.00, 25, 5),
            ("Teclado Mecánico Pro", "K-PRO-02", 2, "Teclado mecánico con switches red, español", 35.00, 65.00, 8, 3),
            ("Café Premium Blend", "C-PREM-03", 3, "Café orgánico tostado molido 500g", 4.20, 8.50, 45, 10),
            ("Soporte para Laptop", "S-LAP-04", 4, "Soporte ergonómico de aluminio ajustable", 12.00, 24.99, 4, 5), # Alerta de stock bajo
            ("Cable HDMI 2.1 2m", "C-HDMI-05", 2, "Cable HDMI de ultra alta velocidad 8K", 3.50, 7.50, 60, 15),
            ("Auriculares Inalámbricos", "A-WIRE-06", 2, "Auriculares bluetooth con cancelación de ruido", 22.00, 45.00, 15, 5),
            ("Organizador de Escritorio", "O-DESK-07", 4, "Organizador de madera de bambú con 3 compartimentos", 9.00, 19.99, 12, 4)
        ]
        cursor.executemany("""
            INSERT INTO products (name, sku, category_id, description, purchase_price, sale_price, stock, min_stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, default_products)
        
        # Generar algunas ventas de prueba recientes para que los gráficos tengan vida útil
        # Venta 1 (Hace 3 días) - Venta normal de contado ($38.50)
        t1 = datetime.now().replace(day=max(1, datetime.now().day - 3)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO sales (timestamp, total_amount, total_cost, total_profit, payment_status, amount_paid) VALUES (?, ?, ?, ?, 'contado', ?)", 
                       (t1, 38.50, 21.20, 17.30, 38.50))
        s1_id = cursor.lastrowid
        cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, purchase_price, sale_price) VALUES (?, ?, ?, ?, ?)",
                       (s1_id, 1, 2, 8.50, 15.00))
        cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, purchase_price, sale_price) VALUES (?, ?, ?, ?, ?)",
                       (s1_id, 3, 1, 4.20, 8.50))
                       
        # Venta 2 (Hace 1 día) - Venta a crédito de prueba ($87.50, ha abonado $40.00)
        t2 = datetime.now().replace(day=max(1, datetime.now().day - 1)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO sales (timestamp, total_amount, total_cost, total_profit, payment_status, customer_name, amount_paid) VALUES (?, ?, ?, ?, 'credito', ?, ?)", 
                       (t2, 87.50, 45.50, 42.00, "Carlos Mendoza", 40.00))
        s2_id = cursor.lastrowid
        cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, purchase_price, sale_price) VALUES (?, ?, ?, ?, ?)",
                       (s2_id, 2, 1, 35.00, 65.00))
        cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, purchase_price, sale_price) VALUES (?, ?, ?, ?, ?)",
                       (s2_id, 5, 3, 3.50, 7.50))

        # Registrar cliente recurrente de prueba
        try:
            cursor.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", ("Carlos Mendoza", "0414-1234567"))
        except IntegrityError:
            pass
                       
        # Venta 3 (Hoy) - Venta normal de contado ($69.99)
        t3 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO sales (timestamp, total_amount, total_cost, total_profit, payment_status, amount_paid) VALUES (?, ?, ?, ?, 'contado', ?)", 
                       (t3, 69.99, 34.00, 35.99, 69.99))
        s3_id = cursor.lastrowid
        cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, purchase_price, sale_price) VALUES (?, ?, ?, ?, ?)",
                       (s3_id, 4, 1, 12.00, 24.99))
        cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, purchase_price, sale_price) VALUES (?, ?, ?, ?, ?)",
                       (s3_id, 6, 1, 22.00, 45.00))
                       
        conn.commit()

    init_sync_tables(conn)
    conn.close()

# ----------------- TASA DE CAMBIO -----------------

def get_exchange_rate():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'exchange_rate'")
    row = cursor.fetchone()
    conn.close()
    if row:
        return float(row["value"])
    return 45.0 # Tasa de cambio de respaldo

def update_exchange_rate(rate):
    try:
        val = float(rate)
        if val <= 0:
            return {"success": False, "error": "La tasa de cambio debe ser mayor a 0."}
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('exchange_rate', ?)", (str(val),))
        conn.commit()
        conn.close()
        return {"success": True, "exchange_rate": val}
    except ValueError:
        return {"success": False, "error": "Formato de tasa de cambio inválido."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ----------------- CRUD CATEGORÍAS -----------------

def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM categories ORDER BY name ASC")
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return categories

def add_category(name, description=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (name, description))
        conn.commit()
        category_id = cursor.lastrowid
        return {"success": True, "id": category_id}
    except IntegrityError:
        return {"success": False, "error": "El nombre de la categoría ya existe."}
    finally:
        conn.close()

def update_category(cat_id, name, description=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE categories SET name = ?, description = ? WHERE id = ?", (name, description, cat_id))
        conn.commit()
        return {"success": True}
    except IntegrityError:
        return {"success": False, "error": "El nombre de la categoría ya existe."}
    finally:
        conn.close()

def delete_category(cat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

# ----------------- CRUD PRODUCTOS -----------------

def get_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.name, p.sku, p.category_id, c.name as category_name, 
               p.description, p.purchase_price, p.sale_price, p.stock, p.min_stock 
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.name ASC
    """)
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return products

def add_product(name, sku, category_id, description, purchase_price, sale_price, stock, min_stock):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO products (name, sku, category_id, description, purchase_price, sale_price, stock, min_stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, sku if sku else None, category_id, description, purchase_price, sale_price, stock, min_stock))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    except IntegrityError as e:
        if "UNIQUE constraint failed: products.sku" in str(e) or ("sku" in str(e).lower() and "unique" in str(e).lower()):
            return {"success": False, "error": "El código SKU ya está registrado en otro producto."}
        return {"success": False, "error": f"Error de integridad: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def update_product(prod_id, name, sku, category_id, description, purchase_price, sale_price, stock, min_stock):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE products 
            SET name = ?, sku = ?, category_id = ?, description = ?, 
                purchase_price = ?, sale_price = ?, stock = ?, min_stock = ?
            WHERE id = ?
        """, (name, sku if sku else None, category_id, description, purchase_price, sale_price, stock, min_stock, prod_id))
        conn.commit()
        return {"success": True}
    except IntegrityError as e:
        if "UNIQUE constraint failed: products.sku" in str(e) or ("sku" in str(e).lower() and "unique" in str(e).lower()):
            return {"success": False, "error": "El código SKU ya está registrado en otro producto."}
        return {"success": False, "error": f"Error de integridad: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def delete_product(prod_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

# ----------------- FASE 3: CARGA RÁPIDA DE STOCK -----------------

def quick_add_stock(product_id, quantity):
    """Añade unidades al stock de un producto existente sin editar toda la ficha."""
    try:
        qty = int(quantity)
        if qty <= 0:
            return {"success": False, "error": "La cantidad a agregar debe ser mayor a 0."}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, stock FROM products WHERE id = ?", (product_id,))
        prod = cursor.fetchone()
        if not prod:
            conn.close()
            return {"success": False, "error": "El producto no existe."}
        
        new_stock = prod["stock"] + qty
        cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
        conn.commit()
        conn.close()
        
        return {"success": True, "product_name": prod["name"], "new_stock": new_stock, "added": qty}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ----------------- FASE 3: CLIENTES RECURRENTES -----------------

def get_customers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone FROM customers ORDER BY name ASC")
    customers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return customers

def add_customer(name, phone=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", (name.strip(), phone.strip()))
        conn.commit()
        cid = cursor.lastrowid
        conn.close()
        return {"success": True, "id": cid, "name": name.strip()}
    except IntegrityError:
        conn.close()
        return {"success": False, "error": "Ya existe un cliente con ese nombre."}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}

def delete_customer(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}

# ----------------- PUNTO DE VENTA & TRANSACCIONES -----------------

def register_sale(items, payment_status='contado', customer_name=None, initial_payment=0.0):
    """
    Registra una nueva venta.
    items: lista de diccionarios, ej. [{"product_id": 1, "quantity": 2}, ...]
    payment_status: 'contado' o 'credito'
    customer_name: nombre del deudor si es credito
    initial_payment: abono inicial en USD
    """
    if not items:
        return {"success": False, "error": "El carrito está vacío."}
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Iniciamos una transacción
        cursor.execute("BEGIN TRANSACTION")
        
        total_amount = 0.0
        total_cost = 0.0
        sale_items_to_insert = []
        
        # Validar stock y recopilar datos
        for item in items:
            prod_id = item["product_id"]
            qty = int(item["quantity"])
            
            if qty <= 0:
                raise Exception("La cantidad debe ser mayor a 0.")
                
            cursor.execute("SELECT name, purchase_price, sale_price, stock FROM products WHERE id = ?", (prod_id,))
            prod = cursor.fetchone()
            
            if not prod:
                raise Exception(f"El producto con ID {prod_id} no existe.")
                
            available_stock = prod["stock"]
            if available_stock < qty:
                raise Exception(f"Stock insuficiente para '{prod['name']}'. Disponible: {available_stock}, solicitado: {qty}")
                
            item_cost = prod["purchase_price"] * qty
            item_revenue = prod["sale_price"] * qty
            
            total_amount += item_revenue
            total_cost += item_cost
            
            sale_items_to_insert.append({
                "product_id": prod_id,
                "quantity": qty,
                "purchase_price": prod["purchase_price"],
                "sale_price": prod["sale_price"]
            })
            
            # Descontar stock
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, prod_id))
            
        total_profit = total_amount - total_cost
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calcular abono real
        init_pay = float(initial_payment)
        if payment_status == 'contado':
            amount_paid = total_amount
        else:
            amount_paid = min(init_pay, total_amount) # Evitar abonar de más
            
        # Si el abono es igual o mayor al total en un crédito, pasa automáticamente a ser contado
        final_payment_status = payment_status
        if final_payment_status == 'credito' and amount_paid >= total_amount:
            final_payment_status = 'contado'
            
        # Insertar cabecera de la venta
        cursor.execute("""
            INSERT INTO sales (timestamp, total_amount, total_cost, total_profit, payment_status, customer_name, amount_paid) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, total_amount, total_cost, total_profit, final_payment_status, customer_name if customer_name else None, amount_paid))
        sale_id = cursor.lastrowid
        
        # Insertar detalles de la venta
        for item in sale_items_to_insert:
            cursor.execute("""
                INSERT INTO sale_items (sale_id, product_id, quantity, purchase_price, sale_price)
                VALUES (?, ?, ?, ?, ?)
            """, (sale_id, item["product_id"], item["quantity"], item["purchase_price"], item["sale_price"]))

        # Si hubo abono inicial en crédito, registrarlo en credit_payments para el balance diario
        if final_payment_status == 'credito' and amount_paid > 0:
            cursor.execute("""
                INSERT INTO credit_payments (sale_id, timestamp, amount)
                VALUES (?, ?, ?)
            """, (sale_id, timestamp, amount_paid))
            
        # Confirmar todo
        conn.commit()
        return {"success": True, "sale_id": sale_id, "total": total_amount, "payment_status": final_payment_status}
        
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def get_sales_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, total_amount, total_cost, total_profit, payment_status, customer_name, amount_paid 
        FROM sales 
        ORDER BY timestamp DESC
    """)
    sales = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sales

def get_sale_details(sale_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Cabecera
    cursor.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
    sale = cursor.fetchone()
    if not sale:
        conn.close()
        return None
        
    # Detalles con nombres de productos
    cursor.execute("""
        SELECT si.id, si.product_id, p.name as product_name, p.sku as product_sku, 
               si.quantity, si.purchase_price, si.sale_price, 
               (si.quantity * si.sale_price) as subtotal
        FROM sale_items si
        LEFT JOIN products p ON si.product_id = p.id
        WHERE si.sale_id = ?
    """, (sale_id,))
    items = [dict(row) for row in cursor.fetchall()]
    
    result = dict(sale)
    result["items"] = items
    conn.close()
    return result

# ----------------- CUENTAS POR COBRAR (CRÉDITOS) -----------------

def get_pending_credits():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, total_amount, total_cost, total_profit, customer_name, amount_paid 
        FROM sales 
        WHERE payment_status = 'credito' AND amount_paid < total_amount
        ORDER BY timestamp DESC
    """)
    credits = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return credits

def register_credit_payment(sale_id, amount_usd):
    try:
        pay_val = float(amount_usd)
        if pay_val <= 0:
            return {"success": False, "error": "El abono debe ser un monto mayor a cero."}
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Obtener estado actual del crédito
        cursor.execute("SELECT total_amount, amount_paid, payment_status FROM sales WHERE id = ?", (sale_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": "La venta especificada no existe."}
            
        total = row["total_amount"]
        already_paid = row["amount_paid"]
        remaining = total - already_paid
        
        # Limitar abono al saldo restante
        actual_payment = min(pay_val, remaining)
        new_paid_total = already_paid + actual_payment
        
        # Si se completó el pago, cambiar estado a 'contado'
        new_status = 'credito'
        if new_paid_total >= total:
            new_status = 'contado'
            
        cursor.execute("""
            UPDATE sales 
            SET amount_paid = ?, payment_status = ? 
            WHERE id = ?
        """, (new_paid_total, new_status, sale_id))

        # FASE 3: Registrar el abono en credit_payments para el Balance Diario
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO credit_payments (sale_id, timestamp, amount)
            VALUES (?, ?, ?)
        """, (sale_id, timestamp, actual_payment))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True, 
            "sale_id": sale_id,
            "abono_registrado": actual_payment, 
            "nuevo_total_abonado": new_paid_total,
            "deuda_restante": max(0.0, total - new_paid_total),
            "liquidado": new_status == 'contado'
        }
    except ValueError:
        return {"success": False, "error": "Monto de abono inválido."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ----------------- FASE 3: CUENTAS CORRIENTES POR DEUDOR -----------------

def get_debtor_accounts():
    """
    Retorna una lista agrupada por deudor con su deuda total acumulada.
    Solo incluye deudores con saldo pendiente > 0.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT customer_name,
               COUNT(id) as num_invoices,
               SUM(total_amount) as total_credit,
               SUM(amount_paid) as total_paid,
               SUM(total_amount - amount_paid) as total_remaining,
               MIN(timestamp) as first_purchase,
               MAX(timestamp) as last_purchase
        FROM sales
        WHERE payment_status = 'credito' AND amount_paid < total_amount AND customer_name IS NOT NULL
        GROUP BY customer_name
        ORDER BY total_remaining DESC
    """)
    accounts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return accounts

def get_debtor_details(customer_name):
    """
    Retorna el desglose detallado de un deudor: todas sus facturas pendientes
    con los artículos específicos comprados en cada una.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener todas las ventas a crédito de este cliente (pendientes y liquidadas)
    cursor.execute("""
        SELECT id, timestamp, total_amount, amount_paid, payment_status,
               (total_amount - amount_paid) as remaining
        FROM sales
        WHERE customer_name = ?
        ORDER BY timestamp DESC
    """, (customer_name,))
    invoices = []
    for row in cursor.fetchall():
        invoice = dict(row)
        # Obtener los artículos de esta venta
        cursor.execute("""
            SELECT si.quantity, si.sale_price, si.purchase_price,
                   (si.quantity * si.sale_price) as subtotal,
                   p.name as product_name, p.sku as product_sku
            FROM sale_items si
            LEFT JOIN products p ON si.product_id = p.id
            WHERE si.sale_id = ?
        """, (invoice["id"],))
        invoice["items"] = [dict(item) for item in cursor.fetchall()]
        invoices.append(invoice)
    
    # Totales consolidados
    total_debt = sum(inv["total_amount"] for inv in invoices)
    total_paid = sum(inv["amount_paid"] for inv in invoices)
    total_remaining = sum(max(0, inv["total_amount"] - inv["amount_paid"]) for inv in invoices if inv["payment_status"] == "credito")
    
    conn.close()
    return {
        "customer_name": customer_name,
        "invoices": invoices,
        "total_debt": total_debt,
        "total_paid": total_paid,
        "total_remaining": total_remaining
    }

# ----------------- FASE 3: BALANCE DIARIO -----------------

def get_daily_balance(date_str=None):
    """
    Calcula el balance financiero del día especificado (o de hoy si no se indica).
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Ventas al contado de hoy (dinero que entró directamente)
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) as cash_revenue,
               COALESCE(SUM(total_cost), 0) as cash_cost,
               COALESCE(SUM(total_profit), 0) as cash_profit,
               COUNT(id) as cash_count
        FROM sales
        WHERE payment_status = 'contado' AND timestamp LIKE ?
          AND customer_name IS NULL
    """, (date_str + "%",))
    cash = dict(cursor.fetchone())
    
    # Incluir también créditos que se pagaron completamente (ahora son 'contado' pero tenían customer_name)
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) as paid_credit_revenue
        FROM sales
        WHERE payment_status = 'contado' AND timestamp LIKE ?
          AND customer_name IS NOT NULL
    """, (date_str + "%",))
    paid_credits_today = dict(cursor.fetchone())
    
    # 2. Abonos cobrados hoy (de credit_payments)
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as payments_received,
               COUNT(id) as payments_count
        FROM credit_payments
        WHERE timestamp LIKE ?
    """, (date_str + "%",))
    abonos = dict(cursor.fetchone())
    
    # 3. Ventas a crédito emitidas hoy (mercancía que salió fiada)
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) as credit_issued,
               COALESCE(SUM(total_cost), 0) as credit_cost,
               COALESCE(SUM(amount_paid), 0) as credit_initial_payments,
               COUNT(id) as credit_count
        FROM sales
        WHERE payment_status = 'credito' AND timestamp LIKE ?
    """, (date_str + "%",))
    credit = dict(cursor.fetchone())
    
    # 4. Todas las ventas del día para calcular el costo total de mercancía vendida
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) as total_revenue,
               COALESCE(SUM(total_cost), 0) as total_cost,
               COALESCE(SUM(total_profit), 0) as total_profit,
               COUNT(id) as total_count
        FROM sales
        WHERE timestamp LIKE ?
    """, (date_str + "%",))
    all_sales = dict(cursor.fetchone())
    
    conn.close()
    
    # Calcular resumen de caja
    cash_in_contado = cash["cash_revenue"] + paid_credits_today["paid_credit_revenue"]
    cash_in_abonos = abonos["payments_received"]
    total_cash = cash_in_contado + cash_in_abonos
    
    # Resumen de facturación
    total_invoiced = all_sales["total_revenue"]
    
    return {
        "date": date_str,
        # Caja (dinero recibido hoy)
        "cash_contado": round(cash_in_contado, 2),
        "cash_abonos": round(cash_in_abonos, 2),
        "total_cash": round(total_cash, 2),
        "cash_sale_count": cash["cash_count"],
        "abonos_count": abonos["payments_count"],
        # Facturación (ventas emitidas)
        "credit_issued": round(credit["credit_issued"], 2),
        "credit_count": credit["credit_count"],
        "total_invoiced": round(total_invoiced, 2),
        "total_sale_count": all_sales["total_count"],
        # Rentabilidad
        "total_cost": round(all_sales["total_cost"], 2),
        "total_profit": round(all_sales["total_profit"], 2),
    }

# ----------------- FASE 3: LIMPIEZA DE HISTORIAL -----------------

def clear_sales_history():
    """
    Elimina todos los registros de ventas, detalles y abonos.
    Los productos e inventario físico se conservan intactos.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credit_payments")
        cursor.execute("DELETE FROM sale_items")
        cursor.execute("DELETE FROM sales")
        conn.commit()
        conn.close()
        return {"success": True, "message": "Historial de ventas, abonos y créditos eliminados con éxito. El inventario se ha conservado intacto."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ----------------- MÉTRICAS DEL DASHBOARD -----------------

def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener tasa de cambio actual
    cursor.execute("SELECT value FROM settings WHERE key = 'exchange_rate'")
    exchange_rate = float(cursor.fetchone()["value"])
    
    # 1. Total Productos
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]
    
    # 2. Total Categorías
    cursor.execute("SELECT COUNT(*) FROM categories")
    total_categories = cursor.fetchone()[0]
    
    # 3. Alertas Stock Bajo
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= min_stock")
    low_stock_alerts = cursor.fetchone()[0]
    
    # 4. Valor total inventario (costo) y (venta) - en USD
    cursor.execute("SELECT SUM(purchase_price * stock), SUM(sale_price * stock) FROM products")
    inventory_costs = cursor.fetchone()
    total_inventory_cost = inventory_costs[0] if inventory_costs[0] else 0.0
    total_inventory_value = inventory_costs[1] if inventory_costs[1] else 0.0
    projected_profit = total_inventory_value - total_inventory_cost
    
    # 5. Ventas acumuladas de hoy - en USD
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(total_amount), SUM(total_profit) FROM sales WHERE timestamp LIKE ?", (today_str + "%",))
    today_sales = cursor.fetchone()
    today_revenue = today_sales[0] if today_sales[0] else 0.0
    today_profit = today_sales[1] if today_sales[1] else 0.0
    
    # 6. Cuentas por Cobrar Pendientes Totales (Monto adeudado en créditos) - en USD
    cursor.execute("SELECT SUM(total_amount - amount_paid) FROM sales WHERE payment_status = 'credito'")
    pending_credits_total = cursor.fetchone()[0]
    pending_credits_total = pending_credits_total if pending_credits_total else 0.0
    
    # 7. Historial de ventas para gráfico de los últimos 7 días - en USD
    cursor.execute("""
        SELECT date(timestamp) as sale_date, SUM(total_amount) as daily_revenue, SUM(total_profit) as daily_profit
        FROM sales
        GROUP BY sale_date
        ORDER BY sale_date DESC
        LIMIT 7
    """)
    recent_sales = [dict(row) for row in cursor.fetchall()]
    recent_sales.reverse()
    
    # 8. Distribución por Categorías
    cursor.execute("""
        SELECT c.name as category_name, COUNT(p.id) as product_count, SUM(p.stock) as total_stock
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        GROUP BY c.id
        ORDER BY product_count DESC
    """)
    category_distribution = [dict(row) for row in cursor.fetchall()]

    conn.close()
    
    return {
        "exchange_rate": exchange_rate,
        "total_products": total_products,
        "total_categories": total_categories,
        "low_stock_alerts": low_stock_alerts,
        "total_inventory_cost": round(total_inventory_cost, 2),
        "total_inventory_value": round(total_inventory_value, 2),
        "projected_profit": round(projected_profit, 2),
        "today_revenue": round(today_revenue, 2),
        "today_profit": round(today_profit, 2),
        "pending_credits_total": round(pending_credits_total, 2),
        "recent_sales": recent_sales,
        "category_distribution": category_distribution
    }

# ----------------- IMPORTACIÓN / EXPORTACIÓN CSV -----------------

def export_inventory_csv(filepath):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name, p.sku, c.name as category_name, p.description, 
                   p.purchase_price, p.sale_price, p.stock, p.min_stock
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.name ASC
        """)
        products = cursor.fetchall()
        
        with open(filepath, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            # Cabecera
            writer.writerow(["Nombre", "SKU-Codigo", "Categoria", "Descripcion", "Precio Compra (USD)", "Precio Venta (USD)", "Stock Actual", "Stock Minimo Alerta"])
            
            for row in products:
                writer.writerow([
                    row["name"], 
                    row["sku"] if row["sku"] else "", 
                    row["category_name"] if row["category_name"] else "", 
                    row["description"] if row["description"] else "", 
                    row["purchase_price"], 
                    row["sale_price"], 
                    row["stock"], 
                    row["min_stock"]
                ])
                
        conn.close()
        return {"success": True, "message": f"Inventario exportado con éxito a {os.path.basename(filepath)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def import_inventory_csv(filepath):
    try:
        if not os.path.exists(filepath):
            return {"success": False, "error": "El archivo CSV no existe."}
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        skipped_count = 0
        
        # Mapear categorías existentes para buscar por nombre
        cursor.execute("SELECT id, name FROM categories")
        categories_map = {row["name"].lower(): row["id"] for row in cursor.fetchall()}
        
        with open(filepath, mode="r", newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            header = next(reader, None)  # Omitir cabecera
            
            for row in reader:
                if len(row) < 7:
                    skipped_count += 1
                    continue
                    
                # Extraer campos
                name = row[0].strip()
                sku = row[1].strip() if row[1].strip() else None
                category_name = row[2].strip()
                description = row[3].strip()
                
                try:
                    purchase_price = float(row[4])
                    sale_price = float(row[5])
                    stock = int(row[6])
                    min_stock = int(row[7]) if len(row) > 7 and row[7].strip() else 5
                except ValueError:
                    skipped_count += 1
                    continue # Omitir filas con valores numéricos inválidos
                
                if not name:
                    skipped_count += 1
                    continue
                
                # Resolver categoría (crear si no existe)
                category_id = None
                if category_name:
                    cat_key = category_name.lower()
                    if cat_key in categories_map:
                        category_id = categories_map[cat_key]
                    else:
                        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
                        category_id = cursor.lastrowid
                        categories_map[cat_key] = category_id
                
                # Insertar o actualizar producto
                try:
                    if sku:
                        # Comprobar si existe por SKU
                        cursor.execute("SELECT id FROM products WHERE sku = ?", (sku,))
                        existing = cursor.fetchone()
                        if existing:
                            cursor.execute("""
                                UPDATE products 
                                SET name = ?, category_id = ?, description = ?, purchase_price = ?, sale_price = ?, stock = stock + ?, min_stock = ?
                                WHERE id = ?
                            """, (name, category_id, description, purchase_price, sale_price, stock, min_stock, existing["id"]))
                        else:
                            cursor.execute("""
                                INSERT INTO products (name, sku, category_id, description, purchase_price, sale_price, stock, min_stock)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (name, sku, category_id, description, purchase_price, sale_price, stock, min_stock))
                    else:
                        cursor.execute("""
                            INSERT INTO products (name, sku, category_id, description, purchase_price, sale_price, stock, min_stock)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (name, None, category_id, description, purchase_price, sale_price, stock, min_stock))
                    
                    imported_count += 1
                except IntegrityError:
                    skipped_count += 1
                    
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Importación completada. {imported_count} productos procesados con éxito. {skipped_count} filas omitidas."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ----------------- SINCRONIZACIÓN OFFLINE -----------------

def init_sync_tables(conn=None):
    """Tablas para cola de sincronización (solo clientes SQLite)."""
    if db_backend.IS_POSTGRES:
        return
    close = False
    if conn is None:
        conn = get_db_connection()
        close = True
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            retries INTEGER NOT NULL DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    if close:
        conn.close()


def enqueue_sync_operation(operation, payload_dict):
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO sync_queue (operation, payload, created_at) VALUES (?, ?, ?)",
        (operation, json.dumps(payload_dict, ensure_ascii=False), timestamp),
    )
    op_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return op_id


def get_pending_sync_operations():
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, operation, payload, retries FROM sync_queue ORDER BY id ASC")
    rows = []
    for row in cursor.fetchall():
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        rows.append(item)
    conn.close()
    return rows


def remove_sync_operation(op_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sync_queue WHERE id = ?", (op_id,))
    conn.commit()
    conn.close()


def increment_sync_retry(op_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sync_queue SET retries = retries + 1 WHERE id = ?", (op_id,))
    conn.commit()
    conn.close()


def count_pending_sync_operations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sync_queue")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def set_sync_meta(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


def get_sync_meta(key, default=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM sync_meta WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default


def adopt_product_id(local_id, server_id):
    if local_id == server_id:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DELETE FROM products WHERE id = ? AND id != ?", (server_id, local_id))
    cursor.execute("UPDATE products SET id = ? WHERE id = ?", (server_id, local_id))
    cursor.execute("UPDATE sale_items SET product_id = ? WHERE product_id = ?", (server_id, local_id))
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def adopt_category_id(local_id, server_id):
    if local_id == server_id:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DELETE FROM categories WHERE id = ? AND id != ?", (server_id, local_id))
    cursor.execute("UPDATE categories SET id = ? WHERE id = ?", (server_id, local_id))
    cursor.execute("UPDATE products SET category_id = ? WHERE category_id = ?", (server_id, local_id))
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def replace_categories_from_server(categories):
    conn = get_db_connection()
    cursor = conn.cursor()
    for cat in categories:
        cursor.execute(
            "INSERT OR REPLACE INTO categories (id, name, description) VALUES (?, ?, ?)",
            (cat["id"], cat["name"], cat.get("description") or ""),
        )
    conn.commit()
    conn.close()


def replace_products_from_server(products):
    conn = get_db_connection()
    cursor = conn.cursor()
    for prod in products:
        cursor.execute("""
            INSERT OR REPLACE INTO products
            (id, name, sku, category_id, description, purchase_price, sale_price, stock, min_stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prod["id"], prod["name"], prod.get("sku"), prod.get("category_id"),
            prod.get("description") or "", prod["purchase_price"], prod["sale_price"],
            prod["stock"], prod["min_stock"],
        ))
    conn.commit()
    conn.close()


def replace_customers_from_server(customers):
    conn = get_db_connection()
    cursor = conn.cursor()
    for cust in customers:
        cursor.execute(
            "INSERT OR REPLACE INTO customers (id, name, phone) VALUES (?, ?, ?)",
            (cust["id"], cust["name"], cust.get("phone") or ""),
        )
    conn.commit()
    conn.close()


def replace_sales_from_server(sales_with_details):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM credit_payments")
    cursor.execute("DELETE FROM sale_items")
    cursor.execute("DELETE FROM sales")
    for sale in sales_with_details:
        cursor.execute("""
            INSERT INTO sales
            (id, timestamp, total_amount, total_cost, total_profit, payment_status, customer_name, amount_paid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sale["id"], sale["timestamp"], sale["total_amount"], sale["total_cost"],
            sale["total_profit"], sale["payment_status"], sale.get("customer_name"),
            sale.get("amount_paid", 0.0),
        ))
        for item in sale.get("items", []):
            cursor.execute("""
                INSERT INTO sale_items (sale_id, product_id, quantity, purchase_price, sale_price)
                VALUES (?, ?, ?, ?, ?)
            """, (
                sale["id"], item.get("product_id"), item["quantity"],
                item["purchase_price"], item["sale_price"],
            ))
        for payment in sale.get("credit_payments", []):
            cursor.execute("""
                INSERT INTO credit_payments (sale_id, timestamp, amount)
                VALUES (?, ?, ?)
            """, (payment["sale_id"], payment["timestamp"], payment["amount"]))
    conn.commit()
    conn.close()


def set_exchange_rate_local(rate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('exchange_rate', ?)", (str(rate),))
    conn.commit()
    conn.close()

# init_db() se invoca explícitamente desde main.py, main_android.py o el servidor API.
