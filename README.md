# 🎓 Tuteur de Maths IA — Collège

Tuteur de mathématiques pour collégiens (6ᵉ à 3ᵉ), avec un parcours personnalisé :
**Diagnostic → Entraînement ciblé → Bilan**, en exercices courts, variés et ludiques. Cette refonte
(exercices structurés, carte de jeu) sera reportée à la version lycée une fois validée par les élèves.

## Fonctionnalités

- 🃏 **Carte de jeu** : un exercice par écran, points, série et progression visibles (choisie par les élèves, voir `PROTOTYPE.md` sur la branche `prototype/ecran-exercice`)
- 🔀 **Six formats en rotation** : QCM, réponse numérique, vrai ou faux, texte à trous, étapes dans l'ordre, et une réponse rédigée environ une fois sur cinq. Jamais deux fois le même format d'affilée.
- 📐 **Figures cotées dessinées par l'app** : cône, cylindre, triangle rectangle, pavé, pyramide, cercle, droite dans un repère
- ✅ **Correction instantanée par l'app** pour les formats fermés ; les corrigés numériques du tuteur sont recalculés et refusés s'ils sont faux
- 💡 **Aide en boutons** : indice, autre indice, correction ; une question libre au tuteur, qui ne donne pas la solution
- 🔍 **Diagnostic → entraînement → bilan** tenus par l'app ; difficulté ajustée aux résultats ; bilan fondé sur les vrais résultats
- 👩‍🏫 **Espace professeur** (mot de passe) : suivi de tous les élèves

Vocabulaire du projet : `GLOSSARY.md`. Décisions : `docs/adr/`.

## Architecture

| Fichier | Rôle |
|---|---|
| `app.py` | Page Streamlit : accueil et profil, espace prof, sauvegarde Supabase |
| `ecran.py` | Écran « carte de jeu » |
| `seance.py` | Déroulé d'une séance (sans Streamlit, testable) |
| `exercices.py` | Contrat d'exercice, correction, rotation des formats, barème |
| `figures.py` | Figures cotées |
| `tuteur.py` | Prompts et appels à l'API Claude |

## Déploiement (Streamlit Cloud + Supabase)

### 1. Base de données

Dans Supabase → **SQL Editor** → coller `supabase_setup.sql` → **Run**.
Le script peut être relancé sans risque. Il fonctionne dans le même projet Supabase que la version lycée
(table séparée `sessions_college`).

### 2. Application

[share.streamlit.io](https://share.streamlit.io) → *New app* → ce dépôt, branche `main`, fichier `app.py`
→ *Advanced settings* → **Secrets** :

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "sb_secret_..."
MOT_DE_PASSE_PROF = "choisissez-un-mot-de-passe"
```

**Utilisez la clé secrète Supabase** (*Project Settings → API Keys*, clé `sb_secret_…`, ou `service_role`
dans *Legacy API Keys*), **jamais la clé publique**. Les élèves sont mineurs : la table n'a aucune politique
d'accès public, et aucun identifiant n'est écrit dans le code. Si la clé manque ou est la clé publique,
l'app fonctionne sans historique et l'espace professeur indique quoi corriger.

## Chapitres

- **6ᵉ** : nombres entiers et décimaux, opérations, fractions, proportionnalité, géométrie plane, aires, symétrie axiale…
- **5ᵉ** : relatifs, fractions, pourcentages, expressions littérales, triangles, symétrie centrale, volumes…
- **4ᵉ** : calcul littéral, équations, Pythagore, translations et rotations, puissances, probabilités…
- **3ᵉ** : identités remarquables, fonctions, Thalès, trigonométrie, homothéties, Scratch…

## Technologies

- **IA** : API Claude (`claude-haiku-4-5`)
- **Figures** : matplotlib
- **Base de données** : Supabase (PostgreSQL)
- **Interface** : Streamlit

## Tests

```bash
pip install -r requirements.txt pytest
python -m pytest -q tests      # IA et base simulées, aucune clé nécessaire
```
