"""Chargement des données AI4I 2020 et création des variables utilisées par les modèles.

Règle d'or (cahier des charges § 5.4) : les colonnes TWF à RNF décrivent la panne elle-même.
Elles servent uniquement de CIBLES, jamais d'entrées.
"""
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
FICHIER_DONNEES = RACINE / "data" / "raw" / "ai4i2020.csv"

RENOMMAGE = {
    "Product ID": "id_produit", "Type": "gamme",
    "Air temperature [K]": "temp_air", "Process temperature [K]": "temp_process",
    "Rotational speed [rpm]": "vitesse", "Torque [Nm]": "couple",
    "Tool wear [min]": "usure_outil", "Machine failure": "panne",
}

CAPTEURS = ["temp_air", "temp_process", "vitesse", "couple", "usure_outil"]
DERIVEES = ["ecart_temp", "puissance", "contrainte"]
GAMMES = {"L": 0, "M": 1, "H": 2}

# Entrées du modèle : la gamme (codée), les 5 capteurs, puis les 3 variables dérivées
ENTREES_BRUTES = ["gamme_code"] + CAPTEURS
ENTREES = ENTREES_BRUTES + DERIVEES

# Types de panne prévisibles à partir des capteurs (RNF est aléatoire par nature)
MODES = ["TWF", "HDF", "PWF", "OSF"]
NOMS_MODES = {
    "TWF": "Usure de l'outil", "HDF": "Dissipation de chaleur", "PWF": "Puissance",
    "OSF": "Surcharge", "RNF": "Aléatoire",
}

# Plages de valeurs observées dans les données (utilisées pour valider les saisies de l'application)
PLAGES = {
    "temp_air": (295.0, 305.0), "temp_process": (305.0, 314.0), "vitesse": (1100, 2900),
    "couple": (3.0, 80.0), "usure_outil": (0, 260),
}


def charger(chemin: Path = FICHIER_DONNEES) -> pd.DataFrame:
    """Lit le fichier CSV d'origine et renomme les colonnes en français."""
    return pd.read_csv(chemin).rename(columns=RENOMMAGE)


def ajouter_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute la gamme codée et les variables dérivées de la physique de l'usinage.

    - ecart_temp : température du procédé − température de l'air (K)   → dissipation de chaleur
    - puissance  : couple × vitesse angulaire (W)                       → panne de puissance
    - contrainte : usure de l'outil × couple (min·N·m)                  → surcharge
    """
    d = df.copy()
    d["gamme_code"] = d["gamme"].map(GAMMES)
    if d["gamme_code"].isna().any():
        raise ValueError("Gamme inconnue : les valeurs autorisées sont L, M et H.")
    d["ecart_temp"] = d["temp_process"] - d["temp_air"]
    d["puissance"] = d["couple"] * d["vitesse"] * 2 * np.pi / 60
    d["contrainte"] = d["usure_outil"] * d["couple"]
    return d


def preparer(df: pd.DataFrame):
    """Renvoie les entrées X, la cible « panne » et les cibles par type de panne."""
    d = ajouter_variables(df)
    return d[ENTREES], d["panne"].astype(int), d[MODES].astype(int)


GRAINE = 42


def separer(df: pd.DataFrame):
    """Séparation entraînement (80 %) / test (20 %), stratifiée sur la panne, toujours identique (graine fixe).

    Renvoie X_tr, X_te, y_tr, y_te, M_tr, M_te, d_tr, d_te (entrées, cible panne, cibles par type, lignes brutes).
    """
    from sklearn.model_selection import train_test_split
    X, y, Y_modes = preparer(df)
    return train_test_split(X, y, Y_modes, df, test_size=0.2, stratify=y, random_state=GRAINE)
