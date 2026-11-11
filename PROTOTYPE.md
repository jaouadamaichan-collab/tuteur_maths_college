# Prototype : écran d'exercice (branche `prototype/ecran-exercice`, ne pas fusionner)

**Question posée** : à quoi doit ressembler l'écran d'exercice pour que la séance soit ludique ?
Trois versions structurellement différentes, sur le même contenu (cônes et cylindres, 4ᵉ, 7 exercices
écrits à l'avance, un par format). Aucune IA, rien n'est enregistré.

| Version | Idée |
|---|---|
| **A · Carte de jeu** | Un exercice par écran, gros boutons, points / série / badges en haut, barre de progression. |
| **B · Chat enrichi** | La conversation actuelle, avec l'exercice cliquable dans le fil et le chat toujours ouvert. |
| **C · Mode mission** | Le stand de glaces de Lina : 7 étapes à débloquer, des pièces au lieu des points. |

On passe d'une version à l'autre avec la barre noire en bas (◀ ▶), ou avec `?variant=A`, `B`, `C` dans l'adresse.

## Mettre en ligne

share.streamlit.io → *New app* → dépôt `tuteur_maths_college`, **branche `prototype/ecran-exercice`**,
fichier `prototype_ecran_exercice.py`. Aucun secret nécessaire.

## Faire tester (3 à 5 élèves, 10 minutes chacun)

Chaque élève fait 3 ou 4 exercices dans **chacune** des trois versions, en commençant par une version
différente d'un élève à l'autre (A puis B puis C, puis B C A, puis C A B…), pour que la première ne soit
pas toujours avantagée. Observer sans aider : où il hésite, ce qu'il clique, s'il sourit ou soupire.

Puis trois questions, dans cet ordre :

1. **Si tu devais refaire une séance demain, laquelle choisirais-tu ? Pourquoi ?**
2. **À quel moment as-tu eu envie de continuer ?** (un exercice, un bouton, les points, l'histoire…)
3. **À quel moment t'es-tu ennuyé·e ou énervé·e ?**

Noter aussi : la classe de l'élève, et s'il a demandé des indices.

## Ce qu'on en fera

La version gagnante (ou un mélange : « les points de A avec l'histoire de C ») sera réécrite proprement
dans l'app. Cette branche restera comme trace du test et ne sera jamais fusionnée dans `main`.
