AÚN SIN CATALOGAR
- [ ] El color del cursor de selección debería ser algo como rojo o naranja, para que siempre se vea, y simplificar.
- [ ] En los mensajes, los colores del nombre "player" y de las demás criaturas tiene que ser diferente, para que se distinga rápicamente quién hace qué.
- [x] El orden de los nombres que aparecen en un tile tiene que corresponder con el de los sptrites. O sea, que si aparece primero dagger, entonces tiene que aparecer el sprite de dagger primero, y ser la dagger lo que se recoja primero. o mejon aún !! Tiene que salir un menú, como el de los cofres, para escoger qué se coge.

RENDIMIENTO
- [!!] Algo está reduciendo el rendimiento. Mejorarlo!! Ver informe hecho por blackbox. P.D. Con 7 criaturas en una planta muy abierta (cueva), ya se nota una bajada de rendimiento considerable. Estoy hay que merorarlo. P.D.: es el cálculo de pathfinding, parece.

TILES
- [ ] Nuevo tipo de tile. Chasm (abismo). Bloquea el movimiento, su sprite es totalmente negro. 

ARMAS
- [x] Criaturas que combaten desarmadas tienen que tener algún bonificador de daño por garras o pueños o lo que sea.
- [x] Añadir en una casilla la distancia a la que se puede lanzar una daga. [P.D. Esto depende de la fuerza y pericia del jugador]
- [ ] Bajarles el color a los sprites de armas.
- [x] Los objetos equipados en el inventario deben ir de otro color.

CRIATURAS
- [-] Slimes! Los slimes deben poder atravesar puertas. Los slimes básicos deben ser muy muy lentos, y no deben atacar por sí mismos. Si se les ataca, sin embargo, y no se consigue matarlos de un solo golpe, se quedarán con el arma con que se les haya atacado. La única manera de recuperar ese arma es matando al slime, o incinerándolo. Si se mata a un slime, este no muere, sino que se convierte en dos mini-slimes, con la mitad de hp cada uno que su original, y por lo demás mismas capacidades (o sea, que puede atravesar puertas y puede absorver las armas de los atacantes). 
- [ ] Cuando los slimes se regeneran a la vista del jugador, debe salir un mensaje indicándolo. De otro modo los jugadores no entenderán por qué no pueden matar a un slime (cuando lo hacen incorrectamente).
- [!] Una forma de simplificar el pathfinding de los slimes. Que lleven un registro de las casillas visitadas; después el slime simplemente intenta moverse a una casilla aleatoria de las que tiene a su alrededor y no está visitada. Así evitamos usar el pathfinding.
- [!] Las criaturas deben huir con hp bajos.
- [x] Mecánica para que las criaturas se equipen con el arma que tengan en su inventario (ver el ejemplo de los goblins).
- [x] Mecánica para que las criaturas se equipen con las armaduras que tengan en su inventario.
- [-] Instancias de una misma clase con puntos de vida diferentes y otros valores diferentes. Actualmente, aunque establezca en entity_factories que los atributos de una criatura (por ejemplo, el base_defense de un goblin, el hp de un monkey, o la stamina de un orc) se generen aleatoriamente, por ejemplo mediante un randint(2,5) o similar, parece que todas las instancias generadas de esa clase de criatura comparten el mismo valor para esos atributos. O sea, que en si en una tirada de randint(7,12) para establecer los puntos hp de un goblin sale 12, todos los goblins generados tienen 12 puntos de hp (comprueba que es correcto lo que digo). ¿Por qué sucede esto? Me gustaría cambiar este funcionamiento. Me gustaría que cada instancia pudiera tener un valor diferente, de modo que se generasen (siguiendo con el ejemplo) algunos goblins con 12 puntos de hp, pero otros con 7, o con 9, etc. ¿Es posible? [P.D. Creo que está parcialmente implementado, pero hay que comprobarlo. Lo que sí está implementado es que la generacín de inventario ahora es exclusiva de cada instancia; antes sucedía que todas las instancias de la clase tenían el mismo inventario resultante de su loot_table].

