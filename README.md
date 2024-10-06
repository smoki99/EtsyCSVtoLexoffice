Du hast Recht, da habe ich mich vertan. In diesem Fall sind Deposits Auszahlungen *von* Etsy und somit Ausgaben, da sie den Etsy-Verkaufserlös reduzieren, der auf dein externes Konto fließt. 

Ich werde die Dokumentation entsprechend anpassen:

# EtsyCSVtoLexoffice: Etsy-CSV für Lexoffice konvertieren

Dieses Python-Programm konvertiert eine CSV-Datei von Etsy in ein Format, das für den Import in Lexoffice geeignet ist. Es liest die Datei `input.csv` ein, verarbeitet die Daten und schreibt sie in die Datei `output.csv`. Zusätzlich wird eine Log-Datei erstellt, die den Konvertierungsprozess dokumentiert. 

**Wichtiger Hinweis:** Dieses Programm dient nur zu Demonstrationszwecken. Der Autor übernimmt keine Garantie für die steuerliche Richtigkeit der Konvertierung. Es liegt in Ihrer Verantwortung, die konvertierten Daten vor dem Import in Lexoffice zu überprüfen und sicherzustellen, dass sie den aktuellen steuerlichen Vorschriften entsprechen.

## Voraussetzungen

* **Python 3:** Stellen Sie sicher, dass Python 3 auf Ihrem System installiert ist. Sie können Python von [https://python.org](https://python.org) herunterladen.
* **Installierte Pakete:** Sie müssen die Pakete `pandas` und `hashlib` installieren. Führen Sie dazu folgenden Befehl in Ihrer Konsole aus: 
    ```bash
    pip install pandas hashlib
    ```

## Anleitung

1. **CSV-Datei von Etsy herunterladen:** Laden Sie die gewünschte CSV-Datei aus Ihrem Etsy-Shop herunter. 
2. **CSV-Datei umbenennen:** Benennen Sie die heruntergeladene CSV-Datei in `input.csv` um.
3. **Skript herunterladen:** Laden Sie die Datei `etsy_to_lexoffice.py` herunter und speichern Sie sie im gleichen Verzeichnis wie die `input.csv`.
4. **Skript ausführen:** Öffnen Sie Ihre Konsole, navigieren Sie zum Verzeichnis der Dateien und führen Sie das Python-Skript aus.  
    ```bash
    python etsy_to_lexoffice.py 
    ```
    Das Skript erstellt eine neue CSV-Datei namens `output.csv`, die für den Import in Lexoffice bereit ist. Außerdem wird eine Log-Datei erstellt, die detaillierte Informationen über den Konvertierungsprozess enthält.
5. **CSV-Datei in Lexoffice importieren:** Importieren Sie die Datei `output.csv` in Lexoffice.

## Funktionsweise im Detail

Das Programm arbeitet in drei Schritten:

### 1. Einlesen und Vorbereiten der Daten

* **Einlesen der Etsy-CSV:** Das Programm liest die Datei `input.csv` ein. Diese Datei sollte die von Etsy heruntergeladene CSV-Datei sein, die in Schritt 2 umbenannt wurde.
* **Initialisierung:** Es werden Variablen initialisiert, um den aktuellen Monat, die aufgelaufenen Gebühren und andere relevante Daten zu speichern. 

### 2. Verarbeitung der Daten

Das Programm iteriert über jede Zeile der `input.csv` und führt je nach Typ der Zeile unterschiedliche Aktionen aus:

* **Auszahlungen (Deposits):** Auszahlungen von Etsy werden erkannt und die relevanten Daten (Datum, Betrag) extrahiert. Das Datum wird von dem Format "Monat Tag, Jahr" in "Tag.Monat.Jahr" umgewandelt. Der Betrag wird als positiver Wert gespeichert, da es sich um eine Ausgabe handelt, die den Etsy-Verkaufserlös reduziert.
* **Verkäufe (Sales):** Verkäufe werden erkannt und die Daten (Datum, Käufer, Bestellnummer, Betrag) extrahiert. Das Datum wird wie bei den Auszahlungen umgewandelt. Der Betrag wird um eventuelle Steuern bereinigt, die Etsy direkt einbehalten hat.
* **Gebühren (Fees) und Marketing:** Gebühren und Marketingausgaben werden erkannt und die Daten (Datum, Art der Gebühr, Betrag) extrahiert. Das Datum wird in das gewünschte Format umgewandelt. Der Betrag wird aufsummiert und nach Art der Gebühr gruppiert. 
* **Monatliche Zusammenfassung:** Am Ende jedes Monats werden die aufgelaufenen Gebühren und Marketingausgaben in die `output.csv` geschrieben.

### 3. Schreiben der Daten

* **Erstellen der `output.csv`:** Das Programm erstellt die Datei `output.csv` und schreibt die konvertierten Daten in der richtigen Reihenfolge und im richtigen Format hinein. 
* **Log-Datei:** Parallel zum Konvertierungsprozess wird eine Log-Datei erstellt. Diese Datei enthält detaillierte Informationen über jede verarbeitete Zeile, z.B. den Typ der Zeile, die extrahierten Daten und eventuelle Fehlermeldungen. Die Log-Datei ist hilfreich, um Fehler zu finden und den Konvertierungsprozess nachzuvollziehen.


##  Speichern der Dateien

Nach der Ausführung des Programms finden Sie die folgenden Dateien in dem Verzeichnis, in dem Sie das Skript ausgeführt haben:

* **`input.csv`:** Die von Ihnen bereitgestellte Etsy-CSV-Datei.
* **`output.csv`:** Die für den Import in Lexoffice konvertierte CSV-Datei.
* **`etsy_to_lexoffice.py`:** Das Python-Skript.
* **`convert_csv_[Datum]_[Zeit].log`:** Die Log-Datei mit detaillierten Informationen zum Konvertierungsprozess.

Bewahren Sie diese Dateien an einem sicheren Ort auf, um Ihre Buchhaltungsunterlagen zu vervollständigen und bei Bedarf darauf zugreifen zu können.

## Anpassung

Das Skript kann an Ihre individuellen Bedürfnisse angepasst werden. Sie können z. B. die Art und Weise ändern, wie bestimmte Daten extrahiert oder formatiert werden. Beachten Sie jedoch, dass Änderungen am Code zu unerwünschten Ergebnissen führen können.

## Haftungsausschluss

Dieses Programm wird ohne jegliche Gewährleistung bereitgestellt. Der Autor haftet nicht für Schäden, die durch die Verwendung dieses Programms entstehen.
