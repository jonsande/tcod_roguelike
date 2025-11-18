VARIOS
- [x] Analyze the combat message issue for adventurers
- [x] Identify where combat messages are added in actions.py (MeleeAction and possibly ThrowItemAction)
- [x] Add visibility check for messages when adventurer is involved
- [x] Implement helper method _add_combat_message in MeleeAction
- [x] Replace add_message calls with _add_combat_message
- [x] Test the changes

ARMAS
- [ ] Bajarles el color a los sprites de armas.

CRIATURAS
- [ ] Personajes únicos!
- [ ] Instancias de una misma clase con puntos de vida diferentes y otros valores diferentes. Actualmente, aunque establezca en entity_factories que los atributos de una criatura (por ejemplo, el base_defense de un goblin, el hp de un monkey, o la stamina de un orc) se generen aleatoriamente, por ejemplo mediante un randint(2,5) o similar, todas las instancias generadas de esa clase de criatura comparten el mismo valor para esos atributos. O sea, que en en una tirada de randint(2,5) para establecer los puntos hp de un goblin sale 3, todos los goblins generados tienen 3 puntos de hp. Me gustaría cambiar este funcionamiento. Me gustaría que cada instancia pudiera tener un valor diferente, de modo que se generasen (siguiendo con el ejemplo) algunos goblins con 3 puntos de hp, pero otros con 2, o con 4, etc.

IA
- [ ] Una vez que un enemigo no visible ha sido aggravated tiene que haber una probabilidad de darle esquinazo. No puede ser que el jugador quede ya como objetivo. En cada turno habrá que hacer una tirada para ver si sigue buscándole o no.
- [ ] Mejorar IAs de enemigos para que vaya más rápido cuando en un mapa hay muchos. Que haya algo así como un estado de letargo, en la que no hagan apenas cálculos.

AVENTURERS
- [x] Ponerles drop loot a los adventurers.
- [ ] Aumentar su fov en la primera planta!! Para que vayan directos a las escaleras.
- [x] Los aventureros exploran la planta en busca de la habitación con escaleras. Si la encuentran, toman las escaleras y desaparecen. Después de eso hay una probabilidad de encontrar sus cadáveres en niveles inferiores. Si en su camino pasan junto a un fuego, se quedarán junto al fuego hasta que este se extinga. Si se quedan sin stamina en algún momento, esperarán un turno para recuperar un punto. Son neutrales al personaje jugador, pero si este ataca a un adventurer, se volverá hostil. Si un jugador ocupa una de las casillas junto a un adventurer este "le hablara". Soltará un mensaje aleatorio de una batería enorme. Esta manera será el modo habitual de conseguir pistas sobre el juego. No todas las pistas serán verdaderas. Pero no todo lo que los adventurers digan serán pistas.
- [ ] Aún hay veces que los adventurers se quedan como dando vueltas en una habitación (creo que cuando algún breakable wall interfiere su camino).
- [x] Los adventurers deberían equiparse con un arma nada más generarse (si tienen alguna en el inventario).

EFECTOS SONOROS / SONIDO
- [ ] Que la transición de música ambiente sea con fade in/out.
- [x] Sonido ambiente!
- [x] Sistema para sonidos sfx
- [ ] Más sonidos (algunos personalizados, que marquen alguna diferencia) de pisadas, risas, armas, fuego.

EFECTOS VISUALES
- [x] Efecto explosión bola de fuego.
- [x] Efectos especiales fogatas.
- [x] Efectos luz adventurers.
- [x] Efectos lightnin bolt.
- [x] Efectos lanzamiento de objetos.
- [ ] Ahora mismo la luz (el fov) de los adventurers sólo se ve si el adventurer es visible. Esto lo ideal es cambiarlo. Aunque el adventurer no sea visible, si alguna de las casillas que sí es visible para el adventurer es visible por el personaje jugador, esa casilla debe verse iluminada.

