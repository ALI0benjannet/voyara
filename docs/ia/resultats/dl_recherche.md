## Global

| approche                                            |   Recall@5 |   Recall@10 |   nDCG@10 |   MRR |   entrainement_s |   latence_ms |
|:----------------------------------------------------|-----------:|------------:|----------:|------:|-----------------:|-------------:|
| Baseline TF-IDF (caractères)                        |      0.651 |       0.737 |     0.626 | 0.63  |          nan     |        1.3   |
| DL Transfer Learning (e5 gelé)                      |      0.83  |       0.907 |     0.796 | 0.787 |          nan     |       11.7   |
| DL Fine-Tuning (e5, graine 42)                      |      0.791 |       0.861 |     0.758 | 0.744 |           23.4   |       11.9   |
| DL Fine-Tuning complet (moyenne 3 graines)          |      0.793 |       0.867 |     0.758 | 0.741 |           23.933 |       11.7   |
| DL Fine-Tuning 6 couches gelées (moyenne 3 graines) |      0.794 |       0.868 |     0.772 | 0.773 |           13.733 |       11.533 |

## nDCG@10 par langue

| approche                                            |   nDCG@10_fr |   nDCG@10_en |   nDCG@10_ar |   nDCG@10_darija |
|:----------------------------------------------------|-------------:|-------------:|-------------:|-----------------:|
| Baseline TF-IDF (caractères)                        |        0.844 |        0.567 |        0.085 |            0.539 |
| DL Transfer Learning (e5 gelé)                      |        0.876 |        0.811 |        0.658 |            0.645 |
| DL Fine-Tuning (e5, graine 42)                      |        0.807 |        0.84  |        0.723 |            0.508 |
| DL Fine-Tuning complet (moyenne 3 graines)          |        0.81  |        0.837 |        0.715 |            0.508 |
| DL Fine-Tuning 6 couches gelées (moyenne 3 graines) |        0.841 |        0.838 |        0.704 |            0.517 |

## Choix du modèle (gelés)

| modele                |   parametres_M |   nDCG@10 |   Recall@5 |   MRR |   latence_ms |   chargement+index_s |
|:----------------------|---------------:|----------:|-----------:|------:|-------------:|---------------------:|
| multilingual-e5-base  |            278 |     0.796 |      0.83  | 0.787 |         14   |                 17.4 |
| multilingual-e5-small |            118 |     0.777 |      0.791 | 0.774 |         11   |                 10.1 |
| LaBSE                 |            472 |     0.683 |      0.721 | 0.658 |         11.4 |                 18   |
| bge-m3                |            568 |     0.827 |      0.841 | 0.829 |         22.8 |                 27.1 |
