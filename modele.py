"""Exercice modèle photographié (ADR 0002) : préparer la photo pour la lecture, puis vérifier que les
exercices créés en sont de vraies variantes et pas une copie.

La photo ne fait que transiter : elle est réduite en mémoire, envoyée au tuteur pour lecture, puis oubliée.
Seule la transcription confirmée par l'élève est conservée.
"""

from __future__ import annotations

import io
import re
import unicodedata
from difflib import SequenceMatcher

from PIL import Image, ImageOps, UnidentifiedImageError

COTE_MAX = 1568          # au-delà, l'API réduit l'image de toute façon
POIDS_MAX = 15_000_000   # photo brute refusée au-delà (15 Mo)
SEUIL_TEXTE = 0.75       # au-delà, l'énoncé est une quasi-copie du modèle
TYPES_ACCEPTES = ["jpg", "jpeg", "png", "webp"]


class PhotoIllisible(ValueError):
    pass


def preparer_image(octets: bytes) -> bytes:
    """Remet la photo à l'endroit, la réduit et la convertit en JPEG (sans métadonnées : ni GPS ni appareil)."""
    if not octets:
        raise PhotoIllisible("La photo est vide.")
    if len(octets) > POIDS_MAX:
        raise PhotoIllisible("La photo est trop lourde (15 Mo maximum).")
    try:
        image = Image.open(io.BytesIO(octets))
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
    except (UnidentifiedImageError, OSError) as ex:
        raise PhotoIllisible("Ce fichier n'est pas une photo lisible (formats acceptés : JPG, PNG, WEBP).") from ex
    image.thumbnail((COTE_MAX, COTE_MAX))
    sortie = io.BytesIO()
    image.save(sortie, format="JPEG", quality=85)   # pas d'exif=… : les métadonnées ne sont pas recopiées
    return sortie.getvalue()


def _normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w,.]+", " ", texte)).strip()


def nombres(texte: str) -> list[str]:
    return sorted(n.replace(",", ".") for n in re.findall(r"\d+(?:[.,]\d+)?", texte or ""))


def trop_proche(exercice: dict, modele: str) -> str | None:
    """Raison du refus si l'exercice recopie le modèle (même texte, ou exactement les mêmes nombres), sinon None."""
    texte = f"{exercice.get('mission', '')} {exercice.get('enonce', '')}"
    if SequenceMatcher(None, _normaliser(texte), _normaliser(modele)).ratio() >= SEUIL_TEXTE:
        return "l'énoncé recopie l'exercice modèle : écris une autre situation avec d'autres nombres"
    nb_ex, nb_modele = nombres(texte), nombres(modele)
    if len(nb_modele) >= 2 and nb_ex == nb_modele:
        return "l'exercice reprend exactement les nombres de l'exercice modèle : change les nombres"
    return None
