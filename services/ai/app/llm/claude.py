"""Fournisseur Claude (SDK officiel `anthropic` 2.x, version d'API 2026-10-21).

- outils natifs (tool use) ; `tool_choice` reste `auto` : le choix forcé (`any` / `tool`)
  renvoie une 400 sur Claude Sonnet 5.5. `strict: true` quand le schéma le permet ;
- sortie structurée via `output_config.format` (JSON Schema), effort via `output_config.effort` ;
- pensée adaptative laissée par défaut (on n'envoie pas `thinking`) : les blocs `thinking`
  sont ignorés pour le texte mais conservés dans `blocs_bruts` ;
- `temperature` n'est jamais envoyée (400 sur tous les modèles avec la version 2026-10-21) ;
- repli côté serveur sur refus (`fallbacks: "default"`), activable par configuration.
"""

import json
import time
from typing import Any

import anthropic

from app.llm.base import (
    AppelOutil,
    LLMCleAbsente,
    LLMIndisponible,
    LLMProvider,
    LLMRefus,
    LLMRequeteInvalide,
    LLMSortieInvalide,
    Message,
    Outil,
    ReponseLLM,
)
from app.llm.tarifs import cout_estime

BETA_REPLI_SERVEUR = "server-side-fallback-2026-07-01"


def outil_vers_claude(outil: Outil) -> dict[str, Any]:
    definition: dict[str, Any] = {
        "name": outil.nom,
        "description": outil.description,
        "input_schema": outil.schema,
    }
    # `strict` garantit des arguments conformes, mais exige additionalProperties: false.
    if outil.schema.get("additionalProperties") is False:
        definition["strict"] = True
    return definition


class ClaudeProvider(LLMProvider):
    nom = "claude"

    def __init__(
        self,
        api_key: str | None,
        modele: str,
        effort: str | None = "medium",
        timeout_s: float = 60.0,
        max_retries: int = 1,
        replis_serveur: bool = True,
        client: Any | None = None,
    ):
        self._modele = modele
        self.effort = effort
        self.replis_serveur = replis_serveur
        self.cle_presente = bool(api_key)
        # `client` injectable : les tests passent un faux client, jamais d'appel réel.
        self._client = client
        self._options = {"api_key": api_key, "timeout": timeout_s, "max_retries": max_retries}

    @property
    def modele(self) -> str:
        return self._modele

    def _client_sdk(self):
        if self._client is None:
            if not self.cle_presente:
                raise LLMCleAbsente("ANTHROPIC_API_KEY absente de la configuration", self.nom)
            self._client = anthropic.AsyncAnthropic(**self._options)
        return self._client

    def construire_requete(
        self,
        messages: list[Message],
        systeme: str | None,
        outils: list[Outil] | None,
        schema_sortie: dict[str, Any] | None,
        max_tokens: int,
    ) -> dict[str, Any]:
        requete: dict[str, Any] = {
            "model": self._modele,
            "max_tokens": max_tokens,
            "messages": [{"role": m.role, "content": m.contenu} for m in messages],
        }
        if systeme:
            requete["system"] = systeme
        if outils:
            requete["tools"] = [outil_vers_claude(o) for o in outils]
        config: dict[str, Any] = {}
        if self.effort:
            config["effort"] = self.effort
        if schema_sortie:
            config["format"] = {"type": "json_schema", "schema": schema_sortie}
        if config:
            requete["output_config"] = config
        if self.replis_serveur:
            requete["betas"] = [BETA_REPLI_SERVEUR]
            requete["fallbacks"] = "default"
        return requete

    async def generer(
        self,
        messages: list[Message],
        systeme: str | None = None,
        outils: list[Outil] | None = None,
        schema_sortie: dict[str, Any] | None = None,
        max_tokens: int = 16000,
        temperature: float | None = None,  # volontairement ignorée (voir le module)
    ) -> ReponseLLM:
        client = self._client_sdk()
        requete = self.construire_requete(messages, systeme, outils, schema_sortie, max_tokens)
        debut = time.perf_counter()
        try:
            reponse = await client.beta.messages.create(**requete)
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise LLMCleAbsente(f"clé refusée par l'API ({exc.status_code})", self.nom) from exc
        except anthropic.RateLimitError as exc:
            raise LLMIndisponible("limite de débit atteinte (429)", self.nom) from exc
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                raise LLMIndisponible(f"erreur serveur ({exc.status_code})", self.nom) from exc
            raise LLMRequeteInvalide(f"requête refusée ({exc.status_code})", self.nom) from exc
        except anthropic.APITimeoutError as exc:
            raise LLMIndisponible("délai dépassé", self.nom) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMIndisponible("connexion impossible", self.nom) from exc
        latence_ms = round((time.perf_counter() - debut) * 1000)
        return self._normaliser(reponse, schema_sortie, latence_ms)

    def _normaliser(self, reponse: Any, schema_sortie: dict | None, latence_ms: int) -> ReponseLLM:
        if reponse.stop_reason == "refusal":
            details = getattr(reponse, "stop_details", None)
            raise LLMRefus(
                "refus d'un classifieur de sécurité",
                self.nom,
                categorie=getattr(details, "category", None),
            )
        textes, appels = [], []
        for bloc in reponse.content:
            if bloc.type == "text":
                textes.append(bloc.text)
            elif bloc.type == "tool_use":
                arguments = bloc.input if isinstance(bloc.input, dict) else json.loads(bloc.input)
                appels.append(AppelOutil(id=bloc.id, nom=bloc.name, arguments=arguments))
        texte = "".join(textes)
        donnees = None
        if schema_sortie and reponse.stop_reason != "tool_use":
            try:
                donnees = json.loads(texte)
            except json.JSONDecodeError as exc:
                raise LLMSortieInvalide("JSON invalide malgré output_config.format", self.nom) from exc
        usage = reponse.usage
        modele = getattr(reponse, "model", None) or self._modele  # modèle de repli éventuel
        return ReponseLLM(
            texte=texte,
            provider=self.nom,
            modele=modele,
            appels_outils=appels,
            donnees=donnees,
            tokens_entree=usage.input_tokens,
            tokens_sortie=usage.output_tokens,
            latence_ms=latence_ms,
            cout_estime=cout_estime(self.nom, modele, usage.input_tokens, usage.output_tokens),
            raison_arret=reponse.stop_reason,
            blocs_bruts=[b.model_dump() if hasattr(b, "model_dump") else b for b in reponse.content],
        )
