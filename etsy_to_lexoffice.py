import csv
from datetime import datetime
import pandas as pd
import logging
import hashlib

# Function to calculate Hash SHA-256 for a file
def calculate_file_hash(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Function to get the current datetime in the desired format
def get_datetime_filename():
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")


def configure_logging(filename):
    """Configures logging to write to the specified file."""
    # Remove any existing handlers
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)

    # Create a new FileHandler for the log file
    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Add the new handler to the logger
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.INFO)


def process_deposit(row, writer):
    try:
        logging.info(f"Processing deposit: {row}")
        date = datetime.strptime(row[0].strip('"'), "%B %d, %Y").date()
        amount = float(row[2].split('€')[1].strip().split(' ')[0].replace(',', '.'))

        output_row = [
            date.strftime("%d.%m.%Y"),
            "Auszahlung",
            "Etsy Ireland UC",
            "Geldtransit/Umbuchung/Auszahlung",
            f"{-amount:,.2f}".replace('.', ',')
        ]
        writer.writerow(output_row)
        logging.info(f"Wrote row to CSV: {output_row}")
    except Exception as e:
        logging.error(f"Error processing deposit row: {row}. Error: {e}")
        raise


def process_sale(row, rows, writer):
    try:
        logging.info(f"Processing sale: {row}")
        date = datetime.strptime(row[0].strip('"'), "%B %d, %Y").date()

        if "for Order" in row[2]:
            order_info = row[2].split("#")[1].strip()
            buyer = row[2].split("for Order")[0].strip()
            amount = float(row[7].replace('€', '').replace(',', '.').strip())

            tax_row = None
            for r in rows:
                if r[1] == "Tax" and r[3] == f"Order #{order_info}":
                    tax_row = r
                    break

            if tax_row:
                fees_taxes_value = float(tax_row[6].replace('-', '').replace('€', '').replace(',', '.'))
                amount -= fees_taxes_value
                calculation_details = f"({row[7].strip()} € - {fees_taxes_value:.2f} € (US-Sales Taxes payed by Etsy))"
            else:
                calculation_details = f"({row[7].strip()} €)"

            output_row = [
                date.strftime("%d.%m.%Y"),
                "Verkauf",
                buyer,
                f"Bestellung #{order_info} {calculation_details}",
                f"{amount:,.2f}".replace('.', ',')
            ]
            writer.writerow(output_row)
            logging.info(f"Wrote row to CSV: {output_row}")
    except Exception as e:
        logging.error(f"Error processing sale row: {row}. Error: {e}")
        raise


def process_fee(row, data, current_month, writer, next_listing_fee_is_renew):
    try:
        logging.info(f"Processing fee: {row}")
        date = datetime.strptime(row[0].strip('"'), "%B %d, %Y").date()

        if "Etsy Ireland UC" not in data:
            data["Etsy Ireland UC"] = {}

        if current_month and current_month != date.month:
            write_summarized_data(data, datetime(date.year, date.month, 1) + pd.offsets.MonthEnd(0), writer)
            data.clear()
        current_month = date.month

        title = row[2]
        fees_taxes = row[6]

        if "Listing fee" in title and next_listing_fee_is_renew:
            update_fees(data, "Etsy Ireland UC", "Renew Sold Fees", fees_taxes)
            next_listing_fee_is_renew = False
        elif "Listing fee" in title:
            update_fees(data, "Etsy Ireland UC", "Listing Fees", fees_taxes)
        elif "Transaction fee" in title:
            update_fees(data, "Etsy Ireland UC", "Transaction Fees", fees_taxes)
        elif "Processing fee" in title:
            update_fees(data, "Etsy Ireland UC", "Processing Fees", fees_taxes)
            next_listing_fee_is_renew = True
        elif "Etsy Ads" in title:
            update_fees(data, "Etsy Ireland UC", "Etsy Ads Fees", fees_taxes)

        return data, current_month, next_listing_fee_is_renew
    except Exception as e:
        logging.error(f"Error processing fee row: {row}. Error: {e}")
        raise


