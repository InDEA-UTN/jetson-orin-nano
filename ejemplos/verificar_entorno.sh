#!/usr/bin/env bash
# verificar_entorno.sh — Estado de la Jetson Orin Nano en una sola salida.
#
# Junta los datos que hacen falta para documentar un procedimiento o para reportar un problema:
# versión de Jetson Linux y de JetPack, kernel, modo de energía, medio de arranque, espacio libre,
# cámaras detectadas y presencia de CUDA.
#
# Solo lee información: no instala ni modifica nada. Se puede correr sin sudo (algunas líneas
# quedan vacías si falta el comando correspondiente; eso también es un dato).
#
# Uso:  bash verificar_entorno.sh
# Para guardarlo:  bash verificar_entorno.sh | tee estado_$(date +%F).txt
#
# Probado en: (completar — JetPack x.y.z / L4T xx.y, fecha)

titulo() { printf '\n=== %s ===\n' "$1"; }

# Ejecuta un comando solo si existe; si no, lo dice en vez de fallar.
si_existe() {
    if command -v "$1" >/dev/null 2>&1; then
        "$@"
    else
        echo "($1 no está instalado)"
    fi
}

titulo "Fecha y equipo"
date
echo "hostname: $(hostname)"

titulo "Modelo de la placa"
if [ -r /proc/device-tree/model ]; then
    tr -d '\0' < /proc/device-tree/model
    echo
else
    echo "(no se pudo leer /proc/device-tree/model)"
fi

titulo "Jetson Linux (L4T)"
if [ -r /etc/nv_tegra_release ]; then
    cat /etc/nv_tegra_release
else
    echo "(no existe /etc/nv_tegra_release: ¿este equipo es una Jetson?)"
fi

titulo "Versión de JetPack"
si_existe apt-cache policy nvidia-jetpack

titulo "Paquetes de bootloader y kernel instalados"
si_existe dpkg -l nvidia-l4t-bootloader nvidia-l4t-kernel

titulo "Sistema operativo y kernel"
si_existe lsb_release -d
uname -a

titulo "Modo de energía"
si_existe nvpmodel -q

titulo "CPU, memoria y swap"
si_existe nproc
si_existe free -h

titulo "Medio de arranque y espacio en disco"
findmnt -n -o SOURCE,FSTYPE,SIZE,USED,AVAIL,TARGET / 2>/dev/null || df -h /
echo "--- todos los sistemas de archivos ---"
df -h -x tmpfs -x devtmpfs 2>/dev/null

titulo "Discos detectados (NVMe y microSD)"
si_existe lsblk -o NAME,SIZE,TYPE,MOUNTPOINT

titulo "Temperaturas"
for zona in /sys/devices/virtual/thermal/thermal_zone*; do
    [ -r "$zona/type" ] && [ -r "$zona/temp" ] || continue
    printf '%s: %s °C\n' "$(cat "$zona/type")" "$(awk '{printf "%.1f", $1/1000}' "$zona/temp")"
done

titulo "CUDA"
if [ -x /usr/local/cuda/bin/nvcc ]; then
    /usr/local/cuda/bin/nvcc --version | tail -2
else
    si_existe nvcc --version
fi

titulo "PyTorch y GPU (si hay Python con torch)"
if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
try:
    import torch
    print("torch:", torch.__version__)
    print("cuda disponible:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("dispositivo:", torch.cuda.get_device_name(0))
except ImportError:
    print("(torch no está instalado en este intérprete)")
PY
else
    echo "(python3 no está instalado)"
fi

titulo "Cámaras detectadas"
si_existe v4l2-ctl --list-devices
echo "--- nodos /dev/video* ---"
ls -1 /dev/video* 2>/dev/null || echo "(no hay /dev/video*: la cámara no está detectada)"
echo "--- mensajes del kernel sobre sensores CSI ---"
dmesg 2>/dev/null | grep -iE 'imx[0-9]+|tegra-camrtc|nvcsi' | tail -15 \
    || echo "(sin mensajes, o hace falta sudo para leer dmesg)"

titulo "Red"
ip -brief address 2>/dev/null | grep -v '^lo'

titulo "Docker"
si_existe docker --version

printf '\nListo. Pegá esta salida completa cuando documentes un procedimiento o reportes un problema.\n'
