import csv
from datetime import datetime
import pandas as pd
import logging
import os

# Function to get the current datetime in the desired format
def get_datetime_filename():
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")

# Configure logging (filename will be updated later)
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')


def process_deposit(row, writer):
    logging.info(f"Calling process_deposit with row: {row}")  # Log the function call
    date_str = row[0].strip('"')
    date = datetime.strptime(date_str, "%B %d, %Y").date()
    
    # Parse the amount from the title
    amount_str = row[2].split('€')[1].strip().split(' ')[0].replace(',', '.')
    amount = float(amount_str)

    output_row = [date.strftime("%d.%m.%Y"), "Auszahlung", "Etsy Ireland UC", "Geldtransit/Umbuchung/Auszahlung", "{:,.2f}".format(amount * -1).replace('.', ',')]
    writer.writerow(output_row)
    logging.info(f"Wrote row to CSV: {output_row}")  # Log the written row
    logging.info(f"Processed Deposit: {row}")  # Log the processed row

def process_sale(row, rows, writer):
    logging.info(f"Calling process_sale with row: {row}")  # Log the function call
    date_str = row[0].strip('"')
    date = datetime.strptime(date_str, "%B %d, %Y").date()
    
    if "for Order" in row[2]:
        order_info = row[2].split("#")[1].strip()
        buyer = row[2].split("for Order")[0].strip()

        # Parse the amount 
        amount_str = row[7].replace('€','').replace(',','.').strip()
        amount = float(amount_str)

        # Find the corresponding Tax row
        tax_row = None
        for i in range(len(rows)):
            if rows[i][1] == "Tax" and rows[i][3] == f"Order #{order_info}":
                tax_row = rows[i]
                break

        # If Tax row found, subtract tax from the sale amount
        if tax_row:
            fees_taxes_value = float(tax_row[6].replace('-', '').replace('€', '').replace(',', '.'))
            logging.info(f"Found sales tax for order #{order_info}: {fees_taxes_value} EUR")  # Log sales tax amount with EUR
            amount -= fees_taxes_value
            logging.info(f"Calculated final sale value after subtracting sales tax: {amount} EUR") # Log calculated sale value with EUR
        else:
            logging.info(f"No sales tax found for order #{order_info}")  # Log if no sales tax found


        output_row = [date.strftime("%d.%m.%Y"), "Verkauf", buyer, f"Bestellung #{order_info}", "{:,.2f}".format(amount).replace('.', ',')]
        writer.writerow(output_row)
        logging.info(f"Wrote row to CSV: {output_row}")  # Log the written row
    logging.info(f"Processed Sale: {row}")  # Log the processed row

def process_fee(row, data, current_month, writer, next_listing_fee_is_renew):
    logging.info(f"Calling process_fee with row: {row}")  # Log the function call
    date_str = row[0].strip('"')
    date = datetime.strptime(date_str, "%B %d, %Y").date()
    
    if "Etsy Ireland UC" not in data:
        data["Etsy Ireland UC"] = {}

    # Check for a change in month
    if current_month is not None and current_month != date.month:
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

    logging.info(f"Processed Fee: {row}")  # Log the processed row
    return data, current_month, next_listing_fee_is_renew


def update_fees(data, recipient, fee_type, fees_taxes):
    logging.info(f"Calling update_fees with recipient: {recipient}, fee_type: {fee_type}, fees_taxes: {fees_taxes}") # Log the function call
    if fee_type not in data[recipient]:
        data[recipient][fee_type] = 0

    if fees_taxes and fees_taxes != '--':
        if fees_taxes.startswith('-'):
            fees_taxes_value = float(fees_taxes.replace('-','').replace('€', '').replace(',','.'))
            previous_sum = data[recipient][fee_type]
            data[recipient][fee_type] += fees_taxes_value
            logging.info(f"Added {fees_taxes_value} EUR to {fee_type} for {recipient} (before: {previous_sum} EUR + fee: {fees_taxes_value} EUR = sum: {data[recipient][fee_type]} EUR)")  # Log the added fee with sum
        else:
            fees_taxes_value = float(fees_taxes.replace('€', '').replace(',','.'))
            previous_sum = data[recipient][fee_type]
            data[recipient][fee_type] -= fees_taxes_value
            logging.info(f"Subtracted {fees_taxes_value} EUR from {fee_type} for {recipient} (before: {previous_sum} EUR - fee: {fees_taxes_value} EUR = sum: {data[recipient][fee_type]} EUR)")  # Log the subtracted fee with sum


