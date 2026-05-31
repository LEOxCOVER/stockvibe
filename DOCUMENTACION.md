# Documentación del Proyecto StockVibe

## Descripción general
StockVibe es una aplicación de inventario y ventas construida en Python con dos frentes principales:
- **Escritorio**: interfaz web integrada con `pywebview` y frontend HTML/CSS/JS.
- **Móvil/Android**: app en `Kivy` con navegación completa para inventario, ventas, historial de ventas, deudores, abonos y ajustes.

El proyecto usa una base de datos SQLite local (`inventory.db`) para almacenar productos, categorías, ventas, clientes, pagos de crédito y configuración.

## Estructura del proyecto

- `main.py`
  - Punto de entrada para la app de escritorio.
  - Carga la interfaz web desde `web/index.html` usando `pywebview`.
  - Expone una API Python al frontend para CRUD de productos, categorías, ventas, deudores y configuración.

- `database.py`
  - Maneja la conexión SQLite y la inicialización de la base de datos.
  - Define las tablas:
    - `categories`
    - `products`
    - `settings`
    - `sales`
    - `sale_items`
    - `customers`
    - `credit_payments`
  - Implementa operaciones:
    - CRUD de categorías
    - CRUD de productos
    - ventas y detalles de ventas
    - gestión de créditos y deudores
    - tasa de cambio
    - inicialización con datos semilla

- `web/`
  - `index.html`: interfaz principal de la aplicación web.
  - `app.js`: lógica de cliente que invoca la API de Python expuesta por `pywebview`.
  - `style.css`: estilos visuales para la app web.

- `requirements.txt`
  - Listado de dependencias Python:
    - `pywebview>=5.1`
    - `kivy>=2.2.0`

- `StockVibe.spec`
  - Especificación de PyInstaller para compilar la app de escritorio en un ejecutable.
  - Incluye los archivos de la carpeta `web` como recursos.

- `buildozer.spec`
  - Configuración para empaquetar el app Android con `buildozer`.
  - Define paquete `org.stockvibe` y dependencias de `kivy`.

- `main_android.py`
  - Implementa la aplicación móvil en Kivy.
  - Contiene pantallas para:
    - dashboard
    - inventario
    - formulario de productos
    - deudores
    - detalle de deudor
    - ajustes
  - Carga datos desde `database.py` y reutiliza la lógica de base de datos SQLite.

## Características principales

- Gestión de inventario:
  - Productos con nombre, SKU, categoría, descripción, precio de compra, precio de venta, stock y stock mínimo.
  - Categorías configurables.

- Ventas y facturación:
  - Registro de ventas con items, costos, ganancias y estado de pago.
  - Carrito de ventas móvil con cobro de ventas en contado y a crédito.
  - Historial de ventas y consulta de facturas desde la app.

- Cuentas por cobrar / Deudores:
  - Registro de ventas a crédito.
  - Consulta de clientes con facturas pendientes.
  - Detalle de deuda, pagos realizados, saldo restante y abonos parciales.

- Ajustes:
  - Tasa de cambio USD/Bs configurable.

- Soporte de importación/exportación de inventario en CSV (desde la API de escritorio).

## Ejecución

### App de escritorio
1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecutar la aplicación:
   ```bash
   python main.py
   ```
3. Para compilar el ejecutable:
   ```bash
   python -m PyInstaller StockVibe.spec
   ```

### App Android (prototipo)
1. Instalar `buildozer` y dependencias de Kivy según la documentación oficial.
2. Construir la app Android:
   ```bash
   buildozer android debug
   ```
3. El archivo APK resultante se genera en `bin/`.

> Nota: la aplicación móvil usa el mismo módulo `database.py` de SQLite, por lo que comparte la lógica de datos basada en el archivo `inventory.db`.

## Recomendaciones de desarrollo

- Si se desea mejorar la experiencia móvil, se puede:
  - refinar la selección de cantidades y la edición de productos en el carrito.
  - mejorar la experiencia de pago en crédito con formularios más claros y validaciones adicionales.
  - sincronizar la base de datos entre modo escritorio y móvil si se usa en dispositivos diferentes.

- Para actualizaciones de esquema, `database.py` ya incluye migraciones simples que añaden campos nuevos a `sales` si no existen.

## Archivos importantes

- `main.py`: lanzamiento desktop con `pywebview`.
- `database.py`: almacenamiento SQLite y lógica de negocio.
- `web/index.html`, `web/app.js`, `web/style.css`: frontend web para escritorio.
- `StockVibe.spec`: configuraciones de PyInstaller.
- `main_android.py`: app Kivy para Android.
- `buildozer.spec`: configuración de empaquetado Android.

## Estado actual

- El proyecto tiene una aplicación de escritorio funcional integrando web y Python.
- El port Android está ahora completo con inventario, ventas, historial de ventas, deudores, abonos y ajustes.
- La app móvil Kivy ya soporta ventas de contado y crédito, historial de facturas y registro de pagos parciales.

---

Generado como documentación central del proyecto StockVibe.
