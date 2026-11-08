import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('pdf_extracted_text.txt', encoding='utf-8') as f:
    pdf_text = f.read()

with open('span321_current_cards.json', encoding='utf-8') as f:
    cards = json.load(f)

print("================================================================================")
print("COMPREHENSIVE AUDIT REPORT: SPAN 321 EXAMEN 1 CARDS VS MASTER PDF")
print("================================================================================")
print(f"Total cards in Database: {len(cards)}")

# 1. Structure & Rules Analysis
print("\n--- 1. MASTER GUIDE RULES (Page 3 of PDF) ---")
print("Rule 1: Responde a lo que se pregunta en la primera frase (siglo/año primero).")
print("Rule 2: Sigue el orden del PPT estrictamente.")
print("Rule 3: Una idea por frase, con fecha o nombre. Cero vaguedad ('hace mucho', etc.).")
print("Rule 4: No mezcles pueblos ni temas.")
print("Rule 5: Usa el vocabulario técnico del PPT (hieratismo, policromía, atomismo, municipio...).")
print("Rule 6 (Implicit): Todas las respuestas incluyen procedencia en corchetes [Guía X; T2 Y].")

# 2. Part I Audit (Midterm 1 Questions 1.1 - 2)
part1_audit = [
    {
        "id": "1.1",
        "title": "Arte rupestre de Altamira [T1 4–12]",
        "db_card": 13, # 1-based index in cards
        "pdf_req": "6 características numeradas: 1. Figuras grandes (bisontes, osos, caballos), 2. Polícromas (rojo, amarillo, negro), 3. En reposo (de pie o sentado), 4. Aisladas (sin formar escenas), 5. Simplicidad de trazado, 6. Sentido realista (protuberancias de la roca). + Neandertal (40k) y Paleolítico (10k).",
        "current_status": "TRUNCATED & MODIFIED into ASCII tree. Missing animal species, repose details, isolated details, Neanderthal context, and [T1 4–12] citation."
    },
    {
        "id": "1.2",
        "title": "Organización política de los íberos [T1 46–47]",
        "db_card": 3,
        "pdf_req": "Respuesta directa: tribus territoriales independientes, no basadas en lazos familiares. + Origen norteafricano (hacia 3000 a.C.), sociedad agraria, guerreros respetados, devoción ibérica.",
        "current_status": "TRUNCATED into ASCII tree. Missing North African origin (3000 a.C.), devoción ibérica details, and [T1 46–47] citation."
    },
    {
        "id": "1.3",
        "title": "Concepto moderno de provincia [Intro 8, 24–25]",
        "db_card": 1,
        "pdf_req": "Primera frase: 'En el siglo XIX, entre 1812 y 1833'. 4 etapas: Roma (3 provincias), Edad Media (reinos), S. XVIII (Borbones centralizan), S. XIX (1812-1833 división moderna Javier de Burgos).",
        "current_status": "CONVERTED to ASCII tree. First sentence present, but loses Javier de Burgos and citation [Intro 8, 24–25]."
    },
    {
        "id": "1.4",
        "title": "Contexto político de Ocho apellidos vascos [Topic Notes 1–3]",
        "db_card": 2,
        "pdf_req": "Primera frase: cese definitivo de la actividad armada de ETA en 2011. + Clima social y político (Urkullu, fin del miedo), humor vs horror (superación del trauma), normalización y 'marca vasca'.",
        "current_status": "TRUNCATED into ASCII tree. Missing Urkullu / PNV context, 'marca vasca', and [Topic Notes 1–3] citation."
    },
    {
        "id": "1.5",
        "title": "La Dama de Elche [T1 49–50, 55, 96, 99]",
        "db_card": [14, 15],
        "pdf_req": "5 partes: 1. Qué es (busto, totalmente policromado), 2. Cultura/época (íbera, s. III-II a.C.), 3. Representación (dama ibérica, dos grandes rodetes/aros, peineta con velo, joyas en el pecho), 4. Función (decorativa, no votiva), 5. Influencias griega (serenidad y proporción del rostro) y oriental (joyas recargadas y rodetes).",
        "current_status": "SPLIT into two separate cards (Card 14 and Card 15), both formatted with ASCII trees. Missing oriental vs Greek facial contrast depth and slide citations."
    },
    {
        "id": "2",
        "title": "Ensayo modelo sobre Roma (hasta el arte) (~550 palabras)",
        "db_card": 16,
        "pdf_req": "Ensayo cronológico con 4 párrafos de cuerpo: 1. Roma y Cartago (218 a.C., II Guerra Púnica), 2. La conquista (218 a.C. a 19 a.C., Viriato y Numancia), 3. La organización (derecho romano, Ius Latii, municipios, provincias), 4. La romanización (unidad social/cultural, atomismo, latín).",
        "current_status": "OUTLINE ONLY in Card 16 formatted with ASCII tree. Missing full prose model and citations."
    }
]