def write_summarized_data(data, last_day_of_month, writer):
    logging.info(f"Calling write_summarized_data with last_day_of_month: {last_day_of_month}")  # Log the function call
    for recipient, fees in data.items():
        for fee_type, amount in fees.items():
            output_row = None
            if fee_type == "Etsy Ads Fees":
                output_row = [last_day_of_month.strftime("%d.%m.%Y"), "Marketing", recipient, fee_type, f"-{amount:,.2f}".format(abs(amount)).replace('.', ',')]
            else:
                output_row = [last_day_of_month.strftime("%d.%m.%Y"), "Gebühr", recipient, fee_type, f"-{amount:,.2f}".format(abs(amount)).replace('.', ',')]
            if output_row:
                writer.writerow(output_row)
                logging.info(f"Wrote row to CSV: {output_row}")  # Log the written row
    logging.info(f"Wrote Summarized Data for {last_day_of_month}")  # Log the summarized data


def convert_csv(input_file, output_file):
    """Converts the input CSV to the output CSV with the specified transformations."""

    # Generate filename with datetime
    filename_prefix = "convert_csv"
    datetime_part = get_datetime_filename()
    log_filename = f"{filename_prefix}_{datetime_part}.log"

    # Remove any existing handlers
    for handler in logging.getLogger().handlers[:]:  
        logging.getLogger().removeHandler(handler)

    # Create a new FileHandler for the log file
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Add the new handler to the logger
    logging.getLogger().addHandler(file_handler)


    # Store data for aggregation
    data = {}
    current_month = None
    next_listing_fee_is_renew = False # Track if the next listing fee is a renew fee

    # Read all rows into a list
    with open(input_file, 'r', encoding='utf-8') as infile, \
            open('output-unsorted.csv', 'w', newline='', encoding='utf-8') as outfile_unsorted:
        reader = csv.reader(infile)
        writer_unsorted = csv.writer(outfile_unsorted, delimiter=',')
        writer_unsorted.writerow(['BUCHUNGSDATUM', 'ZUSATZINFO', 'AUFTRAGGEBER/EMPFÄNGER', 'VERWENDUNGSZWECK', 'BETRAG'])

        rows = list(reader)
        logging.info(f"Read {len(rows)} rows from input file.")  # Log the number of rows read


        for row in rows:
            type = row[1]
            
            if type == "Deposit":
                process_deposit(row, writer_unsorted)
            elif type == "Sale":
                process_sale(row, rows, writer_unsorted)
            elif type == "Fee":
                data, current_month, next_listing_fee_is_renew = process_fee(row, data, current_month, 
                                                                          writer_unsorted, next_listing_fee_is_renew)
            elif type == "Marketing":
                data, current_month, next_listing_fee_is_renew = process_fee(row, data, current_month, 
                                                                          writer_unsorted, next_listing_fee_is_renew)
        # Write summarized data for the last month
        write_summarized_data(data, datetime(datetime.strptime(row[0].strip('"'), "%B %d, %Y").date().year, 
                                                    datetime.strptime(row[0].strip('"'), "%B %d, %Y").date().month, 1) 
                                            + pd.offsets.MonthEnd(0), writer_unsorted)

    # Sort the rows by BUCHUNGSDATUM descending
    with open('output-unsorted.csv', 'r', encoding='utf-8') as outfile_unsorted, \
            open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        reader_unsorted = csv.reader(outfile_unsorted)
        writer = csv.writer(outfile, delimiter=',')
        header = next(reader_unsorted)
        writer.writerow(header)

        rows = list(reader_unsorted)
        rows.sort(key=lambda row: datetime.strptime(row[0], '%d.%m.%Y'), reverse=True)
        writer.writerows(rows)

    logging.info(f"Conversion complete. Output saved to {output_file}")  # Log completion


if __name__ == "__main__":
    convert_csv('input.csv', 'output.csv') 