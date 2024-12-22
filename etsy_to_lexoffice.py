import csv
from datetime import datetime
import pandas as pd
import logging
import hashlib
import argparse
import os
from dotenv import load_dotenv
from decimal import Decimal
from lxml import etree

# Load environment variables from .env file
load_dotenv()

# Configuration for EU countries and VAT rates
EU_COUNTRIES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus", "CZ": "Czech Republic",
    "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "ES": "Spain", "FI": "Finland", "FR": "France",
    "GR": "Greece", "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LT": "Lithuania",
    "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta", "NL": "Netherlands", "PL": "Poland",
    "PT": "Portugal", "RO": "Romania", "SE": "Sweden", "SI": "Sloven", "SK": "Slovakia"
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

# Global counter for invoice numbers
invoice_counter = 0

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
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)

    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

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

def load_orders_file(orders_file):
    """Load the orders CSV file and return a dictionary with Order ID as keys."""
    orders_dict = {}
    with open(orders_file, 'r', encoding='utf-8') as file:
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
    return orders_dict

# ISO 3166-1 alpha-2 country code mapping
COUNTRY_CODE_MAPPING = {
    "Afghanistan": "AF",
    "Albania": "AL",
    "Algeria": "DZ",
    "American Samoa": "AS",
    "Andorra": "AD",
    "Angola": "AO",
    "Anguilla": "AI",
    "Antarctica": "AQ",
    "Antigua and Barbuda": "AG",
    "Argentina": "AR",
    "Armenia": "AM",
    "Aruba": "AW",
    "Australia": "AU",
    "Austria": "AT",
    "Azerbaijan": "AZ",
    "Bahamas": "BS",
    "Bahrain": "BH",
    "Bangladesh": "BD",
    "Barbados": "BB",
    "Belarus": "BY",
    "Belgium": "BE",
    "Belize": "BZ",
    "Benin": "BJ",
    "Bermuda": "BM",
    "Bhutan": "BT",
    "Bolivia (Plurinational State of)": "BO",
    "Bonaire, Sint Eustatius and Saba": "BQ",
    "Bosnia and Herzegovina": "BA",
    "Botswana": "BW",
    "Bouvet Island": "BV",
    "Brazil": "BR",
    "British Indian Ocean Territory": "IO",
    "Brunei Darussalam": "BN",
    "Bulgaria": "BG",
    "Burkina Faso": "BF",
    "Burundi": "BI",
    "Cabo Verde": "CV",
    "Cambodia": "KH",
    "Cameroon": "CM",
    "Canada": "CA",
    "Cayman Islands": "KY",
    "Central African Republic": "CF",
    "Chad": "TD",
    "Chile": "CL",
    "China": "CN",
    "Christmas Island": "CX",
    "Cocos (Keeling) Islands": "CC",
    "Colombia": "CO",
    "Comoros": "KM",
    "Congo": "CG",
    "Congo, Democratic Republic of the": "CD",
    "Cook Islands": "CK",
    "Costa Rica": "CR",
    "Côte d'Ivoire": "CI",
    "Croatia": "HR",
    "Cuba": "CU",
    "Curaçao": "CW",
    "Cyprus": "CY",
    "Czechia": "CZ",
    "Denmark": "DK",
    "Djibouti": "DJ",
    "Dominica": "DM",
    "Dominican Republic": "DO",
    "Ecuador": "EC",
    "Egypt": "EG",
    "El Salvador": "SV",
    "Equatorial Guinea": "GQ",
    "Eritrea": "ER",
    "Estonia": "EE",
    "Eswatini": "SZ",
    "Ethiopia": "ET",
    "Falkland Islands (Malvinas)": "FK",
    "Faroe Islands": "FO",
    "Fiji": "FJ",
    "Finland": "FI",
    "France": "FR",
    "French Guiana": "GF",
    "French Polynesia": "PF",
    "French Southern Territories": "TF",
    "Gabon": "GA",
    "Gambia": "GM",
    "Georgia": "GE",
    "Germany": "DE",
    "Ghana": "GH",
    "Gibraltar": "GI",
    "Greece": "GR",
    "Greenland": "GL",
    "Grenada": "GD",
    "Guadeloupe": "GP",
    "Guam": "GU",
    "Guatemala": "GT",
    "Guernsey": "GG",
    "Guinea": "GN",
    "Guinea-Bissau": "GW",
    "Guyana": "GY",
    "Haiti": "HT",
    "Heard Island and McDonald Islands": "HM",
    "Holy See": "VA",
    "Honduras": "HN",
    "Hong Kong": "HK",
    "Hungary": "HU",
    "Iceland": "IS",
    "India": "IN",
    "Indonesia": "ID",
    "Iran (Islamic Republic of)": "IR",
    "Iraq": "IQ",
    "Ireland": "IE",
    "Isle of Man": "IM",
    "Israel": "IL",
    "Italy": "IT",
    "Jamaica": "JM",
    "Japan": "JP",
    "Jersey": "JE",
    "Jordan": "JO",
    "Kazakhstan": "KZ",
    "Kenya": "KE",
    "Kiribati": "KI",
    "Korea (Democratic People's Republic of)": "KP",
    "Korea, Republic of": "KR",
    "Kuwait": "KW",
    "Kyrgyzstan": "KG",
    "Lao People's Democratic Republic": "LA",
    "Latvia": "LV",
    "Lebanon": "LB",
    "Lesotho": "LS",
    "Liberia": "LR",
    "Libya": "LY",
    "Liechtenstein": "LI",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Macao": "MO",
    "Madagascar": "MG",
    "Malawi": "MW",
    "Malaysia": "MY",
    "Maldives": "MV",
    "Mali": "ML",
    "Malta": "MT",
    "Marshall Islands": "MH",
    "Martinique": "MQ",
    "Mauritania": "MR",
    "Mauritius": "MU",
    "Mayotte": "YT",
    "Mexico": "MX",
    "Micronesia (Federated States of)": "FM",
    "Moldova, Republic of": "MD",
    "Monaco": "MC",
    "Mongolia": "MN",
    "Montenegro": "ME",
    "Montserrat": "MS",
    "Morocco": "MA",
    "Mozambique": "MZ",
    "Myanmar": "MM",
    "Namibia": "NA",
    "Nauru": "NR",
    "Nepal": "NP",
    "Netherlands": "NL",
    "New Caledonia": "NC",
    "New Zealand": "NZ",
    "Nicaragua": "NI",
    "Niger": "NE",
    "Nigeria": "NG",
    "Niue": "NU",
    "Norfolk Island": "NF",
    "Northern Mariana Islands": "MP",
    "Norway": "NO",
    "Oman": "OM",
    "Pakistan": "PK",
    "Palau": "PW",
    "Palestine, State of": "PS",
    "Panama": "PA",
    "Papua New Guinea": "PG",
    "Paraguay": "PY",
    "Peru": "PE",
    "Philippines": "PH",
    "Pitcairn": "PN",
    "Poland": "PL",
    "Portugal": "PT",
    "Puerto Rico": "PR",
    "Qatar": "QA",
    "Réunion": "RE",
    "Romania": "RO",
    "Russian Federation": "RU",
    "Rwanda": "RW",
    "Saint Barthélemy": "BL",
    "Saint Helena, Ascension and Tristan da Cunha": "SH",
    "Saint Kitts and Nevis": "KN",
    "Saint Lucia": "LC",
    "Saint Martin (French part)": "MF",
    "Saint Pierre and Miquelon": "PM",
    "Saint Vincent and the Grenadines": "VC",
    "Samoa": "WS",
    "San Marino": "SM",
    "Sao Tome and Principe": "ST",
    "Saudi Arabia": "SA",
    "Senegal": "SN",
    "Serbia": "RS",
    "Seychelles": "SC",
    "Sierra Leone": "SL",
    "Singapore": "SG",
    "Sint Maarten (Dutch part)": "SX",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Solomon Islands": "SB",
    "Somalia": "SO",
    "South Africa": "ZA",
    "South Georgia and the South Sandwich Islands": "GS",
    "South Sudan": "SS",
    "Spain": "ES",
    "Sri Lanka": "LK",
    "Sudan": "SD",
    "Suriname": "SR",
    "Svalbard and Jan Mayen": "SJ",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Syrian Arab Republic": "SY",
    "Taiwan, Province of China": "TW",
    "Tajikistan": "TJ",
    "Tanzania, United Republic of": "TZ",
    "Thailand": "TH",
    "Timor-Leste": "TL",
    "Togo": "TG",
    "Tokelau": "TK",
    "Tonga": "TO",
    "Trinidad and Tobago": "TT",
    "Tunisia": "TN",
    "Turkey": "TR",
    "Turkmenistan": "TM",
    "Turks and Caicos Islands": "TC",
    "Tuvalu": "TV",
    "Uganda": "UG",
    "Ukraine": "UA",
    "United Arab Emirates": "AE",
    "United Kingdom": "GB",
    "United States": "US",
    "United States Minor Outlying Islands": "UM",
    "Uruguay": "UY",
    "Uzbekistan": "UZ",
    "Vanuatu": "VU",
    "Venezuela (Bolivarian Republic of)": "VE",
    "Viet Nam": "VN",
    "Virgin Islands (British)": "VG",
    "Virgin Islands (U.S.)": "VI",
    "Wallis and Futuna": "WF",
    "Western Sahara": "EH",
    "Yemen": "YE",
    "Zambia": "ZM",
    "Zimbabwe": "ZW",
    "Åland Islands": "AX"
}

