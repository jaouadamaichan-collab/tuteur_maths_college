"""Exercices structurés (ADR 0001) : contrat entre le tuteur et l'app, correction par le code,
rotation des formats, niveau de difficulté et barème.

Le tuteur écrit le contenu d'un exercice dans le format que l'app lui impose, sous forme d'un objet JSON.
Ce module vérifie cet objet avant qu'il n'atteigne l'élève, et corrige les formats fermés.
Aucune dépendance à Streamlit : tout est testable hors ligne.
"""

from __future__ import annotations

import ast
import math
import operator
import random
import re

FORMATS_FERMES = ("qcm", "numerique", "vf", "trous", "ordre")
FORMAT_OUVERT = "ouvert"
FORMATS = FORMATS_FERMES + (FORMAT_OUVERT,)
NOMS_FORMATS = {
    "qcm": "QCM",
    "numerique": "Réponse numérique",
    "vf": "Vrai ou faux",
    "trous": "Texte à trous",
    "ordre": "Étapes dans l'ordre",
    "ouvert": "Réponse rédigée",
}
# Diagnostic (3 exercices) : un prérequis, une application directe, une question de compréhension.
FORMATS_DIAGNOSTIC = ("qcm", "numerique", "vf")
FREQUENCE_OUVERT = 5  # environ un exercice d'entraînement sur cinq est une réponse rédigée
NIVEAUX = ("facile", "moyen", "difficile")
ARRONDIS = {"unité": 1.0, "dixième": 0.1, "centième": 0.01, "exact": 0.0}
TROU = "___"

BAREME = {0: 10, 1: 7, 2: 5}  # points selon le nombre d'indices utilisés
POINTS_APRES_CORRECTION = 3
POINTS_MAX_PARTIEL = 5        # réponse rédigée jugée partiellement juste
BONUS_SERIE = 2
SEUIL_SERIE = 3
EXERCICES_PAR_DUREE = {"15 min": 6, "30 min": 10, "45 min": 14, "1h": 18, "1h30": 24, "2h": 30}


class ExerciceInvalide(ValueError):
    pass


# ───────────── Calcul sûr (double vérification des réponses numériques) ─────────────

_OPERATEURS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}
_FONCTIONS = {"sqrt": math.sqrt, "racine": math.sqrt}
_CONSTANTES = {"pi": math.pi, "π": math.pi}


def evaluer_calcul(expression: str) -> float:
    """Évalue une expression arithmétique écrite par le tuteur (ex. « pi*3**2*4/3 »), sans exécuter de code."""
    texte = str(expression).replace("×", "*").replace("÷", "/").replace("^", "**").replace("π", "pi").replace(",", ".")
    texte = re.sub(r"√\s*\(", "sqrt(", texte)
    if len(texte) > 200:
        raise ExerciceInvalide("Calcul trop long")
    try:
        arbre = ast.parse(texte, mode="eval")
    except SyntaxError as ex:
        raise ExerciceInvalide(f"Calcul illisible : {expression}") from ex

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _OPERATEURS:
            gauche, droite = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(droite) > 10:
                raise ExerciceInvalide("Exposant trop grand")
            return _OPERATEURS[type(n.op)](gauche, droite)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        if isinstance(n, ast.Name) and n.id in _CONSTANTES:
            return _CONSTANTES[n.id]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FONCTIONS and len(n.args) == 1 and not n.keywords:
            return _FONCTIONS[n.func.id](ev(n.args[0]))
        raise ExerciceInvalide(f"Élément non autorisé dans le calcul : {ast.dump(n)[:60]}")

    try:
        valeur = ev(arbre)
    except ExerciceInvalide:
        raise
    except (ZeroDivisionError, ValueError, OverflowError) as ex:
        raise ExerciceInvalide(f"Calcul impossible : {expression}") from ex
    if isinstance(valeur, complex) or not math.isfinite(valeur):   # ex. (-8)**(1/3) donne un complexe en Python
        raise ExerciceInvalide("Calcul sans résultat réel")
    return valeur


