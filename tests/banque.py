"""Exercices valides, un par format, tels que le tuteur doit les renvoyer (JSON brut)."""

import copy

BANQUE = {
    "qcm": {
        "format": "qcm", "notion": "volume du cylindre", "mission": "Lina range ses glaces dans des pots cylindriques.",
        "enonce": "Quelle formule donne le volume d'un cylindre de rayon r et de hauteur h ?",
        "options": ["π × r² × h", "2 × π × r × h", "π × r² × h ÷ 3", "π × r × h"], "bonne_option": "π × r² × h",
        "figure": None, "indices": ["Un cylindre est une pile de disques.", "Volume = aire de la base × hauteur."],
        "correction": "V = π × r² × h.",
    },
    "numerique": {
        "format": "numerique", "notion": "volume du cylindre", "mission": "Son grand pot a un rayon de 3 cm et une hauteur de 10 cm.",
        "enonce": "Calcule le volume du pot.", "calcul": "pi*3**2*10", "reponse": 282.7, "arrondi": "dixième", "unite": "cm³",
        "figure": {"type": "cylindre", "r": 3, "h": 10, "unite": "cm"},
        "indices": ["Utilise V = π × r² × h.", "V = π × 9 × 10 = 90π."], "correction": "V = 90π ≈ 282,7 cm³.",
    },
    "vf": {
        "format": "vf", "notion": "cône", "mission": "Lina sert aussi des cornets.", "enonce": "Vrai ou faux ?",
        "affirmations": [
            {"texte": "La base d'un cône est un disque.", "vrai": True},
            {"texte": "La hauteur d'un cône est plus longue que sa génératrice.", "vrai": False},
            {"texte": "Un cône a un sommet.", "vrai": True},
        ],
        "figure": {"type": "cone", "r": 3, "h": 4, "g": 5, "unite": "cm"},
        "indices": ["Regarde le triangle rectangle.", "L'hypoténuse est le plus long côté."], "correction": "Vrai, faux, vrai.",
    },
    "trous": {
        "format": "trous", "notion": "Pythagore", "mission": "Lina veut la hauteur de ses cornets.", "enonce": "Complète.",
        "texte": "Le triangle est ___ donc on applique le théorème de ___.",
        "trous": [{"options": ["rectangle", "isocèle", "équilatéral"], "bonne": "rectangle"}, {"options": ["Pythagore", "Thalès", "Euclide"], "bonne": "Pythagore"}],
        "figure": None, "indices": ["Regarde l'angle.", "Un mathématicien grec."], "correction": "Rectangle, Pythagore.",
    },
    "ordre": {
        "format": "ordre", "notion": "hauteur du cône", "mission": "Un cornet : r = 3 cm, g = 5 cm.", "enonce": "Remets dans l'ordre.",
        "etapes": ["Le triangle est rectangle.", "g² = h² + r².", "h² = 25 − 9 = 16.", "h = 4 cm."],
        "figure": {"type": "cone", "r": 3, "h": None, "g": 5, "unite": "cm"},
        "indices": ["On justifie d'abord.", "Puis on écrit l'égalité."], "correction": "Rectangle, égalité, calcul, racine.",
    },
    "ouvert": {
        "format": "ouvert", "notion": "comparer des volumes", "mission": "Un client compare un pot et un cornet.",
        "enonce": "Le pot contient-il 3 fois plus que le cornet ? Justifie.", "attendus": "36π contre 12π, rapport 3.",
        "figure": None, "indices": ["Calcule les deux volumes.", "Le cône est le tiers du cylindre."], "correction": "Oui : 36π et 12π.",
    },
}


def exercice(format_):
    return copy.deepcopy(BANQUE[format_])


def bonne_reponse(ex):
    """Bonne réponse d'un exercice validé (format fermé)."""
    f = ex["format"]
    return {
        "qcm": lambda: ex["bonne_option"],
        "numerique": lambda: "282,7",
        "vf": lambda: [a["vrai"] for a in ex["affirmations"]],
        "trous": lambda: [t["bonne"] for t in ex["trous"]],
        "ordre": lambda: list(ex["etapes"]),
    }[f]()
