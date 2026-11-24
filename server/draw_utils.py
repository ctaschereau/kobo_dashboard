"""Petits utilitaires de dessin : polices, ajustement et découpage du texte."""
import os
import sys

from PIL import ImageFont

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

# Police à empattements en gras, utilisée pour le mot « MESSAGE » (repli : la police normale en gras)
SERIF_BOLD_CANDIDATES = [
    os.path.join(HERE, "DejaVuSerif-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "DejaVuSerif-Bold.ttf",
    "georgiab.ttf", "timesbd.ttf", "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
]

_warned = False


def font(size, bold=False):
    """Police TrueType de la taille demandée (avec repli si aucune n'est trouvée)."""
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


def serif_font(size):
    """Police à empattements en gras de la taille demandée (sinon la police normale en gras)."""
    for path in SERIF_BOLD_CANDIDATES:
        try:
            return ImageFont.truetype(path, int(size))
        except OSError:
            continue
    return font(size, True)


def fit(d, text, max_w, size, bold=False, min_size=12):
    """Police la plus grande (<= size) qui fait entrer le texte dans max_w."""
    while size > min_size and d.textlength(text, font=font(size, bold)) > max_w:
        size -= 1
    return font(size, bold)


def wrap(d, text, fnt, max_w, max_lines=None):
    """Découpe le texte en lignes de largeur <= max_w (avec « … » si tronqué)."""
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
