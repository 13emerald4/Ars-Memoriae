import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('pdf_extracted_text.txt', encoding='utf-8') as f:
    text = f.read()

p2_start = text.find('7. Roma y Cartago')
p2_end = text.find('14. Definiciones')
p2_text = text[p2_start:p2_end]

# Section headers in Parte II
section_names = [
    (7, "07 Roma y Cartago"),
    (8, "08 La Conquista Romana"),
    (9, "09 La Organización Romana"),
    (10, "10 La Romanización"),
    (11, "11 Cultura y Arte Romano"),
    (12, "12 La Religión de Roma"),
    (13, "13 La Cristianización de Hispania")
]

# Let's inspect each question's exact text in the PDF
for q_num in range(1, 50):
    # Pattern to match the question start:
    # e.g., \n1. or \n2. ⋆
    # Find position of f"\n{q_num}."
    pos = p2_text.find(f"\n{q_num}.")
    if pos == -1 and p2_text.startswith(f"{q_num}."):
        pos = 0
    if pos == -1:
        print(f"ERROR: Could not find Q{q_num}")
        continue

    # Next question or end
    next_pos = p2_text.find(f"\n{q_num+1}.", pos + 2)
    if next_pos == -1:
        if q_num == 49:
            next_pos = len(p2_text)
        else:
            # Maybe there is a section header between questions
            # Let's find next number
            m = re.search(r'\n(?:\d+\.\s+[A-Z]|\d+\.)', p2_text[pos+3:])
            if m:
                next_pos = pos + 3 + m.start()
            else:
                next_pos = len(p2_text)

    q_block = p2_text[pos:next_pos].strip()
    # Clean out page headers like "=== PAGE 9 ===\nSPAN 321 · E XAMEN 1 · R ECUPERACIÓN Michael Polley"
    q_block_clean = re.sub(r'=== PAGE \d+ ===\s*SPAN 321[^\n]+\n', '', q_block)
    q_block_clean = re.sub(r'\n\d+\s*\n', '\n', q_block_clean)

    first_line = q_block_clean.split('\n')[0]
    print(f"[{q_num:02d}] {first_line}")
