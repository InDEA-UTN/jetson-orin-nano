# Abecedario de Senas LED - Paso 6: fuente de letras para la matriz 8x8.
#
# La Pico (../../espejo_facial_led/pico/main.py) no sabe nada de letras ni de senas: solo recibe
# 8 bytes por UDP y prende los bits que le llegan (protocolo documentado en
# ../../espejo_facial_led/README.md, seccion 9). Toda la inteligencia de "que dibujar" vive de
# este lado. Por eso la Pico no se toca para nada en este proyecto.
#
# Cada letra se disena en una grilla clasica de matrices de puntos, 5 columnas x 7 filas (deja un
# margen de 1 fila/columna dentro del 8x8, y es el tamano estandar con el que una letra mayuscula
# se lee bien en una matriz chica). FUENTE tiene ese 5x7 en bruto, con '#'/'.' para que se vea a
# simple vista en el codigo. sprite_de_letra() lo centra en el canvas de 8x8 real y lo convierte
# a '1'/'0' (misma convencion que gestos.py del espejo facial: fila 0 arriba, bit 7 = pixel
# izquierdo via sprite_a_bytes).
#
# 'space', 'del' y la ausencia de mano NO tienen sprite aca a proposito: la decision fue que la
# matriz se apague en esos tres casos (ver reconocer_letra_matriz.py), no que muestren un simbolo
# propio.

FUENTE = {
    "A": [".###.",
          "#...#",
          "#...#",
          "#####",
          "#...#",
          "#...#",
          "#...#"],
    "B": ["####.",
          "#...#",
          "#...#",
          "####.",
          "#...#",
          "#...#",
          "####."],
    "C": [".####",
          "#....",
          "#....",
          "#....",
          "#....",
          "#....",
          ".####"],
    "D": ["####.",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          "####."],
    "E": ["#####",
          "#....",
          "#....",
          "####.",
          "#....",
          "#....",
          "#####"],
    "F": ["#####",
          "#....",
          "#....",
          "####.",
          "#....",
          "#....",
          "#...."],
    "G": [".####",
          "#....",
          "#....",
          "#.###",
          "#...#",
          "#...#",
          ".####"],
    "H": ["#...#",
          "#...#",
          "#...#",
          "#####",
          "#...#",
          "#...#",
          "#...#"],
    "I": ["#####",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          "#####"],
    "J": ["..###",
          "...#.",
          "...#.",
          "...#.",
          "...#.",
          "#..#.",
          ".##.."],
    "K": ["#...#",
          "#..#.",
          "#.#..",
          "##...",
          "#.#..",
          "#..#.",
          "#...#"],
    "L": ["#....",
          "#....",
          "#....",
          "#....",
          "#....",
          "#....",
          "#####"],
    "M": ["#...#",
          "##.##",
          "#.#.#",
          "#...#",
          "#...#",
          "#...#",
          "#...#"],
    "N": ["#...#",
          "##..#",
          "#.#.#",
          "#..##",
          "#...#",
          "#...#",
          "#...#"],
    "O": [".###.",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          ".###."],
    "P": ["####.",
          "#...#",
          "#...#",
          "####.",
          "#....",
          "#....",
          "#...."],
    "Q": [".###.",
          "#...#",
          "#...#",
          "#...#",
          "#.#.#",
          "#..#.",
          ".##.#"],
    "R": ["####.",
          "#...#",
          "#...#",
          "####.",
          "#.#..",
          "#..#.",
          "#...#"],
    "S": [".####",
          "#....",
          "#....",
          ".###.",
          "....#",
          "....#",
          "####."],
    "T": ["#####",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          "..#.."],
    "U": ["#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          ".###."],
    "V": ["#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          ".#.#.",
          "..#.."],
    # W, X e Y usan 7 columnas en vez de 5: son las tres letras con trazos diagonales, y esos
    # necesitan mas columnas de por medio para verse suaves en vez de comprimidos. Se puede
    # porque cada letra se centra en su propio ancho (ver sprite_de_letra) y la matriz muestra
    # una sola letra fija a la vez, no texto corriendo -- no hace falta que todas midan lo mismo.
    "W": ["#..#..#",
          "#..#..#",
          ".#.#.#.",
          ".#.#.#.",
          ".##.##.",
          "..#.#..",
          "..#.#.."],
    "X": ["#.....#",
          ".#...#.",
          "..#.#..",
          "...#...",
          "..#.#..",
          ".#...#.",
          "#.....#"],
    "Y": ["#.....#",
          ".#...#.",
          "..#.#..",
          "...#...",
          "...#...",
          "...#...",
          "...#..."],
    "Z": ["#####",
          "....#",
          "...#.",
          "..#..",
          ".#...",
          "#....",
          "#####"],
}

def sprite_de_letra(letra):
    """Glifo de FUENTE (5 o 7 columnas, segun la letra) -> sprite de 8 filas de 8 caracteres
    '0'/'1', el formato que ya entiende sprite_a_bytes(). El margen izquierdo se calcula segun
    el ancho de ESA letra, para que una de 5 columnas y una de 7 (W, X, Y: ver el comentario
    en FUENTE) queden centradas cada una en su propio ancho dentro del canvas de 8x8; el margen
    superior se calcula igual, segun el alto (7 filas siempre), para centrar tambien verticalmente
    y no dejar la letra pegada arriba con la fila 8 siempre vacia. Una letra sin glifo definido
    (no deberia pasar con las 26 de LETRAS, pero por si acaso) devuelve la matriz apagada en vez
    de reventar."""
    glifo = FUENTE.get(letra.upper())
    filas = ["0" * 8 for _ in range(8)]
    if glifo is None:
        return filas
    margen_izq = (8 - len(glifo[0])) // 2
    margen_arriba = (8 - len(glifo)) // 2
    for i, fila in enumerate(glifo):
        contenido = "0" * margen_izq + fila.replace("#", "1").replace(".", "0")
        contenido = contenido.ljust(8, "0")
        filas[margen_arriba + i] = contenido
    return filas


def sprite_a_bytes(sprite):
    """8 filas de texto '0'/'1' -> los 8 bytes del protocolo UDP (bit 7 = pixel izquierdo).
    Misma funcion que gestos.py del espejo facial, copiada aca para no acoplar los dos proyectos
    por un import cruzado de dos lineas."""
    return bytes(int(fila, 2) for fila in sprite)
