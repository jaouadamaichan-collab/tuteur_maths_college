"""Contrat d'exercice, correction par le code, rotation des formats, barème (ADR 0001)."""

import random

import pytest

import exercices as E
from figures import FigureInvalide, TYPES, dessiner, valider_figure
from tests.banque import BANQUE, bonne_reponse, exercice


# ───────────── Contrat ─────────────

@pytest.mark.parametrize("format_", E.FORMATS)
def test_chaque_format_de_la_banque_est_valide(format_):
    ex = E.valider_exercice(exercice(format_), format_)
    assert ex["format"] == format_ and len(ex["indices"]) == 2
    if format_ in E.FORMATS_FERMES:
        assert E.est_juste(ex, bonne_reponse(ex))


def test_format_different_de_celui_impose_refuse():
    with pytest.raises(E.ExerciceInvalide, match="au lieu"):
        E.valider_exercice(exercice("qcm"), "vf")


@pytest.mark.parametrize("modif, motif", [
    (lambda e: e.update(bonne_option="π × r²"), "bonne option"),
    (lambda e: e.update(options=["a", "a", "b", "c"], bonne_option="a"), "double"),
    (lambda e: e.update(indices=["un seul"]), "deux indices"),
    (lambda e: e.pop("correction"), "correction"),
    (lambda e: e.update(enonce="  "), "enonce"),
])
def test_qcm_mal_forme_refuse(modif, motif):
    brut = exercice("qcm")
    modif(brut)
    with pytest.raises(E.ExerciceInvalide, match=motif):
        E.valider_exercice(brut, "qcm")


def test_corrige_numerique_faux_intercepte_par_le_double_calcul():
    brut = exercice("numerique")
    brut["reponse"] = 94.2  # oubli du carré : le tuteur s'est trompé
    with pytest.raises(E.ExerciceInvalide, match="incohérent"):
        E.valider_exercice(brut, "numerique")


def test_numerique_arrondi_a_l_unite():
    brut = exercice("numerique")
    brut.update(reponse=283, arrondi="unité")
    ex = E.valider_exercice(brut, "numerique")
    assert E.est_juste(ex, "283") and E.est_juste(ex, "283,0")
    assert not E.est_juste(ex, "282,7") and not E.est_juste(ex, "282") and not E.est_juste(ex, "283,4")
    assert "arrondi" in E.detail_erreur(ex, "282,7")


def test_trous_nombre_de_marques_controle():
    brut = exercice("trous")
    brut["texte"] = "Le triangle est ___."
    with pytest.raises(E.ExerciceInvalide, match="marques"):
        E.valider_exercice(brut, "trous")


def test_figure_incoherente_refusee():
    brut = exercice("vf")
    brut["figure"] = {"type": "cone", "r": 3, "h": 4, "g": 6}
    with pytest.raises(FigureInvalide):
        E.valider_exercice(brut, "vf")


def test_options_et_etapes_melangees_mais_corrigees_juste():
    random.seed(1)
    ordre = E.valider_exercice(exercice("ordre"), "ordre")
    assert ordre["melange"] != ordre["etapes"] and sorted(ordre["melange"]) == sorted(ordre["etapes"])
    assert not E.est_juste(ordre, ordre["melange"])
    vus = {tuple(E.valider_exercice(exercice("qcm"), "qcm")["options"]) for _ in range(20)}
    assert len(vus) > 1  # la bonne option n'est pas toujours à la même place


# ───────────── Calcul sûr ─────────────

@pytest.mark.parametrize("expr, attendu", [
    ("pi*3**2*4/3", 37.6991), ("sqrt(25-9)", 4), ("√(16)", 4), ("2×3÷4", 1.5), ("π*2^2", 12.5664), ("-3+5", 2),
])
def test_evaluer_calcul(expr, attendu):
    assert E.evaluer_calcul(expr) == pytest.approx(attendu, abs=1e-3)


@pytest.mark.parametrize("expr", ["__import__('os').system('ls')", "open('x')", "(1).__class__", "2**999", "1/0", "x+1", "lambda: 1", "[1,2]"])
def test_evaluer_calcul_refuse_tout_le_reste(expr):
    with pytest.raises(E.ExerciceInvalide):
        E.evaluer_calcul(expr)


@pytest.mark.parametrize("saisie, attendu", [("282,7", 282.7), (" 282.7 cm³", 282.7), ("1 000,5", 1000.5), ("-3", -3.0), ("abc", None), ("", None)])
def test_lire_nombre(saisie, attendu):
    assert E.lire_nombre(saisie) == attendu


