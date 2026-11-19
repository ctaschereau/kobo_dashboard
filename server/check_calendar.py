#!/usr/bin/env python3
"""Diagnostic du calendrier : montre ce que contient l'adresse .ics configurée et
pourquoi les événements sont (ou ne sont pas) affichés sur l'image.

Lit l'URL dans config.ini ([calendar] ics_url). N'écrit rien et n'affiche jamais l'URL
complète (elle est secrète) : seulement le nom du serveur.

Usage :
    python3 server/check_calendar.py
    python3 server/check_calendar.py --config /autre/config.ini
"""
import argparse
import importlib.metadata as md
import platform
import sys
from datetime import date, datetime, timedelta

import requests

from calendar_events import _to_local, todays_events
from config import load_config

JOURS_A_VOIR = 7


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=None, help="chemin de config.ini")
    a = ap.parse_args()

    cfg = load_config(a.config)
    if not cfg.calendar_url:
        print("Aucune adresse de calendrier : [calendar] ics_url est vide dans config.ini.")
        return 1

    import icalendar
    import recurring_ical_events

    now = datetime.now(cfg.tz)
    url = cfg.calendar_url.replace("webcal://", "https://", 1)
    host = url.split("/")[2] if "//" in url else "?"

    print(f"Python {platform.python_version()} | icalendar {md.version('icalendar')} | "
          f"recurring-ical-events {md.version('recurring-ical-events')}")
    print(f"Maintenant : {now:%Y-%m-%d %H:%M} ({cfg.timezone})")
    print(f"Serveur du calendrier : {host}")

    # 1. Téléchargement
    r = requests.get(url, timeout=30)
    print(f"Réponse HTTP : {r.status_code}, {len(r.content)} octets, "
          f"type {r.headers.get('Content-Type', '?')}")
    r.raise_for_status()
    if not r.content.lstrip().startswith(b"BEGIN:VCALENDAR"):
        print("Ce n'est PAS un fichier iCal. Début de la réponse :")
        print(r.content[:150])
        return 1

    # 2. Contenu du fichier
    cal = icalendar.Calendar.from_ical(r.content)
    print(f"Événements dans le fichier : {len(cal.walk('VEVENT'))}")
    print(f"Fuseau déclaré par le calendrier : {cal.get('X-WR-TIMEZONE', '(aucun)')}")

    # 3. Les prochains jours, tels que la bibliothèque les voit
    debut = datetime.combine(now.date(), datetime.min.time(), tzinfo=cfg.tz)
    fin = debut + timedelta(days=JOURS_A_VOIR)
    evs = recurring_ical_events.of(cal).between(debut, fin)
    print(f"\nÉvénements des {JOURS_A_VOIR} prochains jours (aujourd'hui compris) : {len(evs)}")
    lignes = []
    for ev in evs:
        start = ev.get("DTSTART").dt
        end_prop = ev.get("DTEND")
        end = end_prop.dt if end_prop is not None else None
        titre = str(ev.get("SUMMARY", "(sans titre)")).strip()
        statut = str(ev.get("STATUS", "")).upper()
        if isinstance(start, datetime):
            s = _to_local(start, cfg.tz)
            e = _to_local(end, cfg.tz) if isinstance(end, datetime) else None
            quand = f"{s:%a %d %b %H:%M}" + (f" -> {e:%H:%M}" if e else "")
            cle = s
        else:
            quand = f"{start:%a %d %b} (journée)"
            cle = datetime.combine(start, datetime.min.time(), tzinfo=cfg.tz)
        lignes.append((cle, f"  {quand}  {titre}" + (f"  [{statut}]" if statut else "")))
    for _, ligne in sorted(lignes):
        print(ligne)
    if not lignes:
        print("  (aucun : le fichier n'a rien pour cette période)")

    # 4. Ce que l'image affichera
    print("\nAffiché sur l'image (événements d'aujourd'hui pas encore terminés) :")
    res = todays_events(cfg.calendar_url, cfg.tz, now)
    if res:
        for label, titre in res:
            print(f"  {label}  {titre}")
    else:
        print("  (rien -> l'image affiche « Rien de prévu »)")
        auj = [l for c, l in sorted(lignes) if c.date() == now.date()]
        if auj:
            print("  Il y a pourtant des événements aujourd'hui : ils sont déjà terminés.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
