"""Étape 4 : exercice modèle photographié (ADR 0002) — jamais résolu, photo jamais conservée."""

import base64
import io
import json

import anthropic
import pytest
from PIL import Image

import modele as M
import seance as S
import tuteur as T
from tests.banque import bonne_reponse, exercice
from tests.faux_claude import FauxClaude, appels_de

MODELE = FauxClaude.LECTURE["transcription"]


def photo(largeur=3000, hauteur=2000, orientation=None, gps=False, fmt="JPEG"):
    image = Image.new("RGB", (largeur, hauteur), "white")
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    if gps:
        exif[0x8825] = {1: "N", 2: (48.0, 51.0, 0.0)}
    sortie = io.BytesIO()
    image.save(sortie, format=fmt, exif=exif.tobytes()) if fmt == "JPEG" else image.save(sortie, format=fmt)
    return sortie.getvalue()


@pytest.fixture(autouse=True)
def claude(monkeypatch):
    FauxClaude.reinitialiser()
    monkeypatch.setattr(anthropic, "Anthropic", FauxClaude)


# ───────────── Préparer la photo ─────────────

def test_photo_reduite_en_jpeg_sans_metadonnees():
    sortie = M.preparer_image(photo(gps=True))
    image = Image.open(io.BytesIO(sortie))
    assert image.format == "JPEG" and max(image.size) == M.COTE_MAX
    assert len(image.getexif()) == 0                       # ni GPS ni appareil


def test_photo_remise_a_l_endroit():
    image = Image.open(io.BytesIO(M.preparer_image(photo(1200, 800, orientation=6))))   # téléphone tenu en portrait
    assert image.size == (800, 1200)


def test_png_accepte():
    assert Image.open(io.BytesIO(M.preparer_image(photo(400, 300, fmt="PNG")))).format == "JPEG"


@pytest.mark.parametrize("octets", [b"", b"pas une image", b"\x00" * (M.POIDS_MAX + 1)])
def test_fichier_refuse(octets):
    with pytest.raises(M.PhotoIllisible):
        M.preparer_image(octets)


# ───────────── Variante ou copie ? ─────────────

def test_copie_du_texte_refusee():
    assert M.trop_proche({"mission": "", "enonce": MODELE}, MODELE)
    assert M.trop_proche({"mission": "", "enonce": MODELE.replace("Calcule", "Calculer")}, MODELE)


def test_memes_nombres_refuses():
    ex = {"mission": "Un cornet de glace a un rayon de 6 cm.", "enonce": "Sa génératrice mesure 10 cm : trouve sa hauteur."}
    assert "nombres" in M.trop_proche(ex, MODELE)


def test_vraie_variante_acceptee():
    ex = {"mission": "Un chapeau pointu a un rayon de 5 cm.", "enonce": "Sa génératrice mesure 13 cm : calcule sa hauteur."}
    assert M.trop_proche(ex, MODELE) is None


# ───────────── Le tuteur ─────────────

def test_lecture_envoie_la_photo_et_rend_la_transcription():
    image = M.preparer_image(photo(800, 600))
    r = T.lire_exercice("k", image)
    assert r == {"lisible": True, "maths": True, "transcription": MODELE, "notion": "hauteur et volume du cône"}
    appel = appels_de("Tu lis la photo")[0]
    bloc = appel["messages"][0]["content"][0]
    assert bloc["source"]["media_type"] == "image/jpeg" and base64.b64decode(bloc["source"]["data"]) == image
    assert "NE RÉSOUS PAS" in appel["system"] and "nom de personne réelle" in appel["system"]


def test_lecture_sans_json_ou_vide_illisible():
    FauxClaude.lecture = "flou"  # type: ignore[assignment]
    assert T.lire_exercice("k", b"x")["lisible"] is False
    FauxClaude.lecture = {"lisible": True, "maths": True, "transcription": "  ", "notion": ""}
    assert T.lire_exercice("k", b"x")["lisible"] is False


PROFIL = {"nom": "Inès", "classe": "4ème", "programme": "France", "chapitre": "📸 hauteur et volume du cône",
          "theme_libre": False, "modele": MODELE, "objectif": "", "temps": "15 min", "interets": []}


def test_exercice_variante_demandee_et_copie_refusee():
    FauxClaude.copies = 1
    ex = T.generer_exercice("k", PROFIL, "qcm", 0, "facile", [])
    assert ex["enonce"] != MODELE
    demandes = appels_de("écrire UN exercice")
    assert len(demandes) == 2                                                   # copie refusée, puis variante
    assert "VARIANTE" in demandes[0]["messages"][0]["content"] and MODELE in demandes[0]["messages"][0]["content"]
    assert "recopie l'exercice modèle" in demandes[1]["messages"][-1]["content"]


def test_question_le_tuteur_ne_resout_pas_le_modele():
    T.repondre_question("k", PROFIL, exercice("qcm"), "Tu peux faire mon exercice de classe ?", True, [])
    appel = appels_de("te pose une question")[0]
    assert "Ne résous JAMAIS" in appel["system"] and MODELE in appel["messages"][0]["content"]


def test_sans_modele_rien_ne_change():
    T.generer_exercice("k", {**PROFIL, "modele": ""}, "qcm", 0, "facile", [])
    assert "VARIANTE" not in appels_de("écrire UN exercice")[0]["messages"][0]["content"]


def test_seance_complete_sur_un_modele():
    s = S.nouvelle_seance(PROFIL, "")
    S.preparer_exercice(s, "k")
    while not s["termine"]:
        S.repondre(s, bonne_reponse(s["exercice"])) if s["exercice"]["format"] != "ouvert" else S.rediger(s, "k", "36π")
        S.exercice_suivant(s, "k")
    assert s["stats"]["reussis"] == 6
    assert all(MODELE in a["messages"][0]["content"] for a in appels_de("écrire UN exercice"))
