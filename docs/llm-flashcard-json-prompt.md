# LLM Prompts & Cognitive Science Card Generation Guide (Ars Memoriae)

Paste the structured prompts below into any LLM chat (ChatGPT, Claude, Gemini, DeepSeek, etc.) alongside your source material, lecture notes, textbook chapters, or existing card decks to generate or refactor high-yield flashcards. Then import the returned JSON via **Decks → Import JSON**, or `POST /api/import/json?deck=<name>`.

---

## 1. Cognitive Science & Flashcard Architecture Principles

Ars Memoriae structures cards according to **Piotr Wozniak’s Minimum Information Principle (SuperMemo)**, **Sweller’s Cognitive Load Theory**, and **Bower’s Hierarchical Semantic Retrieval Theory**:

1. **Direct First-Sentence Rule:** The very first sentence on the back of the card must answer the question directly. If a date, century, name, or key term is requested, that element goes first.
2. **Atomicity (Rule of Atomicity / Eliminating Bloat):** Each card must test only 1–2 distinct facts. Never test a definition, date, and multi-stage evolution on a single card. Split compound facts into discrete sub-cards (e.g. `1A`, `1B`, `1C`).
3. **Elimination of "Wall-of-Text" Essay Cards:** Never place 150+ word essays on the back of a card (this creates an illusion of competence without genuine active recall). Instead, convert complex synthesis and essay questions into **Structural Skeleton Trigger Cards** using hierarchical ASCII trees that outline the core movements, phases, or arguments in sequence.
4. **Cloze Deletion for Lists and Characteristics:** When 4 or more distinct features, elements, or enumerations must be memorized, use Cloze Deletion cards rather than long free-recall lists.
5. **Dual-Coding Schema for Visual Art Pieces & Diagrams:** Every artwork or diagram must adhere to the 4-step dual-coding analysis schema:
   $$\text{1. Qué es (What it is)} \longrightarrow \text{2. Dónde y Cuándo (Where & When)} \longrightarrow \text{3. Qué vemos (Visual Features)} \longrightarrow \text{4. Función / Significado (Significance)}$$
6. **Tree & Subtree Formatting Rules (ASCII Hierarchy Trees):** Incorporate ASCII trees (`├──`, `└──`) into the cards to provide visual chunking and hierarchical organization:
   - **Depth Limit:** 2–3 levels maximum per card (`Parent` $\to$ `Child` $\to$ `Grandchild`).
   - **Context Anchors:** When a card tests a specific atomic node, include a mini-tree on the back highlighting `[ESTA CARTA]` or `[THIS CARD]` to show where it fits into the broader framework.
   - **Macro vs. Micro Testing:** Test top branches first on a Macro card; test sub-branches on separate Micro cards.
7. **No Category Bleed & Technical Vocabulary:** Preserve precise domain terms without mixing distinct historical eras, categories, or modern vs. ancient concepts.
8. **Learn & Practice Socratic Priming (`socratic_lesson` & `key_points`):** Every card powers a two-stage "Learn & Practice" cycle:
   - **Stage 1 (Learn):** The user receives a concise Socratic lesson (80–160 words) establishing the mental model, intuition, and diagnostic questions (e.g., *"How does the runtime/engine differentiate X from Y?"*), along with 2–4 crisp `key_points`.
   - **Stage 2 (Practice):** The user enters the testing phase to actively recall and answer the question from memory without seeing the solution beforehand.

---

## 2. Universal High-Yield Cognitive Science Prompt