def lire_nombre(texte) -> float | None:
    """Lit la saisie d'un élève : virgule ou point, espaces, unité éventuelle en fin."""
    if texte is None:
        return None
    t = str(texte).strip().replace(" ", "").replace(" ", "").replace(",", ".")
    m = re.match(r"^[-+]?\d+(\.\d+)?", t)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def tolerance(arrondi: str) -> float:
    pas = ARRONDIS.get(arrondi, 0.1)
    return pas / 2 + 1e-9 if pas else 1e-6


# ───────────── Validation du contrat ─────────────

def _texte(ex: dict, cle: str, obligatoire: bool = True, longueur: int = 600) -> str:
    v = ex.get(cle)
    if v is None or (isinstance(v, str) and not v.strip()):
        if obligatoire:
            raise ExerciceInvalide(f"Champ « {cle} » manquant")
        return ""
    if not isinstance(v, str):
        raise ExerciceInvalide(f"Champ « {cle} » : texte attendu")
    return " ".join(v.split())[:longueur]


def valider_exercice(brut: dict, format_attendu: str) -> dict:
    """Vérifie et normalise un exercice produit par le tuteur. Lève ExerciceInvalide sinon.
    Les formats fermés reçoivent une réponse attendue que le code sait vérifier."""
    if not isinstance(brut, dict):
        raise ExerciceInvalide("L'exercice n'est pas un objet")
    if brut.get("format") != format_attendu:
        raise ExerciceInvalide(f"Format « {brut.get('format')} » au lieu de « {format_attendu} »")
    ex = {
        "format": format_attendu,
        "enonce": _texte(brut, "enonce"),
        "mission": _texte(brut, "mission", obligatoire=False, longueur=300),
        "notion": _texte(brut, "notion", obligatoire=False, longueur=80),
        "correction": _texte(brut, "correction", longueur=800),
    }
    indices = brut.get("indices")
    if not isinstance(indices, list) or len(indices) < 2 or not all(isinstance(i, str) and i.strip() for i in indices[:2]):
        raise ExerciceInvalide("Il faut deux indices")
    ex["indices"] = [" ".join(i.split())[:400] for i in indices[:2]]

    from figures import valider_figure  # import local : figures dépend de matplotlib

    ex["figure"] = valider_figure(brut.get("figure"))

    f = format_attendu
    if f == "qcm":
        options = brut.get("options")
        if not isinstance(options, list) or not 3 <= len(options) <= 4:
            raise ExerciceInvalide("Un QCM a 3 ou 4 options")
        options = [" ".join(str(o).split())[:150] for o in options]
        if len(set(options)) != len(options):
            raise ExerciceInvalide("Options en double")
        bonne = " ".join(str(brut.get("bonne_option", "")).split())
        if bonne not in options:
            raise ExerciceInvalide("La bonne option ne fait pas partie des options")
        ex["options"] = random.sample(options, len(options))  # le modèle met souvent la bonne en premier
        ex["bonne_option"] = bonne
    elif f == "numerique":
        arrondi = brut.get("arrondi", "dixième")
        if not isinstance(arrondi, str) or arrondi not in ARRONDIS:
            raise ExerciceInvalide(f"Arrondi inconnu : {arrondi}")
        reponse = brut.get("reponse")
        if not isinstance(reponse, (int, float)) or isinstance(reponse, bool):
            raise ExerciceInvalide("Réponse numérique manquante")
        calcul = evaluer_calcul(brut.get("calcul", ""))
        pas = ARRONDIS[arrondi]
        attendu = round(calcul / pas) * pas if pas else calcul
        # Double vérification : la réponse annoncée doit correspondre au calcul refait par le code.
        if abs(attendu - float(reponse)) > max(tolerance(arrondi), 1e-6 * abs(attendu)):
            raise ExerciceInvalide(f"Corrigé incohérent : calcul {calcul:.4f} → {attendu}, réponse annoncée {reponse}")
        ex.update({"reponse": float(reponse), "calcul": str(brut["calcul"]), "arrondi": arrondi, "unite": _texte(brut, "unite", obligatoire=False, longueur=15)})
    elif f == "vf":
        affs = brut.get("affirmations")
        if not isinstance(affs, list) or not 2 <= len(affs) <= 4:
            raise ExerciceInvalide("Il faut 2 à 4 affirmations")
        ex["affirmations"] = []
        for a in affs:
            if not isinstance(a, dict) or not isinstance(a.get("vrai"), bool) or not str(a.get("texte", "")).strip():
                raise ExerciceInvalide("Affirmation mal formée")
            ex["affirmations"].append({"texte": " ".join(a["texte"].split())[:250], "vrai": a["vrai"]})
    elif f == "trous":
        texte = _texte(brut, "texte")
        trous = brut.get("trous")
        if not isinstance(trous, list) or not 1 <= len(trous) <= 4:
            raise ExerciceInvalide("Il faut 1 à 4 trous")
        if texte.count(TROU) != len(trous):
            raise ExerciceInvalide(f"{texte.count(TROU)} marques {TROU} pour {len(trous)} trous")
        ex["texte"], ex["trous"] = texte, []
        for t in trous:
            options = [" ".join(str(o).split())[:60] for o in (t.get("options") or [])] if isinstance(t, dict) else []
            bonne = " ".join(str(t.get("bonne", "")).split()) if isinstance(t, dict) else ""
            if not 2 <= len(options) <= 4 or bonne not in options or len(set(options)) != len(options):
                raise ExerciceInvalide("Trou mal formé")
            ex["trous"].append({"options": random.sample(options, len(options)), "bonne": bonne})
    elif f == "ordre":
        etapes = brut.get("etapes")
        if not isinstance(etapes, list) or not 3 <= len(etapes) <= 5:
            raise ExerciceInvalide("Il faut 3 à 5 étapes")
        etapes = [" ".join(str(e).split())[:200] for e in etapes]
        if len(set(etapes)) != len(etapes):
            raise ExerciceInvalide("Étapes en double")
        ex["etapes"] = etapes
        melange = etapes[:]
        while melange == etapes:
            random.shuffle(melange)
        ex["melange"] = melange
    elif f == "ouvert":
        ex["attendus"] = _texte(brut, "attendus", longueur=600)
    else:
        raise ExerciceInvalide(f"Format inconnu : {f}")
    return ex


