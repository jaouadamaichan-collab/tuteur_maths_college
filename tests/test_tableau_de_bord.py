"""Tableau de bord de l'élève : série de jours, objectif du jour, séance recommandée."""

import json

import progression as P


def seance(date, chapitre="Pyramides et cônes (volumes)", exercices=6, sans_aide=3):
    return {"date_session": f"{date}T17:00:00", "chapitre": chapitre, "nb_exercices": exercices,
            "messages": json.dumps({"resultats": [], "points": 40, "badges": [],
                                    "stats": {"exercices": exercices, "sans_aide": sans_aide}})}


def test_serie_de_jours():
    s = [seance("2026-11-25"), seance("2026-11-24"), seance("2026-11-23"), seance("2026-11-20")]
    assert P.jours_de_suite(s, "2026-11-25") == (3, True)


def test_serie_en_cours_si_seance_hier():
    assert P.jours_de_suite([seance("2026-11-24"), seance("2026-11-23")], "2026-11-25") == (2, False)


def test_serie_cassee():
    assert P.jours_de_suite([seance("2026-11-22")], "2026-11-25") == (0, False)
    assert P.jours_de_suite([], "2026-11-25") == (0, False)


def test_exercices_du_jour():
    s = [seance("2026-11-25", exercices=6), seance("2026-11-25", exercices=10), seance("2026-11-24", exercices=14)]
    assert P.exercices_du_jour(s, "2026-11-25") == 16


CHAPITRES = ["Théorème de Pythagore", "Pyramides et cônes (volumes)", "Puissances"]


def test_recommande_le_chapitre_le_plus_fragile():
    s = [seance("2026-11-25", "Pyramides et cônes (volumes)", 10, 4), seance("2026-11-24", "Théorème de Pythagore", 10, 9)]
    assert P.recommandation(s, CHAPITRES) == {"chapitre": "Pyramides et cônes (volumes)", "raison": "À consolider : 40 % de réussite sans aide"}


def test_sinon_premier_chapitre_pas_encore_travaille():
    s = [seance("2026-11-25", "Théorème de Pythagore", 10, 9)]
    assert P.recommandation(s, CHAPITRES)["chapitre"] == "Pyramides et cônes (volumes)"
    assert P.recommandation([], CHAPITRES) == {"chapitre": "Théorème de Pythagore", "raison": "Pas encore travaillé"}


def test_tout_reussi_le_plus_ancien():
    s = [seance(f"2026-11-2{i}", ch, 10, 10) for i, ch in enumerate(CHAPITRES)]
    assert P.recommandation(s, CHAPITRES) == {"chapitre": "Théorème de Pythagore", "raison": "À revoir pour ne pas oublier"}


def test_chapitres_d_une_autre_classe_ignores():
    s = [seance("2026-11-25", "Thème libre de l'élève", 10, 0)]
    assert P.recommandation(s, CHAPITRES)["chapitre"] == "Théorème de Pythagore"
    assert P.recommandation(s, []) is None
