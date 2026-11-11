#!/usr/bin/env python3
"""
🎓 Tuteur de Maths IA — Collège (6ᵉ → 3ᵉ) — Application Streamlit + Supabase
Parcours personnalisé : diagnostic → entraînement → bilan
Avec suivi persistant et tableau de bord professeur.
"""

import streamlit as st
import json
import os
import re
from datetime import datetime
from anthropic import Anthropic

# ════════════════════════════════════════════════════════════
# ⚙️  CONFIGURATION
# ════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """# 1. Rôle et objectif
Tu es un tuteur de mathématiques pour collégiens (de la 6ᵉ à la 3ᵉ),
intégré à une application Streamlit. Tu aides l'élève à identifier ses
acquis, comprendre ses erreurs et progresser grâce à un parcours
personnalisé : diagnostic → entraînement ciblé → vérification → bilan.

# 2. Informations de départ
Utilise les informations fournies par l'application : classe, pays ou
programme scolaire, chapitre, objectif, temps disponible et historique.

Si des informations indispensables manquent, demande uniquement celles
qui permettent de commencer, en trois questions courtes maximum.
Priorité : classe, chapitre et objectif.
Ne suppose pas le programme à partir de la langue de l'élève.
Si le chapitre est inconnu, aide l'élève à choisir un point de départ.

# 3. Diagnostic initial
Commence par un diagnostic court de trois exercices, présentés un à un :
un prérequis, une application directe et une question de compréhension.
Adapte-les au niveau collège et ajuste la difficulté si nécessaire.
Attends la réponse de l'élève avant de poursuivre.

Présente tes conclusions comme provisoires : une seule erreur ne suffit
pas à établir une lacune, et une seule réussite ne prouve pas la maîtrise.

# 4. Personnalisation de l'entraînement
Choisis chaque nouvel exercice à partir des réponses précédentes.
Travaille une difficulté prioritaire à la fois.
En cas de blocage, simplifie ou reviens au prérequis concerné.
En cas de réussites autonomes répétées, augmente progressivement la difficulté.
Varie les questions pour vérifier la compréhension, pas seulement la mémorisation.
Privilégie des contextes concrets et des situations du quotidien pour rendre
les exercices plus parlants pour un collégien.

# 5. Aide et correction
N'affiche pas la solution avec l'énoncé.
Si l'élève bloque, propose d'abord un indice ciblé, puis une aide plus explicite.
S'il demande directement le corrigé, fournis-le sans le faire attendre.

Après une réponse, indique brièvement ce qui est juste, l'erreur précise
éventuelle et la prochaine étape.
Si le raisonnement manque et qu'il est nécessaire pour évaluer la réponse,
demande une justification courte au lieu de deviner l'origine de l'erreur.
Distingue une réussite autonome d'une réussite obtenue avec aide.

# 6. Rigueur mathématique
Vérifie les énoncés, calculs et corrigés avant de les afficher.
Précise les conditions de validité utiles et accepte les méthodes correctes
différentes de celle que tu avais envisagée.
Si une donnée manque ou si un énoncé est ambigu, signale-le.
Ne présente pas une réponse incertaine comme une certitude.

# 7. Ton et concision
Adopte un ton bienveillant, encourageant et adapté à un collégien,
sans infantiliser l'élève. Utilise un vocabulaire accessible.
Valorise une démarche ou un progrès précis plutôt qu'un compliment générique.
Limite les messages ordinaires à 120 mots, hors énoncé et formules.
Développe davantage uniquement pour une correction nécessaire
ou à la demande de l'élève.

# 8. Format des échanges
Utilise du Markdown simple et du LaTeX pour les expressions mathématiques.
IMPORTANT : utilise uniquement les délimiteurs $ ... $ pour les formules
en ligne et $$ ... $$ pour les formules centrées. N'utilise JAMAIS
\\( \\) ni \\[ \\] ni \\displaystyle.
Affiche uniquement les rubriques utiles :
« Objectif », « Exercice », « Retour » ou « Prochaine étape ».
Ne répète pas toutes les rubriques à chaque message.
Ne propose qu'un nouvel exercice à la fois et termine par une action claire.

# 9. Suivi de la progression
Après trois exercices d'entraînement, à la fin du temps disponible
ou à la demande de l'élève, fournis un bilan de cinq lignes maximum :
- notion travaillée ;
- acquis observés ;
- point à consolider ;
- degré d'autonomie ;
- prochaine étape recommandée.

