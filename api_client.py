"""
Cliente HTTP para la API central de StockVibe.
Expone las mismas funciones que database.py para uso transparente en escritorio y móvil.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import config

DEFAULT_TIMEOUT = 30


class ApiError(Exception):
    pass


def _headers():
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    api_key = config.get_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _base_url():
    url = config.get_api_url()
    if not url:
        raise ApiError(
            "No hay URL de API configurada. Edita stockvibe_config.json o define STOCKVIBE_API_URL."
        )
    return url


def _request(method, path, body=None, raw_body=None, content_type=None):
    url = f"{_base_url()}{path}"
    data = None
    headers = _headers()
    if raw_body is not None:
        data = raw_body
        if content_type:
            headers["Content-Type"] = content_type
    elif body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            payload = resp.read().decode("utf-8")
            if not payload:
                return None
            return json.loads(payload)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            detail = parsed.get("detail", detail)
        except json.JSONDecodeError:
            pass
        raise ApiError(f"Error HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise ApiError(f"No se pudo conectar con el servidor: {e.reason}") from e


def init_db():
    """Verifica conexión con el servidor remoto."""
    result = _request("GET", "/health")
    if not result or not result.get("ok"):
        raise ApiError("El servidor no respondió correctamente.")
    return True


def get_exchange_rate():
    return float(_request("GET", "/settings/exchange-rate"))


def update_exchange_rate(rate):
    return _request("PUT", "/settings/exchange-rate", {"rate": rate})


def get_categories():
    return _request("GET", "/categories")


def add_category(name, description=""):
    return _request("POST", "/categories", {"name": name, "description": description})


def update_category(cat_id, name, description=""):
    return _request("PUT", f"/categories/{cat_id}", {"name": name, "description": description})


def delete_category(cat_id):
    return _request("DELETE", f"/categories/{cat_id}")


def get_products():
    return _request("GET", "/products")


def add_product(name, sku, category_id, description, purchase_price, sale_price, stock, min_stock):
    return _request("POST", "/products", {
        "name": name, "sku": sku, "category_id": category_id, "description": description,
        "purchase_price": purchase_price, "sale_price": sale_price, "stock": stock, "min_stock": min_stock,
    })


def update_product(prod_id, name, sku, category_id, description, purchase_price, sale_price, stock, min_stock):
    return _request("PUT", f"/products/{prod_id}", {
        "name": name, "sku": sku, "category_id": category_id, "description": description,
        "purchase_price": purchase_price, "sale_price": sale_price, "stock": stock, "min_stock": min_stock,
    })


def delete_product(prod_id):
    return _request("DELETE", f"/products/{prod_id}")


def quick_add_stock(product_id, quantity):
    return _request("POST", f"/products/{product_id}/quick-stock", {"quantity": quantity})


def get_customers():
    return _request("GET", "/customers")


def add_customer(name, phone=""):
    return _request("POST", "/customers", {"name": name, "phone": phone})


def delete_customer(customer_id):
    return _request("DELETE", f"/customers/{customer_id}")


def register_sale(items, payment_status="contado", customer_name=None, initial_payment=0.0):
    return _request("POST", "/sales", {
        "items": items,
        "payment_status": payment_status,
        "customer_name": customer_name,
        "initial_payment": initial_payment,
    })


def get_sales_history():
    return _request("GET", "/sales")


def get_sale_details(sale_id):
    return _request("GET", f"/sales/{sale_id}")


def get_pending_credits():
    return _request("GET", "/credits/pending")


def register_credit_payment(sale_id, amount_usd):
    return _request("POST", f"/credits/{sale_id}/payments", {"amount": amount_usd})


def get_debtor_accounts():
    return _request("GET", "/debtors")


def get_debtor_details(customer_name):
    return _request("GET", f"/debtors/{urllib.parse.quote(customer_name, safe='')}")


def get_daily_balance(date_str=None):
    path = "/balance/daily"
    if date_str:
        path += f"?date={urllib.parse.quote(date_str)}"
    return _request("GET", path)


def clear_sales_history():
    return _request("DELETE", "/sales/history")


def get_dashboard_stats():
    return _request("GET", "/dashboard/stats")


def export_inventory_csv(filepath):
    result = _request("GET", "/inventory/export-csv")
    if isinstance(result, dict) and not result.get("success", True):
        return result
    content = result.get("data", "") if isinstance(result, dict) else str(result)
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return {"success": True, "message": f"Inventario exportado con éxito a {os.path.basename(filepath)}"}


def import_inventory_csv(filepath):
    if not os.path.exists(filepath):
        return {"success": False, "error": "El archivo CSV no existe."}
    with open(filepath, "rb") as f:
        content = f.read()
    return _request("POST", "/inventory/import-csv", raw_body=content, content_type="text/csv; charset=utf-8")