```
You are an expert in cognitive science, spaced repetition (Anki/SuperMemo), and high-yield active recall.
Your task is to generate high-retrieval flashcards from the provided study material. The user reviews cards in a Learn & Practice workflow: first receiving a concise Socratic lesson on the concept, and then being tested on the card via active recall.

Output ONLY a JSON array, no prose before or after. Each element is one card formatted as follows:

Basic (question/answer):
{
  "front": "<Atomic question testing 1-2 facts directly>",
  "image": "<Optional image URL: https://... or /media/...>",
  "back": "<Sentence 1: Direct answer. Sentence 2+: Essential context or optional ASCII tree>",
  "socratic_lesson": "<80-160 word concise Socratic lesson teaching the mental model, intuition, and questions to ask yourself before testing>",
  "key_points": ["<Key takeaway 1>", "<Key takeaway 2>", "<Key takeaway 3>"],
  "quote": "<1-4 sentence verbatim excerpt from the source explaining this concept>",
  "locator": "<Slide, chapter, or page reference>",
  "source_title": "<Title of the source material>",
  "tags": ["<topic>", "<subtopic>"]
}

Code (programming / coding challenges):
{
  "kind": "code",
  "title": "<Function or concept title, e.g. describeType(value)>",
  "front": "<Problem statement and requirements>",
  "starter_code": "<Starter code scaffold for the learner>",
  "back": "<Complete solution code>",
  "socratic_lesson": "<80-160 word concise Socratic lesson explaining how the engine, types, and logic work together>",
  "key_points": ["<Key takeaway 1>", "<Key takeaway 2>"],
  "test_cases": [{"input": ..., "expected": ...}],
  "language": "typescript",
  "tags": ["<topic>", "code"]
}

Cloze (fill-in-the-blank, for terms/definitions embedded in a sentence or 4+ item lists):
{
  "kind": "cloze",
  "cloze_text": "<Sentence with the key term wrapped like {{c1::term}}>",
  "image": "<Optional image URL: https://... or /media/...>",
  "back": "<Extra context or hierarchical mini-tree shown after grading, optional>",
  "socratic_lesson": "<80-160 word concise Socratic lesson teaching the underlying concept>",
  "key_points": ["<Key takeaway 1>", "<Key takeaway 2>"],
  "quote": "<1-4 sentence verbatim excerpt from the source>",
  "locator": "<Slide, chapter, or page reference>",
  "source_title": "<Title of the source material>",
  "tags": ["<topic>", "<subtopic>"]
}

Strict Formatting & Cognitive Rules:
1. DIRECT FIRST-SENTENCE RULE: The very first sentence of "back" must directly answer the prompt. If asking for a date, century, or term, put it first.
2. ATOMICITY: One card = one atomic fact. Never combine definition + multi-century history + examples on one card. Split into atomic sub-cards.
3. NO ESSAY DUMPS: Never output 100+ word essay dumps on "back". For multi-phase processes or synthesis questions, output a Structural Skeleton Trigger Card using an ASCII tree:
   Topic Outline
   ├── 1. First Phase / Concept
   ├── 2. Second Phase / Concept
   └── 3. Synthesis / Outcome
4. CLOZE FOR LISTS: If 4 or more distinct characteristics or elements must be recalled, format as cloze deletions ({{c1::...}}) rather than a long free-recall list.
5. DUAL-CODING FOR ART & DIAGRAMS: For visual artworks or diagrams, adhere to the 4-step schema:
   1. Qué es (What it is) -> 2. Dónde y Cuándo (Where & When) -> 3. Qué vemos (Visual Features) -> 4. Función / Significado (Significance/Function).
6. ASCII CONTEXT ANCHORS: When testing a specific sub-branch, you may include a 2-3 level ASCII tree on the back marking [THIS CARD] to maintain spatial context.
7. QUOTE IS MANDATORY: Every card MUST carry a verbatim 1-4 sentence excerpt in "quote" to power Ars Memoriae's Pre-Answer Primer reading mode.
8. SOCRATIC LESSON FOR LEARN & PRACTICE: Every card must include "socratic_lesson" (80-160 words) and "key_points" (2-4 items). Teach the mental model, inquiry process, and diagnostic questions so the learner understands the principles before the quiz tests them. Do NOT simply repeat the back verbatim; teach the concept!

Generate cards from the material below:

<PASTE YOUR SOURCE TEXT / NOTES / TOPIC HERE>
```

---

## 3. Course & Exam Refactoring Prompt (SPAN 321 / Humanities Case Study)

Use this specialized prompt when refactoring university course decks or exam study guides with strict instructor rubrics and historical invariants:

