#!/usr/bin/env python3
"""Génère dashboard.png (600x800, niveaux de gris) pour une Kobo Mini.

Mise en page :
  moitié haute  : météo actuelle (gauche) | habits à mettre (droite)
  moitié basse  : calendrier du jour (gauche) | nouvelles (droite)
Avant midi, les habits sont pour aujourd'hui. Après midi, pour demain.

Dépendances (Raspberry Pi OS) :
    sudo apt install python3-pil python3-requests fonts-dejavu-core
Usage :
    python3 dashboard.py /var/www/html/dashboard.png
Test sans réseau :
    python3 dashboard.py test.png --demo --temp 3 --code 71 --hour 15
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from icons import icon_clothing, icon_weather

# ---------- Configuration ----------
W, H = 600, 800
MID_X, MID_Y = 300, 400
LAT, LON = 45.4042, -71.8929          # Sherbrooke
TZ = "America/Toronto"
# À vérifier : flux RSS de nouvelles en français (liste sur ici.radio-canada.ca/rss)
NEWS_RSS = "https://ici.radio-canada.ca/rss/4159"
NB_TITRES = 2

# Placeholder en attendant le vrai calendrier (.ics)
EVENEMENTS = [
    ("08:30", "Garderie"),
    ("12:00", "Dîner avec Marc"),
    ("17:30", "Souper en famille"),
]

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
HERE = os.path.dirname(os.path.abspath(__file__))
# Polices essayées dans l'ordre (Linux/Pi, puis Windows, puis macOS).
# Astuce : déposer DejaVuSans.ttf et DejaVuSans-Bold.ttf à côté du script les fait choisir en premier.
FONT_CANDIDATES = {
    False: [os.path.join(HERE, "DejaVuSans.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf",
            "arial.ttf", "segoeui.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"],
    True: [os.path.join(HERE, "DejaVuSans-Bold.ttf"),
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf",
           "arialbd.ttf", "segoeuib.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
}


# ---------- Polices et texte ----------
_warned = False


def font(size, bold=False):
    global _warned
    for path in FONT_CANDIDATES[bold]:
        try:
            return ImageFont.truetype(path, int(size))
        except OSError:
            continue
    if not _warned:
        print("ATTENTION : aucune police TrueType trouvée, police de secours "
              "(sans accents ni gras). Installez DejaVu ou copiez DejaVuSans.ttf "
              "à côté du script.", file=sys.stderr)
        _warned = True
    try:
        return ImageFont.load_default(int(size))   # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def fit(d, text, max_w, size, bold=False, min_size=12):
    """Police la plus grande (<= size) qui fait entrer le texte dans max_w."""
    while size > min_size and d.textlength(text, font=font(size, bold)) > max_w:
        size -= 1
    return font(size, bold)


def wrap(d, text, fnt, max_w, max_lines=None):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if d.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and d.textlength(last + "…", font=fnt) > max_w:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


# ---------- Logique météo ----------
def classify(code):
    """Code WMO -> (type d'icône, libellé français)."""
    if code == 0:
        return "sun", "Ciel dégagé"
    if code == 1:
        return "sun", "Surtout dégagé"
    if code == 2:
        return "partly", "Partiellement nuageux"
    if code == 3:
        return "cloud", "Couvert"
    if code in (45, 48):
        return "fog", "Brouillard"
    if code in (51, 53, 55, 56, 57):
        return "rain", "Bruine"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "rain", "Pluie"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow", "Neige"
    if code in (95, 96, 99):
        return "storm", "Orage"
    return "cloud", "Nuageux"


def clothes(ref, tmax, kind, pluie_pct):
    """Liste (icône, libellé) selon la température de référence (°C)."""
    out = []
    if ref >= 20:
        out.append(("tshirt", "T-shirt"))
    else:
        out.append(("coat", "Manteau chaud" if ref < 5 else "Manteau"))
    if ref < -10:
        out.append(("pants", "Pantalon neige"))
    wet = kind in ("rain", "storm") or pluie_pct >= 50
    if ref < 5 or kind == "snow":
        out.append(("boots", "Bottes"))
    elif wet:
        out.append(("boots", "Bottes pluie"))
    if ref < 5:
        out.append(("hat", "Tuque"))
    if ref < 0:
        out.append(("mitts", "Mitaines"))
    if wet and kind != "snow":
        out.append(("umbrella", "Parapluie"))
    if tmax >= 25 and kind in ("sun", "partly"):
        out.append(("sunhat", "Chapeau"))
    return out[:6]


# ---------- Données ----------
def get_weather():
    import requests
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": LAT, "longitude": LON, "timezone": TZ, "forecast_days": 2,
            "current": "temperature_2m,apparent_temperature,weather_code,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                     "precipitation_probability_max",
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def demo_weather(temp, code, night=False):
    return {
        "current": {"temperature_2m": temp, "apparent_temperature": temp - 2,
                    "weather_code": code, "is_day": 0 if night else 1},
        "daily": {
            "weather_code": [code, 61],
            "temperature_2m_max": [temp + 4, temp + 1],
            "temperature_2m_min": [temp - 6, temp - 5],
            "precipitation_probability_max": [20, 70],
        },
    }


def get_headlines():
    try:
        import requests
        r = requests.get(NEWS_RSS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        titres = [i.findtext("title", "").strip() for i in root.iter("item")]
        return [t for t in titres if t][:NB_TITRES]
    except Exception as e:
        print("Nouvelles indisponibles :", e, file=sys.stderr)
        return []


DEMO_NEWS = [
    "Le gouvernement annonce un nouvel investissement dans les transports en commun",
    "Une tempête de neige attendue dans l'Estrie en fin de semaine",
]


# ---------- Dessin ----------
def draw_weather(d, w, now):
    cur, daily = w["current"], w["daily"]
    kind, label = classify(cur["weather_code"])

    # Gauche : icône, libellé, température, min/max
    icon_weather(d, 60, 8, 180, kind, night=not cur.get("is_day", 1))
    d.text((150, 212), label, font=fit(d, label, 280, 26, True), fill=0, anchor="mm")
    temp = f"{round(cur['temperature_2m'])}°"
    d.text((150, 285), temp, font=fit(d, temp, 280, 112, True), fill=0, anchor="mm")
    mm = f"Min {round(daily['temperature_2m_min'][0])}°   Max {round(daily['temperature_2m_max'][0])}°"
    d.text((150, 358), mm, font=fit(d, mm, 280, 28, True), fill=0, anchor="mm")

    # Droite : habits (aujourd'hui avant midi, demain après midi)
    demain = now.hour >= 12
    idx = 1 if demain else 0
    kind_c, _ = classify(daily["weather_code"][idx])
    tmin, tmax = daily["temperature_2m_min"][idx], daily["temperature_2m_max"][idx]
    ref = (tmin + tmax) / 2 if demain else cur["apparent_temperature"]
    items = clothes(ref, tmax, kind_c, daily["precipitation_probability_max"][idx])

    titre = "Habits pour demain" if demain else "Habits pour aujourd'hui"
    d.text((MID_X + 150, 26), titre, font=fit(d, titre, 275, 24, True), fill=0, anchor="mm")
    cell_w, cell_h, top = 140, 112, 52
    for n, (key, lib) in enumerate(items):
        col, row = n % 2, n // 2
        cx = MID_X + 10 + col * cell_w + cell_w // 2 + 5
        cy = top + row * cell_h
        icon_clothing(d, cx - 36, cy + 2, 72, key)
        d.text((cx, cy + 92), lib, font=fit(d, lib, 136, 19, True), fill=0, anchor="mm")


def draw_bottom(d, headlines, now):
    # En-têtes
    d.text((20, 418), "AUJOURD'HUI", font=font(24, True), fill=0)
    d.text((MID_X + 18, 418), "NOUVELLES", font=font(24, True), fill=0)
    d.line((20, 452, MID_X - 15, 452), fill=0, width=3)
    d.line((MID_X + 18, 452, W - 20, 452), fill=0, width=3)

    # Calendrier
    y = 468
    if not EVENEMENTS:
        d.text((20, y), "Rien de prévu", font=font(24), fill=0)
    for heure, titre in EVENEMENTS:
        d.text((20, y), heure, font=font(28, True), fill=0)
        y += 36
        for line in wrap(d, titre, font(24), 265, max_lines=2):
            d.text((20, y), line, font=font(24), fill=0)
            y += 30
        y += 16
        if y > 750:
            break

    # Nouvelles
    y = 468
    if not headlines:
        d.text((MID_X + 18, y), "Nouvelles indisponibles", font=font(20), fill=0)
    for t in headlines:
        for line in wrap(d, t, font(23, True), 262, max_lines=6):
            d.text((MID_X + 18, y), line, font=font(23, True), fill=0)
            y += 30
        y += 18

    d.text((W - 8, H - 4), f"{now:%H:%M}", font=font(13), fill=0, anchor="rd")


def build(out_path, demo=False, temp=-3.0, code=3, hour=None, night=False):
    now = datetime.now()
    if hour is not None:
        now = now.replace(hour=hour)

    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    try:
        w = demo_weather(temp, code, night) if demo else get_weather()
        draw_weather(d, w, now)
    except Exception as e:
        print("Météo indisponible :", e, file=sys.stderr)
        d.text((150, 200), "Météo\nindisponible", font=font(32, True), fill=0,
               anchor="mm", align="center")

    draw_bottom(d, DEMO_NEWS if demo else get_headlines(), now)

    # Séparateurs
    d.line((0, MID_Y, W, MID_Y), fill=0, width=4)
    d.line((MID_X, 14, MID_X, MID_Y - 14), fill=0, width=3)
    d.line((MID_X, MID_Y + 14, MID_X, H - 14), fill=0, width=3)

    img.save(out_path)
    print("Écrit", out_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="dashboard.png")
    ap.add_argument("--demo", action="store_true", help="données fictives, sans réseau")
    ap.add_argument("--temp", type=float, default=-3.0)
    ap.add_argument("--code", type=int, default=3, help="code météo WMO")
    ap.add_argument("--night", action="store_true", help="forcer la nuit (test)")
    ap.add_argument("--hour", type=int, default=None, help="forcer l'heure (test)")
    a = ap.parse_args()
    build(a.out, a.demo, a.temp, a.code, a.hour, a.night)