PERGAMINOS
- [ ] Limitar la distancia a la que se pueden "lanzar" los pergaminos.
- [ ] Pergamino de descender de nivel.
- [ ] El paralysis scroll dura quizá poco.
- [ ] Algún sistema para aumentar el stealth de forma permanente (un pergamino).
- [ ] Pergamino summon monsters
- [ ] Pergamino de generar humo (impide la visión en un área determinada)
- [ ] Pergamino de teletransporte
- [ ] Pergamino que haga el player.fighter.super_memory True, para que se active el sistema de memoria típico
- [ ] Pergamino que identifica si el efecto del objeto es bueno, malo, o neutral.

POCIONES
- [ ] BUG: Creo que la potion of True Sight se está identificando al lanzarla contra criatura. No debería.
- [x] Crear animación para lanzamiento de pociones.
- [ ] ¿Animación para la rotura de pociones?
- [x] Crear animación genérica para lanzamiento de cualquier objeto.

COFRES
- [x] Dibujar un sprite para los cofres para el psuedo-ascii.
- [ ] Sonido al abrir (y cerrar) cofres.
- [ ] Una vez abiertos no se pueden cerrar (arreglar esto).
- [ ] Tenemos que implementar la mecánica para introducir objetos dentro de un cofre. Es decir, para transferir objetos del inventario al cofre abierto.

LIBRERÍAS
- [ ] Con libros y/o pergaminos.

OBJETOS VARIOS
- [ ] La sand bag (tiene que tener 3 usos). Al lanzar arena sobre un enemigo este tiene que quedar cegado (pero la mecánica de cegado para un PNJ deberá ser algo como confusion, o paralisis).
- [!] Libros, notas. La recopilación de notas, para descubrir historias (y secretos) debería ser una pieza clave del juego.
- [!] Más objetos decorativos o interactivos en las habitaciones. Barriles, Carteles con mensajes, inscripciones en el suelo o paredes, aventureros petrificados, restos de...

ARTEFACTOS
- [ ] Crear artefacto revolver. Es un objeto único. Se tiene en el inventario, y al activarlo, permite disparar. El revolver tiene 6 balas (y no se puede recargar, pues no existirán más balas en toda la mazmorra). Cuando se dispara el revolver, el jugador escoge el objetivo. Son objetivos válidos las criaturas que sean visibles y que se encuentren en un radio de 25 casillas o menos. La probabilidad de impactar será como sigue: 100% a la distancia de una casilla.... El daño será variable.

CUEVAS
- [ ] Revisar el loot de las cuevas. Parece que se trata todo como una habitación. Hay que hacerlo de otra forma.
- [ ] Las paredes de las cavernas tienen que usar otro sprite.
- [ ] Las cuevas parece que se consideran un única habitación, de modo que se generan con muchos menos monstruos.

HUD
- [!] Pantalla de ayuda, con descripción de teclas y comandos.
- [x] Las ventanas que se abren con información tienen que aplicar formato al texto (respetar los límites de la ventana, etc.).
- [ ] Mejorar la presentación de texto largo en las ventanas popup (justificado, colores, saltos de línea, etc.)
- [ ] Pantalla de ayuda con el documento de instrucciones de cómo funciona el combate, el sigilo, etc.
- [ ] Mejorar sistema de inventario.
- [x] Info de objetos.
- [ ] Rellenar la info de objetos.

DUNGEON GENERATION
- [!] La probabilidad de generarse un objeto por habitación debe ser independiente. Ahora mismo se aplica la tirada a todas las habitaciones de la planta. Esto hace que el jugador sepa rápido si en esa planta merece la pena buscar o no.
- [ ] El color de los sprites de muro debe ser relativo y fijo al nivel. 
- [ ] Arreglar problemas con la generación de fixed rooms (custom rooms)
- [ ] Las fixed rooms deberían poder crearse con objetos estas salas. Donde aparezca el carácter '~' debe generarse un scroll (aleatorio), donde aparezca el caracter '!' debe generarse una poción aleatoria, y donde aparezca el caracter '/' debe aparecer un arma aleatoria. La probabilidad de que aparezca una cosa u otra debe ser configurable, así como la probabilidad de que aparezca un tipo u otro de pócima (si lo que se genera es una pócima), un tipo u otro de pergamino (si lo que se genera es un pergamino), un tipo u otro de arma (si lo que se genera es un arma).