def update_fees(data, recipient, fee_type, fees_taxes):
    logging.info(f"Updating fees for {recipient}, {fee_type}, {fees_taxes}")
    if fee_type not in data[recipient]:
        data[recipient][fee_type] = 0

    if fees_taxes and fees_taxes != '--':
        fees_taxes_value = float(fees_taxes.replace('-', '').replace('€', '').replace(',', '.'))
        if fees_taxes.startswith('-'):
            data[recipient][fee_type] += fees_taxes_value
            logging.info(f"Added {fees_taxes_value:.2f} EUR to {fee_type} for {recipient} (new sum: {data[recipient][fee_type]:.2f} EUR)")
        else:
            data[recipient][fee_type] -= fees_taxes_value
            logging.info(f"Subtracted {fees_taxes_value:.2f} EUR from {fee_type} for {recipient} (new sum: {data[recipient][fee_type]:.2f} EUR)")


def write_summarized_data(data, last_day_of_month, writer):
    logging.info(f"Writing summarized data for {last_day_of_month}")
    for recipient, fees in data.items():
        for fee_type, amount in fees.items():
            if fee_type == "Etsy Ads Fees":
                output_row = [
                    last_day_of_month.strftime("%d.%m.%Y"), 
                    "Marketing", 
                    recipient, 
                    fee_type, 
                    f"{-amount:,.2f}".format(abs(amount)).replace('.', ',')
                ]
            else:
                output_row = [
                    last_day_of_month.strftime("%d.%m.%Y"), 
                    "Gebühr", 
                    recipient, 
                    fee_type, 
                    f"{-amount:,.2f}".format(abs(amount)).replace('.', ',')
                ]

            if output_row:
                writer.writerow(output_row)
                logging.info(f"Wrote row to CSV: {output_row}")


def convert_csv(input_file, output_file):
    """Converts the input CSV to the output CSV with the specified transformations."""
    filename_prefix = "convert_csv"
    datetime_part = get_datetime_filename()
    log_filename = f"{filename_prefix}_{datetime_part}.log"

    configure_logging(log_filename)

    # Log input file name and hash
    logging.info(f"Input file: {input_file}")
    logging.info(f"Input file hash: {calculate_file_hash(input_file)}")

    data = {}
    current_month = None
    next_listing_fee_is_renew = False 

    with open(input_file, 'r', encoding='utf-8') as infile, \
            open('output-unsorted.csv', 'w', newline='', encoding='utf-8') as outfile_unsorted:
        reader = csv.reader(infile)
        writer_unsorted = csv.writer(outfile_unsorted, delimiter=',')
        writer_unsorted.writerow(['BUCHUNGSDATUM', 'ZUSATZINFO', 'AUFTRAGGEBER/EMPFÄNGER', 'VERWENDUNGSZWECK', 'BETRAG'])

        rows = list(reader)
        logging.info(f"Read {len(rows)} rows from input file.")

        for row in rows:
            type = row[1]
            if type == "Deposit":
                process_deposit(row, writer_unsorted)
            elif type == "Sale":
                process_sale(row, rows, writer_unsorted)
            elif type in ("Fee", "Marketing"):
                data, current_month, next_listing_fee_is_renew = process_fee(row, data, current_month, 
                                                                          writer_unsorted, next_listing_fee_is_renew)

        last_row_date = datetime.strptime(rows[-1][0].strip('"'), "%B %d, %Y").date()
        write_summarized_data(data, datetime(last_row_date.year, last_row_date.month, 1) + pd.offsets.MonthEnd(0), writer_unsorted)

    with open('output-unsorted.csv', 'r', encoding='utf-8') as outfile_unsorted, \
            open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        reader_unsorted = csv.reader(outfile_unsorted)
        writer = csv.writer(outfile, delimiter=',')
        header = next(reader_unsorted)
        writer.writerow(header)

        rows = list(reader_unsorted)
        rows.sort(key=lambda row: datetime.strptime(row[0], '%d.%m.%Y'), reverse=True)
        writer.writerows(rows)

    # Log output file name and hash
    logging.info(f"Conversion complete. Output saved to {output_file}")
    logging.info(f"Output file hash: {calculate_file_hash(output_file)}")


if __name__ == "__main__":
    convert_csv('etsy_statement_2024_10.csv', 'etsy_statement_2024_10_processed.csv') 