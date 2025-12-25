AÚN SIN CATALOGAR
- [ ] Darle a recoger ("g") en la habitación del musgo azul te permite coger musgo azul. El musgo azul tiene varias propiedades. Debe anular la petrificación (es decir, el proceso de petrificación: una criatura ya petrificada es irreversible).
- [ ] Tecla SPACE para abrir menú de interacciones avanzadas.
- [ ] Las llaves debe ser más difícil encontrarlas. Debe haber alguna pista indicando dónde están. Eso permitirá no tener que limpiar los mapas enteros, ni tener que luchar contra todo.
- [ ] Modo de combate alternativo. Opción, activable o desactibable de combate tipo JRPG: al entrar en melée se abre una ventana con una representación del enemigo o enemigos, y opciones, etc.
- [x] Indicar con un pequeño signo en el log el principio de turno.
- [!] Botas que reducen en 1 el ruido al caminar (nunca por debajo de 1).
- [x] Al coger un objeto debería aparecer la letra asignada al mismo.
- [ ] Hay que solucionar el problema de asignación de letras imposibles de teclear, como '{' etc.
- [ ] Equipar armaduras debería consumir 3 turnos (de otro modo compensa ponérselas en mitad de un combate).
- [ ] El color del cursor de selección debería ser algo como rojo o naranja, para que siempre se vea, y simplificar.
- [ ] En los mensajes, los colores del nombre "player" y de las demás criaturas tiene que ser diferente, para que se distinga rápicamente quién hace qué.
- [x] El orden de los nombres que aparecen en un tile tiene que corresponder con el de los sptrites. O sea, que si aparece primero dagger, entonces tiene que aparecer el sprite de dagger primero, y ser la dagger lo que se recoja primero. o mejon aún !! Tiene que salir un menú, como el de los cofres, para escoger qué se coge.


BALANCE
- [ ] Los guardianes de three doors tienen que ser mucho más difíciles. Pero que haya diferentes maneras de pasarlos.
- [ ] Los enemigos tienen que ser más chungos en los niveles de abajo (pues ahora mismo con un power set te cargas a casi todo).
- [ ] En los niveles más bajos, enemigos power, con escudo buenas armas, armadura, etc., enemigos ranged, enemigos mágicos, enemigos que hace phasedoor, etc.


CONCEPTO DE JUEGO
- [ ] Hay que añadir/implementar más "mini-juegos". Interacciones con habitaciones, puzzles genéricos, etc.
- [ ] Hacer que haya menos enemigos. Que el encuentro con un enemigo sea todo un reto. Que de más miedo encontrarse con algo. Que el juego exija obligatoriamente algo de uso de escucha e interacción con el medio. Premiar mejor los comportamientos de sigilo o aprovechamiento de posiciones o escucha, etc.
- [ ] Hay que hacer más interesantes a las cuevas. Que no sea sólo una cuestión de forma del mapa. Pero que la forma del mapa tenga también más impacto.


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
- [x] Quasit.
- [ ] Arpías.
- [ ] Nyarlathotep.
- [ ] Yog-Sothoth.
- [ ] Perros de tíndalos.
- [ ] Azathoth https://hplovecraft.fandom.com/es/wiki/Azathoth
- [ ] El Rey de Amarillo (avatar de Hastur)
- [x] Mimics. Mimic cofre.
- [x] Slimes. Los slimes deben poder atravesar puertas [DESCARTADO; complica mucho e innecesariamente las cosas, por obstrucción de caminos; mejor se quedan en su habitación]. Los slimes básicos deben ser muy muy lentos, y no deben atacar por sí mismos. Si se les ataca, sin embargo, y no se consigue matarlos de un solo golpe, se quedarán con el arma con que se les haya atacado. La única manera de recuperar ese arma es matando al slime, o incinerándolo. Si se mata a un slime, este no muere, sino que se convierte en dos mini-slimes, con la mitad de hp cada uno que su original, y por lo demás mismas capacidades (o sea, que puede atravesar puertas y puede absorver las armas de los atacantes). 
- [x] Cuando los slimes se regeneran a la vista del jugador, debe salir un mensaje indicándolo. De otro modo los jugadores no entenderán por qué no pueden matar a un slime (cuando lo hacen incorrectamente).
- [x] Una forma de simplificar el pathfinding de los slimes. Que lleven un registro de las casillas visitadas; después el slime simplemente intenta moverse a una casilla aleatoria de las que tiene a su alrededor y no está visitada. Así evitamos usar el pathfinding.
- [!] Las criaturas deben huir con hp bajos.
- [x] Mecánica para que las criaturas se equipen con el arma que tengan en su inventario (ver el ejemplo de los goblins).
- [x] Mecánica para que las criaturas se equipen con las armaduras que tengan en su inventario.
- [x] Instancias de una misma clase con puntos de vida diferentes y otros valores diferentes.

