# Cahier des charges — Maintenance prédictive d'un atelier d'usinage

| | |
|---|---|
| **Projet** | PrédiMaint — maintenance prédictive d'un atelier d'usinage |
| **Auteur** | Jean de Dieu Riche TCHIBOUANGA |
| **Version** | 1.0 — novembre 2026 |
| **Statut** | À valider avant le démarrage du développement |

---

## 1. Contexte

L'usine étudiée fabrique des pièces mécaniques par usinage. Son atelier compte un parc de machines-outils qui produisent trois gammes de pièces : qualité basse (L), moyenne (M) et haute (H).

Aujourd'hui, la maintenance y est **corrective**, puisqu'on répare après la panne, ou **préventive systématique**, avec un changement d'outil à intervalles fixes. Ces deux approches coûtent cher :

- une panne imprévue arrête la production, abîme parfois la pièce en cours et mobilise l'équipe de maintenance en urgence ;
- un remplacement systématique jette des outils encore utilisables.

Les machines sont déjà équipées de capteurs : températures, vitesse de rotation, couple et temps d'usure de l'outil. L'usine souhaite exploiter ces données pour **anticiper les pannes** et intervenir au bon moment. C'est le principe de la **maintenance prédictive**.

## 2. Problématique

> Comment exploiter les données des capteurs des machines-outils pour prédire une panne avant qu'elle ne survienne, en identifier la cause probable, et chiffrer le gain économique pour l'usine ?

## 3. Objectifs

### 3.1 Objectif général

Concevoir un outil d'aide à la décision qui, à partir des mesures d'une machine, estime le **risque de panne**, indique le **type de panne probable** et recommande une **action de maintenance**. L'outil chiffre aussi les **coûts évités**.

### 3.2 Objectifs spécifiques

1. Analyser les données des capteurs et comprendre les conditions qui mènent à chaque type de panne.
2. Entraîner et comparer plusieurs modèles de machine learning pour prédire :

    - la panne (oui ou non) ;
    - le type de panne.

3. Rendre les prédictions **explicables**, c'est-à-dire montrer quels capteurs influencent la décision.
4. Traduire les performances du modèle en **impact économique** : pannes évitées, fausses alertes, coût net.
5. Mettre ces résultats à disposition dans une **application web** simple, utilisable par un technicien ou un responsable de maintenance.
6. Publier le projet (code, application et documentation) dans le portfolio.

## 4. Périmètre

| Inclus | Exclus (évolutions possibles, voir § 13) |
|---|---|
| Données historiques des capteurs (fichier fourni) | Connexion en temps réel aux machines |
| Prédiction de la panne et de son type | Pilotage automatique des machines |
| Explication des prédictions | Gestion des stocks de pièces de rechange |
| Calcul économique paramétrable | Planification complète de la GMAO |
| Application web de démonstration | Authentification des utilisateurs |
| Documentation et publication | Assistant conversationnel (prévu en phase 2) |

## 5. Données

### 5.1 Source

**AI4I 2020 Predictive Maintenance Dataset**, publié sur l'UCI Machine Learning Repository.

- Introduit par S. Matzka (2020), *Explainable Artificial Intelligence for Predictive Maintenance Applications*.
- DOI : 10.24432/C5HS5C.
- Licence **CC BY 4.0** : utilisation libre, avec obligation de citer la source.
- Il s'agit d'un **jeu de données synthétique** qui reproduit des données réelles de maintenance industrielle.

### 5.2 Contenu

10 000 relevés, sans valeur manquante.

| Variable | Unité | Rôle |
|---|---|---|
| UDI, Product ID | — | Identifiants (non utilisés pour prédire) |
| Type | L / M / H | Gamme de qualité du produit (50 % / 30 % / 20 %) |
| Air temperature | K | Capteur |
| Process temperature | K | Capteur |
| Rotational speed | tr/min | Capteur |
| Torque | N·m | Capteur |
| Tool wear | min | Temps d'utilisation de l'outil |
| Machine failure | 0 / 1 | **Cible principale** : panne ou non |
| TWF, HDF, PWF, OSF, RNF | 0 / 1 | **Cible secondaire** : type de panne |

### 5.3 Les cinq types de panne

| Code | Panne | Cause, d'après la documentation du jeu de données | Nombre dans le fichier |
|---|---|---|---|
| TWF | Usure de l'outil | Outil remplacé ou cassé entre 200 et 240 min d'usure | 46 |
| HDF | Mauvaise dissipation de chaleur | Écart entre la température de l'air et celle du procédé inférieur à 8,6 K **et** vitesse inférieure à 1 380 tr/min | 115 |
| PWF | Puissance | Puissance (couple × vitesse) inférieure à 3 500 W ou supérieure à 9 000 W | 95 |
| OSF | Surcharge | Usure × couple supérieur à 11 000 min·N·m (L), 12 000 (M) ou 13 000 (H) | 98 |
| RNF | Aléatoire | Probabilité de 0,1 %, indépendante des mesures | 19 |

