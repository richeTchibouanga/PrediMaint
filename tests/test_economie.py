"""Calcul économique sur un petit exemple vérifiable à la main."""
import numpy as np
import pytest

from src.economie import Hypotheses, bilan, courbe_couts


def test_cout_d_une_panne():
    assert Hypotheses().cout_panne == pytest.approx(4 * 350 + 500 + 150)   # 2 050 €


def test_bilan_calculable_a_la_main():
    # 4 relevés : 2 pannes (une détectée, une manquée), 1 fausse alerte, 1 relevé normal sans alerte
    y = np.array([1, 1, 0, 0])
    p = np.array([0.9, 0.1, 0.8, 0.0])
    h = Hypotheses(duree_arret_panne_h=0, cout_reparation=1000, cout_piece_rebutee=0,
                   cout_intervention_preventive=200, cout_fausse_alerte=50, cout_solution_an=0, operations_par_an=4)
    b = bilan(y, p, 0.5, h)
    assert b["cout_corrective"] == pytest.approx(2 * 1000)
    assert b["cout_predictive"] == pytest.approx(200 + 1000 + 50)
    assert b["gain"] == pytest.approx(750)
    assert (b["pannes_evitees"], b["pannes_manquees"], b["fausses_alertes"]) == (1, 1, 1)


def test_courbe_couvre_les_seuils():
    c = courbe_couts(np.array([1, 0]), np.array([0.7, 0.2]), Hypotheses())
    assert c["seuil"].min() == pytest.approx(0.02) and c["seuil"].max() == pytest.approx(0.98)
