"""Migrate SPAN 321 flashcards to tree-structured answers in Ars Memoriae.

Converts 36 SPAN 321 cards in backend/dev.db from flat text/paragraphs to
hierarchical box-drawing trees matching the Ocho Apellidos Vascos card standard.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "dev.db"

# Mapping: note_id -> new_back_content
UPDATES: dict[str, str] = {
    # 01.1 Arte Rupestre (Altamira)
    "8c41d3c31ee94cbdb87e458f4e59f057": (
        "Arte de las cuevas de Altamira (Santander, Cantabria), del Paleolítico (hace ~10.000 años).\n\n"
        "Arte rupestre del norte (Altamira)\n"
        "├── Época y lugar: Paleolítico (~10.000 años), Santander (Cantabria)\n"
        "├── Figuras: grandes, aisladas y en reposo\n"
        "├── Color: polícromas (rojo, amarillo y negro)\n"
        "├── Trazo: simple\n"
        "└── Sentido realista: aprovecha protuberancias de la roca para crear volumen"
    ),

    # 01.2 Organización Política Íbera
    "18d0bff3cc944d439b2190d21eda44a5": (
        "No tenían un gobierno común; se organizaban en tribus territoriales sin vínculo familiar agrupadas en naciones.\n\n"
        "Organización política íbera\n"
        "├── Sin gobierno común: fragmentación política\n"
        "├── Tribus: agrupadas en naciones, con amplio territorio\n"
        "└── Vínculo: territorial, sin lazo familiar en la tribu"
    ),

    # 01.5 La Dama de Elche (Card 1: Influencias artísticas)
    "189a80d024174f388f25751eed12e190": (
        "Muestra una síntesis de influencias griegas y orientales (fenicias).\n\n"
        "Influencias artísticas (Dama de Elche)\n"
        "├── Griega: técnica y detalle realista (rostro, ojos, nariz, labios)\n"
        "└── Oriental (fenicia): hieratismo, simetría del cabello, joyas y adornos"
    ),

    # 01.5 La Dama de Elche (Card 2: 4 preguntas)
    "06ec9ee6c8e64c118e5fcc9643730564": (
        "Dama de Elche\n"
        "├── Qué es: busto, totalmente policromado\n"
        "├── Cultura y época: cultura íbera (influida por la griega), siglos III–II a. C.\n"
        "├── Representación: dama ibérica con dos grandes rodetes (aros), peineta con velo y joyas en el pecho\n"
        "└── Función: escultura decorativa (según el PPT), no votiva (religiosa)"
    ),

    # 02 Roma y la Conquista de Hispania
    "888ab1793abf43fa9d5168171bb94981": (
        "Porque los pueblos peninsulares dejan de ser unidades fragmentadas y adquieren unidad política, económica y cultural.\n\n"
        "España como nación con Roma\n"
        "├── Fin del atomismo: dejan de ser unidades fragmentadas\n"
        "├── Intereses comunes: unión bajo la política y economía de Roma\n"
        "└── Unidad cultural: integración en la civilización romana"
    ),
    "1ef333fb59634fb98285956e5859a158": (
        "Llegaron por las Guerras Púnicas (disputa comercial con Cartago, siglos III–II a. C.).\n\n"
        "Guerras Púnicas y llegada de Roma\n"
        "├── Causa: lucha con Cartago por el dominio comercial\n"
        "├── I Guerra Púnica (264–241 a. C.)\n"
        "├── II Guerra Púnica (218–201 a. C.): llegada a la Península (218 a. C.)\n"
        "└── III Guerra Púnica (149–146 a. C.)"
    ),
    "a4d2ccb3439e479ab512011d7a912dce": (
        "Duró siete siglos, desde la llegada en el siglo II a. C. hasta la caída del Imperio en el siglo V d. C.\n\n"
        "Dominación romana en la Península\n"
        "├── Duración: 7 siglos\n"
        "├── Inicio: siglo II a. C. (218 a. C., II Guerra Púnica)\n"
        "└── Fin: siglo V d. C. (caída del Imperio romano)"
    ),
    "78395cf153c541a1a2372afff8f6cba2": (
        "Supuso el fin de la hegemonía púnica y el inicio de la romanización europea.\n\n"
        "Consecuencias de la caída de Cartago\n"
        "├── Fin: término del predominio africano en el Mediterráneo\n"
        "└── Inicio: comienzo de la romanización de Europa"
    ),
    "8eeebea37fd940f0a099759eab0942f9": (
        "Ocupación militar de dos siglos, larga y penosa (Pompeyo y Julio César), con fuerte resistencia indígena hasta Augusto (38 a. C.).\n\n"
        "Conquista romana de Hispania\n"
        "├── Duración: dos siglos (larga y penosa)\n"
        "├── Guerras civiles: pugnas entre Pompeyo y Julio César\n"
        "├── Resistencia indígena:\n"
        "│   ├── Lusitanos (Viriato)\n"
        "│   ├── Celtíberos (Numancia)\n"
        "│   └── Cántabros y astures\n"
        "└── Hito final: 38 a. C. (Augusto integra Hispania en el Imperio)"
    ),
    "b4ea23f0ccb44956911694d4b33d4201": (
        "Los cartagineses perdieron la guerra y después invadieron Iberia (tras perder Córcega y Cerdeña). Las colonias griegas de la Península pidieron ayuda a Roma.\n\n"
        "I Guerra Púnica (264–241 a. C.)\n"
        "├── Derrota de Cartago: pierde la guerra y los territorios de Córcega y Cerdeña\n"
        "├── Invasión de Iberia: Cartago invade la Península tras la derrota\n"
        "└── Reacción griega: las colonias griegas de la Península piden ayuda a Roma"
    ),
    "ea8fbcda08be45b88ea2baa04c634dd4": (
        "Los romanos lucharon contra los cartagineses dentro de la Península; por eso conquistaron la Península. Roma envió a los Escipiones, que entraron por Ampurias y terminaron por derrotar a Aníbal en África. Los íberos, que antes eran aliados de Cartago, pasaron a ser aliados de Roma.\n\n"
        "II Guerra Púnica (218–201 a. C.) — Clave de la conquista\n"
        "├── Clave de la conquista: luchan dentro de la Península → por eso conquistan la Península\n"
        "├── Llegada: Roma envía a los Escipiones (desembarco por Ampurias, colonia griega aliada)\n"
        "├── Desenlace militar: derrotan finalmente a Aníbal en África (Zama)\n"
        "└── Cambio de alianzas: los íberos (antes aliados de Cartago) pasan a ser aliados de Roma"
    ),

    # 03 Organización Romana y Provincias
    "f006ac7478c84452ad0b22e516e081be": (
        "El Ius Latii otorgaba derechos civiles como paso previo a la ciudadanía completa.\n\n"
        "Ius Latii y Ciudadanía en Hispania\n"
        "├── Concepto: derecho latino (leyes especiales y derechos previos a la ciudadanía)\n"
        "├── Ius Latii: otorgado por Vespasiano (siglo I d. C.)\n"
        "└── Ciudadanía romana: otorgada por Caracalla (siglo III d. C., 212)"
    ),
    "482af4f0f9ad48738bff92ac1aa45c3b": (
        "Coexistieron la organización romana y los sistemas indígenas bajo el derecho romano.\n\n"
        "Organización inicial de Roma\n"
        "├── Sistemas coexistentes:\n"
        "│   ├── Sistemas políticos indígenas\n"
        "│   └── Organización militar y política romana\n"
        "├── Objetivos:\n"
        "│   ├── Garantizar la autoridad de Roma\n"
        "│   └── Asegurar los privilegios de los ciudadanos romanos\n"
        "└── Sustento: el derecho romano"
    ),
    "939e477a343c4a5b8e50d1bf08ab2026": (
        "La administración provincial reconocía las regiones naturales y la identidad de cada grupo.\n\n"
        "Provincias romanas en Hispania\n"
        "├── Provincias principales:\n"
        "│   ├── Tarraconense\n"
        "│   ├── Lusitana\n"
        "│   └── Bética\n"
        "├── Divisiones posteriores:\n"
        "│   ├── Galaica (Caracalla)\n"
        "│   ├── Cartaginense y Mauritana (Diocleciano)\n"
        "│   └── Baleárica\n"
        "└── Criterio: adaptadas a regiones naturales e identidades locales"
    ),

    # 04 Romanización de la Península
    "29581328b65a4deba62bbc1c95b6788e": (
        "La romanización articuló una unidad común sobre la fragmentación previa.\n\n"
        "Romanización vs. Atomismo\n"
        "├── Romanización: proceso formativo de unidad social, política y cultural\n"
        "└── Atomismo: estado previo de división (colonizadores y tribus aisladas)"
    ),
    "2e5c67d04ef74cefaa0d1fe90a2df86f": (
        "Las principales lenguas romances peninsulares.\n\n"
        "Lenguas peninsulares derivadas del latín\n"
        "├── Castellano\n"
        "├── Catalán\n"
        "└── Gallego"
    ),
    "65f39cfbedee444785da1092e3e85906": (
        "Cuatro emperadores romanos tuvieron origen hispánico.\n\n"
        "Emperadores romanos de Hispania\n"
        "├── Adriano\n"
        "├── Trajano\n"
        "├── Marco Aurelio\n"
        "└── Teodosio"
    ),
    "f7a08ee9cdba4135b6e116d929b42ba3": (
        "Sí; la nación es un concepto político alcanzado en el siglo V que integró la diversidad.\n\n"
        "Concepto político de nación\n"
        "├── Naturaleza: concepto político de unidad institucional bajo Roma\n"
        "├── Ritmo dispar: cada pueblo asimiló la cultura a diferente velocidad\n"
        "├── Diversidad interna: convivencia de grupos y tradiciones heterogéneas\n"
        "└── Culminación: Hispania unificada en el siglo V antes de la caída"
    ),

    # 05 Cultura y Arte Romano
    "0bde8a49084344f4a03af99aefc8cbd6": (
        "Artes decorativas muy coloridas que combinaban patrones decorativos y temas mitológicos.\n\n"
        "Mosaicos romanos de Hispania\n"
        "├── Características: arte decorativo muy vistoso y colorido\n"
        "├── Motivos:\n"
        "│   ├── Geométricos y florales\n"
        "│   └── Figuras humanas y animales\n"
        "└── Escenas mitológicas: ej. Ceres, Medusa"
    ),
    "11e089847e574fea9ddc1aaf4c58bd85": (
        "La vida económica y cultural giraba en torno a ciudades construidas para hacer la vida agradable.\n\n"
        "Carácter urbano romano\n"
        "├── Centro neurálgico: la vida social y económica gira en torno a la ciudad\n"
        "├── Finalidad: hacer la vida agradable (otium y servicios cívicos)\n"
        "└── Infraestructuras de ocio y cohesión:\n"
        "    ├── Teatros y circos (ej. Mérida)\n"
        "    └── Vías de comunicación (ej. Vía Augusta)"
    ),
    "91e72d96dfdd43bc90c190389f1c2aac": (
        "Busto del emperador Augusto\n"
        "├── Qué es: busto romano del siglo I d. C.\n"
        "├── Dónde: Mérida\n"
        "├── Qué vemos: retrato muy realista, con la toga\n"
        "└── Qué significa: la toga lo presenta como emperador y pontífice"
    ),
    "5636b59e07854564b28c897de7471f6b": (
        "Tres grandes literatos y pensadores hispanorromanos.\n\n"
        "Autores hispanorromanos\n"
        "├── Lucano: Farsalia (poema épico de la guerra entre Pompeyo y César)\n"
        "├── Marcial: Epigramas (poesía satírica de costumbres)\n"
        "└── Quintiliano: maestro de retórica y formación del orador"
    ),
    "2e3efacfd45f4589815291eb4a7c1716": (
        "Arco de Bará\n"
        "├── Qué es: arco triunfal romano\n"
        "├── Dónde: Tarragona (junto a la Vía Augusta)\n"
        "├── Qué vemos: arco monumental de piedra\n"
        "└── Qué significa: conmemora las glorias de los emperadores"
    ),
    "297d233033f54368a67575a5fc46b8ea": (
        "Venus de Itálica\n"
        "├── Qué es: copia de un ejemplar griego clásico\n"
        "├── Dónde y cuándo: Itálica (Sevilla), hacia el siglo I a. C.\n"
        "├── Qué vemos: desnudo idealizado de gran perfección técnica\n"
        "└── Qué significa: primacía de la técnica sobre la capacidad creadora original"
    ),
    "fbad0f6e28484056bab8434da8087e10": (
        "Séneca fue un filósofo cordobés clave en la difusión del estoicismo clásico.\n\n"
        "Séneca y el estoicismo\n"
        "├── Biografía: nacido en Córdoba; autor de obras filosóficas y literarias\n"
        "├── Filosofía estoica: la conciencia del individuo es la norma de toda virtud\n"
        "└── Trascendencia: enorme prestigio e influencia en la Edad Media y el Renacimiento"
    ),
    "4e3ad47ac62b4f708374a828862ea415": (
        "Teatro romano de Mérida\n"
        "├── Qué es: el teatro romano mejor conservado de España\n"
        "├── Cuándo: siglo I a. C.\n"
        "├── Qué vemos: graderío para 5.000 espectadores y escena (proscenio)\n"
        "└── Qué significa: manifestación del carácter urbano; hacían la vida agradable"
    ),

    # 06 Religión de Roma y Primer Cristianismo
    "37f7be0902e843b2bf67da9be960c2a5": (
        "Planteaba una doble amenaza al orden divino y social de Roma, motivando 300 años de persecuciones.\n\n"
        "Cristianismo como amenaza inicial\n"
        "├── Amenaza política: negaba el carácter divino del emperador\n"
        "├── Amenaza social: defendía la igualdad de todos frente a las jerarquías\n"
        "└── Reacción del Imperio: persecuciones durante 300 años"
    ),
    "679f0e3b08a3405d891a2378cdaa91a7": (
        "La religión romana clásica integraba cuatro elementos complementarios.\n\n"
        "Cuatro elementos de la religión romana\n"
        "├── 1. Mitología griega\n"
        "├── 2. Culto al emperador\n"
        "├── 3. Animismo naturista\n"
        "└── 4. Abstracción de conceptos sociales o políticos (ej. juventud)"
    ),
    "ebcec56db28e423ab2f9bcbe4c7960bc": (
        "Tolerancia general sujeta a dos límites políticos y morales infranqueables.\n\n"
        "Actitud de Roma con religiones indígenas\n"
        "├── Principio general: tolerancia religiosa\n"
        "└── Dos límites estrictos:\n"
        "    ├── Prohibición expresa de sacrificios humanos\n"
        "    └── Persecución de grupos hostiles al Estado (separatismo o ataques al emperador)"
    ),
    "fd522e37a70c48bfba2c188862ca5bde": (
        "Promulgó el Edicto de Milán en el 313 d. C. (siglo IV), transformando las relaciones con la Iglesia.\n\n"
        "Edicto de Milán (313 d. C., Constantino)\n"
        "├── Libertad religiosa: garantía de libertad de culto\n"
        "├── Fin de persecuciones: cese definitivo de la hostilidad estatal\n"
        "└── Alianza institucional: aproximación entre la Iglesia y el Imperio"
    ),
    "1c569b9e640a411ebd217ab28745432c": (
        "Asimiló las instituciones y la cultura organizativa del Imperio romano.\n\n"
        "Romanización del cristianismo (ss. II–III)\n"
        "├── Estructura institucional: adopción del derecho romano y jerarquías\n"
        "├── Centro neurálgico: Roma se erige en centro espiritual\n"
        "└── Síntesis cultural: interpretación cristiana del ideal civilizatorio romano"
    ),
    "70c1fc15fd384cff9ba4c00c7bfe9561": (
        "Ofrecía solidez ética y orden institucional percibidos como la salvación de la civilización.\n\n"
        "Adopción del cristianismo en todas las clases\n"
        "├── Principios morales: ética clara y universal para la vida cotidiana\n"
        "├── Respeto al orden: conservaba las jerarquías sociales existentes\n"
        "├── Doctrina política: formuló una visión del Estado integradora\n"
        "└── Misión histórica: promesa de salvar el Imperio y la civilización romana"
    ),
    "2c77f555dc524fd98b0d54643a48af95": (
        "Estableció el cristianismo como religión oficial y a su muerte el Imperio se fracturó.\n\n"
        "Teodosio (siglo IV)\n"
        "├── Imposición del cristianismo oficial:\n"
        "│   ├── Cristianización del Estado y del derecho\n"
        "│   ├── Cristianización del arte y la literatura\n"
        "│   └── Cristianización de la filosofía (Padres de la Iglesia)\n"
        "└── A su muerte: división definitiva del Imperio (Oriente y Occidente)"
    ),

    # 07 Cristianización de Hispania y Cultura Cristiana
    "9b473437d37c4cedb0b9db7cb61fa5d0": (
        "Porque constituyó la única institución que pervivió a la caída del Imperio.\n\n"
        "Importancia de la Iglesia en Europa\n"
        "├── Supervivencia: única institución que sobrevivió a la caída del Imperio romano\n"
        "└── Legado cultural: puente de transmisión del derecho, el latín y la cultura clásica"
    ),
    "28cbe07bcf9a48169bdf8a2b492a9638": (
        "Adaptó los modelos espaciales romanos para el nuevo culto.\n\n"
        "Arquitectura cristiana primitiva\n"
        "├── Modelo base: la basílica civil romana\n"
        "└── Transformación: adaptada a la liturgia, asamblea y culto cristiano"
    ),
    "cfd7be5d4c514b1a97c3d89139df28e1": (
        "Proceso temprano y tenaz con persecuciones y un fuerte impacto legal y social.\n\n"
        "Cristianización de la Península\n"
        "├── Expansión temprana: llegada de la fe (tradición del Apóstol Santiago)\n"
        "├── Persecuciones: superó una dura resistencia y violencia inicial\n"
        "├── Humanización legal: atemperó la aplicación del derecho romano\n"
        "└── Inclusión social: promovió mayor integración de la población hispana"
    ),
    "640a591ebd67450ca0bc842425aa8a16": (
        "El poeta lírico más relevante del cristianismo hispánico.\n\n"
        "Aurelio Prudencio\n"
        "├── Perfil: el mejor poeta cristiano de Hispania\n"
        "└── Trascendencia litúrgica: sus himnos continúan cantándose en la liturgia católica"
    ),
    "eb07b7c793b44400b364af7f294a1f6b": (
        "Decayó por cautela ante la idolatría pagana, evolucionando hacia un arte más espiritual.\n\n"
        "Escultura cristiana primitiva\n"
        "├── Decadencia: temor a la idolatría y culto a estatuas paganas\n"
        "├── Estética: más tosca, rígida y hierática\n"
        "└── Contenido: intensificación del misticismo y simbolismo religioso"
    ),
}


def migrate(db_path: Path, dry_run: bool = False):
    sys.stdout.reconfigure(encoding="utf-8")
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    updated_count = 0
    missing_notes = []

    for note_id, new_back in UPDATES.items():
        cursor.execute("SELECT field_values FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            missing_notes.append(note_id)
            continue

        field_values = json.loads(row[0]) if row[0] else {}
        field_values["Back"] = new_back
        updated_json = json.dumps(field_values, ensure_ascii=False)

        cursor.execute(
            """
            SELECT c.id, d.name, json_extract(n.field_values, '$.Front')
            FROM cards c
            JOIN decks d ON c.deck_id = d.id
            JOIN notes n ON c.note_id = n.id
            WHERE n.id = ?
            """,
            (note_id,),
        )
        card_info = cursor.fetchone()
        card_id = card_info[0] if card_info else "unknown"
        deck_name = card_info[1] if card_info else "unknown"
        front_q = card_info[2] if card_info else ""

        print(f"[{'DRY-RUN' if dry_run else 'UPDATING'}] Note: {note_id} | Card: {card_id}")
        print(f"  Deck: {deck_name}")
        print(f"  Q: {front_q[:70]}...")

        if not dry_run:
            cursor.execute(
                "UPDATE notes SET field_values = ? WHERE id = ?",
                (updated_json, note_id),
            )
        updated_count += 1

    if not dry_run:
        conn.commit()

    conn.close()

    print("\n" + "=" * 60)
    print(f"Total updates targeted: {len(UPDATES)}")
    print(f"Total notes updated: {updated_count}")
    if missing_notes:
        print(f"WARNING: {len(missing_notes)} notes were not found: {missing_notes}")
    else:
        print("All targeted notes successfully verified and updated!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SPAN 321 card answers to tree format.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying DB.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="Path to dev.db")
    args = parser.parse_args()

    migrate(args.db_path, dry_run=args.dry_run)
