// CACHÉ DE DATOS LOCALES Y CONFIGURACIÓN
let categoriesList = [];
let productsList = [];
let salesHistoryList = [];
let creditsList = [];
let customersList = [];
let cart = [];
let pyApi = null; // Guardará la referencia a pywebview.api

// CONFIGURACIÓN MULTIMONEDA
let exchangeRate = 45.0; // Tasa por defecto, se sobreescribe desde base de datos
let posPaymentMethod = "contado"; // 'contado' o 'credito'
let purchaseCurrencyMode = "USD"; // 'USD' o 'BS'
let saleCurrencyMode = "USD"; // 'USD' o 'BS'
let posInitialCurrency = "USD"; // 'USD' o 'BS'

// INICIALIZACIÓN
document.addEventListener("DOMContentLoaded", () => {
    // Escuchar el evento de inicialización de pywebview
    window.addEventListener('pywebviewready', () => {
        setupApiConnection();
    });

    // Como respaldo en caso de que ya se haya disparado
    if (window.pywebview && window.pywebview.api) {
        setupApiConnection();
    } else {
        console.warn("Esperando por pywebview api...");
    }

    // Enlazar botones críticos del inventario
    document.getElementById("btn-open-product")?.addEventListener("click", openProductModal);
    
    // Iniciar pestaña inicial
    switchTab('dashboard');
});

// VINCULAR API CON PYTHON
async function setupApiConnection() {
    pyApi = window.pywebview.api;
    document.getElementById("connection-status").innerHTML = `
        <span class="dot online"></span>
        <span>Escritorio Conectado</span>
    `;
    
    // Obtener tasa de cambio oficial inicial
    try {
        exchangeRate = await pyApi.get_exchange_rate();
        updateExchangeRateUI();
    } catch (e) {
        console.error("Error al obtener tasa inicial:", e);
    }
    
    // Carga inicial de datos
    loadAllData();
}

async function loadAllData() {
    if (!pyApi) return;
    
    try {
        // Cargar todo de forma concurrente
        await Promise.all([
            reloadCategories(),
            reloadProducts(),
            reloadSalesHistory(),
            reloadPendingCredits(),
            reloadCustomers()
        ]);
        
        // El dashboard se actualiza al final con los datos consolidados
        await updateDashboard();
    } catch (e) {
        console.error("Error cargando datos principales:", e);
        showToast("Error al cargar la información del almacén", "danger");
    }
}

// FORMATO DE MONEDA DUAL
function formatBs(usdAmount) {
    const bsAmount = usdAmount * exchangeRate;
    return bsAmount.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " Bs.";
}

function formatUsd(usdAmount) {
    return "$" + usdAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function updateExchangeRateUI() {
    // Actualizar badges e inputs de tasa
    const badge = document.getElementById("sidebar-exchange-rate");
    if (badge) {
        badge.textContent = `Tasa: ${exchangeRate.toFixed(2)} Bs/$`;
    }
    const input = document.getElementById("form-settings-exchange-rate");
    if (input) {
        input.value = exchangeRate;
    }
}

// ----------------- CONTROLADOR DE NAVEGACIÓN (SPA) -----------------
function switchTab(tabId) {
    // 1. Quitar activo de todos los nav items
    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.remove("active");
    });
    
    // 2. Ocultar todas las secciones
    document.querySelectorAll(".content-section").forEach(sec => {
        sec.classList.remove("active");
    });
    
    // 3. Activar el item y la sección correspondientes
    const activeNav = document.getElementById(`nav-${tabId}`);
    const activeSec = document.getElementById(`section-${tabId}`);
    
    if (activeNav) activeNav.classList.add("active");
    if (activeSec) activeSec.classList.add("active");
    
    // 4. Cambiar el título y subtítulo de la cabecera
    const titleEl = document.getElementById("page-title");
    const subEl = document.getElementById("page-subtitle");
    
    switch (tabId) {
        case 'dashboard':
            titleEl.textContent = "Panel de Control";
            subEl.textContent = "Estadísticas actuales expresadas en Bolívares y Dólares.";
            updateDashboard();
            break;
        case 'inventory':
            titleEl.textContent = "Inventario de Almacén";
            subEl.textContent = "Catálogo de productos con valor base en Dólares ($) y conversión automática.";
            renderProductsTable();
            break;
        case 'categories':
            titleEl.textContent = "Categorías de Venta";
            subEl.textContent = "Clasificación de productos para agilizar tus búsquedas.";
            renderCategoriesTable();
            break;
        case 'pos':
            titleEl.textContent = "Punto de Venta Expreso";
            subEl.textContent = "Registra una venta rápida de contado o crédito con abonos condicionales.";
            posPaymentMethod = "contado"; // reset
            posInitialCurrency = "USD";
            document.getElementById("btn-pay-cash").classList.add("active");
            document.getElementById("btn-pay-credit").classList.remove("active");
            document.getElementById("pos-debtor-group").style.display = "none";
            document.getElementById("pos-debtor-name").value = "";
            document.getElementById("pos-debtor-select").value = "";
            document.getElementById("pos-initial-payment").value = "";
            document.getElementById("pos-initial-currency-btn").textContent = "$ USD";
            document.getElementById("pos-initial-payment-bs").textContent = "Equivale a: 0.00 Bs.";
            renderPosCatalog();
            renderCart();
            if (typeof reloadCustomers === 'function') {
                reloadCustomers();
            }
            break;
        case 'history':
            titleEl.textContent = "Historial de Transacciones";
            subEl.textContent = "Lista histórica de ventas con diferenciación entre cobros al contado y créditos.";
            reloadSalesHistory();
            break;
        case 'credits':
            titleEl.textContent = "Cuentas por Cobrar";
            subEl.textContent = "Control de ventas a crédito, seguimiento de abonos y saldos pendientes.";
            reloadPendingCredits();
            break;
        case 'balance':
            titleEl.textContent = "Balance Diario";
            subEl.textContent = "Resumen financiero diario y resumen de caja por fecha.";
            loadDailyBalance();
            break;
        case 'alerts':
            titleEl.textContent = "Alertas de Stock Crítico";
            subEl.textContent = "Productos que han alcanzado o superado el stock de alerta mínimo.";
            renderAlertsTable();
            break;
        case 'settings':
            titleEl.textContent = "Ajustes del Sistema";
            subEl.textContent = "Configura la tasa de cambio del día y respalda/restaura tu base de datos.";
            loadCloudConfig();
            break;
    }
}

// ----------------- OPERACIONES DE CATEGORÍAS -----------------
async function reloadCategories() {
    if (!pyApi) return;
    categoriesList = await pyApi.get_categories();
    
    // Rellenar selects
    const filterCat = document.getElementById("inventory-filter-category");
    const formCat = document.getElementById("form-product-category");
    
    // Guardar opción seleccionada previamente si existe
    const prevFilterVal = filterCat.value;
    
    filterCat.innerHTML = `<option value="">Todas las Categorías</option>`;
    formCat.innerHTML = `<option value="">Seleccionar Categoría *</option>`;
    
    categoriesList.forEach(cat => {
        filterCat.innerHTML += `<option value="${cat.id}">${cat.name}</option>`;
        formCat.innerHTML += `<option value="${cat.id}">${cat.name}</option>`;
    });
    
    // Restaurar valor anterior
    if (prevFilterVal) filterCat.value = prevFilterVal;
}

async function reloadCustomers() {
    if (!pyApi) return;
    customersList = await pyApi.get_customers();
    const select = document.getElementById("pos-debtor-select");
    if (!select) return;

    const previousValue = select.value;
    select.innerHTML = `<option value="">— Seleccionar cliente registrado —</option>`;
    select.innerHTML += `<option value="__new__">+ Agregar nuevo cliente...</option>`;

    customersList.forEach(customer => {
        select.innerHTML += `<option value="${customer.id}">${escapeHtml(customer.name)}</option>`;
    });

    if (previousValue) {
        select.value = previousValue;
        onCustomerSelectChange();
    }
}

