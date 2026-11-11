"""PROTOTYPE JETABLE (skill /prototype, branche UI) : ne pas fusionner dans main.

Question : à quoi doit ressembler l'écran d'exercice pour que la séance soit ludique ?
Trois variantes structurellement différentes, sur le même contenu, switchables via ?variant=A|B|C
et la barre flottante en bas de l'écran :
  A. Carte de jeu   : un exercice par écran, gros boutons, points et série en haut.
  B. Chat enrichi   : la conversation actuelle, avec les exercices cliquables dans le fil.
  C. Mode mission   : une petite histoire (le stand de glaces de Lina) découpée en étapes à débloquer.

Contenu écrit à l'avance (cônes et cylindres, niveau 4e), aucun appel à l'IA, aucune donnée enregistrée.
Lancer : streamlit run prototype_ecran_exercice.py
"""

import io
import math
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import streamlit as st  # noqa: E402
from matplotlib.patches import Ellipse  # noqa: E402

from app import CSS  # le vrai style de l'app : on juge les variantes en situation

VARIANTES = {"A": "Carte de jeu", "B": "Chat enrichi", "C": "Mode mission"}
BAREME = {0: 10, 1: 7, 2: 5}  # points selon le nombre d'indices ; 3 si la correction a été vue
NOMS_FORMATS = {"qcm": "QCM", "numerique": "Réponse numérique", "vf": "Vrai ou faux", "trous": "Texte à trous", "ordre": "Étapes dans l'ordre", "ouvert": "Réponse rédigée"}

# ═══════════════════════ Contenu (écrit à l'avance) ═══════════════════════

