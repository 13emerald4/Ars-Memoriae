import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('pdf_extracted_text.txt', encoding='utf-8') as f:
    pdf_text = f.read()

with open('span321_current_cards.json', encoding='utf-8') as f:
    cards = json.load(f)

# Inspect sections in PDF
print("=== SECTION HEADERS DETECTED IN PDF ===")
matches = re.findall(r'(?:^|\n)((\d+)\.\s+[^\n]+)', pdf_text)
for m in matches:
    print(m[0])
