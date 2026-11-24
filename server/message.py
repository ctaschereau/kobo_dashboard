"""Message libre affiché dans la colonne de droite à la place des habits, du hockey et des nouvelles.

Source : le fichier message.txt à la racine du projet (non versionné). Format :

    2026-11-25T18:00            <- facultatif : date d'expiration (ISO 8601) sur la première ligne
    Texte du message,
    sur autant de lignes que voulu.

- Pas de première ligne datée : le message reste affiché tant que le fichier n'est pas vidé.
- Date sans heure (2026-11-25) : le message expire à la fin de cette journée.
- Date sans fuseau : interprétée dans le fuseau de config.ini.
- Fichier absent, vide, ou date passée : pas de message, l'affichage normal revient tout seul.
"""
import os
import re
import sys
from datetime import datetime, time

from config import ROOT

MESSAGE_FILE = os.path.join(ROOT, "message.txt")

# Une première ligne qui commence comme une date AAAA-MM-JJ est lue comme une expiration.
_DEBUT_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _parse_expiration(ligne, tz):
    """Date d'expiration (datetime avec fuseau) décrite par `ligne`. Lève ValueError si invalide."""
    texte = ligne.strip()
    if texte[-1:] in ("Z", "z"):                          # fromisoformat n'accepte pas « Z » avant Python 3.11
        texte = texte[:-1] + "+00:00"
    exp = datetime.fromisoformat(texte)
    if len(texte) <= 10:                                  # date seule : valable toute la journée
        exp = datetime.combine(exp.date(), time(23, 59, 59))
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=tz)
    return exp


def current_message(now, path=MESSAGE_FILE):
    """Texte du message à afficher, ou None (pas de fichier, vide ou expiré).

    `now` est un datetime avec fuseau.
    """
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8-sig") as f:           # utf-8-sig : tolère le BOM du Bloc-notes
        lignes = f.read().splitlines()

    if lignes and _DEBUT_DATE.match(lignes[0].strip()):
        premiere = lignes.pop(0)
        try:
            expiration = _parse_expiration(premiere, now.tzinfo)
        except ValueError:
            # Faute de frappe dans la date : on affiche quand même le message, sans expiration.
            print(f"message.txt : date d'expiration invalide ({premiere.strip()!r}), ignorée.",
                  file=sys.stderr)
        else:
            if now >= expiration:
                return None

    texte = "\n".join(lignes).strip()
    return texte or None
