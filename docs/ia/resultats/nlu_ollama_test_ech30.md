# Évaluation NLU — méthode `ollama`, jeu `test` (échantillon stratifié de 30)

## Provenance

| Élément | Valeur |
|---|---|
| Commit Git | `dcfea44` |
| Modifications non commitées | oui (34 fichiers modifiés ou non suivis) |
| Variante | — |
| LLM | Ollama `qwen2.5:3b` (digest `357c53fb659c`), serveur Ollama 0.40.6 · temperature 0.0 |
| Demandes évaluées | 30 |
| Date | 2026-11-10 00:24 |
| Replis sur les règles | 0 |
| Appels LLM réels (hors cache) | 30 |

> Généré le 2026-11-10 par `services/ai/scripts/evaluer_nlu.py`. 30 demandes relues (`valide` ou `corrige`). LLM : Ollama `qwen2.5:3b` (local). Coût : **0 DT** (aucun appel payant).

## Scores

| Score | Valeur |
|---|---|
| **F1 macro** (champs de support ≥ 5, critère « fini » ≥ 0,85) | **0.715** |
| F1 micro global (28 champs) | 0.743 |
| **F1 transport macro** (8 champs, support ≥ 5) | **0.617** |
| F1 transport micro | 0.614 |
| IC 95 % du F1 macro (bootstrap, 1000 tirages, graine 20261109) | [0.612 ; 0.780] |
| IC 95 % du F1 transport macro (idem) | [0.437 ; 0.749] |
| Latence moyenne | 77.8 s |
| Méthode effective | llm 30 |
| Replis sur les règles (LLM en panne, trop lent ou JSON invalide) | 0 |
| Coût | 0 DT |

Champs hors moyenne macro (support < 5) : `date_debut` (4), `budget_illimite` (1), `nb_enfants` (4), `niveau_marche_max` (3), `mobilite_reduite` (1), `vol_direct` (1), `boite_auto` (2), `priorite` (1), `hors_sujet` (0).

## Par champ

| Champ | Support | Précision | Rappel | F1 | Exactitude | Macro |
|---|---|---|---|---|---|---|
| `destination` | 30 | 0.913 | 0.700 | 0.792 | 0.700 | oui |
| `autres_villes` | 7 | 1.000 | 0.571 | 0.727 | 0.933 | oui |
| `date_debut` | 4 | — | 0.000 | 0.000 | 0.867 | non |
| `duree_jours` | 29 | 0.962 | 0.862 | 0.909 | 0.867 | oui |
| `nb_nuits` | 26 | 0.917 | 0.846 | 0.880 | 0.867 | oui |
| `budget_montant` | 26 | 0.917 | 0.846 | 0.880 | 0.867 | oui |
| `budget_devise` | 26 | 1.000 | 0.923 | 0.960 | 0.933 | oui |
| `budget_base` | 26 | 0.958 | 0.885 | 0.920 | 0.900 | oui |
| `budget_illimite` | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `nb_voyageurs` | 29 | 0.846 | 0.759 | 0.800 | 0.767 | oui |
| `nb_adultes` | 26 | 0.800 | 0.769 | 0.784 | 0.733 | oui |
| `nb_enfants` | 4 | 0.500 | 0.250 | 0.333 | 0.867 | non |
| `type_voyage` | 26 | 0.826 | 0.731 | 0.776 | 0.667 | oui |
| `preferences` | 12 | 1.000 | 0.333 | 0.500 | 0.800 | oui |
| `activites_souhaitees` | 9 | 0.500 | 0.556 | 0.526 | 0.867 | oui |
| `niveau_marche_max` | 3 | 0.333 | 0.333 | 0.333 | 0.900 | non |
| `mobilite_reduite` | 1 | 0.500 | 1.000 | 0.667 | 0.967 | non |
| `langue` | 30 | 0.700 | 0.700 | 0.700 | 0.700 | oui |
| `ville_depart` (transport) | 8 | 1.000 | 0.625 | 0.769 | 0.900 | oui |
| `vol` (transport) | 9 | 0.267 | 0.444 | 0.333 | 0.600 | oui |
| `voiture` (transport) | 11 | 0.538 | 0.636 | 0.583 | 0.733 | oui |
| `transfert` (transport) | 6 | 0.500 | 0.833 | 0.625 | 0.800 | oui |
| `vol_direct` (transport) | 1 | — | 0.000 | 0.000 | 0.967 | non |
| `boite_auto` (transport) | 2 | 1.000 | 0.500 | 0.667 | 0.967 | non |
| `priorite` (transport) | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `budget_inclut_transport` (transport) | 13 | 0.667 | 0.923 | 0.774 | 0.767 | oui |
| `hors_sujet` | 0 | 0.000 | — | 0.000 | 0.900 | non |
| `champs_manquants` | 8 | 0.212 | 0.875 | 0.341 | 0.500 | oui |

## Par langue et par source

| Groupe | n | F1 macro | F1 micro | F1 transport macro |
|---|---|---|---|---|
| langue = ar | 6 | 0.584 | 0.671 | 0.331 |
| langue = darija | 6 | 0.370 | 0.362 | 0.458 |
| langue = en | 3 | 0.875 | 0.864 | 0.900 |
| langue = fr | 15 | 0.829 | 0.865 | 0.715 |
| source = genere | 9 | 0.720 | 0.751 | 0.785 |
| source = humain | 21 | 0.700 | 0.740 | 0.563 |

(F1 macro d'un groupe : mêmes champs que la moyenne globale.)

## Matrices d'erreurs

**`type_voyage`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | amis | couple | famille | groupe | solo | None |
|---|---|---|---|---|---|---|
| amis | 5 | · | · | · | · | 2 |
| couple | · | 4 | · | · | · | 1 |
| famille | 1 | · | 5 | · | · | 3 |
| groupe | · | · | · | 1 | · | · |
| solo | · | · | · | · | 4 | · |
| None | 2 | · | · | 1 | · | 1 |

**`besoins_transport.vol`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 14 | · | 7 |
| non | 1 | · | 4 |
| oui | · | · | 4 |

**`besoins_transport.voiture`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 15 | 3 | 1 |
| non | 2 | 3 | · |
| oui | · | 2 | 4 |

**`besoins_transport.transfert`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | oui |
|---|---|---|
| indifferent | 19 | 5 |
| oui | 1 | 5 |

