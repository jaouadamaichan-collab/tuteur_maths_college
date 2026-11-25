"""Flashcards : cartes vérifiées, série où une carte « à revoir » repasse, pile à revoir d'une séance à l'autre."""

import anthropic
import pytest

import flashcards as F
import tuteur as T
from tests.faux_claude import CARTES, FauxClaude, appels_de


@pytest.fixture(autouse=True)
def claude(monkeypatch):
    FauxClaude.reinitialiser()
    monkeypatch.setattr(anthropic, "Anthropic", FauxClaude)


def carte(recto, verso="réponse", **kw):
    return {"recto": recto, "verso": verso, **kw}


# ───────────── Validation ─────────────

def test_cartes_valides_et_schemas_verifies():
    cartes = F.valider_cartes({"cartes": CARTES})
    assert len(cartes) == 5 and cartes[2]["figure"]["type"] == "triangle_rectangle" and cartes[0]["figure"] is None


def test_doublons_cartes_vides_et_schema_faux_ecartes():
    cartes = F.valider_cartes([carte("Unité de la tension ?", "Le volt (V)"), carte("unité de  la TENSION ?"),
                               carte("", "x"), carte("Question sans réponse", ""), "pas une carte",
                               carte("Quelle molécule ?", "H₂O", figure={"type": "cone", "r": -1, "h": 4, "g": None}),
                               carte("Unité de l'intensité ?", "L'ampère (A)")])
    assert [c["recto"] for c in cartes] == ["Unité de la tension ?", "Quelle molécule ?", "Unité de l'intensité ?"]
    assert cartes[1]["figure"] is None          # schéma invalide retiré, carte gardée


def test_trop_peu_de_cartes_refuse():
    with pytest.raises(F.CartesInvalides):
        F.valider_cartes([carte("Une seule question ?")])
    with pytest.raises(F.CartesInvalides):
        F.valider_cartes({"pas": "de cartes"})


# ───────────── Série de révision ─────────────

def serie(n=3):
    return F.nouvelle_revision([carte(f"Question {i} ?", f"Réponse {i}") for i in range(n)], {"nom": "Inès"}, melanger=False)


def test_on_ne_note_pas_une_carte_non_retournee():
    r = serie()
    F.noter(r, True)
    assert F.progression(r) == (0, 3)


def test_carte_a_revoir_repasse_une_seule_fois():
    r = serie()
    for sue in (True, False, True):        # Q0 sue, Q1 à revoir, Q2 sue
        F.retourner(r)
        F.noter(r, sue)
    assert not r["termine"] and F.carte_courante(r)["recto"] == "Question 1 ?"
    F.retourner(r)
    F.noter(r, False)                       # encore à revoir : elle ne repasse plus
    assert r["termine"] and F.carte_courante(r) is None
    assert F.bilan(r) == {"cartes": 3, "sues": 2, "du_premier_coup": 2, "a_revoir": 1, "points": 4}


def test_carte_sue_au_second_passage():
    r = serie(2)
    F.retourner(r); F.noter(r, False)
    F.retourner(r); F.noter(r, True)
    F.retourner(r); F.noter(r, True)
    assert F.bilan(r) == {"cartes": 2, "sues": 2, "du_premier_coup": 1, "a_revoir": 0, "points": 4}


def test_pile_a_revoir_selon_la_derniere_note():
    ancien = {"type": "flashcards", "cartes": [carte("A ?", sue=False), carte("B ?", sue=False), carte("C ?", sue=True)]}
    recent = {"type": "flashcards", "cartes": [carte("a ?", sue=True), carte("D ?", sue=False)]}
    exercices = {"resultats": [], "stats": {"exercices": 6}}
    assert [c["recto"] for c in F.cartes_a_revoir([recent, exercices, ancien])] == ["D ?", "B ?"]


def test_contenu_enregistre():
    r = serie(2)
    F.retourner(r); F.noter(r, True)
    F.retourner(r); F.noter(r, False)
    F.retourner(r); F.noter(r, False)
    c = F.contenu_a_enregistrer(r)
    assert c["type"] == "flashcards" and c["points"] == 2 and [x["sue"] for x in c["cartes"]] == [True, False]
    assert F.cartes_a_revoir([c]) == [{"recto": "Question 1 ?", "verso": "Réponse 1", "figure": None}]


# ───────────── Le tuteur ─────────────

PROFIL = {"nom": "Inès", "classe": "4ème", "programme": "France", "chapitre": "Pyramides et cônes (volumes)", "theme_libre": False}


def test_tuteur_ecrit_les_cartes_du_chapitre():
    cartes = T.generer_cartes("k", PROFIL, 10, deja=["Quelle est l'aire d'un carré de côté 3 cm ?"])
    assert len(cartes) == 5
    appel = appels_de("écrire des flashcards")[0]
    demande = appel["messages"][0]["content"]
    assert "Pyramides et cônes (volumes)" in demande and "Nombre de cartes : 10" in demande and "aire d'un carré" in demande
    assert '"type": "cone"' in appel["system"] and "{figures}" not in appel["system"]


def test_tuteur_reessaie_puis_abandonne():
    FauxClaude.cartes_invalides = 1
    assert len(T.generer_cartes("k", PROFIL, 5)) == 5 and len(appels_de("écrire des flashcards")) == 2
    FauxClaude.reinitialiser()
    FauxClaude.cartes_invalides = 2
    with pytest.raises(T.TuteurIndisponible):
        T.generer_cartes("k", PROFIL, 5)