```markdown
# Context & Task: Flashcard Refactoring for SPAN 321 (Culturas de España)

You are an expert in cognitive science, spaced repetition (Anki/SuperMemo), and Spanish cultural history. Your task is to refactor and optimize a flashcard deck (`SPAN321_Examen1_Flashcards.json`) for the course **SPAN 321: Culturas de España** (Instructor: Prof. María Soledad Fernández Utrera / "Marisol").

---

## 1. Instructor Rubric & Exam Constraints (Non-Negotiable)

Marisol evaluates four strict criteria:
1. **Direct First-Sentence Rule:** The very first sentence must answer the question directly. If a century or date is requested, the century/date goes first.
2. **Follow PPT / Chronological Progression:** Do not skip steps or alter chronological sequences.
3. **One Idea Per Sentence:** Concrete facts with explicit names and dates. Never use vague phrases like *"hace mucho"* or *"varios siglos"*.
4. **No Category Bleed:** Never mix pre-Roman peoples (Iberians, Celts, Celtiberians, Phoenicians, Greeks, Carthaginians) or confuse ancient with modern concepts.
5. **Mandatory PPT Vocabulary:** Must preserve technical terms:
   * `hieratismo`
   * `policromía`
   * `atomismo`
   * `paterfamilias`
   * `Ius Latii`
   * `municipio`
   * `animismo naturista`
   * `estoicismo`
   * `basílica`
6. **Instructor Discrepancy Invariants (Overrides standard textbook facts):**
   * **Constantino:** Siglo IV (313 d. C., Edicto de Milán) — *do not use s. III*.
   * **Teodosio:** Refer strictly to "Teodosio (s. IV)" — *do not write "Teodosio II"*.
   * **Córcega y Cerdeña:** Cartago lost Corsica and Sardinia *after* the 1st Punic War and *before* invading Iberia.
   * **Ius Latii vs. Ciudadanía:** *Ius Latii* granted by Vespasiano (s. I d. C.); universal Roman citizenship granted by Caracalla (s. III d. C.).
   * **Provincia moderna:** Emerges in the **19th century (1812–1833)**; distinct from Roman administrative provinces.

---

## 2. Cognitive Science & Flashcard Architecture Rules

Refactor the deck following **Piotr Wozniak’s Minimum Information Principle**, **Sweller’s Cognitive Load Theory**, and **Bower’s Hierarchical Semantic Retrieval Theory**:

### Rule A: Atomicity (Eliminate Bloat)
* No card should require recalling more than 1–2 distinct facts or sentences.
* Never test definition + date + multi-stage history on a single card. Split into sub-cards (e.g., `1A`, `1B`, `1C`).

### Rule B: Elimination of "Wall-of-Text" Essay Cards
* **Do not put 200+ word essays on the back of cards.** This induces the illusion of competence.
* Transform essay questions into **Structural Skeleton Trigger Cards** using hierarchical trees (outlining the 4–5 thematic movements in order).

### Rule C: Use Cloze Deletion for Lists and Characteristics
* When 4 or more distinct features must be memorized (e.g., Altamira cave art, elements of Roman religion), use Cloze Deletion cards rather than long free-recall lists.

### Rule D: Dual-Coding Schema for Art Pieces
Every artwork must strictly adhere to the 4-step analysis schema:
$$\text{1. Qué es} \longrightarrow \text{2. Dónde y Cuándo} \longrightarrow \text{3. Qué vemos} \longrightarrow \text{4. Qué significa / Función}$$

---

## 3. Tree & Subtree Formatting Rules

Incorporate **ASCII trees** (`├──`, `└──`) into the cards to provide clear visual chunking and hierarchical organization:

1. **Depth Limit:** 2–3 levels maximum per card (`Parent` $\to$ `Child` $\to$ `Grandchild`).
2. **Context Anchors:** When a card tests a specific atomic node (e.g., *Municipios* or *Ius Latii*), include the mini-tree on the back highlighting `[ESTA CARTA]` to show where it fits into the broader framework.
3. **Macro vs. Micro Testing:**
   * Test the top branches first on a Macro card.
   * Test the sub-branches on separate Micro cards.

### Visual Tree Templates

#### Hierarchy of Social Classes:
```text
Clases sociales (Roma)
├── 1. Libres
│   ├── Ciudadanos romanos (Caracalla, s. III d. C.)
│   ├── Latinos (Ius Latii, Vespasiano, s. I d. C.)
│   └── Extranjeros
├── 2. Semilibres (colonos)
└── 3. Esclavos
```

#### Territorial Organization:
```text
Organización territorial
├── Colonias romanas (legionarios veteranos [30 años] + colonos semilibres)
├── Municipios (ciudades indígenas aliadas, autónomas, leyes propias, gran arraigo)
└── Provincias (regiones naturales e identidades)
    ├── Principales: Tarraconense, Lusitana, Bética
    └── Posteriores: Galaica, Cartaginense, Mauritana, Baleárica
