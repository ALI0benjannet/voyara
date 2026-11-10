"""Schémas Pydantic du module 1 : `DemandeVoyage` et la réponse de `POST /api/ai/comprendre`.

`DemandeVoyage` reprend les champs `attendu` du jeu d'évaluation (data/eval/README.md), sauf les
deux champs dérivés : `budget_total_dt` (calculé par `jeu_nlu.deriver`) et `champs_manquants`
(publié à part dans `ReponseComprendre`). Les vocabulaires viennent de `jeu_nlu`.
"""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scripts import jeu_nlu

Besoin = Literal["oui", "non", "indifferent"]
TypeVoyage = Literal["famille", "couple", "solo", "amis", "groupe"]
Langue = Literal["fr", "en", "ar", "darija"]
BaseBudget = Literal["total", "par_personne", "par_nuit", "par_jour"]
Theme = Literal["plage", "culture", "histoire", "nature", "gastronomie",
                "aventure", "detente", "shopping", "nautique", "desert"]
Methode = Literal["regles", "llm", "hybride"]

DUREE_PLANNING_MAX = 14
AVERTISSEMENT_DUREE = "planning limité à 14 jours"

# Les Literal ci-dessus doivent rester alignés sur le vocabulaire du jeu (test_nlu_schemas le vérifie).
VOCABULAIRES_LITERAL = {
    "types": (TypeVoyage, jeu_nlu.TYPES_VOYAGE), "langues": (Langue, jeu_nlu.LANGUES),
    "bases": (BaseBudget, jeu_nlu.BASES_BUDGET), "themes": (Theme, jeu_nlu.THEMES),
    "besoins": (Besoin, jeu_nlu.BESOINS),
}


class Contraintes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    niveau_marche_max: int | None = Field(None, ge=1, le=3)
    mobilite_reduite: bool | None = None
    horaires: str | None = Field(None, max_length=120)


class BesoinsTransport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vol: Besoin = "indifferent"
    voiture: Besoin = "indifferent"
    transfert: Besoin = "indifferent"


class PreferencesTransport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vol_direct: bool | None = None
    boite_auto: bool | None = None
    priorite: Literal["prix", "confort"] | None = None


class DemandeVoyage(BaseModel):
    """Demande de voyage structurée. Les faits (prix, horaires, disponibilités) n'y figurent
    jamais : ils viennent des bases aux étapes suivantes."""

    model_config = ConfigDict(extra="forbid")

    destination: str | None = None
    autres_villes: list[str] = Field(default_factory=list)
    date_debut: date | None = None
    duree_jours: int | None = Field(None, ge=1, le=jeu_nlu.DUREE_MAX_JOURS)
    nb_nuits: int | None = Field(None, ge=0, le=jeu_nlu.DUREE_MAX_JOURS)
    # Total pour tout le groupe, dans la devise dite ; `budget_base` garde la forme d'origine.
    budget_montant: float | None = None
    budget_devise: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    budget_base: BaseBudget | None = None
    budget_illimite: bool = False
    nb_voyageurs: int | None = Field(None, ge=1, le=500)
    nb_adultes: int | None = Field(None, ge=1, le=500)
    nb_enfants: int | None = Field(None, ge=0, le=500)
    type_voyage: TypeVoyage | None = None
    preferences: list[Theme] = Field(default_factory=list)
    activites_souhaitees: list[str] = Field(default_factory=list)
    contraintes: Contraintes = Field(default_factory=Contraintes)
    langue: Langue = "fr"
    ville_depart: str | None = None
    besoins_transport: BesoinsTransport = Field(default_factory=BesoinsTransport)
    preferences_transport: PreferencesTransport = Field(default_factory=PreferencesTransport)
    budget_inclut_transport: bool = False
    hors_sujet: bool = False

    @field_validator("budget_montant")
    @classmethod
    def _budget_positif(cls, valeur: float | None) -> float | None:
        if valeur is not None and valeur <= 0:
            raise ValueError("le budget doit être strictement positif")
        return valeur

    @field_validator("destination")
    @classmethod
    def _destination_catalogue(cls, valeur: str | None) -> str | None:
        if valeur is not None and valeur not in jeu_nlu.VILLES_CATALOGUE:
            raise ValueError(f"destination hors catalogue : {valeur!r}")
        return valeur

    @field_validator("autres_villes")
    @classmethod
    def _autres_villes_catalogue(cls, valeurs: list[str]) -> list[str]:
        for ville in valeurs:
            if ville not in jeu_nlu.VILLES_CATALOGUE:
                raise ValueError(f"ville hors catalogue : {ville!r}")
        return valeurs

    @field_validator("activites_souhaitees")
    @classmethod
    def _activites_courtes(cls, valeurs: list[str]) -> list[str]:
        for activite in valeurs:
            if not activite.strip() or len(activite) > jeu_nlu.LONGUEUR_MAX_ACTIVITE or ";" in activite:
                raise ValueError(f"activité invalide : {activite[:40]!r}")
        return valeurs

    @model_validator(mode="after")
    def _coherence(self) -> "DemandeVoyage":
        if self.ville_depart is not None and self.ville_depart == self.destination:
            raise ValueError("ville_depart identique à la destination")
        return self

    def vers_attendu(self) -> dict[str, Any]:
        """Dictionnaire au format `attendu` du jeu (dates ISO, montants entiers si ronds), avec
        les champs dérivés recalculés par `jeu_nlu.deriver`."""
        a = self.model_dump(mode="json")
        montant = a["budget_montant"]
        if isinstance(montant, float) and montant.is_integer():
            a["budget_montant"] = int(montant)
        jeu_nlu.deriver(a)
        return a


