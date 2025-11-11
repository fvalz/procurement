import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher

class SupplierMatcher:
    def __init__(self, suppliers_df, purchase_orders_df):
        self.suppliers_df = suppliers_df
        self.purchase_orders_df = purchase_orders_df
    
    def find_supplier_in_contracts(self, product_name, category):
        """Szuka dostawcy w umowach terminowych"""
        if self.purchase_orders_df is None or self.purchase_orders_df.empty:
            return {'found': False, 'error': 'Brak danych zamówień'}
        
        # Sprawdź czy kolumna Umowa_ramowa istnieje
        if 'Umowa_ramowa' not in self.purchase_orders_df.columns:
            return {'found': False, 'error': 'Brak kolumny Umowa_ramowa'}
        
        contracts = self.purchase_orders_df[self.purchase_orders_df['Umowa_ramowa'] == 'tak']
        
        if contracts.empty:
            return {'found': False, 'error': 'Brak umów terminowych'}
        
        # Szukaj dopasowania po nazwie produktu
        if product_name:
            # Najpierw szukamy dokładnego dopasowania
            exact_match = contracts[
                contracts['Product_Name'].str.contains(str(product_name), case=False, na=False)
            ]
            if not exact_match.empty:
                supplier = exact_match.iloc[0]
                return {
                    'supplier_name': supplier.get('Supplier', 'Nieznany'),
                    'product_name': supplier.get('Product_Name', 'Nieznany'),
                    'price': supplier.get('Unit_Price', 0),
                    'delivery_time': '2-3 dni',
                    'contract_type': 'terminowy',
                    'found': True
                }
            
            # Jeśli nie ma dokładnego, szukamy po podobieństwie
            best_match = None
            best_score = 0
            
            for _, contract in contracts.iterrows():
                contract_product = str(contract['Product_Name']).lower()
                product_name_lower = str(product_name).lower()
                
                score = SequenceMatcher(None, product_name_lower, contract_product).ratio()
                if score > best_score and score > 0.6:
                    best_score = score
                    best_match = contract
            
            if best_match is not None:
                return {
                    'supplier_name': best_match.get('Supplier', 'Nieznany'),
                    'product_name': best_match.get('Product_Name', 'Nieznany'),
                    'price': best_match.get('Unit_Price', 0),
                    'delivery_time': '2-3 dni',
                    'contract_type': 'terminowy',
                    'found': True,
                    'match_confidence': round(best_score, 2)
                }
        
        # Szukaj dopasowania po kategorii
        if category:
            category_match = contracts[
                (contracts['Category1'] == category) | 
                (contracts['Category2'] == category)
            ]
            if not category_match.empty:
                supplier = category_match.iloc[0]
                return {
                    'supplier_name': supplier.get('Supplier', 'Nieznany'),
                    'product_name': supplier.get('Product_Name', 'Nieznany'),
                    'price': supplier.get('Unit_Price', 0),
                    'delivery_time': '2-3 dni',
                    'contract_type': 'terminowy',
                    'found': True
                }
        
        return {'found': False}
    
    def find_similar_products(self, product_name, category, top_n=3):
        """Znajduje podobne produkty w systemie"""
        if product_name is None or self.purchase_orders_df is None:
            return []
            
        all_products = self.purchase_orders_df['Product_Name'].dropna().unique()
        
        if len(all_products) == 0:
            return []
        
        # Proste wyszukiwanie po podobieństwie tekstu
        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(all_products)
            query_vec = vectorizer.transform([product_name])
            similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
            
            # Znajdź najbardziej podobne produkty
            similar_indices = similarities.argsort()[-top_n:][::-1]
            similar_products = []
            
            for idx in similar_indices:
                if similarities[idx] > 0.1:  # Próg podobieństwa
                    similar_products.append({
                        'product_name': all_products[idx],
                        'similarity_score': round(similarities[idx], 2)
                    })
            
            return similar_products
        except Exception as e:
            print(f"Błąd w wyszukiwaniu podobnych produktów: {e}")
            # Fallback - proste wyszukiwanie
            similar = [p for p in all_products if str(product_name).lower() in str(p).lower()]
            return [{'product_name': p, 'similarity_score': 0.5} for p in similar[:top_n]]