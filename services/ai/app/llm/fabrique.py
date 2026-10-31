"""Choix du fournisseur LLM et bascule automatique (étape 3).

`LLM_PROVIDER` :
- `claude` : Claude seul (une panne remonte à l'appelant) ;
- `ollama` : Ollama seul (coût nul, hors-ligne) ;
- `auto`   : Claude, puis Ollama si la clé est absente ou refusée, si Claude est
  indisponible (réseau, délai, 429, 5xx) ou si la requête est rejetée.
Un **refus de sécurité ne déclenche jamais de bascule** : le contourner avec un modèle
local irait contre la décision du classifieur. Chaque tentative est journalisée.
"""

import time
from typing import Any

from app.llm.base import (
    LLMCleAbsente,
    LLMIndisponible,
    LLMProvider,
    LLMRefus,
    LLMRequeteInvalide,
    Message,
    Outil,
    ReponseLLM,
)
from app.llm.claude import ClaudeProvider
from app.llm.journal import JournalLLM
from app.llm.ollama import OllamaProvider

MODES = ("claude", "ollama", "auto")


def _ms_depuis(debut: float) -> int:
    return round((time.perf_counter() - debut) * 1000)


ERREURS_DE_BASCULE = (LLMCleAbsente, LLMIndisponible, LLMRequeteInvalide)


class ClientLLM:
    """Point d'entrée unique du métier vers les LLM."""

    def __init__(self, mode: str, claude: ClaudeProvider, ollama: OllamaProvider, journal: JournalLLM):
        if mode not in MODES:
            raise ValueError(f"LLM_PROVIDER inconnu : {mode!r} (attendu : {', '.join(MODES)})")
        self.mode = mode
        self.claude = claude
        self.ollama = ollama
        self.journal = journal

    async def _appeler(
        self, provider: LLMProvider, usage: str, parent: int | None, basculable: bool = False,
        **params: Any,
    ) -> tuple[ReponseLLM, int | None]:
        debut = time.perf_counter()
        try:
            reponse = await provider.generer(**params)
        except LLMRefus as exc:
            await self.journal.enregistrer(provider.nom, provider.modele, "refus", usage,
                                           latence_ms=_ms_depuis(debut),
                                           erreur=f"catégorie={exc.categorie}", appel_parent_id=parent)
            raise
        except Exception as exc:
            # Le temps perdu compte aussi : un délai dépassé coûte OLLAMA_TIMEOUT_S secondes.
            statut = "bascule" if basculable and isinstance(exc, ERREURS_DE_BASCULE) else "erreur"
            exc.id_journal = await self.journal.enregistrer(  # type: ignore[attr-defined]
                provider.nom, provider.modele, statut, usage, latence_ms=_ms_depuis(debut),
                erreur=exc, appel_parent_id=parent)
            raise
        id_journal = await self.journal.enregistrer(
            provider.nom, reponse.modele, "succes", usage,
            tokens_entree=reponse.tokens_entree, tokens_sortie=reponse.tokens_sortie,
            latence_ms=reponse.latence_ms, cout_estime=reponse.cout_estime, appel_parent_id=parent,
        )
        return reponse, id_journal

    async def generer(
        self,
        messages: list[Message],
        systeme: str | None = None,
        outils: list[Outil] | None = None,
        schema_sortie: dict[str, Any] | None = None,
        max_tokens: int = 16000,
        temperature: float | None = None,
        usage: str = "inconnu",
    ) -> ReponseLLM:
        params = {"messages": messages, "systeme": systeme, "outils": outils,
                  "schema_sortie": schema_sortie, "max_tokens": max_tokens, "temperature": temperature}
        if self.mode == "claude":
            return (await self._appeler(self.claude, usage, None, **params))[0]
        if self.mode == "ollama":
            return (await self._appeler(self.ollama, usage, None, **params))[0]

        # Mode auto
        if not self.claude.cle_presente:
            parent = await self.journal.enregistrer(
                "claude", self.claude.modele, "bascule", usage, erreur="ANTHROPIC_API_KEY absente")
        else:
            try:
                return (await self._appeler(self.claude, usage, None, basculable=True, **params))[0]
            except ERREURS_DE_BASCULE as exc:
                parent = getattr(exc, "id_journal", None)
        reponse, _ = await self._appeler(self.ollama, usage, parent, **params)
        reponse.bascule_depuis = "claude"
        return reponse


def creer_client_llm(settings: Any, journal: JournalLLM) -> ClientLLM:
    claude = ClaudeProvider(
        api_key=settings.ANTHROPIC_API_KEY,
        modele=settings.CLAUDE_MODEL,
        effort=settings.CLAUDE_EFFORT,
        timeout_s=settings.CLAUDE_TIMEOUT_S,
        max_retries=settings.CLAUDE_MAX_RETRIES,
        replis_serveur=settings.CLAUDE_FALLBACKS,
    )
    ollama = OllamaProvider(settings.OLLAMA_URL, settings.OLLAMA_MODEL, settings.OLLAMA_TIMEOUT_S)
    return ClientLLM(settings.LLM_PROVIDER, claude, ollama, journal)