IA
- [ ] Ampliar el AI HostileEnemy: las criaturas con una BaseAI de tipo HostileEnemy que no hayas sido todavía agraviadas nunca (aggravated), deben tener un comportamiento "oscilante". Es decir, moverse aleatoriamente (pero sin abrir puertas, ni atacar, ni hacer bump sobre nadie ni nada) a alguna casilla de su alrededor cada cierto tiempo (cada 1d6 turnos). Por otra parte, una criatura con una BaseAI de tipo HostileEnemy que haya sido agraviada (aggravated) alguna vez, dejará de estar agraviada si se cumplen la siguiente condición: el personaje que lo agravió queda fuera de su campo de visión (fov) durante 12 + 1d20 turnos. [NOTA: el sistema "oscilante" es útil para hacer más interesante el stealth, pues de otro modo es casi imposible pillar por sorpresa a un enemigo, a no ser que esté dormido.]
- [!] Las criaturas deben huir con hp bajos
- [ ] Una vez que un enemigo no visible ha sido aggravated tiene que haber una probabilidad de darle esquinazo. No puede ser que el jugador quede ya como objetivo. En cada turno habrá que hacer una tirada para ver si sigue buscándole o no.
- [ ] Mejorar IAs de enemigos para que vaya más rápido cuando en un mapa hay muchos. Que haya algo así como un estado de letargo, en la que no hagan apenas cálculos.
- [ ] Que algunos enemigos cojan objetos del suelo. Sobre todo si los ha lanzado el jugador.

AVENTURERS
- [x] Ponerles drop loot a los adventurers.
- [ ] Aumentar su fov en la primera planta!! Para que vayan directos a las escaleras.
- [x] Los aventureros exploran la planta en busca de la habitación con escaleras. Si la encuentran, toman las escaleras y desaparecen. Después de eso hay una probabilidad de encontrar sus cadáveres en niveles inferiores. Si en su camino pasan junto a un fuego, se quedarán junto al fuego hasta que este se extinga. Si se quedan sin stamina en algún momento, esperarán un turno para recuperar un punto. Son neutrales al personaje jugador, pero si este ataca a un adventurer, se volverá hostil. Si un jugador ocupa una de las casillas junto a un adventurer este "le hablara". Soltará un mensaje aleatorio de una batería enorme. Esta manera será el modo habitual de conseguir pistas sobre el juego. No todas las pistas serán verdaderas. Pero no todo lo que los adventurers digan serán pistas.
- [ ] Aún hay veces que los adventurers se quedan como dando vueltas en una habitación (creo que cuando algún breakable wall interfiere su camino).
- [x] Los adventurers deberían equiparse con un arma nada más generarse (si tienen alguna en el inventario).
- [ ] Los adventurers podrían/deberían (según el caso) coger pociones u otros objetos que se encontraran en su línea de visión.

PERSONAJES ÚNICOS O ESPECIALES
- [!] Duende (maligno y benigno). Puede dar consejos al PJ, ayudarlo o putearlo. Se anuncia su presencia en un nivel por medio del sonido de unas risitas (con su correspondiente mensaje). Debe haber varias notas que lo mencionan. Algunas con verdades sobre él y otras con falsedades.
- [-] Anciano del fuego eterno. Normalmente en el nivel de superficie. Junto a un campfire que nunca se apaga. Le da consejos cripticos al PJ. En ocasiones le puede obsequiar con un objeto mágico. En otras partidas el viejo no está, y sólo están los restos de la fogata.
- [ ] Robot estropeado pero aún operativo (imitando quizá el sprite de Cogmind).
- [ ] Slime parlante.

EFECTOS SONOROS / SONIDO
- [ ] Sonido al comer.
- [ ] Sonido de viento en el nivel de superficie.
- [ ] Más sonidos! De muerte específicos por criatura, ataques por arma, bajada de escaleras, etc.
- [-] Sonido de queja/lamento al recibir daño (específico de cada criatura).
- [-] Sonido de ataques con armas y desarmado. [Sistema implementado, pero sin configurar]
- [ ] Sonido del fireball y del pergamino del rayo.
- [x] Sonidos de recoger objetos.
- [x] Sonido de fuergo jungo a las fogatas (al recuperar vida, disparar el función correspondiente).
- [x] Que la transición de música ambiente sea con fade in/out.
- [x] Sonido ambiente!
- [x] Sistema para sonidos sfx
- [-] Más sonidos (algunos personalizados, que marquen alguna diferencia) de pisadas, risas, armas, fuego.

