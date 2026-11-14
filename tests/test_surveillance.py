"""Surveillance en continu simulée : extraits du flux et bilan des alertes."""
import pandas as pd
import pytest

from src.surveillance import SEGMENTS, bilan, flux_de_test, machines


@pytest.fixture(scope="module")
def simu(paquet):
    return machines(flux_de_test(paquet["modele"], paquet["modele_type"], paquet["entrees"]))


def test_flux_dans_l_ordre_d_origine(paquet):
    flux = flux_de_test(paquet["modele"], paquet["modele_type"], paquet["entrees"])
    assert len(flux) == 2000 and flux["UDI"].is_monotonic_increasing


def test_trois_machines_de_30_releves(simu):
    assert list(simu) == list(SEGMENTS)
    for seg in simu.values():
        assert len(seg) == 30 and list(seg["releve"]) == list(range(1, 31))


def test_toutes_les_pannes_reelles_sont_detectees(simu, paquet):
    """Résultat annoncé dans le guide : 7 pannes réelles, 7 détectées, 3 fausses alertes."""
    tot = [bilan(seg, paquet["seuil"]) for seg in simu.values()]
    assert sum(t["pannes"] for t in tot) == 7
    assert sum(t["detectees"] for t in tot) == 7
    assert sum(t["fausses_alertes"] for t in tot) == 3


def test_bilan_calculable_a_la_main():
    seg = pd.DataFrame({"risque": [0.9, 0.1, 0.8, 0.0], "panne": [1, 1, 0, 0]})
    assert bilan(seg, 0.5) == {"releves": 4, "pannes": 2, "detectees": 1, "manquees": 1, "fausses_alertes": 1}
