import csv
from datetime import datetime
import pandas as pd

def process_deposit(row, writer):
    date_str = row[0].strip('"')
    date = datetime.strptime(date_str, "%B %d, %Y").date()
    
    # Parse the amount from the title
    amount_str = row[2].split('€')[1].strip().split(' ')[0].replace(',', '.')
    amount = float(amount_str)

    writer.writerow([date.strftime("%d.%m.%Y"), "Auszahlung", "Etsy Ireland UC", "Geldtransit/Umbuchung/Auszahlung", "{:,.2f}".format(amount * -1).replace('.', ',')])

def process_sale(row, rows, writer):
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
            amount -= fees_taxes_value

        writer.writerow([date.strftime("%d.%m.%Y"), "Verkauf", buyer, f"Bestellung #{order_info}", "{:,.2f}".format(amount).replace('.', ',')])

def process_fee(row, data, current_month, writer, next_listing_fee_is_renew):
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

    return data, current_month, next_listing_fee_is_renew


def update_fees(data, recipient, fee_type, fees_taxes):
    if fee_type not in data[recipient]:
        data[recipient][fee_type] = 0

    if fees_taxes and fees_taxes != '--':
        if fees_taxes.startswith('-'):
            fees_taxes_value = float(fees_taxes.replace('-','').replace('€','').replace(',','.'))
            data[recipient][fee_type] += fees_taxes_value
        else:
            fees_taxes_value = float(fees_taxes.replace('€','').replace(',','.'))
            data[recipient][fee_type] -= fees_taxes_value


def write_summarized_data(data, last_day_of_month, writer):
    for recipient, fees in data.items():
        for fee_type, amount in fees.items():
            if fee_type == "Etsy Ads Fees":
                writer.writerow([last_day_of_month.strftime("%d.%m.%Y"), "Marketing", recipient, fee_type, f"-{amount:,.2f}".format(abs(amount)).replace('.', ',')])
            else:
                writer.writerow([last_day_of_month.strftime("%d.%m.%Y"), "Gebühr", recipient, fee_type, f"-{amount:,.2f}".format(abs(amount)).replace('.', ',')])



def convert_csv(input_file, output_file):
    """Converts the input CSV to the output CSV with the specified transformations."""

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

if __name__ == "__main__":
    convert_csv('input.csv', 'output.csv') 