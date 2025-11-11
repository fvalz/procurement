import streamlit as st
import pandas as pd
from modules.data_loader import DataLoader
from modules.classifier import SimpleClassifier
from modules.supplier_matcher import SupplierMatcher
from modules.pdf_generator import PDFGenerator
from modules.auto_reorder import AutoReorderSystem
import uuid
from datetime import datetime, timedelta
import os

# Konfiguracja strony
st.set_page_config(
    page_title="AI Procurement System",
    page_icon="🏢",
    layout="wide"
)

# Inicjalizacja
@st.cache_resource
def init_system():
    data_loader = DataLoader('data')
    if data_loader.load_all_data():
        classifier = SimpleClassifier(data_loader.products)
        matcher = SupplierMatcher(data_loader.suppliers, data_loader.purchase_orders)
        pdf_generator = PDFGenerator()
        auto_reorder = AutoReorderSystem(data_loader, matcher, pdf_generator)
        return data_loader, classifier, matcher, pdf_generator, auto_reorder
    return None, None, None, None, None

data_loader, classifier, matcher, pdf_generator, auto_reorder = init_system()

if data_loader is None:
    st.error("❌ Błąd ładowania danych! Sprawdź pliki CSV w folderze 'data/'")
    st.stop()

# Interfejs użytkownika
st.title("🏢 AI Procurement System")
st.markdown("### System automatycznego zarządzania zamówieniami")

# Debug info w sidebar
st.sidebar.header("🔍 Debug Info")
if st.sidebar.button("Wyczyść debug"):
    if 'debug_info' in st.session_state:
        del st.session_state.debug_info

# Zakładki
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 Złóż zapotrzebowanie", "📑 Umowy terminowe", "📊 Stany magazynowe", "🏭 Zamówienia produkcyjne", "🚚 W Dostawie", "📦 Historia zamówień"])

