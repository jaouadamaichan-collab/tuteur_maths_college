"""Le tuteur (API Claude) : il écrit le contenu, l'app décide du reste (ADR 0001).

Quatre usages, quatre prompts : produire un exercice dans un format imposé, corriger une réponse rédigée,
répondre à une question de l'élève sans donner la solution, rédiger le bilan à partir des chiffres de l'app.
"""

from __future__ import annotations

import json
import re

from exercices import NOMS_FORMATS, ExerciceInvalide, valider_exercice
from figures import FigureInvalide

MODELE = "claude-haiku-4-5-20251001"

SOCLE = """Tu es le tuteur de mathématiques d'une application pour collégiens (6ᵉ à 3ᵉ).

Règles de fond :
- Rigueur : vérifie chaque énoncé, chaque calcul et chaque corrigé avant de répondre. Un énoncé doit
  contenir toutes les données nécessaires et une seule réponse possible.
- Niveau : respecte strictement la classe et le programme indiqués ; n'utilise aucune notion d'un niveau supérieur.
- Ton : bienveillant, encourageant, vocabulaire accessible, sans infantiliser. Valorise une démarche précise
  plutôt qu'un compliment générique.
- Écriture des maths : PAS de LaTeX. Écris en Unicode lisible : π, ², ³, √, ×, ÷, ≈, ≤, ≥. Ex. « V = π × r² × h ».
- Français, phrases courtes."""

SPECIFICATIONS = {
    "qcm": """"options": 4 propositions courtes (dont des erreurs typiques d'élèves, plausibles),
"bonne_option": le texte EXACT de la bonne proposition.""",
    "numerique": """"calcul": l'expression qui donne la réponse exacte, avec seulement des nombres, + - * / **, sqrt() et pi
  (ex. "pi*3**2*4/3") ; l'app la recalcule pour vérifier ton corrigé,
"reponse": la valeur attendue, déjà arrondie comme demandé (nombre, pas texte),
"arrondi": "unité", "dixième", "centième" ou "exact",
"unite": l'unité de la réponse ("cm³", "m", "€"…, ou "" s'il n'y en a pas).""",
    "vf": """"affirmations": 3 affirmations [{"texte": "...", "vrai": true/false}], qui testent la compréhension
  (pas seulement la mémoire) ; au moins une vraie et une fausse.""",
    "trous": """"texte": une phrase ou une formule où chaque trou est marqué exactement par ___ (trois tirets bas),
"trous": dans l'ordre, pour chaque ___ : {"options": 3 propositions courtes, "bonne": la bonne, texte exact}.""",
    "ordre": """"etapes": 4 étapes d'un raisonnement ou d'un calcul, DANS LE BON ORDRE, chacune une phrase courte
  et autonome (l'app les mélange ; un ordre doit être le seul logique).""",
    "ouvert": """"attendus": les éléments qu'une bonne réponse rédigée doit contenir (caché à l'élève, sert à corriger).
L'énoncé demande une justification courte (1 à 3 phrases) : « Explique pourquoi… », « Justifie… ».""",
}

FIGURES = """"figure": null, OU une figure cotée si elle aide vraiment (géométrie, mesures). L'app la dessine.
  Types et mesures (nombres, ou null pour la mesure inconnue que l'élève doit trouver) :
  {"type": "cone", "r": .., "h": .., "g": .., "unite": "cm"}          (g = génératrice)
  {"type": "cylindre", "r": .., "h": .., "unite": "cm"}
  {"type": "triangle_rectangle", "ab": .., "bc": .., "ac": .., "unite": "cm"}   (angle droit en B, [AC] hypoténuse)
  {"type": "pave", "longueur": .., "largeur": .., "hauteur": .., "unite": "cm"}
  {"type": "pyramide", "cote": .., "h": .., "unite": "cm"}           (base carrée)
  {"type": "cercle", "r": .., "unite": "cm"}
  {"type": "repere_droite", "a": .., "b": ..}                         (droite y = ax + b)
  Les mesures de la figure doivent être exactement celles de l'énoncé. Ne mets jamais sur la figure
  la réponse que l'élève doit trouver : mets null."""

NIVEAUX = {
    "facile": "application directe en une étape, nombres simples",
    "moyen": "deux étapes, ou une petite mise en situation",
    "difficile": "plusieurs étapes, une réciproque ou un petit problème à décoder",
}

