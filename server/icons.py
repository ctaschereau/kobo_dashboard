"""Icônes dessinées à la main (noir et blanc, pour écran e-ink).

Chaque icône est dessinée dans une boîte virtuelle de 100x100 unités,
mise à l'échelle selon la taille demandée.

    icon_weather(d, x, y, taille, genre, night=False)
    icon_clothing(d, x, y, taille, cle)

`d` est un ImageDraw.Draw ; (x, y) est le coin supérieur gauche de l'icône.
"""
import math

# ---------- Icônes (dessinées à la main, boîte virtuelle 100x100) ----------
class Ico:
    def __init__(self, d, ox, oy, size):
        self.d, self.ox, self.oy = d, ox, oy
        self.k = size / 100.0
        self.lw = max(3, round(3.5 * self.k))

    def p(self, x, y):
        return (self.ox + x * self.k, self.oy + y * self.k)

    def pts(self, l):
        return [self.p(x, y) for x, y in l]

    def box(self, b):
        return (*self.p(b[0], b[1]), *self.p(b[2], b[3]))

    def poly(self, l, fill=255):
        pts = self.pts(l)
        self.d.polygon(pts, fill=fill)
        self.d.line(pts + [pts[0]], fill=0, width=self.lw, joint="curve")

    def line(self, l):
        self.d.line(self.pts(l), fill=0, width=self.lw, joint="curve")

    def ell(self, b, fill=255):
        self.d.ellipse(self.box(b), fill=fill, outline=0, width=self.lw)

    def pie(self, b, a0, a1, fill=255):
        self.d.pieslice(self.box(b), a0, a1, fill=fill, outline=0, width=self.lw)

    def arc(self, b, a0, a1):
        self.d.arc(self.box(b), a0, a1, fill=0, width=self.lw)

    def rrect(self, b, r, fill=255):
        self.d.rounded_rectangle(self.box(b), radius=r * self.k, fill=fill,
                                 outline=0, width=self.lw)

    def cloud(self, dx=0, dy=0, s=1.0):
        # Silhouette en deux passes : noir élargi, puis blanc
        parts = [(14, 48, 46, 80), (30, 24, 70, 66), (52, 38, 88, 80), (30, 52, 72, 80)]
        grow = self.lw
        for fillc, g in ((0, grow), (255, 0)):
            for x0, y0, x1, y1 in parts:
                b = [(self.ox + (dx + x0 * s) * self.k - g, self.oy + (dy + y0 * s) * self.k - g),
                     (self.ox + (dx + x1 * s) * self.k + g, self.oy + (dy + y1 * s) * self.k + g)]
                self.d.ellipse([*b[0], *b[1]], fill=fillc)


def moon(i, stars=True):
    i.d.ellipse(i.box((14, 20, 78, 84)), fill=0)
    i.d.ellipse(i.box((36, 8, 92, 64)), fill=255)
    if stars:
        for x, y in ((78, 14), (90, 42)):
            i.line([(x - 6, y), (x + 6, y)])
            i.line([(x, y - 6), (x, y + 6)])


def icon_weather(d, ox, oy, size, kind, night=False):
    i = Ico(d, ox, oy, size)
    if night and kind == "sun":
        moon(i)
    elif night and kind == "partly":
        moon(Ico(d, ox, oy, size * 0.7), stars=False)
        i.cloud(dx=10, dy=18, s=0.9)
    elif kind == "sun":
        i.ell((26, 26, 74, 74))
        for a in range(0, 360, 45):
            r0, r1 = 34, 48
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            i.line([(50 + r0 * c, 50 + r0 * s), (50 + r1 * c, 50 + r1 * s)])
    elif kind == "partly":
        i.ell((16, 16, 52, 52))
        for a in range(180, 360 + 90, 45):
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            i.line([(34 + 24 * c, 34 + 24 * s), (34 + 32 * c, 34 + 32 * s)])
        i.cloud(dx=10, dy=18, s=0.9)
    elif kind == "cloud":
        i.cloud(dy=0)
    elif kind == "rain":
        i.cloud(dy=-8, s=0.95)
        for x in (30, 50, 70):
            i.line([(x + 4, 76), (x - 4, 94)])
    elif kind == "snow":
        i.cloud(dy=-8, s=0.95)
        for x, y in ((28, 88), (50, 92), (72, 88)):
            i.line([(x - 7, y), (x + 7, y)])
            i.line([(x, y - 7), (x, y + 7)])
            i.line([(x - 5, y - 5), (x + 5, y + 5)])
            i.line([(x - 5, y + 5), (x + 5, y - 5)])
    elif kind == "fog":
        i.cloud(dy=-10, s=0.9)
        for y, x0, x1 in ((76, 16, 84), (86, 26, 92), (96, 12, 78)):
            i.line([(x0, y), (x1, y)])
    elif kind == "storm":
        i.cloud(dy=-10, s=0.95)
        i.poly([(54, 66), (36, 88), (48, 88), (42, 104), (66, 78), (54, 78)], fill=0)


def icon_clothing(d, ox, oy, size, key):
    i = Ico(d, ox, oy, size)
    if key == "coat":
        i.poly([(30, 8), (42, 8), (50, 20), (58, 8), (70, 8), (96, 34), (84, 52),
                (72, 42), (72, 94), (28, 94), (28, 42), (16, 52), (4, 34)])
        i.line([(50, 20), (50, 94)])
        i.line([(34, 70), (44, 70)])
        i.line([(56, 70), (66, 70)])
    elif key == "tshirt":
        i.poly([(30, 14), (42, 14), (50, 24), (58, 14), (70, 14), (96, 34), (84, 50),
                (72, 42), (72, 88), (28, 88), (28, 42), (16, 50), (4, 34)])
    elif key == "pants":
        i.poly([(26, 8), (74, 8), (80, 94), (55, 94), (50, 40), (45, 94), (20, 94)])
        i.line([(26, 20), (74, 20)])
    elif key == "boots":
        i.poly([(28, 6), (58, 6), (58, 52), (92, 62), (94, 90), (24, 90), (28, 6)])
        i.line([(24, 78), (94, 78)])
    elif key == "hat":  # tuque
        i.pie((16, 26, 84, 96), 180, 360)
        i.rrect((14, 60, 86, 80), 6)
        i.ell((40, 6, 60, 26))
    elif key == "mitts":
        i.rrect((26, 22, 70, 76), 18)
        i.ell((58, 40, 88, 66))
        i.rrect((26, 74, 70, 94), 4)
    elif key == "umbrella":
        i.pie((6, 8, 94, 96), 180, 360)
        i.line([(50, 52), (50, 84)])
        i.arc((34, 76, 50, 94), 0, 180)
    elif key == "sunhat":
        i.pie((28, 18, 72, 92), 180, 360)
        i.ell((6, 46, 94, 68))
