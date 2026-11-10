# Évaluation NLU — méthode `regles`, jeu `dev`

## Provenance

| Élément | Valeur |
|---|---|
| Commit Git | `dcfea44` |
| Modifications non commitées | oui (32 fichiers modifiés ou non suivis) |
| Variante | — |
| LLM | aucun (règles seules) |
| Demandes évaluées | 77 |
| Date | 2026-11-09 23:10 |
| Replis sur les règles | 0 |
| Appels LLM réels (hors cache) | 0 |

> Généré le 2026-11-09 par `services/ai/scripts/evaluer_nlu.py`. 77 demandes relues (`valide` ou `corrige`). Aucun LLM. Coût : **0 DT** (aucun appel payant).

## Scores

| Score | Valeur |
|---|---|
| **F1 macro** (champs de support ≥ 5, critère « fini » ≥ 0,85) | **0.997** |
| F1 micro global (28 champs) | 0.996 |
| **F1 transport macro** (8 champs, support ≥ 5) | **1.000** |
| F1 transport micro | 1.000 |
| IC 95 % du F1 macro (bootstrap, 1000 tirages, graine 20261109) | [0.993 ; 1.000] |
| IC 95 % du F1 transport macro (idem) | [1.000 ; 1.000] |
| Latence moyenne | 0.0 s |
| Méthode effective | regles 77 |
| Replis sur les règles (LLM en panne, trop lent ou JSON invalide) | 0 |
| Coût | 0 DT |

Champs hors moyenne macro (support < 5) : `budget_illimite` (0), `mobilite_reduite` (3), `boite_auto` (4), `priorite` (2), `hors_sujet` (2).

## Par champ

| Champ | Support | Précision | Rappel | F1 | Exactitude | Macro |
|---|---|---|---|---|---|---|
| `destination` | 74 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `autres_villes` | 11 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `date_debut` | 7 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `duree_jours` | 71 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `nb_nuits` | 66 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_montant` | 68 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_devise` | 68 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_base` | 68 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_illimite` | 0 | — | — | — | 1.000 | non |
| `nb_voyageurs` | 69 | 1.000 | 0.986 | 0.993 | 0.987 | oui |
| `nb_adultes` | 60 | 1.000 | 0.983 | 0.992 | 0.987 | oui |
| `nb_enfants` | 10 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `type_voyage` | 63 | 1.000 | 0.984 | 0.992 | 0.987 | oui |
| `preferences` | 52 | 0.981 | 1.000 | 0.990 | 0.987 | oui |
| `activites_souhaitees` | 63 | 0.984 | 0.984 | 0.984 | 0.987 | oui |
| `niveau_marche_max` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `mobilite_reduite` | 3 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `langue` | 77 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `ville_depart` (transport) | 22 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `vol` (transport) | 26 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `voiture` (transport) | 20 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `transfert` (transport) | 12 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `vol_direct` (transport) | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `boite_auto` (transport) | 4 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `priorite` (transport) | 2 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `budget_inclut_transport` (transport) | 36 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `hors_sujet` | 2 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `champs_manquants` | 31 | 0.969 | 1.000 | 0.984 | 0.987 | oui |

## Par langue et par source

| Groupe | n | F1 macro | F1 micro | F1 transport macro |
|---|---|---|---|---|
| langue = ar | 16 | 0.991 | 0.990 | 1.000 |
| langue = darija | 14 | 1.000 | 1.000 | 1.000 |
| langue = en | 7 | 1.000 | 1.000 | 1.000 |
| langue = fr | 40 | 0.998 | 0.997 | 1.000 |
| source = genere | 25 | 1.000 | 1.000 | 1.000 |
| source = humain | 52 | 0.996 | 0.995 | 1.000 |

(F1 macro d'un groupe : mêmes champs que la moyenne globale.)

## Matrices d'erreurs

**`type_voyage`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | amis | couple | famille | groupe | solo | None |
|---|---|---|---|---|---|---|
| amis | 13 | · | · | · | · | · |
| couple | · | 19 | · | · | · | · |
| famille | · | · | 22 | · | · | · |
| groupe | · | · | · | 3 | · | · |
| solo | · | · | · | · | 5 | 1 |
| None | · | · | · | · | · | 14 |

**`besoins_transport.vol`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 51 | · | · |
| non | · | 9 | · |
| oui | · | · | 17 |

**`besoins_transport.voiture`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 57 | · | · |
| non | · | 9 | · |
| oui | · | · | 11 |

**`besoins_transport.transfert`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | oui |
|---|---|---|
| indifferent | 65 | · |
| oui | · | 12 |

