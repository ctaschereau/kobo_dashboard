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
URL="${DASH_URL:-http://192.168.1.135/dashboard.png}"
OUT="$DIR/Dashboard/dashboard.png"
INTERVAL=1800                               # secondes

# fbink : essaie celui de KOReader, sinon dans le PATH
FBINK="/mnt/onboard/.adds/koreader/fbink"
[ -x "$FBINK" ] || FBINK="$(command -v fbink)"

mkdir -p "$(dirname "$OUT")"

fetch() {
    # -f : échoue sur erreur HTTP, -L : suit les redirections
    if curl -fsSL --max-time 30 -o "$OUT.tmp" "$URL"; then
        mv "$OUT.tmp" "$OUT"
        echo "OK : image téléchargée ($(wc -c < "$OUT") octets)"
        return 0
    fi
    echo "ÉCHEC du téléchargement de $URL (wifi ? adresse ? HTTPS ?)" >&2
    rm -f "$OUT.tmp"
    return 1
}

show() {
    if [ -z "$FBINK" ]; then
        echo "fbink introuvable" >&2
        return 1
    fi
    # -f : rafraîchissement complet, -g : affiche une image
    "$FBINK" -f -g file="$OUT"
}

case "$1" in
    show) fetch && show ;;
    loop) while true; do fetch && show; sleep "$INTERVAL"; done ;;
    *)    fetch ;;
esac
