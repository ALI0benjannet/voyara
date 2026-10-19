"""Schémas de réponse — identiques à l'ancien backend/app/schemas/admin.py
pour que le frontend admin fonctionne sans aucune modification."""

from datetime import datetime

from pydantic import BaseModel

from voyara_common.pagination import Page  # noqa: F401  (ré-export)


# ---------- Statistiques ----------

class BookingStats(BaseModel):
    total: int
    pending: int
    confirmed: int
    cancelled: int
    last_30_days: int


class RevenueStats(BaseModel):
    total: float
    last_30_days: float
    pending: float
    average_basket: float


class UserStats(BaseModel):
    total: int
    active: int
    verified: int
    admins: int
    new_30_days: int


class CategoryCount(BaseModel):
    nom: str
    total: int


class OffersStats(BaseModel):
    sejours: int = 0
    vols_a_venir: int = 0
    voitures: int = 0
    transferts: int = 0


class ActivityStats(BaseModel):
    total: int
    categories: int
    upcoming_availabilities: int
    # Champs ajoutés le 19/10/2026 : valeurs par défaut si le catalog est plus ancien.
    en_attente: int = 0
    par_categorie: list[CategoryCount] = []
    offres: OffersStats = OffersStats()


class RecentBooking(BaseModel):
    id: int
    client: str
    email: str
    activity: str
    statut: str
    montant_total: float
    date_reservation: datetime


class DashboardStats(BaseModel):
    bookings: BookingStats
    revenue: RevenueStats
    users: UserStats
    activities: ActivityStats
    recent_bookings: list[RecentBooking]
    generated_at: datetime


# ---------- Listes paginées ----------

class AdminUserRow(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str
    role: str
    is_active: bool
    is_verified: bool
    phone: str | None = None
    date_inscription: datetime


class AdminBookingRow(BaseModel):
    id: int
    user_id: int
    client: str
    email: str
    activity_id: int
    activity: str
    statut: str
    montant_total: float
    date_reservation: datetime


class AdminActivityRow(BaseModel):
    id: int
    titre: str
    prix: float
    duree: int
    localisation: str
    category: str | None = None
    statut: str = "publiee"
    photos: str | None = None
    bookings_count: int


class AdminPaymentRow(BaseModel):
    id: int
    booking_id: int
    client: str
    montant: float
    type: str
    methode: str
    statut: str
    date_paiement: datetime
