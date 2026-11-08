"""Script to generate the complete, canonical 49-card dataset for SPAN 321 (Parte II).
Integrates Marisol's exact answers, proper nouns, slide citations, and structured ASCII trees.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / "span321_49_questions.json"

CARDS = [
    # =========================================================================
    # SECTION 07: Roma y Cartago (Q1 - Q8)
    # =========================================================================
    {
        "num": 1,
        "section": "07 Roma y Cartago",
        "star": False,
        "front": "¿Cuánto duró la dominación de Roma en la Península? [Guía 1; T2 4]",
        "back": (
            "Duró siete siglos, del siglo II a. C. al siglo V d. C. Terminó cuando cayó el Imperio romano.\n\n"
            "Dominación romana en la Península\n"
            "├── Duración: 7 siglos\n"
            "├── Inicio: siglo II a. C. (218 a. C., II Guerra Púnica)\n"
            "└── Fin: siglo V d. C. (caída del Imperio romano)"
        ),
        "image": None
    },
    {
        "num": 2,
        "section": "07 Roma y Cartago",
        "star": True,
        "front": "★ ¿Por qué se dice que con los romanos comienza la historia de España como nación? [Guía 1; T2 4]",
        "back": (
            "Porque los pueblos peninsulares dejan de ser unidades fragmentadas. Se unen bajo idénticos intereses políticos y económicos, los de Roma, y además ganan una **unidad cultural**.\n\n"
            "España como nación con Roma\n"
            "├── Situación previa: atomismo (tribus fragmentadas e independientes)\n"
            "├── Integración romana:\n"
            "│   ├── Unidad política y territorial (provincias)\n"
            "│   ├── Unidad jurídica (derecho romano)\n"
            "│   └── Unidad cultural y lingüística (el latín)\n"
            "└── Resultado: nacimiento de una conciencia e identidad común en el s. V"
        ),
        "image": None
    },
    {
        "num": 3,
        "section": "07 Roma y Cartago",
        "star": False,
        "front": "¿Cuál fue la causa de la llegada de los romanos a Iberia? [Guía 1; T2 4]",
        "back": (
            "Las **Guerras Púnicas**: la confrontación entre Roma y Cartago por el dominio comercial en el mar Mediterráneo, entre los siglos III y II a. C. Roma no vino por interés directo en Iberia, sino para frenar la expansión cartaginesa.\n\n"
            "Causa de la llegada de Roma\n"
            "├── Conflicto central: Guerras Púnicas (Roma vs. Cartago)\n"
            "├── Época: siglos III–II a. C.\n"
            "├── Motivo: disputa por el dominio comercial del Mediterráneo\n"
            "└── Objetivo inicial: frenar el avance cartaginés y cortar suministros"
        ),
        "image": None
    },
    {
        "num": 4,
        "section": "07 Roma y Cartago",
        "star": False,
        "front": "Da las fechas de las tres Guerras Púnicas. [Guía 1; T2 4]",
        "back": (
            "En conjunto, las Guerras Púnicas abarcaron del **264 al 146 a. C.**:\n\n"
            "• **I Guerra Púnica (264–241 a. C.):** Roma derrota a Cartago en el mar; Cartago pierde Sicilia, Córcega y Cerdeña.\n"
            "• **II Guerra Púnica (218–201 a. C.):** Los cartagineses invaden la Península; Roma llega en el 218 a. C. para cortar suministros a Aníbal.\n"
            "• **III Guerra Púnica (149–146 a. C.):** Destrucción total y definitiva de Cartago.\n\n"
            "Fechas de las tres Guerras Púnicas (264–146 a. C.)\n"
            "├── I Guerra Púnica (264–241 a. C.): Cartago pierde Sicilia y Cerdeña\n"
            "├── II Guerra Púnica (218–201 a. C.): llegada de Roma a Hispania (218 a. C.)\n"
            "└── III Guerra Púnica (149–146 a. C.): destrucción definitiva de Cartago"
        ),
        "image": None
    },
    {
        "num": 5,
        "section": "07 Roma y Cartago",
        "star": False,
        "front": "¿Qué pasó después de la I Guerra Púnica? [Guía 1; T2 4]",
        "back": (
            "Los cartagineses perdieron la guerra y después **invadieron Iberia** (para compensar las pérdidas de Sicilia y Cerdeña y obtener recursos y soldados). Las colonias griegas de la Península pidieron ayuda a Roma.\n\n"
            "> **Aviso de fuentes:** La guía de Marisol aclara que Cartago invadió Iberia tras perder la I Guerra Púnica y los territorios de Córcega y Cerdeña. Usa siempre la versión de la guía.\n\n"
            "Consecuencias de la I Guerra Púnica\n"
            "├── Derrota de Cartago: pérdida de Sicilia, Córcega y Cerdeña\n"
            "├── Invasión de Iberia: Cartago avanza hacia la Península para buscar recursos\n"
            "└── Petición de auxilio: las colonias griegas peninsulares piden ayuda a Roma"
        ),
        "image": None
    },
    {
        "num": 6,
        "section": "07 Roma y Cartago",
        "star": False,
        "front": "¿Qué pasó en la II Guerra Púnica y por qué es la clave de la conquista? [Guía 1; T2 4–5]",
        "back": (
            "Los romanos lucharon contra los cartagineses dentro de la Península. **Por eso conquistaron la Península.**\n\n"
            "Roma envió a **los Escipiones**, que entraron por **Ampurias** (218 a. C.) y terminaron por derrotar a Aníbal en África (batalla de Zama). Los íberos, que antes eran aliados de Cartago, pasaron a ser aliados de Roma.\n\n"
            "II Guerra Púnica (218–201 a. C.) — Clave de la conquista\n"
            "├── Clave: la guerra se libra en suelo ibérico → Roma inicia la ocupación permanente\n"
            "├── Generales: los Escipiones desembarcan en Ampurias (218 a. C.)\n"
            "├── Victoria final: derrota de Aníbal en Zama (África, 202 a. C.)\n"
            "└── Giro político: las tribus íberas cambian de bando y se alían con Roma"
        ),
        "image": None
    },
    {
        "num": 7,
        "section": "07 Roma y Cartago",
        "star": False,
        "front": "¿Por qué entraron los romanos por Ampurias? [Guía 1; T1 96]",
        "back": (
            "Porque las colonias griegas habían pedido ayuda a Roma, y **Ampurias era una colonia griega aliada de Roma** contra los cartagineses.\n\n"
            "Entrada por Ampurias (218 a. C.)\n"
            "├── Punto de entrada: Ampurias (costa catalana)\n"
            "├── Naturaleza: colonia griega aliada de Roma\n"
            "└── Causa: llamada de auxilio de los griegos frente a la expansión cartaginesa"
        ),
        "image": None
    },
    {
        "num": 8,
        "section": "07 Roma y Cartago",
        "star": True,
        "front": "★ ¿Qué supuso la caída de Cartago? [Guía 1; T2 4]",
        "back": (
            "Supuso **el fin del predominio africano en el Mediterráneo** y **el comienzo de la romanización de Europa**.\n\n"
            "Trascendencia de la caída de Cartago\n"
            "├── Fin: término de la hegemonía y predominio africano/púnico en el Mediterráneo\n"
            "└── Comienzo: inicio de la integración y romanización de Europa occidental"
        ),
        "image": None
    },

    # =========================================================================
    # SECTION 08: La Conquista Romana de la Península (Q9 - Q11)
    # =========================================================================
    {
        "num": 9,
        "section": "08 La Conquista Romana",
        "star": False,
        "front": "¿Qué fue la conquista y cuánto duró? [Guía 2; T2 5–7]",
        "back": (
            "Fue la **ocupación y dominación** de los pueblos de la Península. **Duró dos siglos** (del 218 al 19 a. C.). Fue larga y penosa: alternaron períodos de paz y de guerra, especialmente en la época de Pompeyo y Julio César.\n\n"
            "La conquista romana de Hispania\n"
            "├── Naturaleza: proceso militar de ocupación, sumisión y dominación territorial\n"
            "├── Duración: dos siglos completos (218 a. C. a 19 a. C.)\n"
            "├── Carácter: larga y penosa (guerras de desgaste y fases de pacificación)\n"
            "└── Contexto: repercusión de las guerras civiles romanas (Pompeyo y César)"
        ),
        "image": None
    },
    {
        "num": 10,
        "section": "08 La Conquista Romana",
        "star": False,
        "front": "¿Qué pueblos opusieron resistencia y cómo? [Guía 2; T2 6]",
        "back": (
            "Tres pueblos principales opusieron una tenaz resistencia a Roma:\n\n"
            "1. **Los lusitanos:** dirigidos por **Viriato** (un pastor), mediante la táctica de **guerrillas**.\n"
            "2. **Los celtíberos:** con la heroica resistencia en el **asedio de Numancia**.\n"
            "3. **Los cántabros y astures:** en las montañas del norte peninsular.\n\n"
            "Resistencia indígena a Roma\n"
            "├── 1. Lusitanos (Viriato): guerra de guerrillas rápida y emboscadas\n"
            "├── 2. Celtíberos (Numancia): resistencia numantina y asedio total\n"
            "└── 3. Cántabros y astures: resistencia en las montañas del norte"
        ),
        "image": None
    },
    {
        "num": 11,
        "section": "08 La Conquista Romana",
        "star": False,
        "front": "¿Cuándo pasó Hispania a formar parte del Imperio romano? [Guía 2; T2 5, 7]",
        "back": (
            "En el año **19 a. C.** (o 38 a. C. según el inicio de la era hispánica en el PPT), cuando el emperador **Augusto** sometió a cántabros y astures en el norte e integró definitivamente a Hispania en la **Pax Romana** del Imperio.\n\n"
            "Integración de Hispania en el Imperio\n"
            "├── Fecha culminante: 19 a. C. (fin de las Guerras Cántabras)\n"
            "├── Protagonista: el emperador César Augusto\n"
            "└── Resultado: pacificación total y plena incorporación a la Pax Romana"
        ),
        "image": None
    },

    # =========================================================================
    # SECTION 09: La Organización Romana de la Península (Q12 - Q22)
    # =========================================================================
    {
        "num": 12,
        "section": "09 La Organización Romana",
        "star": False,
        "front": "¿Qué sistemas coexistieron desde el inicio y con qué objetivos? [Guía 2; T2 8]",
        "back": (
            "Coexistieron **los sistemas políticos indígenas** y **la organización militar y política de Roma**.\n\n"
            "Sus objetivos eran dos:\n"
            "1. Garantizar la autoridad suprema de Roma.\n"
            "2. Asegurar los privilegios de los ciudadanos romanos.\n\n"
            "Organización inicial de Roma\n"
            "├── Sistemas coexistentes:\n"
            "│   ├── Sistemas políticos consuetudinarios indígenas\n"
            "│   └── Estructura militar y administrativa romana\n"
            "└── Objetivos dobles:\n"
            "    ├── Consolidar la hegemonía y control del Estado romano\n"
            "    └── Preservar los privilegios jurídicos de los ciudadanos romanos"
        ),
        "image": None
    },
    {
        "num": 13,
        "section": "09 La Organización Romana",
        "star": True,
        "front": "★ ¿Qué es el derecho romano y por qué es la mayor contribución de Roma a la civilización occidental? [Guía 2; T2 8]",
        "back": (
            "Es el sistema legal que organiza las relaciones de los individuos entre sí y entre el gobierno y los individuos. Su fundamento es **el individuo**, frente al colectivismo social de las tribus primitivas.\n\n"
            "Es la mayor contribución porque **reconoce libertades básicas** que no dependen de la pertenencia a una tribu o raza (como el derecho a la propiedad) y se aplicó a todos los pueblos sometidos a Roma.\n\n"
            "Trascendencia del Derecho Romano\n"
            "├── Definición: ordenamiento que regula relaciones privadas y públicas\n"
            "├── Fundamento: el individuo (supera el colectivismo tribal cerrado)\n"
            "├── Aportación clave: libertades civiles y derechos de propiedad universales\n"
            "└── Alcance: aplicación uniforme a todas las comunidades del Imperio"
        ),
        "image": None
    },
    {
        "num": 14,
        "section": "09 La Organización Romana",
        "star": False,
        "front": "¿Qué es el paterfamilias? [Guía 2; T2 8]",
        "back": (
            "Es la **persona jurídica fundamental** del derecho romano: el cabeza de familia, que tenía autoridad legal total sobre su familia y sus posesiones.\n\n"
            "El Paterfamilias\n"
            "├── Concepto: eje y pilar jurídico fundamental de la sociedad romana\n"
            "├── Posición: cabeza supremo de la unidad familiar (patria potestas)\n"
            "└── Atribuciones: control legal y patrimonial sobre bienes y dependientes"
        ),
        "image": None
    },
    {
        "num": 15,
        "section": "09 La Organización Romana",
        "star": False,
        "front": "¿Qué clases sociales había en los territorios conquistados? [Guía 2; T2 8]",
        "back": (
            "Había tres grandes estamentos o clases sociales:\n\n"
            "1. **Libres:** se dividían en ciudadanos romanos (plenos derechos) y latinos (derechos civiles, sin voto político directo).\n"
            "2. **Semilibres:** los colonos agrícolas vinculados a la tierra.\n"
            "3. **Esclavos:** sin derechos legales ni personalidad jurídica.\n\n"
            "Estructura social en la Hispania romana\n"
            "├── 1. Libres:\n"
            "│   ├── Ciudadanos romanos (plenitud de derechos políticos y civiles)\n"
            "│   └── Latinos (gozan de Ius Latii, derechos civiles patrimoniales)\n"
            "├── 2. Semilibres: colonos adscritos al cultivo de latifundios\n"
            "└── 3. Esclavos: mano de obra sin derechos jurídicos"
        ),
        "image": None
    },
    {
        "num": 16,
        "section": "09 La Organización Romana",
        "star": True,
        "front": "★ ¿Qué era el Ius Latii y a quién se aplicaba? [Guía 2; T2 9–10]",
        "back": (
            "Era el **derecho latino**: un conjunto de leyes especiales y derechos civiles concedidos a pueblos y ciudades fuera de Italia. Se aplicaba a las personas de condición «latina», que no tenían la ciudadanía romana completa pero sí derechos contractuales y de matrimonio.\n\n"
            "El Ius Latii (Derecho Latino)\n"
            "├── Naturaleza: estatus jurídico intermedio previo a la ciudadanía plena\n"
            "├── Derechos conferidos: derechos comerciales, contractuales y matrimoniales\n"
            "├── Exclusión: sin derechos políticos en la asamblea de Roma\n"
            "└── Destinatarios: poblaciones provinciales leales al Imperio"
        ),
        "image": None
    },
    {
        "num": 17,
        "section": "09 La Organización Romana",
        "star": False,
        "front": "¿Cuándo recibió Hispania el Ius Latii y cuándo la ciudadanía romana? [Guía 2; T2 9–10]",
        "back": (
            "• **Ius Latii:** en el siglo I d. C. (74 d. C.), otorgado por el emperador **Vespasiano** a toda Hispania.\n"
            "• **Ciudadanía romana:** en el siglo III d. C. (**212 d. C.**), otorgada por el emperador **Caracalla** (mediante la *Constitutio Antoniniana*) a todos los habitantes libres del Imperio.\n\n"
            "Cronología de derechos en Hispania\n"
            "├── Siglo I d. C. (74 d. C.): Vespasiano concede el Ius Latii general\n"
            "└── Siglo III d. C. (212 d. C.): Caracalla extiende la ciudadanía universal"
        ),
        "image": None
    },
    {
        "num": 18,
        "section": "09 La Organización Romana",
        "star": False,
        "front": "¿En qué se diferenciaban las colonias romanas de las ciudades indígenas? [Guía 2; T2 9–10]",
        "back": (
            "• **Las colonias:** eran ciudades nuevas o refundadas por Roma, pobladas por ciudadanos romanos (como soldados licenciados tras 30 años de servicio en las legiones).\n"
            "• **Las ciudades indígenas (municipios):** eran ciudades que ya existían antes de la llegada de Roma. Si se aliaban con Roma y adoptaban el derecho latino, se convertían en **municipios** con leyes propias y autonomía.\n\n"
            "Colonias vs. Ciudades Indígenas\n"
            "├── Colonias romanas: de nueva planta, pobladas por legionarios veteranos\n"
            "└── Ciudades indígenas (municipios): preexistentes, aliadas, conservan fueros locales"
        ),
        "image": None
    },
    {
        "num": 19,
        "section": "09 La Organización Romana",
        "star": True,
        "front": "★ ¿Por qué son importantes los municipios? [Guía 2; T2 10]",
        "back": (
            "Porque eran ciudades aliadas que gozaban de **leyes propias** y **gran arraigo popular**. Fueron el vehículo principal de la romanización: a través de ellos los hispanos adoptaron la vida urbana, las instituciones y la cultura romanas de forma voluntaria.\n\n"
            "Importancia de los Municipios\n"
            "├── Autonomía: mantenimiento de asambleas y magistraturas locales propias\n"
            "├── Arraigo popular: vinculación orgánica con las costumbres de los nativos\n"
            "└── Motor de romanización: integración pacífica y asimilación cívica"
        ),
        "image": None
    },
    {
        "num": 20,
        "section": "09 La Organización Romana",
        "star": True,
        "front": "★ ¿Qué provincias romanas había en Hispania? [Guía 2; T2 11]\n\n![](/media/span321_mapa_provincias.jpg)",
        "back": (
            "El número varió con el tiempo. Las tres principales (con Augusto) fueron:\n\n"
            "1. **Tarraconense** (norte y levante).\n"
            "2. **Lusitana** (oeste, actual Portugal y Extremadura).\n"
            "3. **Bética** (sur, valle del Guadalquivir).\n\n"
            "Más tarde se añadieron la **Galaica** (con Caracalla, s. III), la **Cartaginense** y la **Mauritana Tingitana** (con Diocleciano, s. IV), y la **Baleárica**.\n\n"
            "Evolución de las provincias de Hispania\n"
            "├── 1. División augustea (s. I a. C.):\n"
            "│   ├── Tarraconense\n"
            "│   ├── Lusitana\n"
            "│   └── Bética\n"
            "└── 2. Ampliaciones tardías:\n"
            "    ├── Galaica (Caracalla, s. III)\n"
            "    ├── Cartaginense y Mauritana (Diocleciano, s. IV)\n"
            "    └── Baleárica"
        ),
        "image": "/media/span321_mapa_provincias.jpg"
    },
    {
        "num": 21,
        "section": "09 La Organización Romana",
        "star": True,
        "front": "★ ¿Qué tendían a reconocer las divisiones provinciales? [Guía 2; T2 11]",
        "back": (
            "Tendían a reconocer **las regiones naturales** y **la personalidad y costumbres de los pueblos** de cada zona, respetando las características geográficas y las identidades locales previas.\n\n"
            "Criterio de las divisiones provinciales\n"
            "├── Regiones naturales: adaptación a cuencas fluviales y barreras geográficas\n"
            "└── Identidad cultural: reconocimiento tácito de la personalidad de cada pueblo"
        ),
        "image": None
    },
    {
        "num": 22,
        "section": "09 La Organización Romana",
        "star": False,
        "front": "¿Es la provincia romana lo mismo que la provincia moderna? [Guía 2; T2 11; Intro 24–25]",
        "back": (
            "**No.** La provincia romana era una gran demarcación territorial del Imperio con fines militares, tributarios y de administración general. La provincia moderna surge en el **siglo XIX** (entre 1812 y la división de Javier de Burgos en **1833**) como subdivisión administrativa uniforme y centralizada del Estado liberal español.\n\n"
            "Provincia romana vs. Provincia moderna\n"
            "├── Provincia romana: división imperial inmensa para control militar y tributos\n"
            "└── Provincia moderna: división civil uniforme surgida en el s. XIX (1833)"
        ),
        "image": None
    },

    # =========================================================================
    # SECTION 10: La Romanización de la Península (Q23 - Q28)
    # =========================================================================
    {
        "num": 23,
        "section": "10 La Romanización",
        "star": False,
        "front": "¿Qué es la romanización? [Guía 2; T2 12]",
        "back": (
            "Es el proceso histórico mediante el cual los pueblos peninsulares asumieron la cultura, lengua, leyes, religión y modos de vida de Roma, formándose poco a poco una **unidad social, política y cultural** frente al **atomismo** previo de los pueblos indígenas.\n\n"
            "Concepto de Romanización\n"
            "├── Definición: asimilación gradual del modo de vida y civilización romana\n"
            "├── Factores clave: latín, derecho romano, urbanización y calzadas\n"
            "└── Efecto primordial: superación del atomismo tribal indígena"
        ),
        "image": None
    },
    {
        "num": 24,
        "section": "10 La Romanización",
        "star": True,
        "front": "★ ¿Cómo era Hispania en el siglo V, cuando cae el Imperio? [Guía 2; T2 12]",
        "back": (
            "Era una **Hispania plenamente unificada** por el concepto político de **nación hispánica**, aunque internamente estuviera formada por grupos sociales y étnicos diversos. El latín y el derecho habían calado hondamente en toda la población peninsular.\n\n"
            "Hispania en el siglo V d. C.\n"
            "├── Estatus político: entidad cohesionada bajo el concepto de nación hispana\n"
            "├── Base cultural: latinización y asimilación jurídica consolidada\n"
            "└── Estructura social: convivencia integradora de diversos orígenes étnicos"
        ),
        "image": None
    },
    {
        "num": 25,
        "section": "10 La Romanización",
        "star": False,
        "front": "¿Fue igual la romanización en todos los pueblos? [Guía 2; T2 12]",
        "back": (
            "**No, fue desigual.** El sur (Bética) y el levante (Tarraconense) se romanizaron de manera rápida, intensa y pacífica debido a su contacto comercial previo. En cambio, el interior, el oeste y sobre todo el norte montañoso (cántabros y vascones) tuvieron una romanización mucho más tardía, superficial y dificultosa.\n\n"
            "Ritmo desigual de la romanización\n"
            "├── Sur y Levante (Bética, costa mediterránea): romanización rápida y profunda\n"
            "└── Centro y Norte (montañas cantábricas, cántabros y astures): romanización tardía y débil"
        ),
        "image": None
    },
    {
        "num": 26,
        "section": "10 La Romanización",
        "star": True,
        "front": "★ Si cada pueblo se romanizó a su propio ritmo, ¿se puede hablar de una nación? [Guía 2; T2 12]",
        "back": (
            "**Sí.** Porque el concepto de nación aquí es un **concepto político** de integración y destino común, no una homogeneidad étnica absoluta. Aunque cada pueblo avanzó a diferente velocidad, todos convergieron en el siglo V bajo un mismo marco legal, lingüístico y civilizatorio.\n\n"
            "Nación política en Hispania\n"
            "├── Naturaleza: concepto político institucional, no igualdad étnica rígida\n"
            "├── Proceso: asimilación progresiva a velocidades distintas según la región\n"
            "└── Síntesis: convergencia en una identidad común a finales del Imperio"
        ),
        "image": None
    },
    {
        "num": 27,
        "section": "10 La Romanización",
        "star": False,
        "front": "¿Qué lenguas salieron del latín? [Guía 2; T2 14]",
        "back": (
            "Salieron las principales lenguas romances peninsulares:\n\n"
            "• **Castellano** (español)\n"
            "• **Catalán**\n"
            "• **Gallego**\n\n"
            "> **Nota:** El euskera (vasco) es la única lengua peninsular no romance, de origen prerromano.\n\n"
            "Lenguas romances peninsulares derivadas del latín\n"
            "├── Castellano\n"
            "├── Catalán\n"
            "└── Gallego"
        ),
        "image": None
    },
    {
        "num": 28,
        "section": "10 La Romanización",
        "star": False,
        "front": "¿Qué emperadores nacieron en Hispania? [Guía 2; T2 15]\n\n![](/media/span321_emperadores_hispanos.jpg)",
        "back": (
            "Cuatro emperadores romanos tuvieron origen hispánico:\n\n"
            "1. **Trajano** (nacido en Itálica, cerca de Sevilla)\n"
            "2. **Adriano** (también vinculado a Itálica)\n"
            "3. **Marco Aurelio** (de familia hispana de Córdoba)\n"
            "4. **Teodosio** (nacido en Coca, Segovia)\n\n"
            "Emperadores romanos de origen hispano\n"
            "├── Trajano (Itálica, Sevilla)\n"
            "├── Adriano (Itálica, Sevilla)\n"
            "├── Marco Aurelio (ascendencia hispana, Córdoba)\n"
            "└── Teodosio (Coca, Segovia)"
        ),
        "image": "/media/span321_emperadores_hispanos.jpg"
    },

    # =========================================================================
    # SECTION 11: Cultura y Arte (Q29 - Q36)
    # =========================================================================
    {
        "num": 29,
        "section": "11 Cultura y Arte Romano",
        "star": True,
        "front": "★ ¿Qué quiere decir que la cultura romana tenía carácter urbano? [Guía 3; T2 16]\n\n![](/media/span321_calzadas_romanas.jpg)",
        "back": (
            "Quiere decir que la vida social, económica, política y cultural **giraba en torno a la ciudad**. Las ciudades se construían no solo para administrar, sino **para hacer la vida agradable** a los ciudadanos, dotándolas de servicios, comodidades (termas, acueductos), ocio (teatros, circos) y conectándolas mediante calzadas como la **Vía Augusta**.\n\n"
            "Carácter urbano de Roma\n"
            "├── Núcleo vital: la ciudad es el centro motor de economía y civilización\n"
            "├── Filosofía cívica: diseño urbano orientado a hacer la vida agradable\n"
            "├── Infraestructuras: termas, teatros, foros, cloacas y acueductos\n"
            "└── Cohesión territorial: red de comunicaciones y calzadas (ej. Vía Augusta)"
        ),
        "image": "/media/span321_calzadas_romanas.jpg"
    },
    {
        "num": 30,
        "section": "11 Cultura y Arte Romano",
        "star": False,
        "front": "¿Para qué servían los arcos triunfales? Da un ejemplo. [Guía 3; T2 17]\n\n![](/media/span321_arco_bara.jpg)",
        "back": (
            "Servían para **conmemorar las glorias de los emperadores** y recordar el poder de Roma a los viajeros.\n\n"
            "• **Ejemplo:** el **Arco de Bará** (en Tarragona, sobre la Vía Augusta), levantado en el siglo I a. C. en época de Augusto.\n\n"
            "Arcos triunfales romanos\n"
            "├── Función: monumento honorífico que conmemora gestas militares imperiales\n"
            "├── Ubicación típica: vías principales de entrada o calzadas estratégicas\n"
            "└── Ejemplo en Hispania: Arco de Bará (Tarragona, Vía Augusta, s. I a. C.)"
        ),
        "image": "/media/span321_arco_bara.jpg"
    },
    {
        "num": 31,
        "section": "11 Cultura y Arte Romano",
        "star": False,
        "front": "Da un ejemplo de teatro romano en Hispania. [Guía 3; T2 18]\n\n![](/media/span321_teatro_merida.jpg)",
        "back": (
            "El **Teatro romano de Mérida** (Augusta Emerita, Badajoz), construido en el siglo I a. C. bajo el patrocinio del cónsul Agripa. Es el teatro mejor conservado de España, con un graderío semicircular para 5.000 espectadores y un suntuoso frente de escena.\n\n"
            "Teatro romano de Mérida\n"
            "├── Localización y fecha: Mérida (Badajoz), siglo I a. C.\n"
            "├── Promotor: cónsul Marco Vipsanio Agripa\n"
            "├── Arquitectura: cávea semicircular escalonada y proscenio monumental\n"
            "└── Significado: arquetipo de ocio urbano cívico romano"
        ),
        "image": "/media/span321_teatro_merida.jpg"
    },
    {
        "num": 32,
        "section": "11 Cultura y Arte Romano",
        "star": False,
        "front": "¿Cómo eran los bustos romanos? [Guía 3; T2 19]\n\n![](/media/span321_augusto_merida.jpg)",
        "back": (
            "Eran retratos de **gran realismo**, que reproducían fielmente los rasgos individuales, las arrugas y la personalidad del retratado (herencia de la tradición etrusca y republicana). Con el Imperio incorporaron también cierta serenidad e idealización para destacar la dignidad del gobernante (como el **Busto de Augusto** hallado en Mérida).\n\n"
            "Bustos romanos\n"
            "├── Rasgo definitorio: realismo fisonómico minucioso e individualizado\n"
            "├── Evolución imperial: incorporación de serenidad y majestad política\n"
            "└── Ejemplo en Hispania: Busto del emperador Augusto togado (Mérida)"
        ),
        "image": "/media/span321_augusto_merida.jpg"
    },
    {
        "num": 33,
        "section": "11 Cultura y Arte Romano",
        "star": True,
        "front": "★ ¿Qué nos dice la Venus de Itálica sobre la escultura romana? [Guía 3; T2 20]\n\n![](/media/span321_venus_italica.jpg)",
        "back": (
            "Nos dice que la escultura romana se caracterizó por la **copia e imitación de los modelos clásicos griegos**. Muestra una enorme perfección técnica y dominio del mármol, pero refleja la **primacía de la técnica sobre la capacidad creadora original**.\n\n"
            "Venus de Itálica y la escultura romana\n"
            "├── Naturaleza: copia de gran calidad de un arquetipo griego clásico\n"
            "├── Localización: Itálica (Santiponce, Sevilla), siglo I a. C. / d. C.\n"
            "└── Conclusión estética: primacía del virtuosismo técnico sobre la originalidad"
        ),
        "image": "/media/span321_venus_italica.jpg"
    },
    {
        "num": 34,
        "section": "11 Cultura y Arte Romano",
        "star": True,
        "front": "★ ¿Cómo eran los mosaicos romanos de Hispania? [Guía 3; T2 21]\n\n![](/media/span321_mosaicos_medusa_ceres.jpg)",
        "back": (
            "Eran composiciones decorativas muy coloridas y elaboradas mediante **teselas**. Combinaban motivos geométricos y florales con escenas figurativas y narrativas tomadas de la **mitología clásica** (ejemplos destacados: el **Mosaico de Medusa** en Tarragona y el **Mosaico de Ceres** en Mérida).\n\n"
            "Mosaicos romanos en Hispania\n"
            "├── Técnica: empleo de teselas policromadas de piedra y pasta vítrea\n"
            "├── Temas principales:\n"
            "│   ├── Cenefas geométricas y ornatos vegetales\n"
            "│   └── Grandes escenas mitológicas clásicas\n"
            "└── Ejemplos cumbres: Mosaico de Medusa (Tarragona) y Ceres (Mérida)"
        ),
        "image": "/media/span321_mosaicos_medusa_ceres.jpg"
    },
    {
        "num": 35,
        "section": "11 Cultura y Arte Romano",
        "star": True,
        "front": "★ ¿Quién fue Séneca y qué es el estoicismo? [Guía 3; T2 22]",
        "back": (
            "• **Séneca:** filósofo, dramaturgo y político hispanorromano nacido en **Córdoba**, preceptor del emperador Nerón y una de las mentes más brillantes de Roma.\n"
            "• **Estoicismo:** doctrina filosófica que defiende que **la virtud reside en la conciencia del individuo**, en el autodominio de las pasiones y en aceptar el destino con serenidad y entereza moral.\n\n"
            "Séneca y la Filosofía Estoica\n"
            "├── Figura: pensador de Córdoba, máximo exponente del pensamiento hispanorromano\n"
            "├── Doctrina estoica: la conciencia y la razón son la medida de la virtud\n"
            "└── Relevancia: enorme influencia perdurable en el pensamiento cristiano y europeo"
        ),
        "image": None
    },
    {
        "num": 36,
        "section": "11 Cultura y Arte Romano",
        "star": False,
        "front": "¿Quiénes fueron Lucano, Marcial y Quintiliano? [Guía 3; T2 22]",
        "back": (
            "Fueron tres grandes escritores y pensadores nacidos en Hispania que alcanzaron la cima de las letras romanas:\n\n"
            "1. **Lucano** (Córdoba): poeta épico, autor de la *Farsalia* (sobre la guerra civil entre César y Pompeyo).\n"
            "2. **Marcial** (Bílbilis, Calatayud): creador de los *Epigramas* (poemas satíricos agudos y costumbristas).\n"
            "3. **Quintiliano** (Calahorra, La Rioja): célebre maestro de oratoria, autor de la *Institutio Oratoria*.\n\n"
            "Grandes literatos hispanorromanos\n"
            "├── Lucano (Córdoba): poesía épica histórica (*Farsalia*)\n"
            "├── Marcial (Calatayud): poesía satírica e ingenio popular (*Epigramas*)\n"
            "└── Quintiliano (Calahorra): cumbre de la pedagogía y retórica romana"
        ),
        "image": None
    },

    # =========================================================================
    # SECTION 12: La Religión de Roma (Q37 - Q45)
    # =========================================================================
    {
        "num": 37,
        "section": "12 La Religión de Roma",
        "star": False,
        "front": "¿De qué elementos se componía la religión romana? [Guía 4; T2 23]",
        "back": (
            "Se componía de cuatro elementos principales:\n\n"
            "1. **Mitología griega:** dioses antropomórficos adoptados con nombres latinos (Júpiter, Marte, Venus).\n"
            "2. **Culto al emperador:** obligación cívica y política de venerar la figura imperial.\n"
            "3. **Animismo naturista:** culto arcaico a fuerzas de la naturaleza (árboles, ríos, manantiales).\n"
            "4. **Abstracción de conceptos cívicos:** divinización de ideas abstractas (la Concordia, la Fortuna, la Paz, la Juventud).\n\n"
            "Componentes de la religión romana\n"
            "├── 1. Panteón mitológico griego latinizado\n"
            "├── 2. Culto cívico-político al emperador divinizado\n"
            "├── 3. Animismo naturista (espíritus y fuerzas de la tierra)\n"
            "└── 4. Deificación de abstracciones sociales y políticas (Paz, Concordia)"
        ),
        "image": None
    },
    {
        "num": 38,
        "section": "12 La Religión de Roma",
        "star": True,
        "front": "★ ¿Qué actitud tenía Roma con las religiones indígenas? [Guía 4; T2 23]",
        "back": (
            "Roma mantuvo una política general de **tolerancia religiosa**, asimilando dioses locales a su propio panteón. Sin embargo, impuso **dos límites estrictos e infranqueables**:\n\n"
            "1. **Prohibición absoluta de los sacrificios humanos.**\n"
            "2. **Persecución de grupos hostiles al Estado** o que cuestionaran la autoridad del emperador y el orden cívico.\n\n"
            "Actitud religiosa de Roma\n"
            "├── Regla general: amplia tolerancia y sincretismo con cultos autóctonos\n"
            "└── Límites infranqueables:\n"
            "    ├── Prohibición radical de sacrificios humanos\n"
            "    └── Represión de movimientos sediciosos o contrarios al culto imperial"
        ),
        "image": None
    },
    {
        "num": 39,
        "section": "12 La Religión de Roma",
        "star": True,
        "front": "★ ¿Por qué el cristianismo fue al principio una amenaza para Roma? [Guía 4; T2 23]",
        "back": (
            "Porque planteaba una doble amenaza al orden romano:\n\n"
            "1. **Amenaza política:** al ser estrictamente monoteísta, **se negaba a adorar al emperador como a un dios**, lo que Roma interpretaba como traición al Estado.\n"
            "2. **Amenaza social:** defendía la **igualdad de todos los seres humanos ante Dios**, socavando el rígido sistema de clases y la esclavitud. Esto provocó 300 años de persecuciones intermitentes.\n\n"
            "El cristianismo primitivo como amenaza\n"
            "├── Conflicto político: rechazo tajante al culto imperial divino\n"
            "├── Conflicto social: proclamación de la igualdad universal de los hombres\n"
            "└── Reacción estatal: tres siglos de hostilidad legal y persecuciones"
        ),
        "image": None
    },
    {
        "num": 40,
        "section": "12 La Religión de Roma",
        "star": True,
        "front": "★ ¿Cómo se “romanizó” el cristianismo en los siglos II y III? [Guía 4; T2 24]",
        "back": (
            "Se romanizó adoptando las estructuras organizativas del Imperio:\n\n"
            "• Adoptó **el derecho romano** para su organización jurídica y administrativa.\n"
            "• Adoptó la organización territorial romana (diócesis, provincias eclesiásticas).\n"
            "• Estableció a **Roma como centro espiritual y jerárquico** de la cristiandad occidental.\n\n"
            "Romanización de la Iglesia (ss. II–III)\n"
            "├── Marco legal: asimilación de principios del derecho romano\n"
            "├── Geografía eclesiástica: adaptación a las demarcaciones territoriales imperiales\n"
            "└── Sede central: afirmación de Roma como cabeza de la cristiandad"
        ),
        "image": None
    },
    {
        "num": 41,
        "section": "12 La Religión de Roma",
        "star": True,
        "front": "★ ¿Por qué lo adoptaron personas de todas las clases sociales? [Guía 4; T2 24]",
        "back": (
            "Porque ofrecía una respuesta integral para todos los estamentos:\n\n"
            "1. **Clases humildes:** encontraban dignidad, consuelo, caridad comunitaria y la promesa de salvación eterna.\n"
            "2. **Clases altas e intelectuales:** encontraban una **sólida ética moral**, orden institucional y la promesa de salvaguardar la civilización y el orden del Estado frente a la decadencia moral pagana.\n\n"
            "Adopción transversal del cristianismo\n"
            "├── Clases populares: dignidad espiritual, apoyo comunitario y esperanza de redención\n"
            "└── Clases dirigentes: doctrina ética sólida y preservación del orden social y estatal"
        ),
        "image": None
    },
    {
        "num": 42,
        "section": "12 La Religión de Roma",
        "star": False,
        "front": "¿Qué hizo el emperador Constantino? [Guía 4; T2 25]\n\n![](/media/span321_constantino.png)",
        "back": (
            "Promulgó en el año **313 d. C.** el **Edicto de Milán**, mediante el cual concedió **libertad religiosa** en todo el Imperio, puso fin a las persecuciones cristianas y devolvió los bienes confiscados a la Iglesia, inaugurando una estrecha alianza entre el Estado y el cristianismo.\n\n"
            "Emperador Constantino y el Edicto de Milán (313 d. C.)\n"
            "├── Libertad religiosa: garantía universal de culto para los cristianos\n"
            "├── Cese de persecuciones: fin de la clandestinidad de las comunidades\n"
            "└── Alianza política: aproximación institucional entre Iglesia e Imperio"
        ),
        "image": "/media/span321_constantino.png"
    },
    {
        "num": 43,
        "section": "12 La Religión de Roma",
        "star": False,
        "front": "¿Qué hizo Teodosio y qué pasó a su muerte? [Guía 4; T2 25]\n\n![](/media/span321_emperador_teodosio.jpg)",
        "back": (
            "• **Qué hizo:** En el año **380 d. C.** (Edicto de Tesalónica) proclamó el cristianismo como la **religión oficial y exclusiva** del Imperio romano, cristianizando el derecho, el arte y el pensamiento.\n"
            "• **A su muerte (395 d. C.):** El Imperio quedó dividido definitivamente entre sus dos hijos: **Arcadio** (Imperio de Oriente) y **Honorio** (Imperio de Occidente).\n\n"
            "Teodosio y la división del Imperio\n"
            "├── 380 d. C.: el cristianismo se convierte en religión oficial del Imperio\n"
            "├── Cristianización total: leyes, instituciones y filosofía bajo el prisma cristiano\n"
            "└── 395 d. C. (muerte): fractura definitiva en Imperio de Oriente y Occidente"
        ),
        "image": "/media/span321_emperador_teodosio.jpg"
    },
    {
        "num": 44,
        "section": "12 La Religión de Roma",
        "star": False,
        "front": "¿Quiénes fueron los Padres de la Iglesia? [Guía 4; T2 26]\n\n![](/media/span321_padres_de_la_iglesia.jpg)",
        "back": (
            "Fueron los grandes teólogos, escritores y obispos de los **siglos I al VIII** que formularon la doctrina, los dogmas y las bases de la filosofía cristiana adaptando la tradición grecorromana. En Hispania destacó de manera sobresaliente **San Isidoro de Sevilla** (autor de las *Etimologías*).\n\n"
            "Los Padres de la Iglesia (ss. I–VIII)\n"
            "├── Función: formulación teológica, defensa de dogmas y bases filosóficas cristianas\n"
            "├── Perfil habitual: eruditos, pensadores y obispos de gran autoridad moral\n"
            "└── Exponente hispano cumbre: San Isidoro de Sevilla (autor de las *Etimologías*)"
        ),
        "image": "/media/span321_padres_de_la_iglesia.jpg"
    },
    {
        "num": 45,
        "section": "12 La Religión de Roma",
        "star": True,
        "front": "★ ¿Por qué la Iglesia es tan importante para la cultura europea? [Guía 4; T2 26]",
        "back": (
            "Porque fue **la única institución que sobrevivió a la caída del Imperio romano**. Gracias a los monasterios y al clero, la Iglesia sirvió de puente cultural indispensable para preservar y transmitir a la Edad Media el latín, el derecho, la literatura clásica y la memoria civilizatoria de Roma.\n\n"
            "Trascendencia cultural de la Iglesia en Europa\n"
            "├── Supervivencia: única estructura que resistió el colapso del Imperio de Occidente\n"
            "├── Puente histórico: canalizó la herencia grecorromana hacia los reinos medievales\n"
            "└── Transmisión del saber: conservación de manuscritos, lengua latina y derecho"
        ),
        "image": None
    },

    # =========================================================================
    # SECTION 13: La Cristianización de la Península (Q46 - Q49)
    # =========================================================================
    {
        "num": 46,
        "section": "13 La Cristianización de Hispania",
        "star": True,
        "front": "★ ¿Cómo fue la cristianización de la Península? [Guía 4; T2 27]",
        "back": (
            "Fue un proceso **temprano, profundo y tenaz**. Se inició con tradiciones apostólicas (como la predicación de Santiago y San Pablo), superó duras persecuciones romanas con numerosos mártires y terminó por transformar hondamente las costumbres, humanizando el derecho y unificando espiritualmente a las comunidades hispanas.\n\n"
            "Proceso de cristianización en Hispania\n"
            "├── Orígenes: llegada temprana de evangelizadores y apóstoles\n"
            "├── Época de pruebas: firmeza frente a las persecuciones y culto a los mártires\n"
            "└── Transformación social: atemperación moral del derecho y cohesión cívica"
        ),
        "image": None
    },
    {
        "num": 47,
        "section": "13 La Cristianización de Hispania",
        "star": False,
        "front": "¿Cómo era la arquitectura cristiana? [Guía 4; T2 28]\n\n![](/media/span321_basilica.jpg)",
        "back": (
            "Adoptó como modelo la **basílica civil romana**, un gran espacio rectangular con tres naves separadas por columnas y un ábside semicircular en la cabecera. La Iglesia transformó este edificio civil judicial en un templo para la asamblea litúrgica comunitaria y el culto a Dios.\n\n"
            "Arquitectura paleocristiana (La Basílica)\n"
            "├── Modelo origen: basílica civil romana de administración y justicia\n"
            "├── Planta: rectangular, dividida longitudinalmente en tres naves con columnas\n"
            "├── Cabecera: ábside semicircular donde se sitúa el altar sagrado\n"
            "└── Adaptación: orientada a la asamblea colectiva y celebración eucarística"
        ),
        "image": "/media/span321_basilica.jpg"
    },
    {
        "num": 48,
        "section": "13 La Cristianización de Hispania",
        "star": True,
        "front": "★ ¿Por qué decayó la escultura cristiana y cómo era? [Guía 4; T2 28]",
        "back": (
            "• **Por qué decayó:** Decayó por **cautela y temor a la idolatría pagana** (para no confundir la veneración con el culto idólatra a las estatuas de dioses paganos).\n"
            "• **Cómo era:** Era una escultura más tosca, rígida y **hierática** (sin movimiento ni realismo anatómico), concentrada casi exclusivamente en relieves de **sarcófagos** con profundo simbolismo místico y espiritual.\n\n"
            "Escultura paleocristiana\n"
            "├── Causa de decadencia: rechazo de la idolatría pagana y estatuas de bulto redondo\n"
            "├── Rasgos estéticos: hieratismo, esquematismo, rigidez y pérdida de canon anatómico\n"
            "└── Soporte fundamental: relieves en sarcófagos funerarios cristianos"
        ),
        "image": None
    },
    {
        "num": 49,
        "section": "13 La Cristianización de Hispania",
        "star": True,
        "front": "★ ¿Quién fue Aurelio Prudencio? [Guía 4; T2 29]",
        "back": (
            "Fue **el mejor y más relevante poeta lírico cristiano de Hispania** (nacido en Calahorra o Zaragoza en el siglo IV). Creó poemas e himnos cristianos de gran belleza y perfección clásica que continúan cantándose hoy en la liturgia católica.\n\n"
            "Aurelio Prudencio (siglo IV d. C.)\n"
            "├── Perfil: cumbre de la poesía lírica cristiana hispanorromana\n"
            "├── Origen: nacido en el valle del Ebro (Calahorra/Zaragoza)\n"
            "└── Legado: himnos litúrgicos que perduran en el breviario católico"
        ),
        "image": None
    }
]

def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(CARDS, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(CARDS)} cards in {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
