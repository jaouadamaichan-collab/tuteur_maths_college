#!/usr/bin/env python3
"""
🎓 Tuteur de Maths IA — Collège (6ᵉ → 3ᵉ) — Application Streamlit + Supabase
Parcours personnalisé : diagnostic → entraînement → bilan, en exercices structurés
(QCM, réponse numérique, vrai ou faux, texte à trous, étapes dans l'ordre, réponse rédigée).
Le tuteur écrit les exercices, l'app choisit le format, corrige et tient le déroulé (docs/adr/0001).
"""

import html
import json
import os
from datetime import datetime

import streamlit as st

import ecran
import exercices as E
import flashcards as F
import modele as M
import progression as P
import seance as S
import tuteur as T
from tuteur import CENTRES_INTERET

# ════════════════════════════════════════════════════════════
# ⚙️  CONFIGURATION
# ════════════════════════════════════════════════════════════

CHAPITRES = {
    "6ème": [
        "Nombres entiers et décimaux",
        "Addition, soustraction, multiplication",
        "Division euclidienne et décimale",
        "Fractions (introduction)",
        "Proportionnalité (initiation)",
        "Géométrie plane (droites, segments, angles)",
        "Périmètres et aires",
        "Symétrie axiale",
        "Tableaux et graphiques",
    ],
    "5ème": [
        "Nombres relatifs",
        "Fractions (opérations)",
        "Proportionnalité et pourcentages",
        "Expressions littérales (initiation)",
        "Angles et parallélisme",
        "Triangles (construction, inégalité triangulaire)",
        "Symétrie centrale",
        "Parallélépipède, volumes",
        "Prismes droits et cylindres (aires, volumes)",
        "Statistiques (moyenne, médiane)",
    ],
    "4ème": [
        "Nombres relatifs (opérations)",
        "Fractions (opérations avancées)",
        "Calcul littéral (développer, factoriser)",
        "Équations du premier degré",
        "Théorème de Pythagore",
        "Translations et rotations",
        "Pyramides et cônes (volumes)",
        "Proportionnalité (4ᵉ proportionnelle, vitesse)",
        "Statistiques et probabilités",
        "Puissances",
    ],
    "3ème": [
        "Calcul numérique (racines carrées, puissances)",
        "Calcul littéral (identités remarquables)",
        "Équations et inéquations",
        "Fonctions (notion, linéaires, affines)",
        "Théorème de Thalès",
        "Trigonométrie dans le triangle rectangle",
        "Homothéties",
        "Géométrie dans l'espace (sphère, boule, sections de solides)",
        "Probabilités",
        "Statistiques (quartiles, étendue)",
        "Algorithmique et programmation (Scratch)",
    ],
    "Autre": [],
}

# Trois façons de choisir le thème, visibles d'emblée sur l'accueil (pas cachées au bas d'une liste) :
# un chapitre de la liste, l'exercice modèle photographié (ADR 0002), ou un thème libre écrit par l'élève.
MODE_CHAPITRE = "📖 Un chapitre"
PHOTO_THEME = "📸 Mon exercice de classe"
AUTRE_THEME = "✏️ Un autre thème"
MODES_THEME = [MODE_CHAPITRE, PHOTO_THEME, AUTRE_THEME]

PAYS_PROGRAMMES = [
    "France (Éducation Nationale)",
    "Belgique",
    "Suisse",
    "Canada (Québec)",
    "Maroc",
    "Tunisie",
    "Algérie",
    "Côte d'Ivoire",
    "Sénégal",
    "Autre (je préciserai)",
]

# Table Supabase de l'app maths collège (le lycée et la physique-chimie ont les leurs).
TABLE = "sessions_college"

MOT_DE_PASSE_PROF = "prof2024"


# ════════════════════════════════════════════════════════════
# 🎨  CSS GLOBAL
# ════════════════════════════════════════════════════════════

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@400;500;600;700&display=swap');

/* ── Jetons ───────────────────────────────────────────────
   fond menthe très clair, cartes blanches, menthe pour ce qui est mis en avant,
   bleu-vert profond pour les actions, ambre pour la série de jours, rose pour ce qui est à revoir. */
:root {
    --fond: #F4FAF8; --carte: #FFFFFF; --menthe: #D6F2EC; --menthe-fonce: #9BD3C7;
    --encre: #0E3B43; --texte: #23434A; --doux: #5F7C80; --trait: #DCEBE7;
    --ambre: #F4B740; --ambre-clair: #FFF3D6; --rose: #E0517A; --rose-clair: #FDE8EF;
}
.stApp { background: var(--fond); }
.stApp, .stMarkdown, .stMarkdown p, h1, h2, h3, h4, label, button, input, textarea, [data-testid="stWidgetLabel"] {
    font-family: 'Lexend', system-ui, sans-serif;
}
h1, h2, h3, h4 { color: var(--encre); letter-spacing: -0.01em; }
.stMarkdown p { color: var(--texte); }

