import csv
from datetime import datetime
import pandas as pd

def convert_csv(input_file, output_file):
    """Converts the input CSV to the output CSV with the specified transformations."""

    # Store data for aggregation
    data = {}
    
    # Read all rows into a list
    with open(input_file, 'r', encoding='utf-8') as infile, \
            open('output-unsorted.csv', 'w', newline='', encoding='utf-8') as outfile_unsorted:
        reader = csv.reader(infile)
        writer_unsorted = csv.writer(outfile_unsorted, delimiter=',')  # Define writer here

        header = next(reader)
        writer_unsorted.writerow(['BUCHUNGSDATUM', 'ZUSATZINFO', 'AUFTRAGGEBER/EMPFÄNGER', 'VERWENDUNGSZWECK', 'BETRAG'])

        rows = list(reader)  # Read remaining rows into a list

        # Process rows and store data for aggregation
        previous_row = None
        current_month = None
        for row in rows:
            date_str = row[0].strip('"') 
            date = datetime.strptime(date_str, "%B %d, %Y").date()  # Parse the date correctly
            last_day_of_month = datetime(date.year, date.month, 1) + pd.offsets.MonthEnd(0)
            last_day_of_month_str = last_day_of_month.strftime("%d.%m.%Y")

            type = row[1]
            title = row[2]
            info = row[3]
            amount_str = row[7]
            currency = row[4]
            fees_taxes = row[6]

            # Only print debug information for Deposit and Sale rows
            if type == "Deposit" or type == "Sale":
                print(f"Processing row: Date: {date_str}, Type: {type}, Title: {title}, Info: {info}, Amount: {amount_str}, Currency: {currency}, Fees & Taxes: {fees_taxes}") # Debug output for each row

            # Handling Deposits with Empty Amounts
            if type == "Deposit": 
                # Parse the amount from the title
                amount_str = title.split('€')[1].strip().split(' ')[0].replace(',', '.')
                print(f"Parsed Amount: {amount_str}")

                # Convert the amount to a float
                amount = float(amount_str)

                # Write Deposit row directly to the CSV
                writer_unsorted.writerow([date.strftime("%d.%m.%Y"), "Auszahlung", "Etsy Ireland UC", "Geldtransit/Umbuchung/Auszahlung", "{:,.2f}".format(amount * -1).replace('.', ',')])
                print(f"Writing Deposit row: {date.strftime('%d.%m.%Y')},Auszahlung,Etsy Ireland UC,Geldtransit/Umbuchung/Auszahlung,{amount * -1:,.2f}")  # Debug Output
            elif type == "Sale":
                if "for Order" in title: # Check if "#" exists before splitting
                    order_info = title.split("#")[1].strip()  # Extract Order number from Title
                    buyer = title.split("for Order")[0].strip()  # Extract Buyer from Title
                    
                    # Parse the amount from the title
                    amount_str = amount_str.replace('€','').replace(',','.').strip()
                    print(f"Parsed Amount: {amount_str}")

                    # Convert the amount to a float
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
                        print(f"Subtracting Sales Tax: {fees_taxes_value}")

                    # Write Sale row directly to the CSV
                    writer_unsorted.writerow([date.strftime("%d.%m.%Y"), "Verkauf", buyer, f"Bestellung #{order_info}", "{:,.2f}".format(amount).replace('.', ',')])
                    print(f"Writing Sale row: {date.strftime('%d.%m.%Y')},Verkauf,{buyer},Bestellung #{order_info},{amount:,.2f}") # Debug Output
            elif type == "Fee":
                if "Etsy Ireland UC" not in data:
                    data["Etsy Ireland UC"] = {}

                # Check for a change in month
                if current_month is not None and current_month != date.month:
                    print(f"Month changed: {current_month} -> {date.month}")
                    # Write summarized data for the previous month
                    print(f"Data to be written: {data}")
                    for recipient, fees in data.items():
                        for fee_type, amount in fees.items():
                            print(f"Writing {fee_type}: {amount}") # Debug output to pinpoint the issue
                            if fee_type == "Etsy Ads Fees":
                                writer_unsorted.writerow([last_day_of_month_str, "Marketing", recipient, fee_type, f"-{amount:,.2f}".format(abs(amount)).replace('.', ',')])
                            else:
                                writer_unsorted.writerow([last_day_of_month_str, "Gebühr", recipient, fee_type, f"-{amount:,.2f}".format(abs(amount)).replace('.', ',')])

                    # Reset data for the new month
                    data = {} 
                current_month = date.month
                
                if "Listing fee" in title and ignore_next_listing_fee:
                    # Add the fee amount to the "Renew Sold Fees" summary entry
                    if "Renew Sold Fees" not in data["Etsy Ireland UC"]:
                        data["Etsy Ireland UC"]["Renew Sold Fees"] = 0
                    if fees_taxes and fees_taxes != '--':
                        print(f"Parsing fees_taxes: {fees_taxes}")
                        if fees_taxes.startswith('-'):
                            fees_taxes_value = float(fees_taxes.replace('-','').replace('€','').replace(',','.'))
                            data["Etsy Ireland UC"]["Renew Sold Fees"] += fees_taxes_value
                            print(f"Updating Renew Sold Fees (positive): {data['Etsy Ireland UC']['Renew Sold Fees']}")
                        else:
                            fees_taxes_value = float(fees_taxes.replace('€','').replace(',','.'))
                            data["Etsy Ireland UC"]["Renew Sold Fees"] -= fees_taxes_value
                            print(f"Updating Renew Sold Fees (negative): {data['Etsy Ireland UC']['Renew Sold Fees']}")
                    ignore_next_listing_fee = False
                elif "Listing fee" in title:
                    if "Listing Fees" not in data["Etsy Ireland UC"]:
                        data["Etsy Ireland UC"]["Listing Fees"] = 0
                    if fees_taxes and fees_taxes != '--':
                        print(f"Parsing fees_taxes: {fees_taxes}")
                        if fees_taxes.startswith('-'):
                            fees_taxes_value = float(fees_taxes.replace('-','').replace('€','').replace(',','.'))
                            data["Etsy Ireland UC"]["Listing Fees"] += fees_taxes_value
                            print(f"Updating Listing Fees (positive): {data['Etsy Ireland UC']['Listing Fees']}")
                        else:
                            fees_taxes_value = float(fees_taxes.replace('€','').replace(',','.'))
                            data["Etsy Ireland UC"]["Listing Fees"] -= fees_taxes_value
                            print(f"Updating Listing Fees (negative): {data['Etsy Ireland UC']['Listing Fees']}")
                elif "Transaction fee" in title:
                    if "Transaction Fees" not in data["Etsy Ireland UC"]:
                        data["Etsy Ireland UC"]["Transaction Fees"] = 0
                    if fees_taxes and fees_taxes != '--':
                        print(f"Parsing fees_taxes: {fees_taxes}")
                        if fees_taxes.startswith('-'):
                            fees_taxes_value = float(fees_taxes.replace('-','').replace('€','').replace(',','.'))
                            data["Etsy Ireland UC"]["Transaction Fees"] += fees_taxes_value
                            print(f"Updating Transaction Fees (positive): {data['Etsy Ireland UC']['Transaction Fees']}")
                        else:
                            fees_taxes_value = float(fees_taxes.replace('€','').replace(',','.'))
                            data["Etsy Ireland UC"]["Transaction Fees"] -= fees_taxes_value
                            print(f"Updating Transaction Fees (negative): {data['Etsy Ireland UC']['Transaction Fees']}")
                elif "Processing fee" in title:
                    if "Processing Fees" not in data["Etsy Ireland UC"]:
                        data["Etsy Ireland UC"]["Processing Fees"] = 0
                    if fees_taxes and fees_taxes != '--':
                        print(f"Parsing fees_taxes: {fees_taxes}")
                        if fees_taxes.startswith('-'):
                            fees_taxes_value = float(fees_taxes.replace('-','').replace('€','').replace(',','.'))
                            data["Etsy Ireland UC"]["Processing Fees"] += fees_taxes_value
                            print(f"Updating Processing Fees (positive): {data['Etsy Ireland UC']['Processing Fees']}")
                        else:
                            fees_taxes_value = float(fees_taxes.replace('€','').replace(',','.'))
                            data["Etsy Ireland UC"]["Processing Fees"] -= fees_taxes_value
                            print(f"Updating Processing Fees (negative): {data['Etsy Ireland UC']['Processing Fees']}")
                        ignore_next_listing_fee = True # Ignore next Listing Fee
            elif type == "Marketing":
                if "Etsy Ireland UC" not in data:
                    data["Etsy Ireland UC"] = {}
                if "Etsy Ads Fees" not in data["Etsy Ireland UC"]:
                    data["Etsy Ireland UC"]["Etsy Ads Fees"] = 0
                if fees_taxes and fees_taxes != '--':
                    print(f"Parsing fees_taxes: {fees_taxes}")
                    if fees_taxes.startswith('-'):
                        fees_taxes_value = float(fees_taxes.replace('-','').replace('€','').replace(',','.'))
                        data["Etsy Ireland UC"]["Etsy Ads Fees"] += fees_taxes_value
                        print(f"Updating Etsy Ads Fees (positive): {data['Etsy Ireland UC']['Etsy Ads Fees']}")
                    else:
                        fees_taxes_value = float(fees_taxes.replace('€','').replace(',','.'))
                        data["Etsy Ireland UC"]["Etsy Ads Fees"] -= fees_taxes_value
                        print(f"Updating Etsy Ads Fees (negative): {data['Etsy Ireland UC']['Etsy Ads Fees']}")

        # Write summarized data for the last month
        print(f"Data to be written: {data}")
        for recipient, fees in data.items():
            for fee_type, amount in fees.items():
                print(f"Writing {fee_type}: {amount}") # Debug output to pinpoint the issue
                if fee_type == "Etsy Ads Fees":
                    writer_unsorted.writerow([last_day_of_month_str, "Marketing", recipient, fee_type, f"-{amount:,.2f}".format(abs(amount)).replace('.', ',')])
                else:
                    writer_unsorted.writerow([last_day_of_month_str, "Gebühr", recipient, fee_type, f"-{amount:,.2f}".format(abs(amount)).replace('.', ',')])

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
    import pandas as pd
    convert_csv('input.csv', 'output.csv') 