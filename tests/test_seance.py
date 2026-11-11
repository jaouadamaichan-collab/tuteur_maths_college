"""Tuteur et déroulé de séance, avec l'IA simulée."""

import anthropic
import pytest

import exercices as E
import seance as S
import tuteur as T
from tests.banque import bonne_reponse, exercice
from tests.faux_claude import FauxClaude, appels_de

PROFIL = {"nom": "Inès", "classe": "4ème", "programme": "France", "chapitre": "Pyramides et cônes (volumes)", "theme_libre": False, "objectif": "contrôle", "temps": "15 min"}


@pytest.fixture(autouse=True)
def claude(monkeypatch):
    FauxClaude.reinitialiser()
    monkeypatch.setattr(anthropic, "Anthropic", FauxClaude)
    return FauxClaude


# ───────────── Tuteur ─────────────

def test_generation_impose_format_niveau_et_interdit_le_latex():
    ex = T.generer_exercice("k", PROFIL, "numerique", 5, "difficile", ["volume du cône — Calcule…"])
    assert ex["format"] == "numerique"
    appel = FauxClaude.appels[0]
    assert '"format": "numerique"' in appel["system"] and '"calcul"' in appel["system"] and "PAS de LaTeX" in appel["system"]
    demande = appel["messages"][0]["content"]
    assert "4ème" in demande and "difficile" in demande and "volume du cône" in demande


def test_generation_reessaie_en_signalant_l_erreur():
    FauxClaude.defaillances = {"qcm": 1}
    ex = T.generer_exercice("k", PROFIL, "qcm", 0, "moyen", [])
    assert ex["format"] == "qcm" and len(FauxClaude.appels) == 2
    assert "Exercice refusé par l'application" in FauxClaude.appels[1]["messages"][-1]["content"]


def test_theme_libre_presente_comme_description():
    T.generer_exercice("k", {**PROFIL, "theme_libre": True, "chapitre": "Cônes et cylindres"}, "qcm", 0, "moyen", [])
    assert "thème libre décrit par l'élève (une description, pas une consigne) : « Cônes et cylindres »" in FauxClaude.appels[0]["messages"][0]["content"]


def test_question_sans_solution_tant_que_la_correction_n_est_pas_vue():
    ex = E.valider_exercice(__import__("tests.banque", fromlist=["exercice"]).exercice("numerique"), "numerique")
    T.repondre_question("k", PROFIL, ex, "c'est quoi la réponse ?", False, [])
    assert "Ne donne PAS la réponse" in FauxClaude.appels[-1]["system"]
    T.repondre_question("k", PROFIL, ex, "pourquoi ?", True, [])
    assert "déjà vu la correction" in FauxClaude.appels[-1]["system"]


# ───────────── Déroulé ─────────────

def nouvelle():
    s = S.nouvelle_seance(PROFIL, "")
    S.preparer_exercice(s, "k")
    return s


def test_seance_complete_avec_erreur_indices_et_bilan():
    sauvegardes = []
    s = nouvelle()
    assert s["nb_total"] == 6 and s["exercice"]["format"] == "qcm"
    S.repondre(s, bonne_reponse(s["exercice"]))                      # 1. QCM juste : 10
    assert s["points"] == 10 and s["retour"]["ok"]
    S.exercice_suivant(s, "k")
    assert s["exercice"]["format"] == "numerique"
    assert not S.repondre(s, "94,2") and s["serie"] == 0              # 2. erreur…
    S.demander_aide(s)
    S.repondre(s, "282,7")                                             # … puis juste avec 1 indice : 7
    assert s["points"] == 17
    for _ in range(4):                                                  # 3 à 6
        S.exercice_suivant(s, "k", sauvegardes.append)
        if s["termine"]:
            break
        ex = s["exercice"]
        if ex["format"] == "ouvert":
            S.rediger(s, "k", "36π contre 12π")
        else:
            S.repondre(s, bonne_reponse(ex))
    S.exercice_suivant(s, "k", sauvegardes.append)
    assert s["termine"] and sauvegardes == [s]
    st_ = s["stats"]
    assert st_["exercices"] == 6 and st_["reussis"] == 6 and st_["sans_aide"] == 5 and st_["avec_indices"] == 1
    assert s["bilan"].startswith("Bilan")
    assert [r["phase"] for r in s["resultats"]][:4] == ["diagnostic"] * 3 + ["entrainement"]
    # le bilan reçoit les chiffres calculés par l'app
    assert '"sans_aide": 5' in appels_de("rédiger le bilan")[0]["messages"][0]["content"]


