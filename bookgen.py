"""Book title and content pools used to generate random books."""

import random

# Titles available for generated books.
BOOK_TITLES = [
    "Worm-eaten Volume",
    "Crumbling Leatherbound Book",
    "Dusty Grimoire Fragment",
    "Heavy Ironclasp Tome",
    "Brittle Binding Codex",
    "Faded Illuminated Folio",
    "Mildew-stained Compendium",
    "Ancient Script Ledger",
    "Water-warped Anthology",
    "Bone-hinged Tome",
    "Char-streaked Grimoire",
    "Gilt-edged Chronicle",
    "Torn Spine Treatise",
    "Ink-faded Encyclopedia",
    "Ragged Scholar’s Glossary",
    "Runic-etched Handbook",
    "Candle-waxed Manual",
    "Loose-leaf Reference Book",
    "Broken-corner Lexicon",
    "Smoke-tinged Almanac",
    "Moth-bitten Bestiary",
    "Heavy Slate-bound Codex",
    "Dust-layered Archive Book",
    "Severed Binding Monograph",
    "Tarnished Cover Volume",
    "Obsidian-clasp Scriptbook",
    "Scrawled Marginalia Book",
    "Collapsed Spine Primer",
    "Stiff-paged Instruction Book",
    "Forgotten Lore Register",
]


_title_pool = BOOK_TITLES.copy()

# Short text fragments used as book contents.
BOOK_FRAGMENTS = [
    """Enmudecieron todos, conteniendo
el habla, ansiosos de escuchar. Eneas
empieza entonces desde su alto estrado:
«Espantable dolor es el que mandas,
oh reina, renovar con esta historia
del ocaso de Ilión, de cómo el reino,
que es imposible recordar sin llanto, 
""",
"""el Griego derribó: ruina misérrima
que vi y en que arrostré parte tan grande.
¿Quién, Mirmidón o Dólope o soldado
del implacable Ulises, referirla
pudiera sin llorar? Y ya en la altura
la húmeda noche avanza, y las estrellas
lentas declinan convidando al sueño.
""",
"""Mas si tanto interés tu amor te inspira
por saber nuestras lástimas, y en suma
lo que fue Troya en su hora postrimera,
aunque el solo recuerdo me estremece,
y esquiva el alma su dolor, empiezo.
Del Hado rebatidos, tantos años,
los caudillos de Grecia, hartos de lides,
""",
"""con arte digno de la excelsa Palas,
un caballo edifican —los costados,
vigas de abeto, un monte de madera—;
y hacen correr la voz que era el exvoto
por una vuelta venturosa. Astutos,
sortean capitanes escogidos
y en los oscuros flancos los ocultan, 
""",
"""cueva ingente cargada de guerreros.
Hay a vista de Ilión una isla célebre
bajo el troyano cetro rico emporio,
Ténedos, hoy anclaje mal seguro:
vanse hasta allí y en su arenal se esconden.
Los creemos en fuga hacia Micenas,
y de su largo duelo toda Troya 
""",
"""se siente libre al fin. Las puertas se abren
¡qué gozo ir por los dorios campamentos
y ver vacía la llanura toda
y desierta la orilla! «Aquí, los Dólopes,
aquí, las tiendas del cruel Aquiles;
cubrían las escuadras esta playa;
las batallas, aquí…» Muchos admiran """,
"""
la mole del caballo, don funesto
a Palas virginal. Lanza Timetes
la idea de acogerle por los muros
hasta el alcázar —o traición dolosa,
u obra tal vez del Hado que ya urgía—.
Mas Capis, y con él los más juiciosos,
están porque en el mar se hunda al caballo,""",
"""
don insidioso de la astucia griega,
tras entregarle al fuego, o se taladre
a que descubra el monstruo su secreto.
Incierto el vulgo entre los dos vacila.
De pronto, desde lo alto del alcázar,
acorre al frente de crecida tropa
Laoconte enardecido, y desde lejos: """,
"""
«¡Oh ciudadanos míseros! —les grita—
¿qué locura es la vuestra? ¿al enemigo
imagináis en fuga? ¿o que una dádiva
pueda, si es griega, carecer de dolo?
¿no conocéis a Ulises? O es manida
de Argivos este leño, o es la máquina
que, salvando los muros, se dispone """,
"""
a dominar las casas, y de súbito
dar sobre Ilión; en todo caso un fraude.
Mas del caballo no os fiéis, Troyanos:
yo temo al Griego, aunque presente dones.»
Dice, y en un alarde de pujanza,
venablo enorme contra el vientre asesta
del monstruo y sus igares acombados. 
""",
"""Prendido el dardo retembló, y al golpe
respondió en la caverna hondo gemido.
¡Y a no ser por los Hados, por la insania
de ceguera fatal, la madriguera
de esos Griegos hurgara él con la pica,
y en pie estuvieras, Troya,
y sin quebranto os irguierais, alcázares de Príamo! 
""",
"""En este trance unos pastores teucros
con grande grita a un joven maniatado
traían ante el rey. A la captura
no había resistido: empeño suyo
era franquear Ilión a los Argivos;
y resuelto venía a todo extremo,
o a consumar su engaño, o de la muerte 
""",
"""a afrontar el rigor. Para mirarle,
ansiosa en torno de él se arremolina la juventud troyana y le baldona.
Mas oye la perfidia…, y por un Dánao
podrás sin falla conocer a todos.
Porque al verse indefenso entre el concurso,
todo él turbado, en torno la mirada
tiende por la dardania muchedumbre, 
""",
"""y «¡Ay! —suspiró— ¿qué mar, qué tierra amiga
me podrá recibir? ¿o qué me queda
cuitado, sin asilo entre los Griegos,
y reo cuya sangre airados piden
los Dardanios a una?» Este gemido
nos conmueve y abate nuestro encono.
Le alentamos a que hable, que nos diga 
""",
"""de qué raza es nacido, qué le trae
y en qué fundó, al rendirse, su esperanza.
Depuesto el miedo al fin, «Oh rey —prosigue—,
de cuanto ha sido, fuere lo que fuere,
la verdad diré yo. Y antes que nada,
no niego ser argivo: la Fortuna
pudo hacer a Sinón desventurado 
""",
"""mas no hablador mendaz y antojadizo.
Tal vez haya llegado a tus oídos
un nombre: Palamedes, el Belida,
rey glorioso, que, al tiempo de una falsa
alarma de traición, se vio acusado
—atropello inmoral de un inocente
sin más delito que objetar la guerra—. 
""",
"""Lo arrastraron los Griegos al suplicio;
llóranle hoy, tarde ya. Como, aunque pobres,
éramos de su sangre, yo desde Argos,
mandado por mi padre, joven vine
a iniciarme en las armas a su sombra;
y mientras el mantuvo su fortuna
e intacto su prestigio entre los reyes, 
""",
"""también logró mi nombre algún decoro.
Mas cuando, al galope del falsario Ulises,
partióse, como sabes, de esta vida,
derrocado yo al par, triste y oscura
arrastraba mi suerte, protestando
a solas del malogro del amigo. 
""",
"""Y no callé, loco de mí: venganza
me atreví a prometer, si con victoria
volvía yo a mi patria, y duros odios
con esto concité. Tal fue el principio
de mi infortunio y del afán de Ulises
por aterrarme con achaques falsos
y dichos que esparcía por el vulgo. 
""",
"""Consciente de su crimen, dase mañas,
armas buscando contra mí, ni ceja
hasta lograr que Calcas, su ministro…
Mas ¿por qué revolver lo que a vosotros
nada puede importar? ¿a qué alargarme?
Si ante vuestro rigor los Griegos todos
son una cosa, y ser yo Griego basta
para el castigo, tiempo es ya: matadme… 
""",
"""¿Qué más se quiere Ulises? ¡y a buen precio
de seguro os lo pagan los Atridas!"
""",



]