function renderCategoriesTable() {
    const tbody = document.getElementById("categories-tbody");
    tbody.innerHTML = "";
    
    if (categoriesList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No hay categorías registradas. ¡Crea una nueva!</td></tr>`;
        return;
    }
    
    categoriesList.forEach(cat => {
        tbody.innerHTML += `
            <tr>
                <td style="font-weight: 600; color: var(--text-main);">${escapeHtml(cat.name)}</td>
                <td class="text-muted">${escapeHtml(cat.description || 'Sin descripción')}</td>
                <td class="text-center">
                    <div class="actions-cell">
                        <button class="btn-icon edit" title="Editar Categoría" onclick="editCategory(${cat.id}, '${escapeQuote(cat.name)}', '${escapeQuote(cat.description || '')}')">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                        </button>
                        <button class="btn-icon delete" title="Eliminar Categoría" onclick="deleteCategory(${cat.id}, '${escapeQuote(cat.name)}')">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
}

function openCategoryModal() {
    document.getElementById("category-modal-title").textContent = "Nueva Categoría";
    document.getElementById("form-category-id").value = "";
    document.getElementById("category-form").reset();
    document.getElementById("category-modal").classList.add("active");
}

function closeCategoryModal() {
    document.getElementById("category-modal").classList.remove("active");
}

function editCategory(id, name, desc) {
    document.getElementById("category-modal-title").textContent = "Editar Categoría";
    document.getElementById("form-category-id").value = id;
    document.getElementById("form-category-name").value = name;
    document.getElementById("form-category-desc").value = desc;
    document.getElementById("category-modal").classList.add("active");
}

async function saveCategory(event) {
    event.preventDefault();
    if (!pyApi) return;
    
    const id = document.getElementById("form-category-id").value;
    const name = document.getElementById("form-category-name").value.trim();
    const desc = document.getElementById("form-category-desc").value.trim();
    
    let res;
    if (id) {
        res = await pyApi.update_category(parseInt(id), name, desc);
    } else {
        res = await pyApi.add_category(name, desc);
    }
    
    if (res.success) {
        showToast(id ? "Categoría actualizada con éxito" : "Categoría creada con éxito", "success");
        closeCategoryModal();
        await reloadCategories();
        renderCategoriesTable();
    } else {
        showToast(res.error || "Ocurrió un error al guardar", "danger");
    }
}

async function deleteCategory(id, name) {
    if (!pyApi) return;
    if (confirm(`¿Estás seguro de que deseas eliminar la categoría "${name}"?\nLos productos de esta categoría quedarán sin categoría asignada.`)) {
        const res = await pyApi.delete_category(id);
        if (res.success) {
            showToast("Categoría eliminada", "success");
            await reloadCategories();
            renderCategoriesTable();
            await reloadProducts();
            if (document.getElementById("section-inventory").classList.contains("active")) {
                renderProductsTable();
            }
        } else {
            showToast(res.error || "No se pudo eliminar la categoría", "danger");
        }
    }
}

// ----------------- OPERACIONES DE PRODUCTOS (USD BASE) -----------------
async function reloadProducts() {
    if (!pyApi) return;
    productsList = await pyApi.get_products();
    updateSidebarAlertBadge();
}

function updateSidebarAlertBadge() {
    const alertCount = productsList.filter(p => p.stock <= p.min_stock).length;
    const badge = document.getElementById("sidebar-alert-badge");
    const dashboardAlertBg = document.getElementById("stat-alert-icon-bg");
    
    if (alertCount > 0) {
        badge.textContent = alertCount;
        badge.style.display = "block";
        if (dashboardAlertBg) {
            dashboardAlertBg.classList.add("critical");
        }
    } else {
        badge.style.display = "none";
        if (dashboardAlertBg) {
            dashboardAlertBg.classList.remove("critical");
        }
    }
}

function renderProductsTable() {
    const tbody = document.getElementById("products-tbody");
    tbody.innerHTML = "";
    
    const filtered = getFilteredProducts();
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted">No se encontraron productos con los filtros aplicados.</td></tr>`;
        return;
    }
    
    filtered.forEach(p => {
        // Margen calculado sobre el costo de compra
        const profit = p.sale_price - p.purchase_price;
        const marginPct = p.purchase_price > 0 ? (profit / p.purchase_price) * 100 : 0;
        
        // Estado de Stock
        let stockBadge = "";
        if (p.stock === 0) {
            stockBadge = `<span class="badge out-of-stock">Agotado</span>`;
        } else if (p.stock <= p.min_stock) {
            stockBadge = `<span class="badge low-stock">Bajo Stock</span>`;
        } else {
            stockBadge = `<span class="badge in-stock">Disponible</span>`;
        }
        
        tbody.innerHTML += `
            <tr>
                <td style="font-weight: 600; color: var(--text-main);">${escapeHtml(p.name)}</td>
                <td class="text-muted" style="font-family: monospace;">${escapeHtml(p.sku || 'N/A')}</td>
                <td><span class="cat-bullet"><span class="cat-dot" style="background-color: ${getColorHash(p.category_name || 'General')}"></span>${escapeHtml(p.category_name || 'Sin Categoría')}</span></td>
                <!-- Costo de Compra Dual -->
                <td class="text-right">
                    <span class="block-val" style="font-size: 13.5px; font-weight: 600;">${formatBs(p.purchase_price)}</span>
                    <span class="block-val text-muted" style="font-size: 11.5px;">${formatUsd(p.purchase_price)}</span>
                </td>
                <!-- PVP Dual -->
                <td class="text-right">
                    <span class="block-val text-indigo" style="font-size: 14.5px; font-weight: 700;">${formatBs(p.sale_price)}</span>
                    <span class="block-val text-muted" style="font-size: 12px; font-weight: 600;">${formatUsd(p.sale_price)}</span>
                </td>
                <td class="text-right text-success" style="font-weight: 600;">${marginPct.toFixed(1)}%</td>
                <td class="text-center" style="font-weight: 700; ${p.stock <= p.min_stock ? 'color: var(--danger);' : ''}">${p.stock}</td>
                <td class="text-center text-muted">${p.min_stock}</td>
                <td class="text-center">${stockBadge}</td>
                <td class="text-center">
                    <div class="actions-cell">
                        <button class="btn-icon stock" title="Agregar Stock" onclick="openQuickStockModal(${p.id}, '${escapeQuote(p.name)}', ${p.stock})">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                        </button>
                        <button class="btn-icon edit" title="Editar Producto" onclick="editProduct(${p.id})">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                        </button>
                        <button class="btn-icon delete" title="Eliminar Producto" onclick="deleteProduct(${p.id}, '${escapeQuote(p.name)}')">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
}

function getFilteredProducts() {
    const searchVal = document.getElementById("inventory-search").value.toLowerCase().trim();
    const catVal = document.getElementById("inventory-filter-category").value;
    const stockVal = document.getElementById("inventory-filter-stock").value;
    
    return productsList.filter(p => {
        // Filtro Búsqueda
        const matchesSearch = p.name.toLowerCase().includes(searchVal) || (p.sku && p.sku.toLowerCase().includes(searchVal));
        
        // Filtro Categoría
        const matchesCat = catVal === "" || p.category_id === parseInt(catVal);
        
        // Filtro Stock
        let matchesStock = true;
        if (stockVal === "in_stock") {
            matchesStock = p.stock > p.min_stock;
        } else if (stockVal === "low_stock") {
            matchesStock = p.stock > 0 && p.stock <= p.min_stock;
        } else if (stockVal === "out_of_stock") {
            matchesStock = p.stock === 0;
        }
        
        return matchesSearch && matchesCat && matchesStock;
    });
}

function filterProducts() {
    renderProductsTable();
}

function getProductPurchasePriceUsd() {
    const raw = parseFloat(document.getElementById("form-product-p-price").value) || 0;
    return purchaseCurrencyMode === "BS" ? raw / exchangeRate : raw;
}

function getProductSalePriceUsd() {
    const raw = parseFloat(document.getElementById("form-product-s-price").value) || 0;
    return saleCurrencyMode === "BS" ? raw / exchangeRate : raw;
}

function setProductPriceInputFromUsd(elementId, usdValue, mode) {
    const value = mode === "BS" ? usdValue * exchangeRate : usdValue;
    document.getElementById(elementId).value = value.toFixed(2);
}

function togglePurchaseCurrency() {
    purchaseCurrencyMode = purchaseCurrencyMode === "USD" ? "BS" : "USD";
    const button = document.getElementById("btn-purchase-currency");
    button.textContent = purchaseCurrencyMode === "USD" ? "$ USD" : "Bs.";
    setProductPriceInputFromUsd("form-product-p-price", getProductPurchasePriceUsd(), purchaseCurrencyMode);
    calculateMargin();
}

function toggleSaleCurrency() {
    saleCurrencyMode = saleCurrencyMode === "USD" ? "BS" : "USD";
    const button = document.getElementById("btn-sale-currency");
    button.textContent = saleCurrencyMode === "USD" ? "$ USD" : "Bs.";
    setProductPriceInputFromUsd("form-product-s-price", getProductSalePriceUsd(), saleCurrencyMode);
    calculateProductBsPreview();
    calculateMargin();
}

function onPurchasePriceInput() {
    calculateMargin();
}

function onSalePriceInput() {
    calculateMargin();
    calculateProductBsPreview();
}

function calculateSalePriceFromMargin() {
    const margin = parseFloat(document.getElementById("form-product-margin-input").value) || 0;
    const costUsd = getProductPurchasePriceUsd();
    const saleUsd = costUsd * (1 + margin / 100);
    setProductPriceInputFromUsd("form-product-s-price", saleUsd, saleCurrencyMode);
    calculateMargin();
    calculateProductBsPreview();
}

function openQuickStockModal(productId, productName, currentStock) {
    document.getElementById("quick-stock-title").textContent = `Agregar Stock a ${productName}`;
    document.getElementById("form-quick-stock-id").value = productId;
    document.getElementById("form-quick-stock-name").textContent = productName;
    document.getElementById("form-quick-stock-current").textContent = currentStock;
    document.getElementById("form-quick-stock-qty").value = "";
    document.getElementById("quick-stock-modal").classList.add("active");
}

function closeQuickStockModal() {
    document.getElementById("quick-stock-modal").classList.remove("active");
}

async function saveQuickStock(event) {
    event.preventDefault();
    if (!pyApi) return;

    const productId = parseInt(document.getElementById("form-quick-stock-id").value);
    const qty = parseInt(document.getElementById("form-quick-stock-qty").value) || 0;

    if (qty <= 0) {
        showToast("Debes ingresar una cantidad válida para agregar al stock.", "danger");
        return;
    }

    const res = await pyApi.quick_add_stock(productId, qty);
    if (res.success) {
        showToast(`Se agregaron ${res.added} unidades a ${res.product_name}. Stock actual: ${res.new_stock}.`, "success");
        closeQuickStockModal();
        await reloadProducts();
        if (document.getElementById("section-inventory").classList.contains("active")) {
            renderProductsTable();
        }
    } else {
        showToast(res.error || "No se pudo actualizar el stock.", "danger");
    }
}

function onCustomerSelectChange() {
    const select = document.getElementById("pos-debtor-select");
    const input = document.getElementById("pos-debtor-name");
    if (!select || !input) return;
    input.style.display = select.value === "__new__" ? "block" : "none";
    if (select.value !== "__new__") {
        input.value = "";
    }
}

function togglePosInitialCurrency() {
    posInitialCurrency = posInitialCurrency === "USD" ? "BS" : "USD";
    const button = document.getElementById("pos-initial-currency-btn");
    if (button) {
        button.textContent = posInitialCurrency === "USD" ? "$ USD" : "Bs.";
    }
    calculateInitialPaymentBs();
}

function calculateInitialPaymentBs() {
    const raw = parseFloat(document.getElementById("pos-initial-payment").value) || 0;
    const previewEl = document.getElementById("pos-initial-payment-bs");
    if (posInitialCurrency === "USD") {
        previewEl.textContent = `Equivale a: ${formatBs(raw)}`;
    } else {
        const usd = raw / exchangeRate;
        previewEl.textContent = `Equivale a: ${formatUsd(usd)}`;
    }
}

async function confirmClearSalesHistory() {
    if (!pyApi) return;
    if (!confirm("¿Estás seguro de que deseas eliminar todo el historial de ventas y abonos? Esta acción no se puede deshacer.")) {
        return;
    }

    const res = await pyApi.clear_sales_history();
    if (res.success) {
        showToast(res.message || "Historial de ventas eliminado correctamente.", "success");
        await loadAllData();
        if (document.getElementById("section-history").classList.contains("active")) {
            renderSalesHistoryTable();
        }
    } else {
        showToast(res.error || "No se pudo limpiar el historial.", "danger");
    }
}

function openDebtorDetailModal(customerName) {
    document.getElementById("debtor-detail-title").textContent = `Cuenta de: ${customerName}`;
    document.getElementById("debtor-invoices-container").innerHTML = `<div class="text-center text-muted">Cargando detalles...</div>`;
    document.getElementById("debtor-detail-modal").classList.add("active");

    pyApi.get_debtor_details(customerName).then(res => {
        if (!res.success) {
            showToast(res.error || "No se pudieron cargar los detalles del deudor.", "danger");
            closeDebtorDetailModal();
            return;
        }

        const data = res.data;
        document.getElementById("debtor-det-total").textContent = formatBs(data.total_debt);
        document.getElementById("debtor-det-paid").textContent = formatBs(data.total_paid);
        document.getElementById("debtor-det-remaining").textContent = formatBs(data.total_remaining);

        const invoices = data.invoices || [];
        if (invoices.length === 0) {
            document.getElementById("debtor-invoices-container").innerHTML = `<div class="text-center text-muted">No hay facturas registradas para este deudor.</div>`;
            return;
        }

        document.getElementById("debtor-invoices-container").innerHTML = invoices.map(inv => {
            const statusLabel = inv.payment_status === 'credito' ? 'Pendiente' : 'Liquidado';
            const statusClass = inv.payment_status === 'credito' ? 'low-stock' : 'in-stock';
            const actionButton = inv.remaining > 0 ? `<button class="btn btn-sm btn-outline-success" onclick="openCreditPaymentModal(${inv.id}, '${escapeQuote(customerName)}', ${inv.remaining})">Abonar</button>` : '';
            return `
                <div class="debtor-invoice-card">
                    <div class="invoice-header">
                        <div>
                            <strong>Factura #${inv.id}</strong> · ${formatDateString(inv.timestamp)}
                        </div>
                        <div class="invoice-status ${statusClass}">${statusLabel}</div>
                    </div>
                    <div class="invoice-summary">
                        <span>Total: ${formatBs(inv.total_amount)} (${formatUsd(inv.total_amount)})</span>
                        <span>Abonado: ${formatBs(inv.amount_paid)} (${formatUsd(inv.amount_paid)})</span>
                        <span>Restante: ${formatBs(inv.remaining)} (${formatUsd(inv.remaining)})</span>
                        ${actionButton}
                    </div>
                    <div class="table-container">
                        <table class="modern-table compact-table">
                            <thead>
                                <tr>
                                    <th>Producto</th>
                                    <th>SKU</th>
                                    <th class="text-center">Cantidad</th>
                                    <th class="text-right">Precio</th>
                                    <th class="text-right">Subtotal</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${inv.items.map(item => `
                                    <tr>
                                        <td>${escapeHtml(item.product_name || 'Producto Eliminado')}</td>
                                        <td class="text-muted">${escapeHtml(item.product_sku || 'N/A')}</td>
                                        <td class="text-center">${item.quantity}</td>
                                        <td class="text-right">${formatBs(item.sale_price)}</td>
                                        <td class="text-right">${formatBs(item.subtotal)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }).join('');
    }).catch(err => {
        showToast("Error cargando la cuenta del deudor.", "danger");
        closeDebtorDetailModal();
    });
}

function closeDebtorDetailModal() {
    document.getElementById("debtor-detail-modal").classList.remove("active");
}

function openCreditPaymentModal(saleId, customer, remainingUsd) {
    document.getElementById("form-credit-sale-id").value = saleId;
    document.getElementById("form-credit-customer").textContent = customer;
    const remainingEl = document.getElementById("form-credit-remaining");
    remainingEl.textContent = `${formatBs(remainingUsd)} (${formatUsd(remainingUsd)})`;
    remainingEl.dataset.maxUsd = remainingUsd;
    document.getElementById("credit-payment-form").reset();
    document.getElementById("form-credit-payment-bs").textContent = "0.00 Bs.";
    document.getElementById("credit-payment-modal").classList.add("active");
}

function closeCreditPaymentModal() {
    document.getElementById("credit-payment-modal").classList.remove("active");
}

async function loadDailyBalance() {
    if (!pyApi) return;
    const dateInput = document.getElementById("balance-date-picker");
    const selectedDate = dateInput.value || new Date().toISOString().split('T')[0];
    dateInput.value = selectedDate;

    const data = await pyApi.get_daily_balance(selectedDate);
    if (!data || data.error) {
        showToast(data?.error || "No se pudo cargar el balance diario.", "danger");
        return;
    }
    document.getElementById("bal-cash-contado").textContent = formatBs(data.cash_contado);
    document.getElementById("bal-cash-contado-usd").textContent = formatUsd(data.cash_contado);
    document.getElementById("bal-cash-abonos").textContent = formatBs(data.cash_abonos);
    document.getElementById("bal-cash-abonos-usd").textContent = formatUsd(data.cash_abonos);
    document.getElementById("bal-total-cash").textContent = formatBs(data.total_cash);
    document.getElementById("bal-total-cash-usd").textContent = formatUsd(data.total_cash);
    document.getElementById("bal-credit-issued").textContent = formatBs(data.credit_issued);
    document.getElementById("bal-credit-issued-usd").textContent = formatUsd(data.credit_issued);
    document.getElementById("bal-total-invoiced").textContent = formatBs(data.total_invoiced);
    document.getElementById("bal-total-invoiced-usd").textContent = formatUsd(data.total_invoiced);
    document.getElementById("bal-total-cost").textContent = formatBs(data.total_cost);
    document.getElementById("bal-total-cost-usd").textContent = formatUsd(data.total_cost);
    document.getElementById("bal-net-profit").textContent = formatBs(data.total_profit);
    document.getElementById("bal-net-profit-usd").textContent = formatUsd(data.total_profit);
    document.getElementById("bal-total-ops").textContent = data.total_sale_count;
    document.getElementById("bal-cash-count").textContent = data.cash_sale_count;
    document.getElementById("bal-credit-count").textContent = data.credit_count;
    document.getElementById("bal-abonos-count").textContent = data.abonos_count;
}

function openProductModal() {
    try {
        purchaseCurrencyMode = "USD";
        saleCurrencyMode = "USD";
        document.getElementById("btn-purchase-currency").textContent = "$ USD";
        document.getElementById("btn-sale-currency").textContent = "$ USD";
        document.getElementById("product-modal-title").textContent = "Agregar Nuevo Producto";
        document.getElementById("form-product-id").value = "";
        document.getElementById("product-form").reset();
        document.getElementById("form-product-margin").textContent = "0.00%";
        document.getElementById("form-product-bs-preview").textContent = "0.00 Bs.";
        document.getElementById("product-modal").classList.add("active");
    } catch (err) {
        console.error("Error abriendo modal de producto:", err);
        if (typeof showToast === 'function') {
            showToast("No se pudo abrir el formulario de producto.", "danger");
        }
    }
}

function closeProductModal() {
    document.getElementById("product-modal").classList.remove("active");
}

function editProduct(id) {
    const p = productsList.find(item => item.id === id);
    if (!p) return;

    purchaseCurrencyMode = "USD";
    saleCurrencyMode = "USD";
    document.getElementById("btn-purchase-currency").textContent = "$ USD";
    document.getElementById("btn-sale-currency").textContent = "$ USD";

    document.getElementById("product-modal-title").textContent = "Editar Producto";
    document.getElementById("form-product-id").value = p.id;
    document.getElementById("form-product-name").value = p.name;
    document.getElementById("form-product-sku").value = p.sku || '';
    document.getElementById("form-product-category").value = p.category_id || '';
    document.getElementById("form-product-desc").value = p.description || '';
    setProductPriceInputFromUsd("form-product-p-price", p.purchase_price, purchaseCurrencyMode);
    setProductPriceInputFromUsd("form-product-s-price", p.sale_price, saleCurrencyMode);
    document.getElementById("form-product-stock").value = p.stock;
    document.getElementById("form-product-min-stock").value = p.min_stock;

    calculateMargin();
    calculateProductBsPreview();
    document.getElementById("product-modal").classList.add("active");
}

function calculateMargin() {
    const pPrice = getProductPurchasePriceUsd();
    const sPrice = getProductSalePriceUsd();
    const marginEl = document.getElementById("form-product-margin");

    if (pPrice > 0) {
        const profit = sPrice - pPrice;
        const marginPct = (profit / pPrice) * 100;
        marginEl.textContent = `${marginPct.toFixed(2)}%`;
        marginEl.style.color = profit < 0 ? "var(--danger)" : "var(--success)";
    } else {
        marginEl.textContent = "0.00%";
        marginEl.style.color = "var(--primary)";
    }
}

function calculateProductBsPreview() {
    const sPrice = getProductSalePriceUsd();
    const previewEl = document.getElementById("form-product-bs-preview");
    previewEl.textContent = formatBs(sPrice);
}

async function saveProduct(event) {
    event.preventDefault();
    if (!pyApi) return;

    const id = document.getElementById("form-product-id").value;
    const category_id = document.getElementById("form-product-category").value;

    const productData = {
        name: document.getElementById("form-product-name").value.trim(),
        sku: document.getElementById("form-product-sku").value.trim(),
        category_id: category_id ? parseInt(category_id) : null,
        description: document.getElementById("form-product-desc").value.trim(),
        purchase_price: getProductPurchasePriceUsd(),
        sale_price: getProductSalePriceUsd(),
        stock: parseInt(document.getElementById("form-product-stock").value) || 0,
        min_stock: parseInt(document.getElementById("form-product-min-stock").value) || 5
    };

    if (productData.purchase_price < 0 || productData.sale_price < 0) {
        showToast("Los precios no pueden ser negativos", "danger");
        return;
    }

    let res;
    if (id) {
        res = await pyApi.update_product(parseInt(id), productData);
    } else {
        res = await pyApi.add_product(productData);
    }

    if (res.success) {
        showToast(id ? "Producto actualizado con éxito" : "Producto guardado con éxito", "success");
        closeProductModal();
        await reloadProducts();
        renderProductsTable();
    } else {
        showToast(res.error || "Ocurrió un error al guardar", "danger");
    }
}

// Exponer funciones del modal de producto para los handlers inline
window.openProductModal = openProductModal;
window.closeProductModal = closeProductModal;
window.saveProduct = saveProduct;
window.togglePurchaseCurrency = togglePurchaseCurrency;
window.toggleSaleCurrency = toggleSaleCurrency;

async function deleteProduct(id, name) {
    if (!pyApi) return;
    if (confirm(`¿Estás seguro de que deseas eliminar el producto "${name}"?`)) {
        const res = await pyApi.delete_product(id);
        if (res.success) {
            showToast("Producto eliminado", "success");
            await reloadProducts();
            renderProductsTable();
        } else {
            showToast(res.error || "No se pudo eliminar el producto", "danger");
        }
    }
}

// ----------------- TABLA DE ALERTAS DE STOCK BAJO -----------------
function renderAlertsTable() {
    const tbody = document.getElementById("alerts-tbody");
    tbody.innerHTML = "";
    
    const lowStockProds = productsList.filter(p => p.stock <= p.min_stock);
    
    if (lowStockProds.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-success" style="padding: 30px; font-weight: 500;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 8px;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            ¡Excelente! Todos los productos se encuentran con stock óptimo superior al límite mínimo.
        </td></tr>`;
        return;
    }
    
    lowStockProds.forEach(p => {
        const needed = p.min_stock - p.stock;
        let critEl = "";
        
        if (p.stock === 0) {
            critEl = `<span class="badge out-of-stock">Agotado Total</span>`;
        } else {
            critEl = `<span class="badge low-stock">Crítico</span>`;
        }
        
        tbody.innerHTML += `
            <tr>
                <td style="font-weight: 600; color: var(--text-main);">${escapeHtml(p.name)}</td>
                <td style="font-family: monospace;" class="text-muted">${escapeHtml(p.sku || 'N/A')}</td>
                <td><span class="cat-bullet"><span class="cat-dot" style="background-color: ${getColorHash(p.category_name || 'General')}"></span>${escapeHtml(p.category_name || 'Sin Categoría')}</span></td>
                <td class="text-center" style="font-weight: 700; color: var(--danger);">${p.stock}</td>
                <td class="text-center text-muted">${p.min_stock}</td>
                <td class="text-center" style="font-weight: 600; color: var(--warning);">${needed <= 0 ? 1 : needed}</td>
                <td class="text-center">${critEl}</td>
            </tr>
        `;
    });
}

// ----------------- PUNTO DE VENTA EXPRESO (POS) -----------------
function renderPosCatalog() {
    const grid = document.getElementById("pos-grid");
    grid.innerHTML = "";
    
    const searchVal = document.getElementById("pos-search").value.toLowerCase().trim();
    
    // Filtrar productos
    const filtered = productsList.filter(p => {
        return p.name.toLowerCase().includes(searchVal) || (p.sku && p.sku.toLowerCase().includes(searchVal));
    });
    
    if (filtered.length === 0) {
        grid.innerHTML = `<div class="text-center text-muted col-span-2" style="padding: 40px; grid-column: span 100;">No se encontraron productos disponibles.</div>`;
        return;
    }
    
    filtered.forEach(p => {
        const isOutOfStock = p.stock <= 0;
        
        grid.innerHTML += `
            <div class="pos-card ${isOutOfStock ? 'out-of-stock' : ''}" onclick="${isOutOfStock ? '' : `addToCart(${p.id})`}">
                <div>
                    <div class="pos-prod-category">${escapeHtml(p.category_name || 'General')}</div>
                    <div class="pos-prod-name" title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</div>
                </div>
                <div class="pos-card-footer" style="flex-direction: column; align-items: flex-start; gap: 4px;">
                    <div class="pos-prod-price-dual" style="display: flex; flex-direction: column;">
                        <span class="pos-prod-price" style="font-size: 14.5px; color: #a5b4fc;">${formatBs(p.sale_price)}</span>
                        <span style="font-size: 12px; color: var(--text-muted); font-weight: 600;">${formatUsd(p.sale_price)}</span>
                    </div>
                    <span class="pos-prod-stock ${p.stock <= p.min_stock ? 'danger' : ''}" style="margin-top: 5px;">Stock: ${p.stock}</span>
                </div>
            </div>
        `;
    });
}

function filterPosCatalog() {
    renderPosCatalog();
}

function setPaymentMethod(method) {
    posPaymentMethod = method;
    
    const btnCash = document.getElementById("btn-pay-cash");
    const btnCredit = document.getElementById("btn-pay-credit");
    const debtorGroup = document.getElementById("pos-debtor-group");
    
    if (method === "credito") {
        btnCash.classList.remove("active");
        btnCredit.classList.add("active");
        debtorGroup.style.display = "block";
    } else {
        btnCash.classList.add("active");
        btnCredit.classList.remove("active");
        debtorGroup.style.display = "none";
    }
}

function calculateInitialPaymentBs() {
    const val = parseFloat(document.getElementById("pos-initial-payment").value) || 0;
    document.getElementById("pos-initial-payment-bs").textContent = `Equivale a: ${formatBs(val)}`;
}

function addToCart(id) {
    const p = productsList.find(item => item.id === id);
    if (!p || p.stock <= 0) return;
    
    // Buscar si ya está en el carrito
    const cartItem = cart.find(item => item.product_id === id);
    
    if (cartItem) {
        if (cartItem.quantity >= p.stock) {
            showToast(`Máximo stock disponible alcanzado para '${p.name}'`, "warning");
            return;
        }
        cartItem.quantity += 1;
    } else {
        cart.push({
            product_id: p.id,
            name: p.name,
            sale_price: p.sale_price, // guardado en USD
            stock: p.stock,
            quantity: 1
        });
    }
    
    renderCart();
}

function changeCartQty(productId, amount) {
    const cartItem = cart.find(item => item.product_id === productId);
    if (!cartItem) return;
    
    const newQty = cartItem.quantity + amount;
    
    if (newQty <= 0) {
        cart = cart.filter(item => item.product_id !== productId);
    } else {
        if (newQty > cartItem.stock) {
            showToast("No hay más stock disponible", "warning");
            return;
        }
        cartItem.quantity = newQty;
    }
    
    renderCart();
}

function clearCart() {
    cart = [];
    renderCart();
}

function renderCart() {
    const container = document.getElementById("cart-items-container");
    const subtotalEl = document.getElementById("cart-subtotal");
    const subtotalUsdEl = document.getElementById("cart-subtotal-usd");
    const totalEl = document.getElementById("cart-total");
    const totalUsdEl = document.getElementById("cart-total-usd");
    const btnCheckout = document.getElementById("btn-checkout");
    
    container.innerHTML = "";
    
    if (cart.length === 0) {
        container.innerHTML = `
            <div class="empty-cart-message">
                <svg viewBox="0 0 24 24" width="40" height="40" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                </svg>
                <p>El carrito está vacío. Agrega productos desde el catálogo de la izquierda.</p>
            </div>
        `;
        subtotalEl.textContent = "0.00 Bs.";
        subtotalUsdEl.textContent = "$0.00";
        totalEl.textContent = "0.00 Bs.";
        totalUsdEl.textContent = "$0.00";
        btnCheckout.disabled = true;
        return;
    }
    
    let totalUsd = 0.0;
    
    cart.forEach(item => {
        const itemSubtotalUsd = item.sale_price * item.quantity;
        totalUsd += itemSubtotalUsd;
        
        container.innerHTML += `
            <div class="cart-item">
                <div class="cart-item-header">
                    <span class="cart-item-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
                    <div class="totals-dual">
                        <span class="cart-item-subtotal">${formatBs(itemSubtotalUsd)}</span>
                        <span class="sub-tot">${formatUsd(itemSubtotalUsd)}</span>
                    </div>
                </div>
                <div class="cart-item-footer">
                    <span class="cart-item-price">${formatBs(item.sale_price)} c/u</span>
                    <div class="quantity-controls">
                        <button class="qty-btn" onclick="changeCartQty(${item.product_id}, -1)">-</button>
                        <span class="qty-val">${item.quantity}</span>
                        <button class="qty-btn" onclick="changeCartQty(${item.product_id}, 1)">+</button>
                    </div>
                </div>
            </div>
        `;
    });
    
    subtotalEl.textContent = formatBs(totalUsd);
    subtotalUsdEl.textContent = formatUsd(totalUsd);
    totalEl.textContent = formatBs(totalUsd);
    totalUsdEl.textContent = formatUsd(totalUsd);
    btnCheckout.disabled = false;
}

async function checkoutSale() {
    if (!pyApi || cart.length === 0) return;
    
    const checkoutItems = cart.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity
    }));
    
    const debtorSelect = document.getElementById("pos-debtor-select");
    const debtorInput = document.getElementById("pos-debtor-name");
    let debtorName = "";

    if (posPaymentMethod === 'credito') {
        if (debtorSelect && debtorSelect.value === '__new__') {
            debtorName = debtorInput.value.trim();
        } else if (debtorSelect && debtorSelect.value) {
            debtorName = debtorSelect.options[debtorSelect.selectedIndex].text;
        }

        if (!debtorName) {
            showToast("Para una venta a crédito, debes seleccionar o ingresar el nombre del deudor.", "danger");
            return;
        }

        if (debtorSelect && debtorSelect.value === '__new__' && debtorName) {
            const alreadyExists = customersList.some(c => c.name.toLowerCase() === debtorName.toLowerCase());
            if (!alreadyExists) {
                const customerResult = await pyApi.add_customer(debtorName, "");
                if (customerResult.success) {
                    showToast(`Deudor recurrente '${debtorName}' registrado exitosamente.`, "success");
                    await reloadCustomers();
                    debtorSelect.value = customerResult.id;
                    onCustomerSelectChange();
                }
            }
        }
    }

    let initialPaymentUsd = parseFloat(document.getElementById("pos-initial-payment").value) || 0.0;
    if (posPaymentMethod === 'credito' && posInitialCurrency === 'BS') {
        initialPaymentUsd = initialPaymentUsd / exchangeRate;
    }

    const payload = {
        items: checkoutItems,
        payment_status: posPaymentMethod,
        customer_name: posPaymentMethod === 'credito' ? debtorName : null,
        initial_payment: posPaymentMethod === 'credito' ? initialPaymentUsd : 0.0
    };
    
    btnCheckoutState(true);
    
    try {
        const res = await pyApi.register_sale(payload);
        
        if (res.success) {
            const displayTotal = formatBs(res.total);
            if (res.payment_status === 'contado') {
                showToast(`Venta #${res.sale_id} cobrada con éxito por ${displayTotal}`, "success");
            } else {
                showToast(`Venta a crédito #${res.sale_id} registrada con éxito para ${debtorName} por ${displayTotal}`, "success");
            }
            
            clearCart();
            await reloadProducts();
            await reloadSalesHistory();
            await reloadPendingCredits();
            renderPosCatalog();
        } else {
            showToast(res.error || "Error al procesar el cobro de la venta", "danger");
        }
    } catch (e) {
        showToast("Error inesperado en el servidor", "danger");
    } finally {
        btnCheckoutState(false);
    }
}