```

#### Composition of Roman Religion:
```text
Religión romana (mezcla de 4 elementos)
├── 1. Mitología griega
├── 2. Culto al emperador (político y religioso)
├── 3. Animismo naturista (poderes a la naturaleza)
└── 4. Abstracción de conceptos sociopolíticos (ej. juventud)
```

#### Evolution of the "Provincia" Concept:
```text
Evolución de la división territorial
├── 1. Roma: Tarraconense, Lusitana, Bética
├── 2. Edad Media: Reinos divididos (Asturias, León, Castilla, Aragón, Al-Andalus)
├── 3. Siglo XVIII: Borbones centralizan y eliminan derechos regionales
└── 4. Siglo XIX (1812–1833): Surge el concepto moderno (50 provincias / 17 CCAA)
```

#### Universal Essay A Skeleton (Presencia de Roma):
```text
Ensayo A: Hispania Unida
├── Tesis: Con Roma empieza España como nación (unidad política y económica)
├── 1. Llegada: Guerras Púnicas (I, II [218 a.C., Escipiones, Ampurias], III)
├── 2. Conquista: 2 siglos (Viriato, Numancia, astures y cántabros; 38 a.C. Augusto)
├── 3. Organización: Derecho romano, clases, colonias/municipios, provincias
├── 4. Romanización: Unidad frente al atomismo, ritmos, latín, emperadores
└── Conclusión: Herencia viva (derecho, lengua, municipios, concepto de nación)
```

---

## 4. Target JSON Schema

When generating or refactoring cards, format each item using this JSON schema:

```json
{
  "card_type": "qa",
  "front": "Prompt strictly adhering to Marisol's questions or atomic triggers",
  "image": "/media/image_name.jpg",
  "back": "Direct answer in sentence 1 + optional ASCII tree for context",
  "cloze_text": "Text with {{c1::cloze deletions}} if card_type is cloze",
  "quote": "1-4 sentence verbatim excerpt from course PPT/reading",
  "locator": "Slide or guide reference",
  "tags": ["topic", "subtopic"]
}
```

---

## 5. Execution Directive

Parse the provided flashcard deck:
1. Split every composite/bloated question into single-idea atomic cards.
2. Convert multi-item lists into Cloze Deletions.
3. Convert 200+ word essay answers into structural ASCII tree outlines.
4. Add ASCII context trees to definitions and organizational questions.
5. Ensure 100% compliance with Marisol's strict vocabulary and historical date invariants.
```

---

## 4. Complete Output Examples

