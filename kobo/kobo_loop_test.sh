#!/bin/sh
# Test : affiche ./Dashboard/dashboard.png en boucle (aucun téléchargement).
# But : vérifier que la Kobo ne s'endort pas pendant que la boucle tourne.
#
# Installation : copier ce script dans un dossier de la Kobo (ex. /mnt/onboard/dash/)
# avec, à côté, un sous-dossier Dashboard/ contenant dashboard.png.
#
# Usage :
#   sh kobo_loop_test.sh        -> rafraîchit toutes les 60 s
#   sh kobo_loop_test.sh 300    -> rafraîchit toutes les 300 s
# Arrêt : Ctrl-C (ou quitter le terminal de KOReader)

DIR="$(cd "$(dirname "$0")" && pwd)"
IMG="$DIR/Dashboard/dashboard.png"
LOG="$DIR/test_loop.log"
INTERVAL="${1:-60}"

. "$DIR/fbink_common.sh"      # PATH élargi + draw_image (choix d'un fbink qui gère les images)

if [ ! -f "$IMG" ]; then
    echo "Image introuvable : $IMG" >&2
    exit 1
fi

echo "Démarrage : $IMG toutes les ${INTERVAL}s (log : $LOG)"
echo "=== Départ $(date '+%Y-%m-%d %H:%M:%S'), intervalle ${INTERVAL}s ===" >> "$LOG"

n=0
while true; do
    n=$((n + 1))
    now="$(date '+%Y-%m-%d %H:%M:%S')"

    # Affiche l'image (-f : rafraîchissement complet), puis un compteur en bas de l'écran
    if draw_image "$IMG"; then
        "$FBINK_USED" -y -1 "#$n  $now"
    else
        echo "Affichage impossible (voir le message ci-dessus)" >&2
    fi

    echo "$n $now" >> "$LOG"
    sleep "$INTERVAL"
done
