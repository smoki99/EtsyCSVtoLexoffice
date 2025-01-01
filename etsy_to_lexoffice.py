import csv
from datetime import datetime
import logging
import hashlib
import argparse
import os
import glob
from decimal import Decimal
from dotenv import load_dotenv
import pandas as pd
from lxml import etree

# Load environment variables from .env file
load_dotenv()

# Global dictionary to store invoice_number to order_number mapping
invoice_order_mapping = {}

# Configuration for EU countries and VAT rates
EU_COUNTRIES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus", "CZ": "Czech Republic",
    "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "ES": "Spain", "FI": "Finland", "FR": "France",
    "GR": "Greece", "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LT": "Lithuania",
    "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta", "NL": "Netherlands", "PL": "Poland",
    "PT": "Portugal", "RO": "Romania", "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia"
}

# Sender address from .env file
SENDER_COMPANY_NAME = os.getenv("SENDER_COMPANY_NAME")
SENDER_NAME = os.getenv("SENDER_NAME")
SENDER_STREET = os.getenv("SENDER_STREET")
SENDER_CITY = os.getenv("SENDER_CITY")
SENDER_POSTALCODE = os.getenv("SENDER_POSTALCODE")
SENDER_COUNTRY = os.getenv("SENDER_COUNTRY")
SENDER_PHONE_NUMBER = os.getenv("SENDER_PHONE_NUMBER")
SENDER_MAIL = os.getenv("SENDER_MAIL")
SENDER_VAT_ID = os.getenv("SENDER_VAT_ID")
SENDER_HRA = os.getenv("SENDER_HRA")

# Global counter for invoice numbers
INVOICE_COUNTER = 0