# Function to map country name to ISO 3166-1 alpha-2 code
def get_country_code(country_name):
    return COUNTRY_CODE_MAPPING.get(country_name, "")  # Return empty string if not found

def generate_xrechnung_lxml(order_info, buyer, amount, date, address_details):
    global invoice_counter
    invoice_counter += 1
    year = str(date.year)[-2:]
    month = str(date.month).zfill(2)
    invoice_number = f"ETSY-{year}{month}-{invoice_counter:04}"

    # Create Rechnungen folder if it doesn't exist
    invoice_folder = "Rechnungen"
    if not os.path.exists(invoice_folder):
        os.makedirs(invoice_folder)

    # Determine VAT rate and note
    country_code = address_details.get("Ship Country", "")
    if country_code not in EU_COUNTRIES:
        vat_rate = Decimal("0.00")
        vat_category = "G" # Export outside the EU
        vat_note = "Steuerfreie Ausfuhrlieferung"
    else:
        vat_rate = Decimal("0.19")
        vat_category = "S" # Standard rate
        vat_note = "Innergemeinschaftliche Lieferung, Rechnungsstellung mit deutscher Umsatzsteuer aufgrund Kleinunternehmerregelung bis 10.000€ Umsatz."

    # Calculate VAT amount and total amount
    vat_amount = (Decimal(str(amount)) * vat_rate).quantize(Decimal("0.01"))
    total_amount = Decimal(str(amount)) + vat_amount

    # Define namespaces
    NSMAP = {
        None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",  # Default namespace
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }

    # Create root element using QName and nsmap
    root = etree.Element(etree.QName(NSMAP[None], "Invoice"), nsmap=NSMAP)

    # Add schema location information to the root element
    root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = \
        "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2 http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-Invoice-2.1.xsd"
    
    # Add CustomizationID
    CustomizationID = etree.SubElement(root, etree.QName(NSMAP["cbc"], "CustomizationID"))
    CustomizationID.text = "urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_3.0"
    
    # Add ProfileID
    ProfileID = etree.SubElement(root, etree.QName(NSMAP["cbc"], "ProfileID"))
    ProfileID.text = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

    # Add invoice number
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "ID")).text = invoice_number

    # Add issue date
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "IssueDate")).text = date.strftime("%Y-%m-%d")

    # Add due date
    due_date = date + pd.DateOffset(days=14)
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "DueDate")).text = due_date.strftime("%Y-%m-%d")

    # Add invoice type code (380 = commercial invoice)
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "InvoiceTypeCode")).text = "380"

    # Add document currency code
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "DocumentCurrencyCode")).text = "EUR"

    # Add buyer reference
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "BuyerReference")).text = buyer

    # Add AccountingSupplierParty
    supplier_party = etree.SubElement(root, etree.QName(NSMAP["cac"], "AccountingSupplierParty"))
    party = etree.SubElement(supplier_party, etree.QName(NSMAP["cac"], "Party"))

    # Add seller name
    party_name = etree.SubElement(party, etree.QName(NSMAP["cac"], "PartyName"))
    etree.SubElement(party_name, etree.QName(NSMAP["cbc"], "Name")).text = SENDER_NAME

    # Add seller postal address
    postal_address = etree.SubElement(party, etree.QName(NSMAP["cac"], "PostalAddress"))
    etree.SubElement(postal_address, etree.QName(NSMAP["cbc"], "StreetName")).text = SENDER_STREET
    etree.SubElement(postal_address, etree.QName(NSMAP["cbc"], "AdditionalStreetName")).text = ""
    etree.SubElement(postal_address, etree.QName(NSMAP["cbc"], "CityName")).text = SENDER_CITY
    etree.SubElement(postal_address, etree.QName(NSMAP["cbc"], "PostalZone")).text = SENDER_POSTALCODE
    country = etree.SubElement(postal_address, etree.QName(NSMAP["cac"], "Country"))
    etree.SubElement(country, etree.QName(NSMAP["cbc"], "IdentificationCode")).text = SENDER_COUNTRY

    # Add seller tax scheme
    party_tax_scheme = etree.SubElement(party, etree.QName(NSMAP["cac"], "PartyTaxScheme"))
    etree.SubElement(party_tax_scheme, etree.QName(NSMAP["cbc"], "CompanyID")).text = SENDER_VAT_ID
    tax_scheme = etree.SubElement(party_tax_scheme, etree.QName(NSMAP["cac"], "TaxScheme"))
    etree.SubElement(tax_scheme, etree.QName(NSMAP["cbc"], "ID")).text = "VAT"

    # Add seller legal entity
    legal_entity = etree.SubElement(party, etree.QName(NSMAP["cac"], "PartyLegalEntity"))
    etree.SubElement(legal_entity, etree.QName(NSMAP["cbc"], "RegistrationName")).text = SENDER_COMPANY_NAME
    etree.SubElement(legal_entity, etree.QName(NSMAP["cbc"], "CompanyID"), attrib={"schemeID": "0198"}).text = SENDER_VAT_ID

    # Add seller contact
    contact = etree.SubElement(party, etree.QName(NSMAP["cac"], "Contact"))
    etree.SubElement(contact, etree.QName(NSMAP["cbc"], "Name")).text = SENDER_NAME
    etree.SubElement(contact, etree.QName(NSMAP["cbc"], "Telephone")).text = SENDER_PHONE_NUMBER
    etree.SubElement(contact, etree.QName(NSMAP["cbc"], "ElectronicMail")).text = SENDER_MAIL

    # Add AccountingCustomerParty
    customer_party = etree.SubElement(root, etree.QName(NSMAP["cac"], "AccountingCustomerParty"))
    party = etree.SubElement(customer_party, etree.QName(NSMAP["cac"], "Party"))
    
    # Add buyer postal address
    postal_address = etree.SubElement(party, etree.QName(NSMAP["cac"], "PostalAddress"))
    etree.SubElement(postal_address, etree.QName(NSMAP["cbc"], "StreetName")).text = address_details.get("Street 1", "")
    etree.SubElement(postal_address, etree.QName(NSMAP["cbc"], "AdditionalStreetName")).text = address_details.get("Street 2", "")
    etree.SubElement(postal_address, etree.QName(NSMAP["cbc"], "CityName")).text = address_details.get("Ship City", "")
    etree.SubElement(postal_address, etree.QName(NSMAP["cbc"], "PostalZone")).text = address_details.get("Ship Zipcode", "")
    country = etree.SubElement(postal_address, etree.QName(NSMAP["cac"], "Country"))

    etree.SubElement(country, etree.QName(NSMAP["cbc"], "IdentificationCode")).text = get_country_code(address_details.get("Ship Country", ""))
    
    # Add buyer legal entity
    legal_entity = etree.SubElement(party, etree.QName(NSMAP["cac"], "PartyLegalEntity"))
    etree.SubElement(legal_entity, etree.QName(NSMAP["cbc"], "RegistrationName")).text = buyer
    
    # No Buyer TAX ID Needed since B2C
    #etree.SubElement(legal_entity, etree.QName(NSMAP["cbc"], "CompanyID"), attrib={"schemeID": #"0198"}).text = "DE123456789"

    # Add payment means (58 = SEPA credit transfer)
    payment_means = etree.SubElement(root, etree.QName(NSMAP["cac"], "PaymentMeans"))
    etree.SubElement(payment_means, etree.QName(NSMAP["cbc"], "PaymentMeansCode"), attrib={"name": "SEPA credit transfer"}).text = "58"
    # Add PayeeFinancialAccount with IBAN
    payee_financial_account = etree.SubElement(payment_means, etree.QName(NSMAP["cac"], "PayeeFinancialAccount"))
    etree.SubElement(payee_financial_account, etree.QName(NSMAP["cbc"], "ID")).text = "DE12345678901234567890" # Replace with IBAN

    # Add tax total
    tax_total = etree.SubElement(root, etree.QName(NSMAP["cac"], "TaxTotal"))
    etree.SubElement(tax_total, etree.QName(NSMAP["cbc"], "TaxAmount"), attrib={"currencyID": "EUR"}).text = str(vat_amount)

    tax_subtotal = etree.SubElement(tax_total, etree.QName(NSMAP["cac"], "TaxSubtotal"))
    etree.SubElement(tax_subtotal, etree.QName(NSMAP["cbc"], "TaxableAmount"), attrib={"currencyID": "EUR"}).text = str(amount)
    etree.SubElement(tax_subtotal, etree.QName(NSMAP["cbc"], "TaxAmount"), attrib={"currencyID": "EUR"}).text = str(vat_amount)
    tax_category = etree.SubElement(tax_subtotal, etree.QName(NSMAP["cac"], "TaxCategory"))
    etree.SubElement(tax_category, etree.QName(NSMAP["cbc"], "ID")).text = vat_category
    etree.SubElement(tax_category, etree.QName(NSMAP["cbc"], "Percent")).text = str(vat_rate * 100)
    # Add exemption reason if the rate is 0
    if vat_rate == 0:
      etree.SubElement(tax_category, etree.QName(NSMAP["cbc"], "TaxExemptionReason")).text = vat_note
    tax_scheme = etree.SubElement(tax_category, etree.QName(NSMAP["cac"], "TaxScheme"))
    etree.SubElement(tax_scheme, etree.QName(NSMAP["cbc"], "ID")).text = "VAT"

    # Add legal monetary total
    legal_monetary_total = etree.SubElement(root, etree.QName(NSMAP["cac"], "LegalMonetaryTotal"))
    etree.SubElement(legal_monetary_total, etree.QName(NSMAP["cbc"], "LineExtensionAmount"), attrib={"currencyID": "EUR"}).text = str(amount)
    etree.SubElement(legal_monetary_total, etree.QName(NSMAP["cbc"], "TaxExclusiveAmount"), attrib={"currencyID": "EUR"}).text = str(amount)
    etree.SubElement(legal_monetary_total, etree.QName(NSMAP["cbc"], "TaxInclusiveAmount"), attrib={"currencyID": "EUR"}).text = str(total_amount)
    etree.SubElement(legal_monetary_total, etree.QName(NSMAP["cbc"], "PayableAmount"), attrib={"currencyID": "EUR"}).text = str(total_amount)

    # Add invoice line
    invoice_line = etree.SubElement(root, etree.QName(NSMAP["cac"], "InvoiceLine"))
    etree.SubElement(invoice_line, etree.QName(NSMAP["cbc"], "ID")).text = "1"
    etree.SubElement(invoice_line, etree.QName(NSMAP["cbc"], "InvoicedQuantity"), attrib={"unitCode": "C62"}).text = "1"
    etree.SubElement(invoice_line, etree.QName(NSMAP["cbc"], "LineExtensionAmount"), attrib={"currencyID": "EUR"}).text = str(amount)
    item = etree.SubElement(invoice_line, etree.QName(NSMAP["cac"], "Item"))
    etree.SubElement(item, etree.QName(NSMAP["cbc"], "Description")).text = f"Etsy Order {order_info}"
    etree.SubElement(item, etree.QName(NSMAP["cbc"], "Name")).text = "Order"
    classified_tax_category = etree.SubElement(item, etree.QName(NSMAP["cac"], "ClassifiedTaxCategory"))
    etree.SubElement(classified_tax_category, etree.QName(NSMAP["cbc"], "ID")).text = vat_category
    etree.SubElement(classified_tax_category, etree.QName(NSMAP["cbc"], "Percent")).text = str(vat_rate * 100)
    tax_scheme = etree.SubElement(classified_tax_category, etree.QName(NSMAP["cac"], "TaxScheme"))
    etree.SubElement(tax_scheme, etree.QName(NSMAP["cbc"], "ID")).text = "VAT"
    price = etree.SubElement(invoice_line, etree.QName(NSMAP["cac"], "Price"))
    etree.SubElement(price, etree.QName(NSMAP["cbc"], "PriceAmount"), attrib={"currencyID": "EUR"}).text = str(amount)

    # Serialize to XML
    xml_string = etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True).decode("utf-8")

    # Save the XRechnung XML
    invoice_filename = f"{invoice_number}.xml"
    invoice_filepath = os.path.join(invoice_folder, invoice_filename)
    with open(invoice_filepath, "w", encoding="utf-8") as xml_file:
        xml_file.write(xml_string)

    logging.info(f"Generated XRechnung: {invoice_filename}")

