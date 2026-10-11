from datetime import date, time

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategoryRead(ORMModel):
    id: int
    nom: str
    nom_en: str | None = None
    nom_ar: str | None = None


class ActivityRead(ORMModel):
    id: int
    titre: str
    description: str
    titre_en: str | None = None
    titre_ar: str | None = None
    description_en: str | None = None
    description_ar: str | None = None
    prix: float
    duree: int
    localisation: str
    latitude: float | None = None
    longitude: float | None = None
    photos: str | None = None
    category_id: int
    category: CategoryRead | None = None


class AvailabilityRead(ORMModel):
    id: int
    activity_id: int
    date: date
    heure: time
    places_disponibles: int
    # Capacité d'origine : permet au client d'afficher « 6 places sur 8 ».
    places_totales: int = 0