IA - COMPORTAMIENTO DE CRIATURAS
- [ ] Los enemigos también deberían perder DEFENSE al atacar, no??!
- [ ] Crear una ObjectRetrieverAI ordinaria. La criatura con esta AI buscará el objeto objetivo (deberá saber dónde está). Lo cogerá e intentará escapar por las escaleras más cercanas.
- [ ] Ampliar el AI HostileEnemy: algunas criaturas con una BaseAI de tipo HostileEnemy que no hayas sido todavía agraviadas nunca (aggravated), deben tener un comportamiento "oscilante". Es decir, moverse aleatoriamente (pero sin abrir puertas, ni atacar, ni hacer bump sobre nadie ni nada) a alguna casilla de su alrededor cada cierto tiempo (cada 1d6 turnos). Por otra parte, una criatura con una BaseAI de tipo HostileEnemy que haya sido agraviada (aggravated) alguna vez, dejará de estar agraviada si se cumplen la siguiente condición: el personaje que lo agravió queda fuera de su campo de visión (fov) durante 12 + 1d20 turnos. [NOTA: el sistema "oscilante" es útil para hacer más interesante el stealth, pues de otro modo es casi imposible pillar por sorpresa a un enemigo, a no ser que esté dormido.]
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
- [x] Efecto de partículas (viento) en movimiento en el nivel de superficie.
- [x] Efecto explosión bola de fuego.
- [x] Efectos especiales fogatas.
- [x] Efectos luz adventurers.
- [x] Efectos lightnin bolt.
- [x] Efectos lanzamiento de objetos.
- [x] Efecto de transición al/del negro al cambiar de niveles (fading).
- [ ] Ahora mismo la luz (el fov) de los adventurers sólo se ve si el adventurer es visible. Esto lo ideal es cambiarlo. Aunque el adventurer no sea visible, si alguna de las casillas iluminadas por el adventurer (e.e. casillas que sí son visibles para el adventurer) es visible por el personaje jugador, esa casilla debe verse iluminada. Lo mismo con los campfires. Las casillas iluminadas por el campfire que sean visibles por el jugador deben estar iluminadas, aunque el jugador no vea la casilla en la que se encuentra el campfire.

HABILIDADES ESPECIALES
- [ ] Tiene que haber alguna manera de desbloquear habilidades especiales.
- [ ] Saltar una casilla y atacar (ortogonal).
- [ ] Saltar una casilla y atacar (diagonal).
- [ ] Saltar una casilla (retroceder) ortogonal.
- [ ] Saltar una casilla (retroceder) diagonal.
- [ ] Atacar a una casilla de distancia (con lanza).
- [ ] Ganar bonus en ataque diagonal. (Parece que actualmente los enemigos buscan siempre ortogonal. Esto es trabajo ganado. Se trataría de añadir ciertos bonus a los ataques diagonales, y diseñar la manera de conseguir posicionarse en diagonal).

PERKS
- [ ] Heridas, cojera, epilepsia, visiones, u otras cosas, útiles/buenas o no.

