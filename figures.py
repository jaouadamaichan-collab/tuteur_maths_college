"""Figures cotées dessinées par le code (décision Q8) : le tuteur fournit le type et les mesures,
l'app dessine. Une mesure inconnue (null) s'affiche « ? ». Les mesures incohérentes sont refusées.
"""

from __future__ import annotations

import io
import math

TYPES = ("cone", "cylindre", "triangle_rectangle", "pave", "pyramide", "cercle", "repere_droite")
# Paramètres de chaque type : (nom, obligatoire, peut être inconnu)
PARAMETRES = {
    "cone": ("r", "h", "g"),
    "cylindre": ("r", "h"),
    "triangle_rectangle": ("ab", "bc", "ac"),  # angle droit en B, [AC] hypoténuse
    "pave": ("longueur", "largeur", "hauteur"),
    "pyramide": ("cote", "h"),                 # base carrée
    "cercle": ("r",),
    "repere_droite": ("a", "b"),               # droite y = ax + b
}
BLEU, ROUGE, GRIS = "#1e3a5f", "#dc2626", "#94a3b8"


class FigureInvalide(ValueError):
    pass


def _nombre(v, nom, positif=True):
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise FigureInvalide(f"Mesure « {nom} » invalide : {v!r}")
    if positif and v <= 0:
        raise FigureInvalide(f"Mesure « {nom} » doit être positive")
    if abs(v) > 10000:
        raise FigureInvalide(f"Mesure « {nom} » démesurée")
    return float(v)


def valider_figure(brut) -> dict | None:
    """Retourne la figure normalisée, None s'il n'y en a pas, ou lève FigureInvalide."""
    if brut in (None, {}, ""):
        return None
    if not isinstance(brut, dict) or brut.get("type") not in TYPES:
        raise FigureInvalide(f"Type de figure inconnu : {brut.get('type') if isinstance(brut, dict) else brut!r}")
    t = brut["type"]
    positif = t != "repere_droite"
    fig = {"type": t, "unite": str(brut.get("unite") or ("" if t == "repere_droite" else "cm"))[:6]}
    for p in PARAMETRES[t]:
        fig[p] = _nombre(brut.get(p), p, positif)
    connus = [p for p in PARAMETRES[t] if fig[p] is not None]

    if t == "cone":
        if len(connus) < 2 and fig["r"] is None:
            raise FigureInvalide("Cône : il faut au moins le rayon")
        if len(connus) == 3 and not math.isclose(fig["g"] ** 2, fig["h"] ** 2 + fig["r"] ** 2, rel_tol=0.01):
            raise FigureInvalide("Cône incohérent : g² ≠ h² + r²")
        if fig["g"] is not None and (fig["h"] is not None and fig["g"] <= fig["h"] or fig["r"] is not None and fig["g"] <= fig["r"]):
            raise FigureInvalide("Cône incohérent : la génératrice doit être la plus longue")
    if t == "triangle_rectangle":
        if len(connus) < 2:
            raise FigureInvalide("Triangle : il faut au moins deux longueurs")
        if len(connus) == 3 and not math.isclose(fig["ac"] ** 2, fig["ab"] ** 2 + fig["bc"] ** 2, rel_tol=0.01):
            raise FigureInvalide("Triangle incohérent : AC² ≠ AB² + BC²")
        if fig["ac"] is not None and any(fig[c] is not None and fig[c] >= fig["ac"] for c in ("ab", "bc")):
            raise FigureInvalide("Triangle incohérent : l'hypoténuse doit être le plus long côté")
    if t == "repere_droite" and (fig["a"] is None or fig["b"] is None):
        raise FigureInvalide("Droite : a et b sont nécessaires pour la tracer")
    if t in ("cercle",) and fig["r"] is None:
        raise FigureInvalide("Cercle : rayon nécessaire")
    return fig


def _cote(v, unite, nom=""):
    if v is None:
        return f"{nom} = ?" if nom else "?"
    texte = f"{v:g}".replace(".", ",")
    return f"{nom} = {texte} {unite}".strip() if nom else f"{texte} {unite}".strip()


