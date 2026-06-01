"""
Motor de sincronización offline/online para StockVibe.
- Lee y escribe siempre en SQLite local (rápido, funciona sin internet).
- Si hay conexión: envía cambios al servidor y descarga datos actualizados.
- Si no hay conexión: encola cambios para enviarlos después.
"""
import json
import threading
import time
from datetime import datetime

import config
import database as local

_online_cache = {"value": False, "checked_at": 0.0}
_sync_lock = threading.Lock()
_status = {
    "enabled": False,
    "online": False,
    "syncing": False,
    "pending": 0,
    "last_sync": None,
    "last_error": None,
}
_background_started = False
ONLINE_TTL = 20


def is_sync_enabled():
    return config.is_sync()


def _can_sync():
    return is_sync_enabled() and config.get_api_url() and config.get_api_key()


def check_online(force=False):
    if not _can_sync():
        _online_cache["value"] = False
        return False

    now = time.time()
    if not force and (now - _online_cache["checked_at"]) < ONLINE_TTL:
        return _online_cache["value"]

    try:
        import urllib.error
        import urllib.request

        api_url = config.get_api_url()
        api_key = config.get_api_key()
        headers = {"Accept": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        req = urllib.request.Request(f"{api_url}/health", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read().decode())
        online = bool(body.get("ok"))
    except Exception:
        online = False

    _online_cache["value"] = online
    _online_cache["checked_at"] = now
    _status["online"] = online
    return online


def get_status():
    if _can_sync():
        _status["enabled"] = True
        _status["pending"] = local.count_pending_sync_operations()
        if not _status["syncing"]:
            check_online()
    else:
        _status["enabled"] = False
        _status["online"] = False
        _status["pending"] = 0
    return dict(_status)


def _rewrite_queue_product_id(local_id, server_id):
    if local_id == server_id:
        return
    for item in local.get_pending_sync_operations():
        payload = item["payload"]
        changed = False
        if item["operation"] == "register_sale":
            for sale_item in payload.get("items", []):
                if sale_item.get("product_id") == local_id:
                    sale_item["product_id"] = server_id
                    changed = True
        elif item["operation"] == "update_product" and payload.get("prod_id") == local_id:
            payload["prod_id"] = server_id
            changed = True
        elif item["operation"] == "delete_product" and payload.get("prod_id") == local_id:
            payload["prod_id"] = server_id
            changed = True
        elif item["operation"] == "quick_add_stock" and payload.get("product_id") == local_id:
            payload["product_id"] = server_id
            changed = True
        if changed:
            conn = local.get_db_connection()
            conn.cursor().execute(
                "UPDATE sync_queue SET payload = ? WHERE id = ?",
                (json.dumps(payload, ensure_ascii=False), item["id"]),
            )
            conn.commit()
            conn.close()


def _apply_remote(operation, payload):
    import api_client

    p = {k: v for k, v in payload.items() if not k.startswith("_")}

    if operation == "add_category":
        return api_client.add_category(p["name"], p.get("description", ""))
    if operation == "update_category":
        return api_client.update_category(p["cat_id"], p["name"], p.get("description", ""))
    if operation == "delete_category":
        return api_client.delete_category(p["cat_id"])
    if operation == "add_product":
        return api_client.add_product(
            p["name"], p.get("sku"), p.get("category_id"), p.get("description", ""),
            p["purchase_price"], p["sale_price"], p["stock"], p["min_stock"],
        )
    if operation == "update_product":
        return api_client.update_product(
            p["prod_id"], p["name"], p.get("sku"), p.get("category_id"), p.get("description", ""),
            p["purchase_price"], p["sale_price"], p["stock"], p["min_stock"],
        )
    if operation == "delete_product":
        return api_client.delete_product(p["prod_id"])
    if operation == "quick_add_stock":
        return api_client.quick_add_stock(p["product_id"], p["quantity"])
    if operation == "add_customer":
        return api_client.add_customer(p["name"], p.get("phone", ""))
    if operation == "delete_customer":
        return api_client.delete_customer(p["customer_id"])
    if operation == "register_sale":
        return api_client.register_sale(
            p["items"], p.get("payment_status", "contado"),
            p.get("customer_name"), float(p.get("initial_payment", 0.0)),
        )
    if operation == "register_credit_payment":
        return api_client.register_credit_payment(p["sale_id"], p["amount"])
    if operation == "update_exchange_rate":
        return api_client.update_exchange_rate(p["rate"])
    if operation == "clear_sales_history":
        return api_client.clear_sales_history()
    raise ValueError(f"Operación de sync no soportada: {operation}")


def _handle_id_adoption(operation, payload, result):
    if not result.get("success"):
        return
    if operation == "add_product" and "_local_id" in payload:
        server_id = result.get("id")
        local_id = payload["_local_id"]
        if server_id and local_id and server_id != local_id:
            local.adopt_product_id(local_id, server_id)
            _rewrite_queue_product_id(local_id, server_id)
    if operation == "add_category" and "_local_id" in payload:
        server_id = result.get("id")
        local_id = payload["_local_id"]
        if server_id and local_id and server_id != local_id:
            local.adopt_category_id(local_id, server_id)


def push_queue():
    if not check_online(force=True):
        return {"success": False, "error": "Sin conexión al servidor."}

    pushed = 0
    for item in local.get_pending_sync_operations():
        try:
            result = _apply_remote(item["operation"], item["payload"])
            if result.get("success"):
                _handle_id_adoption(item["operation"], item["payload"], result)
                local.remove_sync_operation(item["id"])
                pushed += 1
            else:
                local.increment_sync_retry(item["id"])
                return {"success": False, "error": result.get("error", "Error al sincronizar."), "pushed": pushed}
        except Exception as e:
            local.increment_sync_retry(item["id"])
            return {"success": False, "error": str(e), "pushed": pushed}
    return {"success": True, "pushed": pushed}


def pull_from_server():
    import api_client

    categories = api_client.get_categories()
    products = api_client.get_products()
    customers = api_client.get_customers()
    sales = api_client.get_sales_history()
    rate = api_client.get_exchange_rate()

    local.replace_categories_from_server(categories)
    local.replace_products_from_server(products)
    local.replace_customers_from_server(customers)

    sales_with_details = []
    for sale in sales:
        details = api_client.get_sale_details(sale["id"])
        if details:
            sales_with_details.append(details)
    local.replace_sales_from_server(sales_with_details)
    local.set_exchange_rate_local(rate)
    return {"success": True}


def sync_all(force_pull=True):
    if not _can_sync():
        return {"success": True, "skipped": True}

    if not check_online(force=True):
        _status["online"] = False
        _status["pending"] = local.count_pending_sync_operations()
        return {"success": False, "error": "Sin conexión. Los cambios se guardaron localmente."}

    with _sync_lock:
        _status["syncing"] = True
        _status["last_error"] = None
        try:
            push_result = push_queue()
            if not push_result.get("success"):
                _status["last_error"] = push_result.get("error")
                return push_result

            if force_pull:
                pull_from_server()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            local.set_sync_meta("last_sync", now)
            _status["last_sync"] = now
            _status["pending"] = local.count_pending_sync_operations()
            _status["online"] = True
            return {"success": True, "pushed": push_result.get("pushed", 0)}
        except Exception as e:
            _status["last_error"] = str(e)
            return {"success": False, "error": str(e)}
        finally:
            _status["syncing"] = False


def after_mutation(operation, payload):
    if not _can_sync():
        return

    if check_online(force=True):
        try:
            result = _apply_remote(operation, payload)
            if result.get("success"):
                _handle_id_adoption(operation, payload, result)
                if operation in (
                    "register_sale", "register_credit_payment",
                    "clear_sales_history", "import_inventory_csv",
                ):
                    pull_from_server()
                _status["pending"] = local.count_pending_sync_operations()
                return
        except Exception:
            pass

    local.enqueue_sync_operation(operation, payload)
    _status["pending"] = local.count_pending_sync_operations()
    _status["online"] = False


def init_sync():
    if not _can_sync():
        return
    _status["enabled"] = True
    sync_all(force_pull=True)


def start_background_sync(interval=45):
    global _background_started
    if _background_started or not _can_sync():
        return
    _background_started = True

    def _loop():
        while True:
            time.sleep(interval)
            if _can_sync():
                was_offline = not _online_cache["value"]
                online = check_online(force=True)
                pending = local.count_pending_sync_operations()
                if online and (pending > 0 or was_offline):
                    sync_all(force_pull=True)

    thread = threading.Thread(target=_loop, daemon=True, name="stockvibe-sync")
    thread.start()
