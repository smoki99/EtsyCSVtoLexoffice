import unittest
import csv
from datetime import datetime
from io import StringIO
import pandas as pd
from unittest.mock import patch
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from convertCsv import ( # Import after modifying sys.path
    process_deposit, process_sale, process_fee, update_fees, 
    write_summarized_data, convert_csv
)
class TestEtsyConverter(unittest.TestCase):

    @patch('logging.info')  
    def test_process_deposit(self, mock_logging_info):
        # Test case 1: Normal deposit
        test_row = ['"September 10, 2024"', 'Deposit', '€123.45 sent to your bank account']
        output_file = StringIO()
        writer = csv.writer(output_file)
        process_deposit(test_row, writer)
        output_file.seek(0)
        reader = csv.reader(output_file)
        output_row = next(reader)
        self.assertEqual(output_row, ['10.09.2024', 'Auszahlung', 'Etsy Ireland UC', 'Geldtransit/Umbuchung/Auszahlung', '-123,45'])
        
        # Test case 2: Deposit with a comma in the amount
        test_row = ['"September 11, 2024"', 'Deposit', '€234.56 sent to your bank account']
        output_file = StringIO()
        writer = csv.writer(output_file)
        process_deposit(test_row, writer)
        output_file.seek(0)
        reader = csv.reader(output_file)
        output_row = next(reader)
        self.assertEqual(output_row, ['11.09.2024', 'Auszahlung', 'Etsy Ireland UC', 'Geldtransit/Umbuchung/Auszahlung', '-234,56'])

        # Test case 3: Deposit with a different date format
        test_row = ['"September 20, 2024"', 'Deposit', '€987.65 sent to your bank account']
        output_file = StringIO()
        writer = csv.writer(output_file)
        process_deposit(test_row, writer)
        output_file.seek(0)
        reader = csv.reader(output_file)
        output_row = next(reader)
        self.assertEqual(output_row, ['20.09.2024', 'Auszahlung', 'Etsy Ireland UC', 'Geldtransit/Umbuchung/Auszahlung', '-987,65'])

        mock_logging_info.assert_any_call(f"Processing deposit: {test_row}")
        mock_logging_info.assert_any_call(f"Wrote row to CSV: {output_row}")

    @patch('logging.info') 
    def test_process_sale_with_tax(self, mock_logging_info):
        # Test case 1: Sale with tax
        test_row = ['"September 15, 2024"', 'Sale', 'Payment for Order #9876543210', '', 'EUR', '€88.20', '--', '€88.20', '--', '--', '--']
        tax_row = ['"September 15, 2024"', 'Tax', 'Sales tax paid by buyer', 'Order #9876543210', 'EUR', '--', '-€5.50', '-€5.50', '--', '--', '--']
        rows = [test_row, tax_row] 
        output_file = StringIO()
        writer = csv.writer(output_file)
        process_sale(test_row, rows, writer)
        output_file.seek(0)
        reader = csv.reader(output_file)
        output_row = next(reader)
        self.assertEqual(output_row, ['15.09.2024', 'Verkauf', 'Payment', 'Bestellung #9876543210', '(€88.20 € - 5.50 € (US-Sales Taxes payed by Etsy))', '82,70'])

        # Test case 2: Sale with tax - different amounts and order IDs
        test_row = ['"September 16, 2024"', 'Sale', 'Payment for Order #1122334455', '', 'EUR', '€150.75', '--', '€150.75', '--', '--', '--']
        tax_row = ['"September 16, 2024"', 'Tax', 'Sales tax paid by buyer', 'Order #1122334455', 'EUR', '--', '-€12.25', '-€12.25', '--', '--', '--']
        rows = [test_row, tax_row] 
        output_file = StringIO()
        writer = csv.writer(output_file)
        process_sale(test_row, rows, writer)
        output_file.seek(0)
        reader = csv.reader(output_file)
        output_row = next(reader)
        self.assertEqual(output_row, ['16.09.2024', 'Verkauf', 'Payment', 'Bestellung #1122334455', '(€150.75 € - 12.25 € (US-Sales Taxes payed by Etsy))', '138,50'])

        # Test case 3: Sale with no matching tax row 
        test_row = ['"September 17, 2024"', 'Sale', 'Payment for Order #9900887766', '', 'EUR', '€65.00', '--', '€65.00', '--', '--', '--']
        rows = [test_row]  # No tax row provided
        output_file = StringIO()
        writer = csv.writer(output_file)
        process_sale(test_row, rows, writer)
        output_file.seek(0)
        reader = csv.reader(output_file)
        output_row = next(reader)
        self.assertEqual(output_row, ['17.09.2024', 'Verkauf', 'Payment', 'Bestellung #9900887766', '(€65.00 €)', '65,00'])

        mock_logging_info.assert_any_call(f"Processing sale: {test_row}")
        mock_logging_info.assert_any_call(f"Wrote row to CSV: {output_row}")

    @patch('logging.info')
    def test_process_sale_no_tax(self, mock_logging_info):
        test_row = ['"September 18, 2024"', 'Sale', 'Payment for Order #5566778899', '', 'EUR', '€45.30', '--', '€45.30', '--', '--', '--']
        rows = [test_row] 
        output_file = StringIO()
        writer = csv.writer(output_file)

        process_sale(test_row, rows, writer)

        output_file.seek(0)
        reader = csv.reader(output_file)
        output_row = next(reader)

        self.assertEqual(output_row, ['18.09.2024', 'Verkauf', 'Payment', 'Bestellung #5566778899', '(€45.30 €)', '45,30'])
        mock_logging_info.assert_any_call(f"Processing sale: {test_row}")
        mock_logging_info.assert_any_call(f"Wrote row to CSV: {output_row}")   

    @patch('logging.info') 
    def test_process_fee(self, mock_logging_info):
        data = {}
        current_month = None
        next_listing_fee_is_renew = False
        output_file = StringIO()
        writer = csv.writer(output_file)

        # Test case 1: Listing fee - new month
        test_row = ['"September 1, 2024"', 'Fee', 'Listing fee ($0.20 USD)', 'Listing #1234567890', 'EUR', '--', '-€0.18', '-€0.18', '--', '--', '--']
        data, current_month, next_listing_fee_is_renew = process_fee(test_row, data, current_month, writer, next_listing_fee_is_renew)
        self.assertEqual(data, {'Etsy Ireland UC': {'Listing Fees': 0.18}})
        self.assertEqual(current_month, 9)  # September

        # Test case 2: Transaction fee - same month
        test_row = ['"September 5, 2024"', 'Fee', 'Transaction fee: Something', 'Order #9876543210', 'EUR', '--', '-€1.50', '-€1.50', '--', '--', '--']
        data, current_month, next_listing_fee_is_renew = process_fee(test_row, data, current_month, writer, next_listing_fee_is_renew)
        self.assertEqual(data['Etsy Ireland UC']['Transaction Fees'], 1.50)

        # Test case 3: Etsy Ads fee - ensure correct categorization
        test_row = ['"September 10, 2024"', 'Marketing', 'Etsy Ads', 'Bill for something', 'EUR', '--', '-€3.50', '-€3.50', '--', '--', '--']
        data, current_month, next_listing_fee_is_renew = process_fee(test_row, data, current_month, writer, next_listing_fee_is_renew)
        self.assertEqual(data['Etsy Ireland UC']['Etsy Ads Fees'], 3.50) 

        mock_logging_info.assert_any_call(f"Processing fee: {test_row}") 

    @patch('logging.info')
    def test_update_fees(self, mock_logging_info):
        data = {"Etsy Ireland UC": {}}

        # Test case 1: Add a new fee type
        update_fees(data, "Etsy Ireland UC", "Listing Fees", "-€0.20")
        self.assertEqual(data["Etsy Ireland UC"]["Listing Fees"], 0.20)

        # Test case 2: Add to an existing fee type
        update_fees(data, "Etsy Ireland UC", "Listing Fees", "-€0.30")
        self.assertEqual(data["Etsy Ireland UC"]["Listing Fees"], 0.50)

        # Test case 3: Subtract from an existing fee type
        update_fees(data, "Etsy Ireland UC", "Listing Fees", "€0.10")
        self.assertEqual(data["Etsy Ireland UC"]["Listing Fees"], 0.40)

        mock_logging_info.assert_any_call('Updating fees for Etsy Ireland UC, Listing Fees, €0.10')

    @patch('logging.info')
    def test_write_summarized_data(self, mock_logging_info):
        data = {
            "Etsy Ireland UC": {
                "Listing Fees": 1.20,
                "Transaction Fees": 2.50,
                "Processing Fees": 0.80,
                "Etsy Ads Fees": 4.00
            }
        }
        last_day_of_month = datetime(2024, 9, 30)
        output_file = StringIO()
        writer = csv.writer(output_file)

        write_summarized_data(data, last_day_of_month, writer)

        output_file.seek(0)
        reader = csv.reader(output_file)
        output_rows = list(reader)

        expected_rows = [
            ['30.09.2024', 'Gebühr', 'Etsy Ireland UC', 'Listing Fees', '-1,20'],
            ['30.09.2024', 'Gebühr', 'Etsy Ireland UC', 'Transaction Fees', '-2,50'],
            ['30.09.2024', 'Gebühr', 'Etsy Ireland UC', 'Processing Fees', '-0,80'],
            ['30.09.2024', 'Marketing', 'Etsy Ireland UC', 'Etsy Ads Fees', '-4,00']
        ]
        self.assertEqual(output_rows, expected_rows)

    @patch('logging.info')
    @patch('convertCsv.get_datetime_filename') 
    def test_convert_csv(self, mock_get_datetime_filename, mock_logging_info):
        mock_get_datetime_filename.return_value = '20240930_120000'
        input_csv_content = """Date,Type,Title,Info,Currency,Amount,"Fees & Taxes",Net,"Tax Details",Status,"Availability Date"
"September 10, 2024",Deposit,"€123.45 sent to your bank account",,EUR,--,--,--,--,--
"September 15, 2024",Sale,"Payment for Order #9876543210",,EUR,€88.20,--,€88.20,--,--,--
"September 15, 2024",Tax,"Sales tax paid by buyer","Order #9876543210",EUR,--,-€5.50,-€5.50,--,--,--
"September 15, 2024",Fee,"Transaction fee: Some Fee","Order #9876543210",EUR,--,-€2.20,-€2.20,--,--
"September 15, 2024",Fee,"Processing fee","Order #9876543210",EUR,--,-€1.15,-€1.15,--,--
"September 30, 2024",Marketing,"Etsy Ads","Bill for something",EUR,--,-€5.00,-€5.00,--,--
"""
        # Create a temporary input CSV file
        with open('tests/input_full.csv', 'w', newline='', encoding='utf-8') as f: # encoding added
            f.write(input_csv_content)

        convert_csv('tests/input_full.csv', 'tests/output_full.csv') # test/ added to path

        # Read the output CSV file
        with open('tests/output_full.csv', 'r', encoding='utf-8') as f: # test/ added to path
            reader = csv.reader(f)
            header = next(reader)
            output_rows = list(reader)

        # Assertions
        expected_output_rows = [
            ['30.09.2024', 'Gebühr', 'Etsy Ireland UC', 'Transaction Fees', '-2,20'],
            ['30.09.2024', 'Gebühr', 'Etsy Ireland UC', 'Processing Fees', '-1,15'],
            ['30.09.2024', 'Marketing', 'Etsy Ireland UC', 'Etsy Ads Fees', '-5,00'],
            ['15.09.2024', 'Verkauf', 'Payment', 'Bestellung #9876543210', '(€88.20 € - 5.50 € (US-Sales Taxes payed by Etsy))', '82,70'], 
            ['10.09.2024', 'Auszahlung', 'Etsy Ireland UC', 'Geldtransit/Umbuchung/Auszahlung', '-123,45']
            
            
        ]
        self.assertEqual(header, ['BUCHUNGSDATUM', 'ZUSATZINFO', 'AUFTRAGGEBER/EMPFÄNGER', 'VERWENDUNGSZWECK', 'BETRAG'])
        self.assertEqual(output_rows, expected_output_rows)

if __name__ == '__main__':
    unittest.main()