def dessiner(fig: dict) -> bytes:
    """PNG de la figure. Les mesures inconnues sont déduites (ou prises par défaut) pour le dessin seulement."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Ellipse, Polygon

    figure, ax = plt.subplots(figsize=(3.4, 3.0), dpi=110)
    ax.set_aspect("equal")
    ax.axis("off")
    u, t = fig.get("unite", "cm"), fig["type"]

    if t in ("cone", "cylindre"):
        r = fig["r"] or 3.0
        if t == "cone":
            h = fig["h"] or (math.sqrt(fig["g"] ** 2 - r * r) if fig.get("g") and fig["g"] > r else r * 1.4)
        else:
            h = fig["h"] or r * 1.6
        echelle = 4.0 / max(r * 2, h)  # dessin à taille constante, cotes réelles
        R, H = r * echelle, h * echelle
        ax.add_patch(Ellipse((0, 0), 2 * R, R * 0.6, fill=False, color=BLEU, lw=2))
        ax.plot([0, R], [0, 0], color=ROUGE, lw=1.5, ls="--")
        ax.text(R / 2, -R * 0.3 - 0.35, _cote(fig["r"], u, "r"), ha="center", color=ROUGE, fontsize=10)
        if t == "cylindre":
            ax.add_patch(Ellipse((0, H), 2 * R, R * 0.6, fill=False, color=BLEU, lw=2))
            ax.plot([-R, -R], [0, H], color=BLEU, lw=2)
            ax.plot([R, R], [0, H], color=BLEU, lw=2)
            ax.annotate("", xy=(R + 0.4, H), xytext=(R + 0.4, 0), arrowprops=dict(arrowstyle="<->", color=GRIS))
            ax.text(R + 0.55, H / 2, _cote(fig["h"], u, "h"), va="center", fontsize=10, color=BLEU)
            ax.set_xlim(-R - 0.4, R + 2.6)
        else:
            ax.plot([-R, 0, R], [0, H, 0], color=BLEU, lw=2)
            ax.plot([0, 0], [0, H], color=GRIS, lw=1.5, ls="--")
            ax.plot([0, 0.22, 0.22], [0.22, 0.22, 0], color=GRIS, lw=1)
            ax.text(-R * 0.55 - 0.25, H * 0.55, _cote(fig["h"], u, "h"), ha="right", va="center", fontsize=10, color=BLEU)
            ax.annotate("", xy=(-0.05, H * 0.55), xytext=(-R * 0.55 - 0.2, H * 0.55), arrowprops=dict(arrowstyle="-", color=GRIS, lw=0.8, ls=":"))
            ax.text(R / 2 + 0.25, H / 2 + 0.1, _cote(fig["g"], u, "g"), fontsize=10, color=BLEU)
            ax.set_xlim(-R - 2.2, R + 1.6)
        ax.set_ylim(-R * 0.3 - 0.8, H + (R * 0.3 if t == "cylindre" else 0) + 0.4)

    elif t == "triangle_rectangle":
        ab, bc, ac = fig["ab"], fig["bc"], fig["ac"]
        if ab is None:
            ab = math.sqrt(ac ** 2 - bc ** 2)
        if bc is None:
            bc = math.sqrt(ac ** 2 - ab ** 2)
        e = 4.0 / max(ab, bc)
        A, B, C = (0, ab * e), (0, 0), (bc * e, 0)
        ax.add_patch(Polygon([A, B, C], closed=True, fill=False, color=BLEU, lw=2))
        ax.plot([0, 0.25, 0.25], [0.25, 0.25, 0], color=GRIS, lw=1)
        for nom, (x, y), dx, dy in (("A", A, -0.25, 0.1), ("B", B, -0.3, -0.3), ("C", C, 0.15, -0.3)):
            ax.text(x + dx, y + dy, nom, fontsize=11, color=BLEU, fontweight="bold")
        ax.text(-0.2, A[1] / 2, _cote(fig["ab"], u), ha="right", va="center", fontsize=10)
        ax.text(C[0] / 2, -0.4, _cote(fig["bc"], u), ha="center", fontsize=10)
        ax.text(C[0] / 2 + 0.15, A[1] / 2 + 0.15, _cote(fig["ac"], u), fontsize=10, color=ROUGE)
        ax.set_xlim(-1.4, C[0] + 1.2)
        ax.set_ylim(-0.8, A[1] + 0.5)

    elif t == "pave":
        L, l, h = fig["longueur"] or 5, fig["largeur"] or 3, fig["hauteur"] or 2
        e = 3.5 / max(L, l, h)
        L, l, h = L * e, l * e, h * e
        dx, dy = l * 0.5, l * 0.35
        av = [(0, 0), (L, 0), (L, h), (0, h)]
        ar = [(x + dx, y + dy) for x, y in av]
        ax.add_patch(Polygon(av, closed=True, fill=False, color=BLEU, lw=2))
        for (x1, y1), (x2, y2) in ((av[1], ar[1]), (av[2], ar[2]), (av[3], ar[3]), (ar[1], ar[2]), (ar[2], ar[3])):
            ax.plot([x1, x2], [y1, y2], color=BLEU, lw=2)
        for (x1, y1), (x2, y2) in ((av[0], ar[0]), (ar[0], ar[1]), (ar[0], ar[3])):
            ax.plot([x1, x2], [y1, y2], color=GRIS, lw=1.2, ls="--")
        ax.text(L / 2, -0.4, _cote(fig["longueur"], u), ha="center", fontsize=10)
        ax.text(L + dx / 2 + 0.3, dy / 2 - 0.3, _cote(fig["largeur"], u), fontsize=10)
        ax.text(-0.15, h / 2, _cote(fig["hauteur"], u), ha="right", va="center", fontsize=10)
        ax.set_xlim(-1.6, L + dx + 1.4)
        ax.set_ylim(-0.8, h + dy + 0.4)

    elif t == "pyramide":
        c, h = fig["cote"] or 4, fig["h"] or 5
        e = 3.5 / max(c, h)
        c, h = c * e, h * e
        dx, dy = c * 0.45, c * 0.3
        base = [(0, 0), (c, 0), (c + dx, dy), (dx, dy)]
        centre = ((c + dx) / 2, dy / 2)
        sommet = (centre[0], centre[1] + h)
        ax.plot([0, c, c + dx], [0, 0, dy], color=BLEU, lw=2)
        ax.plot([c + dx, dx, 0], [dy, dy, 0], color=GRIS, lw=1.2, ls="--")
        for i, p in enumerate(base):
            ax.plot([p[0], sommet[0]], [p[1], sommet[1]], color=GRIS if i == 3 else BLEU, lw=1.2 if i == 3 else 2, ls="--" if i == 3 else "-")
        ax.plot([centre[0], sommet[0]], [centre[1], sommet[1]], color=GRIS, lw=1.2, ls="--")
        ax.text(c / 2, -0.4, _cote(fig["cote"], u), ha="center", fontsize=10)
        ax.text(centre[0] - 0.12, centre[1] + h * 0.35, _cote(fig["h"], u, "h"), ha="right", fontsize=10, color=BLEU)
        ax.set_xlim(-0.8, c + dx + 1.2)
        ax.set_ylim(-0.8, sommet[1] + 0.4)

    elif t == "cercle":
        ax.add_patch(Circle((0, 0), 2, fill=False, color=BLEU, lw=2))
        ax.plot([0], [0], "o", color=BLEU, ms=3)
        ax.plot([0, 2], [0, 0], color=ROUGE, lw=1.5, ls="--")
        ax.text(1, 0.15, _cote(fig["r"], u, "r"), ha="center", color=ROUGE, fontsize=10)
        ax.text(-0.2, -0.3, "O", fontsize=11, color=BLEU, fontweight="bold")
        ax.set_xlim(-2.4, 2.4)
        ax.set_ylim(-2.4, 2.4)

    elif t == "repere_droite":
        a, b = fig["a"], fig["b"]
        ax.axis("on")
        ax.set_aspect("auto")
        ax.axhline(0, color=GRIS, lw=1)
        ax.axvline(0, color=GRIS, lw=1)
        ax.grid(True, color="#e2e8f0", lw=0.6)
        xs = [-5, 5]
        ax.plot(xs, [a * x + b for x in xs], color=BLEU, lw=2)
        ax.set_xlim(-5, 5)
        ax.set_ylim(-5, 5)
        ax.set_xticks(range(-5, 6))
        ax.set_yticks(range(-5, 6))
        ax.tick_params(labelsize=7)
        for spine in ax.spines.values():
            spine.set_visible(False)

    tampon = io.BytesIO()
    figure.savefig(tampon, format="png", bbox_inches="tight", transparent=True)
    plt.close(figure)
    return tampon.getvalue()