def process_sale(row, rows, writer, orders_dict):
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
                calculation_details = f"({row[7].strip()} € - {fees_taxes_value:.2f} € (US-Sales Taxes paid by Etsy))"
            else:
                calculation_details = f"({row[7].strip()} €)"

            # Fetch address details from the orders dictionary
            address_details = orders_dict.get(order_info, {})
            address = f"{address_details.get('Street 1', '')} {address_details.get('Street 2', '')}, {address_details.get('Ship City', '')}, {address_details.get('Ship State', '')} {address_details.get('Ship Zipcode', '')}, {address_details.get('Ship Country', '')}"
            calculation_details += f" | Address: {address}"
            calculation_details = calculation_details.replace(',',';')

            output_row = [
                date.strftime("%d.%m.%Y"),
                "Verkauf",
                buyer,
                f"Bestellung #{order_info} {calculation_details}",
                f"{amount:,.2f}".replace('.', ',')
            ]
            writer.writerow(output_row)
            logging.info(f"Wrote row to CSV: {output_row}")

            # Generate XRechnung
            generate_xrechnung_lxml(order_info, buyer, amount, date, address_details)
        
    except Exception as e:
        logging.error(f"Error processing sale row: {row}. Error: {e}")
        raise

def process_refund(row, rows, writer, orders_dict):
    try:
        logging.info(f"Processing refund: {row}")
        date = datetime.strptime(row[0].strip('"'), "%B %d, %Y").date()
        order_info = row[2].split("#")[1].strip()

        buyer = orders_dict.get(order_info, {}).get("Full Name", "Etsy Refund")

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
                logging.info(f"Adjusting refund amount by +{fee_credit_amount:.2f} EUR for fee credit: {fee_credit_row[2]}")
            else:
                logging.warning(f"Fee credit type not handled: {fee_credit_row[2]}")

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
            logging.info(f"Setting refund amount to {amount:.2f} EUR (negating original sale amount minus sales tax)")

        address = orders_dict.get(order_info, {}).get("Address", "Address not found")

        if sale_row:
            sale_amount_str = sale_row[7].strip()
        else:
            sale_amount_str = "N/A"

        if "Partial" in row[2]:
            refund_type = "Partial Refund"
            calculation_details = f"({sale_amount_str} € (Original Sale) - {row[7].strip()} € (Refund) + {total_fee_credit:.2f} € (Fee Credit))"
        else:
            refund_type = "Full Refund"
            calculation_details = f"({sale_amount_str} € (Original Sale) - {row[7].strip()} € (Refund) + {total_fee_credit:.2f} € (Fee Credit))"

        calculation_details += f" | Address: {address}"
        calculation_details = calculation_details.replace(',', ';')

        refund_amount = - abs(refund_amount)

        output_row = [
            date.strftime("%d.%m.%Y"),
            "Rückerstattung",
            buyer,
            f"{refund_type} Bestellung #{order_info} {calculation_details}",
            f"{refund_amount:,.2f}".replace('.', ',')
        ]

        writer.writerow(output_row)
        logging.info(f"Wrote refund row to CSV: {output_row}")
    except Exception as e:
        logging.error(f"Error processing refund row: {row}. Error: {e}")
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
        if "Credit for" in title:
            title = title.split("Credit for ")[1].strip()

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
        elif "Fee for sale made through Offsite Ads" in title:
            update_fees(data, "Etsy Ireland UC", "Offsite Ads Fees", fees_taxes)

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