def calculate_file_hash(filepath):
    """Calculates the SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_datetime_filename():
    """Gets the current datetime in the desired filename format."""
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")


def configure_logging(filename):
    """Configures logging to write to the specified file."""
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)

    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.INFO)


def process_deposit(row, writer):
    """Processes a deposit row from the CSV."""
    try:
        logging.info("Processing deposit: %s", row)
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
        logging.info("Wrote row to CSV: %s", output_row)
    except Exception as e:  # Catching a too general exception is ok in this context since we log the error.
        logging.error("Error processing deposit row: %s. Error: %s", row, e)
        raise


def load_orders_file(orders_directory="."):
    """Load the orders CSV file and return a dictionary with Order ID as keys."""
    orders_dict = {}
    for filename in glob.glob(os.path.join(orders_directory, "EtsySoldOrders*.csv")):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    orders_dict[row["Order ID"]] = {
                        "Full Name": row["Full Name"],
                        "Street 1": row["Street 1"],
                        "Street 2": row["Street 2"],
                        "Ship City": row["Ship City"],
                        "Ship State": row["Ship State"],
                        "Ship Zipcode": row["Ship Zipcode"],
                        "Ship Country": row["Ship Country"]
                    }
            logging.info("Loaded orders from: %s", filename)
            logging.info(f"Input file hash: {calculate_file_hash(filename)}")
        except Exception as e:
            logging.error("Error loading orders from %s: %s", filename, e)
    return orders_dict


def load_country_codes(csv_filepath="country_codes.csv"):
    """Loads country codes from a CSV file into a dictionary."""
    country_codes = {}
    try:
        with open(csv_filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                country_codes[row['country_name']] = row['alpha_2']
    except FileNotFoundError:
        logging.error("Error: Country codes file not found at %s", csv_filepath)
        # Consider exiting the program or using default values
    return country_codes


def get_country_code(country_name, country_codes):
    """Maps a country name to its ISO 3166-1 alpha-2 code."""
    return country_codes.get(country_name, "")  # Return empty string if not found


def generate_invoice_number(date, is_cancellation=False):
    """Generates a unique invoice number based on the date, with an optional -STORNO suffix."""
    global INVOICE_COUNTER
    INVOICE_COUNTER += 1
    year = str(date.year)[-2:]
    month = str(date.month).zfill(2)
    invoice_number = f"ETSY-{year}{month}-{INVOICE_COUNTER:04}"
    if is_cancellation:
        invoice_number += "-STORNO"
    return invoice_number


def generate_xrechnung_lxml(invoice_number, order_info, amount, date,
                            address_details, country_codes, is_cancellation=False,
                            original_invoice_number=None):
    """Generates an XRechnung XML file."""

    # Create Rechnungen folder if it doesn't exist
    invoice_folder = "Rechnungen"
    if not os.path.exists(invoice_folder):
        os.makedirs(invoice_folder)

    # Determine VAT rate and note based on country code from mapping
    country_code = get_country_code(address_details.get("Ship Country", ""), country_codes)
    if country_code not in EU_COUNTRIES:
        vat_rate = Decimal("0.00")
        vat_category = "G"  # Export outside the EU
        vat_note = "Steuerfreie Ausfuhrlieferung"
    else:
        vat_rate = Decimal("0.19")
        vat_category = "S"  # Standard rate
        vat_note = "Innergemeinschaftliche Lieferung, Rechnungsstellung mit deutscher Umsatzsteuer aufgrund Kleinunternehmerregelung bis 10.000€ Umsatz."

    # Calculate VAT amount and total amount
    #vat_amount = (Decimal(str(amount)) * vat_rate).quantize(Decimal("0.01"))
    vat_amount = (Decimal(amount) * vat_rate) / (1 + vat_rate)
    vat_amount = vat_amount.quantize(Decimal("0.01"))

    total_amount = Decimal(str(amount)) - vat_amount

    # Negate amounts for cancellation invoices
    if is_cancellation:
        amount = -amount
        vat_amount = -vat_amount
        total_amount = -total_amount

    # Define namespaces
    nsmap = {
        None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }

    # Create root element using QName and nsmap
    root = etree.Element(etree.QName(nsmap[None], "Invoice"), nsmap=nsmap)

    # Add schema location information to the root element
    root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
        "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2 "
        "http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-Invoice-2.1.xsd"
    )

    # Add CustomizationID
    customization_id = etree.SubElement(root, etree.QName(nsmap["cbc"], "CustomizationID"))
    customization_id.text = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"

    # Add ProfileID
    profile_id = etree.SubElement(root, etree.QName(nsmap["cbc"], "ProfileID"))
    profile_id.text = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

    # Add invoice number
    etree.SubElement(root, etree.QName(nsmap["cbc"], "ID")).text = invoice_number

    # Add issue date
    etree.SubElement(root, etree.QName(nsmap["cbc"], "IssueDate")).text = date.strftime("%Y-%m-%d")

    # Add due date
    due_date = date + pd.DateOffset(days=14)
    etree.SubElement(root, etree.QName(nsmap["cbc"], "DueDate")).text = due_date.strftime("%Y-%m-%d")

    # Add invoice type code (380 = commercial invoice, 381 = corrected invoice)
    if is_cancellation:
        etree.SubElement(root, etree.QName(nsmap["cbc"], "InvoiceTypeCode")).text = "381"
    else:
        etree.SubElement(root, etree.QName(nsmap["cbc"], "InvoiceTypeCode")).text = "380"

    # Add document currency code
    etree.SubElement(root, etree.QName(nsmap["cbc"], "DocumentCurrencyCode")).text = "EUR"

    # B2C keine Leitweg ID
    #etree.SubElement(root, etree.QName(nsmap["cbc"], "BuyerReference")).text = "n/a"

    # Add Billing Reference
    if is_cancellation and original_invoice_number:
        billing_reference = etree.SubElement(root, etree.QName(nsmap["cac"], "BillingReference"))
        invoice_document_reference = etree.SubElement(billing_reference,
                                                       etree.QName(nsmap["cac"], "InvoiceDocumentReference"))
        etree.SubElement(invoice_document_reference, etree.QName(nsmap["cbc"], "ID")).text = original_invoice_number

    # Add AccountingSupplierParty
    supplier_party = etree.SubElement(root, etree.QName(nsmap["cac"], "AccountingSupplierParty"))
    party = etree.SubElement(supplier_party, etree.QName(nsmap["cac"], "Party"))

    # Add seller Email (PEPPOL-EN16931-R020)
    etree.SubElement(party, etree.QName(nsmap["cbc"], "EndpointID"), attrib={"schemeID": "EM"}).text = SENDER_MAIL

    # Add seller name
    party_name = etree.SubElement(party, etree.QName(nsmap["cac"], "PartyName"))
    etree.SubElement(party_name, etree.QName(nsmap["cbc"], "Name")).text = SENDER_NAME

    # Add seller postal address
    postal_address = etree.SubElement(party, etree.QName(nsmap["cac"], "PostalAddress"))
    etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "StreetName")).text = SENDER_STREET
    etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "CityName")).text = SENDER_CITY
    etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "PostalZone")).text = SENDER_POSTALCODE
    country = etree.SubElement(postal_address, etree.QName(nsmap["cac"], "Country"))
    etree.SubElement(country, etree.QName(nsmap["cbc"], "IdentificationCode")).text = SENDER_COUNTRY

    # Add seller tax scheme
    party_tax_scheme = etree.SubElement(party, etree.QName(nsmap["cac"], "PartyTaxScheme"))
    etree.SubElement(party_tax_scheme, etree.QName(nsmap["cbc"], "CompanyID")).text = SENDER_VAT_ID
    tax_scheme = etree.SubElement(party_tax_scheme, etree.QName(nsmap["cac"], "TaxScheme"))
    etree.SubElement(tax_scheme, etree.QName(nsmap["cbc"], "ID")).text = "VAT"

    # Add seller legal entity
    legal_entity = etree.SubElement(party, etree.QName(nsmap["cac"], "PartyLegalEntity"))
    etree.SubElement(legal_entity, etree.QName(nsmap["cbc"], "RegistrationName")).text = SENDER_COMPANY_NAME
    # etree.SubElement(legal_entity, etree.QName(nsmap["cbc"], "CompanyID"), attrib={"schemeID": "0201"}).text = SENDER_HRA
    etree.SubElement(legal_entity, etree.QName(nsmap["cbc"], "CompanyID")).text = SENDER_HRA

    # Add seller contact
    contact = etree.SubElement(party, etree.QName(nsmap["cac"], "Contact"))
    etree.SubElement(contact, etree.QName(nsmap["cbc"], "Name")).text = SENDER_NAME
    etree.SubElement(contact, etree.QName(nsmap["cbc"], "Telephone")).text = SENDER_PHONE_NUMBER
    etree.SubElement(contact, etree.QName(nsmap["cbc"], "ElectronicMail")).text = SENDER_MAIL

    # Add AccountingCustomerParty
    customer_party = etree.SubElement(root, etree.QName(nsmap["cac"], "AccountingCustomerParty"))
    party = etree.SubElement(customer_party, etree.QName(nsmap["cac"], "Party"))

    # Add Buyer Email (PEPPOL-EN16931-R020) - Since we not have we write no-mail@etsy.com
    # NO Buyer Email
    etree.SubElement(party, etree.QName(nsmap["cbc"], "EndpointID"), attrib={"schemeID": "EM"}).text = "no-email@etsy.com"

    # Add buyer postal address
    postal_address = etree.SubElement(party, etree.QName(nsmap["cac"], "PostalAddress"))
    etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "StreetName")).text = "Straße Anonymisiert"  # address_details.get("Street 1", "")
    if address_details.get("Street 2", "") != "":
        etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "AdditionalStreetName")).text = address_details.get("Street 2", "")
    etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "CityName")).text = address_details.get("Ship City", "")
    etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "PostalZone")).text = address_details.get("Ship Zipcode", "")
    country = etree.SubElement(postal_address, etree.QName(nsmap["cac"], "Country"))
    etree.SubElement(country, etree.QName(nsmap["cbc"], "IdentificationCode")).text = get_country_code(
        address_details.get("Ship Country", ""), country_codes)

    # Add buyer legal entity
    legal_entity = etree.SubElement(party, etree.QName(nsmap["cac"], "PartyLegalEntity"))
    etree.SubElement(legal_entity, etree.QName(nsmap["cbc"], "RegistrationName")).text = "Name Anonymisiert"  # buyer

    # Add payment means (42 = Payment into an account)
    # Etsy pays to my Bank Account, that's why 42 is correct
    payment_means = etree.SubElement(root, etree.QName(nsmap["cac"], "PaymentMeans"))
    etree.SubElement(payment_means, etree.QName(nsmap["cbc"], "PaymentMeansCode")).text = "42"

    # Add tax total
    tax_total = etree.SubElement(root, etree.QName(nsmap["cac"], "TaxTotal"))
    etree.SubElement(tax_total, etree.QName(nsmap["cbc"], "TaxAmount"), attrib={"currencyID": "EUR"}).text = f"{vat_amount:.2f}"

    tax_subtotal = etree.SubElement(tax_total, etree.QName(nsmap["cac"], "TaxSubtotal"))
    etree.SubElement(tax_subtotal, etree.QName(nsmap["cbc"], "TaxableAmount"),
                     attrib={"currencyID": "EUR"}).text = f"{amount:.2f}"
    etree.SubElement(tax_subtotal, etree.QName(nsmap["cbc"], "TaxAmount"),
                     attrib={"currencyID": "EUR"}).text = f"{vat_amount:.2f}"
    tax_category = etree.SubElement(tax_subtotal, etree.QName(nsmap["cac"], "TaxCategory"))
    etree.SubElement(tax_category, etree.QName(nsmap["cbc"], "ID")).text = vat_category
    etree.SubElement(tax_category, etree.QName(nsmap["cbc"], "Percent")).text = f"{vat_rate * 100:.2f}"
    # Add exemption reason if the rate is 0
    if vat_rate == 0:
        etree.SubElement(tax_category, etree.QName(nsmap["cbc"], "TaxExemptionReason")).text = vat_note
    tax_scheme = etree.SubElement(tax_category, etree.QName(nsmap["cac"], "TaxScheme"))
    etree.SubElement(tax_scheme, etree.QName(nsmap["cbc"], "ID")).text = "VAT"

    # Add legal monetary total
    legal_monetary_total = etree.SubElement(root, etree.QName(nsmap["cac"], "LegalMonetaryTotal"))
    etree.SubElement(legal_monetary_total, etree.QName(nsmap["cbc"], "LineExtensionAmount"),
                     attrib={"currencyID": "EUR"}).text = f"{amount:.2f}"
    etree.SubElement(legal_monetary_total, etree.QName(nsmap["cbc"], "TaxExclusiveAmount"),
                     attrib={"currencyID": "EUR"}).text = f"{amount:.2f}"
    etree.SubElement(legal_monetary_total, etree.QName(nsmap["cbc"], "TaxInclusiveAmount"),
                     attrib={"currencyID": "EUR"}).text = f"{total_amount:.2f}"
    etree.SubElement(legal_monetary_total, etree.QName(nsmap["cbc"], "PayableAmount"),
                     attrib={"currencyID": "EUR"}).text = f"{total_amount:.2f}"

    # Add invoice line
    invoice_line = etree.SubElement(root, etree.QName(nsmap["cac"], "InvoiceLine"))
    etree.SubElement(invoice_line, etree.QName(nsmap["cbc"], "ID")).text = "1"
    etree.SubElement(invoice_line, etree.QName(nsmap["cbc"], "InvoicedQuantity"),
                     attrib={"unitCode": "C62"}).text = "1" if not is_cancellation else "-1"
    etree.SubElement(invoice_line, etree.QName(nsmap["cbc"], "LineExtensionAmount"),
                     attrib={"currencyID": "EUR"}).text = f"{amount:.2f}"
    item = etree.SubElement(invoice_line, etree.QName(nsmap["cac"], "Item"))
    etree.SubElement(item, etree.QName(nsmap["cbc"], "Description")).text = f"Etsy Bestellung #{order_info}"
    etree.SubElement(item, etree.QName(nsmap["cbc"], "Name")).text = "Bestellung"
    classified_tax_category = etree.SubElement(item, etree.QName(nsmap["cac"], "ClassifiedTaxCategory"))
    etree.SubElement(classified_tax_category, etree.QName(nsmap["cbc"], "ID")).text = vat_category
    etree.SubElement(classified_tax_category, etree.QName(nsmap["cbc"], "Percent")).text = f"{vat_rate * 100:.2f}"
    tax_scheme = etree.SubElement(classified_tax_category, etree.QName(nsmap["cac"], "TaxScheme"))
    etree.SubElement(tax_scheme, etree.QName(nsmap["cbc"], "ID")).text = "VAT"
    price = etree.SubElement(invoice_line, etree.QName(nsmap["cac"], "Price"))
    etree.SubElement(price, etree.QName(nsmap["cbc"], "PriceAmount"),
                     attrib={"currencyID": "EUR"}).text = "{:.2f}".format(abs(amount))

    # Serialize to XML
    xml_string = etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True).decode("utf-8")

    # Save the XRechnung XML
    invoice_filename = f"{invoice_number}.xml"
    invoice_filepath = os.path.join(invoice_folder, invoice_filename)
    with open(invoice_filepath, "w", encoding="utf-8") as xml_file:
        xml_file.write(xml_string)

    logging.info("Generated XRechnung: %s", invoice_filename)


def process_sale(row, rows, writer, orders_dict, country_codes):
    """Processes a sale row from the CSV."""
    try:
        logging.info("Processing sale: %s", row)
        date = datetime.strptime(row[0].strip('"'), "%B %d, %Y").date()

        if "for Order" in row[2]:
            order_info = row[2].split("#")[1].strip()
            buyer = orders_dict.get(order_info, {}).get("Full Name", "Etsy Refund")
            amount = float(row[7].replace('€', '').replace(',', '.').strip())
            if buyer == "Etsy Refund":
                logging.info("Full Cancelation Orders will not processed for %s", order_info)
                return

            tax_row = None
            for r in rows:
                if r[1] == "Tax" and r[3] == f"Order #{order_info}":
                    tax_row = r
                    break

            if tax_row:
                fees_taxes_value = float(tax_row[6].replace('-', '').replace('€', '').replace(',', '.'))
                amount -= fees_taxes_value
                calculation_details = f"({row[7].strip()} € - {fees_taxes_value:.2f} € (US-Sales Taxes paid by Etsy))"
            else:
                calculation_details = f"({row[7].strip()} €)"

            # Fetch address details from the orders dictionary
            address_details = orders_dict.get(order_info, {})
            address = (f"{address_details.get('Street 1', '')} {address_details.get('Street 2', '')}, "
                       f"{address_details.get('Ship City', '')}, {address_details.get('Ship State', '')} "
                       f"{address_details.get('Ship Zipcode', '')}, {address_details.get('Ship Country', '')}")
            calculation_details += f" | Address: {address}"
            calculation_details = calculation_details.replace(',', ';')

            # Generate Invoice Number
            invoice_number = generate_invoice_number(date)

            # Store invoice number to order number mapping
            invoice_order_mapping[order_info] = invoice_number
            logging.info("Invoice Number: %s, Order Number: %s added to mapping.", invoice_number, order_info)

            output_row = [
                date.strftime("%d.%m.%Y"),
                "Verkauf",
                buyer,
                f"Invoice {invoice_number} - Bestellung #{order_info} {calculation_details}",
                f"{amount:,.2f}".replace('.', ',')
            ]
            writer.writerow(output_row)
            logging.info("Wrote row to CSV: %s", output_row)

            # Generate XRechnung
            generate_xrechnung_lxml(invoice_number, order_info, amount, date, address_details, country_codes)

    except Exception as e:
        logging.error("Error processing sale row: %s. Error: %s", row, e)
        raise


def process_refund(row, rows, writer, orders_dict, country_codes):
    """Processes a refund row from the CSV."""
    try:
        logging.info("Processing refund: %s", row)
        date = datetime.strptime(row[0].strip('"'), "%B %d, %Y").date()
        order_info = row[2].split("#")[1].strip()
        address_details = orders_dict.get(order_info, {})

        buyer = orders_dict.get(order_info, {}).get("Full Name", "Etsy Refund")
        if buyer == "Etsy Refund":
            logging.info("Full Cancelation Orders will not processed for %s", order_info)
            return

        if row[6] == '--':
            if row[7] != '--':
                refund_amount = float(row[7].replace('€', '').replace(',', '.').strip())
            else:
                refund_amount = 0.0
        else:
            refund_amount = float(row[6].replace('€', '').replace(',', '.').strip())

        fee_credit_rows = []
        for r in rows:
            if r[1] == "Fee" and "Credit for" in r[2] and f"Order #{order_info}" in r[3]:
                fee_credit_rows.append(r)

        total_fee_credit = 0
        for fee_credit_row in fee_credit_rows:
            fee_credit_amount = float(fee_credit_row[7].replace('€', '').replace(',', '.').strip())
            total_fee_credit += fee_credit_amount

            if "Credit for processing fee" in fee_credit_row[2] or "Credit for transaction fee" in fee_credit_row[2]:
                refund_amount += fee_credit_amount
                logging.info("Adjusting refund amount by +%.2f EUR for fee credit: %s", fee_credit_amount,
                             fee_credit_row[2])
            else:
                logging.warning("Fee credit type not handled: %s", fee_credit_row[2])

        sale_row = None
        for r in rows:
            if r[1] == "Sale" and "for Order" in r[2] and order_info in r[2]:
                sale_row = r
                break

        tax_row = None
        for r in rows:
            if r[1] == "Tax" and r[3] == f"Order #{order_info}":
                tax_row = r
                break

        if sale_row:
            sale_amount = float(sale_row[7].replace('€', '').replace(',', '.').strip())
            if tax_row:
                sales_tax_amount = float(tax_row[6].replace('€', '').replace('-', '').strip())
            else:
                sales_tax_amount = 0.0

            amount = -(sale_amount - sales_tax_amount)
            logging.info("Setting refund amount to %.2f EUR (negating original sale amount minus sales tax)", amount)

        if sale_row:
            sale_amount_str = sale_row[7].strip()
        else:
            sale_amount_str = "N/A"

        # Extract original invoice number from sale row
        original_invoice_number = None
        original_invoice_number = invoice_order_mapping.get(order_info)
        logging.info("Extracted original invoice number: %s", original_invoice_number)

        if "Partial" in row[2]:
            refund_type = "Partial Refund"
            calculation_details = f"({sale_amount_str} € (Original Sale) - {row[7].strip()} € (Refund) + {total_fee_credit:.2f} € (Fee Credit))"
        else:
            refund_type = "Full Refund"
            calculation_details = f"({sale_amount_str} € (Original Sale) - {row[7].strip()} € (Refund) + {total_fee_credit:.2f} € (Fee Credit))"

        calculation_details += f" | Address: {address_details}"
        calculation_details = calculation_details.replace(',', ';')

        refund_amount = -abs(refund_amount)

        # Generate cancellation invoice number
        if original_invoice_number is None:
            cancellation_invoice_number = generate_invoice_number(date, is_cancellation=True)
        else:
            cancellation_invoice_number = original_invoice_number + "-STORNO"

        output_row = [
            date.strftime("%d.%m.%Y"),
            "Rückerstattung",
            buyer,
            f"Invoice {cancellation_invoice_number} - {refund_type} Bestellung #{order_info} {calculation_details}",
            f"{refund_amount:,.2f}".replace('.', ',')
        ]

        writer.writerow(output_row)
        logging.info("Wrote refund row to CSV: %s", output_row)

        # Generate XRechnung for cancellation invoice
        generate_xrechnung_lxml(cancellation_invoice_number, order_info, -refund_amount, date,
                                address_details, country_codes, is_cancellation=True,
                                original_invoice_number=original_invoice_number)
        logging.info("Generated XRechnung for cancellation invoice: %s", cancellation_invoice_number)

    except Exception as e:
        logging.error("Error processing refund row: %s. Error: %s", row, e)
        raise


def process_fee(row, data, current_month, writer, next_listing_fee_is_renew):
    """Processes a fee row from the CSV."""
    try:
        logging.info("Processing fee: %s", row)
        date = datetime.strptime(row[0].strip('"'), "%B %d, %Y").date()

        if "Etsy Ireland UC" not in data:
            data["Etsy Ireland UC"] = {}

        if current_month and current_month != date.month:
            write_summarized_data(data, datetime(date.year, date.month, 1) + pd.offsets.MonthEnd(0), writer)
            data.clear()
        current_month = date.month

        title = row[2]
        fees_taxes = row[6]
        credit = False
        if "Credit for" in title:
            title = title.split("Credit for ")[1].strip()
            logging.info("Processing Credit Fees")
            credit = True

        title = title.lower()
        if "listing fee" in title and next_listing_fee_is_renew:
            update_fees(data, "Etsy Ireland UC", "Renew Sold Fees", fees_taxes)
            #next_listing_fee_is_renew = False
        elif "listing fee" in title:
            update_fees(data, "Etsy Ireland UC", "Listing Fees (Listing, Renew Expired, Renew Sold)", fees_taxes)
        elif "transaction fee" in title:
            update_fees(data, "Etsy Ireland UC", "Transaction Fees", fees_taxes)
            #next_listing_fee_is_renew = False
        elif "processing fee" in title:
            update_fees(data, "Etsy Ireland UC", "Processing Fees", fees_taxes)
            #next_listing_fee_is_renew = True
        elif "etsy ads" in title:
            update_fees(data, "Etsy Ireland UC", "Etsy Ads Fees", fees_taxes)
        elif "fee for sale made through offsite ads" in title:
            update_fees(data, "Etsy Ireland UC", "Offsite Ads Fees", fees_taxes)
        else:
            logging.error(f"Not processing: %s", row)

        return data, current_month, next_listing_fee_is_renew
    except Exception as e:
        logging.error("Error processing fee row: %s. Error: %s", row, e)
        raise

def update_fees(data, recipient, fee_type, fees_taxes):
    logging.info(f"Updating fees for {recipient}, {fee_type}, {fees_taxes.replace('€','EUR ')}")
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
            if fee_type in ("Etsy Ads Fees", "Offsite Ads Fees"):
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

    logging.info(f"Input file: {input_file}")
    logging.info(f"Input file hash: {calculate_file_hash(input_file)}")

    # Load country codes at the beginning
    country_codes = load_country_codes()

    orders_dict = {}
    orders_dict = load_orders_file()

    data = {}
    current_month = None
    next_listing_fee_is_renew = False

    with open(input_file, 'r', encoding='utf-8-sig') as infile, \
            open('output-unsorted.csv', 'w', newline='', encoding='utf-8') as outfile_unsorted:
        reader = csv.reader(infile)
        writer_unsorted = csv.writer(outfile_unsorted, delimiter=',')
        writer_unsorted.writerow(['BUCHUNGSDATUM', 'ZUSATZINFO', 'AUFTRAGGEBER/EMPFÄNGER', 'VERWENDUNGSZWECK', 'BETRAG'])

        # Skip the header row
        next(reader, None)  # Read and discard the header

        # Sort rows by date, oldest first
        rows = sorted(list(reader), key=lambda row: datetime.strptime(row[0].strip('"'), "%B %d, %Y"))
        logging.info(f"Read and sorted {len(rows)} rows from input file {input_file}")

        for row in rows:
            input_type = row[1]
            if input_type == "Deposit":
                process_deposit(row, writer_unsorted)
            elif input_type == "Sale":
                process_sale(row, rows, writer_unsorted, orders_dict, country_codes)
            elif input_type == "Refund":
                process_refund(row, rows, writer_unsorted, orders_dict, country_codes)
            elif input_type in ("Fee", "Marketing"):
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

        for row in reader_unsorted:
            writer.writerow(row)

    logging.info(f"Conversion complete. Output saved to {output_file}")
    logging.info(f"Output file hash: {calculate_file_hash(output_file)}") # Moved outside the with block

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert Etsy CSV statement.')
    parser.add_argument('-infile', '--input_file', required=True, help='Path to the input CSV file')
    parser.add_argument('-outfile', '--output_file', required=True, help='Path to the output CSV file')
    args = parser.parse_args()

    convert_csv(args.input_file, args.output_file)