EFECTOS VISUALES
- [ ] Efecto de partículas (viento) en movimiento en el nivel de superficie.
- [x] Efecto explosión bola de fuego.
- [x] Efectos especiales fogatas.
- [x] Efectos luz adventurers.
- [x] Efectos lightnin bolt.
- [x] Efectos lanzamiento de objetos.
- [x] Efecto de transición al/del negro al cambiar de niveles (fading).
- [ ] Ahora mismo la luz (el fov) de los adventurers sólo se ve si el adventurer es visible. Esto lo ideal es cambiarlo. Aunque el adventurer no sea visible, si alguna de las casillas iluminadas por el adventurer (e.e. casillas que sí son visibles para el adventurer) es visible por el personaje jugador, esa casilla debe verse iluminada. Lo mismo con los campfires. Las casillas iluminadas por el campfire que sean visibles por el jugador deben estar iluminadas, aunque el jugador no vea la casilla en la que se encuentra el campfire.

PERGAMINOS
- [DESCARTADO] Limitar la distancia a la que se pueden "lanzar" los pergaminos. [P.D. Está naturalmente limitada por la limitación de visión]
- [x] Pergamino de descender de nivel.
- [ ] El paralysis scroll dura quizá poco.
- [ ] Algún sistema para aumentar el stealth de forma permanente (un pergamino).
- [ ] Pergamino summon monsters.
- [x] Pergamino de identificación.
- [!] Pergamino de levantar muertos blanco. Todos los cadáveres de la planta se convertiran en skeletons, hostiles hacia el lanzador.
- [!] Pergamino de levantar muertos negro. Todos los cadáveres de la planta se convertirán en skeletons que atacarán a toda criatura visible, excepto al lanzador/lector del pergamino.
- [ ] Pergamino de generar humo (impide la visión en un área determinada)
- [x] Pergamino de teletransporte
- [x] Pergamino que haga el player.fighter.super_memory True, para que se active el sistema de memoria típico
- [ ] Pergamino que identifica si el efecto del objeto es bueno, malo, o neutral.

POCIONES
- [x] BUG: Creo que la potion of True Sight se está identificando al lanzarla contra criatura. No debería.
- [x] Crear animación para lanzamiento de pociones.
- [ ] ¿Animación para la rotura de pociones?
- [x] Crear animación genérica para lanzamiento de cualquier objeto.

ANILLOS
- [ ] Anillo stealth.
- [ ] Anillo de invisibilidad
- [ ] Anilos mixtos, con propiedades mágicas buenas y también malas.
- [x] Anillos malditos.
- [x] Anillo de fuerza +1
- [x] Anillo de estamina.
- [x] Anillo de infravisión.

COLGANTES Y AMULETOS


ARMAS MÁGICAS


ARMADURAS MÁGICAS


COFRES
- [x] Dibujar un sprite para los cofres para el psuedo-ascii.
- [x] Sonido al abrir (y cerrar) cofres.
- [DESCARTADO] Una vez abiertos no se pueden cerrar (arreglar esto).
- [ ] Tenemos que implementar la mecánica para introducir objetos dentro de un cofre. Es decir, para transferir objetos del inventario al cofre abierto.

MOVILIARIO, OBJETOS DECORATIVOS E INTERACTIVOS
- [ ] Rediseñar de un modo coherente las mesas. Ahora mismo son un fighter de la clase Door. Esto es muy raro. Unificar criterios y buscar una forma más elegante e intuitiva de gestionar el ser de las tablas.
- [x] Librerías con libros y/o pergaminos.
- [!] Más objetos decorativos o interactivos en las habitaciones. Barriles, Carteles con mensajes, inscripciones en el suelo o paredes, aventureros petrificados, restos de...

OBJETOS VARIOS
- [ ] Guantes! Alguno mágico, que te suba el to-hit, o la suerte.
- [ ] Botas!
- [ ] Mushroms!
- [x] Cascos! Con propiedades. Hará el juego más interesante, y una forma de poder enfrentarse a la progresión de la dificultad de enemigos.
- [-] Capas! Las capas han de ser lanzables. Además de tener un bonus al stealth. Algunas serán mágicas.
- [ ] Bastones mágicos!
- [!] Pala y cuerda. La pala te permite cavar en la casilla en la que te encuentras y bajar al nivel de abajo. La cuerda te permite volver a subir por el agujero (para evitar quedarte atrapado por el sistema de llaves-cerraduras). Si no tiene una cuerda, soltará un mensaje del tipo a "no voy a cavar un agujero sin tener una cuerda por la que poder bajar", o algo así.
- [x] La sand bag (tiene que tener 3 usos). Al lanzar arena sobre un enemigo este tiene que quedar cegado (pero la mecánica de cegado para un PNJ deberá ser algo como confusion, o paralisis).
- [x] Libros, notas. 