# ───────────── Correction des formats fermés ─────────────

def est_juste(ex: dict, reponse) -> bool:
    f = ex["format"]
    if f == "qcm":
        return reponse == ex["bonne_option"]
    if f == "numerique":
        # La valeur doit être celle demandée, arrondie comme demandé : 282,7 n'est pas juste si l'on demande l'unité.
        x = lire_nombre(reponse)
        return x is not None and abs(x - ex["reponse"]) <= 1e-6 * max(1.0, abs(ex["reponse"]))
    if f == "vf":
        return isinstance(reponse, (list, tuple)) and list(reponse) == [a["vrai"] for a in ex["affirmations"]]
    if f == "trous":
        return isinstance(reponse, (list, tuple)) and list(reponse) == [t["bonne"] for t in ex["trous"]]
    if f == "ordre":
        return isinstance(reponse, (list, tuple)) and list(reponse) == ex["etapes"]
    raise ValueError("La réponse rédigée est corrigée par le tuteur, pas par le code")


def detail_erreur(ex: dict, reponse) -> str:
    """Retour factuel calculé par le code (sans donner la réponse)."""
    f = ex["format"]
    if f == "vf" and isinstance(reponse, (list, tuple)):
        n = sum(1 for r, a in zip(reponse, ex["affirmations"]) if r == a["vrai"])
        return f"{n} sur {len(ex['affirmations'])} correctes."
    if f == "trous" and isinstance(reponse, (list, tuple)):
        n = sum(1 for r, t in zip(reponse, ex["trous"]) if r == t["bonne"])
        return f"{n} trou(s) sur {len(ex['trous'])} correct(s)."
    if f == "ordre" and isinstance(reponse, (list, tuple)):
        n = 0
        for r, e in zip(reponse, ex["etapes"]):
            if r != e:
                break
            n += 1
        return f"Les {n} première(s) étape(s) sont bien placées." if n else "La première étape n'est pas la bonne."
    if f == "numerique":
        x = lire_nombre(reponse)
        if x is None:
            return "Écris un nombre (par exemple 12,5)."
        if ex["arrondi"] != "exact" and abs(x - ex["reponse"]) <= 10 * tolerance(ex["arrondi"]):
            return f"Tu es tout près : vérifie ton arrondi (au {ex['arrondi']})."
    return ""