Une même ligne peut cumuler plusieurs types de panne (24 cas). Au total, le fichier compte **339 pannes, soit 3,39 %** des relevés.

La documentation annonce 120 pannes d'usure et 5 pannes aléatoires, car elle compte aussi les changements d'outil sans panne. Le fichier contient 46 et 19 de ces pannes : on se fie au fichier. Il comporte aussi deux incohérences, traitées à l'étape 2 :

- 9 pannes n'ont aucun type indiqué ;
- 18 pannes aléatoires ne sont pas comptées comme pannes.

### 5.4 Points d'attention

- **Données déséquilibrées** : 96,6 % des relevés sont sans panne. Un modèle qui répondrait toujours « pas de panne » aurait 96,6 % de bonnes réponses tout en étant inutile. La performance sera donc mesurée sur la **détection des pannes** (§ 7.3).
- **Fuite d'information** : les colonnes TWF à RNF décrivent la panne elle-même. Elles ne doivent **jamais** servir d'entrée au modèle, seulement de cible.
- **Données synthétiques** : les résultats démontrent la méthode. Sur une vraie usine, le modèle devrait être réentraîné sur ses propres données.

## 6. Utilisateurs visés

| Utilisateur | Besoin |
|---|---|
| Technicien de maintenance | Savoir si une machine est à risque et quoi vérifier |
| Responsable de maintenance | Vue d'ensemble du parc, priorisation des interventions |
| Directeur d'usine | Gain économique de la maintenance prédictive |
| Recruteur / jury (portfolio) | Comprendre le projet en 2 minutes |

## 7. Besoins fonctionnels

### 7.1 Analyse des données

| N° | Fonction |
|---|---|
| F1 | Présenter la répartition des pannes, globale et par type |
| F2 | Montrer l'influence de chaque capteur sur les pannes (graphiques) |
| F3 | Vérifier les règles de panne documentées (§ 5.3) sur les données |

### 7.2 Modèle de prédiction

| N° | Fonction |
|---|---|
| F4 | Prédire la panne (oui ou non) avec une **probabilité de risque** |
| F5 | Prédire le **type de panne** le plus probable |
| F6 | Créer des variables utiles à partir des capteurs : puissance, écart de température, usure × couple |
| F7 | Comparer au moins trois modèles : régression logistique, forêt aléatoire, gradient boosting |
| F8 | Expliquer chaque prédiction en indiquant les capteurs qui ont le plus pesé |

### 7.3 Critères de performance du modèle

| Indicateur | Signification | Cible |
|---|---|---|
| **Rappel** sur les pannes | Part des vraies pannes détectées | ≥ 85 % |
| **Précision** sur les pannes | Part des alertes justifiées | ≥ 70 % |
| F1-score | Équilibre entre rappel et précision | ≥ 0,75 |
| PR-AUC | Qualité globale sur données déséquilibrées | À maximiser |

Le rappel est prioritaire : une panne non détectée coûte plus cher qu'une fausse alerte. Ces cibles pourront être ajustées après l'exploration, avec justification.

### 7.4 Calcul économique

| N° | Fonction |
|---|---|
| F9 | Paramétrer les coûts : panne imprévue (arrêt et réparation), intervention préventive, fausse alerte |
| F10 | Comparer le coût annuel **sans** prédiction (maintenance corrective) et **avec** le modèle |
| F11 | Afficher le gain net, le nombre de pannes évitées et le retour sur investissement |
| F12 | Ajuster le **seuil d'alerte** du modèle et voir son effet sur les coûts |

Les valeurs de coût par défaut seront fixées à l'étape 4 et présentées comme des hypothèses modifiables.

### 7.5 Application web (tableau de bord de l'atelier)

| N° | Fonction |
|---|---|
| F13 | **Diagnostic d'une machine** : saisir les mesures pour obtenir le risque, le type de panne probable, l'explication et l'action recommandée |
| F14 | **Analyse d'un lot** : importer un fichier CSV de relevés pour obtenir la liste des machines classées par niveau de risque |
| F15 | **Simulation** : faire varier un paramètre (par exemple l'usure de l'outil) et voir l'évolution du risque |
| F16 | **Page économique** : coûts, gains et réglage du seuil (F9 à F12) |
| F17 | **Page « À propos »** : présentation du projet, des données et de leurs limites |

Correspondance entre le type de panne et l'action recommandée (F13) :

