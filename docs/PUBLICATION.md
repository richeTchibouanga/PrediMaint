# PrédiMaint — Étape 6 : tests, publication et bilan du projet

*Livrables L6 et L7 du cahier des charges : tests automatiques, dépôt GitHub, application en ligne, portfolio et LinkedIn.*

## 1. Tests automatiques

Le projet compte **24 tests automatiques** (pytest). Ils s'exécutent en quelques secondes :

```
.venv\Scripts\python -m pytest tests
```

| Fichier | Ce qui est vérifié | Tests |
|---|---|---|
| `test_donnees.py` | Fichier complet (10 000 relevés, 339 pannes), calcul des variables dérivées, refus d'une gamme inconnue, **absence de fuite d'information**, séparation entraînement / test reproductible | 5 |
| `test_modele.py` | **Cibles du cahier des charges** (rappel ≥ 85 %, précision ≥ 70 %), cohérence des métadonnées, scénarios du guide (machine normale, surcharge, chaleur, puissance), frontière de la panne de chaleur, explication des causes, bilan économique | 10 |
| `test_economie.py` | Coût d'une panne, bilan économique sur un exemple calculable à la main, courbe des seuils | 3 |
| `test_lot.py` | Refus des 3 fichiers erronés avec le bon message, analyse du lot atelier, détection des 6 vraies pannes du fichier au format d'origine, niveaux d'alerte | 6 |

**Résultat : 24 tests réussis sur 24.**

En complément, l'application a été testée **dans un navigateur**, automatiquement, en local puis en ligne. Le test ouvre les 5 pages, applique l'exemple « surcharge » et vérifie qu'aucune erreur ne s'affiche. Il a permis de corriger 3 défauts avant la publication :

- un plantage du graphique d'explication ;
- des couleurs inversées dans le graphique de coûts ;
- des noms de mesures masqués.

## 2. Publication

| Élément | Adresse |
|---|---|
| **Application en ligne** | https://predimaint.streamlit.app |
| **Code et documentation** | https://github.com/richeTchibouanga/PrediMaint |
| **Portfolio** | https://riche-tchibouanga.vercel.app (section Projets) |

**Dépôt GitHub (public)**

- 56 fichiers : code, modèle entraîné, données, notebook, tests, documentation et PDF de chaque étape.
- Un README présente le problème, les résultats, les pages de l'application, la démarche, l'installation, les limites et la source des données.

**Application en ligne (Streamlit Community Cloud, gratuit)**

- Déploiement directement depuis le dépôt GitHub, en Python 3.13, avec les versions de bibliothèques figées dans `requirements.txt`. Cela garantit que le modèle donne en ligne les mêmes résultats qu'en local.
- Vérification après la mise en ligne : les 5 pages fonctionnent, et les chiffres sont identiques au local (96 % pour l'exemple « surcharge », 510 000 € de gain annuel).
- Chaque modification envoyée sur GitHub met l'application à jour automatiquement.

**Portfolio**

- Nouvelle carte projet, avec une capture, 4 points forts et les boutons « Essayer l'appli » et « Code source ».
- Nouvelles compétences : pandas, scikit-learn, machine learning, Streamlit, pytest.
- Statistique de l'accueil : « 2 projets en ligne ».

**LinkedIn**

- Une publication d'annonce et le texte de la section Projets du profil, préparés et prêts à publier.

## 3. Critères de réception du cahier des charges

| Critère (§ 12 du cahier des charges) | Statut |
|---|---|
| Le modèle atteint les cibles de performance sur le jeu de test | ✅ Rappel 85,3 %, précision 76,3 %, F1 0,806 |
| Aucune colonne de panne (TWF à RNF) n'est utilisée en entrée du modèle | ✅ Vérifié par un test automatique |
| L'application répond aux fonctions F13 à F17 et fonctionne en ligne | ✅ 5 pages, testées en ligne |
| Les tests automatiques passent | ✅ 24 sur 24 |
| Le README permet d'installer et de lancer le projet en moins de 10 minutes | ✅ 4 commandes d'installation, puis 1 pour lancer |
| La source des données et sa licence sont citées | ✅ README, application (À propos) et rapports |
| Le projet figure dans le portfolio et sur LinkedIn | ✅ Portfolio en ligne ; LinkedIn prêt à publier |

## 4. Livrables du projet

| N° | Livrable | Fichier |
|---|---|---|
| L1 | Cahier des charges | `Etape 1 - Cahier des charges - PrediMaint.pdf` |
| L2 | Exploration des données | `Etape 2 - Exploration des donnees - PrediMaint.pdf` et notebook |
| L3 | Modèle et rapport de performances | `Etape 3 - Resultats du modele - PrediMaint.pdf` (et version Word) |
| L4 | Étude économique | `Etape 4 - Etude economique - PrediMaint.pdf` |
| L5 | Application | `Manuel d'utilisation - PrediMaint.pdf` et application en ligne |
| L6 | Dépôt GitHub documenté | README et ce document |
| L7 | Portfolio et LinkedIn | Carte projet en ligne, textes LinkedIn |
| — | Guide de démonstration et de test | `Guide de demonstration et de test - PrediMaint.pdf` |

## 5. Bilan

**Objectifs atteints**

- Les pannes sont prédites avec un rappel de 85,3 % et une précision de 76,3 %.
- Le type de panne est identifié dans 93,9 % des cas.
- Chaque prédiction est expliquée et associée à une action de maintenance.
- Le gain économique est chiffré : environ 510 000 € par an, soit −73 %, avec des hypothèses modifiables.

**Ce qui a fait la différence**

- **Les variables issues du métier** : puissance, écart de température et contrainte de l'outil. Elles font passer la PR-AUC de 0,76 à 0,89.
- **Une évaluation honnête** : un jeu de test mis de côté dès le départ, un seuil choisi sans regarder le test, et des limites clairement annoncées.
- **La combinaison du prédictif et du préventif** pour les casses d'outil, que les capteurs ne permettent pas d'anticiper.

**Limites**

- Les données sont synthétiques, donc les performances sont optimistes.
- Le modèle se trompe parfois près des frontières de panne.
- Les coûts sont des hypothèses.

**Suites possibles (phase 2)**

- Un assistant IA qui guide le technicien selon la panne prédite.
- Le suivi de chaque outil dans le temps, pour estimer sa durée de vie restante.
- Des alertes automatiques.
- Une adaptation aux données d'une usine réelle.
