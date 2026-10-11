"""Administration des offres de voyage : séjours, vols, voitures, transferts.

Même CRUD pour les quatre tables, généré par `_register_crud`. Tout est réservé
aux admins pour l'instant (lecture comprise) : le site client n'affiche encore
qu'une page « bientôt disponible ». Les routes publiques viendront avec lui.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from voyara_common.auth import require_admin

from app.database import Base, get_db
from app.models import CarRental, Flight, Stay, Transfer

travel_router = APIRouter(
    tags=["Offres de voyage — administration"], dependencies=[Depends(require_admin)]
)


# ---------------------------------------------------------------------------
# Schémas : `XIn` en entrée (création et modification complète), `XRead` en sortie
# ---------------------------------------------------------------------------

class StayIn(BaseModel):
    nom: str = Field(min_length=2, max_length=200)
    type: str = Field(pattern="^(hotel|riad|maison_hotes|appartement)$")
    description: str = Field(min_length=10)
    nom_en: str | None = Field(default=None, max_length=200)
    nom_ar: str | None = Field(default=None, max_length=200)
    description_en: str | None = None
    description_ar: str | None = None
    localisation: str = Field(min_length=2, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    etoiles: int | None = Field(default=None, ge=1, le=5)
    prix_nuit: float = Field(gt=0)
    capacite: int = Field(gt=0, le=50)
    equipements: str | None = None
    actif: bool = True


class StayRead(StayIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    photos: str | None = None


class FlightIn(BaseModel):
    compagnie: str = Field(min_length=2, max_length=100)
    numero_vol: str = Field(min_length=2, max_length=20)
    aeroport_depart: str = Field(pattern="^[A-Z]{3}$")
    aeroport_arrivee: str = Field(pattern="^[A-Z]{3}$")
    ville_depart: str = Field(min_length=2, max_length=100)
    ville_arrivee: str = Field(min_length=2, max_length=100)
    depart_le: datetime
    arrivee_le: datetime
    classe: str = Field(default="economy", pattern="^(economy|business)$")
    prix: float = Field(gt=0)
    # Saisi par l'admin comme capacité ; voir `_apply_flight_capacity`.
    places_totales: int = Field(ge=0, le=900)

    @model_validator(mode="after")
    def _check(self):
        if self.aeroport_depart == self.aeroport_arrivee:
            raise ValueError("Les aéroports de départ et d'arrivée doivent différer")
        if self.arrivee_le <= self.depart_le:
            raise ValueError("L'arrivée doit être postérieure au départ")
        return self


class FlightRead(FlightIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    places_disponibles: int


class CarRentalIn(BaseModel):
    marque: str = Field(min_length=2, max_length=100)
    modele: str = Field(min_length=1, max_length=100)
    categorie: str = Field(pattern="^(economique|compacte|suv|van)$")
    transmission: str = Field(pattern="^(manuelle|automatique)$")
    carburant: str = Field(pattern="^(essence|diesel|hybride|electrique)$")
    nb_places: int = Field(ge=2, le=9)
    agence: str = Field(min_length=2, max_length=150)
    localisation: str = Field(min_length=2, max_length=255)
    prix_jour: float = Field(gt=0)
    disponible: bool = True


class CarRentalRead(CarRentalIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    photos: str | None = None


class TransferIn(BaseModel):
    depart: str = Field(min_length=2, max_length=255)
    arrivee: str = Field(min_length=2, max_length=255)
    type_vehicule: str = Field(pattern="^(taxi|grand_taxi|berline|van|minibus)$")
    capacite: int = Field(gt=0, le=30)
    bagages: int = Field(default=0, ge=0, le=30)
    duree: int = Field(gt=0, description="Durée en minutes")
    prix: float = Field(gt=0)
    description: str | None = None
    actif: bool = True


class TransferRead(TransferIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# CRUD générique
# ---------------------------------------------------------------------------

def _apply_flight_capacity(flight: Flight, capacity: int) -> None:
    """Même règle que les créneaux d'activité : modifier la capacité décale
    les places restantes du même delta, bornées à [0, capacité]."""
    delta = capacity - (flight.places_totales or 0)
    flight.places_totales = capacity
    flight.places_disponibles = max(0, min(capacity, (flight.places_disponibles or 0) + delta))


def _register_crud(
    path: str,
    model: type[Base],
    schema_in: type[BaseModel],
    schema_read: type[BaseModel],
    label: str,
    order_by,
) -> None:
    def get_or_404(db: Session, obj_id: int):
        obj = db.get(model, obj_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{label} introuvable")
        return obj

    def apply(obj, payload: BaseModel) -> None:
        data = payload.model_dump()
        if model is Flight:
            _apply_flight_capacity(obj, data.pop("places_totales"))
        for key, value in data.items():
            setattr(obj, key, value)

    @travel_router.get(path, response_model=list[schema_read], name=f"list_{model.__tablename__}")
    def list_items(db: Session = Depends(get_db)):
        return db.scalars(select(model).order_by(order_by)).all()

    @travel_router.get(
        f"{path}/{{item_id}}", response_model=schema_read, name=f"get_{model.__tablename__}"
    )
    def get_item(item_id: int, db: Session = Depends(get_db)):
        return get_or_404(db, item_id)

    @travel_router.post(
        path,
        response_model=schema_read,
        status_code=status.HTTP_201_CREATED,
        name=f"create_{model.__tablename__}",
    )
    def create_item(payload: schema_in, db: Session = Depends(get_db)):  # type: ignore[valid-type]
        obj = model()
        apply(obj, payload)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @travel_router.put(
        f"{path}/{{item_id}}", response_model=schema_read, name=f"update_{model.__tablename__}"
    )
    def update_item(item_id: int, payload: schema_in, db: Session = Depends(get_db)):  # type: ignore[valid-type]
        obj = get_or_404(db, item_id)
        apply(obj, payload)
        db.commit()
        db.refresh(obj)
        return obj

    @travel_router.delete(
        f"{path}/{{item_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
        name=f"delete_{model.__tablename__}",
    )
    def delete_item(item_id: int, db: Session = Depends(get_db)):
        db.delete(get_or_404(db, item_id))
        db.commit()


_register_crud("/stays", Stay, StayIn, StayRead, "Séjour", Stay.nom)
_register_crud("/flights", Flight, FlightIn, FlightRead, "Vol", Flight.depart_le)
_register_crud("/car-rentals", CarRental, CarRentalIn, CarRentalRead, "Voiture", CarRental.marque)
_register_crud("/transfers", Transfer, TransferIn, TransferRead, "Transfert", Transfer.depart)
