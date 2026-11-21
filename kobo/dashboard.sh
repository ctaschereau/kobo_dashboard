#!/bin/sh
# Lanceur pour KFMon : démarre le tableau de bord quand on ouvre l'icône dans la bibliothèque.
#
# Ce que ça fait :
#   1. vérifie que le réseau fonctionne (en téléchargeant l'image) AVANT de toucher à Nickel :
#      si le wifi est éteint, on tente de l'allumer (si l'outil existe), sinon on affiche un
#      message et on reste dans Nickel, sans rien casser ;
#   2. arrête Nickel (le logiciel Kobo d'origine), qui sinon endormirait la Kobo et
#      redessinerait l'écran par-dessus l'image ;
#   3. lance la boucle de kobo_fetch.sh (téléchargement + affichage) ;
#   4. quand la boucle se termine, redémarre la Kobo, qui revient alors à la normale.
#
# À savoir :
#   - Pour quitter à tout moment : maintenir le bouton d'alimentation enfoncé jusqu'à ce que
#     le voyant clignote rapidement (redémarrage forcé). Ou régler DASH_MAX_LOOPS.
#   - Tout est noté dans launcher.log et fetch.log, à côté de ce script.

DIR="$(cd "$(dirname "$0")" && pwd)"
exec >> "$DIR/launcher.log" 2>&1       # KFMon n'a pas de terminal : tout va dans le journal
PATH="$PATH:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"
FBINK="${FBINK:-$(command -v fbink)}"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') lancement ==="

# Petit message écrit par fbink par-dessus ce que Nickel affiche (rien si fbink manque)
message() {
    [ -x "$FBINK" ] && "$FBINK" -m -y "$1" "$2" >/dev/null 2>&1
}

# 1. Le réseau marche-t-il ? On télécharge l'image tant que Nickel tourne encore.
if ! sh "$DIR/kobo_fetch.sh"; then
    if command -v qndb >/dev/null 2>&1; then
        # Tentative d'allumer le wifi par Nickel lui-même (commande NON vérifiée sur la Mini)
        echo "réseau absent : tentative d'activation du wifi avec qndb"
        qndb -t 15000 -s wmNetworkConnected -m wfmConnectWirelessSilently
        sleep 3
    fi
    if ! sh "$DIR/kobo_fetch.sh"; then
        echo "réseau indisponible : on reste dans Nickel"
        message 10 "Wifi indisponible"
        message 12 "Activez le wifi puis rouvrez l'icone"
        exit 1
    fi
fi

# On note ce que Nickel sait du wifi (interface, module) AVANT de l'arrêter : c'est nécessaire
# pour piloter le wifi sans lui plus tard.
echo "--- environnement de Nickel ---"
pid=$(pidof nickel | cut -d' ' -f1)
if [ -n "$pid" ]; then
    tr '\0' '\n' < "/proc/$pid/environ" | grep -E '^(INTERFACE|WIFI_MODULE|WIFI_MODULE_PATH|PRODUCT|MODEL_NUMBER|PLATFORM)='
else
    echo "(Nickel ne tourne pas)"
fi

# 2. Arrêt de Nickel
sync                                   # évite d'abîmer la base de données de Nickel
# Même liste que le lanceur de KOReader. KFMon, lui, reste en place (et refuse un 2e lancement).
killall -TERM nickel hindenburg sickel fickel fmon 2>/dev/null
sleep 2

echo "--- réseau ---"
ifconfig 2>&1 | head -30               # pour diagnostiquer un problème de wifi

# 3. La boucle
sh "$DIR/kobo_fetch.sh" loop

# 4. Retour à la normale
echo "=== $(date '+%Y-%m-%d %H:%M:%S') boucle terminée, redémarrage ==="
sync
/sbin/reboot
