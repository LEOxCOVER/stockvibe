# StockVibe

StockVibe es una aplicación de inventario y ventas desarrollada en Python con dos modos principales:

- **Escritorio**: interfaz web integrada usando `pywebview` y frontend `HTML/CSS/JS`.
- **Android**: aplicación móvil desarrollada en `Kivy` con navegación para inventario, ventas, historial de ventas, deudores y ajustes.

## Estructura del proyecto

- `main.py`
  - Punto de entrada para la aplicación de escritorio.
  - Carga `web/index.html` con `pywebview`.
  - Expone métodos Python al frontend para CRUD de categorías, productos, ventas, créditos y configuración.

- `database.py`
  - Administra SQLite y la inicialización del esquema.
  - Define las tablas:
    - `categories`
    - `products`
    - `settings`
    - `sales`
    - `sale_items`
    - `customers`
    - `credit_payments`
  - Proporciona funcionalidades de negocio:
    - CRUD de categorías y productos
    - registro de ventas y detalle de facturas
    - administración de créditos y deudores
    - tasa de cambio
    - limpieza e importación/exportación

- `web/`
  - `index.html`: interfaz principal del escritorio.
  - `app.js`: lógica de cliente y llamadas a la API Python.
  - `style.css`: estilos de la interfaz.

- `main_android.py`
  - Aplicación móvil en Kivy.
  - Incluye pantallas para dashboard, inventario, ventas, historial, deudores, detalle de deudor y ajustes.
  - Reutiliza `database.py` para acceder a SQLite.

- `requirements.txt`
  - Dependencias Python:
    - `pywebview>=5.1`
    - `kivy>=2.2.0`

- `StockVibe.spec`
  - Configuración de PyInstaller para empaquetar la app de escritorio.

- `buildozer.spec`
  - Configuración para construir el APK Android.

## Características

- Gestión de inventario con productos, stock, precios y categorías.
- Ventas con carrito, cobro en contado y crédito.
- Historial de ventas y detalle de facturas.
- Cuentas por cobrar, deudores y abonos parciales.
- Ajuste de tasa de cambio USD/Bs.
- Importación/exportación de inventario en CSV (desde la app de escritorio).

## Ejecución

### App de escritorio

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecutar:
   ```bash
   python main.py
   ```
3. Para generar un ejecutable:
   ```bash
   python -m PyInstaller StockVibe.spec
   ```

### App Android

1. Asegúrate de tener `buildozer` instalado y configurado en un entorno compatible.
2. Construir APK:
   ```bash
   buildozer android debug
   ```
3. El APK generado aparecerá en `bin/`.

> Nota: `buildozer` requiere un entorno Linux/WSL configurado. En Windows, instala WSL o usa una máquina Linux para compilar el APK.

## Estado actual

- La app de escritorio funciona con frontend web y backend Python.
- La app Android está completa con inventario, ventas, historial de ventas, deudores, abonos y ajustes.
- `main_android.py` admite ventas de contado y crédito, historial y registro de pagos parciales.

## Sincronización en la nube

Escritorio y móvil pueden compartir la misma base de datos mediante la API central desplegada en **Render** (gratis) con **PostgreSQL en Neon** (gratis).

Ver la guía completa: **[DEPLOY_NUBE.md](DEPLOY_NUBE.md)**

Resumen rápido:
1. Crea base de datos en [Neon](https://neon.tech).
2. Despliega la API con [Render](https://render.com) usando `render.yaml`.
3. Configura `stockvibe_config.json` con `mode: "remote"`, `api_url` y `api_key`.
4. Reinicia escritorio y móvil.

## Notas

- La base de datos SQLite es local en `inventory.db`.
- El código móvil y de escritorio comparten la lógica de persistencia en `database.py`.