# ───────────── Déroulé de la séance (ADR 0001 : tenu par l'app) ─────────────

def nombre_exercices(temps: str) -> int:
    return EXERCICES_PAR_DUREE.get(temps, 10)


def phase(rang: int) -> str:
    """rang = index de l'exercice dans la séance (0 pour le premier)."""
    return "diagnostic" if rang < len(FORMATS_DIAGNOSTIC) else "entrainement"


def choisir_format(rang: int, precedents: list[str], aleatoire: random.Random | None = None) -> str:
    """Diagnostic : QCM, numérique, vrai/faux. Entraînement : rotation des formats fermés, jamais deux fois
    de suite le même, en privilégiant les moins utilisés ; une réponse rédigée environ une fois sur cinq."""
    r = aleatoire or random
    if rang < len(FORMATS_DIAGNOSTIC):
        return FORMATS_DIAGNOSTIC[rang]
    n_entrainement = rang - len(FORMATS_DIAGNOSTIC)
    if n_entrainement % FREQUENCE_OUVERT == FREQUENCE_OUVERT - 1:
        return FORMAT_OUVERT
    dernier = precedents[-1] if precedents else None
    candidats = [f for f in FORMATS_FERMES if f != dernier]
    usage = {f: precedents.count(f) for f in candidats}
    moins = min(usage.values())
    return r.choice([f for f in candidats if usage[f] == moins])


def niveau_suivant(resultats: list[dict], niveau: str = "moyen") -> str:
    """Ajuste la difficulté d'après les derniers résultats : deux réussites sans indice → monte ;
    correction vue → descend (revenir au prérequis)."""
    if not resultats:
        return niveau
    dernier = resultats[-1]
    i = NIVEAUX.index(niveau)
    if dernier.get("correction_vue"):
        return NIVEAUX[max(0, i - 1)]
    if len(resultats) >= 2 and all(r.get("reussi") and r.get("indices", 0) == 0 and not r.get("correction_vue") for r in resultats[-2:]):
        return NIVEAUX[min(len(NIVEAUX) - 1, i + 1)]
    return niveau


# ───────────── Points (décision Q10) ─────────────

def points(indices: int, correction_vue: bool, serie_apres: int, partiel: bool = False) -> tuple[int, int]:
    """Retourne (points de l'exercice, bonus de série). Jamais zéro pour un exercice mené à son terme."""
    base = POINTS_APRES_CORRECTION if correction_vue else BAREME.get(indices, BAREME[2])
    if partiel:
        base = min(base, POINTS_MAX_PARTIEL)
    bonus = BONUS_SERIE if serie_apres >= SEUIL_SERIE else 0
    return base, bonus


def statistiques(resultats: list[dict]) -> dict:
    """Chiffres du bilan, calculés par l'app à partir des vrais résultats."""
    faits = [r for r in resultats if r.get("reussi") is not None]
    reussis = [r for r in faits if r["reussi"]]
    sans_aide = [r for r in reussis if r.get("indices", 0) == 0 and not r.get("correction_vue")]
    echecs_par_format: dict[str, int] = {}
    for r in faits:
        if r.get("indices", 0) or r.get("correction_vue") or r.get("essais", 1) > 1:
            echecs_par_format[r["format"]] = echecs_par_format.get(r["format"], 0) + 1
    return {
        "exercices": len(faits),
        "reussis": len(reussis),
        "sans_aide": len(sans_aide),
        "avec_indices": sum(1 for r in reussis if r.get("indices", 0) and not r.get("correction_vue")),
        "correction_vue": sum(1 for r in faits if r.get("correction_vue")),
        "diagnostic_sans_aide": sum(1 for r in sans_aide if r.get("phase") == "diagnostic"),
        "formats_difficiles": sorted(echecs_par_format, key=lambda f: -echecs_par_format[f])[:2],
        "notions_difficiles": sorted({r.get("notion") for r in faits if r.get("notion") and (r.get("correction_vue") or r.get("indices", 0) >= 2)}),
        "points": sum(r.get("points", 0) for r in faits),
    }