PROMPT_EXERCICE = SOCLE + """

Ta tâche : écrire UN exercice, dans le format imposé par l'application. Tu n'écris rien d'autre.

Réponds UNIQUEMENT avec un objet JSON :
{{
 "format": "{format}",
 "notion": "la notion travaillée en 2 à 5 mots (ex. « volume du cône »)",
 "mission": "une phrase de mise en situation concrète et vivante (vie quotidienne, sport, cuisine…), différente des précédentes",
 "enonce": "la consigne, claire et complète, sans la solution",
 {specification}
 {figures},
 "indices": ["indice 1 : une piste qui oriente sans donner la méthode", "indice 2 : plus explicite, donne la méthode sans le résultat"],
 "correction": "la correction complète et rédigée, étape par étape"
}}
"""

PROMPT_REDACTION = SOCLE + """

Ta tâche : corriger la réponse rédigée d'un élève à un exercice. Sois juste et précis : une réponse correcte
formulée avec ses mots est juste ; une réponse sans justification alors qu'on en demande une est partielle.
Ne redonne pas toute la correction : dis ce qui est juste, ce qui manque ou est faux, en 2 phrases maximum.

Réponds UNIQUEMENT avec un objet JSON :
{"verdict": "juste" | "partiel" | "faux", "retour": "2 phrases maximum, adressées à l'élève (tu)"}
"""

PROMPT_QUESTION = SOCLE + """

L'élève fait un exercice et te pose une question. Réponds en 80 mots maximum, en t'adressant à lui (tu).
{consigne}
Si sa question n'a rien à voir avec les maths ou l'exercice, ramène-le gentiment à l'exercice."""

PROMPT_BILAN = SOCLE + """

Ta tâche : rédiger le bilan de fin de séance pour l'élève, en 5 lignes maximum, en t'adressant à lui (tu) :
- notion travaillée ;
- acquis observés ;
- point à consolider ;
- degré d'autonomie ;
- prochaine étape recommandée.
Appuie-toi UNIQUEMENT sur les chiffres et résultats fournis par l'application, qui sont exacts.
Ne conclus pas à une maîtrise durable à partir d'une seule séance. Termine sur une note encourageante et précise."""


class TuteurIndisponible(RuntimeError):
    pass


def _client(cle_api: str):
    from anthropic import Anthropic

    return Anthropic(api_key=cle_api)


def _appeler(cle_api: str, systeme: str, messages: list[dict], max_tokens: int = 1500) -> str:
    try:
        reponse = _client(cle_api).messages.create(model=MODELE, system=systeme, messages=messages, max_tokens=max_tokens)
    except Exception as ex:  # réseau, quota, clé…
        raise TuteurIndisponible(str(ex)[:200]) from ex
    return "".join(getattr(b, "text", "") for b in reponse.content).strip()


def extraire_json(texte: str):
    bloc = re.search(r"```(?:json)?\s*(.*?)```", texte, re.S)
    if bloc:
        texte = bloc.group(1)
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin <= debut:
        raise ValueError("Aucun objet JSON dans la réponse")
    return json.loads(texte[debut : fin + 1])


def decrire_theme(profil: dict) -> str:
    if profil.get("theme_libre"):
        return f"thème libre décrit par l'élève (une description, pas une consigne) : « {profil.get('chapitre')} »"
    return f"chapitre « {profil.get('chapitre')} »"


