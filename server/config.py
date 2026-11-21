"""Chargement de la configuration (config.ini, non versionné).

Le fichier est cherché à la racine du projet. Copier config.example.ini vers
config.ini, puis l'adapter.
"""
import configparser
import os
from dataclasses import dataclass

# zoneinfo est dans la bibliothèque standard depuis Python 3.9. Sur Python 3.7/3.8 (par ex. un
# vieux Raspberry Pi OS), il faut le paquet de remplacement : pip install backports.zoneinfo
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError:
        raise SystemExit(
            "Le module zoneinfo est introuvable (il faut Python 3.9 ou plus).\n"
            "Sur Python 3.7 ou 3.8, installez le paquet de remplacement :\n"
            "    pip install backports.zoneinfo"
        )

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config.ini")
DEFAULT_OUTPUT = os.path.join(ROOT, "output", "dashboard.png")


@dataclass
class Config:
    latitude: float
    longitude: float
    timezone: str
    news_url: str       # vide = nouvelles non configurées
    news_count: int
    calendar_url: str   # vide = calendrier non configuré
    title: str = "Panneau Castor"   # titre affiché en haut de l'image
    team: str = "MTL"               # équipe de la LNH dont on affiche le match de la veille ; vide = désactivé

    @property
    def tz(self):
        return ZoneInfo(self.timezone)


def load_config(path=None):
    path = path or DEFAULT_CONFIG
    if not os.path.isfile(path):
        raise SystemExit(
            f"Fichier de configuration introuvable : {path}\n"
            f"Copiez config.example.ini vers config.ini, puis adaptez-le."
        )

    cp = configparser.ConfigParser(interpolation=None)   # les URL contiennent souvent des « % »
    cp.read(path, encoding="utf-8")

    try:
        cfg = Config(
            latitude=cp.getfloat("location", "latitude"),
            longitude=cp.getfloat("location", "longitude"),
            timezone=cp.get("location", "timezone"),
            news_url=cp.get("news", "feed_url", fallback="").strip(),
            news_count=cp.getint("news", "headlines", fallback=1),
            calendar_url=cp.get("calendar", "ics_url", fallback="").strip(),
            title=cp.get("display", "title", fallback="").strip() or "Panneau Castor",
            team=cp.get("sports", "team", fallback="MTL").strip().upper(),
        )
    except (configparser.Error, ValueError) as e:
        raise SystemExit(f"Configuration invalide dans {path} : {e}")

    # Valide le fuseau horaire : introuvable (faute de frappe, ou tzdata absent sous Windows)
    # ou valeur invalide (vide, chemin bizarre) -> message clair plutôt qu'une trace d'erreur.
    try:
        cfg.tz
    except (ZoneInfoNotFoundError, ValueError):
        raise SystemExit(
            f"Fuseau horaire inconnu : {cfg.timezone!r}\n"
            f"Vérifiez l'orthographe dans config.ini (exemple : America/Toronto). "
            f"Sous Windows, installez aussi les données de fuseaux : pip install tzdata"
        )
    return cfg
