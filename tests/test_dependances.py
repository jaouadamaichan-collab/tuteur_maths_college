"""Chaque bibliothèque importée par l'app doit figurer dans requirements.txt (sinon Streamlit Cloud plante)."""

import ast
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
LOCAUX = {p.stem for p in RACINE.glob("*.py")}
NOMS_PAQUETS = {"streamlit": "streamlit", "anthropic": "anthropic", "supabase": "supabase", "matplotlib": "matplotlib"}


def test_imports_couverts_par_requirements():
    declares = {l.split(">=")[0].split("==")[0].strip().lower() for l in (RACINE / "requirements.txt").read_text().splitlines() if l.strip()}
    manquants = set()
    for fichier in RACINE.glob("*.py"):
        for noeud in ast.walk(ast.parse(fichier.read_text())):
            modules = []
            if isinstance(noeud, ast.Import):
                modules = [a.name for a in noeud.names]
            elif isinstance(noeud, ast.ImportFrom) and noeud.module and noeud.level == 0:
                modules = [noeud.module]
            for m in modules:
                racine = m.split(".")[0]
                if racine in LOCAUX or racine in sys.stdlib_module_names:
                    continue
                if NOMS_PAQUETS.get(racine, racine).lower() not in declares:
                    manquants.add(f"{racine} ({fichier.name})")
    assert not manquants, f"À ajouter dans requirements.txt : {sorted(manquants)}"


def test_streamlit_assez_recent_pour_segmented_control():
    ligne = next(l for l in (RACINE / "requirements.txt").read_text().splitlines() if l.startswith("streamlit"))
    majeure, mineure = (int(x) for x in ligne.split(">=")[1].split(".")[:2])
    assert (majeure, mineure) >= (1, 40)
