import json, re, sys

sys.stdout.reconfigure(encoding='utf-8')

with open('pdf_extracted_text.txt', encoding='utf-8') as f:
    pdf_text = f.read()

with open('span321_current_cards.json', encoding='utf-8') as f:
    cards = json.load(f)

part1_items = [
    ('1.1', '¿Cuáles son las características del arte rupestre de Altamira?'),
    ('1.2', '¿Cómo se organizaban los íberos a nivel político?'),
    ('1.3', '¿En qué siglo surge el concepto moderno de provincia?'),
    ('1.4', 'Contexto político de Ocho apellidos vascos'),
    ('1.5', 'La Dama de Elche (busto, cultura, representación, función, influencias)'),
    ('2', 'Ensayo modelo sobre la primera parte de Roma'),
]

part2_text = pdf_text[pdf_text.find('7. Roma y Cartago'):pdf_text.find('14. Definiciones')]
q_pattern = re.compile(r'(?:^|\n)(\d+)\.\s*(⋆\s*)?([^\n]+)', re.MULTILINE)
part2_questions = {}
for m in q_pattern.finditer(part2_text):
    n = int(m.group(1))
    if 1 <= n <= 49 and n not in part2_questions:
        t = m.group(3).strip().replace('⋆', '').strip()
        part2_questions[n] = {'star': bool(m.group(2)) or '⋆' in m.group(3), 'title': t}

defs = [
    'Guerras Púnicas', 'Los Escipiones', 'Viriato', 'Numancia', 'Derecho romano',
    'Paterfamilias', 'Ius Latii', 'Colonos', 'Municipio', 'Provincia romana',
    'Romanización', 'Atomismo', 'Vía Augusta', 'Arco triunfal', 'Estoicismo',
    'Animismo naturista', 'Edicto de Milán', 'Padres de la Iglesia', 'Basílica', 'Hieratismo'
]

artworks = [
    'Arco de Bará, Tarragona', 'Teatro romano de Mérida', 'Busto del emperador Augusto, Mérida',
    'Venus de Itálica, Sevilla', 'Mosaico con la cabeza de Medusa, Tarragona',
    'Mosaico de Ceres, Mérida', 'Basílica cristiana'
]

essays = [
    'Ensayo A: Hispania unida',
    'Ensayo B: Religión de Roma y cristianismo',
    'Ensayo C: Carácter urbano',
    'Ensayo D: Ocho apellidos vascos'
]

print('=== MASTER GUIDE INVENTORY ===')
print(f'Part I questions: {len(part1_items)}')
print(f'Part II numbered questions: {len(part2_questions)}')
print(f'Section 14 definitions: {len(defs)}')
print(f'Section 15 artworks (4-part schema): {len(artworks)}')
print(f'Section 16 practice essays: {len(essays)}')
total_pdf_items = len(part1_items) + len(part2_questions) + len(defs) + len(artworks) + len(essays)
print(f'TOTAL UNIQUE STUDY ITEMS IN PDF: {total_pdf_items}')
print(f'CURRENT CARDS IN DATABASE: {len(cards)}')
print()

# Check which Part II questions are missing from current DB cards
missing_part2 = []
merged_part2 = []
present_part2 = []

