# TODO: deberían poder crearse con objetos estas salas. Donde aparezca 
# el carácter '~' debe generarse un scroll (aleatorio), donde aparezca 
# el caracter '!' debe generarse una poción aleatoria, y donde aparezca 
# el caracter '/' debe aparecer un arma aleatoria. La probabilidad de que 
# aparezca una cosa u otra debe ser configurable, así como la probabilidad 
# de que aparezca un tipo u otro de pócima (si lo que se genera es una pócima), 
# un tipo u otro de pergamino (si lo que se genera es un pergamino), un tipo u otro 
# de arma (si lo que se genera es un arma).

room_01 = (
    "..##..##..##..",
    "..............",
    "..............",
    "..##..##..##..",
)

room_02 = (
    "..............",
    "..............",
    "..#..#..#..#..",
    "..............",
    "..............",
)

room_03 = (
    "..............",
    "..#..#..#..#..",
    "..............",
)

room_04 = (
    "....",
    ".....",
    ".......",
    ".........",
    "...........",
)

# room_secret = (
#     "############",
#     "#.......#..#",
#     "#.......#..#",
#     "#.......B..#",
#     "#.......#..#",
#     "############",
# )

# BUG: Esta habitación genera un bug extraño, que ni yo ni Codex hemos sido capaces
# de entender: las puertas no funcionan, como si fueran muros. Lo raro es que las puertas
# de la room_door, en cambio, A VECES sí funcionan.
# room_secret_B = (
#     ".....#..#.....",
#     ".....+..+.....",
#     ".....#..#.....",
# )

# BUG: ver descripción del bug más arriba.
# room_door = (
#     "############",
#     "#.......#..#",
#     "#.......#..#",
#     "#.......+..#",
#     "#.......#..#",
#     "############",
# )

# cross_road = (
#     "###.###",
#     "###.###",
#     "......",
#     "###.###",
#     "###.###",
# )

# cross_road = (
#     "#######",
#     "###.###",
#     "#.....#",
#     "###.###",
#     "#######",
# )