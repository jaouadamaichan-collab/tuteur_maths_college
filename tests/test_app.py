"""Test de bout en bout de l'app collège : IA et Supabase simulés, interface réellement exécutée."""

import json
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_supabase import FauxSupabase  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app.py")


class FausseReponse:
    def __init__(self, texte):
        self.content = [type("B", (), {"text": texte, "type": "text"})()]


class FauxAnthropic:
    appels = []

    def __init__(self, api_key):
        self.messages = self

    def create(self, **kw):
        assert "temperature" not in kw                  # paramètre refusé par l'API en production
        FauxAnthropic.appels.append(kw)
        dernier = kw["messages"][-1]["content"]
        if "bilan" in dernier.lower():
            return FausseReponse("**Bilan** : Pythagore maîtrisé avec aide. Prochaine étape : réciproque.")
        return FausseReponse("**Exercice 1** : calcule l'hypoténuse si \\( a = 3 \\) et \\( b = 4 \\).")


@pytest.fixture
def base(monkeypatch):
    import anthropic
    import supabase

    db = FauxSupabase()
    FauxAnthropic.appels = []
    monkeypatch.setattr(anthropic, "Anthropic", FauxAnthropic)
    monkeypatch.setattr(supabase, "create_client", lambda url, key: db)
    return db


def lancer(secrets):
    at = AppTest.from_file(APP, default_timeout=30)
    at.secrets.update(secrets)
    at.run()
    assert not at.exception, at.exception
    return at


SECRETS = {"ANTHROPIC_API_KEY": "sk-test", "SUPABASE_URL": "https://x.supabase.co", "SUPABASE_KEY": "sb_secret_test"}


def test_parcours_eleve_complet(base):
    at = lancer(SECRETS)
    assert "Collège" in at.markdown[0].value or any("Collège" in m.value for m in at.markdown)
    at.sidebar.text_input[0].input("Inès")
    at.sidebar.selectbox[1].set_value("4ème").run()
    assert "Théorème de Pythagore" in at.sidebar.selectbox[2].options
    at.sidebar.selectbox[2].set_value("Théorème de Pythagore").run()
    next(b for b in at.sidebar.button if "Commencer" in b.label).click().run()
    assert not at.exception, at.exception

    systeme = FauxAnthropic.appels[0]["system"]
    assert "collégiens" in systeme and "Classe : 4ème" in systeme and "Pythagore" in systeme
    affiche = " ".join(m.markdown[0].value for m in at.chat_message if m.markdown)
    assert "$a = 3$" in affiche and "\\(" not in affiche          # \( … \) converti en $ … $ pour Streamlit

    at.chat_input[0].set_value("c = 5").run()
    assert len(FauxAnthropic.appels) == 2

    next(b for b in at.sidebar.button if "Bilan" in b.label).click().run()
    assert not at.exception, at.exception
    lignes = base.tables["sessions_college"]
    assert len(lignes) == 1 and lignes[0]["eleve_nom"] == "Inès" and lignes[0]["classe"] == "4ème"
    assert "Pythagore" in lignes[0]["bilan"]
    assert "sessions" not in base.tables                       # jamais la table du lycée


def test_espace_prof_affiche_la_seance(base):
    base.table("sessions_college").insert({"eleve_nom": "Inès", "classe": "4ème", "chapitre": "Théorème de Pythagore",
                                           "nb_exercices": 2, "phase_finale": "bilan", "bilan": "ok", "date_session": "2026-11-11T10:00:00"}).execute()
    at = lancer(SECRETS)
    at.sidebar.radio[0].set_value(at.sidebar.radio[0].options[1]).run()
    at.text_input[0].input("prof2024").run()
    assert not at.exception, at.exception
    assert any("Inès" in e.label for e in at.expander)


@pytest.mark.parametrize("secrets", [
    {"ANTHROPIC_API_KEY": "sk-test"},                                                                      # pas de base
    {**SECRETS, "SUPABASE_KEY": "sb_publishable_xxx"},                                                     # clé publique refusée
])
def test_sans_base_valide_l_espace_prof_explique_quoi_faire(base, secrets):
    at = lancer(secrets)
    at.sidebar.radio[0].set_value(at.sidebar.radio[0].options[1]).run()
    assert "SUPABASE_KEY" in at.warning[0].value and "secrète" in at.warning[0].value