/* ── Panneau de navigation (clair, comme la page) ─────────── */
[data-testid="stSidebar"] { background: var(--fond); border-right: 1px solid var(--trait); }
[data-testid="stSidebar"] .stMarkdown p { color: var(--texte); }
[data-testid="stSidebar"] [role="radiogroup"] { gap: .35rem; display: flex; flex-direction: column; align-items: stretch; }
[data-testid="stSidebar"] .stRadio, [data-testid="stSidebar"] .stRadio > div, [data-testid="stSidebar"] [role="radiogroup"] > * { width: 100%; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] { box-sizing: border-box;
    padding: .7rem 1rem; border-radius: 14px; border-left: 4px solid transparent; width: 100%; cursor: pointer; margin: 0;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child { display: none; }   /* pastille radio */
[data-testid="stSidebar"] [data-testid="stRadioOption"] p { font-size: 1.02rem; font-weight: 500; color: var(--doux); }
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover { background: #E8F6F2; }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] { background: var(--menthe); border-left-color: var(--encre); }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p { color: var(--encre); font-weight: 600; }
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:focus-visible) { outline: 3px solid var(--ambre); }

/* ── Boutons ─────────────────────────────────────────────── */
.stButton button[kind="primary"], .stButton button[kind="primary"]:focus {
    background: var(--encre); border: none; color: #fff; border-radius: 14px; font-weight: 600;
    padding: .7rem 1.2rem; box-shadow: 0 4px 0 #082A30;
}
.stButton button[kind="primary"]:hover { background: #134B55; color: #fff; }
.stButton button[kind="primary"]:active { transform: translateY(2px); box-shadow: 0 2px 0 #082A30; }
.stButton button[kind="secondary"] {
    background: var(--menthe); border: 1px solid var(--menthe-fonce); color: var(--encre); border-radius: 14px;
    font-weight: 600;
}
.stButton button[kind="secondary"]:hover { background: #C6ECE4; color: var(--encre); border-color: var(--encre); }
.stButton button:focus-visible { outline: 3px solid var(--ambre); outline-offset: 2px; }

/* Champs : texte foncé sur fond blanc (un texte clair y devient invisible ; -webkit-text-fill-color pour Chrome/Safari). */
.stTextInput input, .stTextArea textarea {
    background: #fff !important; color: var(--texte) !important; -webkit-text-fill-color: var(--texte) !important;
    caret-color: var(--encre) !important; border-radius: 12px !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #93AAAD !important; -webkit-text-fill-color: #93AAAD !important; }

/* ── Barre du haut ───────────────────────────────────────── */
.barre-haut { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
              padding: .2rem 0 1.2rem; }
.marque { display: flex; align-items: center; gap: .6rem; font-weight: 700; font-size: 1.35rem; color: var(--encre); }
.marque small { display: block; font-size: .8rem; font-weight: 400; color: var(--doux); }
.pastilles { display: flex; align-items: center; gap: .6rem; }
.pastille { display: inline-flex; align-items: center; gap: .35rem; padding: .45rem .95rem; border-radius: 999px;
            font-weight: 600; font-size: .95rem; }
.pastille.points { background: var(--encre); color: #fff; }
.pastille.serie { background: var(--ambre-clair); color: #7A4F00; }
.avatar { width: 42px; height: 42px; border-radius: 50%; background: var(--menthe); color: var(--encre);
          display: grid; place-items: center; font-weight: 700; border: 2px solid #fff; box-shadow: 0 0 0 2px var(--menthe-fonce); }

/* ── Carte d'accueil (la plus en avant) ──────────────────── */
.st-key-accueil { background: linear-gradient(160deg, #DDF5F0 0%, #CBEDE5 100%); border: 1px solid var(--menthe-fonce);
                  border-radius: 26px; padding: 1.6rem 1.7rem 1rem; }
.salut { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
.salut h2 { font-size: 2rem; font-weight: 700; margin: 0 0 .2rem; color: var(--encre); }
.salut p { margin: 0; color: var(--texte); font-size: 1.02rem; }
.salut svg { flex: none; }
.badges-ligne { font-size: .9rem; color: var(--doux); margin-top: .5rem; }

/* ── Choix de l'entraînement : cadre en pointillés ───────── */
.st-key-choix { background: var(--carte); border: 2px dashed var(--menthe-fonce); border-radius: 20px; padding: 1.2rem 1.3rem; }
.titre-carte { font-weight: 600; font-size: 1.1rem; color: var(--encre); }
.sous-titre { color: var(--doux); font-size: .92rem; margin: .15rem 0 .4rem; }

/* ── Cartes des séances récentes ─────────────────────────── */
[class*="st-key-recente_"] { background: var(--carte); border: 1px solid var(--trait); border-radius: 18px; padding: 1.1rem 1.2rem; }
.recente h4 { font-size: 1.08rem; font-weight: 600; margin: 0 0 .4rem; line-height: 1.35; }
.recente .meta { display: flex; justify-content: space-between; align-items: center; gap: .5rem; margin-bottom: .5rem; }
.recente .a-revoir { color: var(--rose); font-size: .92rem; }
.recente .ok { color: #1F7A5C; font-size: .92rem; }
/* Compteurs de la carte d'exercice */
.compteurs { display: flex; gap: .6rem; margin-bottom: .4rem; }
.compteurs > div { flex: 1; background: var(--carte); border: 1px solid var(--trait); border-radius: 16px; padding: .5rem; text-align: center; }
.compteurs b { display: block; font-size: 1.55rem; color: var(--encre); }
.compteurs span { font-size: .8rem; color: var(--doux); }

/* ── Colonne de droite ──────────────────────────────────── */
.st-key-reco, .st-key-objectif { background: var(--carte); border: 1px solid var(--trait); border-radius: 20px; padding: 1.2rem 1.3rem; }
.st-key-objectif { border-color: #F3DDA6; }
.etiquette { display: flex; align-items: center; gap: .55rem; color: var(--doux); font-weight: 600; font-size: .92rem; }
.etiquette .icone { width: 34px; height: 34px; border-radius: 10px; background: var(--menthe); display: grid; place-items: center; }
.reco-titre { font-size: 1.35rem; font-weight: 700; color: var(--encre); margin: .55rem 0 .5rem; line-height: 1.3; }
.puces { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: .6rem; }
.puce { padding: .25rem .7rem; border: 1px solid var(--trait); border-radius: 999px; font-size: .85rem; color: var(--texte); background: #fff; }
.puce.rose { background: var(--rose-clair); border-color: transparent; color: #B0335A; }
.puce.vert { background: var(--menthe); border-color: transparent; color: var(--encre); }
.objectif-entete { display: flex; justify-content: space-between; align-items: baseline; font-weight: 600; color: var(--encre); }
.objectif-entete span { font-weight: 500; color: var(--doux); font-size: .92rem; }
.jauge { height: 10px; background: #EEF4F2; border-radius: 99px; overflow: hidden; margin: .55rem 0 .4rem; }
.jauge > i { display: block; height: 100%; border-radius: 99px; background: var(--ambre); }
.jauge.rose > i { background: var(--rose); }
.jauge.encre > i { background: var(--encre); }
.serie-msg { background: var(--ambre-clair); color: #7A4F00; border-radius: 14px; padding: .55rem .8rem; font-size: .9rem; font-weight: 500; margin-top: .5rem; }

/* ── Flashcards ─────────────────────────────────────────── */
.st-key-creer_cartes { background: var(--carte); border: 2px dashed var(--menthe-fonce); border-radius: 20px; padding: 1.2rem 1.3rem; }
.st-key-cartes_seance { background: linear-gradient(160deg, #DDF5F0 0%, #CBEDE5 100%); border: 1px solid var(--menthe-fonce);
                       border-radius: 22px; padding: 1.2rem 1.3rem; }
.st-key-pile, .st-key-rappel_cartes { background: var(--carte); border: 1px solid var(--trait); border-radius: 20px; padding: 1.2rem 1.3rem; }
.pile-nombre { font-size: 2.6rem; font-weight: 700; color: var(--rose); line-height: 1.1; margin-top: .4rem; }
.st-key-carte, .st-key-carte_retournee { border-radius: 26px; padding: 2rem 1.6rem 1.4rem; text-align: center; min-height: 260px;
    border: 1px solid var(--trait); box-shadow: 0 8px 0 var(--menthe); }
.st-key-carte, .st-key-carte_retournee { background: var(--carte); }
.st-key-carte_retournee { box-shadow: 0 8px 0 var(--menthe-fonce); }
.face { color: var(--doux); font-size: .9rem; font-weight: 500; margin-bottom: .6rem; text-align: center; }
.question { font-size: 1.5rem; font-weight: 600; color: var(--encre); line-height: 1.35; max-width: 34ch; margin: 0 auto .4rem; text-align: center; }
.reponse { font-size: 1.25rem; font-weight: 500; color: var(--encre); line-height: 1.45; text-align: center;
           background: var(--menthe); border-radius: 16px; padding: .9rem 1.1rem; max-width: 40ch; margin: 1rem auto 0; }
.reponse small { display: block; color: var(--doux); font-size: .85rem; font-weight: 500; margin-bottom: .25rem; }

/* ── Ma progression ─────────────────────────────────────── */
.chiffre { background: var(--carte); border: 1px solid var(--trait); border-radius: 18px; padding: 1rem 1.2rem; }
.chiffre b { display: block; font-size: 1.9rem; color: var(--encre); }
.chiffre span { color: var(--doux); font-size: .92rem; }
.badge-carte { border-radius: 16px; padding: .8rem 1rem; border: 1px solid var(--trait); background: var(--carte); height: 100%; }
.badge-carte.obtenu { background: var(--menthe); border-color: var(--menthe-fonce); }
.badge-carte .nom { font-weight: 600; color: var(--encre); }
.badge-carte p { font-size: .85rem; color: var(--doux); margin: .2rem 0 0; }
.badge-carte.verrouille { opacity: .6; }

/* ── Espace prof ────────────────────────────────────────── */
.hero { padding: .5rem 0 1rem; }
.hero h1 { font-size: 1.9rem; font-weight: 700; color: var(--encre); margin-bottom: .2rem; }
.hero .subtitle { color: var(--doux); }
.dash-metric { background: var(--carte); border: 1px solid var(--trait); border-radius: 18px; padding: 1.1rem; text-align: center; }
.dash-metric .number { font-size: 2rem; font-weight: 700; color: var(--encre); }
.dash-metric .label { font-size: .85rem; color: var(--doux); margin-top: .2rem; }

@media (max-width: 640px) {
    .salut h2 { font-size: 1.6rem; }
    .salut svg { width: 64px; height: 64px; }
    .st-key-accueil { padding: 1.2rem 1.1rem .8rem; }
}
</style>
"""


# ════════════════════════════════════════════════════════════
# 🗄️  SUPABASE
# ════════════════════════════════════════════════════════════

@st.cache_resource
def _client_supabase(url, key):
    from supabase import create_client
    return create_client(url, key)


def get_supabase():
    """Client Supabase côté serveur. Les identifiants sont lus dans les secrets Streamlit,
    jamais dans le code : les élèves sont mineurs, leurs échanges ne doivent pas être lisibles
    par quiconque récupère le dépôt. Utiliser la clé SECRÈTE (sb_secret_… ou service_role) :
    la table n'a aucune politique d'accès public."""
    try:
        import supabase  # noqa: F401
    except ImportError:
        return None
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        return None
    if not url or not key or key.startswith("sb_publishable_"):
        return None
    try:
        return _client_supabase(url, key)
    except Exception:
        return None


def sauvegarder_seance(s):
    """Enregistre une séance terminée : résultats exercice par exercice et chiffres du bilan."""
    sb = get_supabase()
    if not sb:
        return False
    profil = s["profil"]
    data = {
        "eleve_nom": profil.get("nom", "Élève"),
        "classe": profil.get("classe", ""),
        "programme": profil.get("programme", ""),
        "chapitre": profil.get("chapitre", ""),
        "objectif": profil.get("objectif", ""),
        "temps": profil.get("temps", ""),
        "nb_exercices": s["stats"]["exercices"],
        "nb_echanges": s["nb_questions"],
        "phase_finale": "bilan",
        "bilan": s["bilan"] or "",
        "messages": json.dumps({"resultats": s["resultats"], "stats": s["stats"], "points": s["points"],
                                "badges": s["badges_nouveaux"], "interets": profil.get("interets", []),
                                "modele": profil.get("modele") or ""}, ensure_ascii=False),
        "date_session": datetime.now().isoformat(),
    }
    try:
        sb.table(TABLE).insert(data).execute()
        return True
    except Exception:
        return False


def charger_sessions_db(nom):
    sb = get_supabase()
    if not sb:
        return []
    try:
        resp = (
            sb.table(TABLE).select("*")
            .eq("eleve_nom", nom)
            .order("date_session", desc=True)
            .limit(10).execute()
        )
        return resp.data or []
    except Exception:
        return []


def charger_progression(nom):
    """Cumul de toutes les séances enregistrées de l'élève (points, badges, réussite sans aide)."""
    sb = get_supabase()
    if not sb or not nom:
        return P.cumul([])
    try:
        resp = sb.table(TABLE).select("messages, date_session").eq("eleve_nom", nom).limit(500).execute()
        return P.cumul(resp.data or [])
    except Exception:
        return P.cumul([])


def charger_tous_eleves_db():
    sb = get_supabase()
    if not sb:
        return []
    try:
        resp = (
            sb.table(TABLE)
            .select("eleve_nom, classe, chapitre, nb_exercices, phase_finale, bilan, date_session, messages")
            .order("date_session", desc=True)
            .limit(200).execute()
        )
        return resp.data or []
    except Exception:
        return []


def resume_historique(sessions):
    if not sessions:
        return ""
    lignes = ["\n--- HISTORIQUE DES SÉANCES PRÉCÉDENTES ---"]
    for s in sessions[:3]:
        date = str(s.get("date_session", "?"))[:10]
        chapitre = s.get("chapitre", "?")
        bilan = s.get("bilan", "")
        phase = s.get("phase_finale", "")
        nb_ex = s.get("nb_exercices", 0)
        lignes.append(f"\n[{date}] Chapitre : {chapitre} · {nb_ex} exercices · Phase : {phase}")
        if bilan:
            lignes.append(f"Bilan : {bilan}")
    lignes.append("--- FIN HISTORIQUE ---\n")
    return "\n".join(lignes)


# ════════════════════════════════════════════════════════════
# 🤖  CLÉ API (Claude) — le tuteur lui-même est dans tuteur.py
# ════════════════════════════════════════════════════════════

def zone_photo():
    """Exercice modèle (ADR 0002) : photo → lecture par le tuteur → transcription vérifiée par l'élève.
    La photo n'est jamais enregistrée : après lecture, le champ est vidé et seul le texte est gardé.
    Renvoie (transcription confirmée, libellé du thème), ou ("", "") tant qu'il n'y en a pas."""
    lecture = st.session_state.get("lecture")
    if lecture is None:
        st.caption("🔒 Ta photo sert seulement à lire l'exercice : elle n'est jamais enregistrée. "
                   "Cadre juste l'énoncé, sans ton nom ni ton visage.")
        n = st.session_state.get("_photo_n", 0)
        fichier = st.file_uploader("📸 Photo de l'exercice fait en classe", type=M.TYPES_ACCEPTES, key=f"photo_{n}")
        message = st.session_state.pop("_photo_message", None)
        if message:
            st.warning(message)
        if fichier is not None and st.button("🔍 Lire l'exercice", use_container_width=True):
            octets = fichier.getvalue()
            st.session_state["_photo_n"] = n + 1      # nouveau champ au prochain affichage : la photo est oubliée
            try:
                image = M.preparer_image(octets)
                with st.spinner("🔍 Le tuteur lit ton exercice…"):
                    r = T.lire_exercice(get_api_key() or "", image)
            except M.PhotoIllisible as ex:
                st.session_state["_photo_message"] = f"📸 {ex}"
            except T.TuteurIndisponible:
                st.session_state["_photo_message"] = "Le tuteur ne répond pas pour le moment. Réessaie dans un instant."
            else:
                if not r["lisible"]:
                    st.session_state["_photo_message"] = "📸 Je n'arrive pas à lire l'exercice : reprends la photo bien à plat, nette et en entier."
                elif not r["maths"]:
                    st.session_state["_photo_message"] = "📸 Cette photo ne semble pas montrer un exercice de maths."
                else:
                    st.session_state.lecture = r
            finally:
                del octets
            st.rerun()
        return "", ""
    st.markdown("**✅ Vérifie le texte lu par le tuteur** : corrige-le s'il s'est trompé.")
    texte = st.text_area("Ton exercice de classe", value=lecture["transcription"], height=150, max_chars=1500,
                         key="transcription").strip()
    st.caption("Le tuteur va t'entraîner sur des exercices du même type, avec d'autres nombres. "
               "Il ne fera pas ton exercice à ta place : à la fin, c'est toi qui le refais !")
    if st.button("📸 Prendre une autre photo"):
        st.session_state.pop("lecture", None)
        st.session_state.pop("transcription", None)
        st.rerun()
    return texte, f"📸 {lecture['notion'] or 'Exercice de classe'}"


def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


# ════════════════════════════════════════════════════════════
# 📊  TABLEAU DE BORD PROFESSEUR
# ════════════════════════════════════════════════════════════

def synthese_par_eleve(sessions):
    """Une ligne par élève : cumul de ses séances (points, badges, réussite sans aide, formats difficiles)."""
    par_eleve = {}
    for s in sessions:  # triées de la plus récente à la plus ancienne
        par_eleve.setdefault(s.get("eleve_nom", "?"), []).append(s)
    lignes = []
    for nom, seances in par_eleve.items():
        c = P.cumul(seances)
        lignes.append({
            "Élève": nom,
            "Classe": seances[0].get("classe", ""),
            "Séances": c["seances"],
            "Points": c["points"],
            "Badges": " ".join(P.BADGES[b][0] for b in c["badges"]),
            "Sans aide": f"{c['taux_sans_aide']} %" if c["taux_sans_aide"] is not None else "—",
            "Formats où il bloque": ", ".join(E.NOMS_FORMATS[f] for f in c["formats_difficiles"]) or "—",
            "Dernière séance": str(seances[0].get("date_session", ""))[:10],
        })
    return sorted(lignes, key=lambda l: l["Élève"].lower())


def afficher_dashboard_prof():
    sessions = charger_tous_eleves_db()
    if not sessions:
        st.info("📭 Aucune séance enregistrée pour le moment.")
        return

    eleves_uniques = list({s["eleve_nom"] for s in sessions})
    total_exercices = sum(s.get("nb_exercices", 0) for s in sessions)

    col1, col2, col3 = st.columns(3)
    for col, valeur, label in ((col1, len(eleves_uniques), "Élèves"), (col2, len(sessions), "Séances"), (col3, total_exercices, "Exercices")):
        col.markdown(f"""<div class="dash-metric">
            <div class="number">{valeur}</div>
            <div class="label">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("#### 👥 Vue par élève")
    st.dataframe(synthese_par_eleve(sessions), hide_index=True, use_container_width=True)
    st.caption("« Sans aide » : part des exercices réussis sans indice ni correction, sur les séances en exercices structurés. "
               "« Formats où il bloque » : formats où l'élève a le plus souvent eu besoin d'aide ou de plusieurs essais.")

    st.markdown("#### 🗂️ Détail des séances")
    eleve_filtre = st.selectbox(
        "Filtrer par élève", ["Tous les élèves"] + sorted(eleves_uniques)
    )
    if eleve_filtre != "Tous les élèves":
        sessions = [s for s in sessions if s["eleve_nom"] == eleve_filtre]

    for s in sessions:
        date = str(s.get("date_session", ""))[:16].replace("T", " à ")
        nom = s.get("eleve_nom", "?")
        classe = s.get("classe", "")
        chapitre = s.get("chapitre", "?")
        nb_ex = s.get("nb_exercices", 0)
        bilan = s.get("bilan", "")
        contenu = P.lire_contenu(s)
        stats = contenu.get("stats") or {}

        with st.expander(f"✅  **{nom}** · {chapitre} — {date}"):
            st.markdown(f"**Classe :** {classe} · **Exercices :** {nb_ex}")
            if stats:
                st.markdown(
                    f"**Réussis :** {stats.get('reussis', 0)} / {stats.get('exercices', 0)} · "
                    f"**sans aide :** {stats.get('sans_aide', 0)} · **avec indices :** {stats.get('avec_indices', 0)} · "
                    f"**correction vue :** {stats.get('correction_vue', 0)} · **points :** {contenu.get('points', 0)}"
                )
                difficiles = [E.NOMS_FORMATS[f] for f in stats.get("formats_difficiles") or [] if f in E.NOMS_FORMATS]
                notions = stats.get("notions_difficiles") or []
                if difficiles or notions:
                    st.markdown("**À surveiller :** " + " · ".join(difficiles + notions))
            if contenu.get("modele"):
                st.markdown("**📸 Exercice modèle (transcription) :**")
                st.text(contenu["modele"])
            if contenu.get("badges"):
                st.markdown("**Badges gagnés :** " + " · ".join(P.libelle(b) for b in contenu["badges"] if b in P.BADGES))
            if bilan:
                st.info(bilan)

    if eleve_filtre != "Tous les élèves" and len(sessions) >= 2:
        st.markdown("---")
        st.markdown(f"#### 📈 Progression de {eleve_filtre}")
        rows = []
        for s in reversed(sessions):
            stats = P.lire_contenu(s).get("stats") or {}
            rows.append({
                "Date": str(s.get("date_session", ""))[:10],
                "Chapitre": s.get("chapitre", "?"),
                "Exercices": s.get("nb_exercices", 0),
                "Sans aide": stats.get("sans_aide", "—"),
                "Points": P.lire_contenu(s).get("points", "—"),
            })
        st.table(rows)


# ════════════════════════════════════════════════════════════
# 🎨  INTERFACE PRINCIPALE
# ════════════════════════════════════════════════════════════

# Signature de la carte d'accueil : un triangle rectangle, son angle droit et un arc de cercle, dessinés pour l'app.
ATOME = """<svg width="96" height="92" viewBox="0 0 104 100" aria-hidden="true">
  <path d="M12 88 L12 14 L92 88 Z" fill="#ffffff" fill-opacity=".55" stroke="#0E3B43" stroke-width="3.4" stroke-linejoin="round"/>
  <path d="M12 76 L24 76 L24 88" fill="none" stroke="#0E3B43" stroke-width="2.6"/>
  <path d="M70 88 A22 22 0 0 0 76 73" fill="none" stroke="#F4B740" stroke-width="4" stroke-linecap="round"/>
  <circle cx="12" cy="14" r="5" fill="#E0517A"/>
  <circle cx="92" cy="88" r="5" fill="#F4B740"/>
  <circle cx="12" cy="88" r="5" fill="#0E3B43"/>
</svg>"""

PAGE_ACCUEIL, PAGE_CARTES, PAGE_PROGRESSION, PAGE_PROF = "🏠  Aujourd'hui", "🃏  Flashcards", "📈  Ma progression", "🧑‍🏫  Espace prof"
PAGES = [PAGE_ACCUEIL, PAGE_CARTES, PAGE_PROGRESSION, PAGE_PROF]
DUREE_RAPIDE = "15 min"


def aujourd_hui() -> str:
    return datetime.now().date().isoformat()


def charger_seances_eleve(nom):
    """Toutes les séances enregistrées de l'élève, de la plus récente à la plus ancienne."""
    sb = get_supabase()
    if not sb or not nom:
        return []
    try:
        resp = sb.table(TABLE).select("*").eq("eleve_nom", nom).order("date_session", desc=True).limit(500).execute()
        return resp.data or []
    except Exception:
        return []


def barre_haut(nom: str, cumul: dict, jours: int):
    droite = ""
    if nom:
        droite = (f'<span class="pastille points">⭐ {cumul["points"]} pts</span>'
                  f'<span class="pastille serie">🔥 {jours} jour{"s" if jours > 1 else ""}</span>'
                  f'<span class="avatar">{html.escape(nom[:1].upper())}</span>')
    st.markdown(
        f"""<div class="barre-haut"><div class="marque">🎓<div>Tuteur Maths<small>Collège · 6ᵉ → 3ᵉ</small></div></div>
        <div class="pastilles">{droite}</div></div>""",
        unsafe_allow_html=True,
    )


def phrase_accueil(nom: str, jours: int, fait: bool, du_jour: int) -> str:
    if not nom:
        return "Écris ton prénom pour retrouver tes points, tes badges et ta série de jours."
    if du_jour >= P.OBJECTIF_JOUR:
        return "Objectif du jour atteint. Une séance de plus te fera encore progresser."
    if fait:
        return f"Tu as déjà fait {du_jour} exercice{'s' if du_jour > 1 else ''} aujourd'hui. On continue ?"
    if jours:
        return f"Ta série de {jours} jour{'s' if jours > 1 else ''} t'attend : une séance aujourd'hui pour la continuer."
    return "Choisis ton entraînement ci-dessous pour commencer."


def statut_seance(ligne: dict) -> tuple[str, int]:
    """Texte « à revoir » et part de réussite sans aide (en %) d'une séance enregistrée."""
    stats = P.lire_contenu(ligne).get("stats") or {}
    total = int(stats.get("exercices") or ligne.get("nb_exercices") or 0)
    sans_aide = int(stats.get("sans_aide") or 0)
    a_revoir = total - sans_aide if stats else 0
    pct = round(100 * sans_aide / total) if stats and total else 0
    if not stats:
        return f"{total} exercice{'s' if total > 1 else ''}", pct
    if a_revoir:
        return f"{a_revoir} exercice{'s' if a_revoir > 1 else ''} à revoir", pct
    return "Tout réussi sans aide", pct


def profil_depuis_ligne(ligne: dict, base: dict) -> dict:
    """Profil pour refaire une séance enregistrée : même chapitre, même exercice modèle ou même thème libre."""
    chapitre = ligne.get("chapitre", "")
    modele = P.lire_contenu(ligne).get("modele") or ""
    connu = any(chapitre in liste for liste in CHAPITRES.values())
    return {**base, "classe": ligne.get("classe") or base["classe"], "chapitre": chapitre, "modele": modele,
            "theme_libre": not connu and not modele}


def lancer(profil: dict, lignes: list[dict]):
    seance = S.nouvelle_seance(profil, resume_historique(lignes[:10]), P.cumul(lignes))
    with st.spinner("🧠 Le tuteur prépare ton premier exercice…"):
        S.preparer_exercice(seance, get_api_key())
    st.session_state.seance = seance
    st.session_state.pop("_ballons_montres", None)
    st.session_state.pop("lecture", None)
    st.session_state.pop("transcription", None)
    st.rerun()


def page_accueil(sb_ok: bool):
    nom = (st.session_state.get("prenom") or "").strip()
    lignes = charger_seances_eleve(nom) if sb_ok and nom else []
    cumul = P.cumul(lignes)
    jours, fait = P.jours_de_suite(lignes, aujourd_hui())
    du_jour = P.exercices_du_jour(lignes, aujourd_hui())
    barre_haut(nom, cumul, jours)

    principal, rail = st.columns([2.1, 1], gap="large")
    with principal:
        with st.container(key="accueil"):
            badges = " ".join(P.libelle(b) for b in cumul["badges"])
            st.markdown(
                f"""<div class="salut"><div><h2>{"Salut " + html.escape(nom) + " !" if nom else "Bienvenue !"}</h2>
                <p>{phrase_accueil(nom, jours, fait, du_jour)}</p>
                {f'<div class="badges-ligne">Tes badges : {badges}</div>' if badges else ""}</div>{ATOME}</div>""",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            c1.text_input("👤 Ton prénom", placeholder="Ex : Sarah", key="prenom")
            classe = c2.selectbox("📚 Classe", list(CHAPITRES.keys()), key="classe")

        st.markdown("")
        with st.container(key="choix"):
            st.markdown('<div class="titre-carte">🧭 Choisis ton entraînement</div><div class="sous-titre">Un chapitre '
                        "du programme, ton exercice de classe en photo, ou un thème que tu écris toi-même.</div>",
                        unsafe_allow_html=True)
            mode = st.segmented_control("Sur quoi tu veux t'entraîner ?", MODES_THEME, default=MODE_CHAPITRE,
                                        key="mode_theme", label_visibility="collapsed") or MODE_CHAPITRE
            theme_libre, par_photo = mode == AUTRE_THEME, mode == PHOTO_THEME
            modele, chapitre = "", ""
            if mode == MODE_CHAPITRE:
                chapitre = st.selectbox("📖 Chapitre", CHAPITRES.get(classe, []))
            if par_photo:
                modele, chapitre = zone_photo()
            if theme_libre:
                chapitre = st.text_area("✏️ Ton thème", max_chars=150, height=68,
                                        placeholder="Ex : Cônes et cylindres : aires, volumes, Pythagore pour la hauteur").strip()
            c3, c4 = st.columns([1.2, 1], vertical_alignment="center")
            with c3:
                temps = st.select_slider("⏱️ Durée", options=list(E.EXERCICES_PAR_DUREE), value="30 min")
                st.caption(f"{E.nombre_exercices(temps)} exercices")
            with c4:
                btn_start = st.button("🚀 Commencer la séance", use_container_width=True, type="primary")
            with st.expander("⚙️ Personnaliser (centres d'intérêt, objectif, programme)"):
                interets = st.multiselect("❤️ Ce que tu aimes (jusqu'à 3) : tes exercices seront des missions sur ces thèmes",
                                          CENTRES_INTERET, max_selections=3, placeholder="Choisis 1 à 3 centres d'intérêt")
                objectif = st.text_area("🎯 Objectif", placeholder="Ex : Réviser Pythagore pour le contrôle", height=68)
                programme = st.selectbox("🌍 Programme", PAYS_PROGRAMMES)

        refaire = None
        recentes = [l for l in lignes if not F.est_flashcards(P.lire_contenu(l))]
        if recentes:
            st.markdown("### Tes dernières séances")
            cols = st.columns(2)
            for i, ligne in enumerate(recentes[:4]):
                texte, pct = statut_seance(ligne)
                classe_txt = "ok" if texte.startswith("Tout") else "a-revoir"
                with cols[i % 2], st.container(key=f"recente_{i}"):
                    st.markdown(
                        f"""<div class="recente"><h4>{html.escape(ligne.get("chapitre") or "Séance")}</h4>
                        <div class="meta"><span class="{classe_txt}">{texte}</span>
                        <span class="puce vert">{html.escape(ligne.get("classe") or "")}</span></div>
                        <div class="jauge {"encre" if classe_txt == "ok" else "rose"}"><i style="width:{pct}%"></i></div>
                        <div class="sous-titre">{pct} % réussi sans aide · {str(ligne.get("date_session", ""))[:10]}</div></div>""",
                        unsafe_allow_html=True,
                    )
                    if st.button("Refaire ce chapitre", key=f"refaire_{i}", use_container_width=True):
                        refaire = ligne

    with rail:
        reco = P.recommandation(lignes, CHAPITRES.get(classe, []))
        lancer_reco = False
        with st.container(key="reco"):
            st.markdown('<div class="etiquette"><span class="icone">✨</span>Séance recommandée</div>', unsafe_allow_html=True)
            if reco:
                rose = "rose" if reco["raison"].startswith("À consolider") else "vert"
                st.markdown(
                    f"""<div class="reco-titre">{html.escape(reco["chapitre"])}</div><div class="puces">
                    <span class="puce">📚 {E.nombre_exercices(DUREE_RAPIDE)} exercices</span><span class="puce">⏱️ ≈ {DUREE_RAPIDE}</span>
                    <span class="puce {rose}">{html.escape(reco["raison"])}</span></div>""",
                    unsafe_allow_html=True,
                )
                lancer_reco = st.button(f"▶ Lancer la séance · {DUREE_RAPIDE}", type="primary", use_container_width=True,
                                        key="lancer_reco", disabled=not nom)
                if not nom:
                    st.caption("Écris ton prénom pour lancer ta séance.")
            else:
                st.caption("Choisis ta classe pour avoir une recommandation.")
        st.markdown("")
        with st.container(key="objectif"):
            pct = min(100, round(100 * du_jour / P.OBJECTIF_JOUR))
            if fait and jours:
                message = f"🔥 Ta série de {jours} jour{'s' if jours > 1 else ''} continue aujourd'hui."
            elif jours:
                message = f"🔥 Fais une séance aujourd'hui pour garder ta série de {jours} jour{'s' if jours > 1 else ''}."
            else:
                message = "🔥 Une séance aujourd'hui lance ta série de jours."
            st.markdown(
                f"""<div class="objectif-entete">🏆 Objectif du jour <span>{min(du_jour, P.OBJECTIF_JOUR)}/{P.OBJECTIF_JOUR} exercices</span></div>
                <div class="jauge"><i style="width:{pct}%"></i></div>
                <div class="sous-titre">{P.OBJECTIF_JOUR} exercices pour valider ta journée</div>
                <div class="serie-msg">{message}</div>""",
                unsafe_allow_html=True,
            )
        st.markdown("")
        with st.container(key="rappel_cartes"):
            pile = pile_a_revoir(lignes)
            st.markdown(f'<div class="etiquette"><span class="icone">🃏</span>Flashcards</div>'
                        f'<div class="sous-titre">{len(pile)} carte{"s" if len(pile) > 1 else ""} à revoir</div>',
                        unsafe_allow_html=True)
            st.button("Réviser avec des flashcards", use_container_width=True, on_click=aller_aux_cartes, key="vers_cartes")

    base = {"nom": nom or "Élève", "classe": classe, "programme": programme, "interets": interets,
            "objectif": objectif or "Réviser et progresser", "theme_libre": False, "modele": ""}
    if btn_start:
        if theme_libre and not chapitre:
            st.warning("✏️ Écris ton thème dans le champ « Ton thème », puis relance la séance.")
        elif par_photo and not modele:
            st.warning("📸 Ajoute la photo de ton exercice et clique sur « Lire l'exercice », puis relance la séance.")
        else:
            lancer({**base, "chapitre": chapitre, "theme_libre": theme_libre, "modele": modele, "temps": temps}, lignes)
    elif lancer_reco and reco:
        lancer({**base, "chapitre": reco["chapitre"], "temps": DUREE_RAPIDE}, lignes)
    elif refaire:
        lancer({**profil_depuis_ligne(refaire, base), "temps": temps}, lignes)


def page_progression(sb_ok: bool):
    nom = (st.session_state.get("prenom") or "").strip()
    lignes = charger_seances_eleve(nom) if sb_ok and nom else []
    cumul = P.cumul(lignes)
    jours, _ = P.jours_de_suite(lignes, aujourd_hui())
    barre_haut(nom, cumul, jours)
    st.markdown("## Ma progression")
    if not nom:
        st.info("Écris ton prénom sur la page « Aujourd'hui » pour voir ta progression.")
        return
    if not lignes:
        st.info("Aucune séance enregistrée pour l'instant : lance ta première séance sur la page « Aujourd'hui ».")
        return
    taux = f"{cumul['taux_sans_aide']} %" if cumul["taux_sans_aide"] is not None else "—"
    for col, (valeur, libelle) in zip(st.columns(4), ((cumul["seances"], "séances"), (cumul["exercices"], "exercices"),
                                                       (taux, "réussis sans aide"), (f"{jours} j", "série en cours"))):
        col.markdown(f'<div class="chiffre"><b>{valeur}</b><span>{libelle}</span></div>', unsafe_allow_html=True)
    st.markdown("### Tes badges")
    for col, (b, (emoji, nom_badge, comment)) in zip(st.columns(len(P.BADGES)), P.BADGES.items()):
        obtenu = b in cumul["badges"]
        col.markdown(f'<div class="badge-carte {"obtenu" if obtenu else "verrouille"}"><div class="nom">'
                     f'{emoji if obtenu else "🔒"} {nom_badge}</div><p>{comment}</p></div>', unsafe_allow_html=True)
    st.markdown("### Toutes tes séances")
    rows = []
    for ligne in lignes:
        stats = P.lire_contenu(ligne).get("stats") or {}
        rows.append({"Date": str(ligne.get("date_session", ""))[:10],
                     "Type": "Flashcards" if F.est_flashcards(P.lire_contenu(ligne)) else "Exercices",
                     "Chapitre": ligne.get("chapitre", ""),
                     "Exercices": stats.get("exercices", ligne.get("nb_exercices", 0)),
                     "Réussis": stats.get("reussis", "—"), "Sans aide": stats.get("sans_aide", "—"),
                     "Points": P.lire_contenu(ligne).get("points", "—")})
    st.dataframe(rows, hide_index=True, use_container_width=True)


# ───────────── Flashcards ─────────────

def sauvegarder_flashcards(r: dict) -> bool:
    sb = get_supabase()
    if not sb:
        return False
    b, p = F.bilan(r), r["profil"]
    data = {
        "eleve_nom": p.get("nom", "Élève"), "classe": p.get("classe", ""), "programme": p.get("programme", ""),
        "chapitre": f"🃏 {p.get('chapitre', '')}", "objectif": "", "temps": "", "nb_exercices": 0, "nb_echanges": 0,
        "phase_finale": F.TYPE, "bilan": f"Flashcards : {b['sues']} carte(s) sue(s) sur {b['cartes']}, {b['a_revoir']} à revoir.",
        "messages": json.dumps(F.contenu_a_enregistrer(r), ensure_ascii=False),
        "date_session": datetime.now().isoformat(),
    }
    try:
        sb.table(TABLE).insert(data).execute()
        return True
    except Exception:
        return False


def pile_a_revoir(lignes: list[dict]) -> list[dict]:
    return F.cartes_a_revoir([P.lire_contenu(l) for l in lignes])


def aller_aux_cartes():
    st.session_state.nav = PAGE_CARTES


def afficher_revision(r: dict, sb_ok: bool):
    vues, total = F.progression(r)
    if r["termine"]:
        if not r["enregistree"]:
            r["enregistree"] = True
            if sb_ok and r["notes"]:
                sauvegarder_flashcards(r)
        b = F.bilan(r)
        st.markdown(f"## {'Série terminée' if vues == total else 'Série arrêtée'} : +{b['points']} points")
        for col, (valeur, libelle) in zip(st.columns(3), ((b["sues"], "cartes sues"), (b["du_premier_coup"], "du premier coup"),
                                                           (b["a_revoir"], "à revoir"))):
            col.markdown(f'<div class="chiffre"><b>{valeur}</b><span>{libelle}</span></div>', unsafe_allow_html=True)
        ratees = [r["cartes"][i] for i, ok in r["notes"].items() if not ok]
        if ratees:
            st.markdown("### À revoir")
            for c in ratees:
                st.markdown(f"**{html.escape(c['recto'])}**  \n{html.escape(c['verso'])}")
        st.markdown("")
        c1, c2 = st.columns(2) if ratees else (None, st.container())
        if ratees and c1.button(f"🔁 Revoir ces {len(ratees)} cartes", type="primary", use_container_width=True):
            st.session_state.revision = F.nouvelle_revision(ratees, {**r["profil"], "chapitre": "Cartes à revoir"})
            st.rerun()
        if c2.button("🃏 Autres cartes", use_container_width=True):
            st.session_state.revision = None
            st.rerun()
        return

    c = F.carte_courante(r)
    i = r["file"][0]
    st.progress(vues / total, text=f"{r['profil'].get('chapitre', '')} · carte {min(vues + 1, total)} sur {total}")
    with st.container(key="carte_retournee" if r["retournee"] else "carte"):
        st.markdown(f'<div class="face">Question</div><div class="question">{html.escape(c["recto"])}</div>',
                    unsafe_allow_html=True)
        if c.get("figure"):
            _, milieu, _ = st.columns([1, 1.4, 1])
            milieu.image(ecran._image_figure(repr(c["figure"]), c["figure"]), use_container_width=True)
        if r["retournee"]:
            st.markdown(f'<div class="reponse"><small>Réponse</small>{html.escape(c["verso"])}</div>', unsafe_allow_html=True)
    if i in r["repassees"]:
        st.caption("Cette carte revient : tu l'avais notée « À revoir ».")
    st.markdown("")
    if not r["retournee"]:
        if st.button("🔄 Retourner la carte", type="primary", use_container_width=True):
            F.retourner(r)
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        if c1.button("🔁 À revoir", use_container_width=True):
            F.noter(r, False)
            st.rerun()
        if c2.button("✅ Je savais", type="primary", use_container_width=True):
            F.noter(r, True)
            st.rerun()
    if st.button("Arrêter la série", key="arreter_cartes"):
        r["termine"] = True
        st.rerun()


def derniere_thematique(lignes: list[dict]) -> dict | None:
    """Thème de la dernière séance d'exercices : celle en cours ou qui vient de se terminer, sinon la plus récente
    enregistrée (hors flashcards). Garde le chapitre, le thème libre ou l'exercice modèle photographié."""
    s = st.session_state.get("seance")
    if s is not None:
        p = s["profil"]
        return {"classe": p.get("classe", ""), "chapitre": p.get("chapitre", ""),
                "theme_libre": bool(p.get("theme_libre")), "modele": p.get("modele") or ""}
    for ligne in lignes:
        if not F.est_flashcards(P.lire_contenu(ligne)) and ligne.get("chapitre"):
            p = profil_depuis_ligne(ligne, {"classe": ligne.get("classe", "")})
            return {k: p[k] for k in ("classe", "chapitre", "theme_libre", "modele")}
    return None


def demander_cartes_de_la_seance():
    """Bouton du bilan : aller aux flashcards et créer tout de suite les cartes sur le thème de la séance."""
    st.session_state.nav = PAGE_CARTES
    st.session_state["_cartes_de_la_seance"] = True


def creer_cartes(profil: dict, nombre: int, pile: list[dict]):
    try:
        with st.spinner("🃏 Le tuteur écrit tes cartes…"):
            cartes = T.generer_cartes(get_api_key() or "", profil, nombre, deja=[c["recto"] for c in pile])
    except T.TuteurIndisponible:
        st.error("Le tuteur ne répond pas pour le moment. Réessaie dans un instant.")
    else:
        st.session_state.revision = F.nouvelle_revision(cartes, profil)
        st.rerun()


def page_flashcards(sb_ok: bool):
    nom = (st.session_state.get("prenom") or "").strip()
    lignes = charger_seances_eleve(nom) if sb_ok and nom else []
    jours, _ = P.jours_de_suite(lignes, aujourd_hui())
    barre_haut(nom, P.cumul(lignes), jours)
    r = st.session_state.get("revision")
    if r is not None:
        afficher_revision(r, sb_ok)
        return

    pile = pile_a_revoir(lignes)
    derniere = derniere_thematique(lignes)
    base = {"nom": nom or "Élève", "programme": PAYS_PROGRAMMES[0], "theme_libre": False, "modele": ""}
    if st.session_state.pop("_cartes_de_la_seance", False) and derniere:   # demandé depuis le bilan d'une séance
        creer_cartes({**base, **derniere}, 10, pile)

    st.markdown("## Flashcards")
    gauche, droite = st.columns([1.6, 1], gap="large")
    creer_derniere = creer_autre = False
    with gauche:
        if derniere:
            with st.container(key="cartes_seance"):
                nature = ("ton exercice de classe" if derniere["modele"] else "ton thème" if derniere["theme_libre"]
                          else derniere["classe"])
                st.markdown(f'<div class="etiquette"><span class="icone">🎯</span>Sur ta dernière séance</div>'
                            f'<div class="reco-titre">{html.escape(derniere["chapitre"])}</div>'
                            f'<div class="puces"><span class="puce vert">{html.escape(nature)}</span></div>',
                            unsafe_allow_html=True)
                c1, c2 = st.columns([1, 1.3], vertical_alignment="bottom")
                nombre_derniere = c1.segmented_control("Nombre de cartes", F.NOMBRES, default=10, key="nb_cartes") or 10
                creer_derniere = c2.button("✨ Réviser ce thème en flashcards", type="primary", use_container_width=True)
            st.markdown("")
        with st.container(key="creer_cartes"):
            st.markdown('<div class="titre-carte">🃏 ' + ("Ou choisis une autre thématique" if derniere else "Crée tes flashcards")
                        + '</div><div class="sous-titre">Le tuteur écrit une question au recto et la réponse au verso. '
                        "Tu retournes chaque carte et tu dis si tu savais.</div>", unsafe_allow_html=True)
            mode = st.segmented_control("Thématique", [MODE_CHAPITRE, AUTRE_THEME], default=MODE_CHAPITRE,
                                        key="mode_cartes", label_visibility="collapsed") or MODE_CHAPITRE
            classes = list(CHAPITRES.keys())
            classe_eleve = st.session_state.get("classe")
            classe = st.selectbox("📚 Classe", classes, index=classes.index(classe_eleve) if classe_eleve in classes else 0,
                                  key="classe_cartes")
            if mode == MODE_CHAPITRE:
                chapitre = st.selectbox("📖 Chapitre", CHAPITRES.get(classe, []) or ["—"], key="chapitre_cartes")
                pret = bool(CHAPITRES.get(classe))
            else:
                chapitre = st.text_area("✏️ Ta thématique", max_chars=150, height=68, key="theme_cartes",
                                        placeholder="Ex : Les fractions : simplifier et comparer").strip()
                pret = True
            nombre_autre = st.segmented_control("Nombre de cartes", F.NOMBRES, default=10, key="nb_cartes_autre") or 10
            creer_autre = st.button("✨ Créer les cartes", type="primary" if not derniere else "secondary",
                                    use_container_width=True, disabled=not pret)
    with droite, st.container(key="pile"):
        st.markdown(f'<div class="etiquette"><span class="icone">🔁</span>Cartes à revoir</div>'
                    f'<div class="pile-nombre">{len(pile)}</div>'
                    f'<div class="sous-titre">{"Les cartes que tu as notées « À revoir » la dernière fois." if pile else "Aucune carte à revoir pour l’instant."}</div>',
                    unsafe_allow_html=True)
        revoir = st.button(f"Réviser mes {len(pile)} cartes" if pile else "Réviser mes cartes", use_container_width=True,
                           disabled=not pile, key="reviser_pile")
        if not nom:
            st.caption("Écris ton prénom sur l'accueil pour garder tes cartes à revoir.")

    if creer_derniere and derniere:
        creer_cartes({**base, **derniere}, nombre_derniere, pile)
    if creer_autre:
        if mode == AUTRE_THEME and not chapitre:
            st.warning("✏️ Écris ta thématique, puis clique sur « Créer les cartes ».")
        else:
            creer_cartes({**base, "classe": classe, "chapitre": chapitre, "theme_libre": mode == AUTRE_THEME}, nombre_autre, pile)
    if revoir and pile:
        st.session_state.revision = F.nouvelle_revision(pile, {**base, "classe": classe, "chapitre": "Cartes à revoir"})
        st.rerun()


def revenir_a_l_accueil():
    st.session_state.seance = None
    st.session_state.revision = None
    st.session_state.nav = PAGE_ACCUEIL
    st.session_state.pop("_ballons_montres", None)


def main():
    st.set_page_config(
        page_title="Tuteur Maths IA — Collège",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="auto",  # repliée sur téléphone, sinon elle cache la carte
    )
    st.markdown(CSS, unsafe_allow_html=True)
    for k, v in {"seance": None, "revision": None, "prof_auth": False}.items():
        st.session_state.setdefault(k, v)
    # Le prénom et la classe sont saisis sur l'accueil : Streamlit efface la valeur d'un champ qui n'est pas affiché
    # (autre page, séance en cours). La réaffecter à chaque passage la garde d'une page à l'autre.
    for k in ("prenom", "classe"):
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]
    sb_ok = get_supabase() is not None

    with st.sidebar:
        st.button("＋ Nouvelle séance", type="primary", use_container_width=True, on_click=revenir_a_l_accueil)
        st.markdown("")
        page = st.radio("Navigation", PAGES, key="nav", label_visibility="collapsed")

        # Pendant une séance : résumé et commandes (le profil se remplit au centre de l'accueil).
        btn_bilan = False
        seance = st.session_state.seance
        if page == PAGE_ACCUEIL and seance is not None:
            st.divider()
            p = seance["profil"]
            st.markdown(f"👤 **{p['nom']}** · {p['classe']}")
            st.markdown(f"📖 {p['chapitre']}")
            st.markdown(f"🏆 **{S.total_points(seance)} points** au total")
            collection = S.badges(seance)
            if collection:
                st.markdown("  \n".join(P.libelle(b) for b in collection))
            if not seance["termine"]:
                btn_bilan = st.button("🏁 Terminer et voir mon bilan", use_container_width=True)

    if page == PAGE_PROF:
        st.markdown("""<div class="hero">
            <h1>🧑‍🏫 Espace professeur</h1>
            <div class="subtitle">Suivi et progression des élèves</div>
        </div>""", unsafe_allow_html=True)
        if not sb_ok:
            st.warning("Base de données non configurée : ajoutez SUPABASE_URL et SUPABASE_KEY (clé secrète sb_secret_…, pas la clé publique) dans les secrets Streamlit.")
            return
        if not st.session_state.prof_auth:
            try:
                mdp_attendu = st.secrets["MOT_DE_PASSE_PROF"]
            except Exception:
                mdp_attendu = os.environ.get("MOT_DE_PASSE_PROF", MOT_DE_PASSE_PROF)
            _, col_c, _ = st.columns([1, 2, 1])
            with col_c:
                mdp = st.text_input("🔒 Mot de passe", type="password", placeholder="Entrez le mot de passe prof")
                if mdp:
                    if mdp == mdp_attendu:
                        st.session_state.prof_auth = True
                        st.rerun()
                    else:
                        st.error("Mot de passe incorrect.")
            return
        afficher_dashboard_prof()
        return

    if page == PAGE_PROGRESSION:
        page_progression(sb_ok)
        return
    if page == PAGE_CARTES:
        page_flashcards(sb_ok)
        return

    if btn_bilan and st.session_state.seance:
        with st.spinner("📊 Le tuteur rédige ton bilan…"):
            S.terminer(st.session_state.seance, get_api_key(), sauvegarder_seance if sb_ok else None)
        st.rerun()

    if st.session_state.seance is None:
        page_accueil(sb_ok)
        return

    if not get_api_key():
        st.error("⚠️ Clé API Claude manquante : ajoutez ANTHROPIC_API_KEY dans les secrets Streamlit.")
        return
    ecran.afficher(st.session_state.seance, get_api_key(), sauvegarder_seance if sb_ok else None)
    if st.session_state.seance is not None and st.session_state.seance["termine"]:
        st.button("🃏 Réviser ce thème en flashcards", type="primary", use_container_width=True,
                  on_click=demander_cartes_de_la_seance, key="cartes_du_bilan")


if __name__ == "__main__":
    main()
