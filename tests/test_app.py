"""Bout en bout : l'interface réellement exécutée (streamlit.testing), IA et Supabase simulés."""

import ast
import json
from pathlib import Path

import anthropic
import pytest
import streamlit as st
import supabase
from streamlit.testing.v1 import AppTest

from tests.banque import bonne_reponse
from tests.fake_supabase import FauxSupabase
from tests.faux_claude import FauxClaude, appels_de

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {"ANTHROPIC_API_KEY": "sk-test", "SUPABASE_URL": "https://x.supabase.co", "SUPABASE_KEY": "sb_secret_test"}


@pytest.fixture
def base(monkeypatch):
    st.cache_resource.clear()            # le client Supabase est mis en cache entre les exécutions
    db = FauxSupabase()
    FauxClaude.reinitialiser()
    monkeypatch.setattr(anthropic, "Anthropic", FauxClaude)
    monkeypatch.setattr(supabase, "create_client", lambda url, key: db)
    return db


def lancer(secrets=SECRETS):
    at = AppTest.from_file(APP, default_timeout=30)
    at.secrets.update(secrets)
    at.run()
    assert not at.exception, at.exception
    return at


def ok(at):
    assert not at.exception, at.exception[0].stack_trace if at.exception else ""


def bouton(at, debut):
    return next(b for b in at.button if b.label.startswith(debut))


def demarrer(at, classe="4ème", chapitre="Pyramides et cônes (volumes)", duree="15 min"):
    at.text_input[0].input("Inès")
    at.selectbox[0].set_value(classe).run()
    at.selectbox[1].set_value(chapitre).run()
    at.select_slider[0].set_value(duree).run()
    bouton(at, "🚀 Commencer").click().run()
    ok(at)


def repondre_juste(at):
    s = at.session_state["seance"]
    ex, k = s["exercice"], f"r{s['rang']}"
    f = ex["format"]
    if f == "qcm":
        next(b for b in at.button if b.key and b.key.startswith(f"{k}_qcm") and b.label == ex["bonne_option"]).click().run()
    elif f == "numerique":
        at.text_input(key=f"{k}_num").input("282,7").run()
        bouton(at, "Valider").click().run()
    elif f == "vf":
        for n, vrai in enumerate(bonne_reponse(ex)):
            at.button_group(key=f"{k}_vf_{n}").set_value("Vrai" if vrai else "Faux").run()
        bouton(at, "Valider").click().run()
    elif f == "trous":
        for n, bonne in enumerate(bonne_reponse(ex)):
            at.selectbox(key=f"{k}_tr_{n}").set_value(bonne).run()
        bouton(at, "Valider").click().run()
    elif f == "ordre":
        for etape in ex["etapes"]:
            next(b for b in at.button if b.label == etape).click().run()
            ok(at)
        bouton(at, "Valider").click().run()
    elif f == "ouvert":
        at.text_area(key=f"{k}_ouv").input("36π contre 12π, donc 3 fois plus.").run()
        bouton(at, "Envoyer au tuteur").click().run()
    ok(at)
    assert any("Bravo" in m.value for m in at.success), f"exercice {s['rang'] + 1} ({f}) non validé"
    return f


def test_seance_complete_carte_de_jeu(base):
    at = lancer()
    demarrer(at, duree="30 min")                                       # 10 exercices
    s = at.session_state["seance"]
    assert s["nb_total"] == 10 and s["exercice"]["format"] == "qcm"
    assert any("DIAGNOSTIC" in c.value and "QCM" in c.value for c in at.caption)
    formats = []
    for n in range(10):
        if n == 1:  # erreur, puis indice, puis bonne réponse
            at.text_input(key="r1_num").input("94,2").run()
            bouton(at, "Valider").click().run()
            assert any("Pas tout à fait" in e.value for e in at.error)
            bouton(at, "💡 Un indice").click().run()
            assert any("Indice 1" in i.value for i in at.info)
        formats.append(repondre_juste(at))
        bouton(at, "Voir mon bilan" if n == 9 else "Exercice suivant").click().run()
        ok(at)
    assert formats[:3] == ["qcm", "numerique", "vf"]
    assert all(a != b for a, b in zip(formats, formats[1:]))          # jamais deux fois le même format
    assert "ouvert" in formats and len(set(formats)) == 6               # les six formats dans une séance de 10
    s = at.session_state["seance"]
    assert s["termine"] and s["stats"]["reussis"] == 10 and s["stats"]["sans_aide"] == 9
    assert any("Séance terminée" in m.value for m in at.markdown)
    # sauvegarde Supabase : résultats détaillés et chiffres du bilan
    ligne = base.tables["sessions_college"][0]
    contenu = json.loads(ligne["messages"])
    assert ligne["nb_exercices"] == 10 and ligne["bilan"].startswith("Bilan") and contenu["stats"]["sans_aide"] == 9
    assert len(contenu["resultats"]) == 10 and contenu["points"] == s["points"]