ARTEFACTOS
- [ ] Artefacto reloj de arena. El reloj es un objeto necesario para resolver uno de los grandes puzles del juego.
- [ ] Crear artefacto revolver. Es un objeto único. Se tiene en el inventario, y al activarlo, permite disparar. El revolver tiene 6 balas (y no se puede recargar, pues no existirán más balas en toda la mazmorra). Cuando se dispara el revolver, el jugador escoge el objetivo. Son objetivos válidos las criaturas que sean visibles y que se encuentren en un radio de 25 casillas o menos. La probabilidad de impactar será como sigue: 100% a la distancia de una casilla.... El daño será variable.

HUD - USER INTERFACE - ETC
- [ ] Si una criatura está dormida, debe indicarse en la descripción de inspección. Si está despierta pero ignorando al jugador, estaría bien que lo dijera también.
- [ ] Posibilidad de fuentes diferentes en el panel inferior de mensajes, en las ventanas popup, etc. Ver tema fuentes en cogmind: https://www.gridsagegames.com/blog/2014/09/cogmind-fonts/
- [ ] Tras morir, mensaje de confirmación y fundido a negro. Ir a una pantalla con algún arte (una lápida o restos de huesos o lo que sea).
- [ ] Intro. Pantalla de introducción (anulable con tecla ESC). Una transición de tres o cuatro pantallas, con un texto introductorio, y con gráficos ascii a partir de la segunda o tercera pantall. Línea de la historia: elegido por tu tribu para recuperar un antiguo artefacto perdido. En sueños se ha visto el artefacto guardado en un ¿cofre? en el fondo de una ancestral mazmorra (de la que nadie conoce su origen). Texto útil:

«Está escrito en el templo: ...e incontables niños retornarán a la noche primigenia.»
«Estás aterrorizado. Nadie te preparó para esta oscuridad.»
«Has sido elegido para la gran búsqueda»

- [ ] Animación de carga al generar una nueva partida.
- [x] Posibilidad de ejecutar el juego en pantalla completa.
- [!] Pantalla de ayuda, con descripción de teclas y comandos.
- [!] Arreglar el combat panel.
- [ ] Idioma inglés y español.
- [ ] Rediseñar el combat panel.
- [x] Las ventanas que se abren con información tienen que aplicar formato al texto (respetar los límites de la ventana, etc.).
- [x] Que los mensajes repetidos iguales se apilen, al modo de nethack, con un multiplicador, y así no se consuman más líneas.
- [ ] Mejorar la presentación de texto largo en las ventanas popup (justificado, colores, saltos de línea, etc.)
- [ ] Pantalla de ayuda con el documento de instrucciones de cómo funciona el combate, el sigilo, etc.
- [ ] Mejorar sistema de inventario.
- [x] Info de objetos.
- [ ] Rellenar la info de objetos.
- [ ] Etiqueta "poisoned" en el panel de abajo para cuando se está envenenado. Y etiqueta confused.

SALAS ESPECIALES
- [ ] Tiendas!

EVENTOS ESPECIALES
- [ ] Misiones.
- [ ] Mensaje misterioso de radio. Un antiguo mensaje grabado y reproduciéndose en bucle.

HISTORIA / LORE
- [!] Libros mágicos especiales. Algo especial puede suceder si se lanza el libro adecuado contra un slime.
- [ ] Estatua. Personajes petrificados por la poción de petrificación.
- [!] Las notas/libros con mensajes deben ser únicas! Sólo debe haber una instancia de cada.
- [ ] La conversación del anciano y otros personajes importantes tiene que salir en una ventana dedicada.
- [ ] En el nivel 4 debe lanzarse un evento especial.
- [ ] Está previsto que en el juego haya una serie de puzles menores y una serie de puzles mayores. Para resolver algunos de los puzles mayores hará falta algunos objetos únicos, como el reloj de arena y la pala y la cuerda para el nivel de la biblioteca.
- [ ] Eventos especiales:

