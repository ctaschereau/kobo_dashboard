#!/bin/sh
# Télécharge dashboard.png depuis le Raspberry Pi et l'affiche avec fbink.
#
# Installation : copier ce script dans un dossier de la Kobo (ex. /mnt/onboard/dash/).
# L'image est enregistrée à côté du script (dashboard.png), et la boucle tient un
# journal à côté aussi (fetch.log).
#
# Configuration (modifier les valeurs ci-dessous, ou passer des variables) :
#   DASH_URL        adresse de l'image (défaut : celle de l'exemple du README, 192.168.1.135)
#   DASH_INTERVAL   secondes entre deux rafraîchissements en mode loop (défaut : 1800)
#   FBINK           chemin de fbink (défaut : celui du PATH, normalement /usr/bin/fbink)
# Exemple :
#   DASH_URL=http://192.168.1.50/dashboard.png sh kobo_fetch.sh show
#
# Usage :
#   sh kobo_fetch.sh            -> télécharge seulement
#   sh kobo_fetch.sh show       -> télécharge puis affiche
#   sh kobo_fetch.sh loop       -> boucle : télécharge + affiche, et note chaque tour dans fetch.log
# Arrêt de la boucle : Ctrl-C

PATH="$PATH:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"   # le terminal de KOReader a parfois un PATH minimal

DIR="$(cd "$(dirname "$0")" && pwd)"
URL="${DASH_URL:-http://192.168.1.135/dashboard.png}"
INTERVAL="${DASH_INTERVAL:-1800}"
OUT="$DIR/dashboard.png"
LOG="$DIR/fetch.log"
FBINK="${FBINK:-$(command -v fbink)}"

# Télécharge $URL vers le fichier $1 avec le premier outil disponible (HTTP simple, sans TLS).
download() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --max-time 30 -o "$1" "$URL"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -T 30 -O "$1" "$URL"
    elif busybox --list 2>/dev/null | grep -qx wget; then
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
    if [ ! -x "$FBINK" ]; then
        echo "fbink introuvable (voir le README, section Kobo)" >&2
        return 1
    fi
    "$FBINK" -f -g file="$OUT"
}

# Ajoute une ligne horodatée au journal (on garde les 500 dernières lignes).
# Un écart entre deux lignes plus grand que l'intervalle = la Kobo s'est endormie.
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"
    lines=$(wc -l < "$LOG")
    if [ $((lines + 0)) -gt 500 ]; then
        tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
    fi
}

case "$1" in
    show) fetch && show ;;
    loop)
        log "démarrage (intervalle ${INTERVAL}s)"
        while true; do
            if ! fetch; then log "téléchargement échoué"
            elif ! show; then log "affichage échoué"
            else log "ok"
            fi
            sleep "$INTERVAL"
        done
        ;;
    *) fetch ;;
esac
