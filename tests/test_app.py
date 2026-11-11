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


def test_trois_facons_de_choisir_le_theme_visibles_a_l_accueil(base):
    at = lancer()
    modes = at.button_group(key="mode_theme")
    assert [o.strip() for o in modes.options] == ["Un chapitre", "Mon exercice de classe", "Un autre thème"]   # emojis affichés en icônes
    assert modes.value == "📖 Un chapitre" and any(s.label == "📖 Chapitre" for s in at.selectbox)


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
    at.button_group(key="mode_theme").set_value("✏️ Un autre thème").run()
    assert not any(s.label == "📖 Chapitre" for s in at.selectbox)       # plus de liste de chapitres
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


# ───────────── Étape 3 : progression, centres d'intérêt, espace prof ─────────────

def seance_complete(at, interets=()):
    at.text_input[0].input("Inès")
    at.selectbox[0].set_value("4ème").run()
    at.selectbox[1].set_value("Pyramides et cônes (volumes)").run()
    if interets:
        at.multiselect[0].set_value(list(interets)).run()
    at.select_slider[0].set_value("15 min").run()
    bouton(at, "🚀 Commencer").click().run()
    ok(at)
    for n in range(6):
        repondre_juste(at)
        bouton(at, "Voir mon bilan" if n == 5 else "Exercice suivant").click().run()
        ok(at)
    return at.session_state["seance"]


def test_deux_seances_points_et_badges_cumules(base):
    at = lancer()
    s1 = seance_complete(at, interets=["⚽ Sport"])
    assert "seance_terminee" in s1["badges_nouveaux"]
    assert any("Nouveaux badges" in m.value for m in at.success)
    assert "centre d'intérêt de l'élève : sport" in appels_de("écrire UN exercice")[0]["messages"][0]["content"]
    enregistre = json.loads(base.tables["sessions_college"][0]["messages"])
    assert enregistre["badges"] == s1["badges_nouveaux"] and enregistre["interets"] == ["⚽ Sport"]

    # Deuxième séance, même prénom : accueil personnalisé, total cumulé, badges non redonnés
    bouton(at.sidebar, "🗑️ Nouvelle séance").click().run()
    ok(at)
    at.text_input[0].input("Inès").run()
    accueil = " ".join(m.value for m in at.success)
    assert f"Tu as **{s1['points']} points**" in accueil and "Séance terminée" in accueil
    s2 = seance_complete(at)
    assert s2["points_avant"] == s1["points"]
    assert not set(s2["badges_nouveaux"]) & set(s1["badges_nouveaux"])
    assert any(f"Ton total : {s1['points'] + s2['points']} points" in c.value for c in at.caption)
    assert len(base.tables["sessions_college"]) == 2                    # la deuxième séance est bien enregistrée


def test_espace_prof_vue_par_eleve(base):
    at = lancer()
    s = seance_complete(at)
    at.sidebar.radio[0].set_value(at.sidebar.radio[0].options[1]).run()
    at.text_input[0].input("prof2024").run()
    ok(at)
    vue = at.dataframe[0].value
    ligne = vue[vue["Élève"] == "Inès"].iloc[0]
    assert ligne["Points"] == s["points"] and ligne["Séances"] == 1 and ligne["Sans aide"] == "100 %"
    assert "🏁" in ligne["Badges"]
    detail = " ".join(m.value for m in at.markdown)
    assert "**Réussis :** 6 / 6" in detail and "Badges gagnés" in detail


# ───────────── Étape 4 : exercice modèle photographié (ADR 0002) ─────────────

def _png():
    import io
    from PIL import Image
    sortie = io.BytesIO()
    Image.new("RGB", (900, 600), "white").save(sortie, format="PNG")
    return sortie.getvalue()


def _choisir_photo(at):
    at.text_input[0].input("Inès")
    at.selectbox[0].set_value("4ème").run()
    at.button_group(key="mode_theme").set_value("📸 Mon exercice de classe").run()
    ok(at)