CUEVAS
- [x] Revisar el loot de las cuevas. Parece que se trata todo como una habitación. Hay que hacerlo de otra forma.
- [ ] Las paredes de las cavernas tienen que usar otro sprite.
- [x] Las cuevas parece que se consideran un única habitación, de modo que se generan con muchos menos monstruos.

WORLD GENERATION
- [ ] Ramas (branches). En algunos niveles debe haber más de una escalera de bajada. Debe haber una rama principal y otras accesorias, que te proporcionan objetos valiosos o información valiosa. Algunas branches deberías ser obligatorias: en ellas habrá una llave sin la cual no se puede avanzar en la rama principal.

DUNGEON GENERATION
- [x] Hot path.
- [-] Green zone: función que te devuelve el conjunto de habitaciones que son accesibles desde una habitación cualquiera. [Hecho pero con defectos. Hay función específica para debugging]
- [x] Cerciorarse de que el max_instances de un objeto está funcionando. [P.D. Se ha rehecho el sistema. Ahora funciona. Afecta, lo mismo que el nuevo min_instances únicamente a lo generado proceduralemente, no a lo generado estáticamente].
- [x] La probabilidad de generarse un objeto por habitación debe ser independiente.
- [ ] El color de los sprites de muro debe ser relativo y fijo al nivel. 
- [ ] Arreglar problemas con la generación de fixed rooms (custom rooms)
- [ ] Las fixed rooms deberían poder crearse con objetos estas salas. Donde aparezca el carácter '~' debe generarse un scroll (aleatorio), donde aparezca el caracter '!' debe generarse una poción aleatoria, y donde aparezca el caracter '/' debe aparecer un arma aleatoria. La probabilidad de que aparezca una cosa u otra debe ser configurable, así como la probabilidad de que aparezca un tipo u otro de pócima (si lo que se genera es una pócima), un tipo u otro de pergamino (si lo que se genera es un pergamino), un tipo u otro de arma (si lo que se genera es un arma).

FIXED DUNGEONS
- [x] El generate_fixed_dungeon() es algo primitivo. Por ejemplo, sólo genera las criaturas que tiene hardcodeadas dentro de la función. Revisarlo.
- [ ] En cada dungeon total sólo debe haber dos fixed dungeons: una a mitad del descenso, la otra en el nivel final. 
- [ ] La fixed dungeon del nivel final ha de ser siempre igual. Diseñarla.
La fixed dungeon de mitad de descenso se escogerá entre una batería de posibles:
    - [ ] Templo de los monos (templo abandonado, lleno de monos)
    - [ ] Capilla de los centinelas (los centinelas guardando tres puertas, y solo detrás de una de ellas están las escaleras. Estaría bien que hubiera alguna pista en las plantas anteriores indicando cuál es la puerta. O que algún adventurer le contara un rumor al respecto).
    - [ ] Biblioteca. Inspirada en la librería de Indiana Jones: las escaleras de bajada estarán escondidas. En la librería habrá un juego de pistas que te dira cuál es la casilla correcta en la que se encuentran las escaleras de bajada. Habrá que excavar en esa casilla para poder seguir bajando. Para ello hará falta tener un pico o una pala.
    - [ ] Catacumbas (bajo la biblioteca).
    - [ ] Mazmorras (cárceles). Una planta con celdas. En algunas bichos dentro. En alguna otra un personaje único.
    - [ ] Otros.