print("\n--- 2. PART I (MIDTERM 1 SOLUTIONS) AUDIT ---")
for p in part1_audit:
    print(f"Item {p['id']}: {p['title']}")
    print(f"  Current DB Card(s): {p['db_card']}")
    print(f"  Status: {p['current_status']}")

# 3. Part II Questions Mapping (1 to 49)
print("\n--- 3. PART II QUESTIONS (1 TO 49) AUDIT ---")

# Let's map each of the 49 questions manually to be 100% accurate:
part2_cards_map = {
    1: {"card": 6, "status": "PRESENT (ASCII tree, missing [Guía 1; T2 4])"},
    2: {"card": 7, "status": "PRESENT (ASCII tree, missing [Guía 1; T2 4])"},
    3: {"card": 8, "status": "MERGED with Q4 into Card 8 (missing non-direct interest explanation, missing [Guía 1; T2 4])"},
    4: {"card": 8, "status": "MERGED with Q3 into Card 8 (missing territorial losses and Aníbal supply cuts details, missing [Guía 1; T2 4])"},
    5: {"card": 9, "status": "PRESENT (ASCII tree, missing [Guía 1; T2 4])"},
    6: {"card": 10, "status": "PRESENT (ASCII tree, missing [Guía 1; T2 4])"},
    7: {"card": None, "status": "COMPLETELY MISSING: '¿Por qué entraron los romanos por Ampurias? [Guía 1; T2 4]'"},
    8: {"card": 11, "status": "PRESENT (ASCII tree, missing [Guía 1; T2 4])"},
    9: {"card": 12, "status": "MERGED into generic Conquista Card 12 (missing dates 218-19 a.C., 200 years duration, missing [Guía 2; T2 5–7])"},
    10: {"card": 12, "status": "MERGED into generic Conquista Card 12 (missing Viriato / lusitanos guerilla, Numancia / celtíberos siege, cántabros y astures, missing [Guía 2; T2 6])"},
    11: {"card": 12, "status": "MERGED into generic Conquista Card 12 (missing 19 a.C. Augusto Pax Romana, missing [Guía 2; T2 5, 7])"},
    12: {"card": 29, "status": "PRESENT (ASCII tree, missing [Guía 2; T2 8])"},
    13: {"card": 30, "status": "PRESENT (ASCII tree, missing [Guía 2; T2 8])"},
    14: {"card": None, "status": "COMPLETELY MISSING as standalone question: '¿Qué es el paterfamilias? [Guía 2; T2 8]' (only briefly noted in Card 30)"},
    15: {"card": 31, "status": "PRESENT (ASCII tree, missing [Guía 2; T2 8])"},
    16: {"card": 32, "status": "MERGED with Q17 into Card 32 (missing [Guía 2; T2 9–10])"},
    17: {"card": 32, "status": "MERGED with Q16 into Card 32 (missing [Guía 2; T2 9–10])"},
    18: {"card": 33, "status": "MERGED with Q19 into Card 33 (missing [Guía 2; T2 9–10])"},
    19: {"card": 33, "status": "MERGED with Q18 into Card 33 (missing [Guía 2; T2 9–10])"},
    20: {"card": 34, "status": "MERGED with Q21 into Card 34 (missing [Guía 2; T2 11])"},
    21: {"card": 34, "status": "MERGED with Q20 into Card 34 (missing [Guía 2; T2 11])"},
    22: {"card": None, "status": "COMPLETELY MISSING: '¿Es la provincia romana lo mismo que la provincia moderna? [Guía 2; T2 11; Intro 24–25]'"},
    23: {"card": 35, "status": "MERGED with atomismo into Card 35 (missing [Guía 2; T2 12])"},
    24: {"card": None, "status": "COMPLETELY MISSING (HIGH-YIELD ★): '¿Cómo era Hispania en el siglo V, cuando cae el Imperio? [Guía 2; T2 12]'"},
    25: {"card": None, "status": "COMPLETELY MISSING: '¿Fue igual la romanización en todos los pueblos? [Guía 2; T2 12]'"},
    26: {"card": 36, "status": "PRESENT (ASCII tree, missing [Guía 2; T2 12])"},
    27: {"card": 37, "status": "PRESENT (ASCII tree, missing [Guía 2; T2 14])"},
    28: {"card": 38, "status": "PRESENT (ASCII tree, missing [Guía 2; T2 15])"},
    29: {"card": 39, "status": "PRESENT (ASCII tree, missing [Guía 3; T2 16])"},
    30: {"card": 40, "status": "MERGED with artwork Arco de Bará into Card 40 (missing general definition of triumph arch, missing [Guía 3; T2 17])"},
    31: {"card": 41, "status": "MERGED with artwork Teatro de Mérida into Card 41 (missing general definition of Roman theater, missing [Guía 3; T2 18])"},
    32: {"card": 42, "status": "MERGED with Busto de Augusto into Card 42 (missing general portraiture realism, missing [Guía 3; T2 19])"},
    33: {"card": 43, "status": "MERGED with artwork Venus de Itálica into Card 43 (missing [Guía 3; T2 20])"},
    34: {"card": 44, "status": "PRESENT (ASCII tree, missing [Guía 3; T2 21])"},
    35: {"card": 45, "status": "PRESENT (ASCII tree, missing [Guía 3; T2 22])"},
    36: {"card": 46, "status": "PRESENT (ASCII tree, missing [Guía 3; T2 22])"},
    37: {"card": 17, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 23])"},
    38: {"card": 18, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 23])"},
    39: {"card": 19, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 23])"},
    40: {"card": 20, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 24])"},
    41: {"card": 21, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 24])"},
    42: {"card": 22, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 25])"},
    43: {"card": 23, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 25])"},
    44: {"card": None, "status": "COMPLETELY MISSING: '¿Quiénes fueron los Padres de la Iglesia? [Guía 4; T2 26]'"},
    45: {"card": 24, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 26])"},
    46: {"card": 25, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 27])"},
    47: {"card": 26, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 28])"},
    48: {"card": 27, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 28])"},
    49: {"card": 28, "status": "PRESENT (ASCII tree, missing [Guía 4; T2 29])"},
}