EXERCICES = [
    {
        "format": "qcm", "phase": "Diagnostic",
        "mission": "Lina ouvre son stand de glaces. Elle range ses glaces dans des pots en forme de cylindre.",
        "enonce": "Quelle formule donne le volume d'un cylindre de rayon r et de hauteur h ?",
        "options": ["π × r² × h", "2 × π × r × h", "π × r² × h ÷ 3", "π × r × h"],
        "reponse": "π × r² × h",
        "indices": ["Un cylindre, c'est une pile de disques tous identiques.", "Volume = aire de la base × hauteur. Quelle est l'aire d'un disque de rayon r ?"],
        "correction": "V = aire du disque × hauteur = π × r² × h.",
    },
    {
        "format": "numerique", "phase": "Diagnostic", "figure": ("cylindre", {"r": 3, "h": 10}),
        "mission": "Son plus grand pot a un rayon de 3 cm et une hauteur de 10 cm.",
        "enonce": "Calcule le volume du pot, en cm³, arrondi au dixième.",
        "reponse": 90 * math.pi, "tolerance": 0.05, "unite": "cm³",
        "indices": ["Utilise V = π × r² × h.", "r² = 3² = 9, donc V = π × 9 × 10 = 90π. Il reste à arrondir."],
        "correction": "V = π × 3² × 10 = 90π ≈ 282,7 cm³.",
    },
    {
        "format": "vf", "phase": "Diagnostic", "figure": ("cone", {"r": 3, "h": 4, "g": 5}),
        "mission": "Pour les clients pressés, Lina sert aussi des cornets en forme de cône.",
        "enonce": "Vrai ou faux ?",
        "affirmations": [
            ("La base d'un cône de révolution est un disque.", True),
            ("Dans un cône, la hauteur est plus longue que la génératrice.", False),
            ("Le volume d'un cône est le tiers de celui du cylindre de même base et de même hauteur.", True),
        ],
        "indices": ["Regarde la figure : hauteur, rayon et génératrice forment un triangle rectangle.", "Dans un triangle rectangle, le plus long côté est l'hypoténuse. Ici, c'est la génératrice."],
        "correction": "Vrai, faux (la génératrice est l'hypoténuse, donc le plus long côté), vrai.",
    },
    {
        "format": "trous", "phase": "Entraînement", "figure": ("cone", {"r": 3, "h": 4, "g": 5}),
        "mission": "Lina veut connaître la hauteur de ses cornets pour choisir ses boîtes.",
        "enonce": "Complète :",
        "texte": "La hauteur h, le rayon r et la génératrice g forment un triangle {0}. D'après le théorème de {1} : g² = {2} + r².",
        "trous": [(["rectangle", "isocèle", "équilatéral"], "rectangle"), (["Pythagore", "Thalès"], "Pythagore"), (["h²", "g²", "2h"], "h²")],
        "indices": ["La hauteur tombe perpendiculairement sur la base.", "Le théorème qui relie les trois côtés d'un triangle rectangle porte le nom d'un mathématicien grec."],
        "correction": "Triangle rectangle ; théorème de Pythagore : g² = h² + r².",
    },
    {
        "format": "ordre", "phase": "Entraînement", "figure": ("cone", {"r": 3, "h": None, "g": 5}),
        "mission": "Un cornet a un rayon de 3 cm et une génératrice de 5 cm. Quelle est sa hauteur ?",
        "enonce": "Remets les étapes du raisonnement dans l'ordre (clique-les une par une).",
        "etapes": [
            "Le triangle formé par h, r et g est rectangle.",
            "D'après le théorème de Pythagore : g² = h² + r².",
            "Donc h² = g² − r² = 25 − 9 = 16.",
            "Donc h = √16 = 4 cm.",
        ],
        "indices": ["On commence toujours par justifier que le triangle est rectangle.", "On écrit l'égalité de Pythagore avant de remplacer par les nombres."],
        "correction": "Triangle rectangle → égalité de Pythagore → calcul de h² → racine carrée : h = 4 cm.",
    },
    {
        "format": "numerique", "phase": "Entraînement", "figure": ("cone", {"r": 3, "h": 4, "g": 5}),
        "mission": "Combien de glace faut-il pour remplir ce cornet à ras bord ?",
        "enonce": "Calcule le volume du cône de rayon 3 cm et de hauteur 4 cm, en cm³, arrondi au dixième.",
        "reponse": 12 * math.pi, "tolerance": 0.05, "unite": "cm³",
        "indices": ["Le volume d'un cône, c'est le tiers du volume du cylindre de même base et même hauteur.", "V = π × r² × h ÷ 3 = π × 9 × 4 ÷ 3 = 12π. Il reste à arrondir."],
        "correction": "V = π × 3² × 4 ÷ 3 = 12π ≈ 37,7 cm³.",
    },
    {
        "format": "ouvert", "phase": "Entraînement",
        "mission": "Un client affirme : « Un pot cylindrique de rayon 3 cm et de hauteur 4 cm contient 3 fois plus de glace qu'un cornet de même rayon et même hauteur. »",
        "enonce": "A-t-il raison ? Explique en une ou deux phrases.",
        "modele": "Oui : le pot contient π × 3² × 4 = 36π cm³ et le cornet 36π ÷ 3 = 12π cm³, donc 3 fois moins.",
        "indices": ["Calcule les deux volumes, puis compare-les.", "Pot : π × 9 × 4. Cornet : la même chose divisée par 3."],
        "correction": "Il a raison : 36π cm³ pour le pot contre 12π cm³ pour le cornet.",
    },
]

# ═══════════════════════ Figures (dessinées par le code, cotes exactes) ═══════════════════════