COMBATE
- [!] El valor mínimo de TO-HIT debe ser 0!! Si no se rompe la fórmula. Aun así la penalización de armadura se modifica igual, pues cuando el jugador debería ganar 1 punto en melee, se quedaría en 0.
- [x] Rediseñar el sistema de cálculo de daño del combate. Cambiar el modo en que funcionan las armas a este respecto. Hacerlo todo más claro. Y más congruente con el factor "pericia del luchador" (proficiency).
- [x] Describir bien cómo funciona el combate, con sus elementos tácticos y sus fórmulas.
- [x] Modificar el character information, acorde con el rediseño del sistema de cálculo de daño.
- [-] Echar un vistazo a la mecánica de sigilo/stealth y backstab (es muy antigua y necesita seguramente ajustes). [P.D. Está revisada, pero necesita testeo, y seguramente necesita más revisión].
- [x] Modificar la mecánica del combate táctico. Actualmente es:
- [DESCARTADO] Si el enemigo está paralizado (o ciego), no debería bajarte stamina por luchar contra él o pasar turno junto a él. Tiene que cambiar el sistema melee con él. Por ejemplo: no debe gastar stamina esperar turno junto a él. 
- [x] Si el enemigo está ciego o paralizado, debe tmb haber un bonus a tu hit muy grande. (Hecho: ahora mismo el bonus viene por la penalización al Defense y al to hit que sufre el propio cegado o paralizado).
- [ ] Ataques especiales!! Por ejemplo, que puedas hacer un ataque al mismo tiempo que retrocedes una casilla, o una carga, o un ataque con desplazamiento lateral... Algo que le de un rollo ajedrez.
- [-] El sistema de fortificar (fortify). Si te queda algún punto de stamina y pasas turno con un enemigo a tu lado adoptas posición defensiva. Gasta un punto de estamina pero aumenta tu valor defensivo. PARECE QUE ESTOY YA FUNCIONA!! LO ÚNICO QUE HACE FALTA ES QUE APAREZCA UN INDICADOR DE QUE SE ESTÁ FORTIFICANDO.

MECÁNICAS
- [ ] Mejorar el sistema de agraviar criaturas. Su cálculo no debería atravesar paredes. Pero cuidado con el deterioro del rendimiento!
- [ ] Estado de invisibilidad.
- [ ] Estado de oculto en las sombras.
- [ ] Cuando el Personaje Jugador mejore su percepción, podrá interpretar qué tipo de criatura se oye al otro lado de una puerta, si la conoce.
- [x] Revisar las mecánicas de sigilo y la ia al respecto.
- Sistema de puertas con llave:
    - [x] Si las llaves de color se van a consumir, deben generarse tantas como puertas de ese color. Quizá lo complica todo mucho. Mejor que las llaves no se consuman.
    - [x] Las llaves deben poder generarse en el inventario de mosntruos. Esto hay que programarlo en _ensure_keys_for_locked_doors() de game_map.py.
- [x] Generación de ítems aleatorios en los mapas de tipo fixed maps.
- [x] Cuando hay varios objetos en el suelo y se da a recoger, debe salir un menú para escoger qué objeto se quiere recoger.
- [x] Cuando hay más de un objeto de la misma clase en el suelo, debe salir un multiplicador.
- [x] Esperar junto a una puerta cerrada para oir/escuchar. Te dice si hay alguna criatura a unas 5 o 6 casillas a distancia tras la puerta.
- [x] Solucionar el tema de la lámpara/linterna y el fov!!
- [ ] La recopilación de notas, para descubrir historias (y secretos) debería ser una pieza clave del juego.
- [x] Cofres!
- [-] Decidir cómo se sube la DEFENSE. Hay que tener en cuenta que la DEFENSE es el valor contra el que tira el atacante para decidir un hit. Actualmente sólo es posible acumular puntos mediante la mecánica táctica de melee (de esperar, retirarse, etc.), pero haría falta que hubiera alguna manera de que el PJ desarrollara su DEFENSE a lo largo de la partida. [P.D. Actualmente se suve el DEF por un sistema básico de xp: se contabiliza el número de impactos fallados dirigidos contra el jugador; a partir de un determinado número, configurable desde el settings, gana 1 punto a DEF y el contador se reinicia].
- [-] Decidir en consecuencia (con lo decidido para el DEFENSE) cómo subir el To-hit. Progresiń en el aumento de defensa tiene que ir acompañado de la posibilidad de progresión en el to-hit. [P.D. En el modelo actual el to hit se puede subir mediante pociones y a las bonificaciones de las propias armas; pendiente está crear algún encantamiento o pergamino dedicado a ello].
- [x] Puertas cerradas con llave. Sólo se abren si el personaje jugador tiene la llave correspondiente a esa puerta en el inventario. Las llaves se tienen que generar siempre en lugares de la mazmorra anteriores a la puerta [redactar esto mejor].
- [!] Trampas!
- [ ] Portales mágicos!
- [x] Objeto malditos!: debe ser simplificado (tipo unexplored, no nethack: o sea, que no haya con un mismo nombre una versión maldita y otra no, pues complica mucho el código). 
- [ ] Unos objetos se considerarán "bueno", otros "malos", y otros "netrales". Crearles ese atributo, a fin de poder crear un pergamino de tipo "detectar magia".
- [ ] Profundizar en el sistema de críticos (creo que hay algo en el stealth mode, pero nada más)
- [ ] Profundizar en el sistema de suerte.
- [DESCARTADO] Sí que va a haber un sistema de experiencia. Estará oculto. El jugador no sabrá nada. Servirá para subir la weapon proficiency. Hay que rediseñarlo. Dará puntos por los túrnos que se pase en melee junto a una criatura hostil (hay que arreglar eso de que junto a neutrales se entre en melee también).

