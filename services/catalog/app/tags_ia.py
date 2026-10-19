"""Vocabulaire et schémas des attributs IA d'une activité (étape 2 du moteur IA).

Source unique des valeurs autorisées : les contraintes CHECK du modèle, les
schémas de l'API admin, le script de pré-étiquetage et les tests lisent tous
ces constantes. Ajouter une valeur ici suffit côté backend ; côté admin, il faut
aussi ajouter son libellé dans @voyara/i18n (fr / en / ar).
"""

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

Theme = Literal[
    "plage", "culture", "histoire", "nature", "gastronomie",
    "aventure", "detente", "shopping", "nautique", "desert",
]
Public = Literal["famille", "couple", "solo", "groupe", "enfants"]
MomentIdeal = Literal["matin", "apres_midi", "soir", "indifferent"]

THEMES: tuple[str, ...] = get_args(Theme)
PUBLICS: tuple[str, ...] = get_args(Public)
MOMENTS: tuple[str, ...] = get_args(MomentIdeal)
NIVEAUX_MARCHE: tuple[int, ...] = (1, 2, 3)  # 1 faible · 2 moyen · 3 élevé


def _sans_doublon(valeurs: list[str]) -> list[str]:
    """Dédoublonne en gardant l'ordre canonique du vocabulaire (sortie stable)."""
    return list(dict.fromkeys(valeurs))


def tags_de(activite) -> dict:
    """Attributs IA d'une activité (ORM) sous forme de dictionnaire JSON."""
    return {
        "themes": list(activite.themes or []),
        "public": list(activite.public or []),
        "niveau_marche": activite.niveau_marche,
        "interieur": activite.interieur,
        "moment_ideal": activite.moment_ideal,
        "tags_valides": bool(activite.tags_valides),
    }


class TagsIA(BaseModel):
    """Attributs IA complets — ce qu'un humain valide dans l'admin."""

    model_config = ConfigDict(extra="forbid")

    themes: list[Theme] = Field(min_length=1)
    public: list[Public] = Field(min_length=1)
    niveau_marche: int = Field(ge=1, le=3, description="1 faible, 2 moyen, 3 élevé")
    interieur: bool
    moment_ideal: MomentIdeal

    @field_validator("themes", "public")
    @classmethod
    def _dedoublonner(cls, valeurs: list[str]) -> list[str]:
        return _sans_doublon(valeurs)


class TagsIAValidation(TagsIA):
    """Corps du PUT admin : les tags + l'état de validation voulu."""

    tags_valides: bool = True
