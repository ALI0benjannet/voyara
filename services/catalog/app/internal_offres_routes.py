"""Offres de voyage pour le moteur IA (étape 2-bis) — routes internes uniquement.

- hébergements : export paginé avec `modifie_depuis`, comme /internal/activities/export
  (ils rejoindront l'index sémantique du service ai, étape 5) ;
- vols, voitures, transferts : **recherche structurée en direct**, sans index : prix,
  places et horaires changent souvent et se cherchent par critères exacts. La source
  de vérité reste catalog, interrogée au moment de la demande.

Protégées par `require_internal_key`, jamais exposées par le gateway. Prix en DT,
dates ISO 8601 (avec décalage quand le fuseau de l'aéroport est connu), aucun champ
personnel. Le moteur IA propose ces offres ; il ne réserve ni ne paie jamais.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from voyara_common.internal import require_internal_key
from voyara_common.pagination import paginate

from app.database import get_db
from app.lieux import Lieu, resoudre_lieu, ville_de_localisation
from app.models import Aeroport, CarRental, Flight, Stay, Transfer
from app.offres_routes import DELAI_MIN_VOL
from app.recherche_transport import (
    ATTENTE_MAX,
    ATTENTE_MIN,
    CLES_TRI,
    DEVISE,
    composer_correspondances,
    fenetre_jours,
    itineraire,
    nb_jours_location,
)
from app.routers import _vers_utc

internal_offres_router = APIRouter(
    prefix="/internal",
    tags=["Offres de voyage — moteur IA (interne)"],
    dependencies=[Depends(require_internal_key)],
)

TAILLE_MAX = 100


def _page(items: list, page: int, size: int) -> dict:
    """Pagination d'une liste déjà triée (résultats composés en Python)."""
    return paginate(len(items), page, size, items[(page - 1) * size: page * size])


def _aeroports(db: Session) -> list[Aeroport]:
    return db.scalars(select(Aeroport).order_by(Aeroport.code_iata)).all()


def _villes_connues(db: Session) -> set[str]:
    villes = set(db.scalars(select(CarRental.ville).distinct()))
    villes |= set(db.scalars(select(Transfer.ville_depart).distinct()))
    villes |= set(db.scalars(select(Transfer.ville_arrivee).distinct()))
    villes |= set(db.scalars(select(Flight.ville_depart).distinct()))
    return {v for v in villes if v}


# ---------------------------------------------------------------------------
# Référentiel et hébergements
# ---------------------------------------------------------------------------


@internal_offres_router.get("/airports")
def aeroports(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=TAILLE_MAX),
):
    """Référentiel des aéroports (code IATA, nom, ville desservie, pays, fuseau)."""
    lignes = [
        {"code_iata": a.code_iata, "nom": a.nom, "ville": a.ville, "pays": a.pays, "fuseau": a.fuseau}
        for a in _aeroports(db)
    ]
    return _page(lignes, page, size)


@internal_offres_router.get("/stays/export")
def export_stays(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    modifie_depuis: datetime | None = Query(
        None,
        description="ISO 8601 ; sans fuseau = UTC. Renvoie les séjours modifiés à partir de "
        "cet instant (borne incluse : l'appelant dédoublonne par id).",
    ),
    actif: bool | None = None,
):
    """Export des hébergements pour l'index sémantique du moteur IA (étape 5).

    Inactifs compris par défaut, pour que l'appelant apprenne les retraits ; un séjour
    supprimé n'apparaît plus (resynchronisation complète de temps en temps). `etoiles`
    est le seul indicateur de qualité : les avis (service review) ne portent que sur
    les activités, aucune note n'est inventée."""
    stmt = select(Stay)
    if modifie_depuis is not None:
        stmt = stmt.where(Stay.modifie_le >= _vers_utc(modifie_depuis))
    if actif is not None:
        stmt = stmt.where(Stay.actif.is_(actif))
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    sejours = db.scalars(
        stmt.order_by(Stay.modifie_le, Stay.id).offset((page - 1) * size).limit(size)
    ).all()
    items = [
        {
            "id": s.id,
            "nom": s.nom,
            "nom_en": s.nom_en,
            "nom_ar": s.nom_ar,
            "type": s.type,
            "description": s.description,
            "description_en": s.description_en,
            "description_ar": s.description_ar,
            "localisation": s.localisation,
            "ville": ville_de_localisation(s.localisation),
            "latitude": s.latitude,
            "longitude": s.longitude,
            "etoiles": s.etoiles,
            "prix_nuit": float(s.prix_nuit),
            "devise": DEVISE,
            "capacite": s.capacite,
            "equipements": [e.strip() for e in (s.equipements or "").split(",") if e.strip()],
            "photos": s.photos,
            "actif": s.actif,
            "modifie_le": s.modifie_le.isoformat(),
        }
        for s in sejours
    ]
    return paginate(total, page, size, items)


# ---------------------------------------------------------------------------
# Vols : directs + correspondances à 1 escale
# ---------------------------------------------------------------------------