VARIOS
- [ ] El nombre del Personaje Jugador (PJ) debe generarse proceduralmente, siguiendo las siguientes reglas y consideraciones: habrá una batería de hasta 12 nombres de pila, y un contador de cuántas veces se ha jugado una partida con ese nombre de pila. Al comenzar una partida, se escogerá aleatoriamente un nombre de pila, se le añadirá el artículo " the ", y por último se le añadirá un ordinal (escrito en texto, no en número), de modo que quede un resultado así como, por ejemplo, "Abelardo the fourth". No podrá haber más de 16 ordinales por nombre.


BUGS

bug: los enemigos ciegos siguen persiguiéndote. Deberían quedarse quietos. O moverse al tuntún.

GUB: A veces los adventurers atacan al jugador! Parecen ataques aleatorios. como si estuviese tratando de moverse a esa casilla (pues no engancha a melee). Se diría que no está bien configurado. Si en la casilla destina esta player, debe hacer un WaitAction.

BUG: A los adventurers, cuando se les lanza una poción de ceguera se comportan como si nada. Si estás combatiendo con ellos esto es bastante frustrante.

BUG: Se están generando fogatas sobre las escaleras de bajada!!!!

BUG: Al lanzar la restore stamina potion el cursor no vuelve a 0,0. Lo mismo al lanzar un pergamino de fireball, Lo mismo al lanzar una poción de veneno poison.

BUG: Parece que si queda un meat donde hay una puerta, y la puerta se cierra, el sprite de meat se queda por encima del de la puerta. Lo mismo pasa con los cadáveres. No sé cón otros objetos.

BUG: El hot_path a veces no se genera correctamente. Puede ser que tenga que ver con el modo en que construye el camino la máquina. Ahora mismo no lo construye siguiendo las casillas transitables.

BUG: Cuando se lanza una poción de ceguera contra una criatura y la criatura recupera la visión al de un tiempo, se recibe el mensaje: "Shapes slowly emerge again around you". Es incorrecto. Hay que relativizar el mensaje.

BUG: Cuando el texto de la pantalla de arriba es demasiado largo, se sale de la pantalla.

BUG: cuando una adventurer entra en combate con una criatura salen los mensajes del combate en pantalla. No deberían salir, si el adventurer no es visible para ej personaje jugador.

BUGS: cuando dos adventurers se encuentran, a veces se siguen atascando. No creo que haya muchas posibilidades de que suceda, porque no es probable que se generen más de dos adventurers en una misma planta, ni tampoco que se crucen. Pero puede pasar. Es un bug conocido que no he conseguido solucionar por ahora.

BUG: ningún sprite debe poder estar encima del sprite de scaleras.

BUG: en un mapa se ha generado en la casilla en la que había un muro destruible. Esto no debe ocurrir. Pero, si por algún error ocurriera, desde luego el sprite del muro rompible (mientras no se haya destruido) tiene que verse por encima del sprite de cualquier otro objeto.

BUG: El ... BUT FAILS cuando es un adventurer atacándote aparece en rojo, pero debería ser verde.

BUG: A veces el sprite de escaleras que suben no se ve!! A veces parece quedar bajo el sprite de las baldosas del suelo.

Debris que oculta escaleras

[SOLUCIONADO (parece)] [P.D. No está solucionado del todo. Con las fixed rooms genera problemas] A veces se generan mapas en los que no es posible llegar a las escaleras. Si al generar un mapa no existe manera transitable de llegar a las escaleras de bajada desde el punto de inserción del jugador habrá que o bien eliminar los muros necesarios para que sí exista camino transitable hasta las escaleras, o bien sustituir los muros mínimos necesarios por muros rompibles (si el camino está bloqueado por un muro rompible o más sí se considera que existe manera transitable de llegar a las escaleras, pues se puede romper ese muro para llegar a las escaleras).