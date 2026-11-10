# Évaluation NLU — méthode `regles`, jeu `test` (échantillon stratifié de 30)

## Provenance

| Élément | Valeur |
|---|---|
| Commit Git | `dcfea44` |
| Modifications non commitées | oui (38 fichiers modifiés ou non suivis) |
| Variante | — |
| LLM | aucun (règles seules) |
| Demandes évaluées | 30 |
| Date | 2026-11-10 00:25 |
| Replis sur les règles | 0 |
| Appels LLM réels (hors cache) | 0 |

> Généré le 2026-11-10 par `services/ai/scripts/evaluer_nlu.py`. 30 demandes relues (`valide` ou `corrige`). Aucun LLM. Coût : **0 DT** (aucun appel payant).

## Scores

| Score | Valeur |
|---|---|
| **F1 macro** (champs de support ≥ 5, critère « fini » ≥ 0,85) | **0.843** |
| F1 micro global (28 champs) | 0.897 |
| **F1 transport macro** (8 champs, support ≥ 5) | **0.786** |
| F1 transport micro | 0.795 |
| IC 95 % du F1 macro (bootstrap, 1000 tirages, graine 20261109) | [0.781 ; 0.894] |
| IC 95 % du F1 transport macro (idem) | [0.617 ; 0.927] |
| Latence moyenne | 0.0 s |
| Méthode effective | regles 30 |
| Replis sur les règles (LLM en panne, trop lent ou JSON invalide) | 0 |
| Coût | 0 DT |

Champs hors moyenne macro (support < 5) : `date_debut` (4), `budget_illimite` (1), `nb_enfants` (4), `niveau_marche_max` (3), `mobilite_reduite` (1), `vol_direct` (1), `boite_auto` (2), `priorite` (1), `hors_sujet` (0).

## Par champ

| Champ | Support | Précision | Rappel | F1 | Exactitude | Macro |
|---|---|---|---|---|---|---|
| `destination` | 30 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `autres_villes` | 7 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `date_debut` | 4 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `duree_jours` | 29 | 1.000 | 0.897 | 0.945 | 0.900 | oui |
| `nb_nuits` | 26 | 1.000 | 0.923 | 0.960 | 0.933 | oui |
| `budget_montant` | 26 | 0.960 | 0.923 | 0.941 | 0.933 | oui |
| `budget_devise` | 26 | 1.000 | 0.962 | 0.980 | 0.967 | oui |
| `budget_base` | 26 | 0.960 | 0.923 | 0.941 | 0.933 | oui |
| `budget_illimite` | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `nb_voyageurs` | 29 | 1.000 | 0.793 | 0.885 | 0.800 | oui |
| `nb_adultes` | 26 | 0.909 | 0.769 | 0.833 | 0.733 | oui |
| `nb_enfants` | 4 | 1.000 | 0.750 | 0.857 | 0.967 | non |
| `type_voyage` | 26 | 1.000 | 0.846 | 0.917 | 0.867 | oui |
| `preferences` | 12 | 1.000 | 0.833 | 0.909 | 0.933 | oui |
| `activites_souhaitees` | 9 | 1.000 | 0.111 | 0.200 | 0.800 | oui |
| `niveau_marche_max` | 3 | 1.000 | 0.333 | 0.500 | 0.933 | non |
| `mobilite_reduite` | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `langue` | 30 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `ville_depart` (transport) | 8 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `vol` (transport) | 9 | 0.875 | 0.778 | 0.824 | 0.933 | oui |
| `voiture` (transport) | 11 | 0.875 | 0.636 | 0.737 | 0.867 | oui |
| `transfert` (transport) | 6 | 1.000 | 0.333 | 0.500 | 0.867 | oui |
| `vol_direct` (transport) | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `boite_auto` (transport) | 2 | — | 0.000 | 0.000 | 0.933 | non |
| `priorite` (transport) | 1 | — | 0.000 | 0.000 | 0.967 | non |
| `budget_inclut_transport` (transport) | 13 | 1.000 | 0.769 | 0.870 | 0.900 | oui |
| `hors_sujet` | 0 | — | — | — | 1.000 | non |
| `champs_manquants` | 8 | 0.400 | 1.000 | 0.571 | 0.700 | oui |

## Par langue et par source

| Groupe | n | F1 macro | F1 micro | F1 transport macro |
|---|---|---|---|---|
| langue = ar | 6 | 0.693 | 0.818 | 0.733 |
| langue = darija | 6 | 0.829 | 0.910 | 0.792 |
| langue = en | 3 | 0.831 | 0.886 | 0.600 |
| langue = fr | 15 | 0.898 | 0.925 | 0.913 |
| source = genere | 9 | 0.774 | 0.899 | 0.633 |
| source = humain | 21 | 0.858 | 0.897 | 0.838 |

(F1 macro d'un groupe : mêmes champs que la moyenne globale.)

## Matrices d'erreurs

**`type_voyage`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | amis | couple | famille | groupe | solo | None |
|---|---|---|---|---|---|---|
| amis | 6 | · | · | · | · | 1 |
| couple | · | 5 | · | · | · | · |
| famille | · | · | 6 | · | · | 3 |
| groupe | · | · | · | 1 | · | · |
| solo | · | · | · | · | 4 | · |
| None | · | · | · | · | · | 4 |

**`besoins_transport.vol`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 21 | · | · |
| non | 1 | 3 | 1 |
| oui | · | · | 4 |

**`besoins_transport.voiture`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 19 | · | · |
| non | 1 | 3 | 1 |
| oui | 2 | · | 4 |

**`besoins_transport.transfert`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | oui |
|---|---|---|
| indifferent | 24 | · |
| oui | 4 | 2 |