@st.cache_data
def figure(nature: str, r: float, h, g=None) -> bytes:
    fig, ax = plt.subplots(figsize=(3.2, 3.2), dpi=110)
    ax.set_aspect("equal")
    ax.axis("off")
    bleu, gris = "#1e3a5f", "#94a3b8"
    hauteur = h if h is not None else math.sqrt(g * g - r * r)
    if nature == "cylindre":
        hh = hauteur * 0.45
        ax.add_patch(Ellipse((0, 0), 2 * r, r * 0.6, fill=False, color=bleu, lw=2))
        ax.add_patch(Ellipse((0, hh), 2 * r, r * 0.6, fill=False, color=bleu, lw=2))
        ax.plot([-r, -r], [0, hh], color=bleu, lw=2)
        ax.plot([r, r], [0, hh], color=bleu, lw=2)
        ax.plot([0, r], [0, 0], color="#dc2626", lw=1.5, ls="--")
        ax.text(r / 2, -r * 0.3 - 0.55, f"r = {r} cm", ha="center", color="#dc2626", fontsize=10)
        ax.annotate("", xy=(r + 0.6, hh), xytext=(r + 0.6, 0), arrowprops=dict(arrowstyle="<->", color=gris))
        ax.text(r + 0.8, hh / 2, f"h = {h} cm", va="center", fontsize=10, color=bleu)
        ax.set_xlim(-r - 0.5, r + 3.2)
        ax.set_ylim(-r * 0.3 - 1.1, hh + 1)
    else:
        ax.add_patch(Ellipse((0, 0), 2 * r, r * 0.6, fill=False, color=bleu, lw=2))
        ax.plot([-r, 0, r], [0, hauteur, 0], color=bleu, lw=2)
        ax.plot([0, 0], [0, hauteur], color=gris, lw=1.5, ls="--")
        ax.plot([0, r], [0, 0], color="#dc2626", lw=1.5, ls="--")
        ax.plot([0, 0.35, 0.35], [0.35, 0.35, 0], color=gris, lw=1)  # angle droit
        ax.text(r / 2, -r * 0.3 - 0.55, f"r = {r} cm", ha="center", color="#dc2626", fontsize=10)
        ax.text(-0.2, hauteur / 2, "h = ?" if h is None else f"h = {h} cm", ha="right", va="center", fontsize=10, color=bleu)
        if g is not None:
            ax.text(r / 2 + 0.35, hauteur / 2 + 0.2, f"g = {g} cm", fontsize=10, color=bleu)
        ax.set_xlim(-r - 1.5, r + 1.5)
        ax.set_ylim(-r * 0.3 - 1.1, hauteur + 0.6)
    tampon = io.BytesIO()
    fig.savefig(tampon, format="png", bbox_inches="tight", transparent=True)
    plt.close(fig)
    return tampon.getvalue()


def afficher_figure(ex, largeur=240):
    if ex.get("figure"):
        nature, p = ex["figure"]
        st.image(figure(nature, p["r"], p.get("h"), p.get("g")), width=largeur)


# ═══════════════════════ Moteur commun (état, correction, points) ═══════════════════════


def melanger(etapes):
    while True:  # jamais déjà dans le bon ordre
        m = random.sample(etapes, len(etapes))
        if m != etapes:
            return m


def etat(v):
    cle = f"etat_{v}"
    if cle not in st.session_state:
        st.session_state[cle] = {"i": 0, "points": 0, "serie": 0, "indices": 0, "correction_vue": False,
                                 "fini": False, "resultats": [], "badges": [], "ordre": [], "retour": None,
                                 "melange": {k: melanger(e["etapes"]) for k, e in enumerate(EXERCICES) if e["format"] == "ordre"},
                                 "auto_eval": None}
    return st.session_state[cle]


