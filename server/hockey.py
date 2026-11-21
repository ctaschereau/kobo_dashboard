"""Résultat de la veille d'une équipe de la LNH.

Source : l'API publique de la LNH (api-web.nhle.com, sans clé) :
    GET /v1/score/AAAA-MM-JJ  ->  {"games": [{"gameState", "homeTeam": {"abbrev", "score"},
                                               "awayTeam": {...}, "periodDescriptor": {"periodType"}}]}
Elle n'est pas documentée officiellement (les points d'accès sont ceux du site nhl.com).
"""
from datetime import timedelta

import requests

API = "https://api-web.nhle.com/v1/score/{date}"

# États d'un match terminé (« OFF » est celui que renvoie l'API ; « FINAL » par prudence)
FINIS = ("OFF", "FINAL")

# Noms affichés. Les Canadiens, les Rangers et les Islanders par leur surnom : « New York »
# serait ambigu.
NOMS = {
    "ANA": "Anaheim", "BOS": "Boston", "BUF": "Buffalo", "CGY": "Calgary", "CAR": "Caroline",
    "CHI": "Chicago", "COL": "Colorado", "CBJ": "Columbus", "DAL": "Dallas", "DET": "Détroit",
    "EDM": "Edmonton", "FLA": "Floride", "LAK": "Los Angeles", "MIN": "Minnesota",
    "MTL": "Canadiens", "NSH": "Nashville", "NJD": "New Jersey", "NYI": "Islanders",
    "NYR": "Rangers", "OTT": "Ottawa", "PHI": "Philadelphie", "PIT": "Pittsburgh",
    "SEA": "Seattle", "SJS": "San Jose", "STL": "St. Louis", "TBL": "Tampa Bay",
    "TOR": "Toronto", "UTA": "Utah", "VAN": "Vancouver", "VGK": "Vegas", "WPG": "Winnipeg",
    "WSH": "Washington",
}

SUITES = {"OT": "Prolongation", "SO": "Fusillade"}


def _nom(equipe):
    """Nom à afficher : notre table, sinon le nom donné par l'API, sinon l'abréviation."""
    abbrev = equipe.get("abbrev", "?")
    if abbrev in NOMS:
        return NOMS[abbrev]
    nom = equipe.get("name")
    if isinstance(nom, dict):
        nom = nom.get("default")
    return nom or abbrev


def yesterdays_game(team, now):
    """Résultat du match terminé de `team` (abréviation LNH) la veille de `now`, ou None.

    Retourne {"lignes": [(notre équipe, buts), (adversaire, buts)], "suite": "Prolongation"|
    "Fusillade"|""}. `now` est un datetime avec fuseau : « la veille » suit la date locale.
    """
    jour = (now - timedelta(days=1)).date()
    r = requests.get(API.format(date=jour.isoformat()), timeout=15)
    r.raise_for_status()
    for g in r.json().get("games", []):
        home, away = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        if team not in (home.get("abbrev"), away.get("abbrev")):
            continue
        if g.get("gameState") not in FINIS:
            continue                                    # reporté, pas encore joué, en cours
        if home.get("score") is None or away.get("score") is None:
            continue
        nous, eux = (home, away) if home.get("abbrev") == team else (away, home)
        periode = (g.get("periodDescriptor") or {}).get("periodType", "REG")
        return {
            "lignes": [(_nom(nous), int(nous["score"])), (_nom(eux), int(eux["score"]))],
            "suite": SUITES.get(periode, ""),
        }
    return None