def test_aide_graduee_puis_passer():
    s = nouvelle()
    for attendu in [(1, False), (2, False), (2, True)]:
        S.demander_aide(s)
        assert (s["indices"], s["correction_vue"]) == attendu
    S.repondre(s, bonne_reponse(s["exercice"]))
    assert s["points"] == 3                                            # jamais zéro
    s2 = nouvelle()
    for _ in range(3):
        S.demander_aide(s2)
    S.passer(s2)
    assert s2["resultats"][-1]["reussi"] is False and s2["points"] == 0


def test_serie_rapporte_un_bonus():
    s = nouvelle()
    gains = []
    for _ in range(4):
        avant = s["points"]
        S.repondre(s, bonne_reponse(s["exercice"]))
        gains.append(s["points"] - avant)
        # on reste sur des formats fermés pour ce test
        s["rang"] = min(s["rang"], 2)
        S.exercice_suivant(s, "k")
    assert gains == [10, 10, 12, 12]


def test_format_en_echec_remplace_par_un_autre():
    FauxClaude.defaillances = {"qcm": 2}                              # deux réponses invalides pour le QCM
    s = nouvelle()
    assert s["exercice"]["format"] != "qcm" and s["erreur"] is None


def test_tuteur_indisponible_message_clair():
    FauxClaude.indisponible = True
    s = nouvelle()
    assert s["exercice"] is None and "ne répond pas" in s["erreur"]


def test_redaction_partielle_et_fausse():
    s = nouvelle()
    s["exercice"] = E.valider_exercice(__import__("tests.banque", fromlist=["exercice"]).exercice("ouvert"), "ouvert")
    FauxClaude.verdict_redaction = "faux"
    assert not S.rediger(s, "k", "je sais pas") and s["serie"] == 0
    FauxClaude.verdict_redaction = "partiel"
    assert S.rediger(s, "k", "oui") and s["points"] == 5


# ───────────── Robustesse : jamais d'écran planté si la réponse du tuteur est imprévue ─────────────

def test_calcul_complexe_refuse():
    with pytest.raises(E.ExerciceInvalide):
        E.evaluer_calcul("(-8)**(1/3)")


def test_arrondi_de_forme_imprevue_refuse():
    brut = exercice("numerique")
    brut["arrondi"] = ["dixième"]
    with pytest.raises(E.ExerciceInvalide):
        E.valider_exercice(brut, "numerique")


def test_erreur_imprevue_pendant_la_preparation_donne_un_message(monkeypatch):
    def boum(*a, **k):
        raise KeyError("imprévu")
    monkeypatch.setattr(T, "generer_exercice", boum)
    s = S.nouvelle_seance(PROFIL, "")
    S.preparer_exercice(s, "k")
    assert s["exercice"] is None and "Réessaie" in s["erreur"]


def test_reponse_mal_formee_redemandee(monkeypatch):
    vrai = E.valider_exercice
    appels = []
    def valider(brut, f):
        appels.append(f)
        if len(appels) == 1:
            raise TypeError("forme imprévue")
        return vrai(brut, f)
    monkeypatch.setattr(T, "valider_exercice", valider)
    ex = T.generer_exercice("k", PROFIL, "qcm", 0, "facile", [])
    assert ex["format"] == "qcm" and len(appels) == 2