| Type de panne | Action recommandée |
|---|---|
| Usure de l'outil (TWF) | Planifier le changement d'outil |
| Dissipation de chaleur (HDF) | Vérifier le refroidissement et la ventilation, augmenter la vitesse si possible |
| Puissance (PWF) | Contrôler les paramètres de coupe et l'alimentation du moteur |
| Surcharge (OSF) | Réduire la charge et changer l'outil usé |
| Aléatoire (RNF) | Inspection générale ; non prévisible par les capteurs |

## 8. Exigences techniques

| Domaine | Exigence |
|---|---|
| Langage | Python 3.15 |
| Bibliothèques | pandas, NumPy, scikit-learn, Matplotlib, Streamlit, joblib |
| Reproductibilité | Graine aléatoire fixée, versions figées dans `requirements.txt`, séparation entraînement / test stratifiée (80 % / 20 %), validation croisée |
| Qualité du code | Code organisé en modules, fonctions documentées, tests automatiques des fonctions principales |
| Performance | Réponse de l'application en moins de 2 secondes pour une machine |
| Hébergement | Code sur GitHub (dépôt public), application en ligne sur Streamlit Community Cloud (gratuit) |
| Langue | Interface et documentation en français |
| Licence des données | Citer AI4I 2020 (CC BY 4.0) dans le README et dans l'application |

### Organisation prévue du dépôt

```
maintenance-predictive/
├── data/raw/            données d'origine (non modifiées)
├── docs/                cahier des charges, notes
├── notebooks/           exploration des données
├── src/                 préparation des données, entraînement, économie
├── models/              modèle entraîné
├── app/                 application Streamlit
├── tests/               tests automatiques
├── requirements.txt
└── README.md
```

## 9. Livrables

| N° | Livrable |
|---|---|
| L1 | Ce cahier des charges |
| L2 | Notebook d'exploration des données, commenté |
| L3 | Code d'entraînement et modèle sauvegardé, avec le rapport de performances |
| L4 | Étude économique paramétrable |
| L5 | Application Streamlit en ligne |
| L6 | Dépôt GitHub avec un README clair (objectif, résultats, captures, mode d'emploi) |
| L7 | Fiche projet dans le portfolio et publication LinkedIn |

## 10. Planning prévisionnel

| Étape | Contenu | Durée estimée |
|---|---|---|
| 1 | Mise en place : dossier, environnement, données | ½ jour |
| 2 | Exploration des données (L2) | 1 à 2 jours |
| 3 | Modèles, comparaison, explicabilité (L3) | 2 à 3 jours |
| 4 | Étude économique (L4) | 1 jour |
| 5 | Application Streamlit (L5) | 2 à 3 jours |
| 6 | Tests, README, mise en ligne, portfolio, LinkedIn (L6, L7) | 1 à 2 jours |
| | **Total** | **environ 2 semaines** à temps partiel |

## 11. Contraintes et risques

| Risque | Conséquence | Mesure prévue |
|---|---|---|
| Données déséquilibrées | Modèle qui ignore les pannes | Métriques adaptées, pondération des classes, réglage du seuil |
| Fuite d'information | Résultats faussement excellents | Exclure TWF à RNF et les identifiants des entrées |
| Données synthétiques | Performances meilleures que sur une vraie usine | Le dire clairement (README, application) |
| Pannes aléatoires (RNF) | Impossibles à prédire | Les signaler comme limite, sans chercher à les « apprendre » |
| Python 3.15 très récent | Incompatibilité d'une bibliothèque | Versions vérifiées à l'installation, solution de repli en Python 3.12 |
| Coûts économiques estimés | Gain chiffré discutable | Hypothèses visibles et modifiables dans l'application |

## 12. Critères de réception

Le projet sera considéré comme terminé lorsque :

- [ ] le modèle atteint les cibles du § 7.3 sur le jeu de test, ou un écart est justifié ;
- [ ] aucune colonne de panne (TWF à RNF) n'est utilisée en entrée du modèle ;
- [ ] l'application répond aux fonctions F13 à F17 et fonctionne en ligne ;
- [ ] les tests automatiques passent ;
- [ ] le README permet à quelqu'un d'installer et de lancer le projet en moins de 10 minutes ;
- [ ] la source des données et sa licence sont citées ;
- [ ] le projet figure dans le portfolio et sur LinkedIn.

## 13. Évolutions possibles (phase 2)

- **Assistant IA de maintenance** : à partir de la panne prédite, un assistant (LLM avec RAG sur des procédures de maintenance) explique au technicien les étapes d'intervention.
- **Données temporelles** : suivre chaque machine dans le temps pour estimer sa durée de vie restante (RUL).
- **Alertes** : notification automatique (e-mail ou messagerie) quand le risque dépasse le seuil.
- **Données réelles** : adapter le modèle aux données d'une usine partenaire.
