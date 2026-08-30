# Activate Environment
source ./csvetsyconverter/bin/activate

# Eigenbelege
python ./csv_to_xrechnung.py ./eigenbeleg_input.csv ./xrechnungen/

# Etsy Belege
python ./etsy_to_lexoffice.py -infile ./etsy_statement_2026_1.csv -outfile ./etsy_statement_2026_1-processed.csv