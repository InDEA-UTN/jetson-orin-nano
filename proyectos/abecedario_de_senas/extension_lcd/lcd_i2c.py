# Driver minimo para un LCD de caracteres HD44780 (16x2) con el modulo I2C PCF8574 soldado atras.
# Escrito a mano en vez de bajar una libreria: es corto, y asi queda a la vista que hace cada byte
# que viaja por el I2C.
#
# El PCF8574 copia cada byte que recibe por I2C a sus 8 patitas de salida, que estan soldadas a
# pines del LCD (cableado de casi todos los modulos que se venden):
#
#   bit:   7    6    5    4    3     2    1    0
#          D7   D6   D5   D4   LUZ   E    RW   RS
#
# Solo hay 4 cables de datos (D4..D7), asi que el LCD se usa en "modo 4 bits": cada byte se manda
# en dos mitades, primero la alta y despues la baja, cada una con un pulso de E.

import time

RS = 0x01    # bit 0: 0 = comando, 1 = caracter a escribir
E = 0x04     # bit 2: el LCD toma los datos cuando E baja de 1 a 0
LUZ = 0x08   # bit 3: luz de fondo prendida
# RW (bit 1) no aparece: siempre escribimos, nunca leemos del LCD, asi que queda siempre en 0.

# Direccion en la memoria del LCD donde empieza cada linea: la linea 2 no arranca donde termina la
# 1 (0x10), sino en 0x40 -- es asi en el controlador HD44780, no depende del modulo.
INICIO_LINEA = (0x00, 0x40)


class LcdI2C:
    def __init__(self, i2c, direccion=0x27):
        self.i2c = i2c
        self.direccion = direccion

        # Secuencia de arranque de la hoja de datos del HD44780: al prenderse no se sabe si quedo
        # en modo 8 o 4 bits, asi que se le manda "modo 8 bits" tres veces para llevarlo a un
        # estado conocido, y recien ahi se lo pasa a 4 bits. Las esperas son las de la hoja.
        time.sleep_ms(50)           # el LCD necesita ~40 ms despues de recibir alimentacion
        for espera in (5, 1, 1):
            self._nibble(0x30, 0)
            time.sleep_ms(espera)
        self._nibble(0x20, 0)       # a partir de aca, modo 4 bits

        self._comando(0x28)         # 4 bits, 2 lineas, letras de 5x8 puntos
        self._comando(0x08)         # display apagado mientras se configura
        self.borrar()
        self._comando(0x06)         # despues de cada caracter el cursor avanza a la derecha
        self._comando(0x0C)         # display prendido, sin cursor ni parpadeo

    def _comando(self, valor):
        self._byte(valor, 0)

    def borrar(self):
        self._comando(0x01)
        time.sleep_ms(2)            # borrar es el unico comando lento (~1.5 ms)

    def _nibble(self, valor, rs):
        # Manda la mitad ALTA de `valor` (sus bits 7..4), que caen justo en D7..D4. Son dos bytes
        # en una sola transaccion I2C: el primero con E=1 y el segundo con E=0 -- ese paso de 1 a 0
        # es el que hace que el LCD tome los datos.
        b = (valor & 0xF0) | LUZ | rs
        self.i2c.writeto(self.direccion, bytes((b | E, b)))

    def _byte(self, valor, rs):
        # Un byte completo en modo 4 bits: primero la mitad alta, despues la baja (corrida 4
        # lugares a la izquierda para que tambien caiga en D7..D4).
        self._nibble(valor, rs)
        self._nibble(valor << 4, rs)

    def mover(self, columna, fila):
        # Comando 0x80 = "mover el cursor a esta posicion de memoria". Se le suma donde empieza la
        # fila (ver INICIO_LINEA) mas la columna.
        self._comando(0x80 | (INICIO_LINEA[fila] + columna))

    def escribir(self, texto):
        for c in texto:
            # La tabla de caracteres del LCD coincide con ASCII en lo basico (letras sin tilde,
            # numeros, signos). Cualquier otra cosa (enie, acentos) se muestra como '?'.
            codigo = ord(c)
            self._byte(codigo if 32 <= codigo < 127 else ord('?'), RS)

    def linea(self, fila, texto):
        # Escribe una fila entera, rellenando con espacios hasta las 16 columnas: asi se pisan los
        # caracteres que hubieran quedado de un texto anterior mas largo. Se evita llamar a
        # borrar() antes porque hace parpadear la pantalla.
        self.mover(0, fila)
        self.escribir(texto[:16] + " " * (16 - len(texto)))