_fragment_pool = BOOK_FRAGMENTS.copy()

STATIC_BOOKS = {
    "corridor_chronicles": {
        "title": "Crónicas del Pasillo 8a",
        "content": (
            "Lo intentamos con una solución de limo y carbón. Al principio pareció dar resultado."
        ),
    },
    "fungi_book": {
        "title": "Tratado sobre hongos luminosos",
        "content": (
            "Los antiguos habitantes del Desierto Pálido apreciaban mucho el hongo rojo. Cavaron profundas cavernas subterráneas para poder acceder a ellos."
        ),
    },
    "living_stoone_theory": {
        "title": "Teoría de la piedra viva",
        "content": (
            "[...]"
        ),
    },
    "nine_lanterns_codex": {
        "title": "El códice de las nueve linternas",
        "content": (
            "[...]"
        ),
    },
    "coal_stories": {
        "title": "Historias a la luz del carbón",
        "content": (
            "Los aventureros veteranos atan campanas diminutas a sus mochilas. Dicen que ahuyentan a lo que vive en el techo.",
        ),
    },
    "crack_finder_book": {
        "title": "Manual del buscador de grietas",
        "content": (
            "[...]"
        ),
    },
    "lower_cavern_bestiary": {
        "title": "Bestiario de la caverna baja",
        "content": (
            "[...]"
        ),
    },
    "sixteen_rings": {
        "title": "Los 16 anillos",
        "content": (
            "[...]"
        ),
    },
    "wanderers_diary": {
        "title": "El diario del errante",
        "content": (
            "[...]"
        ),
    },
    "tired_librarian_notes": {
        "title": "Notas de un bibliotecario cansado",
        "content": (
            "[...]"
        ),
    },
    "forgotten_canticle": {
        "title": "Cántico olvidado",
        "content": (
            "En cada tramo de escalera se oyen los versos, pero sólo bajan. "
            "Nunca suben. Quien los siga encontrará la puerta sin bisagras."
        ),
    },
    "architect_notes": {
        "title": "Notas del arquitecto",
        "content": (
            "Nunca usamos los mismos planos dos veces. Si ves un pasillo donde no debería estar, "
            "alguien ha abierto el pliegue equivocado."
        ),
    },
    "red_tower_mails": {
        "title": "Cartas desde la Torre Roja",
        "content": (
            "Un viajero asegura haber visto a las ratas pararse en dos patas y hablar entre ellas cuando creen que nadie mira."
        ),
    },
}


def random_book_title() -> str:
    """Return a random book title, cycling through the pool before repeating."""
    global _title_pool
    if not _title_pool:
        _title_pool = BOOK_TITLES.copy()
    index = random.randint(0, len(_title_pool) - 1)
    return _title_pool.pop(index)


def random_book_fragment() -> str:
    """Return a random book fragment, cycling through the pool before repeating."""
    global _fragment_pool
    if not _fragment_pool:
        _fragment_pool = BOOK_FRAGMENTS.copy()
    index = random.randint(0, len(_fragment_pool) - 1)
    return _fragment_pool.pop(index)


def get_static_book_payload(key: str) -> tuple[str, str]:
    """Return (title, content) for a static book key."""
    entry = STATIC_BOOKS[key]
    return entry["title"], entry["content"]
