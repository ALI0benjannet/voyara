# Journal du moteur IA

Une ligne par étape terminée. Détail dans [rapports/](rapports/) · vue d'ensemble : [README.md](README.md).

| Date | Étape | Résumé |
|---|---|---|
| 2026-10-11 | 0 · Cadrage | CLAUDE.md, docs/ia/ (vision, 6 modules, modèle de rapport), ADR-007 (service `ai` :8008, `voyara_ai` + pgvector, LLM hybride Claude/Ollama), phase « Moteur IA » (étapes 0–13) dans plan.md ; Phase 10 marquée remplacée. Aucun code applicatif. |
| 2026-10-11 | 0 · Cadrage (addendum) | Étape 1 étendue : seed réaliste idempotent du catalogue (≥ 30 activités à Djerba, 60–100 sur 5 villes, GPS, prix DT, durées, créneaux 4 semaines, fr/en/ar). Risque étape 3 : option Postgres dédié au service ai (pgvector:pg16, port 5435) à trancher. |
| 2026-10-11 | 1 · Seed du catalogue (sous-tâche) | `services/catalog/scripts/seed_catalogue_demo.py` (idempotent, `--verifier`) : 86 activités réelles géocodées via OSM (Djerba 32, Tunis/Sidi Bou Saïd 16, Sousse/Monastir 14, Hammamet 12, Tozeur 12), fr/en/ar, 3 664 créneaux du 12/10 au 08/11/2026. Catalogue : 96 activités. Collecte POI/météo restante. |
| 2026-10-12 | 1 · Photos du catalogue (sous-tâche) | `services/catalog/scripts/seed_photos_demo.py` : 86 photos Wikimedia Commons (licence lue via l'API, CC0 / domaine public / CC BY / CC BY-SA uniquement) versionnées dans `static/activities/demo/` (21,2 Mo), crédits sur `/credits`. Relie les photos en base sans réseau. Garde-fou dans l'upload admin. 96/96 activités illustrées. |
