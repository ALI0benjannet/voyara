# Évaluation NLU — méthode `hybride`, jeu `test` (5 premières demandes)

## Provenance

| Élément | Valeur |
|---|---|
| Commit Git | `dcfea44` |
| Modifications non commitées | oui (30 fichiers modifiés ou non suivis) |
| Variante | v1 |
| LLM | Ollama `qwen2.5:3b` (digest `357c53fb659c`), serveur Ollama 0.40.6 · temperature 0.0 |
| Demandes évaluées | 5 |
| Date | 2026-11-09 22:47 |
| Replis sur les règles | 0 |
| Appels LLM réels (hors cache) | 0 |

## Conditions API

Simulation depuis le cache (aucun nouvel appel) : chaque demande dont l'appel Ollama a dépassé `NLU_DELAI_LLM_S` = 25 s reçoit la sortie des règles seules, comme la route. Le résultat officiel reste le F1 sans limite de temps ci-dessous ; celui-ci est une donnée pour l'étape 9.

| Conditions API | Valeur |
|---|---|
| Demandes au-delà de 25 s (repli sur les règles) | 1 / 5 (20.0%) |
| F1 macro en conditions API | 0.960 |
| F1 transport macro en conditions API | — |

> Généré le 2026-11-09 par `services/ai/scripts/evaluer_nlu.py`. 5 demandes relues (`valide` ou `corrige`). LLM : Ollama `qwen2.5:3b` (local). Coût : **0 DT** (aucun appel payant).

## Scores

| Score | Valeur |
|---|---|
| **F1 macro** (champs de support ≥ 5, critère « fini » ≥ 0,85) | **0.960** |
| F1 micro global (28 champs) | 0.922 |
| **F1 transport macro** (8 champs, support ≥ 5) | **—** |
| F1 transport micro | 0.800 |
| Latence moyenne | 27.1 s |
| Méthode effective | hybride 5 |
| Replis sur les règles (LLM en panne, trop lent ou JSON invalide) | 0 |
| Coût | 0 DT |

Champs hors moyenne macro (support < 5) : `autres_villes` (0), `date_debut` (1), `nb_nuits` (4), `budget_illimite` (0), `nb_enfants` (1), `activites_souhaitees` (2), `niveau_marche_max` (0), `mobilite_reduite` (0), `ville_depart` (1), `vol` (1), `voiture` (0), `transfert` (1), `vol_direct` (0), `boite_auto` (0), `priorite` (1), `budget_inclut_transport` (2), `hors_sujet` (0), `champs_manquants` (0).

## Par champ

| Champ | Support | Précision | Rappel | F1 | Exactitude | Macro |
|---|---|---|---|---|---|---|
| `destination` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `autres_villes` | 0 | — | — | — | 1.000 | non |
| `date_debut` | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `duree_jours` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `nb_nuits` | 4 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `budget_montant` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_devise` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_base` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_illimite` | 0 | — | — | — | 1.000 | non |
| `nb_voyageurs` | 5 | 0.800 | 0.800 | 0.800 | 0.800 | oui |
| `nb_adultes` | 5 | 1.000 | 0.800 | 0.889 | 0.800 | oui |
| `nb_enfants` | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `type_voyage` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `preferences` | 6 | 1.000 | 0.833 | 0.909 | 0.800 | oui |
| `activites_souhaitees` | 2 | 0.500 | 0.500 | 0.500 | 0.600 | non |
| `niveau_marche_max` | 0 | 0.000 | — | 0.000 | 0.800 | non |
| `mobilite_reduite` | 0 | 0.000 | — | 0.000 | 0.800 | non |
| `langue` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `ville_depart` (transport) | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `vol` (transport) | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `voiture` (transport) | 0 | — | — | — | 1.000 | non |
| `transfert` (transport) | 1 | — | 0.000 | 0.000 | 0.800 | non |
| `vol_direct` (transport) | 0 | — | — | — | 1.000 | non |
| `boite_auto` (transport) | 0 | — | — | — | 1.000 | non |
| `priorite` (transport) | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `budget_inclut_transport` (transport) | 2 | 1.000 | 0.500 | 0.667 | 0.800 | non |
| `hors_sujet` | 0 | — | — | — | 1.000 | non |
| `champs_manquants` | 0 | — | — | — | 1.000 | non |

## Par langue et par source

| Groupe | n | F1 macro | F1 micro | F1 transport macro |
|---|---|---|---|---|
| langue = ar | 1 | 0.800 | 0.870 | — |
| langue = darija | 1 | 0.900 | 0.900 | — |
| langue = en | 1 | 1.000 | 0.889 | — |
| langue = fr | 2 | 1.000 | 0.966 | — |
| source = genere | 5 | 0.960 | 0.922 | — |

(F1 macro d'un groupe : mêmes champs que la moyenne globale.)

## Matrices d'erreurs

**`type_voyage`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | amis | couple | famille | solo |
|---|---|---|---|---|
| amis | 1 | · | · | · |
| couple | · | 1 | · | · |
| famille | · | · | 2 | · |
| solo | · | · | · | 1 |

**`besoins_transport.vol`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | oui |
|---|---|---|
| indifferent | 4 | · |
| oui | · | 1 |

**`besoins_transport.voiture`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent |
|---|---|
| indifferent | 5 |

**`besoins_transport.transfert`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | oui |
|---|---|---|
| indifferent | 4 | · |
| oui | 1 | · |