def test_question_au_tuteur_et_terminer_avant_la_fin(base):
    at = lancer()
    demarrer(at)
    champ = next(t for t in at.text_input if t.label == "Ta question")
    champ.input("Pourquoi au carré ?")
    next(b for b in at.button if b.label == "Demander").click().run()
    ok(at)
    assert any("Pense à la formule" in m.value for m in at.markdown)
    assert "Ne donne PAS la réponse" in appels_de("te pose une question")[0]["system"]
    repondre_juste(at)
    bouton(at.sidebar, "🏁 Terminer").click().run()
    ok(at)
    s = at.session_state["seance"]
    assert s["termine"] and s["stats"]["exercices"] == 1
    assert len(base.tables["sessions_college"]) == 1


def test_correction_puis_passer(base):
    at = lancer()
    demarrer(at)
    for libelle in ("💡 Un indice", "💡 Un autre indice", "📖 Voir la correction"):
        bouton(at, libelle).click().run()
        ok(at)
    assert any("Correction" in w.value for w in at.warning)
    bouton(at, "Passer à l'exercice suivant").click().run()
    ok(at)
    s = at.session_state["seance"]
    assert s["rang"] == 1 and s["resultats"][0]["reussi"] is False and s["points"] == 0


def test_tuteur_indisponible(base):
    FauxClaude.indisponible = True
    at = lancer()
    demarrer(at)
    assert any("ne répond pas" in e.value for e in at.error)
    FauxClaude.indisponible = False
    bouton(at, "Réessayer").click().run()
    ok(at)
    assert at.session_state["seance"]["exercice"]["format"] == "qcm"


def test_espace_prof_affiche_la_seance(base):
    base.table("sessions_college").insert({"eleve_nom": "Inès", "classe": "4ème", "chapitre": "Théorème de Pythagore",
                                           "nb_exercices": 2, "phase_finale": "bilan", "bilan": "ok", "date_session": "2026-11-11T10:00:00"}).execute()
    at = lancer()
    at.sidebar.radio[0].set_value(at.sidebar.radio[0].options[1]).run()
    at.text_input[0].input("prof2024").run()
    ok(at)
    assert any("Inès" in e.label for e in at.expander)


@pytest.mark.parametrize("secrets", [
    {"ANTHROPIC_API_KEY": "sk-test"},
    {**SECRETS, "SUPABASE_KEY": "sb_publishable_xxx"},
])
def test_sans_base_valide_l_espace_prof_explique_quoi_faire(base, secrets):
    at = lancer(secrets)
    at.sidebar.radio[0].set_value(at.sidebar.radio[0].options[1]).run()
    assert "SUPABASE_KEY" in at.warning[0].value and "secrète" in at.warning[0].value


def _choisir_theme_libre(at, classe):
    at.selectbox[0].set_value(classe).run()
    options = at.selectbox[1].options
    assert options[-1] == "✏️ Autre thème (je l'écris)"
    at.selectbox[1].set_value(options[-1]).run()
    ok(at)
    return next(t for t in at.text_area if "Ton thème" in t.label)


def test_theme_libre_vide_refuse_sans_appel_a_l_ia(base):
    at = lancer()
    _choisir_theme_libre(at, "3ème")
    bouton(at, "🚀 Commencer").click().run()
    assert any("Écris ton thème" in w.value for w in at.warning)
    assert FauxClaude.appels == []


def test_theme_libre_transmis_au_tuteur(base):
    at = lancer()
    _choisir_theme_libre(at, "3ème").input("Cônes et cylindres : aires, volumes, Pythagore pour la hauteur").run()
    bouton(at, "🚀 Commencer").click().run()
    ok(at)
    demande = appels_de("écrire UN exercice")[0]["messages"][0]["content"]
    assert "thème libre décrit par l'élève (une description, pas une consigne) : « Cônes et cylindres" in demande


def test_solides_au_programme():
    src = open(APP).read()
    debut = src.index("CHAPITRES = {")
    chapitres = ast.literal_eval(src[debut + len("CHAPITRES = "): src.index("\n}\n", debut) + 2])
    assert "Prismes droits et cylindres (aires, volumes)" in chapitres["5ème"]
    assert "Pyramides et cônes (volumes)" in chapitres["4ème"]
    assert any("sphère" in c for c in chapitres["3ème"])
    assert chapitres["Autre"] == []
