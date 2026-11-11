"""Client Anthropic simulé : reconnaît la tâche demandée par le prompt système et répond comme le tuteur."""

import json
import re

from tests.banque import exercice


class Reponse:
    def __init__(self, texte):
        self.content = [type("Bloc", (), {"text": texte, "type": "text"})()]


class FauxClaude:
    appels: list = []
    defaillances: dict = {}     # format -> nombre de réponses invalides à renvoyer avant une valide
    verdict_redaction = "juste"
    indisponible = False

    def __init__(self, api_key=None):
        self.messages = self

    @classmethod
    def reinitialiser(cls):
        cls.appels, cls.defaillances, cls.verdict_redaction, cls.indisponible = [], {}, "juste", False

    def create(self, **kw):
        assert "temperature" not in kw, "paramètre refusé par l'API en production"
        FauxClaude.appels.append(kw)
        if FauxClaude.indisponible:
            raise ConnectionError("réseau coupé")
        systeme = kw["system"]
        if "Ta tâche : écrire UN exercice" in systeme:
            format_ = re.search(r'"format": "(\w+)"', systeme).group(1)
            if FauxClaude.defaillances.get(format_, 0) > 0:
                FauxClaude.defaillances[format_] -= 1
                return Reponse("Voici un exercice sympa ! (pas de JSON)")
            return Reponse("```json\n" + json.dumps(exercice(format_), ensure_ascii=False) + "\n```")
        if "corriger la réponse rédigée" in systeme:
            return Reponse(json.dumps({"verdict": FauxClaude.verdict_redaction, "retour": "Bien justifié avec les deux volumes."}))
        if "te pose une question" in systeme:
            return Reponse("Pense à la formule du volume : aire de la base × hauteur.")
        if "rédiger le bilan" in systeme:
            return Reponse("Bilan : tu maîtrises le volume du cylindre. Continue !")
        raise AssertionError("prompt inattendu : " + systeme[:80])


def appels_de(tache: str) -> list:
    return [a for a in FauxClaude.appels if tache in a["system"]]