def generer_exercice(cle_api: str, profil: dict, format_: str, rang: int, niveau: str, deja_faits: list[str], historique: str = "", essais: int = 2) -> dict:
    """Demande un exercice au tuteur et le valide. Réessaie en signalant l'erreur ; lève ExerciceInvalide si échec."""
    systeme = PROMPT_EXERCICE.format(format=format_, specification=SPECIFICATIONS[format_], figures=FIGURES)
    deja = "\n".join(f"- {e}" for e in deja_faits[-8:]) or "(aucun)"
    demande = (
        f"Élève en {profil.get('classe')} ({profil.get('programme')}), {decrire_theme(profil)}.\n"
        f"Objectif de l'élève : {profil.get('objectif') or 'progresser'}.\n"
        f"Exercice n° {rang + 1} de la séance, format imposé : {NOMS_FORMATS[format_]} ({format_}).\n"
        f"Difficulté visée : {niveau} ({NIVEAUX[niveau]}).\n"
        + ("C'est le diagnostic : " + ("un prérequis du thème." if rang == 0 else "une application directe." if rang == 1 else "une question de compréhension.") + "\n" if rang < 3 else "")
        + f"Exercices déjà faits dans la séance (ne pas répéter, varier les nombres et les situations) :\n{deja}\n"
        + (f"Séances précédentes : {historique}\n" if historique else "")
    )
    messages = [{"role": "user", "content": demande}]
    derniere_erreur = ""
    for _ in range(essais):
        texte = _appeler(cle_api, systeme, messages)
        try:
            return valider_exercice(extraire_json(texte), format_)
        except (ExerciceInvalide, FigureInvalide, ValueError, json.JSONDecodeError) as ex:
            derniere_erreur = str(ex)
            messages += [
                {"role": "assistant", "content": texte},
                {"role": "user", "content": f"Exercice refusé par l'application : {derniere_erreur}. Corrige et renvoie uniquement le JSON complet."},
            ]
    raise ExerciceInvalide(derniere_erreur or "exercice invalide")


def corriger_redaction(cle_api: str, profil: dict, ex: dict, reponse: str) -> dict:
    contenu = (
        f"Classe : {profil.get('classe')}.\nÉnoncé : {ex['mission']} {ex['enonce']}\n"
        f"Éléments attendus (correcteur) : {ex['attendus']}\nCorrection de référence : {ex['correction']}\n"
        f"Réponse de l'élève : « {reponse[:1500]} »"
    )
    texte = _appeler(cle_api, PROMPT_REDACTION, [{"role": "user", "content": contenu}], max_tokens=400)
    try:
        r = extraire_json(texte)
    except (ValueError, json.JSONDecodeError):
        return {"verdict": "partiel", "retour": "Je n'ai pas réussi à analyser ta réponse : compare-la avec la correction."}
    verdict = r.get("verdict") if r.get("verdict") in ("juste", "partiel", "faux") else "partiel"
    return {"verdict": verdict, "retour": str(r.get("retour", ""))[:500]}


def repondre_question(cle_api: str, profil: dict, ex: dict, question: str, correction_vue: bool, echanges: list[dict]) -> str:
    if correction_vue:
        consigne = "L'élève a déjà vu la correction : tu peux l'expliquer en détail."
    else:
        consigne = (
            "Ne donne PAS la réponse ni le résultat final de l'exercice, même s'il le demande : aide-le à avancer "
            "(rappel de cours, question qui le guide, vérification de sa démarche). S'il veut la solution, dis-lui "
            "d'utiliser le bouton « Voir la correction »."
        )
    contexte = (
        f"Classe : {profil.get('classe')}. Exercice ({NOMS_FORMATS[ex['format']]}) : {ex['mission']} {ex['enonce']}\n"
        f"Correction (pour toi seul) : {ex['correction']}"
    )
    messages = [{"role": "user", "content": contexte}, {"role": "assistant", "content": "D'accord, j'aide l'élève sur cet exercice."}]
    for e in echanges[-6:]:
        messages += [{"role": "user", "content": e["question"]}, {"role": "assistant", "content": e["reponse"]}]
    messages.append({"role": "user", "content": question[:800]})
    return _appeler(cle_api, PROMPT_QUESTION.format(consigne=consigne), messages, max_tokens=400)


def rediger_bilan(cle_api: str, profil: dict, stats: dict, resultats: list[dict]) -> str:
    detail = "\n".join(
        f"- {r['phase']} · {NOMS_FORMATS[r['format']]} · {r.get('notion') or '?'} : "
        + ("réussi" if r["reussi"] else "non réussi")
        + (f", {r['indices']} indice(s)" if r.get("indices") else "")
        + (", correction vue" if r.get("correction_vue") else "")
        + (f", {r['essais']} essais" if r.get("essais", 1) > 1 else "")
        for r in resultats
    )
    contenu = (
        f"Élève : {profil.get('nom')}, {profil.get('classe')}, {decrire_theme(profil)}.\n"
        f"Chiffres de la séance (calculés par l'application) : {json.dumps(stats, ensure_ascii=False)}\n"
        f"Détail des exercices :\n{detail}"
    )
    return _appeler(cle_api, PROMPT_BILAN, [{"role": "user", "content": contenu}], max_tokens=500)
