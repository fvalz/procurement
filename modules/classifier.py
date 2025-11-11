import re
from difflib import SequenceMatcher

class SimpleClassifier:
    def __init__(self, products_df):
        self.products_df = products_df

    def classify_request(self, user_text):
        user_text_lower = user_text.lower()
        
        # Próba wyciągnięcia ilości
        quantity = self._extract_quantity(user_text)
        
        # Próba dopasowania produktu z katalogu
        product_match, match_confidence = self._match_product(user_text_lower)
        
        if product_match is not None:
            return {
                'product_id': product_match['Product_ID'],
                'product_name': product_match['Product_Name'],
                'category': product_match['Category'],
                'quantity': quantity or 1,
                'confidence': match_confidence,
                'found_in_catalog': True,
                'unit': product_match.get('Unit', 'szt.')
            }
        else:
            # Jeśli nie znaleziono produktu, zwracamy kategorie na podstawie słów kluczowych
            category = self._classify_by_keywords(user_text_lower)
            return {
                'product_id': None,
                'product_name': None,
                'category': category,
                'quantity': quantity or 1,
                'confidence': 0.3,
                'found_in_catalog': False,
                'unit': 'szt.'
            }

    def _extract_quantity(self, text):
        patterns = [
            r'(\d+)\s*szt\.',
            r'(\d+)\s*op\.',
            r'(\d+)\s*sztuk',
            r'(\d+)\s*opakowań',
            r'need\s*(\d+)',
            r'potrzebuję\s*(\d+)',
            r'potrzebujemy\s*(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _match_product(self, text):
        best_match = None
        best_score = 0
        
        for _, product in self.products_df.iterrows():
            product_name = str(product['Product_Name']).lower()
            
            # Sprawdź czy nazwa produktu występuje w tekście
            if product_name in text:
                return product, 0.9
            
            # Oblicz podobieństwo tekstu
            score = SequenceMatcher(None, text, product_name).ratio()
            if score > best_score and score > 0.3:  # Próg podobieństwa
                best_score = score
                best_match = product
        
        # POPRAWIONE: Użyj jawnych warunków zamiast niejednoznacznego "if best_match"
        if best_match is not None:
            return best_match, best_score
        else:
            return None, 0

    def _classify_by_keywords(self, text):
        keywords = {
            'IT': ['laptop', 'monitor', 'computer', 'software', 'hardware', 'dell', 'hp', 'samsung', 'siemens'],
            'Office': ['paper', 'papier', 'chair', 'krzesło', 'biuro', 'office', 'toner', 'drukarka'],
            'Production': ['motor', 'silnik', 'sensor', 'czujnik', 'tool', 'narzędzie', 'production', 'produkcja'],
            'BHP': ['safety', 'bezpieczeństwo', 'glasses', 'okulary', 'workwear', 'odzież']
        }
        for category, words in keywords.items():
            if any(word in text for word in words):
                return category
        return 'Other'