missing_count = sum(1 for v in part2_cards_map.values() if v['card'] is None)
merged_count = sum(1 for v in part2_cards_map.values() if 'MERGED' in v['status'])
present_count = sum(1 for v in part2_cards_map.values() if 'PRESENT' in v['status'])

print(f"Part II Summary: {present_count} present (all with trees & missing citations), {merged_count} merged, {missing_count} completely missing.")

# 4. Section 14 (Definiciones)
print("\n--- 4. SECTION 14 (DEFINICIONES) AUDIT ---")
defs_list = [
    'Guerras Púnicas', 'Los Escipiones', 'Viriato', 'Numancia', 'Derecho romano',
    'Paterfamilias', 'Ius Latii', 'Colonos', 'Municipio', 'Provincia romana',
    'Romanización', 'Atomismo', 'Vía Augusta', 'Arco triunfal', 'Estoicismo',
    'Animismo naturista', 'Edicto de Milán', 'Padres de la Iglesia', 'Basílica', 'Hieratismo'
]
print(f"Total definitions required in Section 14: {len(defs_list)}")
print("Current dedicated definition cards in Database: 0 (ZERO!)")
print("All 20 exam-format definitions ('2-3 frases, con fecha o nombre cuando lo haya') are missing as dedicated cards!")

# 5. Section 15 (Obras de Arte)
print("\n--- 5. SECTION 15 (OBRAS DE ARTE - 4-PART SCHEMA) AUDIT ---")
artworks_list = [
    ('1. Arco de Bará, Tarragona', 'Card 40 (merged with Q30, tree format, missing date s. I a.C. and sillares de piedra)'),
    ('2. Teatro romano de Mérida', 'Card 41 (merged with Q31, tree format, missing s. I a.C. Agripa and semicircular tiers)'),
    ('3. Busto del emperador Augusto, Mérida', 'Card 42 (merged with Q32, tree format, missing realism/idealism details)'),
    ('4. Venus de Itálica, Sevilla', 'Card 43 (merged with Q33, tree format, missing Greek influence comparison)'),
    ('5. Mosaico con la cabeza de Medusa, Tarragona', 'Card 44 (merged with Q34, tree format, missing geometric framing and tesserae details)'),
    ('6. Mosaico de Ceres, Mérida', 'COMPLETELY MISSING (ZERO cards for Ceres mosaic!)'),
    ('7. Basílica cristiana', 'Card 26 (tree format, lacks the formal 4-part artwork schema: Qué es / Dónde y cuándo / Qué vemos / Qué significa)')
]
for name, stat in artworks_list:
    print(f"  {name} -> {stat}")

# 6. Section 16 (Ensayos de Práctica)
print("\n--- 6. SECTION 16 (ENSAYOS DE PRÁCTICA) AUDIT ---")
essay_cards = [
    ('Ensayo A: Hispania unida', 'Card 16 (Outline with tree)'),
    ('Ensayo B: Religión de Roma y cristianismo', 'Card 4 (Outline with tree)'),
    ('Ensayo C: Carácter urbano', 'Card 5 (Outline with tree)'),
    ('Ensayo D: Ocho apellidos vascos', 'COMPLETELY MISSING')
]
for name, stat in essay_cards:
    print(f"  {name} -> {stat}")

