"""Coût estimé d'un appel LLM, en USD (tarifs publics Anthropic par million de tokens).

Relevés dans la documentation Claude API (cache du 06/10/2026). Les tokens de pensée
adaptative sont comptés dans les tokens de sortie, donc déjà inclus. Ollama tourne en
local : coût 0. Un modèle inconnu donne None (on n'invente pas de tarif).
"""

# modèle -> (USD / M tokens d'entrée, USD / M tokens de sortie)
TARIFS_USD_PAR_MILLION: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-fable-5-1": (10.00, 50.00),
}


def cout_estime(provider: str, modele: str, tokens_entree: int, tokens_sortie: int) -> float | None:
    if provider == "ollama":
        return 0.0
    tarif = TARIFS_USD_PAR_MILLION.get(modele)
    if tarif is None:
        return None
    return round((tokens_entree * tarif[0] + tokens_sortie * tarif[1]) / 1_000_000, 6)
