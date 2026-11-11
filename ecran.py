"""Écran d'exercice « carte de jeu » (version A du prototype, choisie par les élèves le 11/11/2026)."""

from __future__ import annotations

import re

import streamlit as st

import exercices as E
import progression as P
import seance as S
from figures import dessiner

PHASES = {"diagnostic": "🔍 Diagnostic", "entrainement": "🎯 Entraînement"}


def brut(texte: str) -> str:
    """Neutralise la mise en forme Markdown/LaTeX dans un texte écrit par le tuteur."""
    return re.sub(r"([\\*_\[\]$`#])", r"\\\1", str(texte or ""))


@st.cache_data(show_spinner=False)
def _image_figure(cle: str, figure: dict) -> bytes:
    return dessiner(figure)


def compteurs(s: dict) -> None:
    blocs = (("⭐ Points", s["points"]), ("🔥 Série", s["serie"]), ("🏅 Badges", len(S.badges(s))))
    st.markdown(
        "<div style='display:flex;gap:.6rem;flex-wrap:nowrap;margin-bottom:.4rem'>"
        + "".join(
            "<div style='flex:1;background:#f1f5f9;border-radius:.8rem;padding:.45rem;text-align:center'>"
            f"<div style='font-size:1.55rem;font-weight:800;color:#1e3a5f'>{v}</div>"
            f"<div style='font-size:.75rem;color:#64748b'>{lib}</div></div>"
            for lib, v in blocs
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    fait = min(s["rang"] + (1 if s["reussi"] else 0), s["nb_total"])
    st.progress(fait / s["nb_total"], text=f"Exercice {min(s['rang'] + 1, s['nb_total'])} sur {s['nb_total']}")


def zone_reponse(s: dict, cle_api: str) -> None:
    ex, k = s["exercice"], f"r{s['rang']}"
    f = ex["format"]
    if f == "qcm":
        cols = st.columns(2)
        for n, opt in enumerate(ex["options"]):
            if cols[n % 2].button(brut(opt), key=f"{k}_qcm_{n}", use_container_width=True):
                S.repondre(s, opt)
                st.rerun()
    elif f == "numerique":
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        unite = f" ({ex['unite']})" if ex.get("unite") else ""
        arrondi = "" if ex["arrondi"] == "exact" else f", arrondie au {ex['arrondi']}"
        val = c1.text_input(f"Ta réponse{unite}{arrondi}", key=f"{k}_num", placeholder="ex : 12,5")
        if c2.button("Valider", key=f"{k}_okn", type="primary", use_container_width=True) and val.strip():
            S.repondre(s, val)
            st.rerun()
    elif f == "vf":
        reponses = []
        for n, a in enumerate(ex["affirmations"]):
            c1, c2 = st.columns([4, 2], vertical_alignment="center")
            c1.markdown(f"**{n + 1}.** {brut(a['texte'])}")
            reponses.append(c2.segmented_control(f"Affirmation {n + 1}", ["Vrai", "Faux"], key=f"{k}_vf_{n}", label_visibility="collapsed"))
        if st.button("Valider", key=f"{k}_okvf", type="primary", disabled=None in reponses):
            S.repondre(s, [r == "Vrai" for r in reponses])
            st.rerun()
    elif f == "trous":
        cols = st.columns(len(ex["trous"]))
        choix = [cols[n].selectbox(f"Trou {n + 1}", ["…", *t["options"]], key=f"{k}_tr_{n}") for n, t in enumerate(ex["trous"])]
        morceaux = ex["texte"].split(E.TROU)
        st.markdown(brut(morceaux[0]) + "".join(f" **[{brut(c) if c != '…' else '____'}]** " + brut(m) for c, m in zip(choix, morceaux[1:])))
        if st.button("Valider", key=f"{k}_oktr", type="primary", disabled="…" in choix):
            S.repondre(s, choix)
            st.rerun()
    elif f == "ordre":
        st.caption("Clique les étapes dans l'ordre.")
        for n, etape in enumerate(s["ordre"]):
            st.success(f"{n + 1}. {brut(etape)}")
        restantes = [e for e in ex["melange"] if e not in s["ordre"]]
        for n, etape in enumerate(restantes):
            if st.button(brut(etape), key=f"{k}_ord_{len(s['ordre'])}_{n}", use_container_width=True):
                s["ordre"].append(etape)
                st.rerun()
        c1, c2 = st.columns(2)
        if s["ordre"] and c1.button("↺ Recommencer", key=f"{k}_rz"):
            s["ordre"] = []
            st.rerun()
        if not restantes and c2.button("Valider", key=f"{k}_oko", type="primary"):
            S.repondre(s, list(s["ordre"]))
            st.rerun()
    elif f == "ouvert":
        texte = st.text_area("Ta réponse (1 à 3 phrases)", key=f"{k}_ouv", height=100)
        if st.button("Envoyer au tuteur", key=f"{k}_okouv", type="primary", disabled=not texte.strip()):
            with st.spinner("Le tuteur lit ta réponse…"):
                S.rediger(s, cle_api, texte)
            st.rerun()


def zone_aide(s: dict, cle_api: str) -> None:
    ex, k = s["exercice"], f"r{s['rang']}"
    for n in range(s["indices"]):
        st.info(f"💡 Indice {n + 1} : {brut(ex['indices'][n])}")
    if s["correction_vue"]:
        st.warning(f"📖 Correction : {brut(ex['correction'])}")
    if s["reussi"]:
        return
    if not s["correction_vue"]:
        libelle = ("💡 Un indice", "💡 Un autre indice", "📖 Voir la correction")[s["indices"]]
        if st.button(libelle, key=f"{k}_aide_{s['indices']}", use_container_width=True):
            S.demander_aide(s)
            st.rerun()
    elif st.button("Passer à l'exercice suivant (non compté)", key=f"{k}_passer"):
        S.passer(s)
        S.exercice_suivant(s, cle_api, st.session_state.get("_sauvegarder"))
        st.rerun()
    with st.expander("💬 Une question sur cet exercice ?"):
        for e in s["echanges"]:
            st.markdown(f"**Toi :** {brut(e['question'])}")
            st.markdown(f"**Tuteur :** {brut(e['reponse'])}")
        with st.form(f"{k}_question", clear_on_submit=True):
            question = st.text_input("Ta question", placeholder="Ex : pourquoi on divise par 3 ?")
            if st.form_submit_button("Demander") and question.strip():
                with st.spinner("Le tuteur réfléchit…"):
                    S.poser_question(s, cle_api, question.strip())
                st.rerun()


def zone_retour(s: dict, cle_api: str, sauvegarder) -> None:
    r = s["retour"]
    if not r:
        return
    if r["ok"]:
        msg = f"✅ Bravo ! +{r['gain']} points" + (f" +{r['bonus']} (série de {s['serie']} 🔥)" if r["bonus"] else "")
        if r.get("texte"):
            msg += f"\n\n{brut(r['texte'])}"
        st.success(msg)
        dernier = s["rang"] + 1 >= s["nb_total"]
        if st.button("Voir mon bilan →" if dernier else "Exercice suivant →", key=f"r{s['rang']}_suivant", type="primary", use_container_width=True):
            with st.spinner("Le tuteur prépare la suite…" if not dernier else "Le tuteur rédige ton bilan…"):
                S.exercice_suivant(s, cle_api, sauvegarder)
            st.rerun()
    else:
        st.error("Pas tout à fait." + (f" {brut(r['texte'])}" if r.get("texte") else "") + " Réessaie, ou prends un indice.")


def carte(s: dict, cle_api: str, sauvegarder) -> None:
    compteurs(s)
    if s["erreur"]:
        st.error(s["erreur"])
        if st.button("Réessayer", type="primary"):
            with st.spinner("Le tuteur prépare l'exercice…"):
                S.preparer_exercice(s, cle_api)
            st.rerun()
        return
    ex = s["exercice"]
    _, centre, _ = st.columns([1, 8, 1])
    with centre, st.container(border=True):
        st.caption(f"{PHASES[S.phase_courante(s)].upper()} · {E.NOMS_FORMATS[ex['format']]}" + (f" · {brut(ex['notion'])}" if ex.get("notion") else ""))
        if ex.get("mission"):
            st.markdown(f"*{brut(ex['mission'])}*")
        st.markdown(f"#### {brut(ex['enonce'])}")
        if ex.get("figure"):
            st.image(_image_figure(repr(sorted(ex["figure"].items())), ex["figure"]), width=260)
        if not s["reussi"]:
            zone_reponse(s, cle_api)
        zone_retour(s, cle_api, sauvegarder)
        zone_aide(s, cle_api)


def bilan(s: dict) -> None:
    st_ = s["stats"]
    if not st.session_state.get("_ballons_montres"):
        st.balloons()
        st.session_state["_ballons_montres"] = True
    st.markdown(f"## 🎉 Séance terminée : +{s['points']} points")
    st.caption(f"🏆 Ton total : {S.total_points(s)} points")
    c1, c2, c3 = st.columns(3)
    c1.metric("Exercices réussis", f"{st_['reussis']} / {st_['exercices']}")
    c2.metric("Sans aucune aide", st_["sans_aide"])
    c3.metric("Avec des indices", st_["avec_indices"])
    if s["badges_nouveaux"]:
        st.success("Nouveaux badges : " + " · ".join(f"**{P.libelle(b)}**" for b in s["badges_nouveaux"]))
    st.info(brut(s["bilan"]))
    with st.expander(f"🏅 Ma collection de badges ({len(S.badges(s))} sur {len(P.BADGES)})"):
        for b, (emoji, nom, comment) in P.BADGES.items():
            if b in S.badges(s):
                st.markdown(f"{emoji} **{nom}** · {comment}")
            else:
                st.markdown(f"🔒 {nom} · *{comment}*")


def feter_badges(s: dict) -> None:
    """Annonce chaque nouveau badge une seule fois (décision Q10 : célébration)."""
    while s["a_feter"]:
        b = s["a_feter"].pop(0)
        emoji, nom, comment = P.BADGES[b]
        st.toast(f"Nouveau badge : **{nom}** · {comment}", icon=emoji)


def afficher(s: dict, cle_api: str, sauvegarder) -> None:
    st.session_state["_sauvegarder"] = sauvegarder
    feter_badges(s)
    if s["termine"]:
        bilan(s)
    else:
        carte(s, cle_api, sauvegarder)
