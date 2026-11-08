import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('pdf_extracted_text.txt', encoding='utf-8') as f:
    text = f.read()

p2_start = text.find('7. Roma y Cartago')
p2_end = text.find('14. Definiciones')
p2_text = text[p2_start:p2_end]

# Clean out page headers and page numbers
cleaned = re.sub(r'=== PAGE \d+ ===\s*SPAN 321[^\n]+\n', '', p2_text)
cleaned = re.sub(r'\n\s*\d+\s*\n', '\n', cleaned)

# Split by question numbers
# Each question starts with \n<n>. or at start
q_dict = {}
for n in range(1, 50):
    # match start of question n
    # search for e.g. "\n1. " or "^1. "
    m = re.search(rf'(?:^|\n){n}\.\s*(⋆\s*)?(.*?)(?=(?:\n\d+\.|\n[A-Z0-9\.\s]+—|\n\d+\s+[A-Z]|$))', cleaned, re.DOTALL)
    if m:
        star = bool(m.group(1))
        content = m.group(2).strip()
        q_dict[n] = {'star': star, 'content': content}
    else:
        print(f"FAILED TO EXTRACT Q{n}")

print(f"Extracted {len(q_dict)} items.")

with open('extracted_q_raw.json', 'w', encoding='utf-8') as f:
    json.dump(q_dict, f, ensure_ascii=False, indent=2)

print("Saved raw extracted items to extracted_q_raw.json")