def test_detail_erreur_ne_donne_pas_la_reponse():
    ex = E.valider_exercice(exercice("numerique"), "numerique")
    assert not E.est_juste(ex, "282,74") and "arrondi" in E.detail_erreur(ex, "282,74")
    assert "282" not in E.detail_erreur(ex, "282,9")
    vf = E.valider_exercice(exercice("vf"), "vf")
    assert E.detail_erreur(vf, [True, True, True]) == "2 sur 3 correctes."


# ───────────── Déroulé ─────────────

def test_rotation_des_formats():
    r = random.Random(0)
    formats = []
    for rang in range(30):
        formats.append(E.choisir_format(rang, formats, r))
    assert formats[:3] == ["qcm", "numerique", "vf"]
    assert all(a != b for a, b in zip(formats, formats[1:]))                       # jamais deux fois de suite
    assert [i for i, f in enumerate(formats) if f == "ouvert"] == [7, 12, 17, 22, 27]  # 1 sur 5 à l'entraînement
    entrainement = formats[3:]
    comptes = {f: entrainement.count(f) for f in E.FORMATS_FERMES}
    assert max(comptes.values()) - min(comptes.values()) <= 1                         # usage équilibré


def test_niveau_s_adapte():
    ok = {"reussi": True, "indices": 0, "correction_vue": False}
    assert E.niveau_suivant([ok, ok], "moyen") == "difficile"
    assert E.niveau_suivant([ok, ok], "difficile") == "difficile"
    assert E.niveau_suivant([ok, {"reussi": True, "indices": 0, "correction_vue": True}], "moyen") == "facile"
    assert E.niveau_suivant([ok, {"reussi": True, "indices": 1, "correction_vue": False}], "moyen") == "moyen"


def test_bareme():
    assert E.points(0, False, 1) == (10, 0)
    assert E.points(1, False, 1) == (7, 0)
    assert E.points(2, False, 2) == (5, 0)
    assert E.points(2, True, 1) == (3, 0)        # jamais zéro
    assert E.points(0, False, 3) == (10, 2)      # bonus de série
    assert E.points(0, False, 1, partiel=True) == (5, 0)


def test_statistiques():
    res = [
        {"phase": "diagnostic", "format": "qcm", "reussi": True, "indices": 0, "correction_vue": False, "essais": 1, "points": 10, "notion": "a"},
        {"phase": "entrainement", "format": "ordre", "reussi": True, "indices": 2, "correction_vue": True, "essais": 3, "points": 3, "notion": "b"},
        {"phase": "entrainement", "format": "ordre", "reussi": False, "indices": 2, "correction_vue": True, "essais": 2, "points": 0, "notion": "b"},
    ]
    s = E.statistiques(res)
    assert (s["exercices"], s["reussis"], s["sans_aide"], s["correction_vue"], s["points"]) == (3, 2, 1, 2, 13)
    assert s["formats_difficiles"] == ["ordre"] and s["notions_difficiles"] == ["b"]


# ───────────── Figures ─────────────

@pytest.mark.parametrize("brut", [
    {"type": "cone", "r": 3, "h": None, "g": 5}, {"type": "cylindre", "r": 3, "h": 10}, {"type": "triangle_rectangle", "ab": 3, "bc": 4, "ac": None},
    {"type": "pave", "longueur": 6, "largeur": 4, "hauteur": 2.5}, {"type": "pyramide", "cote": 6, "h": None}, {"type": "cercle", "r": 2},
    {"type": "repere_droite", "a": -0.5, "b": 2},
])
def test_chaque_figure_se_dessine(brut):
    png = dessiner(valider_figure(brut))
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_catalogue_complet():
    assert set(TYPES) == {"cone", "cylindre", "triangle_rectangle", "pave", "pyramide", "cercle", "repere_droite"}


@pytest.mark.parametrize("brut", [
    {"type": "cone", "r": 3, "h": 4, "g": 6}, {"type": "cone", "r": 3, "h": 5, "g": 4}, {"type": "triangle_rectangle", "ab": 5, "bc": 4, "ac": 3},
    {"type": "triangle_rectangle", "ab": 3, "bc": None, "ac": None}, {"type": "cercle", "r": -1}, {"type": "etoile"}, {"type": "cylindre", "r": "3"},
])
def test_figure_invalide(brut):
    with pytest.raises(FigureInvalide):
        valider_figure(brut)


def test_pas_de_figure():
    assert valider_figure(None) is None and valider_figure({}) is None
