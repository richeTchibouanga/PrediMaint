"""Modèle : performances sur le jeu de test et comportement sur les scénarios du guide de démonstration."""
import json

import pytest
from conftest import RACINE, machine

from src.donnees import charger, separer
from src.economie import Hypotheses, bilan
from src.explication import expliquer, probabilite, type_probable


def risque(paquet, **mesures):
    return probabilite(paquet["modele"], machine(**mesures), paquet["entrees"])


def test_cibles_du_cahier_des_charges(paquet):
    _, X_te, _, y_te, *_ = separer(charger())
    p = paquet["modele"].predict_proba(X_te[paquet["entrees"]])[:, 1]
    alerte = p >= paquet["seuil"]
    vp = (alerte & (y_te.values == 1)).sum()
    assert vp / y_te.sum() >= 0.85                      # rappel ≥ 85 %
    assert vp / alerte.sum() >= 0.70                    # précision ≥ 70 %


def test_metadonnees_coherentes(paquet):
    meta = json.loads((RACINE / "models" / "metadata.json").read_text(encoding="utf-8"))
    assert meta["seuil_alerte"] == pytest.approx(paquet["seuil"])
    assert meta["entrees"] == paquet["entrees"]


def test_machine_normale_sans_alerte(paquet):
    assert risque(paquet) < 0.05


@pytest.mark.parametrize("mesures, type_attendu", [
    (dict(temp_process=309.0, vitesse=1300, couple=62.0, usure_outil=205), "Surcharge"),
    (dict(gamme="M", temp_air=302.5, temp_process=310.5, vitesse=1330, couple=45.0, usure_outil=60), "Dissipation de chaleur"),
    (dict(gamme="H", temp_air=299.0, temp_process=309.5, vitesse=2700, couple=11.0, usure_outil=30), "Puissance"),
    (dict(vitesse=1250, couple=70.0, usure_outil=50), "Puissance"),
])
def test_scenarios_de_panne(paquet, mesures, type_attendu):
    assert risque(paquet, **mesures) >= 0.6
    t = type_probable(paquet["modele_type"], machine(**mesures), paquet["entrees"])
    assert t.iloc[0]["type"] == type_attendu


def test_frontiere_de_la_panne_de_chaleur(paquet):
    """Deux machines presque identiques, de part et d'autre de la limite physique (8,6 K et 1 380 tr/min)."""
    dedans = risque(paquet, gamme="M", temp_air=302.0, temp_process=310.4, vitesse=1370, couple=45.0, usure_outil=60)
    dehors = risque(paquet, gamme="M", temp_air=302.0, temp_process=310.8, vitesse=1390, couple=45.0, usure_outil=60)
    assert dedans >= 0.6 and dehors < paquet["seuil"]


def test_explication_designe_les_bonnes_causes(paquet):
    ex = expliquer(paquet["modele"], machine(temp_process=309.0, vitesse=1300, couple=62.0, usure_outil=205),
                   paquet["reference"], paquet["entrees"])
    assert set(ex["mesure"].head(2)) == {"Usure de l'outil", "Couple"}


def test_bilan_economique_par_defaut(paquet):
    _, X_te, _, y_te, *_ = separer(charger())
    p = paquet["modele"].predict_proba(X_te[paquet["entrees"]])[:, 1]
    b = bilan(y_te, p, paquet["seuil"], Hypotheses())
    assert b["cout_corrective"] == pytest.approx(697_000)
    assert b["gain"] == pytest.approx(510_000)
