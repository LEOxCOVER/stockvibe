"""
API REST central de StockVibe.
Desplegar en Render.com con PostgreSQL gratuito en Neon.tech.
"""
import io
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import database  # noqa: E402

API_KEY = os.environ.get("STOCKVIBE_API_KEY", "").strip()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.init_db()
    yield


app = FastAPI(
    title="StockVibe API",
    description="API central para sincronizar inventario y ventas entre escritorio y móvil.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida o ausente.")


# --- Modelos ---

class CategoryCreate(BaseModel):
    name: str
    description: str = ""


class ProductCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    category_id: Optional[int] = None
    description: str = ""
    purchase_price: float
    sale_price: float
    stock: int
    min_stock: int = 5


class QuickStockBody(BaseModel):
    quantity: int


class CustomerCreate(BaseModel):
    name: str
    phone: str = ""


class SaleItem(BaseModel):
    product_id: int
    quantity: int


class SaleCreate(BaseModel):
    items: list[SaleItem]
    payment_status: str = "contado"
    customer_name: Optional[str] = None
    initial_payment: float = 0.0


class CreditPaymentBody(BaseModel):
    amount: float


class ExchangeRateBody(BaseModel):
    rate: float


# --- Rutas públicas ---

@app.get("/health")
def health():
    return {"ok": True, "service": "stockvibe-api"}


# --- Configuración ---

@app.get("/settings/exchange-rate", dependencies=[Depends(verify_api_key)])
def get_exchange_rate():
    return database.get_exchange_rate()


@app.put("/settings/exchange-rate", dependencies=[Depends(verify_api_key)])
def update_exchange_rate(body: ExchangeRateBody):
    return database.update_exchange_rate(body.rate)


# --- Categorías ---

@app.get("/categories", dependencies=[Depends(verify_api_key)])
def get_categories():
    return database.get_categories()


@app.post("/categories", dependencies=[Depends(verify_api_key)])
def add_category(body: CategoryCreate):
    return database.add_category(body.name, body.description)


@app.put("/categories/{cat_id}", dependencies=[Depends(verify_api_key)])
def update_category(cat_id: int, body: CategoryCreate):
    return database.update_category(cat_id, body.name, body.description)


@app.delete("/categories/{cat_id}", dependencies=[Depends(verify_api_key)])
def delete_category(cat_id: int):
    return database.delete_category(cat_id)


# --- Productos ---

@app.get("/products", dependencies=[Depends(verify_api_key)])
def get_products():
    return database.get_products()


@app.post("/products", dependencies=[Depends(verify_api_key)])
def add_product(body: ProductCreate):
    return database.add_product(
        body.name, body.sku, body.category_id, body.description,
        body.purchase_price, body.sale_price, body.stock, body.min_stock,
    )


@app.put("/products/{prod_id}", dependencies=[Depends(verify_api_key)])
def update_product(prod_id: int, body: ProductCreate):
    return database.update_product(
        prod_id, body.name, body.sku, body.category_id, body.description,
        body.purchase_price, body.sale_price, body.stock, body.min_stock,
    )


@app.delete("/products/{prod_id}", dependencies=[Depends(verify_api_key)])
def delete_product(prod_id: int):
    return database.delete_product(prod_id)


@app.post("/products/{product_id}/quick-stock", dependencies=[Depends(verify_api_key)])
def quick_add_stock(product_id: int, body: QuickStockBody):
    return database.quick_add_stock(product_id, body.quantity)


# --- Clientes ---

@app.get("/customers", dependencies=[Depends(verify_api_key)])
def get_customers():
    return database.get_customers()


@app.post("/customers", dependencies=[Depends(verify_api_key)])
def add_customer(body: CustomerCreate):
    return database.add_customer(body.name, body.phone)


@app.delete("/customers/{customer_id}", dependencies=[Depends(verify_api_key)])
def delete_customer(customer_id: int):
    return database.delete_customer(customer_id)


# --- Ventas ---

@app.get("/sales", dependencies=[Depends(verify_api_key)])
def get_sales_history():
    return database.get_sales_history()


@app.get("/sales/{sale_id}", dependencies=[Depends(verify_api_key)])
def get_sale_details(sale_id: int):
    details = database.get_sale_details(sale_id)
    if not details:
        raise HTTPException(status_code=404, detail="Venta no encontrada.")
    return details


@app.post("/sales", dependencies=[Depends(verify_api_key)])
def register_sale(body: SaleCreate):
    items = [item.model_dump() for item in body.items]
    return database.register_sale(
        items, body.payment_status, body.customer_name, body.initial_payment,
    )


@app.delete("/sales/history", dependencies=[Depends(verify_api_key)])
def clear_sales_history():
    return database.clear_sales_history()


# --- Créditos ---

@app.get("/credits/pending", dependencies=[Depends(verify_api_key)])
def get_pending_credits():
    return database.get_pending_credits()


@app.post("/credits/{sale_id}/payments", dependencies=[Depends(verify_api_key)])
def register_credit_payment(sale_id: int, body: CreditPaymentBody):
    return database.register_credit_payment(sale_id, body.amount)


# --- Deudores ---

@app.get("/debtors", dependencies=[Depends(verify_api_key)])
def get_debtor_accounts():
    return database.get_debtor_accounts()


@app.get("/debtors/{customer_name}", dependencies=[Depends(verify_api_key)])
def get_debtor_details(customer_name: str):
    return database.get_debtor_details(customer_name)


# --- Balance y dashboard ---

@app.get("/balance/daily", dependencies=[Depends(verify_api_key)])
def get_daily_balance(date: Optional[str] = Query(default=None)):
    return database.get_daily_balance(date)


@app.get("/dashboard/stats", dependencies=[Depends(verify_api_key)])
def get_dashboard_stats():
    return database.get_dashboard_stats()


# --- CSV ---

@app.get("/inventory/export-csv", dependencies=[Depends(verify_api_key)])
def export_inventory_csv():
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        path = tmp.name
    result = database.export_inventory_csv(path)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Error al exportar."))
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    os.unlink(path)
    return {"success": True, "data": content}


@app.post("/inventory/import-csv", dependencies=[Depends(verify_api_key)])
async def import_inventory_csv(request: Request):
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="El cuerpo CSV está vacío.")
    import tempfile
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
        tmp.write(raw)
        path = tmp.name
    result = database.import_inventory_csv(path)
    os.unlink(path)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Error al importar."))
    return result
