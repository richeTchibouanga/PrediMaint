"""Éléments partagés par les tests : chemin du projet et modèle entraîné (chargé une seule fois)."""
import sys
from pathlib import Path

import joblib
import pandas as pd
import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
EXEMPLES = RACINE / "data" / "exemples"


@pytest.fixture(scope="session")
def paquet():
    return joblib.load(RACINE / "models" / "predimaint.joblib")


def machine(gamme="L", temp_air=300.0, temp_process=310.0, vitesse=1500, couple=40.0, usure_outil=100):
    """Une machine décrite par ses 6 mesures (par défaut : une machine qui fonctionne normalement)."""
    return pd.DataFrame([dict(gamme=gamme, temp_air=temp_air, temp_process=temp_process,
                              vitesse=vitesse, couple=couple, usure_outil=usure_outil)])
