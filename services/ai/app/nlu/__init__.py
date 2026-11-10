"""Module 1 — compréhension du voyageur (NLU, étape 4).

Texte libre (fr / en / ar / darija) → `DemandeVoyage` structurée, champs manquants et question de
clarification. Méthode hybride : des règles déterministes pour les faits explicites (montants,
durées, dates, villes, langue, transport), le LLM (via `ClientLLM`) pour ce qui demande de
comprendre (voyageurs, préférences, activités, contraintes, hors sujet), puis normalisation et
validation. Le vocabulaire et les règles dérivées viennent de `scripts/jeu_nlu.py` (source unique,
partagée avec le jeu d'évaluation) : importé, jamais recopié.
"""
