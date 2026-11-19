#!/bin/sh
# Télécharge dashboard.png depuis le Raspberry Pi et l'affiche avec fbink.
#
# Installation : copier ce script dans un dossier de la Kobo (ex. /mnt/onboard/dash/).
# L'image est enregistrée dans ./Dashboard/dashboard.png, à côté du script.
#
# Configuration : l'adresse par défaut (192.168.1.135) est celle de l'exemple du README.
# Modifiez URL ci-dessous, ou passez la vôtre par la variable DASH_URL :
#   DASH_URL=http://192.168.1.50/dashboard.png sh kobo_fetch.sh show
#
# Usage :
#   sh kobo_fetch.sh            -> télécharge seulement
#   sh kobo_fetch.sh show       -> télécharge puis affiche
#   sh kobo_fetch.sh loop       -> boucle : télécharge + affiche toutes les 30 min
# Arrêt de la boucle : Ctrl-C

DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/fbink_common.sh"      # PATH élargi + draw_image (choix d'un fbink qui gère les images)

URL="${DASH_URL:-http://192.168.1.135/dashboard.png}"
OUT="$DIR/Dashboard/dashboard.png"
INTERVAL=1800                               # secondes

mkdir -p "$(dirname "$OUT")"

# Télécharge $URL vers le fichier $1, avec le premier outil disponible :
# curl, sinon wget, sinon le wget de busybox. (HTTP simple : pas besoin de TLS.)
download() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --max-time 30 -o "$1" "$URL"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -T 30 -O "$1" "$URL"
    elif command -v busybox >/dev/null 2>&1 && busybox --list 2>/dev/null | grep -qx wget; then
        busybox wget -q -T 30 -O "$1" "$URL"
    else
        echo "Aucun outil de téléchargement trouvé (curl, wget, busybox wget)" >&2
        return 1
    fi
}

fetch() {
    if download "$OUT.tmp" && [ -s "$OUT.tmp" ]; then
        mv "$OUT.tmp" "$OUT"
        echo "OK : image téléchargée ($(wc -c < "$OUT") octets)"
        return 0
    fi
    echo "ÉCHEC du téléchargement de $URL (wifi ? adresse ?)" >&2
    rm -f "$OUT.tmp"
    return 1
}

show() {
    draw_image "$OUT"
}

case "$1" in
    show) fetch && show ;;
    loop) while true; do fetch && show; sleep "$INTERVAL"; done ;;
    *)    fetch ;;
esac