PERGAMINOS
- [ ] Pergamino de círculo protector. Impide durante 25 turnos la entrada de toda criatura en un radio de 2.
- [ ] Pergamino de imagen doble. Durante X turnos aumenta la defensa del lector en 4.
- [ ] Pergamino de escudo mágico. Durante X turnos aumenta la defensa del lector en Y puntos.
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
- [ ] Poción de aumento del FOH temporal!! Que lo aumente un montón temporalmente, de forma que quien la beba reciba un montón de mensajes detallados de lo que está pasando/hay a su alrededor.
- [ ] Poción de pequeño aumento permanente del FOH.
- [x] BUG: Creo que la potion of True Sight se está identificando al lanzarla contra criatura. No debería.
- [x] Crear animación para lanzamiento de pociones.
- [ ] ¿Animación para la rotura de pociones?
- [x] Crear animación genérica para lanzamiento de cualquier objeto.

ANILLOS
- [!] Anillo de detectar peligro. Se activa si hay un peligro dentro de un radio x. El anillo apretará más o menos el dedo de su portador dependiendo del nivel de peligro detectado.
- [ ] Anillo stealth.
- [ ] Anillo de invisibilidad
- [ ] Anilos mixtos, con propiedades mágicas buenas y también malas.
- [x] Anillos malditos.
- [x] Anillo de fuerza +1
- [x] Anillo de estamina.
- [x] Anillo de infravisión.

COLGANTES Y AMULETOS


ARMAS MÁGICAS


BASTONES MÁGICOS ÚNICOS
- [x] Bastón tunelador. [Actualmente el bastón tiene cargas infinitas]


ARMADURAS MÁGICAS


COFRES
- [x] Dibujar un sprite para los cofres para el psuedo-ascii.
- [x] Sonido al abrir (y cerrar) cofres.
- [DESCARTADO] Una vez abiertos no se pueden cerrar (arreglar esto).
- [ ] Tenemos que implementar la mecánica para introducir objetos dentro de un cofre. Es decir, para transferir objetos del inventario al cofre abierto.

COFRES ESPECIALES (O ÚNICOS)
- [!] Cofres especiales (con contenidos especiales, fijos o no) para colocar en ciertas habitaciones en particular o niveles o ramas. Por ejemplo, que al final de una rama secundaria haya una probabilidad de que se genere un cofre especial con algún objeto muy valioso o especial o único.
- [ ] Se pueden hacer también librerías especiales.

MOVILIARIO, OBJETOS DECORATIVOS E INTERACTIVOS
- [ ] Rediseñar de un modo coherente las mesas. Ahora mismo son un fighter de la clase Door. Esto es muy raro. Unificar criterios y buscar una forma más elegante e intuitiva de gestionar el ser de las tablas.
- [x] Librerías con libros y/o pergaminos.
- [!] Más objetos decorativos o interactivos en las habitaciones. Barriles, Carteles con mensajes, inscripciones en el suelo o paredes, aventureros petrificados, restos de...

OBJETOS VARIOS
- [x] Escudos. Los escudos deben añadirte DEFENSE. Deben equiparse en la ranura OFFHAND.
- [ ] Guantes. Alguno mágico, que te suba el to-hit, o la suerte.
- [ ] Botas.
- [ ] Mushroms.
- [x] Cascos. Con propiedades. Hará el juego más interesante, y una forma de poder enfrentarse a la progresión de la dificultad de enemigos.
- [-] Capas. Las capas han de ser lanzables. Además de tener un bonus al stealth. Algunas serán mágicas.
- [-] Bastones mágicos.
- [!] Pala y cuerda. La pala te permite cavar en la casilla en la que te encuentras y bajar al nivel de abajo. La cuerda te permite volver a subir por el agujero (para evitar quedarte atrapado por el sistema de llaves-cerraduras). Si no tiene una cuerda, soltará un mensaje del tipo a "no voy a cavar un agujero sin tener una cuerda por la que poder bajar", o algo así.
- [x] La sand bag (tiene que tener 3 usos). Al lanzar arena sobre un enemigo este tiene que quedar cegado (pero la mecánica de cegado para un PNJ deberá ser algo como confusion, o paralisis).
- [x] Libros, notas.

