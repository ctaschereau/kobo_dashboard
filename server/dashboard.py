#!/usr/bin/env python3
"""Génère dashboard.png (600x800, niveaux de gris) pour une Kobo Mini.

Mise en page :
  bandeau       : titre (gauche) | date et heure de mise à jour (droite)
  bloc météo    : météo actuelle (gauche) | habits à mettre (droite)
  bloc du bas   : calendrier du jour, tous les calendriers fusionnés (gauche) | nouvelle (droite)
Avant midi, les habits sont pour aujourd'hui. Après midi, pour demain.

Message : si message.txt (à la racine du projet) contient un message non expiré, il prend toute
la colonne de droite (habits, hockey et nouvelles disparaissent). Voir server/message.py.

Configuration : config.ini à la racine du projet (voir config.example.ini).
Image produite : output/dashboard.png (dans le dossier du projet) par défaut.

Usage :
    python3 server/dashboard.py
    python3 server/dashboard.py --config /autre/config.ini
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from PIL import Image, ImageDraw

from calendar_events import todays_events
from config import DEFAULT_OUTPUT, load_config
from draw_utils import fit, font, serif_font, wrap
from hockey import yesterdays_game
from icons import icon_clothing, icon_weather
from message import current_message

# ---------- Mise en page ----------
W, H = 600, 800
MID_X = 300                       # séparateur vertical (gauche | droite)
HEADER_H = 54                     # bandeau du titre
WEATHER_H = 400                   # bloc météo
MID_Y = HEADER_H + WEATHER_H      # séparateur horizontal météo / bas
BOTTOM_TOP = MID_Y + 4            # début du bloc du bas
BOTTOM_H = H - BOTTOM_TOP         # hauteur du bloc du bas

MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.",
               "août", "sept.", "oct.", "nov.", "déc."]


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
def get_weather(cfg):
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": cfg.latitude, "longitude": cfg.longitude,
            "timezone": cfg.timezone, "forecast_days": 2,
            "current": "temperature_2m,apparent_temperature,weather_code,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                     "precipitation_probability_max",
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_headlines(cfg):
    r = requests.get(cfg.news_url, timeout=15)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    titres = [i.findtext("title", "").strip() for i in root.iter("item")]
    return [t for t in titres if t][:cfg.news_count]


def collect(cfg, now):
    """Rassemble les données. Pour les nouvelles et le calendrier, une chaîne
    de caractères signifie « message à afficher à la place » (non configuré, erreur).

    Si un message libre est actif (message.txt), la colonne de droite lui est réservée :
    on ne va donc pas chercher les nouvelles ni le hockey.
    """
    try:
        weather = get_weather(cfg)
    except Exception as e:
        print("Météo indisponible :", e, file=sys.stderr)
        weather = None

    try:
        message = current_message(now)
    except Exception as e:                      # un message illisible ne doit jamais bloquer l'image
        print("Message indisponible :", e, file=sys.stderr)
        message = None

    headlines = None
    if message:
        pass
    elif not cfg.news_url:
        headlines = "Nouvelles non configurées"
    else:
        try:
            headlines = get_headlines(cfg) or "Aucune nouvelle"
        except Exception as e:
            print("Nouvelles indisponibles :", e, file=sys.stderr)
            headlines = "Nouvelles indisponibles"

    cal_failed = 0                              # nombre de calendriers qu'on n'a pas pu lire
    if not cfg.calendar_url:
        events = "Calendrier non configuré"
    else:
        try:
            events, cal_failed = todays_events(cfg.calendar_urls, cfg.tz, now)
        except Exception as e:
            print("Calendrier indisponible :", e, file=sys.stderr)
            events = "Calendrier indisponible"

    game = None
    if cfg.team and not message:
        try:
            game = yesterdays_game(cfg.team, now)
        except Exception as e:                  # le hockey est facultatif : jamais bloquant
            print("Résultat de hockey indisponible :", e, file=sys.stderr)

    return weather, headlines, events, game, message, cal_failed


# ---------- Dessin ----------
def draw_weather(d, w, now, with_clothes=True):
    """Météo actuelle (gauche) et habits (droite). Sans les habits : la droite est réservée au message."""
    cur, daily = w["current"], w["daily"]
    kind, label = classify(cur["weather_code"])

    # Gauche : icône, libellé, température, min/max
    icon_weather(d, 60, 8, 180, kind, night=not cur.get("is_day", 1))
    d.text((150, 212), label, font=fit(d, label, 280, 26, True), fill=0, anchor="mm")
    temp = f"{round(cur['temperature_2m'])}°"
    d.text((150, 285), temp, font=fit(d, temp, 280, 112, True), fill=0, anchor="mm")
    mm = f"Min {round(daily['temperature_2m_min'][0])}°   Max {round(daily['temperature_2m_max'][0])}°"
    d.text((150, 358), mm, font=fit(d, mm, 280, 28, True), fill=0, anchor="mm")

    if not with_clothes:
        return

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


def draw_header(d, title, now):
    """Bandeau du haut : titre à gauche, date/heure de mise à jour (petit) à droite."""
    stamp1 = "Mis à jour"
    stamp2 = f"{now.day} {MOIS_COURTS[now.month - 1]} à {now:%H:%M}"
    f1, f2 = font(14), fit(d, stamp2, 150, 17, min_size=11)
    stamp_w = max(d.textlength(stamp1, font=f1), d.textlength(stamp2, font=f2))
    d.text((W - 20, 16), stamp1, font=f1, fill=0, anchor="rm")
    d.text((W - 20, 36), stamp2, font=f2, fill=0, anchor="rm")
    d.text((20, 26), title, font=fit(d, title, W - 40 - stamp_w - 16, 36, True),
           fill=0, anchor="lm")


def draw_calendar(d, events, failed=0):
    """Calendrier du jour (coordonnées locales au bloc du bas).

    `failed` : nombre de calendriers inaccessibles. Les autres s'affichent quand même, mais une
    petite note en bas évite de croire qu'il n'y a rien de prévu.
    """
    if failed:
        note = f"{failed} calendrier{'s' if failed > 1 else ''} inaccessible{'s' if failed > 1 else ''}"
        d.text((20, BOTTOM_H - 30), note, font=font(17), fill=0)
    _draw_events(d, events, BOTTOM_H - 8 - (30 if failed else 0))


def _draw_events(d, events, bottom):
    x, y, max_w = 20, 52, 265
    if isinstance(events, str):                       # message (non configuré, erreur)
        for line in wrap(d, events, font(22), max_w):
            d.text((x, y), line, font=font(22), fill=0)
            y += 29
        return
    if not events:
        d.text((x, y), "Rien de prévu", font=font(24), fill=0)
        return
    for n, (label, titre) in enumerate(events):
        lines = wrap(d, titre, font(22), max_w, max_lines=2)
        needed = 30 + 26 * len(lines) + 12
        reserve = 28 if n < len(events) - 1 else 0    # place pour « + N autres »
        if y + needed + reserve > bottom:
            reste = len(events) - n
            d.text((x, y), f"+ {reste} autre{'s' if reste > 1 else ''}", font=font(22, True), fill=0)
            return
        d.text((x, y), label, font=fit(d, label, max_w, 26, True), fill=0)
        y += 30
        for line in lines:
            d.text((x, y), line, font=font(22), fill=0)
            y += 26
        y += 12


def draw_game(d, game, x, y, max_w=262):
    """Résultat de la veille : deux lignes (le gagnant en gras). Retourne le y suivant."""
    (_, s1), (_, s2) = game["lignes"]
    gagnant = 0 if s1 > s2 else 1
    for i, (nom, score) in enumerate(game["lignes"]):
        texte = f"{nom} : {score}"
        d.text((x, y), texte, font=fit(d, texte, max_w, 26, i == gagnant), fill=0)
        y += 32
    if game["suite"]:
        d.text((x, y), game["suite"], font=font(18), fill=0)
        y += 24
    return y


def draw_news(d, headlines, top=52):
    """Manchettes en police normale, autant que la place le permet (bloc du bas)."""
    x, y, max_w, bottom = MID_X + 18, top, 262, BOTTOM_H - 8
    if isinstance(headlines, str):
        for line in wrap(d, headlines, font(22), max_w):
            d.text((x, y), line, font=font(22), fill=0)
            y += 29
        return
    for t in headlines:
        dispo = (bottom - y) // 30
        if dispo < 1:
            break
        for line in wrap(d, t, font(23), max_w, max_lines=min(dispo, 8)):
            d.text((x, y), line, font=font(23), fill=0)
            y += 30
        y += 16


def _wrap_paragraphs(d, text, fnt, max_w):
    """Découpe le texte en lignes en gardant les retours à la ligne (ligne vide = espace)."""
    lines = []
    for para in text.split("\n"):
        lines.extend(wrap(d, para, fnt, max_w) or [""])
    return lines


def draw_message(d, message):
    """Message libre : toute la colonne de droite, sous le bandeau, avec la plus grande police
    (44 à 18 px) qui fait tenir le texte. Dessiné directement sur l'image finale."""
    x, max_w = MID_X + 18, W - 20 - (MID_X + 18)
    top, bottom = HEADER_H + 16, H - 24

    # Titre « MESSAGE » : gros, en police à empattements, souligné
    size = 48
    while size > 24 and d.textlength("MESSAGE", font=serif_font(size)) > max_w:
        size -= 2
    d.text((x, top), "MESSAGE", font=serif_font(size), fill=0)
    ligne_y = top + int(size * 1.25)
    d.line((x, ligne_y, W - 20, ligne_y), fill=0, width=4)
    top = ligne_y + 18
    max_h = bottom - top

    for size in range(44, 17, -2):
        fnt, lh = font(size), int(size * 1.3)
        lines = _wrap_paragraphs(d, message, fnt, max_w)
        if len(lines) * lh <= max_h:
            break
    else:                                             # trop long même en petit : on tronque avec « … »
        fnt, lh = font(18), int(18 * 1.3)
        lines = _wrap_paragraphs(d, message, fnt, max_w)[:max(1, max_h // lh)]
        last = lines[-1]
        while last and d.textlength(last + "…", font=fnt) > max_w:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"

    y = top
    for line in lines:
        d.text((x, y), line, font=fnt, fill=0)
        y += lh


def render(weather, headlines, events, game, now, title="Panneau Castor", message=None, cal_failed=0):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    draw_header(d, title, now)

    # Bloc météo : dessiné dans sa propre image, puis collé sous le bandeau
    wb = Image.new("L", (W, WEATHER_H), 255)
    dw = ImageDraw.Draw(wb)
    if weather is not None:
        draw_weather(dw, weather, now, with_clothes=not message)
    else:
        dw.text((150, 200), "Météo\nindisponible", font=font(32, True), fill=0,
                anchor="mm", align="center")
    img.paste(wb, (0, HEADER_H))

    # Bloc du bas : calendrier | nouvelles (ou message libre, dessiné plus bas)
    bb = Image.new("L", (W, BOTTOM_H), 255)
    db = ImageDraw.Draw(bb)
    xr = MID_X + 18                                   # colonne de droite
    db.text((20, 10), "AUJOURD'HUI", font=font(22, True), fill=0)
    db.line((20, 40, MID_X - 15, 40), fill=0, width=3)
    draw_calendar(db, events, cal_failed)
    if message:
        pass                                          # la colonne de droite est dessinée après le collage
    elif game:                                          # « Hier » au-dessus des nouvelles
        db.text((xr, 10), "HIER", font=font(22, True), fill=0)
        db.line((xr, 40, W - 20, 40), fill=0, width=3)
        y = draw_game(db, game, xr, 52) + 10
        db.text((xr, y), "NOUVELLES", font=font(22, True), fill=0)
        db.line((xr, y + 30, W - 20, y + 30), fill=0, width=3)
        draw_news(db, headlines, y + 42)
    else:
        db.text((xr, 10), "NOUVELLES", font=font(22, True), fill=0)
        db.line((xr, 40, W - 20, 40), fill=0, width=3)
        draw_news(db, headlines)
    img.paste(bb, (0, BOTTOM_TOP))

    # Séparateurs
    d.line((0, HEADER_H - 2, W, HEADER_H - 2), fill=0, width=4)
    if message:                                       # la colonne de droite ne fait qu'un seul bloc
        d.line((0, MID_Y, MID_X, MID_Y), fill=0, width=4)
        d.line((MID_X, HEADER_H + 14, MID_X, H - 14), fill=0, width=3)
        draw_message(d, message)
    else:
        d.line((0, MID_Y, W, MID_Y), fill=0, width=4)
        d.line((MID_X, HEADER_H + 14, MID_X, MID_Y - 14), fill=0, width=3)
        d.line((MID_X, MID_Y + 14, MID_X, H - 14), fill=0, width=3)
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=None, help="chemin de config.ini")
    a = ap.parse_args()

    cfg = load_config(a.config)
    now = datetime.now(cfg.tz)
    weather, headlines, events, game, message, cal_failed = collect(cfg, now)
    img = render(weather, headlines, events, game, now, cfg.title, message, cal_failed)

    os.makedirs(os.path.dirname(DEFAULT_OUTPUT), exist_ok=True)
    tmp = DEFAULT_OUTPUT + ".tmp"
    img.save(tmp, format="PNG")
    os.replace(tmp, DEFAULT_OUTPUT)   # écriture atomique : nginx ne sert jamais un fichier à moitié écrit
    print("Écrit", DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()
