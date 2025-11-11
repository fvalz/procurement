import pandas as pd
from datetime import datetime, timedelta
import os

class AutoReorderSystem:
    def __init__(self, data_loader, supplier_matcher, pdf_generator):
        self.data_loader = data_loader
        self.supplier_matcher = supplier_matcher
        self.pdf_generator = pdf_generator
    
    def check_production_needs(self):
        """Sprawdza które produkty potrzebują automatycznego zamówienia"""
        production_orders = []
        
        if self.data_loader.inventory is None:
            print("❌ Brak danych inventory")
            return production_orders
        
        # Debug: sprawdź dostępne kolumny w inventory
        print("🔍 Kolumny w inventory:", self.data_loader.inventory.columns.tolist())
        print("🔍 Przykładowe dane inventory:")
        print(self.data_loader.inventory[['Product_ID', 'Product_Name', 'Stock', 'Min_stock_level']].head())
        
        # Znajdź produkty z niskim stanem - POPRAWIONE FILTROWANIE
        try:
            # Sprawdź czy kolumny istnieją
            if 'Stock' not in self.data_loader.inventory.columns or 'Min_stock_level' not in self.data_loader.inventory.columns:
                print("❌ Brak wymaganych kolumn w inventory")
                return production_orders
            
            # Filtruj produkty z niskim stanem
            low_stock_products = self.data_loader.inventory[
                self.data_loader.inventory['Stock'] <= self.data_loader.inventory['Min_stock_level']
            ]
            
            print(f"🔍 Znaleziono {len(low_stock_products)} produktów z niskim stanem")
            
        except Exception as e:
            print(f"❌ Błąd podczas filtrowania niskich stanów: {e}")
            return production_orders
        
        # Pobierz listę już złożonych zamówień (aby uniknąć duplikatów)
        existing_orders = self._get_existing_production_orders()
        
        for _, product in low_stock_products.iterrows():
            try:
                # Użyj bezpiecznego dostępu do kolumn
                product_id = product.get('Product_ID', 'Unknown')
                product_name = product.get('Product_Name')
                
                if not product_name:
                    print(f"⚠️ Pominięto produkt bez nazwy: {product_id}")
                    continue
                
                # Sprawdź czy już nie ma aktywnego zamówienia dla tego produktu
                if self._has_active_order(existing_orders, product_id):
                    print(f"⚠️ Pominięto produkt {product_name} - już ma aktywne zamówienie")
                    continue
                
                # Pobierz szczegóły produktu z bazy produktów
                product_details = self._get_product_details(product_id)
                category = product_details.get('category', 'Unknown')
                unit = product_details.get('unit', 'szt.')
                lead_time = product_details.get('lead_time', 7)
                
                current_stock = product.get('Stock', 0)
                min_stock = product.get('Min_stock_level', 0)
                
                # Oblicz sugerowaną ilość do zamówienia
                suggested_quantity = self._calculate_suggested_quantity(
                    current_stock, min_stock, lead_time
                )
                
                # Oblicz przewidywaną datę dostawy - POPRAWIONE: konwersja na int
                estimated_delivery = (datetime.now() + timedelta(days=int(lead_time))).strftime("%Y-%m-%d")
                
                # Znajdź dostawcę
                supplier_result = self.supplier_matcher.find_supplier_in_contracts(
                    product_name,
                    category
                )
                
                order_info = {
                    'product_id': product_id,
                    'product_name': product_name,
                    'category': category,
                    'current_stock': current_stock,
                    'min_stock': min_stock,
                    'unit': unit,
                    'suggested_quantity': suggested_quantity,
                    'lead_time_days': lead_time,
                    'estimated_delivery': estimated_delivery
                }
                
                # Dodaj informacje o dostawcy jeśli znaleziono
                if supplier_result.get('found'):
                    order_info.update({
                        'supplier_found': True,
                        'supplier_name': supplier_result.get('supplier_name'),
                        'price': supplier_result.get('price'),
                        'delivery_time': supplier_result.get('delivery_time'),
                        'contract_type': supplier_result.get('contract_type')
                    })
                else:
                    order_info.update({
                        'supplier_found': False,
                        'error': supplier_result.get('error', 'Nie znaleziono dostawcy')
                    })
                
                production_orders.append(order_info)
                print(f"✅ Dodano produkt do zamówienia: {product_name} (stan: {current_stock}/{min_stock})")
                
            except Exception as e:
                print(f"❌ Błąd przetwarzania produktu {product.get('Product_ID', 'Unknown')}: {e}")
                continue
        
        print(f"🎯 Łącznie znaleziono {len(production_orders)} produktów do zamówienia")
        return production_orders
    
    def _get_product_details(self, product_id):
        """Pobiera szczegóły produktu z bazy produktów"""
        try:
            if self.data_loader.products is None:
                return {'category': 'Unknown', 'unit': 'szt.', 'lead_time': 7}
            
            product_row = self.data_loader.products[
                self.data_loader.products['Product_ID'] == product_id
            ]
            
            if not product_row.empty:
                product = product_row.iloc[0]
                
                # POPRAWIONE: bezpieczna konwersja lead_time na int
                lead_time = product.get('Average_Lead_Time_Days', 7)
                try:
                    lead_time = int(lead_time)
                except (ValueError, TypeError):
                    lead_time = 7
                
                return {
                    'category': product.get('Category', 'Unknown'),
                    'unit': product.get('Unit', 'szt.'),
                    'lead_time': lead_time
                }
        except Exception as e:
            print(f"❌ Błąd pobierania szczegółów produktu {product_id}: {e}")
        
        return {'category': 'Unknown', 'unit': 'szt.', 'lead_time': 7}
    
    def _get_existing_production_orders(self):
        """Pobiera listę istniejących zamówień produkcyjnych"""
        try:
            orders_file = f"{self.data_loader.data_dir}/orders.csv"
            if os.path.exists(orders_file):
                orders_df = pd.read_csv(orders_file)
                # Filtruj tylko zamówienia produkcyjne które nie zostały dostarczone
                if 'delivery_status' in orders_df.columns and 'order_type' in orders_df.columns:
                    production_orders = orders_df[
                        (orders_df['order_type'] == 'Produkcyjne') & 
                        (orders_df['delivery_status'].isin(['ordered', 'in_transit']))
                    ]
                    return production_orders
        except Exception as e:
            print(f"❌ Błąd ładowania istniejących zamówień: {e}")
        
        return pd.DataFrame()
    
    def _has_active_order(self, existing_orders, product_id):
        """Sprawdza czy istnieje już aktywne zamówienie dla produktu"""
        if existing_orders.empty:
            return False
        
        # Sprawdź czy istnieje zamówienie dla tego produktu które nie zostało dostarczone
        if 'product_id' in existing_orders.columns:
            product_orders = existing_orders[
                (existing_orders['product_id'] == product_id)
            ]
            return not product_orders.empty
        
        return False
    
    def _calculate_suggested_quantity(self, current_stock, min_stock, lead_time_days):
        """Oblicza sugerowaną ilość do zamówienia"""
        try:
            # Prosta heurystyka: zamów 2x minimalny stan minus aktualny stan
            # + zapas na czas dostawy
            safety_stock = max(min_stock * 0.5, 10)  # Zapas bezpieczeństwa
            suggested = (min_stock * 2) - current_stock + safety_stock
            
            # Zaokrąglij do pełnych jednostek
            return max(int(suggested), min_stock)
        except:
            return min_stock * 2
    
    def create_production_order(self, product_info, quantity):
        """Tworzy zamówienie produkcyjne"""
        order_data = {
            'order_id': f"PROD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'user_input': f"Automatyczne zamówienie produkcyjne - {product_info['product_name']}",
            'product_name': product_info['product_name'],
            'product_id': product_info['product_id'],
            'category': product_info['category'],
            'quantity': quantity,
            'unit': product_info.get('unit', 'szt.'),
            'supplier_name': product_info.get('supplier_name', 'Nieznany dostawca'),
            'price': product_info.get('price', 0),
            'contract_type': product_info.get('contract_type', 'oferta'),
            'order_type': 'Produkcyjne',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'estimated_delivery': product_info.get('estimated_delivery', (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")),
            'delivery_status': 'ordered'
        }
        
        # Generuj PDF
        pdf_path = self.pdf_generator.generate_order_pdf(order_data)
        
        # Zapisz zamówienie
        success = self.data_loader.save_order(order_data)
        
        return success, pdf_path