LIBROS MÁGICOS (e.e. capaces de hacer algo)
- [ ] Libros que explican qué hacen, cómo funcionan, condiciones, etc. de otros libros mágicos.
- [x] Todos los libros deben poder leerse en voz alta. Para que un libro "mágico" produzca sus efectos hará falta leerlo en voz alta.
- [ ] Al leer en voz alta un libro "ordinario" habrá una probabilidad de "pacificar" a una criatura hostil, o incluso de volverla amiga o aliada, o producir en ella efectos varios. Los goblins deben poder pacificarse con ciertos libros. No todas las criaturas podrán ser pacificadas.
- [!] Libros mágicos especiales. Algo especial puede suceder si se lanza el libro adecuado contra un slime.
- [ ] Los libros mágicos serán libros con efectos muy poderosos, pero cuyos efectos son sensibles a condiciones, o que sólo pueden activarse sus efectos si al leerlos se cumplen una serie de condiciones. Los libros mágicos no se consumen. Pero leerlos tiene un coste. Algunos pueden transformar de algún modo al jugador, o producir un efecto colateral/secundario.
- [ ] Libro de levantar muertos. Todos los cadáveres se levantan como zombies y los huesos como skeletons. En un caso los levantados serán aliados del jugador y en otro enemigos.
- [ ] Libro/s reactivo/s: a) Se vuelve ilegible si matas a cierto tipo de criatura. b) Cambia su efecto según tu alineamiento o reputación. c) Te “juzga” y decide si cooperar. Pueden negarse a ser leídos. Pueden también atraer enemigos que quieren destruirlos.
- [ ] Libro/s con condiciones para poder ser leídos: luz, silencio o tiempo sin interrupciones; leer en combate tiene efectos imprevisibles; según la cordura u otro atributo, puede tener efectos diferentes.
- [-] Libro de silencio. Deja en silencio todo durante X turnos. Bajo ciertas condiciones, todas las criaturas se duermen.
- [ ] Libro de conciencia remota. Te permite tomar la perspectiva de un enemigo. Mientras estás "conectado" con él no puedes ver lo que pasa a tu alrededor. Bajo ciertas condiciones, puedes tomar el control de la criatura. Bajo ciertas condiciones, puedes escoger con qué criatura conectar.
- [ ] Libro transformador. Transforma un objeto en otro. Bajo ciertas condiciones, transforma todos los objetos de tu inventario en otros. Bajo ciertas condiciones, te permite controlar qué objeto conseguir.
- [ ] Libro que no debería existir. No aparece identificado como libro. Leerlo crea una copia imperfecta del jugador. La copia aprende de tus acciones.
- [!] Libro de visión. Permite ver qué hay en otro punto del mapa.
- [ ] Libro de portal. Abre un portal mágico que lleva a algún otro sitio. Bajo ciertas circunstancias te introduce en un bucle espacio-temporal.
- [ ] Libro de portal espejo. Genera un portal. Si hay generados dos portales, al entrar por uno se aparece por el otro. No puede haber más de dos portales creados al mismo tiempo. Los portales tienen (quizá) una duración. 
- [x] Libro de las pociones! Si lo lees, identifica todas las pociones.
- [ ] Libro de los pergaminos. Idem.
- [ ] Libro de círculo de protección. Ninguna criatura podrá entrar en un radio de 2 casillas.
- [ ] Leer en voz alta debe requerir tres turnos. Si en ese tiempo el jugador es atacado la lectura será interrumpida.

ARTEFACTOS
- [ ] Artefacto reloj de arena. El reloj es un objeto necesario para resolver uno de los grandes puzles del juego.
- [ ] Crear artefacto revolver. Es un objeto único. Se tiene en el inventario, y al activarlo, permite disparar. El revolver tiene 6 balas (y no se puede recargar, pues no existirán más balas en toda la mazmorra). Cuando se dispara el revolver, el jugador escoge el objetivo. Son objetivos válidos las criaturas que sean visibles y que se encuentren en un radio de 25 casillas o menos. La probabilidad de impactar será como sigue: 100% a la distancia de una casilla.... El daño será variable.

