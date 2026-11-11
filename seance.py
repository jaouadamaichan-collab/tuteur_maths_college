"""Déroulé d'une séance (ADR 0001 : tenu par l'app). Aucune dépendance à Streamlit : l'état est un dict
conservé dans st.session_state par l'écran, et chaque action est une fonction testable.
"""

from __future__ import annotations

import exercices as E
import tuteur as T


def nouvelle_seance(profil: dict, historique: str = "") -> dict:
    return {
        "profil": profil,
        "historique": historique,
        "nb_total": E.nombre_exercices(profil.get("temps", "30 min")),
        "rang": 0,
        "niveau": "moyen",
        "exercice": None,
        "formats": [],
        "deja": [],
        "resultats": [],
        "points": 0,
        "serie": 0,
        "nb_questions": 0,
        "termine": False,
        "bilan": None,
        "stats": None,
        "erreur": None,
        **_etat_exercice(),
    }


def _etat_exercice() -> dict:
    return {"indices": 0, "correction_vue": False, "essais": 0, "retour": None, "ordre": [], "echanges": [], "reussi": False}


def phase_courante(s: dict) -> str:
    return E.phase(s["rang"])


def preparer_exercice(s: dict, cle_api: str) -> None:
    """Choisit le format (rotation), ajuste la difficulté, demande l'exercice au tuteur.
    Si le tuteur échoue sur un format, l'app en essaie un autre plutôt que de bloquer l'élève."""
    s.update(_etat_exercice())
    s["exercice"], s["erreur"] = None, None
    s["niveau"] = E.niveau_suivant(s["resultats"], s["niveau"])
    format_ = E.choisir_format(s["rang"], s["formats"])
    essayes = []
    for _ in range(3):
        essayes.append(format_)
        try:
            s["exercice"] = T.generer_exercice(cle_api, s["profil"], format_, s["rang"], s["niveau"], s["deja"], s["historique"])
            s["formats"].append(format_)
            s["deja"].append(f"{s['exercice']['notion'] or ''} — {s['exercice']['enonce'][:120]}")
            return
        except E.ExerciceInvalide:
            restants = [f for f in E.FORMATS_FERMES if f not in essayes and (not s["formats"] or f != s["formats"][-1])]
            if not restants:
                break
            format_ = restants[0]
        except T.TuteurIndisponible as ex:
            s["erreur"] = f"Le tuteur ne répond pas pour le moment ({ex}). Réessaie dans un instant."
            return
    s["erreur"] = "Le tuteur n'a pas réussi à préparer un exercice valable. Réessaie."


def demander_aide(s: dict) -> None:
    """Indice 1, indice 2, puis correction (décision Q3)."""
    if s["reussi"]:
        return
    if s["indices"] < 2:
        s["indices"] += 1
    else:
        s["correction_vue"] = True


def _reussite(s: dict, partiel: bool = False) -> None:
    ex = s["exercice"]
    s["serie"] += 1
    gain, bonus = E.points(s["indices"], s["correction_vue"], s["serie"], partiel)
    s["points"] += gain + bonus
    s["reussi"] = True
    s["resultats"].append({
        "rang": s["rang"], "phase": phase_courante(s), "format": ex["format"], "notion": ex.get("notion"),
        "niveau": s["niveau"], "reussi": True, "partiel": partiel, "indices": s["indices"],
        "correction_vue": s["correction_vue"], "essais": s["essais"], "points": gain + bonus, "enonce": ex["enonce"],
    })
    s["retour"] = {"ok": True, "gain": gain, "bonus": bonus, "texte": s["retour"]["texte"] if s.get("retour") else ""}


def repondre(s: dict, reponse) -> bool:
    """Correction par l'app d'un format fermé. Retourne True si c'est juste."""
    ex = s["exercice"]
    s["essais"] += 1
    if E.est_juste(ex, reponse):
        s["retour"] = None
        _reussite(s)
        return True
    s["serie"] = 0
    s["retour"] = {"ok": False, "texte": E.detail_erreur(ex, reponse)}
    if ex["format"] == "ordre":
        s["ordre"] = []
    return False


def rediger(s: dict, cle_api: str, texte: str) -> bool:
    """Réponse rédigée, corrigée par le tuteur (format ouvert)."""
    ex = s["exercice"]
    s["essais"] += 1
    try:
        r = T.corriger_redaction(cle_api, s["profil"], ex, texte)
    except T.TuteurIndisponible as ex_:
        s["retour"] = {"ok": False, "texte": f"Le tuteur ne répond pas ({ex_}). Réessaie."}
        s["essais"] -= 1
        return False
    if r["verdict"] in ("juste", "partiel"):
        s["retour"] = {"ok": True, "texte": r["retour"]}
        _reussite(s, partiel=r["verdict"] == "partiel")
        return True
    s["serie"] = 0
    s["retour"] = {"ok": False, "texte": r["retour"]}
    return False


def passer(s: dict) -> None:
    """Après avoir vu la correction, l'élève peut passer : l'exercice compte comme non réussi, sans point."""
    ex = s["exercice"]
    s["serie"] = 0
    s["resultats"].append({
        "rang": s["rang"], "phase": phase_courante(s), "format": ex["format"], "notion": ex.get("notion"),
        "niveau": s["niveau"], "reussi": False, "partiel": False, "indices": s["indices"],
        "correction_vue": s["correction_vue"], "essais": s["essais"], "points": 0, "enonce": ex["enonce"],
    })
    s["reussi"] = True  # l'exercice est clos


def poser_question(s: dict, cle_api: str, question: str) -> None:
    try:
        reponse = T.repondre_question(cle_api, s["profil"], s["exercice"], question, s["correction_vue"], s["echanges"])
    except T.TuteurIndisponible as ex:
        reponse = f"Le tuteur ne répond pas pour le moment ({ex})."
    s["echanges"].append({"question": question, "reponse": reponse})
    s["nb_questions"] += 1


def exercice_suivant(s: dict, cle_api: str, sauvegarder=None) -> None:
    s["rang"] += 1
    if s["rang"] >= s["nb_total"]:
        terminer(s, cle_api, sauvegarder)
    else:
        preparer_exercice(s, cle_api)


def terminer(s: dict, cle_api: str, sauvegarder=None) -> None:
    """Bilan : chiffres calculés par l'app, rédaction par le tuteur, sauvegarde."""
    s["termine"] = True
    s["stats"] = E.statistiques(s["resultats"])
    if not s["resultats"]:
        s["bilan"] = "Séance arrêtée avant le premier exercice : pas de bilan cette fois."
    else:
        try:
            s["bilan"] = T.rediger_bilan(cle_api, s["profil"], s["stats"], s["resultats"])
        except T.TuteurIndisponible:
            st_ = s["stats"]
            s["bilan"] = f"{st_['reussis']} exercice(s) réussi(s) sur {st_['exercices']}, dont {st_['sans_aide']} sans aide. Bravo pour ta séance !"
    if sauvegarder:
        sauvegarder(s)
