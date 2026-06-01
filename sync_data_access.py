"""
Capa de datos en modo sync: SQLite local + sincronización automática con la nube.
"""
import database as local
import sync_engine as sync

READ_OPS = {
    "get_exchange_rate", "get_categories", "get_products", "get_customers",
    "get_sales_history", "get_sale_details", "get_pending_credits",
    "get_debtor_accounts", "get_debtor_details", "get_daily_balance",
    "get_dashboard_stats",
}


def init_db():
    local.init_db()
    sync.init_sync()


def get_exchange_rate():
    return local.get_exchange_rate()


def update_exchange_rate(rate):
    result = local.update_exchange_rate(rate)
    if result.get("success"):
        sync.after_mutation("update_exchange_rate", {"rate": rate})
    return result


def get_categories():
    return local.get_categories()


def add_category(name, description=""):
    result = local.add_category(name, description)
    if result.get("success"):
        sync.after_mutation("add_category", {
            "name": name, "description": description, "_local_id": result.get("id"),
        })
    return result


def update_category(cat_id, name, description=""):
    result = local.update_category(cat_id, name, description)
    if result.get("success"):
        sync.after_mutation("update_category", {
            "cat_id": cat_id, "name": name, "description": description,
        })
    return result


def delete_category(cat_id):
    result = local.delete_category(cat_id)
    if result.get("success"):
        sync.after_mutation("delete_category", {"cat_id": cat_id})
    return result


def get_products():
    return local.get_products()


def add_product(name, sku, category_id, description, purchase_price, sale_price, stock, min_stock):
    result = local.add_product(
        name, sku, category_id, description, purchase_price, sale_price, stock, min_stock,
    )
    if result.get("success"):
        sync.after_mutation("add_product", {
            "name": name, "sku": sku, "category_id": category_id, "description": description,
            "purchase_price": purchase_price, "sale_price": sale_price,
            "stock": stock, "min_stock": min_stock, "_local_id": result.get("id"),
        })
    return result


def update_product(prod_id, name, sku, category_id, description, purchase_price, sale_price, stock, min_stock):
    result = local.update_product(
        prod_id, name, sku, category_id, description, purchase_price, sale_price, stock, min_stock,
    )
    if result.get("success"):
        sync.after_mutation("update_product", {
            "prod_id": prod_id, "name": name, "sku": sku, "category_id": category_id,
            "description": description, "purchase_price": purchase_price, "sale_price": sale_price,
            "stock": stock, "min_stock": min_stock,
        })
    return result


def delete_product(prod_id):
    result = local.delete_product(prod_id)
    if result.get("success"):
        sync.after_mutation("delete_product", {"prod_id": prod_id})
    return result


def quick_add_stock(product_id, quantity):
    result = local.quick_add_stock(product_id, quantity)
    if result.get("success"):
        sync.after_mutation("quick_add_stock", {"product_id": product_id, "quantity": quantity})
    return result


def get_customers():
    return local.get_customers()


def add_customer(name, phone=""):
    result = local.add_customer(name, phone)
    if result.get("success"):
        sync.after_mutation("add_customer", {"name": name, "phone": phone})
    return result


def delete_customer(customer_id):
    result = local.delete_customer(customer_id)
    if result.get("success"):
        sync.after_mutation("delete_customer", {"customer_id": customer_id})
    return result


def register_sale(items, payment_status="contado", customer_name=None, initial_payment=0.0):
    result = local.register_sale(items, payment_status, customer_name, initial_payment)
    if result.get("success"):
        sync.after_mutation("register_sale", {
            "items": items, "payment_status": payment_status,
            "customer_name": customer_name, "initial_payment": initial_payment,
        })
    return result


def get_sales_history():
    return local.get_sales_history()


def get_sale_details(sale_id):
    return local.get_sale_details(sale_id)


def get_pending_credits():
    return local.get_pending_credits()


def register_credit_payment(sale_id, amount_usd):
    result = local.register_credit_payment(sale_id, amount_usd)
    if result.get("success"):
        sync.after_mutation("register_credit_payment", {"sale_id": sale_id, "amount": amount_usd})
    return result


def get_debtor_accounts():
    return local.get_debtor_accounts()


def get_debtor_details(customer_name):
    return local.get_debtor_details(customer_name)


def get_daily_balance(date_str=None):
    return local.get_daily_balance(date_str)


def clear_sales_history():
    result = local.clear_sales_history()
    if result.get("success"):
        sync.after_mutation("clear_sales_history", {})
    return result


def get_dashboard_stats():
    return local.get_dashboard_stats()


def export_inventory_csv(filepath):
    return local.export_inventory_csv(filepath)


def import_inventory_csv(filepath):
    result = local.import_inventory_csv(filepath)
    if result.get("success"):
        try:
            if sync.check_online(force=True):
                sync.sync_all(force_pull=True)
        except Exception:
            pass
    return result
