import webview
import data_access as database
import config
import os
import sys

def get_resource_path(relative_path):
    """ Obtiene la ruta absoluta de un recurso, compatible con desarrollo y PyInstaller """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

class Api:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    # --- Métodos de Categorías ---
    def get_categories(self):
        try:
            return database.get_categories()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_category(self, name, description=""):
        try:
            return database.add_category(name, description)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_category(self, cat_id, name, description=""):
        try:
            return database.update_category(cat_id, name, description)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_category(self, cat_id):
        try:
            return database.delete_category(cat_id)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Métodos de Productos ---
    def get_products(self):
        try:
            return database.get_products()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_product(self, data):
        try:
            return database.add_product(
                name=data["name"],
                sku=data.get("sku"),
                category_id=data.get("category_id"),
                description=data.get("description", ""),
                purchase_price=float(data["purchase_price"]),
                sale_price=float(data["sale_price"]),
                stock=int(data["stock"]),
                min_stock=int(data["min_stock"])
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_product(self, prod_id, data):
        try:
            return database.update_product(
                prod_id=prod_id,
                name=data["name"],
                sku=data.get("sku"),
                category_id=data.get("category_id"),
                description=data.get("description", ""),
                purchase_price=float(data["purchase_price"]),
                sale_price=float(data["sale_price"]),
                stock=int(data["stock"]),
                min_stock=int(data["min_stock"])
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_product(self, prod_id):
        try:
            return database.delete_product(prod_id)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- FASE 3: Stock Rápido ---
    def quick_add_stock(self, product_id, quantity):
        try:
            return database.quick_add_stock(product_id, quantity)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- FASE 3: Clientes Recurrentes ---
    def get_customers(self):
        try:
            return database.get_customers()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_customer(self, name, phone=""):
        try:
            return database.add_customer(name, phone)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_customer(self, customer_id):
        try:
            return database.delete_customer(customer_id)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Métodos de Ventas ---
    def register_sale(self, data):
        try:
            return database.register_sale(
                items=data["items"],
                payment_status=data.get("payment_status", "contado"),
                customer_name=data.get("customer_name"),
                initial_payment=float(data.get("initial_payment", 0.0))
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_sales_history(self):
        try:
            return database.get_sales_history()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_sale_details(self, sale_id):
        try:
            details = database.get_sale_details(sale_id)
            if details:
                return {"success": True, "data": details}
            return {"success": False, "error": "Venta no encontrada."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Cuentas por Cobrar (Créditos) & Ajustes ---
    def get_exchange_rate(self):
        try:
            return database.get_exchange_rate()
        except Exception as e:
            return 45.0 # Tasa por defecto

    def update_exchange_rate(self, rate):
        try:
            return database.update_exchange_rate(rate)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_pending_credits(self):
        try:
            return database.get_pending_credits()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_credit_payment(self, sale_id, amount):
        try:
            return database.register_credit_payment(sale_id, amount)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- FASE 3: Cuentas Corrientes (Deudores Agrupados) ---
    def get_debtor_accounts(self):
        try:
            return database.get_debtor_accounts()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_debtor_details(self, customer_name):
        try:
            details = database.get_debtor_details(customer_name)
            return {"success": True, "data": details}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- FASE 3: Balance Diario ---
    def get_daily_balance(self, date_str=None):
        try:
            return database.get_daily_balance(date_str)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- FASE 3: Limpieza de Base de Datos ---
    def clear_sales_history(self):
        try:
            return database.clear_sales_history()
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Estadísticas de Panel de Control ---
    def get_dashboard_stats(self):
        try:
            return {"success": True, "data": database.get_dashboard_stats()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Diálogos e Importación/Exportación de Archivos ---
    def export_inventory(self):
        if not self.window:
            return {"success": False, "error": "Ventana no inicializada."}
            
        try:
            # Abrir diálogo nativo para guardar archivo
            file_types = ('Archivos CSV (*.csv)', '*.csv')
            result = self.window.create_file_dialog(
                webview.SAVE_DIALOG, 
                file_types=file_types, 
                save_filename='inventario_stockvibe.csv'
            )
            
            if not result:
                return {"success": False, "error": "Operación cancelada por el usuario."}
                
            filepath = result
            if isinstance(result, list) or isinstance(result, tuple):
                filepath = result[0]
                
            return database.export_inventory_csv(filepath)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def import_inventory(self):
        if not self.window:
            return {"success": False, "error": "Ventana no inicializada."}
            
        try:
            # Abrir diálogo nativo para seleccionar archivo
            file_types = ('Archivos CSV (*.csv)', '*.csv')
            result = self.window.create_file_dialog(
                webview.OPEN_DIALOG, 
                file_types=file_types
            )
            
            if not result:
                return {"success": False, "error": "Operación cancelada por el usuario."}
                
            filepath = result
            if isinstance(result, list) or isinstance(result, tuple):
                filepath = result[0]
                
            return database.import_inventory_csv(filepath)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Sincronización en la nube ---
    def get_cloud_config(self):
        try:
            return {
                "success": True,
                "data": {
                    "mode": config.get_mode(),
                    "api_url": config.get_api_url(),
                    "api_key_set": bool(config.get_api_key()),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_cloud_config(self, data):
        try:
            mode = str(data.get("mode", "local")).strip().lower()
            if mode not in ("local", "remote"):
                return {"success": False, "error": "Modo inválido. Use 'local' o 'remote'."}
            cfg = config.load_config()
            cfg["mode"] = mode
            if data.get("api_url"):
                cfg["api_url"] = str(data["api_url"]).strip().rstrip("/")
            if data.get("api_key"):
                cfg["api_key"] = str(data["api_key"]).strip()
            path = config.save_config(cfg)
            return {
                "success": True,
                "message": f"Configuración guardada. Reinicia la aplicación para aplicar el modo '{mode}'.",
                "path": path,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_cloud_connection(self, data=None):
        try:
            import json
            import urllib.error
            import urllib.request

            data = data or {}
            api_url = str(data.get("api_url") or config.get_api_url()).strip().rstrip("/")
            api_key = str(data.get("api_key") or config.get_api_key()).strip()
            if not api_url:
                return {"success": False, "error": "Indica la URL del servidor."}

            headers = {"Accept": "application/json"}
            if api_key:
                headers["X-API-Key"] = api_key
            req = urllib.request.Request(f"{api_url}/health", headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode())
            if body.get("ok"):
                return {"success": True, "message": "Conexión con el servidor exitosa."}
            return {"success": False, "error": "Respuesta inesperada del servidor."}
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"Error HTTP {e.code} al conectar."}
        except Exception as e:
            return {"success": False, "error": str(e)}

def main():
    # Inicializar base de datos (local) o verificar servidor (remoto)
    try:
        database.init_db()
    except Exception as e:
        if config.is_remote():
            print(f"Advertencia: no se pudo conectar al servidor remoto: {e}")
        else:
            raise
    
    # Crear API
    api = Api()
    
    # Ruta absoluta del frontend (compatible con PyInstaller)
    html_path = get_resource_path(os.path.join('web', 'index.html'))
    
    # Configurar ventana
    window = webview.create_window(
        title='StockVibe v1.2 - Gestión de Inventario & Ventas',
        url=html_path,
        js_api=api,
        width=1200,
        height=800,
        min_size=(1000, 700),
        text_select=False, # Evitar seleccionar textos de la UI como una web común
        background_color='#0f172a' # Coincide con nuestro slate-900 oscuro
    )
    
    # Asociar la ventana a la API
    api.set_window(window)
    
    # Arrancar la aplicación de escritorio
    # debug=True habilita el menú de inspección al hacer clic derecho para desarrollo
    webview.start(debug=True)

if __name__ == '__main__':
    main()
