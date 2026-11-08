import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('pdf_extracted_text.txt', encoding='utf-8') as f:
    text = f.read()

# Let's define the section boundaries exactly
sections_def = [
    ("07 Roma y Cartago", "7. Roma y Cartago\n", "8. La conquista romana de la Península\n", range(1, 9)),
    ("08 La conquista romana de la Península", "8. La conquista romana de la Península\n", "9. La organización romana de la Península\n", range(9, 12)),
    ("09 La organización romana de la Península", "9. La organización romana de la Península\n", "10. La romanización de la Península\n", range(12, 23)),
    ("10 La romanización de la Península", "10. La romanización de la Península\n", "11. Cultura y arte\n", range(23, 29)),
    ("11 Cultura y arte", "11. Cultura y arte\n", "12. La religión de Roma\n", range(29, 37)),
    ("12 La religión de Roma", "12. La religión de Roma\n", "13. La cristianización de la Península", range(37, 46)),
    ("13 La cristianización de la Península y la cultura cristiana", "13. La cristianización de la Península y la cultura cristiana\n", "14. Definiciones\n", range(46, 50)),
]

all_parsed_questions = {}

for sec_name, sec_start_str, sec_end_str, q_range in sections_def:
    p1 = text.find(sec_start_str)
    p2 = text.find(sec_end_str)
    sec_text = text[p1 + len(sec_start_str):p2]
    
    # Clean page markers from sec_text
    sec_text = re.sub(r'=== PAGE \d+ ===\s*SPAN 321[^\n]+\n', '', sec_text)
    # Remove standalone page numbers on their own line
    sec_text = re.sub(r'\n\s*\d+\s*\n', '\n', sec_text)
    
    print(f"\n=== SECTION: {sec_name} (Questions {list(q_range)[0]} to {list(q_range)[-1]}) ===")
    
    q_list = list(q_range)
    for idx, q_num in enumerate(q_list):
        # find question header
        # e.g., "\n1. " or "^1. "
        q_match = re.search(rf'(?:^|\n){q_num}\.\s*(⋆\s*)?(.*?)(?=(?:\n{q_num+1}\.|$))', sec_text, re.DOTALL)
        if not q_match:
            print(f"ERROR: Could not match Q{q_num} in section {sec_name}")
            continue
        
        star = bool(q_match.group(1))
        body = q_match.group(2).strip()
        
        # In body, the question line is before the answer.
        # Find citation [Guía X; T2 Y] or question mark
        # Let's inspect the first lines
        lines = [line.strip() for line in body.split('\n') if line.strip()]
        
        all_parsed_questions[q_num] = {
            "section": sec_name,
            "q_num": q_num,
            "star": star,
            "raw_body": body
        }
        
        st_mark = "★ " if star else "  "
        print(f"  Q{q_num:02d} {st_mark}{lines[0][:65]}")

print(f"\nSuccessfully parsed {len(all_parsed_questions)} questions!")
