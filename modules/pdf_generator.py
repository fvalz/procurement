from fpdf import FPDF
import os
from datetime import datetime

class PDFGenerator:
    def __init__(self, output_dir='orders'):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def _safe_text(self, text):
        """Zamienia polskie znaki na podstawowe znaki ASCII"""
        if not isinstance(text, str):
            text = str(text)
        replacements = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
            'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N',
            'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
        }
        for pol, eng in replacements.items():
            text = text.replace(pol, eng)
        return text
    
    def _safe_float(self, value):
        """Bezpiecznie konwertuje wartość na float"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Usuń spacje i zamień przecinki na kropki
                cleaned = value.replace(' ', '').replace(',', '.')
                return float(cleaned)
            return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def generate_order_pdf(self, order_data):
        """Generuje profesjonalny dokument zamówienia"""
        pdf = FPDF()
        pdf.add_page()
        
        # Nagłówek dokumentu
        self._add_header(pdf, order_data)
        
        # Sekcja danych zamawiającego i dostawcy
        self._add_company_info(pdf, order_data)
        
        # Tabela z produktami
        self._add_products_table(pdf, order_data)
        
        # Sekcja warunków zamówienia
        self._add_terms_section(pdf, order_data)
        
        # Stopka z podpisami
        self._add_footer(pdf)
        
        # Zapisz plik
        filename = f"Zamowienie_{order_data.get('order_id', 'BRAK')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        pdf.output(filepath)
        
        return filepath
    
    def _add_header(self, pdf, order_data):
        """Dodaje nagłówek dokumentu"""
        # Tło nagłówka
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(10, 10, 190, 25, 'F')
        
        # Tytuł
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(190, 10, self._safe_text('ZAMÓWIENIE'), 0, 1, 'C')
        
        # Numer zamówienia i data
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(95, 8, self._safe_text(f"Numer: {order_data.get('order_id', 'BRAK')}"), 0, 0, 'L')
        pdf.cell(95, 8, self._safe_text(f"Data: {datetime.now().strftime('%d.%m.%Y')}"), 0, 1, 'R')
        
        pdf.ln(5)
    
    def _add_company_info(self, pdf, order_data):
        """Dodaje informacje o firmie i dostawcy"""
        # Nagłówek sekcji
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(190, 8, self._safe_text('DANE STRON'), 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        
        # Dwie kolumny: Zamawiający i Dostawca
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(95, 6, self._safe_text('ZAMAWIAJĄCY:'), 0, 0, 'L')
        pdf.cell(95, 6, self._safe_text('DOSTAWCA:'), 0, 1, 'L')
        
        pdf.set_font('Arial', '', 10)
        
        # Dane zamawiającego (stałe)
        zamawiajacy = [
            "FIRMA EXAMPLE SP. Z O.O.",
            "ul. Przykładowa 123",
            "00-001 Warszawa",
            "NIP: 1234567890",
            "Tel: +48 22 123 45 67"
        ]
        
        for line in zamawiajacy:
            pdf.cell(95, 5, self._safe_text(line), 0, 0, 'L')
            pdf.cell(95, 5, '', 0, 1, 'L')
        
        pdf.ln(2)
        
        # Dane dostawcy
        dostawca_nazwa = order_data.get('supplier_name', 'Nieznany dostawca')
        pdf.cell(95, 5, '', 0, 0, 'L')
        pdf.cell(95, 5, self._safe_text(dostawca_nazwa), 0, 1, 'L')
        
        pdf.ln(8)
    
    def _add_products_table(self, pdf, order_data):
        """Dodaje tabelę z produktami"""
        # Bezpieczne pobranie i konwersja wartości liczbowych
        quantity = self._safe_float(order_data.get('quantity', 1))
        price = self._safe_float(order_data.get('price', 0.0))
        value = quantity * price
        
        product_name = order_data.get('product_name', 'Nieznany produkt')
        unit = order_data.get('unit', 'szt.')
        
        # Nagłówek tabeli
        pdf.set_fill_color(200, 200, 200)
        pdf.set_font('Arial', 'B', 10)
        
        pdf.cell(100, 8, self._safe_text('NAZWA PRODUKTU'), 1, 0, 'C', True)
        pdf.cell(20, 8, self._safe_text('ILOŚĆ'), 1, 0, 'C', True)
        pdf.cell(25, 8, self._safe_text('J.M.'), 1, 0, 'C', True)
        pdf.cell(25, 8, self._safe_text('CENA'), 1, 0, 'C', True)
        pdf.cell(20, 8, self._safe_text('WARTOŚĆ'), 1, 1, 'C', True)
        
        # Wiersz z produktem
        pdf.set_font('Arial', '', 10)
        
        pdf.cell(100, 8, self._safe_text(product_name), 1, 0, 'L')
        pdf.cell(20, 8, self._safe_text(str(int(quantity))), 1, 0, 'C')
        pdf.cell(25, 8, self._safe_text(unit), 1, 0, 'C')
        pdf.cell(25, 8, self._safe_text(f"{price:.2f} PLN"), 1, 0, 'R')
        pdf.cell(20, 8, self._safe_text(f"{value:.2f} PLN"), 1, 1, 'R')
        
        pdf.ln(5)
        
        # Podsumowanie
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(145, 8, self._safe_text('RAZEM DO ZAPŁATY:'), 0, 0, 'R')
        pdf.cell(45, 8, self._safe_text(f"{value:.2f} PLN"), 1, 1, 'R')
        
        pdf.ln(8)
    
    def _add_terms_section(self, pdf, order_data):
        """Dodaje sekcję warunków zamówienia"""
        # Nagłówek sekcji
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(190, 8, self._safe_text('WARUNKI ZAMÓWIENIA'), 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        
        pdf.set_font('Arial', '', 10)
        
        # Termin dostawy
        estimated_delivery = order_data.get('estimated_delivery', 'Nieokreślony')
        if estimated_delivery != 'Nieokreślony':
            try:
                delivery_date = datetime.strptime(estimated_delivery, '%Y-%m-%d')
                estimated_delivery = delivery_date.strftime('%d.%m.%Y')
            except:
                pass
        
        terms = [
            f"Termin dostawy: {estimated_delivery}",
            f"Forma dostawy: {order_data.get('contract_type', 'oferta')}",
            "Warunki płatności: 14 dni od daty faktury",
            "Miejsce dostawy: siedziba Zamawiającego",
            "Uwagi: Prosimy o potwierdzenie realizacji zamówienia"
        ]
        
        for term in terms:
            pdf.cell(190, 5, self._safe_text(term), 0, 1, 'L')
        
        pdf.ln(5)
        
        # Dodatkowe informacje
        if order_data.get('user_input'):
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(190, 6, self._safe_text('DODATKOWE INFORMACJE:'), 0, 1, 'L')
            pdf.set_font('Arial', '', 9)
            
            # Długi tekst dzielimy na linie
            user_input = order_data.get('user_input', '')
            lines = self._split_text(user_input, 80)
            for line in lines:
                pdf.cell(190, 4, self._safe_text(line), 0, 1, 'L')
            
            pdf.ln(5)
    
    def _add_footer(self, pdf):
        """Dodaje stopkę z podpisami"""
        pdf.ln(10)
        
        # Linia na podpisy
        pdf.line(20, pdf.get_y(), 90, pdf.get_y())
        pdf.line(110, pdf.get_y(), 180, pdf.get_y())
        
        pdf.ln(5)
        
        # Podpisy
        pdf.set_font('Arial', '', 9)
        pdf.cell(70, 5, self._safe_text('Podpis Zamawiającego'), 0, 0, 'C')
        pdf.cell(50, 5, '', 0, 0, 'C')
        pdf.cell(70, 5, self._safe_text('Podpis Dostawcy'), 0, 1, 'C')
        
        pdf.ln(15)
        
        # Informacja o dokumencie
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(190, 4, self._safe_text('Dokument wygenerowany automatycznie przez System Procurement AI'), 0, 1, 'C')
        pdf.cell(190, 4, self._safe_text(f'Wygenerowano: {datetime.now().strftime("%d.%m.%Y %H:%M")}'), 0, 1, 'C')
    
    def _split_text(self, text, max_length):
        """Dzieli tekst na linie o określonej maksymalnej długości"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= max_length:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines