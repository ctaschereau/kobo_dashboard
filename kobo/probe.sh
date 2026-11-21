#!/bin/sh
# Diagnostic en LECTURE SEULE : rassemble ce qu'il faut savoir sur cette Kobo pour économiser la
# batterie (veille, réveil par l'horloge, wifi). Ne modifie rien, ne met pas la Kobo en veille.
#
# À lancer dans le terminal de KOReader :
#   sh /mnt/onboard/.adds/dash/probe.sh
# Le résultat est écrit dans probe.txt, à côté du script (relisez-le avant de le partager :
# il contient les adresses réseau de la Kobo).

DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/probe.txt"
PATH="$PATH:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"

{
echo "== système =="
uname -a
cat /mnt/onboard/.kobo/version 2>/dev/null

echo; echo "== batterie =="
for d in /sys/class/power_supply/*; do
    echo "$d : capacité=$(cat "$d/capacity" 2>/dev/null) état=$(cat "$d/status" 2>/dev/null) courant=$(cat "$d/current_now" 2>/dev/null)"
done

echo; echo "== veille et réveil par l'horloge (RTC) =="
echo "états possibles (/sys/power/state) : $(cat /sys/power/state 2>&1)"
echo "state-extended : $(cat /sys/power/state-extended 2>&1)"
ls -la /sys/power/ 2>&1
ls -la /sys/class/rtc/ 2>&1
ls -la /sys/class/rtc/rtc0/ 2>&1
echo "wakealarm : $(cat /sys/class/rtc/rtc0/wakealarm 2>&1)"
echo "date système : $(date '+%Y-%m-%d %H:%M:%S')  /  horloge matérielle : $(hwclock -r 2>&1)"
command -v rtcwake >/dev/null 2>&1 && echo "rtcwake : $(command -v rtcwake)" || echo "rtcwake : absent"

echo; echo "== wifi =="
echo "interfaces :"; ifconfig 2>&1 | head -20
echo "modules chargés :"; lsmod 2>&1 | head -20
echo "scripts wifi de KOReader :"
ls -la /mnt/onboard/.adds/koreader/*wifi* /mnt/onboard/.adds/koreader/*-ip.sh 2>&1
echo "outils : $(for t in wpa_supplicant wpa_cli dhcpcd udhcpc iwconfig; do command -v $t >/dev/null 2>&1 && printf '%s ' $t; done)"

echo; echo "== environnement de Nickel (seulement s'il tourne) =="
pid=$(pidof nickel | cut -d' ' -f1)
if [ -n "$pid" ]; then
    tr '\0' '\n' < "/proc/$pid/environ" | grep -E '^(INTERFACE|WIFI_MODULE|WIFI_MODULE_PATH|PRODUCT|MODEL_NUMBER|PLATFORM)='
else
    echo "(Nickel ne tourne pas : normal dans le terminal de KOReader. Voir launcher.log)"
fi

echo; echo "== processus en cours =="
ps 2>&1 | head -40

echo; echo "== journaux du lanceur et de la boucle (30 dernières lignes) =="
echo "--- launcher.log"; tail -30 "$DIR/launcher.log" 2>&1
echo "--- fetch.log";    tail -30 "$DIR/fetch.log" 2>&1
} > "$OUT" 2>&1

echo "Diagnostic écrit dans $OUT"
