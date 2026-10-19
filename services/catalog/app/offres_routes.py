"""Offres de voyage — lecture publique (site client).

Les routes `/stays`, `/flights`, `/car-rentals`, `/transfers` de `travel_routes`
restent réservées aux admins (CRUD complet, offres inactives comprises). Ici,
en lecture seule et sans authentification, seules les offres réservables :
séjours actifs, voitures disponibles, transferts actifs, vols à venir avec des
places. Exposées par le gateway sous `/api/v1/offres/*`.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CarRental, Flight, Stay, Transfer
from app.travel_routes import CarRentalRead, FlightRead, StayRead, TransferRead

offres_router = APIRouter(prefix="/offres", tags=["Offres de voyage — public"])

# Un vol se réserve au plus tôt quelques heures avant le départ.
DELAI_MIN_VOL = timedelta(hours=3)
MAX_VOLS = 200


def _commence_par(colonne, ville: str | None):
    """Filtre « Djerba, … » : la localisation commence par la ville choisie."""
    return func.lower(colonne).like(f"{ville.lower()}%") if ville else None


@offres_router.get("/sejours", response_model=list[StayRead])
def sejours(
    db: Session = Depends(get_db),
    ville: str | None = Query(None, max_length=100),
    type: str | None = Query(None, pattern="^(hotel|riad|maison_hotes|appartement)$"),
    voyageurs: int | None = Query(None, ge=1, le=50),
):
    stmt = select(Stay).where(Stay.actif.is_(True))
    if ville:
        stmt = stmt.where(_commence_par(Stay.localisation, ville))
    if type:
        stmt = stmt.where(Stay.type == type)
    if voyageurs:
        stmt = stmt.where(Stay.capacite >= voyageurs)
    return db.scalars(stmt.order_by(Stay.prix_nuit, Stay.id)).all()


@offres_router.get("/sejours/{stay_id}", response_model=StayRead)
def sejour(stay_id: int, db: Session = Depends(get_db)):
    stay = db.get(Stay, stay_id)
    if not stay or not stay.actif:
        raise HTTPException(status_code=404, detail="Séjour introuvable")
    return stay


@offres_router.get("/vols", response_model=list[FlightRead])
def vols(
    db: Session = Depends(get_db),
    depart: str | None = Query(None, pattern="^[A-Z]{3}$", description="Code IATA de départ"),
    arrivee: str | None = Query(None, pattern="^[A-Z]{3}$", description="Code IATA d'arrivée"),
    jour: date | None = Query(None, description="Date de départ (AAAA-MM-JJ)"),
    classe: str | None = Query(None, pattern="^(economy|business)$"),
    limite: int = Query(MAX_VOLS, ge=1, le=1000, description="Nombre maximal de vols renvoyés"),
):
    stmt = select(Flight).where(
        Flight.depart_le >= datetime.now() + DELAI_MIN_VOL,
        Flight.places_disponibles > 0,
    )
    if depart:
        stmt = stmt.where(Flight.aeroport_depart == depart)
    if arrivee:
        stmt = stmt.where(Flight.aeroport_arrivee == arrivee)
    if jour:
        debut = datetime.combine(jour, datetime.min.time())
        stmt = stmt.where(Flight.depart_le >= debut, Flight.depart_le < debut + timedelta(days=1))
    if classe:
        stmt = stmt.where(Flight.classe == classe)
    return db.scalars(stmt.order_by(Flight.depart_le, Flight.prix).limit(limite)).all()


@offres_router.get("/voitures", response_model=list[CarRentalRead])
def voitures(
    db: Session = Depends(get_db),
    ville: str | None = Query(None, max_length=100),
    categorie: str | None = Query(None, pattern="^(economique|compacte|suv|van)$"),
):
    stmt = select(CarRental).where(CarRental.disponible.is_(True))
    if ville:
        stmt = stmt.where(_commence_par(CarRental.localisation, ville))
    if categorie:
        stmt = stmt.where(CarRental.categorie == categorie)
    return db.scalars(stmt.order_by(CarRental.prix_jour, CarRental.id)).all()


@offres_router.get("/transferts", response_model=list[TransferRead])
def transferts(
    db: Session = Depends(get_db),
    depart: str | None = Query(None, max_length=255, description="Début du lieu de départ"),
):
    stmt = select(Transfer).where(Transfer.actif.is_(True))
    if depart:
        stmt = stmt.where(_commence_par(Transfer.depart, depart))
    return db.scalars(stmt.order_by(Transfer.depart, Transfer.prix, Transfer.id)).all()
