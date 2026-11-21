#!/bin/sh
# Télécharge dashboard.png depuis le Raspberry Pi et l'affiche avec fbink.
#
# Installation : copier ce script dans un dossier de la Kobo (ex. /mnt/onboard/.adds/dash/).
# L'image est enregistrée à côté du script (dashboard.png), et la boucle tient un
# journal à côté aussi (fetch.log).
#
# Réglages : fichier « dashboard.conf » à côté du script (modèle : dashboard.conf.example).
# Des variables d'environnement de même nom, si elles sont définies, priment sur le fichier :
#   DASH_URL         adresse de l'image (défaut : celle de l'exemple du README, 192.168.1.135)
#   DASH_INTERVAL    secondes entre deux rafraîchissements en mode loop (défaut : 1800)
#   DASH_MAX_LOOPS   nombre de tours avant d'arrêter la boucle, 0 = sans fin (défaut : 0)
#   FBINK            chemin de fbink (défaut : celui du PATH, normalement /usr/bin/fbink)
# Exemple :
#   DASH_INTERVAL=300 sh kobo_fetch.sh loop
#
# Usage :
#   sh kobo_fetch.sh            -> télécharge seulement
#   sh kobo_fetch.sh show       -> télécharge puis affiche
#   sh kobo_fetch.sh loop       -> boucle : télécharge + affiche, et note chaque tour dans fetch.log
# Arrêt de la boucle : Ctrl-C

PATH="$PATH:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"   # le terminal de KOReader a parfois un PATH minimal

DIR="$(cd "$(dirname "$0")" && pwd)"

# Réglages : dashboard.conf, puis les variables d'environnement par-dessus
_url="$DASH_URL"; _interval="$DASH_INTERVAL"; _max="$DASH_MAX_LOOPS"
[ -f "$DIR/dashboard.conf" ] && . "$DIR/dashboard.conf"
[ -n "$_url" ] && DASH_URL="$_url"
[ -n "$_interval" ] && DASH_INTERVAL="$_interval"
[ -n "$_max" ] && DASH_MAX_LOOPS="$_max"

URL="${DASH_URL:-http://192.168.1.135/dashboard.png}"
INTERVAL="${DASH_INTERVAL:-1800}"
MAX_LOOPS="${DASH_MAX_LOOPS:-0}"
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

# Niveau de batterie (ex. « 83% »), ou « ? » si introuvable : permet de mesurer la consommation.
battery() {
    for f in /sys/class/power_supply/*/capacity; do
        if [ -r "$f" ]; then echo "$(cat "$f")%"; return; fi
    done
    echo "?"
}

# Ajoute une ligne horodatée au journal (on garde les 500 dernières lignes).
# Un écart entre deux lignes plus grand que l'intervalle = la Kobo s'est endormie.
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $* [batterie $(battery)]" >> "$LOG"
    lines=$(wc -l < "$LOG")
    if [ $((lines + 0)) -gt 500 ]; then
        tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
    fi
}

case "$1" in
    show) fetch && show ;;
    loop)
        log "démarrage (intervalle ${INTERVAL}s, tours max : ${MAX_LOOPS})"
        n=0
        while true; do
            # Les messages vont dans le journal, pas dans le terminal : un terminal qui
            # affiche du texte redessine l'écran et abîme l'image.
            if ! fetch >> "$LOG" 2>&1; then log "téléchargement échoué"
            elif ! show >> "$LOG" 2>&1; then log "affichage échoué"
            else log "ok"
            fi
            n=$((n + 1))
            if [ "$MAX_LOOPS" -gt 0 ] && [ "$n" -ge "$MAX_LOOPS" ]; then
                log "nombre de tours atteint ($MAX_LOOPS), fin de la boucle"
                break
            fi
            sleep "$INTERVAL"
        done
        ;;
    *) fetch ;;
esac
