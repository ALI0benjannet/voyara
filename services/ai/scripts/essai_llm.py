"""Essai manuel de la couche LLM (étape 3) : un vrai appel, journalisé dans `llm_appels`.

Modes :
  texte   une question libre, réponse en texte ;
  json    extraction structurée (schéma JSON, aperçu de l'étape 4) ;
  outil   le modèle doit appeler l'outil `meteo` (aperçu de l'agent de l'étape 8).

Usage (depuis services/ai, conteneur postgres-ai démarré) :
    python scripts/essai_llm.py --provider ollama --mode json
    python scripts/essai_llm.py --provider auto              # sans clé : bascule sur Ollama
    python scripts/essai_llm.py --provider claude --mode outil

La clé ANTHROPIC_API_KEY est lue dans .env ; elle n'est jamais affichée.
Code de sortie : 0 succès, 1 erreur LLM, 2 refus de sécurité.
"""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.llm.base import ErreurLLM, LLMRefus, Message, Outil  # noqa: E402
from app.llm.fabrique import creer_client_llm  # noqa: E402
from app.llm.journal import JournalLLM, JournalMemoire  # noqa: E402

SYSTEME = ("Tu es l'assistant de voyage de Voyara (Tunisie). Réponds en français, brièvement. "
           "N'invente jamais de prix, d'horaire ni de disponibilité.")
DEMANDE = "Je vais à Jerba 3 jours avec ma femme et nos deux enfants, 300 dinars, culture et plage."
SCHEMA = {
    "type": "object",
    "properties": {
        "destination": {"type": "string"},
        "duree_jours": {"type": "integer"},
        "budget_total_dt": {"type": ["number", "null"]},
        "nb_adultes": {"type": "integer"},
        "nb_enfants": {"type": "integer"},
        "preferences": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["destination", "duree_jours", "budget_total_dt", "nb_adultes", "nb_enfants", "preferences"],
    "additionalProperties": False,
}
OUTIL_METEO = Outil("meteo", "Prévisions météo d'une ville de Tunisie pour une date (AAAA-MM-JJ).", {
    "type": "object",
    "properties": {"ville": {"type": "string"}, "date": {"type": "string"}},
    "required": ["ville", "date"],
    "additionalProperties": False,
})


async def essayer(provider: str, mode: str, journaliser: bool) -> int:
    settings.LLM_PROVIDER = provider
    if journaliser:
        Base.metadata.create_all(bind=engine)
        journal = JournalLLM(SessionLocal)
    else:
        journal = JournalMemoire()
    llm = creer_client_llm(settings, journal)
    print(f"Fournisseur demandé : {provider} · clé Claude : "
          f"{'présente' if llm.claude.cle_presente else 'absente'} · modèles : "
          f"{llm.claude.modele} / {llm.ollama.modele}")

    params: dict = {"systeme": SYSTEME, "usage": "essai"}
    if mode == "texte":
        params["messages"] = [Message("user", "En une phrase : que voir à Sidi Bou Saïd ?")]
    elif mode == "json":
        params["messages"] = [Message("user", f"Extrais la demande de voyage : « {DEMANDE} »")]
        params["schema_sortie"] = SCHEMA
        params["temperature"] = 0  # appliquée par Ollama seulement
    else:
        params["messages"] = [Message("user", "Quel temps fera-t-il à Djerba le 2026-11-07 ? "
                                              "Utilise l'outil meteo.")]
        params["outils"] = [OUTIL_METEO]

    try:
        r = await llm.generer(max_tokens=2000, **params)
    except LLMRefus as exc:
        print(f"✗ Refus de sécurité ({exc.provider}, catégorie {exc.categorie}) — aucune bascule.")
        return 2
    except ErreurLLM as exc:
        print(f"✗ {type(exc).__name__} ({exc.provider}) : {exc}")
        if isinstance(journal, JournalMemoire):
            print(f"  journal : {journal.lignes}")
        return 1

    print(f"✓ Servi par {r.provider} ({r.modele})" + (f", après bascule depuis {r.bascule_depuis}"
                                                     if r.bascule_depuis else ""))
    print(f"  latence {r.latence_ms} ms · tokens {r.tokens_entree} -> {r.tokens_sortie} · "
          f"coût estimé {r.cout_estime} USD · arrêt : {r.raison_arret}")
    if r.donnees is not None:
        print("  données :", json.dumps(r.donnees, ensure_ascii=False))
    for appel in r.appels_outils:
        print(f"  appel d'outil : {appel.nom}({json.dumps(appel.arguments, ensure_ascii=False)})")
    if r.texte and r.donnees is None:
        print("  texte :", r.texte.strip()[:500])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Essai manuel de la couche LLM.")
    parser.add_argument("--provider", choices=["claude", "ollama", "auto"], default=settings.LLM_PROVIDER)
    parser.add_argument("--mode", choices=["texte", "json", "outil"], default="texte")
    parser.add_argument("--sans-journal", action="store_true", help="ne pas écrire dans llm_appels")
    args = parser.parse_args()
    return asyncio.run(essayer(args.provider, args.mode, not args.sans_journal))


if __name__ == "__main__":
    sys.exit(main())
