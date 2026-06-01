from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.metrics import dp
from kivy.clock import Clock
import data_access as database
import config

KV = """
#:import dp kivy.metrics.dp

<NavBar@BoxLayout>:
    size_hint_y: None
    height: dp(48)
    spacing: dp(4)
    padding: dp(4)
    canvas.before:
        Color:
            rgba: 0.06, 0.09, 0.17, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12, 12, 0, 0]

    Button:
        text: 'Dashboard'
        background_normal: ''
        background_color: (0.12, 0.46, 0.89, 1) if app.root.current == 'dashboard' else (0.18, 0.18, 0.28, 1)
        on_release: app.change_screen('dashboard')
    Button:
        text: 'Inventario'
        background_normal: ''
        background_color: (0.12, 0.46, 0.89, 1) if app.root.current == 'inventory' else (0.18, 0.18, 0.28, 1)
        on_release: app.change_screen('inventory')
    Button:
        text: 'Ventas'
        background_normal: ''
        background_color: (0.12, 0.46, 0.89, 1) if app.root.current == 'sales' else (0.18, 0.18, 0.28, 1)
        on_release: app.change_screen('sales')
    Button:
        text: 'Deudores'
        background_normal: ''
        background_color: (0.12, 0.46, 0.89, 1) if app.root.current == 'debtors' else (0.18, 0.18, 0.28, 1)
        on_release: app.change_screen('debtors')
    Button:
        text: 'Ajustes'
        background_normal: ''
        background_color: (0.12, 0.46, 0.89, 1) if app.root.current == 'settings' else (0.18, 0.18, 0.28, 1)
        on_release: app.change_screen('settings')

<ProductRow@Button>:
    product_id: 0
    text_size: self.width - dp(24), None
    valign: 'middle'
    halign: 'left'
    shorten: True
    padding: dp(10), dp(10)
    size_hint_y: None
    height: dp(72)
    background_normal: ''
    background_color: (0.12, 0.16, 0.26, 1)
    on_release: app.edit_product(self.product_id)

<DebtorRow@Button>:
    customer_name: ''
    text_size: self.width - dp(24), None
    valign: 'middle'
    halign: 'left'
    shorten: True
    padding: dp(10), dp(10)
    size_hint_y: None
    height: dp(72)
    background_normal: ''
    background_color: (0.14, 0.20, 0.30, 1)
    on_release: app.open_debtor_details(self.customer_name)

<CartRow@Button>:
    product_id: 0
    text_size: self.width - dp(24), None
    valign: 'middle'
    halign: 'left'
    shorten: True
    padding: dp(10), dp(10)
    size_hint_y: None
    height: dp(72)
    background_normal: ''
    background_color: (0.16, 0.22, 0.34, 1)
    on_release: app.remove_from_cart(self.product_id)

<SaleProductRow@Button>:
    product_id: 0
    text_size: self.width - dp(24), None
    valign: 'middle'
    halign: 'left'
    shorten: True
    padding: dp(10), dp(10)
    size_hint_y: None
    height: dp(72)
    background_normal: ''
    background_color: (0.10, 0.40, 0.10, 1)
    on_release: app.add_to_cart(self.product_id)

<InvoiceRow@Button>:
    sale_id: 0
    text_size: self.width - dp(24), None
    valign: 'middle'
    halign: 'left'
    shorten: True
    padding: dp(10), dp(10)
    size_hint_y: None
    height: dp(72)
    background_normal: ''
    background_color: (0.14, 0.12, 0.20, 1)
    on_release: app.select_debtor_invoice(self.sale_id)

<SaleHistoryRow@Button>:
    sale_id: 0
    text_size: self.width - dp(24), None
    valign: 'middle'
    halign: 'left'
    shorten: True
    padding: dp(10), dp(10)
    size_hint_y: None
    height: dp(72)
    background_normal: ''
    background_color: (0.18, 0.10, 0.10, 1)
    on_release: app.open_sale_history(self.sale_id)

ScreenManager:
    id: screen_manager

    Screen:
        name: 'dashboard'
        BoxLayout:
            orientation: 'vertical'
            NavBar:
                root_manager: root_manager
            BoxLayout:
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(12)
                Label:
                    text: 'StockVibe Mobile - Dashboard'
                    size_hint_y: None
                    height: dp(44)
                    bold: True
                    color: 1, 1, 1, 1
                GridLayout:
                    cols: 2
                    spacing: dp(10)
                    size_hint_y: None
                    height: dp(220)
                    BoxLayout:
                        orientation: 'vertical'
                        padding: dp(12)
                        canvas.before:
                            Color:
                                rgba: 0.10, 0.14, 0.24, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [16]
                        Label:
                            text: 'Productos registrados'
                            size_hint_y: None
                            height: dp(24)
                            color: 0.8, 0.8, 0.8, 1
                        Label:
                            text: str(app.dashboard_product_count)
                            font_size: '32sp'
                            bold: True
                            color: 1, 1, 1, 1
                    BoxLayout:
                        orientation: 'vertical'
                        padding: dp(12)
                        canvas.before:
                            Color:
                                rgba: 0.10, 0.14, 0.24, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [16]
                        Label:
                            text: 'Valor inventario (USD)'
                            size_hint_y: None
                            height: dp(24)
                            color: 0.8, 0.8, 0.8, 1
                        Label:
                            text: '$' + '{:.2f}'.format(app.dashboard_inventory_value)
                            font_size: '32sp'
                            bold: True
                            color: 1, 1, 1, 1
                    BoxLayout:
                        orientation: 'vertical'
                        padding: dp(12)
                        canvas.before:
                            Color:
                                rgba: 0.10, 0.14, 0.24, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [16]
                        Label:
                            text: 'Stock total'
                            size_hint_y: None
                            height: dp(24)
                            color: 0.8, 0.8, 0.8, 1
                        Label:
                            text: str(app.dashboard_total_stock)
                            font_size: '32sp'
                            bold: True
                            color: 1, 1, 1, 1
                    BoxLayout:
                        orientation: 'vertical'
                        padding: dp(12)
                        canvas.before:
                            Color:
                                rgba: 0.10, 0.14, 0.24, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [16]
                        Label:
                            text: 'Deudores activos'
                            size_hint_y: None
                            height: dp(24)
                            color: 0.8, 0.8, 0.8, 1
                        Label:
                            text: str(len(app.debtors))
                            font_size: '32sp'
                            bold: True
                            color: 1, 1, 1, 1
                Label:
                    text: 'Navega entre inventario, deudores y ajustes. El valor del inventario se calcula en USD y se puede llevar a Bs si lo necesitas.'
                    color: 0.8, 0.8, 0.8, 1
                    valign: 'top'
                    text_size: self.width, None
                    size_hint_y: None
                    height: dp(80)

    Screen:
        name: 'inventory'
        BoxLayout:
            orientation: 'vertical'
            NavBar:
                root_manager: root_manager
            BoxLayout:
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(10)
                BoxLayout:
                    size_hint_y: None
                    height: dp(44)
                    spacing: dp(6)
                    Button:
                        text: 'Nuevo Producto'
                        on_release: app.new_product()
                    Button:
                        text: 'Actualizar'
                        on_release: app.load_products()
                Label:
                    id: inventory_status
                    text: app.inventory_message
                    size_hint_y: None
                    height: dp(24)
                    color: 0.8, 0.8, 0.8, 1
                RecycleView:
                    id: products_rv
                    viewclass: 'ProductRow'
                    RecycleBoxLayout:
                        default_size: None, dp(72)
                        default_size_hint: 1, None
                        size_hint_y: None
                        height: self.minimum_height
                        orientation: 'vertical'

    Screen:
        name: 'sales'
        BoxLayout:
            orientation: 'vertical'
            NavBar:
                root_manager: root_manager
            ScrollView:
                do_scroll_x: False
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(12)
                    spacing: dp(10)
                    size_hint_y: None
                    height: self.minimum_height
                    Label:
                        text: 'Ventas'
                        size_hint_y: None
                        height: dp(40)
                        bold: True
                        color: 1, 1, 1, 1
                    BoxLayout:
                        orientation: 'horizontal'
                        spacing: dp(10)
                        size_hint_y: None
                        height: dp(44)
                        Spinner:
                            id: sale_payment_status_spinner
                            text: app.sale_payment_status
                            values: ['contado', 'credito']
                        TextInput:
                            id: sale_customer_name
                            hint_text: 'Cliente para crédito'
                            text: app.sale_customer_name
                            multiline: False
                        TextInput:
                            id: sale_initial_payment
                            hint_text: 'Abono inicial USD'
                            text: app.sale_initial_payment
                            multiline: False
                            input_filter: 'float'
                    Label:
                        text: app.sale_message
                        size_hint_y: None
                        height: dp(24)
                        color: 1, 0.6, 0.4, 1
                    Label:
                        text: 'Productos disponibles'
                        size_hint_y: None
                        height: dp(28)
                        bold: True
                        color: 0.9, 0.9, 0.9, 1
                    RecycleView:
                        id: sale_products_rv
                        viewclass: 'SaleProductRow'
                        RecycleBoxLayout:
                            default_size: None, dp(72)
                            default_size_hint: 1, None
                            size_hint_y: None
                            height: self.minimum_height
                            orientation: 'vertical'
                    Label:
                        text: 'Carrito'
                        size_hint_y: None
                        height: dp(28)
                        bold: True
                        color: 0.9, 0.9, 0.9, 1
                    RecycleView:
                        id: cart_rv
                        viewclass: 'CartRow'
                        RecycleBoxLayout:
                            default_size: None, dp(72)
                            default_size_hint: 1, None
                            size_hint_y: None
                            height: self.minimum_height
                            orientation: 'vertical'
                    BoxLayout:
                        orientation: 'horizontal'
                        spacing: dp(10)
                        size_hint_y: None
                        height: dp(44)
                        Label:
                            text: 'Total: $' + '{:.2f}'.format(app.sale_total)
                            color: 1, 1, 1, 1
                        Button:
                            text: 'Cobrar'
                            on_release: app.checkout_sale()
                        Button:
                            text: 'Limpiar carrito'
                            on_release: app.clear_cart()
                        Button:
                            text: 'Historial'
                            on_release: app.change_screen('sale_history')

    Screen:
        name: 'sale_history'
        BoxLayout:
            orientation: 'vertical'
            NavBar:
                root_manager: root_manager
            BoxLayout:
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(10)
                Label:
                    text: 'Historial de Ventas'
                    size_hint_y: None
                    height: dp(40)
                    bold: True
                    color: 1, 1, 1, 1
                RecycleView:
                    id: sales_history_rv
                    viewclass: 'SaleHistoryRow'
                    RecycleBoxLayout:
                        default_size: None, dp(72)
                        default_size_hint: 1, None
                        size_hint_y: None
                        height: self.minimum_height
                        orientation: 'vertical'
                Label:
                    text: app.sale_message
                    size_hint_y: None
                    height: dp(48)
                    color: 1, 0.6, 0.4, 1
                    text_size: self.width, None
                Button:
                    text: 'Volver'
                    size_hint_y: None
                    height: dp(44)
                    on_release: app.change_screen('sales')

    Screen:
        name: 'product_form'
        BoxLayout:
            orientation: 'vertical'
            NavBar:
                root_manager: root_manager
            ScrollView:
                do_scroll_x: False
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(12)
                    spacing: dp(12)
                    size_hint_y: None
                    height: self.minimum_height
                    Label:
                        text: 'Formulario de Producto'
                        size_hint_y: None
                        height: dp(40)
                        bold: True
                        color: 1, 1, 1, 1
                    GridLayout:
                        cols: 1
                        spacing: dp(10)
                        size_hint_y: None
                        height: self.minimum_height
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_y: None
                            height: dp(90)
                            Label:
                                text: 'Nombre'
                                size_hint_y: None
                                height: dp(20)
                                color: 0.8, 0.8, 0.8, 1
                            TextInput:
                                id: product_name
                                multiline: False
                                size_hint_y: None
                                height: dp(44)
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_y: None
                            height: dp(90)
                            Label:
                                text: 'SKU'
                                size_hint_y: None
                                height: dp(20)
                                color: 0.8, 0.8, 0.8, 1
                            TextInput:
                                id: product_sku
                                multiline: False
                                size_hint_y: None
                                height: dp(44)
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_y: None
                            height: dp(90)
                            Label:
                                text: 'Categoría'
                                size_hint_y: None
                                height: dp(20)
                                color: 0.8, 0.8, 0.8, 1
                            Spinner:
                                id: product_category
                                text: app.category_names[0] if app.category_names else 'General'
                                values: app.category_names
                                size_hint_y: None
                                height: dp(44)
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_y: None
                            height: dp(90)
                            Label:
                                text: 'Descripción'
                                size_hint_y: None
                                height: dp(20)
                                color: 0.8, 0.8, 0.8, 1
                            TextInput:
                                id: product_description
                                multiline: True
                                size_hint_y: None
                                height: dp(120)
                        BoxLayout:
                            orientation: 'horizontal'
                            spacing: dp(10)
                            size_hint_y: None
                            height: dp(90)
                            BoxLayout:
                                orientation: 'vertical'
                                Label:
                                    text: 'Costo USD'
                                    color: 0.8, 0.8, 0.8, 1
                                    size_hint_y: None
                                    height: dp(20)
                                TextInput:
                                    id: product_price_purchase
                                    multiline: False
                                    input_filter: 'float'
                                    size_hint_y: None
                                    height: dp(44)
                            BoxLayout:
                                orientation: 'vertical'
                                Label:
                                    text: 'Venta USD'
                                    color: 0.8, 0.8, 0.8, 1
                                    size_hint_y: None
                                    height: dp(20)
                                TextInput:
                                    id: product_price_sale
                                    multiline: False
                                    input_filter: 'float'
                                    size_hint_y: None
                                    height: dp(44)
                        BoxLayout:
                            orientation: 'horizontal'
                            spacing: dp(10)
                            size_hint_y: None
                            height: dp(90)
                            BoxLayout:
                                orientation: 'vertical'
                                Label:
                                    text: 'Stock'
                                    color: 0.8, 0.8, 0.8, 1
                                    size_hint_y: None
                                    height: dp(20)
                                TextInput:
                                    id: product_stock
                                    multiline: False
                                    input_filter: 'int'
                                    size_hint_y: None
                                    height: dp(44)
                            BoxLayout:
                                orientation: 'vertical'
                                Label:
                                    text: 'Stock mínimo'
                                    color: 0.8, 0.8, 0.8, 1
                                    size_hint_y: None
                                    height: dp(20)
                                TextInput:
                                    id: product_min_stock
                                    multiline: False
                                    input_filter: 'int'
                                    size_hint_y: None
                                    height: dp(44)
                        Label:
                            id: product_form_message
                            text: app.product_form_message
                            color: 1, 0.6, 0.4, 1
                            size_hint_y: None
                            height: dp(24)
                        BoxLayout:
                            size_hint_y: None
                            height: dp(48)
                            spacing: dp(10)
                            Button:
                                text: 'Guardar'
                                on_release: app.save_product()
                            Button:
                                text: 'Cancelar'
                                on_release: app.change_screen('inventory')

    Screen:
        name: 'debtors'
        BoxLayout:
            orientation: 'vertical'
            NavBar:
                root_manager: root_manager
            BoxLayout:
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(10)
                Button:
                    text: 'Actualizar deudores'
                    size_hint_y: None
                    height: dp(44)
                    on_release: app.load_debtors()
                RecycleView:
                    id: debtors_rv
                    viewclass: 'DebtorRow'
                    RecycleBoxLayout:
                        default_size: None, dp(72)
                        default_size_hint: 1, None
                        size_hint_y: None
                        height: self.minimum_height
                        orientation: 'vertical'

    Screen:
        name: 'debtor_detail'
        BoxLayout:
            orientation: 'vertical'
            NavBar:
                root_manager: root_manager
            BoxLayout:
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(10)
                Label:
                    id: debtor_detail_title
                    text: 'Detalle de Deudor'
                    size_hint_y: None
                    height: dp(32)
                    bold: True
                    color: 1, 1, 1, 1
                GridLayout:
                    cols: 2
                    spacing: dp(10)
                    size_hint_y: None
                    height: dp(100)
                    BoxLayout:
                        orientation: 'vertical'
                        Label:
                            text: 'Total Crédito'
                            color: 0.8, 0.8, 0.8, 1
                        Label:
                            id: debtor_total
                            text: '$0.00'
                            bold: True
                            color: 1, 1, 1, 1
                    BoxLayout:
                        orientation: 'vertical'
                        Label:
                            text: 'Abonado'
                            color: 0.8, 0.8, 0.8, 1
                        Label:
                            id: debtor_paid
                            text: '$0.00'
                            bold: True
                            color: 0.4, 1, 0.6, 1
                    BoxLayout:
                        orientation: 'vertical'
                        Label:
                            text: 'Restante'
                            color: 0.8, 0.8, 0.8, 1
                        Label:
                            id: debtor_remaining
                            text: '$0.00'
                            bold: True
                            color: 1, 0.4, 0.4, 1
                RecycleView:
                    id: debtor_invoices_rv
                    viewclass: 'InvoiceRow'
                    RecycleBoxLayout:
                        default_size: None, dp(64)
                        default_size_hint: 1, None
                        size_hint_y: None
                        height: self.minimum_height
                        orientation: 'vertical'
                Label:
                    text: 'Monto a abonar (USD)'
                    size_hint_y: None
                    height: dp(24)
                    color: 0.8, 0.8, 0.8, 1
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: dp(10)
                    size_hint_y: None
                    height: dp(44)
                    TextInput:
                        id: debtor_payment_amount
                        hint_text: 'USD'
                        text: app.debtor_payment_amount
                        multiline: False
                        input_filter: 'float'
                    Button:
                        text: 'Registrar abono'
                        on_release: app.register_debtor_payment()
                Label:
                    id: debtor_payment_message
                    text: app.debtor_payment_message
                    color: 1, 0.6, 0.4, 1
                    size_hint_y: None
                    height: dp(24)
                Button:
                    text: 'Volver'
                    size_hint_y: None
                    height: dp(44)
                    on_release: app.change_screen('debtors')

    Screen:
        name: 'settings'
        BoxLayout:
            orientation: 'vertical'
            NavBar:
                root_manager: root_manager
            BoxLayout:
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(10)
                Label:
                    text: 'Ajustes'
                    size_hint_y: None
                    height: dp(40)
                    bold: True
                    color: 1, 1, 1, 1
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: dp(10)
                    size_hint_y: None
                    height: dp(90)
                    BoxLayout:
                        orientation: 'vertical'
                        Label:
                            text: 'Tasa de Cambio (Bs/USD)'
                            color: 0.8, 0.8, 0.8, 1
                            size_hint_y: None
                            height: dp(24)
                        TextInput:
                            id: exchange_rate_input
                            text: str(app.exchange_rate)
                            multiline: False
                            input_filter: 'float'
                    Button:
                        text: 'Guardar tasa'
                        size_hint_x: None
                        width: dp(140)
                        on_release: app.save_exchange_rate()
                Label:
                    id: settings_message
                    text: app.settings_message
                    color: 1, 0.6, 0.4, 1
                    size_hint_y: None
                    height: dp(24)
"""