def avertissements_demande(demande: DemandeVoyage) -> list[str]:
    """Avertissements non bloquants (la demande reste acceptée)."""
    sortie = []
    if demande.duree_jours is not None and demande.duree_jours > DUREE_PLANNING_MAX:
        sortie.append(AVERTISSEMENT_DUREE)
    return sortie


class RequeteComprendre(BaseModel):
    texte: str = Field(..., min_length=1, max_length=2000)
    # « Aujourd'hui » pour résoudre les dates relatives ; par défaut la date du jour à Tunis.
    date_reference: date | None = None

    @field_validator("texte")
    @classmethod
    def _texte_non_vide(cls, valeur: str) -> str:
        if not valeur.strip():
            raise ValueError("texte vide")
        return valeur


class ReponseComprendre(BaseModel):
    demande: DemandeVoyage
    champs_manquants: list[str]
    question_clarification: str | None = None
    avertissements: list[str] = Field(default_factory=list)
    # Fournisseur qui a réellement répondu : "regles", "ollama" ou "claude"
    provider: str
    latence_ms: int
    methode: Methode


# --- JSON Schema demandé au LLM -------------------------------------------------

# Champs que le LLM remplit en mode hybride (le reste vient des règles).
CHAMPS_LLM_HYBRIDE = ("type_voyage", "nb_voyageurs", "nb_adultes", "nb_enfants", "preferences",
                      "activites_souhaitees", "niveau_marche_max", "mobilite_reduite", "hors_sujet")


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


# Variante « hybride v2 » (ablation, décidée après avoir vu le total du test) : le LLM propose aussi
# les besoins de transport et la ville de départ, retenus seulement là où les règles ne sont pas sûres.
CHAMPS_LLM_TRANSPORT = ("ville_depart", "vol", "voiture", "transfert")


def schema_llm_hybride(transport: bool = False) -> dict[str, Any]:
    """Schéma réduit (≈ 80 tokens de sortie) : ce qui demande de comprendre le texte.
    `transport=True` (v2) ajoute `ville_depart`, `vol`, `voiture`, `transfert`."""
    entier = {"type": "integer"}
    proprietes = {
        "type_voyage": _nullable({"type": "string", "enum": list(jeu_nlu.TYPES_VOYAGE)}),
        "nb_voyageurs": _nullable(entier),
        "nb_adultes": _nullable(entier),
        "nb_enfants": _nullable(entier),
        "preferences": {"type": "array", "items": {"type": "string", "enum": list(jeu_nlu.THEMES)}},
        "activites_souhaitees": {"type": "array", "items": {"type": "string"}},
        "niveau_marche_max": _nullable({"type": "integer", "enum": [1, 2, 3]}),
        "mobilite_reduite": _nullable({"type": "boolean"}),
        "hors_sujet": {"type": "boolean"},
    }
    if transport:
        besoin = {"type": "string", "enum": list(jeu_nlu.BESOINS)}
        proprietes |= {"ville_depart": _nullable({"type": "string"}), "vol": besoin, "voiture": besoin,
                       "transfert": besoin}
    return {"type": "object", "properties": proprietes, "required": list(proprietes),
            "additionalProperties": False}


def schema_llm_complet() -> dict[str, Any]:
    """Schéma de `DemandeVoyage` entier (mode « LLM seul », pour la comparaison). `budget_montant`
    y est le montant **tel que dit** : la multiplication par personne / nuit / jour est faite
    ensuite par la normalisation, jamais par le LLM. Schéma à plat (sans `$ref`) : plus sûr pour
    la sortie contrainte d'Ollama."""
    texte, entier, booleen = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
    besoin = {"type": "string", "enum": list(jeu_nlu.BESOINS)}
    proprietes = {
        "destination": _nullable({"type": "string", "enum": list(jeu_nlu.VILLES_CATALOGUE)}),
        "autres_villes": {"type": "array", "items": {"type": "string", "enum": list(jeu_nlu.VILLES_CATALOGUE)}},
        "date_debut": _nullable({"type": "string", "description": "AAAA-MM-JJ"}),
        "duree_jours": _nullable(entier),
        "nb_nuits": _nullable(entier),
        "budget_montant": _nullable({"type": "number"}),
        "budget_devise": _nullable(texte),
        "budget_base": _nullable({"type": "string", "enum": list(jeu_nlu.BASES_BUDGET)}),
        "budget_illimite": booleen,
        "langue": {"type": "string", "enum": list(jeu_nlu.LANGUES)},
        "ville_depart": _nullable(texte),
        "vol": besoin, "voiture": besoin, "transfert": besoin,
        "vol_direct": _nullable(booleen),
        "boite_auto": _nullable(booleen),
        "priorite": _nullable({"type": "string", "enum": list(jeu_nlu.PRIORITES)}),
    }
    proprietes.update(schema_llm_hybride()["properties"])
    return {"type": "object", "properties": proprietes, "required": list(proprietes),
            "additionalProperties": False}
