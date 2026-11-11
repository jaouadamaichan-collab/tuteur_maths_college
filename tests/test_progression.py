"""Badges et cumul d'une séance à l'autre (décisions Q10, Q11)."""

import json

import anthropic
import pytest

import progression as P
import seance as S
import tuteur as T
from tests.banque import bonne_reponse
from tests.faux_claude import FauxClaude, appels_de


def r(format_="qcm", reussi=True, indices=0, correction_vue=False):
    return {"format": format_, "reussi": reussi, "indices": indices, "correction_vue": correction_vue}


# ───────────── Règles des badges ─────────────

def test_premier_sans_indice():
    assert "premier_sans_indice" not in P.badges_obtenus([r(indices=1)], 1)
    assert "premier_sans_indice" in P.badges_obtenus([r(indices=1), r()], 1)


def test_serie_de_5():
    assert "serie_5" not in P.badges_obtenus([], 4) and "serie_5" in P.badges_obtenus([], 5)


def test_trois_formats_reussis():
    assert "trois_formats" not in P.badges_obtenus([r("qcm"), r("vf"), r("trous", reussi=False)], 0)
    assert "trois_formats" in P.badges_obtenus([r("qcm"), r("vf"), r("trous")], 0)


def test_je_me_suis_releve():
    assert "releve" not in P.badges_obtenus([r(correction_vue=True), r(correction_vue=True)], 0)
    assert "releve" not in P.badges_obtenus([r(correction_vue=False), r()], 0)
    assert "releve" in P.badges_obtenus([r(reussi=False, correction_vue=True), r(indices=2)], 0)


def test_seance_terminee_seulement_si_complete():
    assert "seance_terminee" not in P.badges_obtenus([r()], 1)
    assert "seance_terminee" in P.badges_obtenus([r()], 1, seance_complete=True)


def test_nouveaux_dans_l_ordre_du_catalogue_sans_doublon():
    assert P.nouveaux(["serie_5"], {"seance_terminee", "serie_5", "premier_sans_indice"}) == ["premier_sans_indice", "seance_terminee"]


# ───────────── Cumul ─────────────

def seance_enregistree(points, badges, exercices, sans_aide, formats_difficiles=()):
    return {"messages": json.dumps({"resultats": [{}] * exercices, "points": points, "badges": badges,
                                    "stats": {"exercices": exercices, "sans_aide": sans_aide, "formats_difficiles": list(formats_difficiles)}})}


def test_cumul_sur_plusieurs_seances_et_ancien_format_ignore():
    seances = [
        seance_enregistree(60, ["premier_sans_indice"], 6, 4, ["ordre"]),
        seance_enregistree(85, ["serie_5", "premier_sans_indice"], 10, 8, ["ordre", "trous"]),
        {"messages": json.dumps([{"role": "user", "content": "ancienne séance en chat"}])},
        {"messages": "pas du json"},
        {"messages": {"resultats": [], "points": 5, "badges": ["inconnu"], "stats": {}}},
    ]
    c = P.cumul(seances)
    assert c["points"] == 150 and c["badges"] == ["premier_sans_indice", "serie_5"]
    assert c["seances"] == 5 and c["seances_structurees"] == 3
    assert c["exercices"] == 16 and c["taux_sans_aide"] == 75 and c["formats_difficiles"][0] == "ordre"


def test_cumul_vide():
    c = P.cumul([])
    assert c["points"] == 0 and c["badges"] == [] and c["taux_sans_aide"] is None


# ───────────── Dans la séance ─────────────

PROFIL = {"nom": "Inès", "classe": "4ème", "programme": "France", "chapitre": "Pyramides et cônes (volumes)",
          "theme_libre": False, "objectif": "", "temps": "15 min", "interets": ["⚽ Sport", "🍳 Cuisine"]}


@pytest.fixture(autouse=True)
def claude(monkeypatch):
    FauxClaude.reinitialiser()
    monkeypatch.setattr(anthropic, "Anthropic", FauxClaude)


def faire_seance(progression=None, aide_au_premier=False):
    s = S.nouvelle_seance(PROFIL, "", progression)
    S.preparer_exercice(s, "k")
    annonces = []
    while not s["termine"]:
        ex = s["exercice"]
        if aide_au_premier and s["rang"] == 0:
            for _ in range(3):
                S.demander_aide(s)
        if ex["format"] == "ouvert":
            S.rediger(s, "k", "36π contre 12π")
        else:
            S.repondre(s, bonne_reponse(ex))
        annonces += s["a_feter"]
        s["a_feter"] = []
        S.exercice_suivant(s, "k")
    return s, annonces + s["a_feter"]


def test_badges_gagnes_pendant_la_seance_et_annonces_une_fois():
    s, annonces = faire_seance(aide_au_premier=True)
    assert s["badges_nouveaux"] == annonces
    assert set(s["badges_nouveaux"]) == {"premier_sans_indice", "releve", "trois_formats", "serie_5", "seance_terminee"}
    assert len(annonces) == len(set(annonces))


def test_badges_deja_acquis_ne_sont_pas_redonnes_et_total_cumule():
    s, _ = faire_seance(progression={"points": 120, "badges": ["premier_sans_indice", "serie_5"]})
    assert "premier_sans_indice" not in s["badges_nouveaux"] and "serie_5" not in s["badges_nouveaux"]
    assert S.total_points(s) == 120 + s["points"]
    assert S.badges(s)[:2] == ["premier_sans_indice", "serie_5"]


def test_seance_arretee_avant_la_fin_sans_badge_seance_terminee():
    s = S.nouvelle_seance(PROFIL, "")
    S.preparer_exercice(s, "k")
    S.repondre(s, bonne_reponse(s["exercice"]))
    S.terminer(s, "k")
    assert "seance_terminee" not in s["badges_nouveaux"]


def test_centres_d_interet_transmis_en_alternance():
    s, _ = faire_seance()
    demandes = [a["messages"][0]["content"] for a in appels_de("écrire UN exercice")]
    assert "centre d'intérêt de l'élève : sport" in demandes[0]
    assert "centre d'intérêt de l'élève : cuisine" in demandes[1]


def test_sans_centre_d_interet_vie_quotidienne():
    assert "vie quotidienne" in T.consigne_mission({"interets": []}, 0)