HUD - USER INTERFACE - ETC
- [ ] Ventana con diálogos.
- [ ] Instrucciones que se carguen de un html, con colores.
- [x] Si una criatura está dormida, debe indicarse en la descripción de inspección. Si está despierta pero ignorando al jugador, estaría bien que lo dijera también.
- [ ] Posibilidad de fuentes diferentes en el panel inferior de mensajes, en las ventanas popup, etc. Ver tema fuentes en cogmind: https://www.gridsagegames.com/blog/2014/09/cogmind-fonts/
- [ ] Tras morir, mensaje de confirmación y fundido a negro. Ir a una pantalla con algún arte (una lápida o restos de huesos o lo que sea). P.D.: Es más interesante una pantalla en la que aparezca el número de turnos sobrevivido, el inventario, el nivel al que se ha llegado, etc. (tomar como modelo el obituario de The warlock of finetop mountain roguelike). Ejemplo:

A great adventurer has fallen
Abelardo the adventurer was killed by a orc archer.
He survived X turns.
He killed X creatures.
Stats
As darkness surrounds Abelardo, the last sound he hears is laughter.
He entered Firetop mountain.
He found the orcish barracks.
Equipment
[...]
Messajes (últimos mensajes)
[...]
Output to Abelardo.txt

- [x] Intro. Pantalla de introducción (anulable con tecla ESC). Una transición de tres o cuatro pantallas, con un texto introductorio, y con gráficos ascii a partir de la segunda o tercera pantall. Línea de la historia: elegido por tu tribu para recuperar un antiguo artefacto perdido. En sueños se ha visto el artefacto guardado en un ¿cofre? en el fondo de una ancestral mazmorra (de la que nadie conoce su origen). Texto útil:

«Está escrito en el templo: ...e incontables niños retornarán a la noche primigenia.»
«Estás aterrorizado. Nadie te preparó para esta oscuridad.»
«Has sido elegido para la gran búsqueda»

- [ ] Animación de carga al generar una nueva partida.
- [x] Posibilidad de ejecutar el juego en pantalla completa.
- [x] Pantalla de ayuda, con descripción de teclas y comandos.
- [x] Arreglar el combat panel.
- [ ] Idioma inglés y español.
- [ ] Rediseñar el combat panel.
- [x] Las ventanas que se abren con información tienen que aplicar formato al texto (respetar los límites de la ventana, etc.).
- [x] Que los mensajes repetidos iguales se apilen, al modo de nethack, con un multiplicador, y así no se consuman más líneas.
- [ ] Mejorar la presentación de texto largo en las ventanas popup (justificado, colores, saltos de línea, etc.)
- [x] Pantalla de ayuda con el documento de instrucciones de cómo funciona el combate, el sigilo, etc.
- [ ] Mejorar sistema de inventario.
- [x] Info de objetos.
- [ ] Rellenar la info de objetos.
- [ ] Etiqueta "poisoned" en el panel de abajo para cuando se está envenenado. Y etiqueta confused.

SALAS ESPECIALES
- [ ] Tiendas.

EVENTOS ESPECIALES
- [ ] Misiones.
- [ ] Mensaje misterioso de radio. Un antiguo mensaje grabado y reproduciéndose en bucle.

HISTORIA / LORE
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
- [x] Ramas (branches). En algunos niveles debe haber más de una escalera de bajada. Debe haber una rama principal y otras accesorias, que te proporcionan objetos valiosos o información valiosa. Algunas branches deberías ser obligatorias: en ellas habrá una llave sin la cual no se puede avanzar en la rama principal.
- [!] Habitaciones con etiquetas. Para generar descripciones y eventos y creación de historia. Habrá etiquetas comunes ("cámara húmeda", "celda vacía", etc.) y etiquetas únicas. Ciertos eventos se dispararán sólo en las habitaciones con etiquetas únicas. Habrá tmb habitaciones que el PJ deberá investigar o pasar por, etc.

DUNGEON GENERATION
- [ ] Crear algún generador diferente.
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

bug; estoy recibiendo mensajes de "quasit attacks quasit" pero no estoy viendo ningún quasit.

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