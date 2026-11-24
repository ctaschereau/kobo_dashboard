"""Lecture de calendriers iCal (.ics) et liste des événements du jour.

Plusieurs calendriers peuvent être combinés : les événements sont fusionnés dans une seule
liste triée, sans indiquer de quel calendrier ils viennent. Deux événements qui commencent
à la même heure (ou qui sont tous deux sur toute la journée) avec le même titre ne comptent
que pour un.

(Nommé calendar_events.py pour ne pas masquer le module `calendar` de la bibliothèque standard.)
"""
import sys
from datetime import date, datetime, timedelta

import requests


def _to_local(value, tz):
    """datetime -> datetime avec fuseau local (les heures « flottantes » sont supposées locales)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def _host(url):
    """Nom du serveur seulement : l'adresse complète d'un calendrier est secrète."""
    return url.split("/")[2] if "//" in url else "?"


def _titre_cle(titre):
    """Titre normalisé pour comparer : sans différence de majuscules ni d'espaces."""
    return " ".join(titre.split()).casefold()


def _fetch_events(ics_url, tz, now):
    """Événements d'aujourd'hui, pas encore terminés, d'UN calendrier.

    Retourne une liste de tuples (groupe, début, libellé, titre) : groupe 0 = toute la journée
    (affiché en premier), 1 = avec heure. Lève une exception si le calendrier est inaccessible
    ou illisible.
    """
    # Importées ici : ces bibliothèques ne sont nécessaires que si un calendrier est configuré.
    import icalendar
    import recurring_ical_events

    url = ics_url.replace("webcal://", "https://", 1)
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    cal = icalendar.Calendar.from_ical(r.content)

    day_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    events = []
    for ev in recurring_ical_events.of(cal).between(day_start, day_end):
        if str(ev.get("STATUS", "")).upper() == "CANCELLED":
            continue
        title = str(ev.get("SUMMARY", "")).strip() or "(sans titre)"
        start = ev.get("DTSTART").dt
        end_prop = ev.get("DTEND")
        end = end_prop.dt if end_prop is not None else None

        if isinstance(start, datetime):
            start = _to_local(start, tz)
            end = _to_local(end, tz) if isinstance(end, datetime) else None
            if start >= day_end or (end and end <= day_start):
                continue                      # hors de la journée
            if end and end <= now:
                continue                      # déjà terminé
            events.append((1, start, start.strftime("%H:%M"), title))
        elif isinstance(start, date):
            events.append((0, datetime.min.replace(tzinfo=tz), "Journée", title))
    return events


def todays_events(ics_urls, tz, now):
    """Événements d'aujourd'hui, pas encore terminés, de tous les calendriers, fusionnés et triés.

    `ics_urls` : une adresse, ou une liste d'adresses (une chaîne est séparée sur les espaces
    et les sauts de ligne).

    Retourne (événements, échecs) : `événements` est une liste de tuples (libellé, titre), où le
    libellé est l'heure de début (« 08:30 ») ou « Journée » ; `échecs` est le nombre de calendriers
    qu'on n'a pas pu lire. Un calendrier en panne n'empêche pas d'afficher les autres : on ne lève
    une exception que si AUCUN n'a pu être lu.
    """
    urls = ics_urls.split() if isinstance(ics_urls, str) else list(ics_urls)
    merged, failed, last_error = {}, 0, None
    for n, url in enumerate(urls, 1):
        try:
            found = _fetch_events(url, tz, now)
        except Exception as e:
            failed += 1
            last_error = e
            if len(urls) > 1:                 # avec un seul calendrier, l'appelant affiche l'erreur
                print(f"Calendrier {n}/{len(urls)} ({_host(url)}) indisponible : {e}",
                      file=sys.stderr)
            continue
        for groupe, start, label, title in found:
            # Même heure + même titre = même événement : on garde le premier rencontré.
            merged.setdefault((groupe, start, _titre_cle(title)), (label, title))

    if urls and failed == len(urls):
        raise last_error
    return [merged[k] for k in sorted(merged)], failed
