"""Démonstration de la validation Deep Learning (sans LLM) : résultats et tests en direct.

- recherche d'activités (Ons) : TF-IDF, e5 gelé, e5 fine-tuné si le modèle est présent ;
- classification des demandes (Boutheina) : règles de l'étape 4, TF-IDF + régression
  logistique, XLM-R fine-tuné si les modèles sont présents.

Page temporaire « DL test » du site client ; routes publiques sous `/api/ai/dl/*`.
"""