# Keywords to match cards with Part II question numbers
for n in range(1, 50):
    info = part2_questions.get(n)
    if not info: continue
    title = info['title']
    star = '★ ' if info['star'] else ''
    
    # Check matching in cards
    matched_cards = []
    for c in cards:
        cf = c['front'].lower()
        cb = c['back'].lower()
        # Specific matchers
        if n == 1 and 'duró la dominación' in cf: matched_cards.append(c)
        elif n == 2 and 'historia de españa como nación' in cf: matched_cards.append(c)
        elif n == 3 and 'llegaron los romanos a iberia' in cf: matched_cards.append(c)
        elif n == 4 and 'fechas de las tres guerras' in cf: matched_cards.append(c)
        elif n == 5 and 'después de la i guerra púnica' in cf: matched_cards.append(c)
        elif n == 6 and 'en la ii guerra púnica' in cf: matched_cards.append(c)
        elif n == 7 and 'ampurias' in cf: matched_cards.append(c)
        elif n == 8 and 'caída de cartago' in cf: matched_cards.append(c)
        elif n == 9 and 'qué fue la conquista y cuánto duró' in cf: matched_cards.append(c)
        elif n == 10 and 'pueblos opusieron resistencia' in cf: matched_cards.append(c)
        elif n == 11 and 'pasar hispania a formar parte del imperio' in cf: matched_cards.append(c)
        elif n == 12 and 'sistemas coexistieron' in cf: matched_cards.append(c)
        elif n == 13 and 'derecho romano' in cf and 'mayor contribución' in cf: matched_cards.append(c)
        elif n == 14 and 'paterfamilias' in cf: matched_cards.append(c)
        elif n == 15 and 'clases sociales' in cf: matched_cards.append(c)
        elif n == 16 and 'era el ius latii' in cf: matched_cards.append(c)
        elif n == 17 and 'recibió hispania el ius latii' in cf: matched_cards.append(c)
        elif n == 18 and 'diferenciaban las colonias' in cf: matched_cards.append(c)
        elif n == 19 and 'importantes los municipios' in cf or 'importan' in cf: matched_cards.append(c)
        elif n == 20 and 'provincias romanas había' in cf: matched_cards.append(c)
        elif n == 21 and 'reconocer las divisiones' in cf or 'qué reconocían' in cf: matched_cards.append(c)
        elif n == 22 and 'provincia moderna' in cf: matched_cards.append(c)
        elif n == 23 and 'qué es la romanización' in cf: matched_cards.append(c)
        elif n == 24 and 'siglo v' in cf and 'cuando cae el imperio' in cf: matched_cards.append(c)
        elif n == 25 and 'igual la romanización' in cf: matched_cards.append(c)
        elif n == 26 and 'propio ritmo' in cf: matched_cards.append(c)
        elif n == 27 and 'lenguas salieron del latín' in cf: matched_cards.append(c)
        elif n == 28 and 'emperadores' in cf and 'hispania' in cf: matched_cards.append(c)
        elif n == 29 and 'carácter urbano' in cf: matched_cards.append(c)
        elif n == 30 and 'arcos triunfales' in cf: matched_cards.append(c)
        elif n == 31 and 'ejemplo de teatro romano' in cf: matched_cards.append(c)
        elif n == 32 and 'bustos romanos' in cf: matched_cards.append(c)
        elif n == 33 and 'venus de itálica' in cf: matched_cards.append(c)
        elif n == 34 and 'mosaicos romanos' in cf: matched_cards.append(c)
        elif n == 35 and 'séneca' in cf: matched_cards.append(c)
        elif n == 36 and 'lucano' in cf: matched_cards.append(c)
        elif n == 37 and 'elementos se componía la religión' in cf: matched_cards.append(c)
        elif n == 38 and 'actitud tenía roma con las religiones' in cf: matched_cards.append(c)
        elif n == 39 and 'amenaza para roma' in cf: matched_cards.append(c)
        elif n == 40 and 'romanizó' in cf and 'cristianismo' in cf: matched_cards.append(c)
        elif n == 41 and 'todas las clases sociales' in cf: matched_cards.append(c)
        elif n == 42 and 'constantino' in cf: matched_cards.append(c)
        elif n == 43 and 'teodosio' in cf: matched_cards.append(c)
        elif n == 44 and 'padres de la iglesia' in cf: matched_cards.append(c)
        elif n == 45 and 'iglesia es tan importante' in cf: matched_cards.append(c)
        elif n == 46 and 'cómo fue la cristianización' in cf: matched_cards.append(c)
        elif n == 47 and 'arquitectura cristiana' in cf: matched_cards.append(c)
        elif n == 48 and 'escultura cristiana' in cf: matched_cards.append(c)
        elif n == 49 and 'aurelio prudencio' in cf: matched_cards.append(c)

    if not matched_cards:
        # Check if mentioned in combined question Card 12 (conquista)
        if n in [9, 10, 11]:
            merged_part2.append((n, star, title, 'Merged into generic Conquista card'))
        else:
            missing_part2.append((n, star, title))
    elif len(matched_cards) == 1:
        # Check if question text is merged with another question
        q_front = matched_cards[0]['front']
        if ' y ' in q_front and n in [3, 4, 16, 17, 18, 19, 20, 21, 23]:
            merged_part2.append((n, star, title, f'Merged in front: {q_front[:60]}...'))
        else:
            present_part2.append((n, star, title))

print(f'Part II Status: {len(present_part2)} cleanly present, {len(merged_part2)} merged, {len(missing_part2)} completely missing.')
print()
print('--- COMPLETELY MISSING PART II QUESTIONS ---')
for n, st, t in missing_part2:
    print(f'  Q{n:02d}: {st}{t}')

print()
print('--- MERGED / NON-ATOMIC PART II QUESTIONS ---')
for n, st, t, reason in merged_part2:
    print(f'  Q{n:02d}: {st}{t} -> {reason}')
