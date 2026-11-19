"""Lecture d'un calendrier iCal (.ics) et liste des événements du jour.

(Nommé calendar_events.py pour ne pas masquer le module `calendar` de la bibliothèque standard.)
"""
from datetime import date, datetime, timedelta

import requests


def _to_local(value, tz):
    """datetime -> datetime avec fuseau local (les heures « flottantes » sont supposées locales)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def todays_events(ics_url, tz, now):
    """Événements d'aujourd'hui, pas encore terminés, triés.

    Retourne une liste de tuples (libellé, titre) : le libellé est l'heure de début
    (« 08:30 ») ou « Journée » pour un événement sur toute la journée.
    Lève une exception si le calendrier est inaccessible ou illisible.
    """
    # Importées ici : ces bibliothèques ne sont nécessaires que si une URL de calendrier est configurée.
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
            events.append(((1, start), start.strftime("%H:%M"), title))
        elif isinstance(start, date):
            events.append(((0, datetime.min.replace(tzinfo=tz)), "Journée", title))

    events.sort(key=lambda e: e[0])
    return [(label, title) for _, label, title in events]