def _codes_vol(lieu: Lieu, db: Session) -> set[str]:
    """Aéroports d'un lieu de vol ; 404 si le lieu n'en désigne aucun."""
    codes = set(lieu.codes)
    if lieu.mode == "ville" and lieu.ville:
        # Ville absente du référentiel mais présente dans les vols (saisie admin).
        codes |= set(db.scalars(select(Flight.aeroport_depart).where(Flight.ville_depart == lieu.ville)))
        codes |= set(db.scalars(select(Flight.aeroport_arrivee).where(Flight.ville_arrivee == lieu.ville)))
    if not codes:
        raise HTTPException(status_code=404, detail=f"Lieu inconnu : {lieu.saisie}")
    return codes


@internal_offres_router.get("/flights/search")
def rechercher_vols(
    db: Session = Depends(get_db),
    origine: str = Query(..., min_length=2, max_length=100, description="Code IATA ou ville"),
    destination: str = Query(..., min_length=2, max_length=100, description="Code IATA ou ville"),
    date_vol: date = Query(..., alias="date", description="Date de départ souhaitée (AAAA-MM-JJ)"),
    tolerance_jours: int = Query(0, ge=0, le=3, description="± N jours autour de la date"),
    nb_passagers: int = Query(1, ge=1, le=9),
    classe: str | None = Query(None, pattern="^(economy|business)$"),
    escales_max: int = Query(1, ge=0, le=1),
    tri: str = Query("pertinence", pattern="^(pertinence|prix|depart|duree)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=TAILLE_MAX),
):
    """Vols aller simple : chaque tronçon a au moins `nb_passagers` places et part au
    plus tôt dans `DELAI_MIN_VOL`. Un vol complet n'est jamais renvoyé."""
    referentiel = _aeroports(db)
    codes_connus = set(db.scalars(select(Flight.aeroport_depart).distinct()))
    villes = _villes_connues(db)
    depart = _codes_vol(resoudre_lieu(origine, referentiel, villes, codes_connus), db)
    arrivee = _codes_vol(resoudre_lieu(destination, referentiel, villes, codes_connus), db)
    if depart & arrivee:
        raise HTTPException(status_code=422, detail="L'origine et la destination doivent différer")
    fuseaux = {a.code_iata: a.fuseau for a in referentiel}

    debut, fin = fenetre_jours(date_vol, tolerance_jours)
    reservable = [
        Flight.places_disponibles >= nb_passagers,
        Flight.depart_le >= datetime.now() + DELAI_MIN_VOL,
    ]
    if classe:
        reservable.append(Flight.classe == classe)

    def vols(*conditions):
        return db.scalars(select(Flight).where(*reservable, *conditions)).all()

    dans_la_fenetre = (Flight.depart_le >= debut, Flight.depart_le < fin)
    resultats = [
        itineraire([v], date_vol, nb_passagers, fuseaux)
        for v in vols(Flight.aeroport_depart.in_(depart), Flight.aeroport_arrivee.in_(arrivee),
                      *dans_la_fenetre)
    ]
    if escales_max >= 1:
        premiers = vols(Flight.aeroport_depart.in_(depart), Flight.aeroport_arrivee.not_in(arrivee),
                        *dans_la_fenetre)
        if premiers:
            seconds = vols(
                Flight.aeroport_depart.in_({v.aeroport_arrivee for v in premiers}),
                Flight.aeroport_arrivee.in_(arrivee),
                Flight.depart_le >= min(v.arrivee_le for v in premiers) + ATTENTE_MIN,
                Flight.depart_le <= max(v.arrivee_le for v in premiers) + ATTENTE_MAX,
            )
            resultats += [
                itineraire([v1, v2], date_vol, nb_passagers, fuseaux)
                for v1, v2 in composer_correspondances(premiers, seconds)
            ]
    resultats.sort(key=CLES_TRI[tri])
    return _page(resultats, page, size)


# ---------------------------------------------------------------------------
# Voitures de location
# ---------------------------------------------------------------------------


def _filtre_lieu(stmt, lieu: Lieu, colonne_aeroport, colonne_ville):
    """IATA -> colonne aéroport ; ville connue -> colonne ville ; texte : filtré en Python."""
    if lieu.mode == "aeroport":
        return stmt.where(colonne_aeroport.in_(lieu.codes))
    if lieu.mode == "ville":
        return stmt.where(colonne_ville == lieu.ville)
    return stmt


@internal_offres_router.get("/car-rentals/search")
def rechercher_voitures(
    db: Session = Depends(get_db),
    lieu_prise: str = Query(..., min_length=2, max_length=255, description="Code IATA, ville ou lieu"),
    lieu_retour: str | None = Query(None, min_length=2, max_length=255, description="Défaut : lieu de prise"),
    prise_le: datetime = Query(..., description="ISO 8601"),
    retour_le: datetime = Query(..., description="ISO 8601, après la prise"),
    nb_places: int = Query(1, ge=1, le=9),
    transmission: str | None = Query(None, pattern="^(manuelle|automatique)$"),
    categorie: str | None = Query(None, pattern="^(economique|compacte|suv|van)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=TAILLE_MAX),
):
    """Voitures disponibles. Le catalogue ne connaît pas l'aller simple : le retour doit
    se faire dans la ville de prise (sinon aucun résultat). `disponible` est un simple
    indicateur : il n'existe pas encore de stock par date (pas de réservation de voiture)."""
    if retour_le <= prise_le:
        raise HTTPException(status_code=422, detail="Le retour doit être postérieur à la prise")
    referentiel, villes = _aeroports(db), _villes_connues(db)
    prise = resoudre_lieu(lieu_prise, referentiel, villes)
    retour = resoudre_lieu(lieu_retour, referentiel, villes) if lieu_retour else prise

    stmt = select(CarRental).where(CarRental.disponible.is_(True), CarRental.nb_places >= nb_places)
    if transmission:
        stmt = stmt.where(CarRental.transmission == transmission)
    if categorie:
        stmt = stmt.where(CarRental.categorie == categorie)
    stmt = _filtre_lieu(stmt, prise, CarRental.aeroport, CarRental.ville)
    voitures = db.scalars(stmt.order_by(CarRental.prix_jour, CarRental.id)).all()

    def retour_possible(v: CarRental) -> bool:
        if retour.ville:
            return retour.ville == v.ville
        return retour.correspond_au_texte(v.localisation, v.agence)

    if prise.mode == "texte":
        voitures = [v for v in voitures if prise.correspond_au_texte(v.localisation, v.agence)]
    voitures = [v for v in voitures if retour_possible(v)]

    nb_jours = nb_jours_location(prise_le, retour_le)
    items = [
        {
            "id": v.id,
            "marque": v.marque,
            "modele": v.modele,
            "categorie": v.categorie,
            "transmission": v.transmission,
            "carburant": v.carburant,
            "nb_places": v.nb_places,
            "agence": v.agence,
            "localisation": v.localisation,
            "ville": v.ville,
            "aeroport": v.aeroport,
            "photos": v.photos,
            "prise_le": prise_le.isoformat(),
            "retour_le": retour_le.isoformat(),
            "nb_jours": nb_jours,
            "prix_jour": float(v.prix_jour),
            "prix_total": round(float(v.prix_jour) * nb_jours, 2),
            "devise": DEVISE,
        }
        for v in voitures
    ]
    return _page(items, page, size)


# ---------------------------------------------------------------------------
# Transferts
# ---------------------------------------------------------------------------


@internal_offres_router.get("/transfers/search")
def rechercher_transferts(
    db: Session = Depends(get_db),
    depart: str = Query(..., min_length=2, max_length=255, description="Code IATA, ville ou lieu"),
    arrivee: str = Query(..., min_length=2, max_length=255, description="Code IATA, ville ou lieu"),
    date_heure: datetime = Query(..., description="Prise en charge, ISO 8601"),
    nb_passagers: int = Query(1, ge=1, le=30),
    bagages: int = Query(0, ge=0, le=30),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=TAILLE_MAX),
):
    """Transferts avec chauffeur dans le sens demandé (le sens inverse n'est pas déduit :
    son prix n'est pas connu). Prix par véhicule, pour un véhicule de capacité suffisante."""
    referentiel, villes = _aeroports(db), _villes_connues(db)
    lieu_depart = resoudre_lieu(depart, referentiel, villes)
    lieu_arrivee = resoudre_lieu(arrivee, referentiel, villes)

    stmt = select(Transfer).where(
        Transfer.actif.is_(True), Transfer.capacite >= nb_passagers, Transfer.bagages >= bagages
    )
    stmt = _filtre_lieu(stmt, lieu_depart, Transfer.aeroport_depart, Transfer.ville_depart)
    stmt = _filtre_lieu(stmt, lieu_arrivee, Transfer.aeroport_arrivee, Transfer.ville_arrivee)
    transferts = db.scalars(stmt.order_by(Transfer.prix, Transfer.duree, Transfer.id)).all()
    if lieu_depart.mode == "texte":
        transferts = [t for t in transferts if lieu_depart.correspond_au_texte(t.depart)]
    if lieu_arrivee.mode == "texte":
        transferts = [t for t in transferts if lieu_arrivee.correspond_au_texte(t.arrivee)]

    items = [
        {
            "id": t.id,
            "depart": t.depart,
            "arrivee": t.arrivee,
            "ville_depart": t.ville_depart,
            "ville_arrivee": t.ville_arrivee,
            "aeroport_depart": t.aeroport_depart,
            "aeroport_arrivee": t.aeroport_arrivee,
            "type_vehicule": t.type_vehicule,
            "capacite": t.capacite,
            "bagages": t.bagages,
            "duree_min": t.duree,
            "description": t.description,
            "depart_le": date_heure.isoformat(),
            "arrivee_estimee": (date_heure + timedelta(minutes=t.duree)).isoformat(),
            "nb_passagers": nb_passagers,
            "prix_total": float(t.prix),
            "prix_par_passager": round(float(t.prix) / nb_passagers, 2),
            "devise": DEVISE,
        }
        for t in transferts
    ]
    return _page(items, page, size)
