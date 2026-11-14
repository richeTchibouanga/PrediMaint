"""Données : chargement, variables dérivées, absence de fuite d'information, séparation reproductible."""
import math

import pytest
from conftest import machine

from src.donnees import ENTREES, MODES, ajouter_variables, charger, separer


def test_fichier_complet():
    df = charger()
    assert df.shape == (10_000, 14)
    assert int(df["panne"].sum()) == 339
    assert df.isna().sum().sum() == 0


def test_variables_derivees():
    d = ajouter_variables(machine(temp_air=300.0, temp_process=309.0, vitesse=1300, couple=62.0, usure_outil=205)).iloc[0]
    assert d["ecart_temp"] == pytest.approx(9.0)
    assert d["puissance"] == pytest.approx(62.0 * 1300 * 2 * math.pi / 60)
    assert d["contrainte"] == pytest.approx(205 * 62.0)
    assert d["gamme_code"] == 0


def test_gamme_inconnue_refusee():
    with pytest.raises(ValueError):
        ajouter_variables(machine(gamme="X"))


def test_aucune_fuite_d_information():
    """Les colonnes qui décrivent la panne ne doivent jamais servir d'entrée au modèle."""
    interdites = set(MODES) | {"RNF", "panne", "UDI", "id_produit"}
    assert not interdites & set(ENTREES)


def test_separation_reproductible_et_stratifiee():
    a = separer(charger())
    b = separer(charger())
    assert list(a[1].index) == list(b[1].index)          # même jeu de test à chaque fois
    assert len(a[1]) == 2000 and int(a[3].sum()) == 68   # 20 % des relevés, 68 pannes