with tab1:
    st.header("Złóż nowe zapotrzebowanie")
    
    user_input = st.text_area(
        "Opisz czego potrzebujesz:",
        placeholder="np. 'Potrzebuję 2 szt. Siemens Motors 957 dla produkcji'",
        height=100
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        order_type = st.radio("Typ zamówienia:", ["Standardowe", "Produkcyjne"])
    
    with col2:
        if st.button("🔍 Sprawdź dostawcę", type="primary", use_container_width=True):
            if user_input.strip():
                with st.spinner("Analizuję zapytanie..."):
                    # Klasyfikacja
                    classification = classifier.classify_request(user_input)
                    
                    # Debug: zapisz informacje o klasyfikacji
                    st.session_state.debug_info = {
                        'user_input': user_input,
                        'classification': classification,
                        'products_in_db': len(data_loader.products) if data_loader.products is not None else 0
                    }
                    
                    # Wyszukiwanie dostawcy
                    supplier_result = matcher.find_supplier_in_contracts(
                        classification.get('product_name'), 
                        classification.get('category')
                    )
                    
                    # Debug: dodaj informacje o dostawcy
                    if 'debug_info' in st.session_state:
                        st.session_state.debug_info['supplier_result'] = supplier_result
                    
                    # Zapisz wyniki w sesji
                    st.session_state.classification = classification
                    st.session_state.supplier_result = supplier_result
                    st.session_state.user_input = user_input
            else:
                st.warning("Wpisz opis potrzebnego produktu")

    # Wyświetl debug info w sidebar
    if 'debug_info' in st.session_state:
        st.sidebar.subheader("Ostatnie zapytanie")
        st.sidebar.write(f"**Wejście:** {st.session_state.debug_info.get('user_input')}")
        st.sidebar.write(f"**Produkty w DB:** {st.session_state.debug_info.get('products_in_db')}")
        st.sidebar.write("**Klasyfikacja:**", st.session_state.debug_info.get('classification'))
        st.sidebar.write("**Dostawca:**", st.session_state.debug_info.get('supplier_result'))

    # Wyświetl wyniki jeśli są
    if 'classification' in st.session_state:
        st.divider()
        st.subheader("Wynik wyszukiwania")
        
        classification = st.session_state.classification
        supplier_result = st.session_state.supplier_result
        
        # Informacje o produkcie
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📦 Znaleziony produkt:**")
            if classification.get('found_in_catalog', False):
                product_name = classification.get('product_name', 'Nieznany produkt')
                st.success(f"✅ {product_name}")
                st.info(f"Kategoria: {classification.get('category', 'Inne')}")
                st.info(f"Ilość: {classification.get('quantity', 1)} {classification.get('unit', 'szt.')}")
                st.info(f"ID produktu: {classification.get('product_id', 'Brak')}")
            else:
                st.warning("❌ Produkt nieznany w katalogu")
                st.info(f"Przypisana kategoria: {classification.get('category', 'Inne')}")
                st.info(f"Zaufanie: {classification.get('confidence', 0)}")
                
                # Pokaż sugestie produktów z bazy
                if data_loader.products is not None:
                    st.markdown("**📋 Dostępne produkty w bazie:**")
                    product_samples = data_loader.products.head(5)[['Product_ID', 'Product_Name', 'Category']]
                    for _, product in product_samples.iterrows():
                        st.write(f"- {product['Product_Name']} ({product['Category']})")
        
        with col2:
            st.markdown("**🏢 Dostawca:**")
            if supplier_result.get('found', False):
                st.success("✅ Znaleziono w umowie terminowej!")
                st.info(f"Dostawca: {supplier_result.get('supplier_name', 'Nieznany dostawca')}")
                st.info(f"Cena: {supplier_result.get('price', 0.0)} PLN")
                st.info(f"Dostawa: {supplier_result.get('delivery_time', 'Nieokreślony')}")
                if supplier_result.get('match_confidence'):
                    st.info(f"Zaufanie dopasowania: {supplier_result.get('match_confidence')}")
                
                # Przycisk zatwierdzenia
                if st.button("✅ Zatwierdź zamówienie", type="primary", key="approve_order"):
                    # Sprawdź czy product_name jest dostępne
                    product_name = classification.get('product_name')
                    if not product_name:
                        st.error("❌ Nie można utworzyć zamówienia: brak nazwy produktu!")
                    else:
                        # Generuj zamówienie
                        estimated_delivery = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                        order_data = {
                            'order_id': f"ORD-{uuid.uuid4().hex[:8].upper()}",
                            'user_input': st.session_state.user_input,
                            'product_name': product_name,
                            'category': classification.get('category', 'Inne'),
                            'quantity': classification.get('quantity', 1),
                            'unit': classification.get('unit', 'szt.'),
                            'supplier_name': supplier_result.get('supplier_name', 'Nieznany dostawca'),
                            'price': supplier_result.get('price', 0.0),
                            'contract_type': supplier_result.get('contract_type', 'oferta'),
                            'order_type': order_type,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'estimated_delivery': estimated_delivery,
                            'delivery_status': 'ordered'
                        }
                        
                        # Generuj PDF
                        try:
                            pdf_path = pdf_generator.generate_order_pdf(order_data)
                            
                            # Zapisz zamówienie
                            success = data_loader.save_order(order_data)
                            
                            if success:
                                st.success(f"📄 Zamówienie zatwierdzone! Wygenerowano: {pdf_path}")
                                st.balloons()
                                
                                # Wyczyść stan sesji po udanym zamówieniu
                                if 'classification' in st.session_state:
                                    del st.session_state.classification
                                if 'supplier_result' in st.session_state:
                                    del st.session_state.supplier_result
                                if 'user_input' in st.session_state:
                                    del st.session_state.user_input
                                
                                # Odśwież stronę aby zobaczyć nowe zamówienie
                                st.rerun()
                            else:
                                st.error("❌ Błąd zapisywania zamówienia!")
                        except Exception as e:
                            st.error(f"❌ Błąd generowania PDF: {e}")
            else:
                st.warning("❌ Brak dostawcy w umowach terminowych")
                if supplier_result.get('error'):
                    st.error(f"Błąd: {supplier_result.get('error')}")
                
                # Pokaz podobne produkty
                similar = matcher.find_similar_products(
                    classification.get('product_name'),
                    classification.get('category')
                )
                
                if similar:
                    st.markdown("**💡 Podobne produkty w systemie:**")
                    for product in similar:
                        st.write(f"- {product.get('product_name', 'Nieznany')} (dopasowanie: {product.get('similarity_score', 0)})")
                
                # Tryb ofertowy
                st.markdown("**📄 Tryb ofertowy:**")
                uploaded_file = st.file_uploader("Prześlij ofertę PDF", type='pdf')
                if uploaded_file and st.button("🔄 Utwórz zamówienie z oferty"):
                    st.info("📝 Tworzę zamówienie na podstawie oferty...")
                    # Tutaj dodamy parsowanie PDF

with tab2:
    st.header("Umowy terminowe")
    
    contracts = data_loader.get_contracts()
    if not contracts.empty:
        st.dataframe(
            contracts[['Supplier', 'Product_Name', 'Category1', 'Unit_Price', 'Currency']],
            use_container_width=True
        )
    else:
        st.info("Brak umów terminowych w systemie")

with tab3:
    st.header("📊 Stany magazynowe")
    
    if data_loader.inventory is not None and not data_loader.inventory.empty:
        # Filtrowanie i sortowanie
        col1, col2 = st.columns(2)
        with col1:
            low_stock_only = st.checkbox("Pokaż tylko niskie stany", value=True)
        with col2:
            sort_by = st.selectbox("Sortuj według:", ["Product_Name", "Stock", "Min_stock_level"])
        
        # Filtruj dane
        inventory_display = data_loader.inventory.copy()
        if low_stock_only:
            inventory_display = inventory_display[inventory_display['Stock'] <= inventory_display['Min_stock_level']]
        
        # Sortuj dane
        inventory_display = inventory_display.sort_values(by=sort_by)
        
        # Wyświetl stan magazynowy z kolorowaniem
        st.dataframe(
            inventory_display[['Product_ID', 'Product_Name', 'Stock', 'Min_stock_level', 'Unit']],
            use_container_width=True
        )
        
        # Statystyki
        col1, col2, col3 = st.columns(3)
        with col1:
            total_products = len(data_loader.inventory)
            st.metric("Łączna liczba produktów", total_products)
        with col2:
            low_stock_count = len(data_loader.inventory[data_loader.inventory['Stock'] <= data_loader.inventory['Min_stock_level']])
            st.metric("Produkty z niskim stanem", low_stock_count)
        with col3:
            critical_count = len(data_loader.inventory[data_loader.inventory['Stock'] <= data_loader.inventory['Min_stock_level'] * 0.5])
            st.metric("Produkty krytyczne", critical_count, delta=f"-{critical_count}", delta_color="inverse")
    else:
        st.info("Brak danych magazynowych")

with tab4:
    st.header("🏭 Zamówienia produkcyjne")
    
    st.markdown("### Automatyczne zamówienia dla produkcji")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Sprawdź potrzeby produkcyjne", type="primary", use_container_width=True):
            with st.spinner("Analizuję stany magazynowe..."):
                production_orders = auto_reorder.check_production_needs()
                st.session_state.production_orders = production_orders
    
    with col2:
        auto_reorder_enabled = st.checkbox("Włącz automatyczne zamawianie", value=False)
        if auto_reorder_enabled:
            st.info("🔄 System automatycznie utworzy zamówienia dla produktów z niskim stanem")
    
    # Wyświetl wyniki jeśli są
    if 'production_orders' in st.session_state:
        production_orders = st.session_state.production_orders
        
        if production_orders:
            st.success(f"📋 Znaleziono {len(production_orders)} produktów do zamówienia")
            
            for i, order in enumerate(production_orders):
                with st.expander(f"📦 {order['product_name']} (Stan: {order['current_stock']}/{order['min_stock']})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"**Produkt:** {order['product_name']}")
                        st.info(f"**Aktualny stan:** {order['current_stock']} {order['unit']}")
                        st.info(f"**Minimalny stan:** {order['min_stock']} {order['unit']}")
                        st.info(f"**Proponowana ilość:** {order['suggested_quantity']} {order['unit']}")
                        st.info(f"**Przewidywana dostawa:** {order.get('estimated_delivery', 'Nieokreślona')}")
                    
                    with col2:
                        if order.get('supplier_found'):
                            st.success("✅ Znaleziono dostawcę")
                            st.info(f"**Dostawca:** {order['supplier_name']}")
                            st.info(f"**Cena:** {order['price']} PLN")
                            st.info(f"**Dostawa:** {order['delivery_time']}")
                            
                            if st.button(f"📝 Utwórz zamówienie", key=f"prod_order_{i}"):
                                # Generuj zamówienie produkcyjne
                                order_data = {
                                    'order_id': f"PROD-{uuid.uuid4().hex[:8].upper()}",
                                    'user_input': f"Automatyczne zamówienie produkcyjne - {order['product_name']}",
                                    'product_name': order['product_name'],
                                    'product_id': order['product_id'],
                                    'category': order['category'],
                                    'quantity': order['suggested_quantity'],
                                    'unit': order['unit'],
                                    'supplier_name': order['supplier_name'],
                                    'price': order['price'],
                                    'contract_type': order['contract_type'],
                                    'order_type': 'Produkcyjne',
                                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'estimated_delivery': order.get('estimated_delivery'),
                                    'delivery_status': 'ordered'
                                }
                                
                                # Generuj PDF
                                pdf_path = pdf_generator.generate_order_pdf(order_data)
                                
                                # Zapisz zamówienie
                                success = data_loader.save_order(order_data)
                                
                                if success:
                                    st.success(f"📄 Zamówienie produkcyjne utworzone! Wygenerowano: {pdf_path}")
                                    
                                    # Odśwież stronę
                                    st.rerun()
                                else:
                                    st.error("❌ Błąd zapisywania zamówienia!")
                        else:
                            st.warning("❌ Nie znaleziono dostawcy")
                            st.info(f"**Powód:** {order.get('error', 'Nieznany błąd')}")
        else:
            st.info("✅ Wszystkie produkty mają wystarczające stany magazynowe")

with tab5:
    st.header("🚚 Zamówienia w Dostawie")
    
    # Pobierz zamówienia w dostawie
    delivery_orders = data_loader.get_orders_in_delivery()
    
    if not delivery_orders.empty:
        st.success(f"📦 Znaleziono {len(delivery_orders)} zamówień w dostawie")
        
        # Filtry
        col1, col2 = st.columns(2)
        with col1:
            show_overdue = st.checkbox("Pokaż tylko przeterminowane", value=False)
        with col2:
            order_type_filter = st.selectbox("Filtruj typ zamówienia:", ["Wszystkie", "Standardowe", "Produkcyjne"])
        
        # Filtruj dane
        filtered_orders = delivery_orders.copy()
        
        if show_overdue:
            today = datetime.now().strftime("%Y-%m-%d")
            filtered_orders = filtered_orders[filtered_orders['estimated_delivery'] < today]
        
        if order_type_filter != "Wszystkie":
            filtered_orders = filtered_orders[filtered_orders['order_type'] == order_type_filter]
        
        # Wyświetl zamówienia
        for _, order in filtered_orders.iterrows():
            with st.expander(f"📦 {order['product_name']} - {order['order_id']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.info(f"**Zamówienie:** {order['order_id']}")
                    st.info(f"**Produkt:** {order['product_name']}")
                    st.info(f"**Ilość:** {order['quantity']} {order.get('unit', 'szt.')}")
                    st.info(f"**Dostawca:** {order['supplier_name']}")
                
                with col2:
                    st.info(f"**Typ:** {order['order_type']}")
                    st.info(f"**Status:** {order['delivery_status']}")
                    st.info(f"**Data zamówienia:** {order['timestamp']}")
                    
                    # Sprawdź czy dostawa jest przeterminowana
                    estimated_delivery = order.get('estimated_delivery')
                    if estimated_delivery:
                        today = datetime.now().date()
                        delivery_date = datetime.strptime(estimated_delivery, "%Y-%m-%d").date()
                        days_remaining = (delivery_date - today).days
                        
                        if days_remaining < 0:
                            st.error(f"**Przewidywana dostawa:** {estimated_delivery} (⏰ {abs(days_remaining)} dni po terminie!)")
                        elif days_remaining == 0:
                            st.warning(f"**Przewidywana dostawa:** {estimated_delivery} (Dzisiaj!)")
                        else:
                            st.info(f"**Przewidywana dostawa:** {estimated_delivery} (za {days_remaining} dni)")
                
                with col3:
                    # Przyciski zarządzania dostawą
                    if order['delivery_status'] == 'ordered':
                        if st.button(f"🚚 Oznacz jako wysłane", key=f"ship_{order['order_id']}"):
                            data_loader.update_delivery_status(order['order_id'], 'in_transit')
                            st.rerun()
                    
                    if order['delivery_status'] == 'in_transit':
                        delivered_quantity = st.number_input(
                            f"Dostarczona ilość ({order['product_name']}):",
                            min_value=0,
                            max_value=int(order['quantity']),
                            value=int(order['quantity']),
                            key=f"qty_{order['order_id']}"
                        )
                        
                        if st.button(f"✅ Oznacz jako dostarczone", key=f"deliver_{order['order_id']}"):
                            data_loader.update_delivery_status(
                                order['order_id'], 
                                'delivered',
                                delivered_quantity
                            )
                            st.success(f"✅ Zamówienie {order['order_id']} oznaczone jako dostarczone!")
                            st.rerun()
        
        # Statystyki
        col1, col2, col3 = st.columns(3)
        with col1:
            total_in_delivery = len(delivery_orders)
            st.metric("Zamówienia w dostawie", total_in_delivery)
        with col2:
            overdue_count = len(delivery_orders[
                delivery_orders['estimated_delivery'] < datetime.now().strftime("%Y-%m-%d")
            ])
            st.metric("Zamówienia przeterminowane", overdue_count, delta=f"+{overdue_count}", delta_color="inverse")
        with col3:
            production_in_delivery = len(delivery_orders[delivery_orders['order_type'] == 'Produkcyjne'])
            st.metric("Zamówienia produkcyjne", production_in_delivery)
    else:
        st.info("📭 Brak zamówień w dostawie")

with tab6:
    st.header("📦 Historia zamówień")
    
    # Sprawdź czy plik orders.csv istnieje
    orders_file = 'data/orders.csv'
    if os.path.exists(orders_file):
        try:
            orders_df = pd.read_csv(orders_file)
            if not orders_df.empty:
                # Filtry
                col1, col2, col3 = st.columns(3)
                with col1:
                    filter_type = st.selectbox("Filtruj typ zamówienia:", ["Wszystkie", "Standardowe", "Produkcyjne"], key="history_filter")
                with col2:
                    filter_status = st.selectbox("Filtruj status:", ["Wszystkie", "ordered", "in_transit", "delivered"], key="status_filter")
                with col3:
                    show_last = st.slider("Pokaż ostatnie zamówienia:", 5, 50, 10, key="history_slider")
                
                # Filtruj dane
                orders_display = orders_df.copy()
                if filter_type != "Wszystkie":
                    orders_display = orders_display[orders_display['order_type'] == filter_type]
                
                if filter_status != "Wszystkie":
                    orders_display = orders_display[orders_display['delivery_status'] == filter_status]
                
                orders_display = orders_display.tail(show_last)
                
                st.dataframe(orders_display, use_container_width=True)
                
                # Statystyki
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_orders = len(orders_df)
                    st.metric("Łączna liczba zamówień", total_orders)
                with col2:
                    delivered_orders = len(orders_df[orders_df['delivery_status'] == 'delivered'])
                    st.metric("Dostarczone zamówienia", delivered_orders)
                with col3:
                    if not orders_df.empty:
                        latest_order = orders_df.iloc[-1]
                        st.metric("Ostatnie zamówienie", latest_order['order_id'])
            else:
                st.info("Brak zamówień w historii")
        except Exception as e:
            st.error(f"Błąd ładowania historii zamówień: {e}")
    else:
        st.info("Brak zamówień w historii")

# Uruchomienie
if __name__ == "__main__":
    st.info("🚀 System gotowy do działania! Wpisz zapytanie w zakładce 'Złóż zapotrzebowanie'")