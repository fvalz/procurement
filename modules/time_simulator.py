import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

class TimeSimulator:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.current_date = None
        self.load_simulation_state()
    
    def load_simulation_state(self):
        """Ładuje stan symulacji z pliku"""
        try:
            state_file = f'{self.data_dir}/simulation_state.csv'
            if os.path.exists(state_file):
                state_df = pd.read_csv(state_file)
                self.current_date = datetime.strptime(state_df.iloc[0]['current_date'], '%Y-%m-%d').date()
                print(f"✅ Załadowano datę symulacji: {self.current_date}")
            else:
                # Domyślnie dzisiejsza data
                self.current_date = datetime.now().date()
                self.save_simulation_state()
                print(f"✅ Utworzono nową symulację od: {self.current_date}")
        except Exception as e:
            print(f"❌ Błąd ładowania stanu symulacji: {e}")
            self.current_date = datetime.now().date()
    
    def save_simulation_state(self):
        """Zapisuje stan symulacji do pliku"""
        try:
            state_file = f'{self.data_dir}/simulation_state.csv'
            state_df = pd.DataFrame({
                'current_date': [self.current_date.strftime('%Y-%m-%d')],
                'last_updated': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            })
            state_df.to_csv(state_file, index=False)
        except Exception as e:
            print(f"❌ Błąd zapisu stanu symulacji: {e}")
    
    def advance_time(self, days=1):
        """Przesuwa czas symulacji o określoną liczbę dni"""
        old_date = self.current_date
        self.current_date += timedelta(days=days)
        self.save_simulation_state()
        print(f"⏰ Czas symulacji: {old_date} -> {self.current_date} (+{days} dni)")
        return self.current_date
    
    def simulate_daily_operations(self, data_loader):
        """Symuluje codzienne operacje biznesowe"""
        print(f"🔄 Symulowanie operacji dla {self.current_date}")
        
        # 1. Symuluj zużycie produktów
        self._simulate_consumption(data_loader)
        
        # 2. Aktualizuj statusy dostaw
        self._update_delivery_statuses(data_loader)
        
        # 3. Generuj nowe zapotrzebowania użytkowników
        self._simulate_user_requests(data_loader)
        
        print("✅ Symulacja dzienna zakończona")
    
    def _simulate_consumption(self, data_loader):
        """Symuluje zużycie produktów"""
        if data_loader.inventory is None:
            return
        
        try:
            # Losowe zużycie produktów (1-10% stanu dziennie)
            consumption_factor = random.uniform(0.01, 0.10)
            
            for idx, product in data_loader.inventory.iterrows():
                current_stock = product['Stock']
                if current_stock > 0:
                    # Zużyj losową ilość, ale nie poniżej zera
                    consumption = max(1, int(current_stock * consumption_factor * random.uniform(0.5, 1.5)))
                    new_stock = max(0, current_stock - consumption)
                    
                    data_loader.inventory.at[idx, 'Stock'] = new_stock
                    data_loader.inventory.at[idx, 'Closing_Stock'] = new_stock
            
            # Zapisz zmiany
            data_loader.inventory.to_csv(f'{self.data_dir}/inventory.csv', index=False)
            print(f"📉 Symulowano zużycie produktów (współczynnik: {consumption_factor:.2%})")
            
        except Exception as e:
            print(f"❌ Błąd symulacji zużycia: {e}")
    
    def _update_delivery_statuses(self, data_loader):
        """Aktualizuje statusy dostaw na podstawie czasu symulacji"""
        try:
            orders_file = f'{self.data_dir}/orders.csv'
            if not os.path.exists(orders_file):
                return
            
            orders_df = pd.read_csv(orders_file)
            updated_orders = 0
            
            for idx, order in orders_df.iterrows():
                if order['delivery_status'] in ['ordered', 'in_transit']:
                    estimated_delivery = order.get('estimated_delivery')
                    if estimated_delivery and isinstance(estimated_delivery, str):
                        try:
                            delivery_date = datetime.strptime(estimated_delivery, '%Y-%m-%d').date()
                            
                            # Jeśli data dostawy minęła, oznacz jako dostarczone
                            if delivery_date <= self.current_date:
                                orders_df.at[idx, 'delivery_status'] = 'delivered'
                                orders_df.at[idx, 'delivery_date'] = self.current_date.strftime('%Y-%m-%d')
                                
                                # Aktualizuj stan magazynowy
                                product_name = order['product_name']
                                quantity = order['quantity']
                                data_loader._update_inventory_on_delivery(product_name, quantity)
                                
                                updated_orders += 1
                                
                        except ValueError:
                            continue
            
            if updated_orders > 0:
                orders_df.to_csv(orders_file, index=False)
                print(f"📦 Zaktualizowano {updated_orders} zamówień do statusu 'dostarczone'")
                
        except Exception as e:
            print(f"❌ Błąd aktualizacji statusów dostaw: {e}")
    
    def _simulate_user_requests(self, data_loader):
        """Symuluje nowe zapotrzebowania od użytkowników"""
        try:
            # 30% szans na nowe zapotrzebowanie każdego dnia
            if random.random() > 0.3:
                return
            
            requests_file = f'{self.data_dir}/user_requests.csv'
            
            # Przykładowe zapotrzebowania
            sample_requests = [
                "Potrzebuję 5 laptopów Dell dla nowych pracowników",
                "Zamów 20 opakowań papieru A4 do drukarki",
                "Potrzebujemy 3 nowych monitorów 24 cali",
                "Zamów materiały biurowe: długopisy, notesy, spinacze",
                "Potrzebuję 2 sztuki Siemens Sensors dla produkcji",
                "Zamów części zamienne do maszyn produkcyjnych"
            ]
            
            new_request = {
                'Request_ID': f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'User_Text': random.choice(sample_requests),
                'Detected_Product': '',
                'Detected_Category': '',
                'Timestamp': self.current_date.strftime('%Y-%m-%d %H:%M')
            }
            
            # Dodaj do pliku
            if os.path.exists(requests_file):
                existing_requests = pd.read_csv(requests_file)
                updated_requests = pd.concat([existing_requests, pd.DataFrame([new_request])], ignore_index=True)
                updated_requests.to_csv(requests_file, index=False)
            else:
                pd.DataFrame([new_request]).to_csv(requests_file, index=False)
            
            print(f"📝 Wygenerowano nowe zapotrzebowanie: {new_request['User_Text']}")
            
        except Exception as e:
            print(f"❌ Błąd symulacji zapotrzebowań: {e}")
    
    def get_simulation_info(self):
        """Zwraca informacje o symulacji"""
        real_date = datetime.now().date()
        sim_days = (self.current_date - real_date).days
        
        return {
            'current_simulation_date': self.current_date,
            'real_world_date': real_date,
            'days_ahead': max(0, sim_days),
            'is_future': sim_days > 0
        }
    
    def reset_simulation(self):
        """Resetuje symulację do aktualnej daty"""
        self.current_date = datetime.now().date()
        self.save_simulation_state()
        print("🔄 Zresetowano symulację do aktualnej daty")