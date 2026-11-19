#!/bin/sh
# Lanceur pour KFMon : démarre le tableau de bord quand on ouvre l'icône dans la bibliothèque.
#
# Ce que ça fait :
#   1. arrête Nickel (le logiciel Kobo d'origine), qui sinon endormirait la Kobo et
#      redessinerait l'écran par-dessus l'image ;
#   2. lance la boucle de kobo_fetch.sh (téléchargement + affichage) ;
#   3. quand la boucle se termine, redémarre la Kobo, qui revient alors à la normale.
#
# À savoir :
#   - Activez le wifi AVANT d'ouvrir l'icône : il reste actif quand Nickel est arrêté.
#   - Pour quitter à tout moment : maintenir le bouton d'alimentation enfoncé jusqu'à ce que
#     le voyant clignote rapidement (redémarrage forcé). Ou régler DASH_MAX_LOOPS.
#   - Tout est noté dans launcher.log et fetch.log, à côté de ce script.

DIR="$(cd "$(dirname "$0")" && pwd)"
exec >> "$DIR/launcher.log" 2>&1       # KFMon n'a pas de terminal : tout va dans le journal

echo "=== $(date '+%Y-%m-%d %H:%M:%S') lancement ==="

sync                                   # évite d'abîmer la base de données de Nickel
# Même liste que le lanceur de KOReader. KFMon, lui, reste en place (et refuse un 2e lancement).
killall -TERM nickel hindenburg sickel fickel fmon 2>/dev/null
sleep 2

echo "--- réseau ---"
ifconfig 2>&1 | head -30               # pour diagnostiquer un problème de wifi

sh "$DIR/kobo_fetch.sh" loop

echo "=== $(date '+%Y-%m-%d %H:%M:%S') boucle terminée, redémarrage ==="
sync
/sbin/reboot
