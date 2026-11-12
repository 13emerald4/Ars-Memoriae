import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('pdf_extracted_text.txt', encoding='utf-8') as f:
    text = f.read()

# Let's inspect where each section begins and ends
sections = [
    ("Parte I", "1. Pregunta 1.1", "7. Roma y Cartago"),
    ("07 Roma y Cartago", "7. Roma y Cartago", "8. La conquista"),
    ("08 La conquista romana", "8. La conquista romana", "9. La organización"),
    ("09 La organización romana", "9. La organización romana", "10. La romanización"),
    ("10 La romanización", "10. La romanización", "11. Cultura y arte"),
    ("11 Cultura y arte", "11. Cultura y arte", "12. La religión de Roma"),
    ("12 La religión de Roma", "12. La religión de Roma", "13. La cristianización"),
    ("13 La cristianización", "13. La cristianización", "14. Definiciones"),
    ("14 Definiciones", "14. Definiciones", "15. Análisis breve de obras de arte"),
    ("15 Análisis de obras de arte", "15. Análisis breve de obras de arte", "16. Ensayos de práctica"),
    ("16 Ensayos de práctica", "16. Ensayos de práctica", "17. Simulacro de examen"),
]

for name, start_str, end_str in sections:
    p1 = text.find(start_str)
    p2 = text.find(end_str)
    print(f"Section '{name}': start={p1}, end={p2}, len={p2-p1 if p1 != -1 and p2 != -1 else 'ERR'}")
