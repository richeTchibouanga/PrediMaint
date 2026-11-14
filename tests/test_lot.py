"""Analyse d'un lot : contrôle des fichiers et résultats sur les fichiers d'exemple du guide."""
import pandas as pd
import pytest
from conftest import EXEMPLES

from src.lot import analyser_lot, lire_csv, niveau


def analyser(nom, paquet):
    return analyser_lot(lire_csv(EXEMPLES / nom), paquet["modele"], paquet["modele_type"],
                        paquet["entrees"], paquet["seuil"])


@pytest.mark.parametrize("fichier, message", [
    ("erreur_colonne_manquante.csv", "Colonnes manquantes : couple"),
    ("erreur_gamme_inconnue.csv", "ne doit contenir que L, M ou H"),
    ("erreur_valeur_non_numerique.csv", "ne sont pas des nombres"),
])
def test_fichiers_errones_refuses(fichier, message):
    with pytest.raises(ValueError, match=message):
        lire_csv(EXEMPLES / fichier)


def test_lot_atelier(paquet):
    res = analyser("lot_atelier_10_machines.csv", paquet)
    assert len(res) == 10
    assert int((res["risque"] >= paquet["seuil"]).sum()) == 7
    assert res.iloc[0]["machine"] == "M02"                               # la plus risquée en tête
    m06 = res[res["machine"] == "M06"].iloc[0]
    assert m06["niveau"] == "Pas d'alerte" and "changer l'outil" in m06["action"]   # règle des 200 min


def test_format_d_origine_toutes_les_pannes_detectees(paquet):
    res = analyser("lot_format_origine_ai4i.csv", paquet)
    alerte = res["risque"] >= paquet["seuil"]
    assert (alerte == (res["panne"] == 1)).all()                         # 6 pannes, 6 alertes, 0 fausse alerte


def test_niveaux():
    assert niveau(0.10, 0.26) == "Pas d'alerte"
    assert niveau(0.30, 0.26) == "Alerte : intervention à planifier"
    assert niveau(0.70, 0.26) == "Alerte critique : intervenir rapidement"


def test_fichier_excel_francais_accepte(paquet):
    """Point-virgule et virgule décimale (« 300,5 »), comme un CSV enregistré par Excel en français."""
    df = lire_csv(EXEMPLES / "lot_excel_francais.csv")
    assert df.loc[0, "temp_air"] == pytest.approx(300.5) and df.loc[0, "couple"] == pytest.approx(40.0)
    res = analyser_lot(df, paquet["modele"], paquet["modele_type"], paquet["entrees"], paquet["seuil"])
    assert res.iloc[0]["machine"] == "M02" and res.iloc[0]["panne_probable"] == "Surcharge"


def test_export_reimportable(paquet, tmp_path):
    """Les résultats exportés au format Excel français peuvent être réimportés tels quels."""
    res = analyser("lot_atelier_10_machines.csv", paquet)
    f = tmp_path / "resultats.csv"
    f.write_bytes(res.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"))
    relu = lire_csv(f)
    assert len(relu) == 10 and relu["couple"].dtype.kind == "f"


def test_mesures_hors_plage_signalees(paquet):
    """Une température saisie en °C au lieu de K ne doit pas donner un faux « Pas d'alerte »."""
    res = analyser("erreur_temperature_celsius.csv", paquet)
    m04 = res.iloc[0]                                                    # placé en tête de liste
    assert m04["machine"] == "M04" and m04["niveau"] == "Mesures à vérifier"
    assert "temp_air = 26 K" in m04["action"] and pd.isna(m04["risque"])
    assert int((res["niveau"] == "Mesures à vérifier").sum()) == 1