function btnCheckoutState(isLoading) {
    const btn = document.getElementById("btn-checkout");
    if (isLoading) {
        btn.disabled = true;
        btn.querySelector("span").textContent = "Procesando...";
    } else {
        btn.disabled = false;
        btn.querySelector("span").textContent = "Confirmar Cobro (Venta)";
    }
}

// ----------------- HISTORIAL DE VENTAS Y TRANSACCIONES -----------------
async function reloadSalesHistory() {
    if (!pyApi) return;
    salesHistoryList = await pyApi.get_sales_history();
    renderSalesHistoryTable();
}

function renderSalesHistoryTable() {
    const tbody = document.getElementById("sales-tbody");
    tbody.innerHTML = "";
    
    if (salesHistoryList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No se registran ventas históricas en el sistema.</td></tr>`;
        return;
    }
    
    salesHistoryList.forEach(sale => {
        let methodBadge = "";
        if (sale.payment_status === "credito") {
            methodBadge = `<span class="badge low-stock">Crédito</span>`;
        } else {
            methodBadge = `<span class="badge in-stock">Contado</span>`;
        }
        
        tbody.innerHTML += `
            <tr>
                <td style="font-weight: 700; color: var(--text-main);">#${sale.id}</td>
                <td>${formatDateString(sale.timestamp)}</td>
                <td class="text-center">${methodBadge}</td>
                <td class="text-muted" style="font-weight: 500;">${escapeHtml(sale.customer_name || 'Al Contado')}</td>
                <!-- Total Recaudado Dual -->
                <td class="text-right">
                    <span class="block-val" style="font-weight: 600; color: var(--success);">${formatBs(sale.total_amount)}</span>
                    <span class="block-val text-muted" style="font-size: 12px;">${formatUsd(sale.total_amount)}</span>
                </td>
                <!-- Costo Dual -->
                <td class="text-right text-muted">
                    <span class="block-val" style="font-size: 13px;">${formatBs(sale.total_cost)}</span>
                    <span class="block-val" style="font-size: 11px;">${formatUsd(sale.total_cost)}</span>
                </td>
                <!-- Ganancia Neta Dual -->
                <td class="text-right">
                    <span class="block-val" style="font-weight: 600; color: #a5b4fc;">${formatBs(sale.total_profit)}</span>
                    <span class="block-val text-muted" style="font-size: 12px;">${formatUsd(sale.total_profit)}</span>
                </td>
                <td class="text-center">
                    <button class="btn-icon edit" title="Ver Comprobante Detallado" onclick="viewSaleDetails(${sale.id})">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    </button>
                </td>
            </tr>
        `;
    });
}

async function viewSaleDetails(saleId) {
    if (!pyApi) return;
    
    const res = await pyApi.get_sale_details(saleId);
    if (!res.success) {
        showToast(res.error || "No se cargaron los detalles", "danger");
        return;
    }
    
    const sale = res.data;
    
    document.getElementById("sale-detail-title").textContent = `Detalle de Venta #${sale.id}`;
    document.getElementById("sale-det-date").textContent = formatDateString(sale.timestamp);
    document.getElementById("sale-det-total").innerHTML = `
        <span class="block-val">${formatBs(sale.total_amount)}</span>
        <span class="block-val text-muted" style="font-size:12px; font-weight:500;">${formatUsd(sale.total_amount)}</span>
    `;
    document.getElementById("sale-det-profit").innerHTML = `
        <span class="block-val">${formatBs(sale.total_profit)}</span>
        <span class="block-val text-muted" style="font-size:12px; font-weight:500;">${formatUsd(sale.total_profit)}</span>
    `;
    
    // Configurar estado
    const statusEl = document.getElementById("sale-det-status");
    statusEl.className = "badge";
    if (sale.payment_status === "credito") {
        statusEl.textContent = "Crédito Pendiente";
        statusEl.classList.add("low-stock");
        
        document.getElementById("sale-det-debtor-group").style.display = "block";
        document.getElementById("sale-det-paid-group").style.display = "block";
        document.getElementById("sale-det-debtor").textContent = sale.customer_name;
        document.getElementById("sale-det-paid").textContent = `${formatBs(sale.amount_paid)} (${formatUsd(sale.amount_paid)})`;
    } else {
        statusEl.textContent = sale.customer_name ? "Crédito Liquidado" : "Contado Pagado";
        statusEl.classList.add("in-stock");
        
        if (sale.customer_name) {
            document.getElementById("sale-det-debtor-group").style.display = "block";
            document.getElementById("sale-det-debtor").textContent = sale.customer_name;
        } else {
            document.getElementById("sale-det-debtor-group").style.display = "none";
        }
        document.getElementById("sale-det-paid-group").style.display = "none";
    }
    
    const tbody = document.getElementById("sale-detail-tbody");
    tbody.innerHTML = "";
    
    sale.items.forEach(item => {
        tbody.innerHTML += `
            <tr>
                <td style="font-weight: 600;">${escapeHtml(item.product_name || 'Producto Eliminado')}</td>
                <td class="text-muted" style="font-family: monospace;">${escapeHtml(item.product_sku || 'N/A')}</td>
                <td class="text-center">${item.quantity}</td>
                <!-- PVP Dual en Detalles -->
                <td class="text-right">
                    <span class="block-val" style="font-weight: 500;">${formatBs(item.sale_price)}</span>
                    <span class="block-val text-muted" style="font-size: 11px;">${formatUsd(item.sale_price)}</span>
                </td>
                <!-- Subtotal Dual -->
                <td class="text-right">
                    <span class="block-val" style="font-weight: 600;">${formatBs(item.subtotal)}</span>
                    <span class="block-val text-muted" style="font-size: 11.5px;">${formatUsd(item.subtotal)}</span>
                </td>
            </tr>
        `;
    });
    
    document.getElementById("sale-detail-modal").classList.add("active");
}

function closeSaleDetailModal() {
    document.getElementById("sale-detail-modal").classList.remove("active");
}

// ----------------- GESTIÓN DE CUENTAS POR COBRAR (CRÉDITOS) -----------------
async function reloadPendingCredits() {
    if (!pyApi) return;
    creditsList = await pyApi.get_debtor_accounts();
    updateSidebarCreditsBadge();
    renderCreditsTable();
}

function updateSidebarCreditsBadge() {
    const badge = document.getElementById("sidebar-credits-badge");
    if (!badge) return;
    
    if (creditsList.length > 0) {
        badge.textContent = creditsList.length;
        badge.style.display = "block";
    } else {
        badge.style.display = "none";
    }
}

function renderCreditsTable() {
    const tbody = document.getElementById("credits-tbody");
    tbody.innerHTML = "";
    
    if (creditsList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-success" style="padding: 30px; font-weight: 500;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 8px;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            ¡Felicitaciones! No posees deudas por cobrar pendientes en tu negocio.
        </td></tr>`;
        return;
    }
    
    creditsList.forEach(account => {
        const total = account.total_credit || 0;
        const paid = account.total_paid || 0;
        const remaining = account.total_remaining || 0;

        tbody.innerHTML += `
            <tr>
                <td style="font-weight: 600; color: var(--text-main);">${escapeHtml(account.customer_name)}</td>
                <td class="text-center">${account.num_invoices}</td>
                <td class="text-right">
                    <span class="block-val" style="font-weight: 600; color: var(--text-main);">${formatBs(total)}</span>
                    <span class="block-val text-muted" style="font-size:11.5px;">${formatUsd(total)}</span>
                </td>
                <td class="text-right">
                    <span class="block-val text-success" style="font-weight: 600;">${formatBs(paid)}</span>
                    <span class="block-val text-muted" style="font-size:11.5px;">${formatUsd(paid)}</span>
                </td>
                <td class="text-right">
                    <span class="block-val text-danger" style="font-weight: 700;">${formatBs(remaining)}</span>
                    <span class="block-val text-muted" style="font-size:12.5px; font-weight: 600;">${formatUsd(remaining)}</span>
                </td>
                <td class="text-center">
                    <button class="btn btn-outline-primary btn-sm" onclick="openDebtorDetailModal('${escapeQuote(account.customer_name)}')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="vertical-align: middle; margin-right:4px;"><path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                        Ver Cuenta
                    </button>
                </td>
            </tr>
        `;
    });
}

function openCreditPaymentModal(saleId, customer, remainingUsd) {
    document.getElementById("form-credit-sale-id").value = saleId;
    document.getElementById("form-credit-customer").textContent = customer;
    
    // Guardar saldo restante en dólares en el dataset del modal
    const remainingEl = document.getElementById("form-credit-remaining");
    remainingEl.textContent = `${formatBs(remainingUsd)} (${formatUsd(remainingUsd)})`;
    remainingEl.dataset.maxUsd = remainingUsd;
    
    document.getElementById("credit-payment-form").reset();
    document.getElementById("form-credit-payment-bs").textContent = "0.00 Bs.";
    
    document.getElementById("credit-payment-modal").classList.add("active");
}

function closeCreditPaymentModal() {
    document.getElementById("credit-payment-modal").classList.remove("active");
}

function calculateCreditPaymentBs() {
    const valUsd = parseFloat(document.getElementById("form-credit-payment-usd").value) || 0.0;
    const maxUsd = parseFloat(document.getElementById("form-credit-remaining").dataset.maxUsd) || 0.0;
    
    // Limitar al saldo restante por interfaz
    if (valUsd > maxUsd) {
        document.getElementById("form-credit-payment-usd").value = maxUsd.toFixed(2);
        document.getElementById("form-credit-payment-bs").textContent = formatBs(maxUsd);
    } else {
        document.getElementById("form-credit-payment-bs").textContent = formatBs(valUsd);
    }
}

async function saveCreditPayment(event) {
    event.preventDefault();
    if (!pyApi) return;
    
    const saleId = parseInt(document.getElementById("form-credit-sale-id").value);
    const amountUsd = parseFloat(document.getElementById("form-credit-payment-usd").value) || 0.0;
    
    if (amountUsd <= 0) {
        showToast("El monto del abono debe ser mayor a cero.", "danger");
        return;
    }
    
    try {
        const res = await pyApi.register_credit_payment(saleId, amountUsd);
        if (res.success) {
            if (res.liquidado) {
                showToast(`¡Crédito liquidado por completo! Se registró abono final de ${formatBs(res.abono_registrado)}.`, "success");
            } else {
                showToast(`Abono registrado con éxito por ${formatBs(res.abono_registrado)}. Restante: ${formatBs(res.deuda_restante)}.`, "success");
            }
            closeCreditPaymentModal();
            await reloadPendingCredits();
            await reloadSalesHistory();
            await updateDashboard();
        } else {
            showToast(res.error || "No se pudo registrar el abono", "danger");
        }
    } catch (e) {
        showToast("Error inesperado en el servidor", "danger");
    }
}

// ----------------- PANEL DE CONTROL (DASHBOARD) -----------------
async function updateDashboard() {
    if (!pyApi) return;
    
    const res = await pyApi.get_dashboard_stats();
    if (!res.success) return;
    
    const stats = res.data;
    
    // Sincronizar tasa de cambio local
    exchangeRate = stats.exchange_rate;
    updateExchangeRateUI();
    
    // Inyectar contadores principales en Bolívares y Dólares
    // Costo
    document.getElementById("stat-inv-cost").textContent = formatBs(stats.total_inventory_cost);
    document.getElementById("stat-inv-cost-usd").textContent = formatUsd(stats.total_inventory_cost);
    // Venta Proyectada
    document.getElementById("stat-inv-value").textContent = formatBs(stats.total_inventory_value);
    document.getElementById("stat-inv-value-usd").textContent = formatUsd(stats.total_inventory_value);
    // Ganancia
    document.getElementById("stat-inv-profit").textContent = formatBs(stats.projected_profit);
    document.getElementById("stat-inv-profit-usd").textContent = formatUsd(stats.projected_profit);
    // Cuentas por Cobrar (Deuda Activa)
    document.getElementById("stat-inv-credits").textContent = formatBs(stats.pending_credits_total);
    document.getElementById("stat-inv-credits-usd").textContent = `${formatUsd(stats.pending_credits_total)} de saldo pendiente`;
    
    // Stock Bajo
    const lowStockCount = stats.low_stock_alerts;
    const lowStockEl = document.getElementById("stat-low-stock");
    const lowStockDescEl = document.getElementById("stat-low-stock-desc");
    
    lowStockEl.textContent = lowStockCount;
    if (lowStockCount > 0) {
        lowStockEl.style.color = "var(--danger)";
        lowStockDescEl.textContent = `${lowStockCount} alertas críticas por reponer.`;
    } else {
        lowStockEl.style.color = "var(--success)";
        lowStockDescEl.textContent = "Excelente, inventario completo.";
    }
    
    // Valores consolidados de hoy
    document.getElementById("today-revenue").textContent = formatBs(stats.today_revenue);
    document.getElementById("today-revenue-usd").textContent = formatUsd(stats.today_revenue);
    document.getElementById("today-profit").textContent = formatBs(stats.today_profit);
    document.getElementById("today-profit-usd").textContent = formatUsd(stats.today_profit);
    
    // Categorías compactas
    const catListContainer = document.getElementById("dashboard-category-list");
    catListContainer.innerHTML = "";
    
    if (stats.category_distribution.length === 0) {
        catListContainer.innerHTML = `<div class="text-muted text-center" style="font-size: 13px;">No hay productos asignados.</div>`;
    } else {
        const topCats = stats.category_distribution.slice(0, 4);
        topCats.forEach(cat => {
            catListContainer.innerHTML += `
                <div class="category-compact-item">
                    <span class="cat-bullet">
                        <span class="cat-dot" style="background-color: ${getColorHash(cat.category_name || 'General')}"></span>
                        ${escapeHtml(cat.category_name || 'General')}
                    </span>
                    <span class="cat-count">${cat.product_count} prods (${cat.total_stock || 0} uds)</span>
                </div>
            `;
        });
    }
    
    // RENDERIZAR GRÁFICO SVG INTERACTIVO (DÓLARES COMO BASE DE AUDITORÍA)
    renderSvgDashboardChart(stats.recent_sales);
}

// DIBUJAR GRÁFICO SVG NATIVO PREMIUM (VALORES BASE EN USD)
function renderSvgDashboardChart(recentSales) {
    const container = document.getElementById("dashboard-chart-container");
    container.innerHTML = "";
    
    if (!recentSales || recentSales.length === 0) {
        container.innerHTML = `<div class="no-data-chart">No se registran ventas para los análisis financieros históricos.</div>`;
        return;
    }
    
    const width = 740;
    const height = 280;
    const paddingLeft = 60;
    const paddingRight = 30;
    const paddingTop = 30;
    const paddingBottom = 40;
    
    let maxAmount = 100.0;
    recentSales.forEach(s => {
        if (s.daily_revenue > maxAmount) maxAmount = s.daily_revenue;
        if (s.daily_profit > maxAmount) maxAmount = s.daily_profit;
    });
    
    maxAmount = Math.ceil(maxAmount * 1.15 / 50) * 50;
    
    const chartWidth = width - paddingLeft - paddingRight;
    const chartHeight = height - paddingTop - paddingBottom;
    
    const getX = (index) => paddingLeft + (index * (chartWidth / (recentSales.length - 1 || 1)));
    const getY = (amount) => paddingTop + chartHeight - (amount * (chartHeight / maxAmount));
    
    let svgContent = `<svg width="100%" height="100%" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" style="background: transparent;">
        <defs>
            <linearGradient id="gradientRevenue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="var(--primary)" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="var(--primary)" stop-opacity="0.0"/>
            </linearGradient>
            <linearGradient id="gradientProfit" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="var(--success)" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="var(--success)" stop-opacity="0.0"/>
            </linearGradient>
        </defs>
    `;
    
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
        const val = (maxAmount / gridLines) * i;
        const y = getY(val);
        svgContent += `
            <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" stroke="var(--border-color)" stroke-width="1" stroke-dasharray="4 4" />
            <text x="${paddingLeft - 10}" y="${y + 4}" fill="var(--text-dim)" font-size="11" font-weight="600" text-anchor="end">$${Math.round(val)}</text>
        `;
    }
    
    svgContent += `
        <line x1="${paddingLeft}" y1="${paddingTop + chartHeight}" x2="${width - paddingRight}" y2="${paddingTop + chartHeight}" stroke="var(--border-color)" stroke-width="1" />
        <line x1="${paddingLeft}" y1="${paddingTop}" x2="${paddingLeft}" y2="${paddingTop + chartHeight}" stroke="var(--border-color)" stroke-width="1" />
    `;
    
    let revenuePathPoints = [];
    let profitPathPoints = [];
    let labelsSvg = "";
    let dotsSvg = "";
    
    recentSales.forEach((s, idx) => {
        const x = getX(idx);
        const yRev = getY(s.daily_revenue);
        const yProf = getY(s.daily_profit);
        
        revenuePathPoints.push(`${x},${yRev}`);
        profitPathPoints.push(`${x},${yProf}`);
        
        const dateObj = new Date(s.sale_date + 'T00:00:00');
        const formattedDate = dateObj.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
        
        labelsSvg += `
            <text x="${x}" y="${paddingTop + chartHeight + 22}" fill="var(--text-muted)" font-size="12" font-weight="600" text-anchor="middle">${formattedDate}</text>
        `;
        
        dotsSvg += `
            <circle cx="${x}" cy="${yRev}" r="5" fill="var(--bg-surface)" stroke="var(--primary)" stroke-width="3" />
            <text x="${x}" y="${yRev - 12}" fill="var(--text-main)" font-size="10.5" font-weight="700" text-anchor="middle">$${s.daily_revenue.toFixed(0)}</text>
            <circle cx="${x}" cy="${yProf}" r="4" fill="var(--bg-surface)" stroke="var(--success)" stroke-width="2.5" />
        `;
    });
    
    const revPath = "M " + revenuePathPoints.join(" L ");
    const profPath = "M " + profitPathPoints.join(" L ");
    
    const revAreaPath = `${revPath} L ${getX(recentSales.length - 1)},${paddingTop + chartHeight} L ${getX(0)},${paddingTop + chartHeight} Z`;
    const profAreaPath = `${profPath} L ${getX(recentSales.length - 1)},${paddingTop + chartHeight} L ${getX(0)},${paddingTop + chartHeight} Z`;
    
    svgContent += `<path d="${revAreaPath}" fill="url(#gradientRevenue)" />`;
    svgContent += `<path d="${profAreaPath}" fill="url(#gradientProfit)" />`;
    
    svgContent += `<path d="${revPath}" fill="none" stroke="var(--primary)" stroke-width="3" stroke-linecap="round" />`;
    svgContent += `<path d="${profPath}" fill="none" stroke="var(--success)" stroke-width="2.5" stroke-linecap="round" />`;
    
    svgContent += labelsSvg;
    svgContent += dotsSvg;
    
    svgContent += `
        <g transform="translate(${width - 240}, 10)">
            <rect x="0" y="0" width="12" height="12" rx="3" fill="var(--primary)" />
            <text x="20" y="10" fill="var(--text-muted)" font-size="12" font-weight="600">Ingresos ($)</text>
            <rect x="130" y="0" width="12" height="12" rx="3" fill="var(--success)" />
            <text x="150" y="10" fill="var(--text-muted)" font-size="12" font-weight="600">Utilidad ($)</text>
        </g>
    `;
    
    svgContent += `</svg>`;
    
    container.innerHTML = svgContent;
}

// ----------------- SINCRONIZACIÓN EN LA NUBE -----------------
async function loadCloudConfig() {
    if (!pyApi || !pyApi.get_cloud_config) return;
    try {
        const res = await pyApi.get_cloud_config();
        if (!res.success) return;
        const data = res.data;
        document.getElementById("cloud-mode").value = data.mode || "local";
        document.getElementById("cloud-api-url").value = data.api_url || "";
        document.getElementById("cloud-api-key-hint").textContent = data.api_key_set
            ? "Ya hay una clave guardada. Déjala en blanco para conservarla."
            : "Introduce la clave definida en el servidor (STOCKVIBE_API_KEY).";
    } catch (e) {
        console.warn("No se pudo cargar la config de nube", e);
    }
}

async function saveCloudConfig(event) {
    event.preventDefault();
    if (!pyApi || !pyApi.save_cloud_config) return;

    const payload = {
        mode: document.getElementById("cloud-mode").value,
        api_url: document.getElementById("cloud-api-url").value.trim(),
    };
    const apiKey = document.getElementById("cloud-api-key").value.trim();
    if (apiKey) payload.api_key = apiKey;

    try {
        const res = await pyApi.save_cloud_config(payload);
        if (res.success) {
            showToast(res.message || "Configuración guardada.", "success");
            loadCloudConfig();
        } else {
            showToast(res.error || "No se pudo guardar.", "danger");
        }
    } catch (e) {
        showToast("Error al guardar la configuración.", "danger");
    }
}

async function testCloudConnection() {
    if (!pyApi || !pyApi.test_cloud_connection) return;
    const payload = {
        api_url: document.getElementById("cloud-api-url").value.trim(),
    };
    const apiKey = document.getElementById("cloud-api-key").value.trim();
    if (apiKey) payload.api_key = apiKey;
    try {
        const res = await pyApi.test_cloud_connection(payload);
        showToast(res.success ? (res.message || "Conexión OK") : (res.error || "Falló la conexión"), res.success ? "success" : "danger");
    } catch (e) {
        showToast("Error al probar la conexión.", "danger");
    }
}

// ----------------- EDICIÓN DE TASA DE CAMBIO -----------------
async function saveExchangeRate(event) {
    event.preventDefault();
    if (!pyApi) return;
    
    const newRate = parseFloat(document.getElementById("form-settings-exchange-rate").value) || 0.0;
    
    if (newRate <= 0) {
        showToast("La tasa de cambio debe ser mayor a 0.", "danger");
        return;
    }
    
    try {
        const res = await pyApi.update_exchange_rate(newRate);
        if (res.success) {
            showToast(`¡Tasa de cambio actualizada con éxito a ${newRate.toFixed(2)} Bs/$!`, "success");
            exchangeRate = res.exchange_rate;
            
            // Re-renderizar dinámicamente toda la UI en base a la nueva tasa
            updateExchangeRateUI();
            await updateDashboard();
            
            if (document.getElementById("section-inventory").classList.contains("active")) {
                renderProductsTable();
            }
            if (document.getElementById("section-pos").classList.contains("active")) {
                renderPosCatalog();
                renderCart();
            }
            if (document.getElementById("section-history").classList.contains("active")) {
                renderSalesHistoryTable();
            }
            if (document.getElementById("section-credits").classList.contains("active")) {
                renderCreditsTable();
            }
        } else {
            showToast(res.error || "No se pudo actualizar la tasa", "danger");
        }
    } catch (e) {
        showToast("Error inesperado en el servidor", "danger");
    }
}

// ----------------- EXPORTACIÓN E IMPORTACIÓN CSV -----------------
async function exportCSV() {
    if (!pyApi) return;
    showToast("Abriendo diálogo para exportar...", "warning");
    const res = await pyApi.export_inventory();
    if (res.success) {
        showToast(res.message, "success");
    } else {
        if (res.error !== "Operación cancelada por el usuario.") {
            showToast(res.error || "Ocurrió un error al exportar", "danger");
        } else {
            showToast("Exportación cancelada", "warning");
        }
    }
}

async function importCSV() {
    if (!pyApi) return;
    showToast("Abriendo selector de archivos CSV...", "warning");
    const res = await pyApi.import_inventory();
    if (res.success) {
        showToast(res.message, "success");
        await loadAllData();
        switchTab('inventory');
    } else {
        if (res.error !== "Operación cancelada por el usuario.") {
            showToast(res.error || "Ocurrió un error al importar", "danger");
        } else {
            showToast("Importación cancelada", "warning");
        }
    }
}

// ----------------- UTILIDADES DE FORMATOS Y ESTÉTICA -----------------
function escapeHtml(text) {
    if (!text) return "";
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, function(m) { return map[m]; });
}

function escapeQuote(text) {
    if (!text) return "";
    return text.toString().replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}

function getColorHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash % 360);
    return `hsl(${hue}, 65%, 60%)`;
}

function formatDateString(dateStr) {
    if (!dateStr) return "";
    try {
        const parts = dateStr.split(" ");
        const dateParts = parts[0].split("-");
        const timeParts = parts[1].split(":");
        
        let hr = parseInt(timeParts[0]);
        const ampm = hr >= 12 ? 'pm' : 'am';
        hr = hr % 12;
        hr = hr ? hr : 12;
        const min = timeParts[1];
        
        return `${dateParts[2]}/${dateParts[1]}/${dateParts[0]} ${hr}:${min} ${ampm}`;
    } catch (e) {
        return dateStr;
    }
}

// SISTEMA FLUIDO DE TOAST NOTIFICATIONS
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let icon = "";
    if (type === "success") {
        icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (type === "danger") {
        icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
    } else {
        icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }
    
    toast.innerHTML = `
        ${icon}
        <span>${escapeHtml(message)}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = "slideIn 0.3s ease-in reverse forwards";
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3500);
}
