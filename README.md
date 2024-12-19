Okay, I've updated the documentation to include detailed information about refunds, refund fees, and partial refunds. Here's the revised documentation:

# EtsyCSVtoLexoffice: Etsy-CSV für Lexoffice konvertieren

Dieses Python-Programm konvertiert eine CSV-Datei von Etsy in ein Format, das für den Import in Lexoffice geeignet ist. Es liest die Datei `input.csv` ein, verarbeitet die Daten und schreibt sie in die Datei `output.csv`. Zusätzlich wird eine Log-Datei erstellt, die den Konvertierungsprozess dokumentiert.

**Wichtiger Hinweis:** Dieses Programm dient nur zu Demonstrationszwecken. Der Autor übernimmt keine Garantie für die steuerliche Richtigkeit der Konvertierung. Es liegt in Ihrer Verantwortung, die konvertierten Daten vor dem Import in Lexoffice zu überprüfen und sicherzustellen, dass sie den aktuellen steuerlichen Vorschriften entsprechen.

## Voraussetzungen

*   **Python 3:** Stellen Sie sicher, dass Python 3 auf Ihrem System installiert ist. Sie können Python von [https://python.org](https://python.org) herunterladen.
*   **Installierte Pakete:** Sie müssen die Pakete `pandas` und `hashlib` installieren. Führen Sie dazu folgenden Befehl in Ihrer Konsole aus:
    ```bash
    pip install pandas hashlib
    ```

## Anleitung

1. **CSV-Datei Monthly Payments von Etsy herunterladen:** Laden Sie die gewünschte CSV-Datei aus Ihrem Etsy-Shop herunter, diese können Sie in `input.csv` umbenennen.
2. **CSV-Datei Orders von Etsy herunterladen:** Laden Sie aus Shop Manager > Einstellungen > Optionen die Orders für den Monat herunter und ändern Sie den Namen der CSV-Datei in `orders.csv` um.
3. **Skript herunterladen:** Laden Sie die Datei `etsy_to_lexoffice.py` herunter und speichern Sie sie im gleichen Verzeichnis wie die `input.csv` und `orders.csv`
4. **Skript ausführen:** Öffnen Sie Ihre Konsole, navigieren Sie zum Verzeichnis der Dateien und führen Sie das Python-Skript aus.
    ```bash
    python etsy_to_lexoffice.py -infile ./input.csv -outfile ./output.csv --ordersfile ./orders.csv
    ```
    Das Skript erstellt eine neue CSV-Datei namens `output.csv`, die für den Import in Lexoffice bereit ist. Außerdem wird eine Log-Datei erstellt, die detaillierte Informationen über den Konvertierungsprozess enthält.
5. **CSV-Datei in Lexoffice importieren:** Importieren Sie die Datei `output.csv` in Lexoffice.

## Funktionsweise im Detail

Das Programm arbeitet in drei Schritten:

### 1. Einlesen und Vorbereiten der Daten

*   **Einlesen der Etsy-CSV:** Das Programm liest die Datei `input.csv` ein. Diese Datei sollte die von Etsy heruntergeladene CSV-Datei sein, die in Schritt 2 umbenannt wurde.
*   **Initialisierung:** Es werden Variablen initialisiert, um den aktuellen Monat, die aufgelaufenen Gebühren und andere relevante Daten zu speichern.

### 2. Verarbeitung der Daten

Das Programm iteriert über jede Zeile der `input.csv` und führt je nach Typ der Zeile unterschiedliche Aktionen aus:

*   **Auszahlungen (Deposits):** Auszahlungen von Etsy werden erkannt und die relevanten Daten (Datum, Betrag) extrahiert. Das Datum wird von dem Format "Monat Tag, Jahr" in "Tag.Monat.Jahr" umgewandelt. Der Betrag wird als positiver Wert gespeichert, da es sich um eine Ausgabe handelt, die den Etsy-Verkaufserlös reduziert.
*   **Verkäufe (Sales):** Verkäufe werden erkannt und die Daten (Datum, Käufer, Bestellnummer, Betrag) extrahiert. Das Datum wird wie bei den Auszahlungen umgewandelt. Der Betrag wird um eventuelle Steuern (State-Tax) bereinigt, die Etsy direkt einbehalten hat.
*   **Rückerstattungen (Refunds):**
    *   **Vollständige Rückerstattungen:** Bei einer vollständigen Rückerstattung wird der ursprüngliche Verkaufsbetrag (vor Abzug der Steuern) negiert, um den Verkauf effektiv rückgängig zu machen.
    *   **Teilrückerstattungen:** Bei Teilrückerstattungen wird der in der Rückerstattungszeile angegebene Betrag verwendet und um etwaige Gutschriften für Transaktionsgebühren und Bearbeitungsgebühren ("Credit for transaction fee", "Credit for processing fee") bereinigt.
    *   **Berechnungsdetails:** Die "Rückerstattung"-Zeile in der `output.csv` enthält detaillierte Informationen zur Berechnung, einschließlich des ursprünglichen Verkaufsbetrags, des Rückerstattungsbetrags und etwaiger Gebührengutschriften.
*   **Gebühren (Fees) und Marketing:** Gebühren und Marketingausgaben werden erkannt und die Daten (Datum, Art der Gebühr, Betrag) extrahiert. Das Datum wird in das gewünschte Format umgewandelt. Der Betrag wird aufsummiert und nach Art der Gebühr gruppiert.
*   **Monatliche Zusammenfassung:** Am Ende jedes Monats werden die aufgelaufenen Gebühren und Marketingausgaben in die `output.csv` geschrieben.

### 3. Schreiben der Daten

*   **Erstellen der `output.csv`:** Das Programm erstellt die Datei `output.csv` und schreibt die konvertierten Daten in der richtigen Reihenfolge und im richtigen Format hinein.
*   **Log-Datei:** Parallel zum Konvertierungsprozess wird eine Log-Datei erstellt. Diese Datei enthält detaillierte Informationen über jede verarbeitete Zeile, z.B. den Typ der Zeile, die extrahierten Daten und eventuelle Fehlermeldungen. Die Log-Datei ist hilfreich, um Fehler zu finden und den Konvertierungsprozess nachzuvollziehen.

##  Speichern der Dateien

Nach der Ausführung des Programms finden Sie die folgenden Dateien in dem Verzeichnis, in dem Sie das Skript ausgeführt haben:

*   **`input.csv`:** Die von Ihnen bereitgestellte Etsy-CSV-Datei.
*   **`output.csv`:** Die für den Import in Lexoffice konvertierte CSV-Datei.
*   **`orders.csv`:** Die CSV-Datei mit den Bestelldaten, die für die Adressinformationen verwendet wird.
*   **`etsy_to_lexoffice.py`:** Das Python-Skript.
*   **`convert_csv_[Datum]_[Zeit].log`:** Die Log-Datei mit detaillierten Informationen zum Konvertierungsprozess.

Bewahren Sie diese Dateien an einem sicheren Ort auf, um Ihre Buchhaltungsunterlagen zu vervollständigen und bei Bedarf darauf zugreifen zu können.

## Anpassung

Das Skript kann an Ihre individuellen Bedürfnisse angepasst werden. Sie können z. B. die Art und Weise ändern, wie bestimmte Daten extrahiert oder formatiert werden. Beachten Sie jedoch, dass Änderungen am Code zu unerwünschten Ergebnissen führen können.

## Haftungsausschluss

Dieses Programm wird ohne jegliche Gewährleistung bereitgestellt. Der Autor haftet nicht für Schäden, die durch die Verwendung dieses Programms entstehen.

## Etsy CSV Converter: Detailed Documentation

This document provides a detailed explanation of the Python script designed to convert an Etsy transaction CSV into a structured format suitable for accounting or analysis, specifically for Lexoffice import.

### 1. Overview

The script takes an input CSV file containing Etsy transaction data (sales, deposits, fees, refunds) and transforms it into a more organized CSV output file. The output file presents the data in a chronologically sorted manner, summarizes fees by month and category, uses a consistent format for dates and amounts, and handles refunds (both full and partial) accurately.

### 2. Code Structure and Flow

The script is structured into several functions to improve readability, maintainability, and testability. Here's a breakdown of the main components:

**2.1. Main Function: `convert_csv(input_file, output_file, orders_file=None)`**

This function acts as the primary driver of the conversion process.

```mermaid
graph TD
    A[Start] --> B{Configure Logging}
    B --> C{Calculate Input File Hash}
    C --> D{Open Input & Unsorted Output Files}
    D --> E{Read all rows from CSV}
    E --> F{Iterate through each row}
    F --> G{Check row type}
    G -- "Deposit" --> H[Process Deposit]
    G -- "Sale" --> I[Process Sale]
    G -- "Refund" --> S[Process Refund]
    G -- "Fee/Marketing" --> J[Process Fee]
    H --> K[Write to Unsorted Output]
    I --> K
    J --> K
    S --> K
    F --> L{End of Row Iteration}
    K --> L
    L --> M{Write Summarized Data}
    M --> N{Open Unsorted and Sorted Output Files}
    N --> O{Sort Rows by Date}
    O --> P{Write Sorted Data}
    P --> Q{Calculate Output File Hash}
    Q --> R[End]
```

**2.2. Processing Functions:**

*   **`process_deposit(row, writer)`:** Extracts relevant information (date, amount) from a "Deposit" row and writes it to the output CSV in the desired format.

```mermaid
graph LR
    A[Deposit Row] --> B{Extract Date}
    B --> C{Extract Amount}
    C --> D{Format Output Row}
    D --> E{Write Row to CSV}
```

*   **`process_sale(row, rows, writer, orders_dict)`:** Processes "Sale" entries, considering associated taxes and fees to calculate the net sale amount. It searches for corresponding "Tax" rows to accurately adjust the sale value.

```mermaid
graph LR
    A[Sale Row] --> B{Extract Order Info, Buyer, Amount}
    B --> C{Find Matching Tax Row}
    C -- Found --> D{Calculate Net Sale Amount}
    C -- Not Found --> E{Use Original Sale Amount}
    D --> F{Format Output Row}
    E --> F
    F --> G{Write Row to CSV}
```

*   **`process_refund(row, rows, writer, orders_dict)`:** Handles "Refund" entries, including both full and partial refunds.
    *   **Full Refunds:** For full refunds, it negates the original sale amount (before tax deduction) to effectively reverse the sale.
    *   **Partial Refunds:** For partial refunds, it uses the amount specified in the refund row and adjusts it for any corresponding "Credit for transaction fee" and "Credit for processing fee" entries.
    *   **Calculation Details:** The refund row in the output CSV includes detailed calculation information, including the original sale amount, refund amount, and any applicable fee credits.

```mermaid
graph LR
graph LR
    A[Refund Row] --> B{Extract Date, Order Info, Buyer}
    B --> C{Initialize Refund Amount from Row}
    C --> D{Find Corresponding Fee Credit Rows}
    D --> E{Loop through Fee Credit Rows}
    E --> F{Check if Credit for Processing or Transaction Fee}
    F -- Yes --> G{Add Credit Amount to Refund Amount}
    F -- No --> H{Log Warning}
    G --> E
    H --> E
    E --> I{Find Original Sale Row}
    I --> J{Determine Refund Type (Partial or Full)}
    J --> K{Create Calculation Details String}
    K --> L{Negate Refund Amount}
    L --> M{Format Output Row with Calculation Details}
    M --> N{Write Row to CSV}
```

*   **`process_fee(row, data, current_month, writer, next_listing_fee_is_renew)`:** Handles different types of fees (Listing, Transaction, etc.) by categorizing and summarizing them monthly. It accumulates fee data in the `data` dictionary for later output.

```mermaid
graph LR
    A[Fee Row] --> B{Extract Date, Title, Amount}
    B --> C{Determine Fee Type}
    C --> D{Update Monthly Fee Summary}
    D --> E{Handle Listing Fee Renewal Logic}
    E --> F{Update next_listing_fee_is_renew}
```

**2.3. Helper Functions:**

*   **`calculate_file_hash(filepath)`:** Calculates the SHA-256 hash of a given file to ensure data integrity.
*   **`get_datetime_filename()`:** Generates a timestamped filename, useful for log files.
*   **`configure_logging(filename)`:** Sets up the logging system to write messages to a file for debugging and tracking.
*   **`load_orders_file(orders_file)`:** Loads the orders CSV file to provide address information for sales and refund rows.
*   **`update_fees(data, recipient, fee_type, fees_taxes)`:** Updates the accumulated fee data in the `data` dictionary.
*   **`write_summarized_data(data, last_day_of_month, writer)`:** Writes the summarized monthly fee data to the output CSV.

### 3. Data Structures

The script utilizes a few essential data structures:

*   **`data` (dictionary):** Stores summarized fee information. The keys are fee recipients (e.g., "Etsy Ireland UC"), and the values are dictionaries containing fee types (e.g., "Listing Fees") and their corresponding accumulated amounts.
*   **`rows` (list):** Holds all rows read from the input CSV file, allowing for efficient searching for related entries (e.g., matching "Sale" rows with their "Tax" counterparts, or "Refund" rows with their corresponding "Fee Credit" rows).
*   **`orders_dict` (dictionary):**  Created from the `orders.csv` file to store address details. It uses the Order ID as the key, and each value is a dictionary containing the "Full Name" and "Address" associated with that order.

### 4. Example Usage

To run the script:

```bash
python etsy_to_lexoffice.py -infile ./input.csv -outfile ./output.csv --ordersfile ./orders.csv
```

This will:

1. Read the data from `input.csv` (Etsy monthly statement CSV).
2. Read the data from `orders.csv` (Etsy orders CSV).
3. Process the data, including handling sales, deposits, fees, and refunds (both full and partial).
4. Create a new, formatted CSV file named `output.csv` suitable for import into Lexoffice.
5. Generate a log file named `convert_csv_[Date]_[Time].log` with detailed information about the conversion process.

### 5. Error Handling and Logging

The script incorporates error handling using `try-except` blocks to catch potential exceptions during data processing. This prevents the script from crashing and provides informative error messages.

The `logging` module is used extensively to log key events, potential issues, and detailed information about refunds (including calculation details and adjustments for fee credits). This information is written to a timestamped log file, aiding in debugging, monitoring the script's behavior, and understanding how refund amounts are calculated.

### 6. Refund Handling in Detail

The script's refund handling logic is crucial for accurate accounting. Here's a more detailed explanation:

**a. Full Refunds:**

*   The script identifies the original "Sale" row associated with the refund.
*   It retrieves the original sale amount (before any tax deduction).
*   It negates this original sale amount to effectively reverse the sale in the output CSV.

**b. Partial Refunds:**

*   The script starts with the refund amount specified in the "Refund" row.
*   It searches for corresponding "Fee" rows with descriptions like "Credit for processing fee" or "Credit for transaction fee" that are associated with the same order.
*   It adds these fee credit amounts back to the refund amount. This is because when a partial refund is issued, Etsy also credits back a portion of the fees.
*   The calculation details in the output CSV show the original sale amount, the partial refund amount, and the sum of the fee credits, providing transparency into how the final refund amount was determined.

**c. Sales Tax Refunds:**

*   The script identifies sales tax refund rows ("Tax" rows with "Refund to buyer for sales tax").
*   In `process_refund` it subtracts the sales tax refund amount from the initial refund amount.
*   The sales tax refund is also considered in the `process_sale` function to ensure the correct net sale amount is calculated.

### 7. Important Notes

*   **Data Integrity:** The script calculates SHA-256 hashes of the input and output files to help verify data integrity.
*   **Lexoffice Compatibility:** The output CSV is formatted to be compatible with Lexoffice's import requirements, including date format, amount format, and column order.
*   **Error Handling:**  The `try-except` blocks help prevent crashes and provide informative error messages if something goes wrong.
*   **Logging:** The detailed logging helps you understand how the script is processing the data and troubleshoot any issues.
*   **Partial Refunds:** The script handles partial refunds correctly by adding back any associated fee credits to the initial refund amount, providing an accurate net refund value.

This documentation provides a comprehensive understanding of the Etsy CSV conversion script, particularly focusing on the intricacies of refund handling. By following the explanations, diagrams, and examples, you can easily grasp the code's functionality, data flow, and its suitability for preparing Etsy data for Lexoffice import. Remember to always double-check the generated output to ensure accuracy before importing it into your accounting software.
