"""Validation humaine des tags IA (étape 2 du moteur IA) — JWT admin requis.

Démarche « weak labelling + human in the loop » : un script propose des tags
(scripts/pre_etiqueter.py → CSV → scripts/importer_propositions.py), l'admin
les relit, corrige et valide ici. Exposé par le gateway sous /api/v1/etiquetage.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from voyara_common.auth import require_admin
from voyara_common.pagination import paginate

from app.database import get_db
from app.models import Activity, Category
from app.tags_ia import TagsIAValidation, tags_de

etiquetage_router = APIRouter(
    prefix="/etiquetage",
    tags=["Catalogue — tags IA"],
    dependencies=[Depends(require_admin)],
)

CHAMPS_TAGS = ("themes", "public", "niveau_marche", "interieur", "moment_ideal")


def _ligne(a: Activity) -> dict:
    return {
        "id": a.id,
        "titre": a.titre,
        "titre_en": a.titre_en,
        "titre_ar": a.titre_ar,
        "description": a.description,
        "localisation": a.localisation,
        "duree": a.duree,
        "photos": a.photos,
        "statut": a.statut,
        "category": (
            {"id": a.category.id, "nom": a.category.nom,
             "nom_en": a.category.nom_en, "nom_ar": a.category.nom_ar}
            if a.category else None
        ),
        **tags_de(a),
        "tags_proposes": a.tags_proposes,
        "modifie_le": a.modifie_le.isoformat() if a.modifie_le else None,
    }


@etiquetage_router.get("/activities")
def lister(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=100),
    category_id: int | None = None,
    tags_valides: bool | None = None,
):
    stmt = select(Activity).options(joinedload(Activity.category))
    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.join(Category, Activity.category_id == Category.id, isouter=True).where(
            func.lower(Activity.titre).like(pattern)
            | func.lower(Activity.localisation).like(pattern)
            | func.lower(func.coalesce(Category.nom, "")).like(pattern)
        )
    if category_id:
        stmt = stmt.where(Activity.category_id == category_id)
    if tags_valides is not None:
        stmt = stmt.where(Activity.tags_valides.is_(tags_valides))

    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    activites = db.scalars(
        stmt.order_by(Activity.id).offset((page - 1) * size).limit(size)
    ).unique().all()
    return paginate(total, page, size, [_ligne(a) for a in activites])


@etiquetage_router.put("/activities/{activity_id}")
def enregistrer(activity_id: int, payload: TagsIAValidation, db: Session = Depends(get_db)):
    """Enregistre les tags relus. `tags_valides=false` garde l'activité « à valider »."""
    activite = db.get(Activity, activity_id)
    if not activite:
        raise HTTPException(status_code=404, detail="Activité introuvable")
    for champ, valeur in payload.model_dump().items():
        setattr(activite, champ, valeur)
    db.commit()
    db.refresh(activite)
    return _ligne(activite)


@etiquetage_router.get("/stats")
def statistiques(db: Session = Depends(get_db)):
    """Avancement de la validation et écart entre proposition et validation.

    `corrections` : pour chaque champ, part des activités validées (et pré-
    étiquetées) dont l'humain a changé la valeur proposée. C'est la mesure de
    qualité du pré-étiquetage — elle n'a de sens qu'après validation humaine."""
    activites = db.scalars(select(Activity)).all()
    publiees = [a for a in activites if a.statut == "publiee"]
    comparables = [a for a in activites if a.tags_valides and a.tags_proposes]

    def differe(a: Activity, champ: str) -> bool:
        propose, valide = a.tags_proposes.get(champ), getattr(a, champ)
        if isinstance(valide, list):
            return sorted(propose or []) != sorted(valide)
        return propose != valide

    corrections = {
        champ: (
            round(sum(differe(a, champ) for a in comparables) / len(comparables), 3)
            if comparables else None
        )
        for champ in CHAMPS_TAGS
    }
    sources: dict[str, int] = {}
    for a in activites:
        if a.tags_proposes:
            source = str(a.tags_proposes.get("source", "inconnue"))
            sources[source] = sources.get(source, 0) + 1
    return {
        "total": len(activites),
        "publiees": len(publiees),
        "validees": sum(a.tags_valides for a in activites),
        "publiees_validees": sum(a.tags_valides for a in publiees),
        "avec_proposition": sum(1 for a in activites if a.tags_proposes),
        "sources": sources,
        "comparables": len(comparables),
        "corrections": corrections,
        "inchangees": sum(
            1 for a in comparables if not any(differe(a, c) for c in CHAMPS_TAGS)
        ),
    }
