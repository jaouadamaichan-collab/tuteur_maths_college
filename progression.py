"""Progression d'un élève d'une séance à l'autre (décisions Q10, Q11) : badges et points cumulés.

Le cumul se calcule à partir des séances enregistrées (colonne messages de sessions_college) : aucune
table supplémentaire. L'élève est identifié par son prénom ; deux homonymes partagent leur progression
(limite connue, à lever plus tard avec un code élève donné par le prof).
"""

from __future__ import annotations

import json
from collections import Counter

# id : (emoji, nom, comment l'obtenir)
BADGES = {
    "premier_sans_indice": ("🎯", "Premier sans indice", "Réussir un exercice sans aucune aide"),
    "serie_5": ("🔥", "Série de 5", "Réussir 5 exercices d'affilée"),
    "trois_formats": ("🎨", "Trois formats", "Réussir trois formats d'exercice différents dans une séance"),
    "releve": ("💪", "Je me suis relevé·e", "Réussir un exercice juste après en avoir eu besoin de la correction"),
    "seance_terminee": ("🏁", "Séance terminée", "Aller au bout d'une séance complète"),
}


def libelle(badge_id: str) -> str:
    emoji, nom, _ = BADGES[badge_id]
    return f"{emoji} {nom}"


def badges_obtenus(resultats: list[dict], serie: int, seance_complete: bool = False) -> set[str]:
    """Badges que les résultats de la séance en cours permettent d'obtenir."""
    obtenus = set()
    reussis = [r for r in resultats if r.get("reussi")]
    if any(r.get("indices", 0) == 0 and not r.get("correction_vue") for r in reussis):
        obtenus.add("premier_sans_indice")
    if serie >= 5:
        obtenus.add("serie_5")
    if len({r["format"] for r in reussis}) >= 3:
        obtenus.add("trois_formats")
    for avant, apres in zip(resultats, resultats[1:]):
        if avant.get("correction_vue") and apres.get("reussi") and not apres.get("correction_vue"):
            obtenus.add("releve")
    if seance_complete:
        obtenus.add("seance_terminee")
    return obtenus


def nouveaux(deja: list[str], obtenus: set[str]) -> list[str]:
    """Nouveaux badges, dans l'ordre du catalogue (affichage stable)."""
    return [b for b in BADGES if b in obtenus and b not in deja]


def lire_contenu(ligne: dict) -> dict:
    """Contenu structuré d'une séance enregistrée ; {} pour les anciennes séances au format chat."""
    brut = ligne.get("messages")
    if isinstance(brut, str):
        try:
            brut = json.loads(brut)
        except ValueError:
            return {}
    return brut if isinstance(brut, dict) and "resultats" in brut else {}


def cumul(seances: list[dict]) -> dict:
    """Points, badges et statistiques cumulés d'un élève sur toutes ses séances enregistrées."""
    points, badges, formats_difficiles = 0, [], Counter()
    exercices = sans_aide = structurees = 0
    for ligne in seances:
        c = lire_contenu(ligne)
        if not c:
            continue
        structurees += 1
        points += int(c.get("points") or 0)
        for b in c.get("badges") or []:
            if b in BADGES and b not in badges:
                badges.append(b)
        stats = c.get("stats") or {}
        exercices += int(stats.get("exercices") or 0)
        sans_aide += int(stats.get("sans_aide") or 0)
        formats_difficiles.update(stats.get("formats_difficiles") or [])
    return {
        "points": points,
        "badges": [b for b in BADGES if b in badges],
        "seances": len(seances),
        "seances_structurees": structurees,
        "exercices": exercices,
        "sans_aide": sans_aide,
        "taux_sans_aide": round(100 * sans_aide / exercices) if exercices else None,
        "formats_difficiles": [f for f, _ in formats_difficiles.most_common(2)],
    }
