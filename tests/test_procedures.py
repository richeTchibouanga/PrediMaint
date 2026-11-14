"""Fiches de procédures et intervention guidée."""
from datetime import datetime

import pytest

from src.procedures import (DOSSIER, FICHE_PAR_TYPE, SECTIONS, charger_fiches, choisir_fiche, compte_rendu,
                            deroule, lire_fiche)


def test_toutes_les_fiches_sont_valides():
    fiches = charger_fiches()
    assert len(fiches) == 9
    for fiche in fiches.values():
        assert all(fiche.section(s) for s in SECTIONS), fiche.code
        assert fiche.meta.get("Durée estimée") and fiche.meta.get("Intervenant"), fiche.code


def test_chaque_type_de_panne_a_sa_fiche():
    fiches = charger_fiches()
    for mode, code in FICHE_PAR_TYPE.items():
        assert fiches[code].meta["Type de panne"] == mode


def test_la_consignation_vient_toujours_en_premier():
    for code in FICHE_PAR_TYPE.values():
        sequence = [f.code for f in deroule(code)]
        assert sequence == ["SEC-01", "SEC-02", code, "CTRL-01"]


def test_toute_intervention_rappelle_la_consignation():
    for code in FICHE_PAR_TYPE.values():
        assert any("SEC-01" in e for e in charger_fiches()[code].section("Sécurité")), code


@pytest.mark.parametrize("risque, type_, usure, attendu", [
    (0.96, "OSF", 205, "PROC-OSF"),     # alerte : fiche du type prédit
    (0.92, "HDF", 60, "PROC-HDF"),
    (0.12, None, 215, "PROC-TWF"),      # pas d'alerte mais zone d'usure : changement préventif
    (0.00, None, 100, None),            # machine normale : rien à faire
])
def test_choix_de_la_fiche(risque, type_, usure, attendu):
    assert choisir_fiche(risque, 0.26, type_, usure) == attendu


def test_fiche_mal_formee_refusee(tmp_path):
    f = tmp_path / "X-01.md"
    f.write_text("# X-01 — Fiche incomplète\n\n## Étapes\n1. Une étape\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sections manquantes"):
        lire_fiche(f)


def test_compte_rendu():
    mesures = dict(gamme="L", temp_air=300.0, temp_process=309.0, vitesse=1300, couple=62.0, usure_outil=205)
    diag = {"risque": 0.962, "niveau": "Alerte critique : intervenir rapidement", "type": "OSF"}
    faites = {f.code: [True] * len(f.etapes) for f in deroule("PROC-OSF")}
    faites["CTRL-01"][-1] = False
    texte = compte_rendu(mesures, diag, "PROC-OSF", faites, "J. Dupont", "Plaquette écaillée.",
                         date=datetime(2026, 11, 15, 9, 30))
    assert "15/11/2026 09:30" in texte and "J. Dupont" in texte and "Plaquette écaillée." in texte
    assert "Risque de panne : 96 %" in texte and "Surcharge" in texte
    total = sum(len(v) for v in faites.values())
    assert f"{total - 1} étapes réalisées sur {total}" in texte and "incomplète" in texte
    assert "- [x] Retirer l'outil de son porte-outil." in texte


def test_dossier_present():
    assert DOSSIER.is_dir()
