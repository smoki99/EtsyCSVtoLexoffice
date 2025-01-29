import os
import sys
import pandas as pd
from datetime import datetime
from decimal import Decimal

# Import functions from xrechnung_generator.py
from xrechnung_generator import generate_xrechnung_lxml, load_country_codes

def process_csv_to_xrechnung(csv_filepath, output_dir):
    """
    Reads invoice data from a CSV file, generates XRechnung XML files,
    and saves them to the specified output directory.
    """

    try:
        # Load country codes
        country_codes = load_country_codes()

        # Read CSV into a pandas DataFrame
        df = pd.read_csv(csv_filepath)

        # Iterate through rows and generate XRechnung for each invoice
        for index, row in df.iterrows():
            # Extract data from CSV (adjust column names as needed)
            invoice_number = row['Invoice Number']
            order_info = row['Order Info']
            amount = Decimal(row['Amount'])
            date_str = row['Date']
            date = datetime.strptime(date_str, "%Y-%m-%d")  # Adjust date format if needed
            buyer = row['Buyer']

            # Create address details dictionary
            address_details = {
                "Street 1": row['Street 1'],
                "Street 2": row['Street 2'],
                "Ship City": row['City'],
                "Ship Zipcode": row['Zipcode'],
                "Ship Country": row['Country']
            }

            print(address_details.get("Street 1", ""))

            # Handle optional cancellation data
            is_cancellation = row.get('Is Cancellation', False)  # Use .get() for optional columns
            original_invoice_number = row.get('Original Invoice Number', None)

            # Generate XRechnung XML
            generate_xrechnung_lxml(
                invoice_number, order_info, amount, date, buyer,
                address_details, country_codes, is_cancellation,
                original_invoice_number, output_dir
            )

            print(f"Generated XRechnung for invoice: {invoice_number}")

    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_filepath}")
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing column in CSV: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python csv_to_xrechnung.py <csv_filepath> <output_directory>")
        sys.exit(1)

    csv_filepath = sys.argv[1]
    output_dir = sys.argv[2]

    process_csv_to_xrechnung(csv_filepath, output_dir) 