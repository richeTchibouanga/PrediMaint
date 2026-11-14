"""Fiches de procédures de maintenance et intervention guidée (phase 2, option sans modèle de langage).

Les fiches sont des fichiers Markdown dans data/procedures/, lisibles par un humain et par le programme :
    # CODE — Titre
    Clé : valeur            (métadonnées : Catégorie, Type de panne, Durée estimée, Intervenant)
    ## Section              (Quand l'utiliser, Sécurité, Outillage et pièces, Étapes, Vérification)
    - élément  ou  1. étape

Ce sont des procédures TYPES rédigées pour le projet, à remplacer par les procédures de l'usine.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from .donnees import NOMS_MODES, RACINE

DOSSIER = RACINE / "data" / "procedures"
SECTIONS = ["Quand l'utiliser", "Sécurité", "Outillage et pièces", "Étapes", "Vérification"]
FICHE_PAR_TYPE = {"OSF": "PROC-OSF", "HDF": "PROC-HDF", "PWF": "PROC-PWF", "TWF": "PROC-TWF", "RNF": "PROC-RNF"}
SEQUENCE_SECURITE = ["SEC-01", "SEC-02"]
FICHE_CONTROLE = "CTRL-01"


@dataclass
class Fiche:
    code: str
    titre: str
    meta: dict = field(default_factory=dict)
    sections: dict = field(default_factory=dict)

    def section(self, nom: str) -> list[str]:
        return self.sections.get(nom, [])

    @property
    def etapes(self) -> list[str]:
        return self.section("Étapes")


def lire_fiche(chemin: Path) -> Fiche:
    """Lit une fiche Markdown et vérifie sa structure."""
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    m = re.match(r"^#\s+(\S+)\s+—\s+(.+)$", lignes[0].strip())
    if not m:
        raise ValueError(f"{chemin.name} : la première ligne doit être « # CODE — Titre ».")
    fiche = Fiche(code=m.group(1), titre=m.group(2).strip())
    courante = None
    for ligne in lignes[1:]:
        texte = ligne.strip()
        if not texte:
            continue
        if texte.startswith("## "):
            courante = texte[3:].strip()
            fiche.sections[courante] = []
        elif courante is None and " : " in texte:
            cle, valeur = texte.split(" : ", 1)
            fiche.meta[cle.strip()] = valeur.strip()
        elif courante is not None:
            element = re.sub(r"^(?:-|\d+\.)\s+", "", texte)
            fiche.sections[courante].append(element)
    manquantes = [s for s in SECTIONS if not fiche.sections.get(s)]
    if manquantes:
        raise ValueError(f"{chemin.name} : sections manquantes ou vides : {', '.join(manquantes)}")
    if fiche.code != chemin.stem:
        raise ValueError(f"{chemin.name} : le code de la fiche ({fiche.code}) doit correspondre au nom du fichier.")
    return fiche


@lru_cache(maxsize=1)
def charger_fiches() -> dict[str, Fiche]:
    """Toutes les fiches, indexées par leur code."""
    return {f.code: f for f in (lire_fiche(p) for p in sorted(DOSSIER.glob("*.md")))}


def choisir_fiche(risque: float, seuil: float, type_probable: str | None, usure_outil: float,
                  zone_usure: float = 200) -> str | None:
    """Code de la fiche d'intervention adaptée au diagnostic, ou None si aucune intervention n'est nécessaire.

    - Alerte du modèle : fiche du type de panne probable.
    - Pas d'alerte mais outil en zone d'usure : changement préventif de l'outil.
    """
    if risque >= seuil and type_probable in FICHE_PAR_TYPE:
        return FICHE_PAR_TYPE[type_probable]
    if usure_outil >= zone_usure:
        return FICHE_PAR_TYPE["TWF"]
    return None


def deroule(code_intervention: str) -> list[Fiche]:
    """Ordre de l'intervention : sécurité d'abord, puis la fiche d'intervention, puis la remise en service."""
    fiches = charger_fiches()
    return [fiches[c] for c in SEQUENCE_SECURITE + [code_intervention, FICHE_CONTROLE]]


def compte_rendu(mesures: dict, diagnostic: dict, code_intervention: str, faites: dict[str, list[bool]],
                 technicien: str = "", observations: str = "", date: datetime | None = None) -> str:
    """Compte rendu d'intervention en texte (Markdown), prêt à télécharger ou à archiver.

    `faites` : pour chaque code de fiche, la liste des étapes cochées (True) ou non (False).
    """
    date = date or datetime.now()
    fiches = charger_fiches()
    total = sum(len(v) for v in faites.values())
    cochees = sum(sum(v) for v in faites.values())
    lignes = [
        "# Compte rendu d'intervention — PrédiMaint",
        "",
        f"- **Date** : {date:%d/%m/%Y %H:%M}",
        f"- **Technicien** : {technicien or 'non renseigné'}",
        f"- **Fiche d'intervention** : {code_intervention} — {fiches[code_intervention].titre}",
        f"- **Avancement** : {cochees} étapes réalisées sur {total}"
        + (" ✅" if total and cochees == total else " ⚠️ intervention incomplète"),
        "",
        "## Machine",
        "",
        f"Gamme {mesures['gamme']} · température de l'air {mesures['temp_air']:g} K · température du procédé "
        f"{mesures['temp_process']:g} K · vitesse {mesures['vitesse']:g} tr/min · couple {mesures['couple']:g} N·m · "
        f"usure de l'outil {mesures['usure_outil']:g} min",
        "",
        "## Diagnostic avant intervention",
        "",
        f"- Risque de panne : {diagnostic['risque'] * 100:.0f} % ({diagnostic['niveau']})",
        f"- Panne probable : {NOMS_MODES.get(diagnostic.get('type') or '', 'aucune')}",
        "",
        "## Étapes",
    ]
    for code, etats in faites.items():
        fiche = fiches[code]
        lignes += ["", f"### {code} — {fiche.titre}", ""]
        lignes += [f"- [{'x' if ok else ' '}] {etape}" for etape, ok in zip(fiche.etapes, etats)]
    lignes += ["", "## Observations", "", observations.strip() or "Aucune.", "",
               "---", "*Procédures types PrédiMaint : à remplacer par les procédures de l'usine.*"]
    return "\n".join(lignes)
