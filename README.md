# 🎓 Tuteur de Maths IA — Collège

Tuteur de mathématiques pour collégiens (6ᵉ à 3ᵉ), avec un parcours personnalisé :
**Diagnostic → Entraînement ciblé → Bilan**. Même moteur et même interface que la version lycée,
avec un prompt et des chapitres adaptés au collège.

## Fonctionnalités

- 🔍 **Diagnostic** : 3 exercices rapides pour identifier les acquis
- 🎯 **Entraînement adaptatif** : difficulté ajustée en temps réel, contextes concrets
- 📊 **Bilan de séance** : acquis, points à consolider, prochaine étape
- 🗄️ **Historique** : l'élève retrouve ses séances précédentes
- 👩‍🏫 **Espace professeur** (mot de passe) : suivi de tous les élèves

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
- **Base de données** : Supabase (PostgreSQL)
- **Interface** : Streamlit

## Tests

```bash
pip install -r requirements.txt pytest
python -m pytest -q tests      # IA et base simulées, aucune clé nécessaire
```