class StockVibeApp(App):
    categories = ListProperty([])
    products = ListProperty([])
    debtors = ListProperty([])
    invoice_rows = ListProperty([])
    category_names = ListProperty([])
    editing_product_id = NumericProperty(0)
    exchange_rate = NumericProperty(45.0)
    dashboard_product_count = NumericProperty(0)
    dashboard_inventory_value = NumericProperty(0.0)
    dashboard_total_stock = NumericProperty(0)
    inventory_message = StringProperty('')
    cart_items = ListProperty([])
    sale_message = StringProperty('')
    sale_payment_status = StringProperty('contado')
    sale_total = NumericProperty(0.0)
    sale_customer_name = StringProperty('')
    sale_initial_payment = StringProperty('0.0')
    selected_debtor_sale_id = NumericProperty(0)
    debtor_payment_amount = StringProperty('0.0')
    debtor_payment_message = StringProperty('')
    current_debtor_customer = StringProperty('')
    product_form_message = StringProperty('')
    settings_message = StringProperty('')

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        try:
            database.init_db()
        except Exception as e:
            if config.is_remote():
                self.settings_message = f'Sin conexión al servidor: {e}'
            else:
                raise
        if config.is_sync():
            Clock.schedule_interval(self._background_sync, 45)
        self.exchange_rate = database.get_exchange_rate()
        self.load_categories()
        self.load_products()
        self.load_debtors()
        self.update_dashboard()

    def _background_sync(self, _dt):
        if not config.is_sync():
            return
        try:
            import sync_engine
            sync_engine.sync_all(force_pull=True)
            screen = self.root.current
            if screen == 'inventory':
                self.load_products()
            elif screen == 'dashboard':
                self.update_dashboard()
            elif screen == 'debtors':
                self.load_debtors()
        except Exception:
            pass

    def change_screen(self, screen_name):
        self.root.current = screen_name
        if screen_name == 'dashboard':
            self.update_dashboard()
        elif screen_name == 'inventory':
            self.load_products()
        elif screen_name == 'sales':
            self.load_sale_products()
        elif screen_name == 'sale_history':
            self.load_sales_history()
        elif screen_name == 'debtors':
            self.load_debtors()
        elif screen_name == 'settings':
            self.settings_message = ''

    def load_categories(self):
        self.categories = database.get_categories()
        self.category_names = [cat['name'] for cat in self.categories] or ['General']
        if self.root and self.root.ids.get('product_category'):
            self.root.ids.product_category.text = self.category_names[0]

    def load_products(self):
        self.products = database.get_products()
        self.inventory_message = f'{len(self.products)} productos cargados.'
        items = []
        for product in self.products:
            label = f"{product['name']} ({product['category_name'] or 'Sin categoría'})\nStock: {product['stock']} · Compra ${product['purchase_price']:.2f} · Venta ${product['sale_price']:.2f}"
            items.append({'text': label, 'product_id': product['id']})
        if self.root and self.root.ids.get('products_rv'):
            self.root.ids.products_rv.data = items

    def load_debtors(self):
        self.debtors = database.get_debtor_accounts()
        items = []
        for account in self.debtors:
            label = f"{account['customer_name']}\nSaldo: ${account['total_remaining']:.2f} · Facturas: {account['num_invoices']}"
            items.append({'text': label, 'customer_name': account['customer_name']})
        if self.root and self.root.ids.get('debtors_rv'):
            self.root.ids.debtors_rv.data = items

    def load_sale_products(self):
        self.load_products()
        self.sale_payment_status = 'contado'
        self.sale_customer_name = ''
        self.sale_initial_payment = '0.0'
        items = []
        for product in self.products:
            label = f"{product['name']} ({product['category_name'] or 'Sin categoría'})\nStock: {product['stock']} · Venta ${product['sale_price']:.2f}"
            items.append({'text': label, 'product_id': product['id']})
        if self.root and self.root.ids.get('sale_products_rv'):
            self.root.ids.sale_products_rv.data = items
        self.update_cart_display()
        self.sale_message = ''

    def load_sales_history(self):
        history = database.get_sales_history()
        items = []
        for sale in history:
            customer = sale['customer_name'] or 'General'
            items.append({'text': f"Factura #{sale['id']} · {sale['timestamp']}\nTotal ${sale['total_amount']:.2f} · {sale['payment_status']} · {customer}", 'sale_id': sale['id']})
        if self.root and self.root.ids.get('sales_history_rv'):
            self.root.ids.sales_history_rv.data = items

    def open_sale_history(self, sale_id):
        sale = database.get_sale_details(sale_id)
        if not sale:
            self.sale_message = 'No se encontró la venta seleccionada.'
            return
        details = [f"{item['product_name']} x{item['quantity']} · ${item['sale_price']:.2f} = ${item['subtotal']:.2f}" for item in sale['items']]
        self.sale_message = f"Venta #{sale_id}: ${sale['total_amount']:.2f}. Items: {'; '.join(details)}"

    def select_debtor_invoice(self, sale_id):
        self.selected_debtor_sale_id = sale_id
        self.debtor_payment_message = f'Factura seleccionada #{sale_id}.'

    def register_debtor_payment(self):
        if self.selected_debtor_sale_id == 0:
            self.debtor_payment_message = 'Selecciona primero una factura pendiente.'
            return
        try:
            amount = float(self.root.ids.debtor_payment_amount.text or 0)
        except ValueError:
            self.debtor_payment_message = 'Monto de abono inválido.'
            return
        if amount <= 0:
            self.debtor_payment_message = 'El abono debe ser mayor a cero.'
            return

        result = database.register_credit_payment(self.selected_debtor_sale_id, amount)
        if result.get('success'):
            self.debtor_payment_message = f"Abono registrado: ${result['abono_registrado']:.2f}. Restante: ${result['deuda_restante']:.2f}."
            self.open_debtor_details(self.current_debtor_customer)
        else:
            self.debtor_payment_message = result.get('error', 'Error registrando el pago.')

    def add_to_cart(self, product_id):
        product = next((p for p in self.products if p['id'] == product_id), None)
        if not product:
            self.sale_message = 'Producto no encontrado.'
            return
        if product['stock'] <= 0:
            self.sale_message = f"'{product['name']}' no tiene stock disponible."
            return

        existing = next((item for item in self.cart_items if item['product_id'] == product_id), None)
        if existing:
            if existing['quantity'] >= product['stock']:
                self.sale_message = f"No puedes agregar más de '{product['name']}' al carrito."
                return
            existing['quantity'] += 1
        else:
            if not hasattr(self, 'cart_items'):
                self.cart_items = []
            self.cart_items.append({'product_id': product_id, 'quantity': 1, 'product_name': product['name'], 'sale_price': product['sale_price']})

        self.sale_message = f"Agregado '{product['name']}' al carrito."
        self.update_cart_display()

    def remove_from_cart(self, product_id):
        if not hasattr(self, 'cart_items'):
            self.cart_items = []
        self.cart_items = [item for item in self.cart_items if item['product_id'] != product_id]
        self.sale_message = 'Artículo eliminado del carrito.'
        self.update_cart_display()

    def clear_cart(self):
        self.cart_items = []
        self.sale_message = 'Carrito limpio.'
        self.update_cart_display()

    def update_cart_display(self):
        total = 0.0
        cart_data = []
        for item in getattr(self, 'cart_items', []):
            subtotal = item['sale_price'] * item['quantity']
            total += subtotal
            cart_data.append({'text': f"{item['product_name']} x{item['quantity']} · ${item['sale_price']:.2f} = ${subtotal:.2f}", 'product_id': item['product_id']})
        self.sale_total = total
        if self.root and self.root.ids.get('cart_rv'):
            self.root.ids.cart_rv.data = cart_data

    def checkout_sale(self):
        if not getattr(self, 'cart_items', []):
            self.sale_message = 'El carrito está vacío.'
            return

        payment_status = self.root.ids.sale_payment_status_spinner.text
        customer_name = self.root.ids.sale_customer_name.text.strip() if payment_status == 'credito' else None
        try:
            initial_payment = float(self.root.ids.sale_initial_payment.text or 0)
        except ValueError:
            self.sale_message = 'El abono inicial debe ser un número válido.'
            return

        if payment_status == 'credito' and not customer_name:
            self.sale_message = 'Ingresa el nombre del cliente para crédito.'
            return

        items = [{'product_id': item['product_id'], 'quantity': item['quantity']} for item in self.cart_items]
        result = database.register_sale(items, payment_status=payment_status, customer_name=customer_name, initial_payment=initial_payment)

        if result.get('success'):
            self.sale_message = f"Venta registrada. Total: ${result.get('total', 0):.2f}."
            self.clear_cart()
            self.load_products()
            self.load_debtors()
            self.update_dashboard()
        else:
            self.sale_message = result.get('error', 'Error registrando la venta.')

    def update_dashboard(self):
        self.dashboard_product_count = len(self.products)
        self.dashboard_inventory_value = sum(p['sale_price'] * p['stock'] for p in self.products)
        self.dashboard_total_stock = sum(p['stock'] for p in self.products)

    def new_product(self):
        self.editing_product_id = 0
        if self.root:
            self.root.ids.product_name.text = ''
            self.root.ids.product_sku.text = ''
            self.root.ids.product_description.text = ''
            self.root.ids.product_price_purchase.text = ''
            self.root.ids.product_price_sale.text = ''
            self.root.ids.product_stock.text = ''
            self.root.ids.product_min_stock.text = ''
            self.root.ids.product_form_message.text = ''
            self.root.ids.product_category.text = self.category_names[0] if self.category_names else 'General'
        self.change_screen('product_form')

    def edit_product(self, product_id):
        product = next((p for p in self.products if p['id'] == product_id), None)
        if not product:
            return
        self.editing_product_id = product_id
        self.root.ids.product_name.text = product['name']
        self.root.ids.product_sku.text = product['sku'] or ''
        self.root.ids.product_description.text = product['description'] or ''
        self.root.ids.product_price_purchase.text = f"{product['purchase_price']:.2f}"
        self.root.ids.product_price_sale.text = f"{product['sale_price']:.2f}"
        self.root.ids.product_stock.text = str(product['stock'])
        self.root.ids.product_min_stock.text = str(product['min_stock'])
        self.root.ids.product_category.text = product['category_name'] or (self.category_names[0] if self.category_names else 'General')
        self.root.ids.product_form_message.text = ''
        self.change_screen('product_form')

    def save_product(self):
        name = self.root.ids.product_name.text.strip()
        sku = self.root.ids.product_sku.text.strip()
        description = self.root.ids.product_description.text.strip()
        category_name = self.root.ids.product_category.text
        category_id = next((cat['id'] for cat in self.categories if cat['name'] == category_name), None)

        try:
            purchase_price = float(self.root.ids.product_price_purchase.text or 0)
            sale_price = float(self.root.ids.product_price_sale.text or 0)
            stock = int(self.root.ids.product_stock.text or 0)
            min_stock = int(self.root.ids.product_min_stock.text or 5)
        except ValueError:
            self.root.ids.product_form_message.text = 'Revisa los valores numéricos del formulario.'
            return

        if not name:
            self.root.ids.product_form_message.text = 'El nombre del producto es obligatorio.'
            return

        if purchase_price < 0 or sale_price < 0 or stock < 0 or min_stock < 0:
            self.root.ids.product_form_message.text = 'Los valores no pueden ser negativos.'
            return

        if self.editing_product_id:
            result = database.update_product(self.editing_product_id, name, sku, category_id, description, purchase_price, sale_price, stock, min_stock)
        else:
            result = database.add_product(name, sku, category_id, description, purchase_price, sale_price, stock, min_stock)

        if result.get('success'):
            self.load_products()
            self.update_dashboard()
            self.change_screen('inventory')
        else:
            self.root.ids.product_form_message.text = result.get('error', 'Error guardando el producto.')

    def open_debtor_details(self, customer_name):
        self.current_debtor_customer = customer_name
        self.selected_debtor_sale_id = 0
        self.debtor_payment_amount = '0.0'
        self.debtor_payment_message = ''
        details = database.get_debtor_details(customer_name)
        self.root.ids.debtor_detail_title.text = f'Deudor: {customer_name}'
        self.root.ids.debtor_total.text = f"${details['total_debt']:.2f}"
        self.root.ids.debtor_paid.text = f"${details['total_paid']:.2f}"
        self.root.ids.debtor_remaining.text = f"${details['total_remaining']:.2f}"

        invoices = []
        for invoice in details['invoices']:
            invoices.append({
                'text': f"Factura #{invoice['id']} · {invoice['timestamp']}\nTotal: ${invoice['total_amount']:.2f} · Pago: ${invoice['amount_paid']:.2f} · Restante: ${invoice['remaining']:.2f}",
                'sale_id': invoice['id']
            })
        self.root.ids.debtor_invoices_rv.data = invoices
        self.change_screen('debtor_detail')

    def save_exchange_rate(self):
        try:
            rate_value = float(self.root.ids.exchange_rate_input.text or 0)
        except ValueError:
            self.settings_message = 'Tasa de cambio inválida.'
            return

        result = database.update_exchange_rate(rate_value)
        if result.get('success'):
            self.exchange_rate = rate_value
            self.settings_message = 'Tasa actualizada correctamente.'
        else:
            self.settings_message = result.get('error', 'No se pudo actualizar la tasa.')

if __name__ == '__main__':
    StockVibeApp().run()
