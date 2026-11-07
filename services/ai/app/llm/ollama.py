"""Fournisseur Ollama (LLM local, gratuit, hors-ligne) via son API HTTP `/api/chat`.

- `format` : JSON Schema si `schema_sortie` est fourni (sortie contrainte), sinon texte ;
- outils au format « function » ; `options.temperature` et `num_predict` supportés ;
- tokens : `prompt_eval_count` (entrée) et `eval_count` (sortie) ; coût 0.
"""

import json
import time
from typing import Any

import httpx

from app.llm.base import (
    AppelOutil,
    LLMIndisponible,
    LLMProvider,
    LLMRequeteInvalide,
    LLMSortieInvalide,
    Message,
    Outil,
    ReponseLLM,
)


def outil_vers_ollama(outil: Outil) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {"name": outil.nom, "description": outil.description, "parameters": outil.schema},
    }


class OllamaProvider(LLMProvider):
    nom = "ollama"

    def __init__(
        self,
        url: str,
        modele: str,
        timeout_s: float = 180.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.url = url.rstrip("/")
        self._modele = modele
        self.timeout_s = timeout_s
        self.transport = transport  # httpx.MockTransport dans les tests

    @property
    def modele(self) -> str:
        return self._modele

    def construire_requete(
        self,
        messages: list[Message],
        systeme: str | None,
        outils: list[Outil] | None,
        schema_sortie: dict[str, Any] | None,
        max_tokens: int,
        temperature: float | None,
    ) -> dict[str, Any]:
        historique = [{"role": "system", "content": systeme}] if systeme else []
        historique += [{"role": m.role, "content": m.contenu} for m in messages]
        options: dict[str, Any] = {"num_predict": max_tokens}
        if temperature is not None:
            options["temperature"] = temperature
        requete: dict[str, Any] = {
            "model": self._modele,
            "messages": historique,
            "stream": False,
            "options": options,
        }
        if schema_sortie:
            requete["format"] = schema_sortie
        if outils:
            requete["tools"] = [outil_vers_ollama(o) for o in outils]
        return requete

    async def est_joignable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0, transport=self.transport) as client:
                return (await client.get(f"{self.url}/api/tags")).status_code == 200
        except httpx.HTTPError:
            return False

    async def generer(
        self,
        messages: list[Message],
        systeme: str | None = None,
        outils: list[Outil] | None = None,
        schema_sortie: dict[str, Any] | None = None,
        max_tokens: int = 16000,
        temperature: float | None = None,
    ) -> ReponseLLM:
        requete = self.construire_requete(messages, systeme, outils, schema_sortie, max_tokens, temperature)
        debut = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s, transport=self.transport) as client:
                reponse = await client.post(f"{self.url}/api/chat", json=requete)
        except httpx.TimeoutException as exc:
            raise LLMIndisponible("délai dépassé", self.nom) from exc
        except httpx.HTTPError as exc:
            raise LLMIndisponible(f"Ollama injoignable ({type(exc).__name__})", self.nom) from exc
        if reponse.status_code >= 500:
            raise LLMIndisponible(f"erreur serveur ({reponse.status_code})", self.nom)
        if reponse.status_code != 200:
            # 404 : modèle non téléchargé (`ollama pull`), ou requête mal formée
            raise LLMRequeteInvalide(f"requête refusée ({reponse.status_code})", self.nom)
        latence_ms = round((time.perf_counter() - debut) * 1000)
        return self._normaliser(reponse.json(), schema_sortie, latence_ms)

    def _normaliser(self, corps: dict, schema_sortie: dict | None, latence_ms: int) -> ReponseLLM:
        message = corps.get("message") or {}
        texte = message.get("content") or ""
        appels = []
        for i, appel in enumerate(message.get("tool_calls") or []):
            fonction = appel.get("function") or {}
            arguments = fonction.get("arguments") or {}
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            appels.append(AppelOutil(id=appel.get("id") or f"ollama-{i}", nom=fonction.get("name", ""),
                                     arguments=arguments))
        donnees = None
        if schema_sortie and not appels:
            try:
                donnees = json.loads(texte)
            except json.JSONDecodeError as exc:
                raise LLMSortieInvalide("JSON invalide", self.nom) from exc
        return ReponseLLM(
            texte=texte,
            provider=self.nom,
            modele=corps.get("model") or self._modele,
            appels_outils=appels,
            donnees=donnees,
            tokens_entree=int(corps.get("prompt_eval_count") or 0),
            tokens_sortie=int(corps.get("eval_count") or 0),
            latence_ms=latence_ms,
            cout_estime=0.0,
            raison_arret="tool_use" if appels else corps.get("done_reason"),
            blocs_bruts=[message],
        )
