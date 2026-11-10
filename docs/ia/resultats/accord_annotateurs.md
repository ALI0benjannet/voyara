# Accord entre annotateurs — jeu NLU (étape 4)

> Généré le 2026-11-09 par `services/ai/scripts/accord_annotateurs.py`. Annotateur A : équipe (`brut/demandes_equipe.json`) ; annotateur B : annotation du jeu (`demandes_humaines_a_annoter.jsonl`). 130 demandes humaines ; statuts : corrige 7, valide 123.

| Champ | n | Accords | Accord (%) | κ de Cohen | Interprétation |
|---|---|---|---|---|---|
| `destination` | 130 | 130 | 100.0 | 1.000 | presque parfait |
| `autres_villes` | 130 | 130 | 100.0 | — | — |
| `langue` | 130 | 130 | 100.0 | 1.000 | presque parfait |
| `type_voyage` | 130 | 107 | 82.3 | 0.779 | substantiel |
| `nb_voyageurs` | 130 | 126 | 96.9 | — | — |
| `duree_jours` | 130 | 130 | 100.0 | — | — |
| `budget_montant` | 130 | 113 | 86.9 | — | — |
| `budget_devise` | 130 | 130 | 100.0 | 1.000 | presque parfait |
| `budget_base` | 130 | 130 | 100.0 | 1.000 | presque parfait |
| `ville_depart` | 130 | 122 | 93.8 | 0.848 | presque parfait |
| `vol` | 130 | 119 | 91.5 | 0.782 | substantiel |
| `voiture` | 130 | 121 | 93.1 | 0.858 | presque parfait |
| `transfert` | 130 | 130 | 100.0 | 1.000 | presque parfait |
| `champs_manquants` | 130 | 102 | 78.5 | — | — |
| `activites (nombre)` | 130 | 106 | 81.5 | — | — |

κ moyen sur les 9 champs catégoriels : **0.919**.

Lecture : κ corrige l'accord du hasard (`null` compte comme une catégorie) ; échelle de Landis et Koch : > 0,8 presque parfait, > 0,6 substantiel, > 0,4 modéré. Les champs numériques ou listes (voyageurs, durée, montant, autres villes, champs manquants) n'ont qu'un pourcentage d'accord exact. Pour les activités, l'équipe note des codes normalisés (`nuit_desert`) et le jeu des textes tels que dits (« nuit sous tente ») : seul le **nombre** d'activités par demande est comparé. Une partie des désaccords est **voulue** : les règles du README (budget par personne converti en total, date manquante pour un vol, type de voyage plus strict) ont été appliquées après coup à l'annotation B.

**Limite : les deux annotations ne sont pas indépendantes.** B est une pré-annotation faite en voyant A (ordre des villes, `budget_base` repris de `budget_type`, correspondance des langues). Les accords sont donc **surestimés**, en particulier à 100 % pour `destination`, `langue` et `budget_base`. Une mesure indépendante demanderait qu'un second annotateur annote à l'aveugle un sous-échantillon.