def _lire(at, octets=None):
    at.file_uploader[0].set_value(("exo.png", octets or _png(), "image/png")).run()
    bouton(at, "🔍 Lire l'exercice").click().run()
    ok(at)


def test_photo_lue_verifiee_puis_seance_de_variantes(base):
    at = lancer()
    _choisir_photo(at)
    assert any("jamais enregistrée" in c.value for c in at.caption)
    _lire(at)
    # La photo est oubliée : plus de champ photo, seul le texte lu reste, et l'élève peut le corriger
    assert len(at.file_uploader) == 0
    lecture = at.session_state["lecture"]
    assert not any(isinstance(v, bytes) for v in lecture.values())
    champ = at.text_area(key="transcription")
    assert champ.value == FauxClaude.LECTURE["transcription"]
    corrige = champ.value.replace("10 cm", "10 cm (génératrice)")
    champ.input(corrige).run()
    at.select_slider[0].set_value("15 min").run()
    bouton(at, "🚀 Commencer").click().run()
    ok(at)
    s = at.session_state["seance"]
    assert s["profil"]["modele"] == corrige and s["profil"]["chapitre"] == "📸 hauteur et volume du cône"
    assert "lecture" not in at.session_state
    assert corrige in appels_de("écrire UN exercice")[0]["messages"][0]["content"]
    for n in range(6):
        repondre_juste(at)
        bouton(at, "Voir mon bilan" if n == 5 else "Exercice suivant").click().run()
        ok(at)
    assert any("refais ton exercice de classe" in m.value for m in at.markdown)
    # Enregistré : la transcription confirmée, jamais l'image
    ligne = base.tables["sessions_college"][0]
    assert json.loads(ligne["messages"])["modele"] == corrige
    assert len(json.dumps(ligne, ensure_ascii=False)) < 20_000 and "base64" not in json.dumps(ligne)
    # L'espace prof montre la transcription
    at.sidebar.radio[0].set_value(at.sidebar.radio[0].options[1]).run()
    at.text_input[0].input("prof2024").run()
    ok(at)
    assert any(corrige in t.value for t in at.text)


def test_photo_sans_lecture_on_ne_demarre_pas(base):
    at = lancer()
    _choisir_photo(at)
    bouton(at, "🚀 Commencer").click().run()
    assert any("Lire l'exercice" in w.value for w in at.warning)
    assert at.session_state["seance"] is None and FauxClaude.appels == []


@pytest.mark.parametrize("lecture, octets, message", [
    ({"lisible": False, "maths": True, "transcription": "", "notion": ""}, None, "reprends la photo"),
    ({"lisible": True, "maths": False, "transcription": "Liste de courses", "notion": ""}, None, "ne semble pas montrer un exercice de maths"),
    (None, b"pas une image", "pas une photo lisible"),
])
def test_photo_refusee_explique_quoi_faire(base, lecture, octets, message):
    if lecture:
        FauxClaude.lecture = lecture
    at = lancer()
    _choisir_photo(at)
    _lire(at, octets)
    assert any(message in w.value for w in at.warning)
    assert "lecture" not in at.session_state
    assert at.file_uploader[0].key == "photo_1" and at.file_uploader[0].value is None   # champ vidé, on peut réessayer


def test_autre_photo_efface_la_lecture(base):
    at = lancer()
    _choisir_photo(at)
    _lire(at)
    bouton(at, "📸 Prendre une autre photo").click().run()
    ok(at)
    assert "lecture" not in at.session_state and len(at.file_uploader) == 1


def test_exercice_vide_affiche_reessayer_au_lieu_de_planter(base):
    """Bug vu en production : exercice vide sans message d'erreur → TypeError à l'affichage."""
    at = lancer()
    demarrer(at)
    s = at.session_state["seance"]
    s["exercice"], s["erreur"] = None, None
    at.run()
    ok(at)
    assert any("Réessaie" in e.value for e in at.error)
    bouton(at, "Réessayer").click().run()
    ok(at)
    assert at.session_state["seance"]["exercice"] is not None
