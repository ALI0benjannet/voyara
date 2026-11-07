"""Interface commune des fournisseurs de LLM (étape 3).

Le métier (compréhension, explications, agent) ne parle qu'à `LLMProvider` : changer de
fournisseur, comparer Claude et Ollama sur le même jeu de test ou basculer en cas de panne
ne touche pas au code appelant. Principe directeur : le LLM comprend et explique ; il ne
fournit jamais un prix, un horaire ou une disponibilité (ceux-ci viennent des bases).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    contenu: str


@dataclass(frozen=True)
class Outil:
    """Outil proposé au modèle ; `schema` = JSON Schema des arguments."""

    nom: str
    description: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class AppelOutil:
    id: str
    nom: str
    arguments: dict[str, Any]


@dataclass
class ReponseLLM:
    """Réponse normalisée, identique quel que soit le fournisseur."""

    texte: str
    provider: str
    modele: str
    appels_outils: list[AppelOutil] = field(default_factory=list)
    # JSON déjà décodé quand un `schema_sortie` a été demandé
    donnees: dict[str, Any] | None = None
    tokens_entree: int = 0
    tokens_sortie: int = 0
    latence_ms: int = 0
    cout_estime: float | None = None  # USD ; None si le tarif du modèle est inconnu
    raison_arret: str | None = None
    # Renseigné par la fabrique quand la réponse vient d'une bascule (ex. "claude")
    bascule_depuis: str | None = None
    # Contenu brut du fournisseur (blocs Claude, dont `thinking`) : l'agent de l'étape 8
    # doit le renvoyer tel quel dans l'historique, sans le modifier.
    blocs_bruts: list[Any] = field(default_factory=list)


# --- Erreurs typées ---------------------------------------------------------


class ErreurLLM(Exception):
    """Base des erreurs de la couche LLM. `provider` = fournisseur en cause."""

    def __init__(self, message: str, provider: str = ""):
        super().__init__(message)
        self.provider = provider


class LLMCleAbsente(ErreurLLM):
    """Clé API non configurée (Claude)."""


class LLMIndisponible(ErreurLLM):
    """Réseau, délai dépassé, saturation (429) ou erreur serveur (5xx) : réessayable."""


class LLMRequeteInvalide(ErreurLLM):
    """Requête refusée par le fournisseur (400, 404 modèle inconnu...) : bug à corriger."""


class LLMSortieInvalide(ErreurLLM):
    """Le modèle n'a pas rendu un JSON conforme au schéma demandé."""


class LLMRefus(ErreurLLM):
    """Refus d'un classifieur de sécurité. Jamais contourné par une bascule."""

    def __init__(self, message: str, provider: str = "", categorie: str | None = None):
        super().__init__(message, provider)
        self.categorie = categorie


class LLMProvider(ABC):
    nom: str = ""

    @property
    @abstractmethod
    def modele(self) -> str: ...

    @abstractmethod
    async def generer(
        self,
        messages: list[Message],
        systeme: str | None = None,
        outils: list[Outil] | None = None,
        schema_sortie: dict[str, Any] | None = None,
        max_tokens: int = 16000,
        temperature: float | None = None,
    ) -> ReponseLLM:
        """Un appel au modèle. `temperature` n'est appliquée que là où le fournisseur
        l'accepte (Ollama) : la version d'API Claude 2026-10-21 la refuse."""
