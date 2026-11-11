#!/usr/bin/env python3
"""
🎓 Tuteur de Maths IA — Collège (6ᵉ → 3ᵉ) — Application Streamlit + Supabase
Parcours personnalisé : diagnostic → entraînement → bilan, en exercices structurés
(QCM, réponse numérique, vrai ou faux, texte à trous, étapes dans l'ordre, réponse rédigée).
Le tuteur écrit les exercices, l'app choisit le format, corrige et tient le déroulé (docs/adr/0001).
"""

import json
import os
from datetime import datetime

import streamlit as st

import ecran
import exercices as E
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

MOT_DE_PASSE_PROF = "prof2024"


# ════════════════════════════════════════════════════════════
# 🎨  CSS GLOBAL
# ════════════════════════════════════════════════════════════

CSS = """
<style>
/* ── Reset & base ─────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e3a5f 0%, #0f2440 100%);
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stTextArea label {
    color: #94a3b8 !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #f1f5f9 !important;
    border-radius: 0.5rem;
}
/* Champs de saisie : texte foncé sur fond blanc. Streamlit enveloppe le champ dans un cadre blanc :
   un texte clair y devient invisible. -webkit-text-fill-color est nécessaire sur Chrome/Safari. */
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea {
    background: #ffffff !important;
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
    caret-color: #1e293b !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder,
[data-testid="stSidebar"] .stTextArea textarea::placeholder {
    color: #94a3b8 !important;
    -webkit-text-fill-color: #94a3b8 !important;
}
/* Boutons secondaires (Nouvelle séance…) : fond translucide, sinon texte clair sur fond blanc. */
[data-testid="stSidebar"] .stButton button[kind="secondary"] {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
}
[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.16) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
}

/* ── Hero ──────────────────────────────────────────────── */
.hero {
    text-align: center;
    padding: 2rem 1rem 1rem;
}
.hero h1 {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #1e3a5f, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.hero .subtitle {
    color: #64748b;
    font-size: 1rem;
    font-weight: 400;
}

/* ── Cartes d'accueil ─────────────────────────────────── */
.welcome-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 1rem;
    padding: 1.5rem;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
    height: 100%;
}
.welcome-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.08);
}
.welcome-card .icon {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}
.welcome-card h3 {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 0.4rem;
}
.welcome-card p {
    font-size: 0.85rem;
    color: #64748b;
    line-height: 1.5;
}

/* ── Phase badges ─────────────────────────────────────── */
.phase-bar {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.6rem 1rem;
    border-radius: 0.8rem;
    margin-bottom: 0.5rem;
}
.phase-diagnostic {
    background: linear-gradient(135deg, #fef3c7, #fde68a);
    border: 1px solid #f59e0b;
}
.phase-entrainement {
    background: linear-gradient(135deg, #dbeafe, #bfdbfe);
    border: 1px solid #3b82f6;
}
.phase-bilan {
    background: linear-gradient(135deg, #d1fae5, #a7f3d0);
    border: 1px solid #10b981;
}
.phase-bar .phase-icon { font-size: 1.3rem; }
.phase-bar .phase-label {
    font-weight: 700;
    font-size: 0.9rem;
    color: #1e293b;
}
.phase-bar .phase-detail {
    font-size: 0.8rem;
    color: #475569;
    margin-left: auto;
}

/* ── Stats en session ─────────────────────────────────── */
.stats-row {
    display: flex;
    gap: 0.8rem;
    margin-bottom: 1rem;
}
.stat-pill {
    flex: 1;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.7rem;
    padding: 0.6rem 0.8rem;
    text-align: center;
}
.stat-pill .val {
    font-size: 1.4rem;
    font-weight: 800;
    color: #1e3a5f;
}
.stat-pill .lbl {
    font-size: 0.7rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ── Chat bubbles ─────────────────────────────────────── */
[data-testid="stChatMessage"] {
    border-radius: 1rem !important;
    margin-bottom: 0.8rem !important;
    border: none !important;
    padding: 1rem 1.2rem !important;
}

/* ── Bouton d'accueil ─────────────────────────────────── */
.start-hint {
    text-align: center;
    padding: 2rem 1rem;
    color: #94a3b8;
    font-size: 0.95rem;
}
.start-hint .arrow { font-size: 1.5rem; }

/* ── Historique cards ─────────────────────────────────── */
.history-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.8rem;
    padding: 1rem;
    margin-bottom: 0.5rem;
}
.history-card .date {
    font-size: 0.75rem;
    color: #94a3b8;
    text-transform: uppercase;
}
.history-card .chapter {
    font-weight: 600;
    color: #1e293b;
}
.history-card .detail {
    font-size: 0.85rem;
    color: #64748b;
}

/* ── Dashboard prof ───────────────────────────────────── */
.dash-metric {
    background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
    border: 1px solid #bae6fd;
    border-radius: 1rem;
    padding: 1.2rem;
    text-align: center;
}
.dash-metric .number {
    font-size: 2rem;
    font-weight: 800;
    color: #0369a1;
}
.dash-metric .label {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 0.2rem;
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
        sb.table("sessions_college").insert(data).execute()
        return True
    except Exception:
        return False


def charger_sessions_db(nom):
    sb = get_supabase()
    if not sb:
        return []
    try:
        resp = (
            sb.table("sessions_college").select("*")
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
        resp = sb.table("sessions_college").select("messages, date_session").eq("eleve_nom", nom).limit(500).execute()
        return P.cumul(resp.data or [])
    except Exception:
        return P.cumul([])


def charger_tous_eleves_db():
    sb = get_supabase()
    if not sb:
        return []
    try:
        resp = (
            sb.table("sessions_college")
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

def main():
    st.set_page_config(
        page_title="Tuteur Maths IA — Collège",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="auto",  # repliée sur téléphone, sinon elle cache la carte
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Init session state ────────────────────────────────
    for k, v in {
        "seance": None, "page": "tuteur", "prof_auth": False,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    sb_ok = get_supabase() is not None

    # ══════════════════════════════════════════════════════════
    # 📚  SIDEBAR
    # ══════════════════════════════════════════════════════════

    with st.sidebar:
        st.markdown("# 🎓 Tuteur Maths")
        st.markdown("**Collège · 6ᵉ → 3ᵉ**")
        st.caption("Ton coach de maths personnel")
        st.divider()

        page = st.radio(
            "Navigation",
            ["🧑‍🎓  Ma séance", "📊  Espace prof"],
            label_visibility="collapsed",
        )
        st.session_state.page = "tuteur" if "séance" in page else "prof"

        # Le profil se remplit au centre de l'écran d'accueil (sur téléphone, un panneau latéral
        # resté ouvert cacherait la carte d'exercice). Ici : résumé et commandes de la séance.
        btn_bilan = False
        seance = st.session_state.seance
        if st.session_state.page == "tuteur" and seance is not None:
            st.divider()
            p = seance["profil"]
            st.markdown(f"👤 **{p['nom']}** · {p['classe']}")
            st.markdown(f"📖 {p['chapitre']}")
            st.markdown(f"🏆 **{S.total_points(seance)} points** au total")
            collection = S.badges(seance)
            if collection:
                st.markdown("  \n".join(P.libelle(b) for b in collection))
            st.divider()
            if not seance["termine"]:
                btn_bilan = st.button("🏁 Terminer et voir mon bilan", use_container_width=True, type="primary")
            if st.button("🗑️ Nouvelle séance", use_container_width=True):
                st.session_state.seance = None
                st.session_state.pop("_ballons_montres", None)
                st.rerun()

    # ══════════════════════════════════════════════════════════
    # 📊  PAGE PROFESSEUR
    # ══════════════════════════════════════════════════════════

    if st.session_state.page == "prof":
        st.markdown("""<div class="hero">
            <h1>📊 Espace Professeur</h1>
            <div class="subtitle">Suivi et progression des élèves</div>
        </div>""", unsafe_allow_html=True)

        if not sb_ok:
            st.warning("Base de données non configurée : ajoutez SUPABASE_URL et SUPABASE_KEY (clé secrète sb_secret_…, pas la clé publique) dans les secrets Streamlit.")
            return

        if not st.session_state.prof_auth:
            mdp_attendu = MOT_DE_PASSE_PROF
            try:
                mdp_attendu = st.secrets["MOT_DE_PASSE_PROF"]
            except Exception:
                mdp_attendu = os.environ.get("MOT_DE_PASSE_PROF", MOT_DE_PASSE_PROF)

            st.markdown("")
            col_l, col_c, col_r = st.columns([1, 2, 1])
            with col_c:
                mdp = st.text_input("🔒 Mot de passe", type="password",
                                     placeholder="Entrez le mot de passe prof")
                if mdp:
                    if mdp == mdp_attendu:
                        st.session_state.prof_auth = True
                        st.rerun()
                    else:
                        st.error("Mot de passe incorrect.")
            return

        afficher_dashboard_prof()
        return

    # ══════════════════════════════════════════════════════════
    # 🧑‍🎓  PAGE ÉLÈVE
    # ══════════════════════════════════════════════════════════

    # ── Fin anticipée ─────────────────────────────────────
    if btn_bilan and st.session_state.seance:
        with st.spinner("📊 Le tuteur rédige ton bilan…"):
            S.terminer(st.session_state.seance, get_api_key(), sauvegarder_seance if sb_ok else None)
        st.rerun()

    # ── Écran d'accueil : profil au centre ────────────────
    if st.session_state.seance is None:
        st.markdown("""<div class="hero">
            <h1>🎓 Tuteur de Maths IA — Collège</h1>
            <div class="subtitle">Ton parcours personnalisé pour progresser en maths</div>
        </div>""", unsafe_allow_html=True)

        _, centre, _ = st.columns([1, 6, 1])
        with centre, st.container(border=True):
            c1, c2 = st.columns(2)
            nom = c1.text_input("👤 Ton prénom", placeholder="Ex: Sarah")
            classe = c2.selectbox("📚 Classe", list(CHAPITRES.keys()))
            mode = st.segmented_control("🧭 Sur quoi tu veux t'entraîner ?", MODES_THEME, default=MODE_CHAPITRE,
                                        key="mode_theme") or MODE_CHAPITRE
            theme_libre = mode == AUTRE_THEME
            par_photo = mode == PHOTO_THEME
            modele, chapitre = "", ""
            if mode == MODE_CHAPITRE:
                chapitre = st.selectbox("📖 Chapitre", CHAPITRES.get(classe, []))
            if par_photo:
                modele, chapitre = zone_photo()
            if theme_libre:
                chapitre = st.text_area(
                    "✏️ Ton thème",
                    placeholder="Ex: Cônes et cylindres : aires, volumes, Pythagore pour la hauteur",
                    max_chars=150,
                    height=68,
                ).strip()
            interets = st.multiselect(
                "❤️ Ce que tu aimes (jusqu'à 3) : tes exercices seront des missions sur ces thèmes",
                CENTRES_INTERET, max_selections=3, placeholder="Choisis 1 à 3 centres d'intérêt",
            )
            c3, c4 = st.columns(2)
            objectif = c3.text_area("🎯 Objectif (facultatif)", placeholder="Ex: Réviser Pythagore pour le contrôle", height=68)
            with c4:
                temps = st.select_slider("⏱️ Durée", options=list(E.EXERCICES_PAR_DUREE), value="30 min")
                st.caption(f"{E.nombre_exercices(temps)} exercices")
            programme = st.selectbox("🌍 Programme", PAYS_PROGRAMMES)

            sessions_passees = charger_sessions_db(nom) if sb_ok and nom else []
            progression = charger_progression(nom) if sb_ok and nom else P.cumul([])
            if sessions_passees:
                collection = " ".join(P.libelle(b) for b in progression["badges"])
                st.success(
                    f"🏆 Bon retour {nom} ! Tu as **{progression['points']} points** "
                    f"en {progression['seances']} séance(s)." + (f"  \nTes badges : {collection}" if collection else "")
                )
            btn_start = st.button("🚀 Commencer la séance", use_container_width=True, type="primary")

        if btn_start and theme_libre and not chapitre:
            st.warning("✏️ Écris ton thème dans le champ « Ton thème », puis relance la séance.")
            btn_start = False
        if btn_start and par_photo and not modele:
            st.warning("📸 Ajoute la photo de ton exercice et clique sur « Lire l'exercice », puis relance la séance.")
            btn_start = False

        if btn_start:
            profil = {
                "nom": nom or "Élève",
                "classe": classe, "programme": programme,
                "chapitre": chapitre,
                "theme_libre": theme_libre,
                "modele": modele,
                "interets": interets,
                "objectif": objectif or "Réviser et progresser",
                "temps": temps,
            }
            seance = S.nouvelle_seance(profil, resume_historique(sessions_passees), progression)
            with st.spinner("🧠 Le tuteur prépare ton premier exercice…"):
                S.preparer_exercice(seance, get_api_key())
            st.session_state.seance = seance
            st.session_state.pop("_ballons_montres", None)
            st.session_state.pop("lecture", None)
            st.session_state.pop("transcription", None)
            st.rerun()

        st.markdown("")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""<div class="welcome-card">
                <div class="icon">🔍</div>
                <h3>Diagnostic</h3>
                <p>3 exercices rapides (QCM, calcul, vrai ou faux) pour savoir où tu en es.</p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("""<div class="welcome-card">
                <div class="icon">🎯</div>
                <h3>Entraînement</h3>
                <p>Des exercices variés et adaptés à ton niveau. Gagne des points, enchaîne les séries, demande un indice si tu bloques.</p>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown("""<div class="welcome-card">
                <div class="icon">📊</div>
                <h3>Bilan</h3>
                <p>Un résumé de tes progrès avec tes acquis et tes prochaines étapes.</p>
            </div>""", unsafe_allow_html=True)

        if sessions_passees:
            st.markdown("")
            st.markdown("#### 📂 Tes dernières séances")
            for s in sessions_passees[:3]:
                date = str(s.get("date_session", ""))[:10]
                ch = s.get("chapitre", "?")
                nb = s.get("nb_exercices", 0)
                bilan = s.get("bilan", "")
                st.markdown(f"""<div class="history-card">
                    <span class="date">📅 {date}</span><br>
                    <span class="chapter">{ch}</span>
                    <span class="detail"> · {nb} exercices</span>
                </div>""", unsafe_allow_html=True)
                if bilan:
                    with st.expander("Voir le bilan"):
                        st.info(bilan)
        return

    # ══════════════════════════════════════════════════════════
    # 🃏  CARTE D'EXERCICE (version A du prototype)
    # ══════════════════════════════════════════════════════════

    if not get_api_key():
        st.error("⚠️ Clé API Claude manquante : ajoutez ANTHROPIC_API_KEY dans les secrets Streamlit.")
        return
    ecran.afficher(st.session_state.seance, get_api_key(), sauvegarder_seance if sb_ok else None)


if __name__ == "__main__":
    main()