Appuie ce bilan uniquement sur les réponses réellement observées.
Ne conclus pas à une maîtrise durable à partir d'une seule séance.

# 10. Limites liées à l'application
Utilise uniquement l'historique et les données effectivement transmis.
Si un bilan antérieur existe, reprends à partir de celui-ci et vérifie
brièvement les acquis avant de poursuivre.
Ne prétends jamais avoir sauvegardé une progression ou modifié l'interface
sans confirmation d'un outil de l'application.
Si aucun historique n'est disponible, indique-le simplement et commence
un nouveau diagnostic."""

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
        "Statistiques (moyenne, médiane)",
    ],
    "4ème": [
        "Nombres relatifs (opérations)",
        "Fractions (opérations avancées)",
        "Calcul littéral (développer, factoriser)",
        "Équations du premier degré",
        "Théorème de Pythagore",
        "Translations et rotations",
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
        "Probabilités",
        "Statistiques (quartiles, étendue)",
        "Algorithmique et programmation (Scratch)",
    ],
    "Autre": ["Je préciserai dans le chat"],
}

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
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea {
    color: #1e293b !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stTextArea label {
    color: #94a3b8 !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #f1f5f9 !important;
    border-radius: 0.5rem;
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


def sauvegarder_session_db(profil, messages, nb_exercices, phase, bilan=""):
    sb = get_supabase()
    if not sb:
        return False
    msgs = [
        {"role": m["role"], "content": m["content"]}
        for m in messages if m["role"] != "system"
    ]
    data = {
        "eleve_nom": profil.get("nom", "Élève"),
        "classe": profil.get("classe", ""),
        "programme": profil.get("programme", ""),
        "chapitre": profil.get("chapitre", ""),
        "objectif": profil.get("objectif", ""),
        "temps": profil.get("temps", ""),
        "nb_exercices": nb_exercices,
        "nb_echanges": len([m for m in msgs if m["role"] == "user"]),
        "phase_finale": phase,
        "bilan": bilan,
        "messages": json.dumps(msgs, ensure_ascii=False),
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


def charger_tous_eleves_db():
    sb = get_supabase()
    if not sb:
        return []
    try:
        resp = (
            sb.table("sessions_college")
            .select("eleve_nom, classe, chapitre, nb_exercices, phase_finale, bilan, date_session")
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
# 🔤  FORMATAGE LATEX
# ════════════════════════════════════════════════════════════

def fix_latex(text):
    text = re.sub(r'\\\[\s*', '\n$$\n', text)
    text = re.sub(r'\s*\\\]', '\n$$\n', text)
    text = re.sub(r'\\\(\s*', ' $', text)
    text = re.sub(r'\s*\\\)', '$ ', text)
    text = text.replace(r'\displaystyle ', '')
    text = text.replace(r'\displaystyle', '')
    return text


# ════════════════════════════════════════════════════════════
# 🤖  APPEL LLM (Claude API)
# ════════════════════════════════════════════════════════════

def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


def appel_tuteur(messages):
    api_key = get_api_key()
    if not api_key:
        return "⚠️ Clé API manquante."

    client = Anthropic(api_key=api_key)
    system_prompt = ""
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        else:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            system=system_prompt,
            messages=chat_messages,
            max_tokens=2048,
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"❌ Erreur : {str(e)[:200]}"


def construire_contexte_initial(profil, historique_txt=""):
    infos = (
        f"\n--- PROFIL ÉLÈVE ---\n"
        f"Nom/Pseudo : {profil.get('nom', 'non renseigné')}\n"
        f"Classe : {profil.get('classe', 'non renseignée')}\n"
        f"Programme : {profil.get('programme', 'non renseigné')}\n"
        f"Chapitre : {profil.get('chapitre', 'non renseigné')}\n"
        f"Objectif : {profil.get('objectif', 'non renseigné')}\n"
        f"Temps disponible : {profil.get('temps', 'non renseigné')}\n"
        f"--- FIN PROFIL ---\n"
    )
    return SYSTEM_PROMPT + infos + historique_txt


# ════════════════════════════════════════════════════════════
# 📊  TABLEAU DE BORD PROFESSEUR
# ════════════════════════════════════════════════════════════

def afficher_dashboard_prof():
    sessions = charger_tous_eleves_db()
    if not sessions:
        st.info("📭 Aucune séance enregistrée pour le moment.")
        return

    eleves_uniques = list({s["eleve_nom"] for s in sessions})
    total_exercices = sum(s.get("nb_exercices", 0) for s in sessions)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="dash-metric">
            <div class="number">{len(eleves_uniques)}</div>
            <div class="label">Élèves</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="dash-metric">
            <div class="number">{len(sessions)}</div>
            <div class="label">Séances</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="dash-metric">
            <div class="number">{total_exercices}</div>
            <div class="label">Exercices</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

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
        phase = s.get("phase_finale", "?")
        bilan = s.get("bilan", "")

        phase_emoji = {"diagnostic": "🔍", "entrainement": "🎯", "bilan": "✅"}.get(phase, "📝")

        with st.expander(f"{phase_emoji}  **{nom}** · {chapitre} — {date}"):
            st.markdown(f"**Classe :** {classe} · **Exercices :** {nb_ex} · **Phase :** {phase}")
            if bilan:
                st.info(bilan)

    if eleve_filtre != "Tous les élèves" and len(sessions) >= 2:
        st.markdown("---")
        st.markdown(f"#### 📈 Progression de {eleve_filtre}")
        rows = []
        for s in reversed(sessions):
            rows.append({
                "Date": str(s.get("date_session", ""))[:10],
                "Chapitre": s.get("chapitre", "?"),
                "Exercices": s.get("nb_exercices", 0),
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
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Init session state ────────────────────────────────
    for k, v in {
        "messages": [], "session_active": False, "profil": {},
        "nb_exercices": 0, "phase": "config", "debut_session": None,
        "page": "tuteur", "prof_auth": False,
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

        if st.session_state.page == "tuteur":
            st.divider()

            nom = st.text_input("👤 Ton prénom", placeholder="Ex: Sarah")
            programme = st.selectbox("🌍 Programme", PAYS_PROGRAMMES)
            classe = st.selectbox("📚 Classe", list(CHAPITRES.keys()))
            chapitres_dispo = CHAPITRES.get(classe, ["Autre"])
            chapitre = st.selectbox("📖 Chapitre", chapitres_dispo)
            objectif = st.text_area(
                "🎯 Objectif", placeholder="Ex: Réviser Pythagore pour le contrôle",
                height=68,
            )
            temps = st.select_slider(
                "⏱️ Durée",
                options=["15 min", "30 min", "45 min", "1h", "1h30", "2h"],
                value="30 min",
            )

            if sb_ok and nom:
                sessions_passees = charger_sessions_db(nom)
                if sessions_passees:
                    st.caption(f"📂 {len(sessions_passees)} séance(s) trouvée(s)")
            else:
                sessions_passees = []

            st.divider()

            if not st.session_state.session_active:
                btn_start = st.button(
                    "🚀 Commencer la séance",
                    use_container_width=True, type="primary",
                )
                btn_bilan = False
            else:
                col1, col2 = st.columns(2)
                with col1:
                    btn_start = st.button("🔄 Relancer", use_container_width=True)
                with col2:
                    btn_bilan = st.button("📊 Bilan", use_container_width=True, type="primary")

                if st.button("💾 Sauvegarder", use_container_width=True):
                    if sb_ok:
                        if sauvegarder_session_db(
                            st.session_state.profil,
                            st.session_state.messages,
                            st.session_state.nb_exercices,
                            st.session_state.phase,
                        ):
                            st.success("✅ Sauvegardé !")

                if st.button("🗑️ Nouvelle séance", use_container_width=True):
                    for k in ["messages", "session_active", "nb_exercices", "phase", "debut_session"]:
                        st.session_state[k] = {"messages": [], "session_active": False,
                                               "nb_exercices": 0, "phase": "config",
                                               "debut_session": None}[k]
                    st.rerun()
        else:
            btn_start = False
            btn_bilan = False
            nom = classe = programme = chapitre = objectif = ""
            temps = "30 min"
            sessions_passees = []

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

    # ── Lancement ─────────────────────────────────────────
    if btn_start:
        profil = {
            "nom": nom or "Élève",
            "classe": classe, "programme": programme,
            "chapitre": chapitre,
            "objectif": objectif or "Réviser et progresser",
            "temps": temps,
        }
        st.session_state.profil = profil
        st.session_state.session_active = True
        st.session_state.nb_exercices = 0
        st.session_state.phase = "diagnostic"
        st.session_state.debut_session = datetime.now()

        historique_txt = resume_historique(sessions_passees)
        contexte = construire_contexte_initial(profil, historique_txt)
        st.session_state.messages = [{"role": "system", "content": contexte}]

        with st.spinner("🧠 Préparation du diagnostic..."):
            premier_msg = (
                f"Bonjour ! Je suis prêt pour une séance de {temps} "
                f"sur le chapitre « {chapitre} » en {classe}. "
                f"Mon objectif : {objectif or 'réviser et progresser'}. "
                "Commence le diagnostic."
            )
            st.session_state.messages.append({"role": "user", "content": premier_msg})
            reponse = appel_tuteur(st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": reponse})
        st.rerun()

    # ── Bilan ─────────────────────────────────────────────
    if btn_bilan and st.session_state.session_active:
        st.session_state.messages.append(
            {"role": "user", "content": "Peux-tu me faire un bilan de cette séance ?"}
        )
        with st.spinner("📊 Génération du bilan..."):
            reponse = appel_tuteur(st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": reponse})
        st.session_state.phase = "bilan"
        if sb_ok:
            sauvegarder_session_db(
                st.session_state.profil, st.session_state.messages,
                st.session_state.nb_exercices, "bilan", bilan=reponse,
            )
        st.rerun()

    # ── Écran d'accueil ───────────────────────────────────
    if not st.session_state.session_active:
        st.markdown("""<div class="hero">
            <h1>🎓 Tuteur de Maths IA — Collège</h1>
            <div class="subtitle">Ton parcours personnalisé pour progresser en maths</div>
        </div>""", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""<div class="welcome-card">
                <div class="icon">🔍</div>
                <h3>Diagnostic</h3>
                <p>3 exercices rapides pour identifier tes acquis et tes points à travailler.</p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("""<div class="welcome-card">
                <div class="icon">🎯</div>
                <h3>Entraînement</h3>
                <p>Des exercices adaptés à ton niveau, avec des indices et des corrections.</p>
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

        st.markdown("""<div class="start-hint">
            <div class="arrow">👈</div>
            Remplis ton profil dans le panneau à gauche, puis clique sur
            <strong>Commencer la séance</strong>
        </div>""", unsafe_allow_html=True)
        return

    # ══════════════════════════════════════════════════════════
    # 💬  ZONE DE CHAT
    # ══════════════════════════════════════════════════════════

    # ── Barre de phase ────────────────────────────────────
    phase = st.session_state.phase
    phase_conf = {
        "diagnostic": ("🔍", "Diagnostic en cours", "phase-diagnostic"),
        "entrainement": ("🎯", "Entraînement", "phase-entrainement"),
        "bilan": ("✅", "Bilan de séance", "phase-bilan"),
    }
    icon, label, css = phase_conf.get(phase, ("📝", "En cours", "phase-entrainement"))

    nb_ex = st.session_state.nb_exercices
    nb_msgs = max(0, len([m for m in st.session_state.messages if m["role"] == "user"]) - 1)
    duree = ""
    if st.session_state.debut_session:
        duree = f"{(datetime.now() - st.session_state.debut_session).seconds // 60} min"

    st.markdown(f"""
    <div class="phase-bar {css}">
        <span class="phase-icon">{icon}</span>
        <span class="phase-label">{label}</span>
        <span class="phase-detail">{nb_ex} exercices · {nb_msgs} échanges{' · ' + duree if duree else ''}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Messages ──────────────────────────────────────────
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "system":
            continue
        if i == 1 and msg["role"] == "user" and "Commence le diagnostic" in msg.get("content", ""):
            continue
        with st.chat_message(msg["role"], avatar="🎓" if msg["role"] == "assistant" else "🧑‍🎓"):
            st.markdown(fix_latex(msg["content"]))

    # ── Input ─────────────────────────────────────────────
    if user_input := st.chat_input("Écris ta réponse ici..."):
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(user_input)

        mots_exercice = ["exercice", "question", "calcule", "résous", "détermine",
                         "montre que", "prouve", "simplifie", "développe", "factorise"]

        with st.chat_message("assistant", avatar="🎓"):
            with st.spinner("🧠 Réflexion..."):
                reponse = appel_tuteur(st.session_state.messages)

            st.markdown(fix_latex(reponse))
            st.session_state.messages.append({"role": "assistant", "content": reponse})

            reponse_lower = reponse.lower()
            if any(mot in reponse_lower for mot in mots_exercice):
                st.session_state.nb_exercices += 1
                if st.session_state.nb_exercices > 3 and st.session_state.phase == "diagnostic":
                    st.session_state.phase = "entrainement"
            if any(mot in reponse_lower for mot in ["bilan", "résumé", "synthèse"]):
                st.session_state.phase = "bilan"


if __name__ == "__main__":
    main()
