import pandas as pd
import os
from datetime import datetime, timedelta

class DataLoader:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.products = None
        self.inventory = None
        self.suppliers = None
        self.purchase_orders = None
        self.user_requests = None
    
    def load_all_data(self):
        """Ładuje wszystkie pliki CSV"""
        try:
            # Ładuj produkty
            if os.path.exists(f'{self.data_dir}/products.csv'):
                self.products = pd.read_csv(f'{self.data_dir}/products.csv')
                print(f"✅ Załadowano produkty: {len(self.products)} rekordów")
            else:
                print("❌ Brak pliku products.csv")
                return False
            
            # Ładuj inventory i agreguj dane
            if os.path.exists(f'{self.data_dir}/inventory.csv'):
                inventory_raw = pd.read_csv(f'{self.data_dir}/inventory.csv')
                
                # Agreguj dane inventory - suma Stock i Closing_Stock dla każdego produktu
                if not inventory_raw.empty:
                    self.inventory = self._aggregate_inventory_data(inventory_raw)
                    print(f"✅ Załadowano i zagregowano inventory: {len(self.inventory)} unikalnych produktów")
                else:
                    self.inventory = pd.DataFrame()
                    print("⚠️ Plik inventory.csv jest pusty")
            else:
                print("⚠️ Brak pliku inventory.csv")
            
            # Ładuj suppliers
            if os.path.exists(f'{self.data_dir}/suppliers.csv'):
                self.suppliers = pd.read_csv(f'{self.data_dir}/suppliers.csv')
                print(f"✅ Załadowano suppliers: {len(self.suppliers)} rekordów")
            else:
                print("❌ Brak pliku suppliers.csv")
                return False
            
            # Ładuj purchase_order_history
            if os.path.exists(f'{self.data_dir}/purchase_order_history.csv'):
                self.purchase_orders = pd.read_csv(f'{self.data_dir}/purchase_order_history.csv')
                print(f"✅ Załadowano purchase orders: {len(self.purchase_orders)} rekordów")
            else:
                print("❌ Brak pliku purchase_order_history.csv")
                return False
            
            # Ładuj user_requests (opcjonalnie)
            if os.path.exists(f'{self.data_dir}/user_requests.csv'):
                self.user_requests = pd.read_csv(f'{self.data_dir}/user_requests.csv')
                print(f"✅ Załadowano user requests: {len(self.user_requests)} rekordów")
            else:
                print("⚠️ Brak pliku user_requests.csv")
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd ładowania danych: {e}")
            return False

    def _aggregate_inventory_data(self, inventory_raw):
        """Agreguje dane inventory - sumuje stany dla każdego produktu"""
        try:
            # Sprawdź dostępne kolumny
            print("🔍 Kolumny w inventory_raw:", inventory_raw.columns.tolist())
            
            # Grupuj po Product_ID i sumuj ilości
            aggregation_rules = {
                'Stock': 'sum',
                'Closing_Stock': 'sum',
                'Min_stock_level': 'first',  # Weź pierwszą wartość minimalnego stanu
                'Unit': 'first',             # Weź pierwszą jednostkę
                'Product_Name': 'first'      # Weź pierwszą nazwę produktu
            }
            
            # Jeśli istnieje kolumna Date, możemy też dodać najnowszą datę
            if 'Date' in inventory_raw.columns:
                aggregation_rules['Date'] = 'max'
            
            # Wykonaj agregację
            inventory_aggregated = inventory_raw.groupby('Product_ID').agg(aggregation_rules).reset_index()
            
            print(f"🔍 Przed agregacją: {len(inventory_raw)} wierszy")
            print(f"🔍 Po agregacji: {len(inventory_aggregated)} unikalnych produktów")
            
            # Debug: pokaż przykładowe dane przed i po agregacji
            if not inventory_raw.empty:
                sample_product = inventory_raw['Product_ID'].iloc[0]
                print(f"🔍 Przykład agregacji dla produktu {sample_product}:")
                before_agg = inventory_raw[inventory_raw['Product_ID'] == sample_product][['Product_ID', 'Stock', 'Closing_Stock']]
                after_agg = inventory_aggregated[inventory_aggregated['Product_ID'] == sample_product][['Product_ID', 'Stock', 'Closing_Stock']]
                print(f"   Przed: {len(before_agg)} wierszy, suma Stock: {before_agg['Stock'].sum()}")
                print(f"   Po: {len(after_agg)} wierszy, Stock: {after_agg['Stock'].iloc[0]}")
            
            return inventory_aggregated
            
        except Exception as e:
            print(f"❌ Błąd agregacji danych inventory: {e}")
            # W razie błędu zwróć oryginalne dane
            return inventory_raw
    
    def get_contracts(self):
        """Zwraca umowy terminowe"""
        if self.purchase_orders is not None and 'Umowa_ramowa' in self.purchase_orders.columns:
            contracts = self.purchase_orders[self.purchase_orders['Umowa_ramowa'] == 'tak']
            return contracts
        return pd.DataFrame()
    
    def save_order(self, order_data):
        """Zapisuje nowe zamówienie do pliku CSV"""
        orders_file = f'{self.data_dir}/orders.csv'
        
        try:
            # Upewnij się, że wszystkie wymagane pola istnieją
            required_fields = ['order_id', 'user_input', 'product_name', 'category', 
                             'quantity', 'supplier_name', 'price', 'contract_type', 'timestamp']
            
            # Uzupełnij brakujące pola wartościami domyślnymi
            default_order = {
                'order_id': 'UNKNOWN',
                'user_input': '',
                'product_name': 'Nieznany produkt',
                'category': 'Inne',
                'quantity': 1,
                'supplier_name': 'Nieznany dostawca',
                'price': 0.0,
                'contract_type': 'oferta',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'delivery_status': 'ordered',
                'estimated_delivery': (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            }
            
            # Użyj wartości z order_data lub domyślnych
            complete_order = {**default_order, **order_data}
            
            # Tworzy plik jeśli nie istnieje z nagłówkami
            if not os.path.exists(orders_file):
                pd.DataFrame([complete_order]).to_csv(orders_file, index=False)
                print(f"✅ Utworzono nowy plik zamówień: {orders_file}")
            else:
                # Wczytaj istniejące zamówienia
                existing_orders = pd.read_csv(orders_file)
                
                # Sprawdź czy order_id już istnieje (zapobieganie duplikatom)
                if complete_order['order_id'] in existing_orders['order_id'].values:
                    print(f"⚠️ Zamówienie {complete_order['order_id']} już istnieje!")
                    return False
                    
                # Dodaj nowe zamówienie
                updated_orders = pd.concat([existing_orders, pd.DataFrame([complete_order])], ignore_index=True)
                updated_orders.to_csv(orders_file, index=False)
                print(f"✅ Zapisano zamówienie {complete_order['order_id']} do {orders_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd zapisu zamówienia: {e}")
            import traceback
            print(f"Szczegóły błędu: {traceback.format_exc()}")
            return False

    def update_delivery_status(self, order_id, status, delivered_quantity=None):
        """Aktualizuje status dostawy zamówienia"""
        try:
            orders_file = f'{self.data_dir}/orders.csv'
            if not os.path.exists(orders_file):
                return False
            
            orders_df = pd.read_csv(orders_file)
            
            # Znajdź zamówienie
            order_mask = orders_df['order_id'] == order_id
            if not order_mask.any():
                print(f"❌ Nie znaleziono zamówienia {order_id}")
                return False
            
            # Aktualizuj status
            orders_df.loc[order_mask, 'delivery_status'] = status
            
            # Jeśli dostarczono, zaktualizuj stan magazynowy
            if status == 'delivered' and delivered_quantity is not None:
                product_name = orders_df.loc[order_mask, 'product_name'].iloc[0]
                self._update_inventory_on_delivery(product_name, delivered_quantity)
                orders_df.loc[order_mask, 'delivered_quantity'] = delivered_quantity
                orders_df.loc[order_mask, 'delivery_date'] = datetime.now().strftime("%Y-%m-%d")
            
            # Zapisz zmiany
            orders_df.to_csv(orders_file, index=False)
            print(f"✅ Zaktualizowano status zamówienia {order_id} na: {status}")
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd aktualizacji statusu dostawy: {e}")
            return False

    def _update_inventory_on_delivery(self, product_name, quantity):
        """Aktualizuje stan magazynowy po dostawie"""
        try:
            if self.inventory is None:
                return False
            
            # Znajdź produkt w inventory
            product_mask = self.inventory['Product_Name'] == product_name
            if not product_mask.any():
                print(f"❌ Nie znaleziono produktu '{product_name}' w inventory")
                return False
            
            # Aktualizuj stan magazynowy
            self.inventory.loc[product_mask, 'Stock'] += quantity
            self.inventory.loc[product_mask, 'Closing_Stock'] += quantity
            
            # Zapisz zmiany do pliku
            self.inventory.to_csv(f'{self.data_dir}/inventory.csv', index=False)
            print(f"✅ Zaktualizowano stan magazynowy po dostawie: {product_name} +{quantity}")
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd aktualizacji inventory po dostawie: {e}")
            return False

    def get_orders_in_delivery(self):
        """Zwraca zamówienia w trakcie dostawy"""
        try:
            orders_file = f'{self.data_dir}/orders.csv'
            if not os.path.exists(orders_file):
                return pd.DataFrame()
            
            orders_df = pd.read_csv(orders_file)
            
            # Filtruj zamówienia w trakcie dostawy
            delivery_orders = orders_df[
                (orders_df['delivery_status'] == 'ordered') | 
                (orders_df['delivery_status'] == 'in_transit')
            ]
            
            return delivery_orders
            
        except Exception as e:
            print(f"❌ Błąd ładowania zamówień w dostawie: {e}")
            return pd.DataFrame()

    def get_inventory_status(self):
        """Zwraca status magazynowy z połączonymi danymi produktów"""
        if self.inventory is not None and self.products is not None:
            return self.inventory.merge(
                self.products[['Product_ID', 'Product_Name', 'Category', 'Unit', 'Min_Stock_Level']],
                on='Product_ID',
                how='left'
            )

    
        return pd.DataFrame()