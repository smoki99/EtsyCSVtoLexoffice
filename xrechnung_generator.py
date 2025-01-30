# xrechnung_generator.py
import os
from datetime import datetime
from decimal import Decimal
from lxml import etree
import pandas as pd
import csv
import math
from dotenv import load_dotenv

# Configuration for EU countries and VAT rates
EU_COUNTRIES = {
     "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus", "CZ": "Czech Republic",
     "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "ES": "Spain", "FI": "Finland", "FR": "France",
     "GR": "Greece", "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LT": "Lithuania",
     "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta", "NL": "Netherlands", "PL": "Poland",
     "PT": "Portugal", "RO": "Romania", "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia"
}

load_dotenv()

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

# Configuration for EU countries and VAT rates
EU_COUNTRIES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus", "CZ": "Czech Republic",
    "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "ES": "Spain", "FI": "Finland", "FR": "France",
    "GR": "Greece", "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LT": "Lithuania",
    "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta", "NL": "Netherlands", "PL": "Poland",
    "PT": "Portugal", "RO": "Romania", "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia"
}

def load_country_codes(csv_filepath="country_codes.csv"):
    """Loads country codes from a CSV file into a dictionary."""
    country_codes = {}
    try:
        with open(csv_filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                country_codes[row['country_name']] = row['alpha_2']
    except FileNotFoundError:
        print("Error: Country codes file not found at %s", csv_filepath)
        # Consider exiting the program or using default values
    return country_codes

# Load country codes at the beginning
country_codes = load_country_codes()

def get_country_code(country_name, country_codes):
    """Maps a country name to its ISO 3166-1 alpha-2 code."""
    return country_codes.get(country_name, "")  # Return empty string if not found


def generate_xrechnung_lxml(invoice_number, order_info, amount, date, buyer,
                            address_details, country_codes, is_cancellation=False,
                            original_invoice_number=None, output_dir="Rechnungen", reverse_charge=False, buyer_vat_id=""):
    """Generates an XRechnung XML file."""

    # Create Rechnungen folder if it doesn't exist
    invoice_folder = output_dir
    #print(output_dir)
    if not os.path.exists(invoice_folder):
        os.makedirs(invoice_folder)

    # Determine VAT rate and note based on country code from mapping
    country_code = get_country_code(address_details.get("Ship Country", ""), country_codes)
    if (reverse_charge == False):
        if country_code == "DE":
            vat_rate = Decimal("0.19")
            vat_category = "S"  # Standard rate
            vat_note = "Lieferung innerhalb Deutschlands mit deutscher Mehrwertsteuer."
        if country_code == "UK":
            vat_rate = Decimal("0.00")
            vat_category = "O"  # Marketplace Sale or below 135 GBP
            vat_note = "§ 3c UStG i.V.m. Section 14 VAT Act 1994 (VAT durch Marketplace abgeführt)"
        elif country_code in EU_COUNTRIES:
            vat_rate = Decimal("0.19")
            vat_category = "S"
            vat_note = "Lieferung gemäß § 3a UStG (Umsatz unter 10.000 € grenzüberschreitend)"
        else:
            vat_rate = Decimal("0.00")
            vat_category = "G"  # Export outside the EU
            vat_note = "Steuerfreie Ausfuhrlieferung nach § 4 Nr. 1a UStG."
    else:
        if country_code == "DE":  # In Deutschland gibt es normalerweise kein Reverse Charge!
            vat_rate = Decimal("0.19")
            vat_category = "S"  # Standard rate
            vat_note = "Lieferung innerhalb Deutschlands mit deutscher Mehrwertsteuer. Regelbesteuerung"
        elif country_code == "UK":
            vat_rate = Decimal("0.00")
            vat_category = "K"  # Reverse Charge für UK (Post-Brexit)
            vat_note = "§ 13b Abs. 2 UStG (Reverse Charge im Bestimmungsland)"
        elif country_code in EU_COUNTRIES:
            vat_rate = Decimal("0.00")
            vat_category = "K"  # Reverse Charge innerhalb der EU
            vat_note = "Reverse Charge - Steuerschuldnerschaft des Leistungsempfängers gemäß Art. 196 MwStSystRL i.V.m. §13b UStG"
        else:
            vat_rate = Decimal("0.00")
            vat_category = "Z"  # Export außerhalb der EU
            vat_note = "§ 13b Abs. 2 UStG (Reverse Charge im Bestimmungsland)"


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
    # WZ 47.71
    if (reverse_charge==False):
        etree.SubElement(root, etree.QName(nsmap["cbc"], "BuyerReference")).text = "WZ 47.71" 
        # WZ 47.71 ist der richtige Branchen-Code für den Einzelhandel mit Bekleidung, wenn du T-Shirts an Endkunden (B2C) verkaufst.
    else:
        etree.SubElement(root, etree.QName(nsmap["cbc"], "BuyerReference")).text = "WZ 47.10" 
        # WZ 74.10 – "Design von Mode"

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
    etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "StreetName")).text = address_details.get("Street 1", "")
    
    #street2 = address_details.get("Street 2")
    #if not (isinstance(street2, float) and math.isnan(street2)):
    #    etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "AdditionalStreetName")).text = street2
    etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "CityName")).text = address_details.get("Ship City", "")

    zipcode = address_details.get("Ship Zipcode")
    if not (isinstance(zipcode, float) and math.isnan(zipcode)):
        etree.SubElement(postal_address, etree.QName(nsmap["cbc"], "PostalZone")).text = address_details.get("Ship Zipcode", "")
    country = etree.SubElement(postal_address, etree.QName(nsmap["cac"], "Country"))
    etree.SubElement(country, etree.QName(nsmap["cbc"], "IdentificationCode")).text = get_country_code(
        address_details.get("Ship Country", ""), country_codes)

    # Add VAT ID Buyer if defined
    #if (buyer_vat_id!=""):
          #party_tax_scheme2 = etree.SubElement(postal_address, etree.QName(nsmap["cac"], "PartyTaxScheme"))
          #etree.SubElement(party_tax_scheme2, etree.QName(nsmap["cbc"], "CompanyID")).text = buyer_vat_id
          #etree.SubElement(party_tax_scheme2, etree.QName(nsmap["cbc"], "ID")).text = "VAT"
    # Add buyer tax scheme
    if (buyer_vat_id!=""):
        party_tax_scheme = etree.SubElement(party, etree.QName(nsmap["cac"], "PartyTaxScheme"))
        etree.SubElement(party_tax_scheme, etree.QName(nsmap["cbc"], "CompanyID")).text = buyer_vat_id
        tax_scheme = etree.SubElement(party_tax_scheme, etree.QName(nsmap["cac"], "TaxScheme"))
        etree.SubElement(tax_scheme, etree.QName(nsmap["cbc"], "ID")).text = "VAT"


    # Add buyer legal entity
    legal_entity = etree.SubElement(party, etree.QName(nsmap["cac"], "PartyLegalEntity"))
    etree.SubElement(legal_entity, etree.QName(nsmap["cbc"], "RegistrationName")).text = buyer

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
    if vat_rate == 0 and vat_category!="Z":
        etree.SubElement(tax_category, etree.QName(nsmap["cbc"], "TaxExemptionReason")).text = vat_note
    #else:
        #etree.SubElement(tax_category, etree.QName(nsmap["cbc"], "TaxTypeCode")).text = "VAT"
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
    etree.SubElement(item, etree.QName(nsmap["cbc"], "Description")).text = order_info
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

    return invoice_filename

    #logging.info("Generated XRechnung: %s", invoice_filename)