```json
[
  {
    "card_type": "qa",
    "front": "Dama de Elche: ¿qué tipo de escultura es, a qué cultura pertenece y cuál era su función según el PPT?",
    "image": "/media/span321_dama_elche.jpg",
    "back": "Es un busto de escultura decorativa perteneciente a la cultura ibérica (siglos III–II a. C.) con influencia griega, sin función religiosa.\n\nEsquema de análisis (Dama de Elche):\n├── 1. Qué es: Busto policromado con grandes aros y peineta con velo\n├── 2. Cuándo: Siglos III–II a. C. (cultura ibera con influencia griega)\n├── 3. Función: Escultura decorativa (no votiva ni religiosa)\n└── 4. Rasgo clave: Hieratismo en el rostro y detalle en las joyas",
    "quote": "Dama de Elche. Se estima ser obra de la cultura ibera, ya influida por la griega, entre el siglo III y II antes de Cristo. El PPT la clasifica como escultura decorativa, no entre las figuras votivas (religiosas).",
    "locator": "Tema 1 PPT, diap. 49, 55 · Guía de estudio, P. 1.5",
    "tags": ["arte prerromano", "íberos", "Dama de Elche"]
  },
  {
    "card_type": "cloze",
    "cloze_text": "Los cuatro elementos de la religión romana tradicional eran: la {{c1::mitología griega}}, el {{c2::culto al emperador}}, el {{c3::animismo naturista}} y la {{c4::abstracción de conceptos sociopolíticos}}.",
    "back": "Religión romana (mezcla sincrética de 4 elementos)\n├── 1. Mitología griega\n├── 2. Culto al emperador (político y religioso)\n├── 3. Animismo naturista (poderes a la naturaleza)\n└── 4. Abstracción de conceptos sociopolíticos (ej. juventud)",
    "quote": "La religión romana se componía de: Mitología griega, Culto al emperador, Animismo naturista y Abstracción de conceptos sociopolíticos.",
    "locator": "Tema 2 PPT, diap. 63 · Guía de Marisol, pp. 3–4",
    "tags": ["religión romana", "roma"]
  },
  {
    "card_type": "qa",
    "front": "★ ¿Qué era el Ius Latii y a quién se aplicaba en Hispania?",
    "back": "El Ius Latii otorgaba los derechos del derecho romano a los latinos en el plano civil, comercial y matrimonial, pero no en el político (no podían votar ni ser magistrados en Roma).\n\nClases sociales (Roma)\n├── 1. Libres\n│   ├── Ciudadanos romanos (Caracalla, s. III d. C.)\n│   ├── Latinos (Ius Latii, Vespasiano, s. I d. C.) <-- [ESTA CARTA]\n│   └── Extranjeros\n├── 2. Semilibres (colonos)\n└── 3. Esclavos",
    "quote": "Ius Latii: El derecho romano se aplicaba a los ciudadanos romanos y a los latinos. Los latinos disfrutaban de algunos derechos civiles, comerciales y matrimoniales, pero no políticos.",
    "locator": "Tema 2 PPT, diap. 12 · Guía de Marisol, p. 2",
    "tags": ["organización romana", "derecho romano", "Ius Latii"]
  }
]
```

---

## 5. Importing into Ars Memoriae

- **Web UI:** Decks → **Import JSON** → paste the JSON array → name the deck → click **Import**.
- **REST API:** `POST /api/import/json?deck=<Deck+Name>` with the JSON array as the request body.
- **Learn & Practice:** Every card with a non-empty `quote` field automatically unlocks reading citations and the Pre-Answer Primer.

---

## 6. Code Cards (JavaScript, TypeScript, Python)

A code card is graded by running the answer against its tests, so it needs a
starter, a reference answer and test cases. The function the tests call must
be the **first** function in the code.

```json
{
  "kind": "code",
  "language": "typescript",
  "title": "firstElement<T>(arr)",
  "front": "Return the first item of an array, or undefined when it is empty.",
  "starter_code": "function firstElement(arr: any[]): any {\n  return undefined;\n}",
  "back": "function firstElement<T>(arr: T[]): T | undefined {\n  return arr[0];\n}",
  "test_cases": [
    { "input": [["a", "b"]], "expected": "a" },
    { "input": [[]], "expected": { "$undefined": true } }
  ],
  "type_check": true,
  "type_tests": "// @ts-expect-error: the result may be undefined\nconst n: number = firstElement([1]);"
}
```

- **`input`** is the argument list (`[arg1, arg2]`). Wrap a single array argument in another array.
- **`{"$undefined": true}`** stands for `undefined`, which JSON can't write, in an input or as `expected`.
- **`{"$throws": "RangeError: too big"}`** expects the call to throw (or reject) with an error whose `Name: message` contains that text.
- **`type_check`** (TypeScript) also checks the answer with the compiler in strict mode; **`type_tests`** are extra lines that must compile, and `// @ts-expect-error` lines that must *not* — use them to reject answers typed `any`.
- Include tests for the edge cases (empty input, boundaries, error paths), not only the happy path: a test suite that a wrong answer passes grades that wrong answer as correct.