def convert_csv(input_file, output_file, orders_file=None):
    """Converts the input CSV to the output CSV with the specified transformations."""
    filename_prefix = "convert_csv"
    datetime_part = get_datetime_filename()
    log_filename = f"{filename_prefix}_{datetime_part}.log"

    configure_logging(log_filename)

    logging.info(f"Input file: {input_file}")
    logging.info(f"Input file hash: {calculate_file_hash(input_file)}")

    orders_dict = {}
    if orders_file:
        logging.info(f"Loading orders file: {orders_file}")
        orders_dict = load_orders_file(orders_file)

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
                process_sale(row, rows, writer_unsorted, orders_dict)
            elif type == "Refund":
                process_refund(row, rows, writer_unsorted, orders_dict)
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

    logging.info(f"Conversion complete. Output saved to {output_file}")
    logging.info(f"Output file hash: {calculate_file_hash(output_file)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert Etsy CSV statement.')
    parser.add_argument('-infile', '--input_file', required=True, help='Path to the input CSV file')
    parser.add_argument('-outfile', '--output_file', required=True, help='Path to the output CSV file')
    parser.add_argument('-ordersfile', '--orders_file', help='Path to the Etsy orders CSV file for address details')
    args = parser.parse_args()

    convert_csv(args.input_file, args.output_file, args.orders_file)