# Abecedario de Senas LED - previsualizar la fuente de letras_matriz.py SIN matriz fisica ni Pico.
#
# Iterar contra la matriz real es lento (copiar, correr, mirar los LEDs, volver a Thonny a
# corregir); iterar en la consola es gratis. Este script imprime el sprite de 8x8 que le llegaria
# a la Pico como bloques de texto, para pescar a ojo las letras que no se leen bien antes de
# gastar tiempo probandolas en el hardware.
#
# Uso: python3 ver_letras_matriz.py           -> las 26 letras
#      python3 ver_letras_matriz.py M N W      -> solo esas (para iterar rapido una en particular)

import sys

import letras_matriz

LLENO = "█"
VACIO = "·"


def imprimir(letra):
    sprite = letras_matriz.sprite_de_letra(letra)
    print(f"{letra}:")
    for fila in sprite:
        print("".join(LLENO if bit == "1" else VACIO for bit in fila))
    print()


letras = sys.argv[1:] if len(sys.argv) > 1 else sorted(letras_matriz.FUENTE)
for letra in letras:
    imprimir(letra.upper())
