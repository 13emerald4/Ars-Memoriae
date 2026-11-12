import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('pdf_extracted_text.txt', encoding='utf-8') as f:
    text = f.read()

# Let's inspect how question and citation are structured
sections_def = [
    ("07 Roma y Cartago", "7. Roma y Cartago\n", "8. La conquista romana de la Península\n", range(1, 9)),
    ("08 La conquista romana de la Península", "8. La conquista romana de la Península\n", "9. La organización romana de la Península\n", range(9, 12)),
    ("09 La organización romana de la Península", "9. La organización romana de la Península\n", "10. La romanización de la Península\n", range(12, 23)),
    ("10 La romanización de la Península", "10. La romanización de la Península\n", "11. Cultura y arte\n", range(23, 29)),
    ("11 Cultura y arte", "11. Cultura y arte\n", "12. La religión de Roma\n", range(29, 37)),
    ("12 La religión de Roma", "12. La religión de Roma\n", "13. La cristianización de la Península", range(37, 46)),
    ("13 La cristianización de la Península y la cultura cristiana", "13. La cristianización de la Península y la cultura cristiana\n", "14. Definiciones\n", range(46, 50)),
]

parsed_items = []

for sec_name, sec_start_str, sec_end_str, q_range in sections_def:
    p1 = text.find(sec_start_str)
    p2 = text.find(sec_end_str)
    sec_text = text[p1 + len(sec_start_str):p2]
    sec_text = re.sub(r'=== PAGE \d+ ===\s*SPAN 321[^\n]+\n', '', sec_text)
    sec_text = re.sub(r'\n\s*\d+\s*\n', '\n', sec_text)

    for q_num in q_range:
        m = re.search(rf'(?:^|\n){q_num}\.\s*(⋆\s*)?(.*?)(?=(?:\n{q_num+1}\.|$))', sec_text, re.DOTALL)
        star = bool(m.group(1))
        raw = m.group(2).strip()

        # In the raw text, let's see how question vs answer is split.
        # Most questions end with '?' followed by a newline, or citation in brackets
        # Let's find first '?' or if it's Q4 ("Da las fechas..."): ends with '.'
        # Let's inspect the lines of raw:
        lines = raw.split('\n')
        # Check if first line ends with '?' or if question spans multiple lines
        q_lines = []
        a_lines = []
        found_q = False

        for idx, line in enumerate(lines):
            l = line.strip()
            if not found_q:
                q_lines.append(l)
                if '?' in l or (q_num in [4, 31] and l.endswith('.')):
                    found_q = True
            else:
                a_lines.append(l)

        q_text = ' '.join(q_lines).strip()
        a_text = '\n'.join(a_lines).strip()

        # Check for citation at the end of answer or question
        # Many answers end with e.g. [Guía 1; T2 4]
        cit_match = re.search(r'\[(Guía\s*\d+[^\]]*)\]', a_text)
        citation = cit_match.group(0) if cit_match else ""

        parsed_items.append({
            "num": q_num,
            "star": star,
            "section": sec_name,
            "question": q_text,
            "answer": a_text,
            "citation": citation
        })

print("Sample parsed items:")
for item in parsed_items[:5]:
    print(f"--- Q{item['num']} (Star={item['star']}) ---")
    print("QUESTION:", item['question'])
    print("CITATION:", item['citation'])
    print("ANSWER:\n", item['answer'][:150])