FIXED DUNGEONS
- [ ] En cada dungeon total sólo debe haber dos fixed dungeons: una a mitad del descenso, la otra en el nivel final. 
- [ ] La fixed dungeon del nivel final ha de ser siempre igual. Diseñarla.
La fixed dungeon de mitad de descenso se escogerá entre una batería de posibles:
    - [ ] Templo de los monos (templo abandonado, lleno de monos)
    - [ ] Capilla de los centinelas (los centinelas guardando tres puertas, y solo detrás de una de ellas están las escaleras. Estaría bien que hubiera alguna pista en las plantas anteriores indicando cuál es la puerta. O que algún adventurer le contara un rumor al respecto).
    - [ ] Otros.

COMBATE
- [!] Rediseñar el sistema de cálculo de daño del combate. Cambiar el modo en que funcionan las armas a este respecto. Hacerlo todo más claro. Y más congruente con el factor "pericia del luchador" (proficiency).
- [ ] Si el enemigo está paralizado, no debería bajarte stamina por luchar contra él o pasar turno junto a él.
- [ ] Ataques especiales!! Por ejemplo, que puedas hacer un ataque al mismo tiempo que retrocedes una casilla, o una carga, o un ataque con desplazamiento lateral... Algo que le de un rollo ajedrez.
- [ ] El sistema de fortificar (fortify). Si te queda algún punto de stamina y pasas turno con un enemigo a tu lado adoptas posición defensiva. Gasta un punto de estamina pero aumenta tu valor defensivo. PARECE QUE ESTOY YA FUNCIONA!! LO ÚNICO QUE HACE FALTA ES QUE APAREZCA UN INDICADOR DE QUE SE ESTÁ FORTIFICANDO.

MECÁNICAS
- [x] Cofres!
- [ ] Puertas cerradas con llave. Sólo se abren si el personaje jugador tiene la llave correspondiente a esa puerta en el inventario. Las llaves se tienen que generar siempre en lugares de la mazmorra anteriores a la puerta [redactar esto mejor].
- [!] Trampas!
- [ ] Portales mágicos!
- [ ] Objeto malditos!: debe ser simplificado (tipo unexplored, no nethack: o sea, que no haya con un mismo nombre una versión maldita y otra no, pues complica mucho el código). Unos objetos se considerarán "bueno", otros "malos", y otros "netrales".
- [ ] Profundizar en el sistema de críticos (creo que hay algo en el stealth mode, pero nada más)
- [ ] Profundizar en el sistema de suerte.


BUGS

BUG: cuando una adventurer entra en combate con una criatura salen los mensajes del combate en pantalla. No deberían salir, si el adventurer no es visible para ej personaje jugador.

BUGS: cuando dos adventurers se encuentran, a veces se siguen atascando. No creo que haya muchas posibilidades de que suceda, porque no es probable que se generen más de dos adventurers en una misma planta, ni tampoco que se crucen. Pero puede pasar. Es un bug conocido que no he conseguido solucionar por ahora.

BUG: ningún sprite debe poder estar encima del sprite de scaleras.

BUG: en un mapa se ha generado en la casilla en la que había un muro destruible. Esto no debe ocurrir. Pero, si por algún error ocurriera, desde luego el sprite del muro rompible (mientras no se haya destruido) tiene que verse por encima del sprite de cualquier otro objeto.

BUG: El ... BUT FAILS cuando es un adventurer atacándote aparece en rojo, pero debería ser verde.

BUG: A veces el sprite de escaleras que suben no se ve!! A veces parece quedar bajo el sprite de las baldosas del suelo.

Debris que oculta escaleras

[SOLUCIONADO (parece)] [P.D. No está solucionado del todo. Con las fixed rooms genera problemas] A veces se generan mapas en los que no es posible llegar a las escaleras. Si al generar un mapa no existe manera transitable de llegar a las escaleras de bajada desde el punto de inserción del jugador habrá que o bien eliminar los muros necesarios para que sí exista camino transitable hasta las escaleras, o bien sustituir los muros mínimos necesarios por muros rompibles (si el camino está bloqueado por un muro rompible o más sí se considera que existe manera transitable de llegar a las escaleras, pues se puede romper ese muro para llegar a las escaleras).