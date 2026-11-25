"""Flashcards : des cartes question / réponse que l'élève retourne et note lui-même (« Je savais » ou « À revoir »).

Une carte notée « À revoir » repasse une fois en fin de série. D'une séance à l'autre, une carte reste « à revoir »
tant que sa dernière note n'est pas « Je savais » : c'est la pile proposée dans « Réviser mes cartes à revoir ».
Les cartes sont écrites par le tuteur et vérifiées ici (longueurs, doublons, schéma valide) ; rien n'est corrigé
automatiquement, l'élève s'évalue.
"""

from __future__ import annotations

import random

from figures import FigureInvalide, valider_figure

NOMBRES = (5, 10, 15)
MIN_CARTES, MAX_CARTES = 3, 20
POINTS_PAR_CARTE = 2          # par carte sue (du premier coup ou au second passage)
TYPE = "flashcards"           # marque des séances de flashcards dans la table des séances


class CartesInvalides(ValueError):
    pass


def _cle(recto: str) -> str:
    return " ".join(recto.lower().split())


def valider_cartes(brut) -> list[dict]:
    """Cartes propres et sans doublon. Une carte mal formée est écartée ; trop peu de cartes valides : erreur."""
    if isinstance(brut, dict):
        brut = brut.get("cartes")
    if not isinstance(brut, list):
        raise CartesInvalides("Il faut une liste « cartes »")
    cartes, vus = [], set()
    for c in brut[:MAX_CARTES]:
        if not isinstance(c, dict):
            continue
        recto, verso = str(c.get("recto") or "").strip(), str(c.get("verso") or "").strip()
        if not 3 <= len(recto) <= 200 or not 1 <= len(verso) <= 300 or _cle(recto) in vus:
            continue
        try:
            figure = valider_figure(c.get("figure"))
        except FigureInvalide:
            figure = None   # la carte reste utile sans son schéma
        vus.add(_cle(recto))
        cartes.append({"recto": recto, "verso": verso, "figure": figure})
    if len(cartes) < MIN_CARTES:
        raise CartesInvalides(f"Seulement {len(cartes)} carte(s) valide(s) sur {len(brut)}")
    return cartes


# ───────────── Une série de révision ─────────────

def nouvelle_revision(cartes: list[dict], profil: dict, melanger: bool = True) -> dict:
    ordre = list(range(len(cartes)))
    if melanger:
        random.shuffle(ordre)
    return {"cartes": cartes, "profil": profil, "file": ordre, "retournee": False,
            "notes": {}, "repassees": set(), "termine": False, "enregistree": False}


def carte_courante(r: dict) -> dict | None:
    return r["cartes"][r["file"][0]] if r["file"] else None


def retourner(r: dict) -> None:
    r["retournee"] = True


def noter(r: dict, sue: bool) -> None:
    """Note la carte affichée. « À revoir » : elle repasse une fois en fin de série."""
    if not r["file"] or not r["retournee"]:
        return
    i = r["file"].pop(0)
    r["notes"][i] = sue
    if not sue and i not in r["repassees"]:
        r["repassees"].add(i)
        r["file"].append(i)
    r["retournee"] = False
    r["termine"] = not r["file"]


def progression(r: dict) -> tuple[int, int]:
    """(cartes déjà vues au moins une fois, nombre de cartes)."""
    return len(r["notes"]), len(r["cartes"])


def bilan(r: dict) -> dict:
    sues = [i for i, ok in r["notes"].items() if ok]
    premier_coup = [i for i in sues if i not in r["repassees"]]
    a_revoir = [i for i, ok in r["notes"].items() if not ok]
    return {"cartes": len(r["cartes"]), "sues": len(sues), "du_premier_coup": len(premier_coup),
            "a_revoir": len(a_revoir), "points": POINTS_PAR_CARTE * len(sues)}


def contenu_a_enregistrer(r: dict) -> dict:
    """Ce qui est gardé dans la colonne messages : chaque carte avec sa dernière note."""
    b = bilan(r)
    return {"type": TYPE, "resultats": [], "stats": {}, "points": b["points"], "badges": [], "bilan_cartes": b,
            "cartes": [{**c, "sue": bool(r["notes"].get(i))} for i, c in enumerate(r["cartes"])]}


# ───────────── D'une séance à l'autre ─────────────

def est_flashcards(contenu: dict) -> bool:
    return contenu.get("type") == TYPE


def cartes_a_revoir(contenus_recents_dabord: list[dict]) -> list[dict]:
    """Cartes dont la dernière note est « À revoir » (contenus des séances, de la plus récente à la plus ancienne)."""
    derniere: dict = {}
    for contenu in contenus_recents_dabord:
        if not est_flashcards(contenu):
            continue
        for c in contenu.get("cartes") or []:
            cle = _cle(str(c.get("recto", "")))
            if cle and cle not in derniere:
                derniere[cle] = c
    return [{"recto": c["recto"], "verso": c["verso"], "figure": c.get("figure")}
            for c in derniere.values() if not c.get("sue")]