def nombre(texte):
    try:
        return float(str(texte).replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def est_juste(ex, reponse):
    f = ex["format"]
    if f == "qcm":
        return reponse == ex["reponse"]
    if f == "numerique":
        x = nombre(reponse)
        return x is not None and abs(x - ex["reponse"]) <= ex["tolerance"]
    if f == "vf":
        return list(reponse) == [a[1] for a in ex["affirmations"]]
    if f == "trous":
        return list(reponse) == [t[1] for t in ex["trous"]]
    if f == "ordre":
        return list(reponse) == ex["etapes"]
    if f == "ouvert":
        return reponse in ("juste", "moitie")
    return False


def valider(v, reponse):
    e = etat(v)
    ex = EXERCICES[e["i"]]
    if est_juste(ex, reponse):
        gain = 3 if e["correction_vue"] else BAREME.get(e["indices"], 5)
        if ex["format"] == "ouvert" and reponse == "moitie":
            gain = min(gain, 5)
        e["serie"] += 1
        bonus = 2 if e["serie"] >= 3 else 0
        e["points"] += gain + bonus
        precedent_aide = bool(e["resultats"]) and e["resultats"][-1]["correction_vue"]
        e["resultats"].append({"format": ex["format"], "indices": e["indices"], "correction_vue": e["correction_vue"]})
        nouveaux = badges_gagnes(e, precedent_aide)
        e["badges"] += nouveaux
        e["retour"] = {"ok": True, "gain": gain, "bonus": bonus, "badges": nouveaux}
        st.toast(f"+{gain + bonus} points" + (" · série 🔥" if bonus else ""), icon="⭐")
        for b in nouveaux:
            st.toast(f"Badge : {b}", icon="🏅")
    else:
        e["serie"] = 0
        e["retour"] = {"ok": False}


def badges_gagnes(e, precedent_aide):
    r = e["resultats"]
    candidats = []
    if r[-1]["indices"] == 0 and not r[-1]["correction_vue"]:
        candidats.append("Premier sans indice")
    if e["serie"] >= 5:
        candidats.append("Série de 5")
    if len({x["format"] for x in r}) >= 3:
        candidats.append("Trois formats réussis")
    if precedent_aide and not r[-1]["correction_vue"]:
        candidats.append("Je me suis relevé·e")
    return [b for b in candidats if b not in e["badges"]]


def suivant(v):
    e = etat(v)
    e.update({"indices": 0, "correction_vue": False, "ordre": [], "retour": None, "auto_eval": None})
    if e["i"] + 1 >= len(EXERCICES):
        e["fini"] = True
        if "Séance terminée" not in e["badges"]:
            e["badges"].append("Séance terminée")
    else:
        e["i"] += 1


def demander_aide(v):
    e = etat(v)
    if e["indices"] < 2:
        e["indices"] += 1
    else:
        e["correction_vue"] = True


def bloc_aide(v, ex, compact=False):
    """Indices en boutons (décision Q3) : indice 1, indice 2, puis correction."""
    e = etat(v)
    for k in range(e["indices"]):
        st.info(f"💡 Indice {k + 1} : {ex['indices'][k]}")
    if e["correction_vue"]:
        st.warning(f"📖 Correction : {ex['correction']}")
    if e["retour"] and e["retour"]["ok"]:
        return
    libelle = "💡 Un indice" if e["indices"] == 0 else ("💡 Un autre indice" if e["indices"] == 1 else "📖 Voir la correction")
    if not e["correction_vue"]:
        st.button(libelle, key=f"aide_{v}_{e['i']}_{e['indices']}", on_click=demander_aide, args=(v,), use_container_width=not compact)


def saisie(v, ex, gros=True):
    """Affiche la zone de réponse du format et appelle valider() quand l'élève répond."""
    e = etat(v)
    k = f"{v}_{e['i']}"
    f = ex["format"]
    if f == "qcm":
        if gros:
            cols = st.columns(2)
            for n, opt in enumerate(ex["options"]):
                cols[n % 2].button(opt, key=f"qcm_{k}_{n}", on_click=valider, args=(v, opt), use_container_width=True, type="secondary")
        else:
            choix = st.radio("Ta réponse", ex["options"], index=None, key=f"qcmr_{k}", horizontal=True, label_visibility="collapsed")
            if st.button("Valider", key=f"okq_{k}") and choix:
                valider(v, choix)
                st.rerun()
    elif f == "numerique":
        c1, c2 = st.columns([3, 1])
        val = c1.text_input(f"Ta réponse ({ex['unite']})", key=f"num_{k}", placeholder="ex : 12,5")
        c2.write("")
        c2.write("")
        if c2.button("Valider", key=f"okn_{k}", type="primary", use_container_width=True):
            valider(v, val)
            st.rerun()
    elif f == "vf":
        reponses = []
        for n, (aff, _) in enumerate(ex["affirmations"]):
            c1, c2 = st.columns([4, 2])
            c1.markdown(f"**{n + 1}.** {aff}")
            reponses.append(c2.segmented_control("vf", ["Vrai", "Faux"], key=f"vf_{k}_{n}", label_visibility="collapsed"))
        if st.button("Valider", key=f"okvf_{k}", type="primary", disabled=None in reponses):
            valider(v, [r == "Vrai" for r in reponses])
            st.rerun()
    elif f == "trous":
        morceaux = ex["texte"].split("{")
        choix = []
        st.markdown(morceaux[0])
        cols = st.columns(len(ex["trous"]))
        for n, (options, _) in enumerate(ex["trous"]):
            choix.append(cols[n].selectbox(f"Trou {n + 1}", ["…", *options], key=f"tr_{k}_{n}"))
        st.caption("Phrase complète : " + ex["texte"].format(*[c if c != "…" else "____" for c in choix]))
        if st.button("Valider", key=f"oktr_{k}", type="primary", disabled="…" in choix):
            valider(v, choix)
            st.rerun()
    elif f == "ordre":
        restantes = [s for s in e["melange"][e["i"]] if s not in e["ordre"]]
        for n, s in enumerate(e["ordre"]):
            st.success(f"{n + 1}. {s}")
        for s in restantes:
            if st.button(s, key=f"ord_{k}_{s[:20]}", use_container_width=True):
                e["ordre"].append(s)
                st.rerun()
        c1, c2 = st.columns(2)
        if e["ordre"] and c1.button("↺ Recommencer", key=f"rz_{k}"):
            e["ordre"] = []
            st.rerun()
        if not restantes and c2.button("Valider", key=f"oko_{k}", type="primary"):
            valider(v, e["ordre"])
            if not e["retour"]["ok"]:
                e["ordre"] = []
            st.rerun()
    elif f == "ouvert":
        st.text_area("Ta réponse", key=f"ouv_{k}", height=90)
        if e["auto_eval"] is None:
            if st.button("Comparer avec une réponse modèle", key=f"cmp_{k}", type="primary"):
                e["auto_eval"] = "a_faire"
                st.rerun()
        else:
            st.success(f"Réponse modèle : {ex['modele']}")
            st.caption("Dans l'app réelle, c'est le tuteur qui lira ta réponse. Ici, compare toi-même :")
            c1, c2, c3 = st.columns(3)
            c1.button("J'avais juste", key=f"ae1_{k}", on_click=valider, args=(v, "juste"), use_container_width=True)
            c2.button("À moitié", key=f"ae2_{k}", on_click=valider, args=(v, "moitie"), use_container_width=True)
            c3.button("Je n'avais pas trouvé", key=f"ae3_{k}", on_click=lambda: (demander_aide(v), demander_aide(v), demander_aide(v), valider(v, "juste")), use_container_width=True)


def retour_exercice(v, ex):
    e = etat(v)
    r = e["retour"]
    if not r:
        return False
    if r["ok"]:
        msg = f"✅ Bravo ! +{r['gain']} points" + (f" +{r['bonus']} (série de {e['serie']} 🔥)" if r["bonus"] else "")
        st.success(msg)
        st.button("Exercice suivant →" if e["i"] + 1 < len(EXERCICES) else "Voir mon bilan →", key=f"suiv_{v}_{e['i']}", on_click=suivant, args=(v,), type="primary", use_container_width=True)
        return True
    st.error("Pas tout à fait. Réessaie, ou demande un indice.")
    return False


def bilan(v):
    e = etat(v)
    sans_aide = sum(1 for r in e["resultats"] if r["indices"] == 0 and not r["correction_vue"])
    st.balloons()
    st.markdown(f"### 🎉 Séance terminée : {e['points']} points")
    st.write(f"{len(e['resultats'])} exercices réussis, dont **{sans_aide} sans indice**.")
    st.write("Badges : " + (" · ".join(f"🏅 {b}" for b in e["badges"]) or "aucun"))
    if st.button("Recommencer cette version", key=f"rst_{v}"):
        del st.session_state[f"etat_{v}"]
        st.rerun()


# ═══════════════════════ Variante A : carte de jeu ═══════════════════════


def variante_a():
    v = "A"
    e = etat(v)
    st.markdown(
        "<div style='display:flex;gap:.6rem;flex-wrap:nowrap'>"
        + "".join(
            f"<div style='flex:1;background:#f1f5f9;border-radius:.8rem;padding:.5rem;text-align:center'>"
            f"<div style='font-size:1.6rem;font-weight:800;color:#1e3a5f'>{val}</div><div style='font-size:.75rem;color:#64748b'>{lib}</div></div>"
            for lib, val in (("⭐ Points", e["points"]), ("🔥 Série", e["serie"]), ("🏅 Badges", len(e["badges"])))
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.progress(min(len(e["resultats"]), len(EXERCICES)) / len(EXERCICES), text=f"Exercice {min(e['i'] + 1, len(EXERCICES))} sur {len(EXERCICES)}")
    if e["fini"]:
        bilan(v)
        return
    ex = EXERCICES[e["i"]]
    _, centre, _ = st.columns([1, 6, 1])
    with centre, st.container(border=True):
        st.caption(f"{ex['phase'].upper()} · {NOMS_FORMATS[ex['format']]}")
        st.markdown(f"#### {ex['enonce']}")
        st.markdown(f"*{ex['mission']}*")
        afficher_figure(ex, 220)
        if not retour_exercice(v, ex):
            saisie(v, ex, gros=True)
        bloc_aide(v, ex)


# ═══════════════════════ Variante B : chat enrichi ═══════════════════════


def variante_b():
    v = "B"
    e = etat(v)
    with st.sidebar:
        st.markdown(f"⭐ **{e['points']} points** · 🔥 série {e['serie']} · 🏅 {len(e['badges'])}")
    for n in range(e["i"] if not e["fini"] else len(EXERCICES)):
        passe = EXERCICES[n]
        with st.chat_message("assistant", avatar="🎓"):
            st.markdown(f"**{passe['phase']} · {NOMS_FORMATS[passe['format']]}** — {passe['mission']} {passe['enonce']}")
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown("✅ Réussi")
    if e["fini"]:
        with st.chat_message("assistant", avatar="🎓"):
            bilan(v)
        return
    ex = EXERCICES[e["i"]]
    with st.chat_message("assistant", avatar="🎓"):
        st.markdown(f"**{ex['phase']} · {NOMS_FORMATS[ex['format']]}**")
        st.markdown(f"{ex['mission']} {ex['enonce']}")
        afficher_figure(ex, 200)
        if not retour_exercice(v, ex):
            saisie(v, ex, gros=False)
        bloc_aide(v, ex, compact=True)
    question = st.chat_input("Une question ? Écris-la ici…")
    if question:
        st.toast("Dans l'app réelle, le tuteur répondrait ici.", icon="💬")


# ═══════════════════════ Variante C : mode mission ═══════════════════════

ETAPES_MISSION = ["🏪 Ouverture", "🥫 Le grand pot", "🍦 Les cornets", "📐 La bonne boîte", "🧭 La hauteur", "🍨 À ras bord", "🗣️ Le client"]


def variante_c():
    v = "C"
    e = etat(v)
    st.markdown("### 🍦 Mission : le stand de glaces de Lina")
    icones = "".join("✅" if n < len(e["resultats"]) else ("➡️" if n == e["i"] and not e["fini"] else "🔒") for n in range(len(ETAPES_MISSION)))
    with st.container(key="carte_compacte"):
        st.markdown(f"{icones} · 🪙 **{e['points']}** · 🔥 {e['serie']}")
    carte, scene = st.columns([1, 2.2])
    with carte, st.container(key="carte_complete"):
        for n, nom in enumerate(ETAPES_MISSION):
            if n < len(e["resultats"]):
                st.markdown(f"✅ ~~{nom}~~")
            elif n == e["i"] and not e["fini"]:
                st.markdown(f"➡️ **{nom}**")
            else:
                st.markdown(f"🔒 {nom}")
        st.divider()
        st.markdown(f"🪙 **{e['points']}** pièces · 🔥 {e['serie']}")
        for b in e["badges"]:
            st.caption(f"🏅 {b}")
    with scene:
        if e["fini"]:
            st.success("🏆 Mission accomplie : le stand de Lina est prêt !")
            bilan(v)
            return
        ex = EXERCICES[e["i"]]
        st.markdown(f"#### Étape {e['i'] + 1} : {ETAPES_MISSION[e['i']]}")
        st.info(f"🧑‍🍳 **Lina** : {ex['mission']}")
        st.markdown(f"**{ex['enonce']}**")
        afficher_figure(ex, 230)
        if not retour_exercice(v, ex):
            saisie(v, ex, gros=True)
        bloc_aide(v, ex)


# ═══════════════════════ Barre de bascule (prototype uniquement) ═══════════════════════

BARRE_CSS = """
<style>
.st-key-barre_prototype {position: fixed; bottom: 14px; left: 50%; transform: translateX(-50%); z-index: 1000;
  background: #111827; border-radius: 999px; padding: 2px 10px; box-shadow: 0 6px 20px rgba(0,0,0,.35); width: min(430px, 94vw);}
.st-key-barre_prototype [data-testid="stHorizontalBlock"] {flex-direction: row !important; flex-wrap: nowrap !important; align-items: center;}
.st-key-barre_prototype [data-testid="stColumn"] {min-width: 0 !important; width: auto !important;}
.st-key-barre_prototype [data-testid="stColumn"]:nth-child(2) {flex: 1 1 auto !important;}
.st-key-barre_prototype [data-testid="stColumn"]:not(:nth-child(2)) {flex: 0 0 2.4rem !important;}
.st-key-carte_compacte {display: none;}
@media (max-width: 640px) {
  .st-key-carte_compacte {display: block;}
  .st-key-carte_complete {display: none;}
}
.st-key-barre_prototype p, .st-key-barre_prototype button {color: #f9fafb !important;}
.st-key-barre_prototype button {background: transparent !important; border: none !important;}
</style>
"""


def changer(variante):
    st.query_params["variant"] = variante


def barre(courante):
    cles = list(VARIANTES)
    i = cles.index(courante)
    st.markdown(BARRE_CSS, unsafe_allow_html=True)
    with st.container(key="barre_prototype"):
        c1, c2, c3 = st.columns([1, 5, 1], vertical_alignment="center")
        c1.button("◀", key="prec", on_click=changer, args=(cles[i - 1],))
        c2.markdown(f"<p style='text-align:center;margin:0'>PROTOTYPE · {courante} ({VARIANTES[courante]})</p>", unsafe_allow_html=True)
        c3.button("▶", key="suiv", on_click=changer, args=(cles[(i + 1) % len(cles)],))


# ═══════════════════════ Page ═══════════════════════

st.set_page_config(page_title="Prototype — écran d'exercice", page_icon="🧪", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
variante = st.query_params.get("variant", "A")
variante = variante if variante in VARIANTES else "A"

with st.sidebar:  # la vraie barre latérale de l'app, figée sur un profil d'exemple
    st.markdown("# 🎓 Tuteur Maths")
    st.markdown("**Collège · 6ᵉ → 3ᵉ**")
    st.divider()
    st.markdown("👤 **Inès** · 4ème")
    st.markdown("📖 Pyramides et cônes (volumes)")
    st.markdown("❤️ Centres d'intérêt : cuisine")
    st.divider()
    st.caption("🧪 Prototype : contenu écrit à l'avance, aucune IA, rien n'est enregistré.")

{"A": variante_a, "B": variante_b, "C": variante_c}[variante]()
st.write("")
st.write("")
st.write("")
barre(variante)
