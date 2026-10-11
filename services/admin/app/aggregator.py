"""Agrégation des données des autres services pour le dashboard admin.

C'est LE point clé de l'architecture microservices : l'ancien admin_service
faisait des jointures SQL entre users/bookings/payments/activities ; ici on
compose les mêmes réponses par appels aux endpoints internes des services
propriétaires des données (pattern API Composition / BFF).
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from voyara_common.internal import ServiceClient

from app.config import settings

logger = logging.getLogger(__name__)

auth = ServiceClient(settings.AUTH_SERVICE_URL)
catalog = ServiceClient(settings.CATALOG_SERVICE_URL)
booking = ServiceClient(settings.BOOKING_SERVICE_URL)
payment = ServiceClient(settings.PAYMENT_SERVICE_URL)


def _unavailable(service: str) -> HTTPException:
    return HTTPException(
        status_code=503, detail=f"Le service '{service}' est momentanément indisponible"
    )


async def _call(service_name: str, coro):
    try:
        return await coro
    except httpx.HTTPError:
        logger.exception("Appel interne échoué vers %s", service_name)
        raise _unavailable(service_name)


async def _users_by_ids(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    data = await _call(
        "auth", auth.get("/internal/users/batch", params={"ids": ",".join(map(str, ids))})
    )
    return {u["id"]: u for u in data}


async def _activities_by_ids(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    data = await _call(
        "catalog",
        catalog.get("/internal/activities/batch", params={"ids": ",".join(map(str, ids))}),
    )
    return {a["id"]: a for a in data}


def _client_name(user: dict | None) -> str:
    if not user:
        return "—"
    return f"{user.get('prenom', '')} {user.get('nom', '')}".strip() or "—"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

async def dashboard_stats() -> dict:
    booking_stats, user_stats, activity_stats, revenue_raw, recent_raw = await asyncio.gather(
        _call("booking", booking.get("/internal/stats/bookings")),
        _call("auth", auth.get("/internal/stats/users")),
        _call("catalog", catalog.get("/internal/stats/activities")),
        _call("payment", payment.get("/internal/stats/revenue")),
        _call("booking", booking.get("/internal/bookings/recent", params={"limit": 8})),
    )

    # Fallback historique : aucun paiement enregistré → somme des réservations confirmées
    total = revenue_raw["total"]
    confirmed_count = booking_stats["confirmed"]
    if total == 0.0:
        fallback = await _call("booking", booking.get("/internal/stats/confirmed-revenue"))
        total = round(fallback["total"], 2)

    revenue = {
        "total": round(total, 2),
        "last_30_days": revenue_raw["last_30_days"],
        "pending": revenue_raw["pending"],
        "average_basket": round(total / confirmed_count, 2) if confirmed_count else 0.0,
    }

    # Enrichissement des réservations récentes (noms + titres)
    user_ids = sorted({b["user_id"] for b in recent_raw})
    activity_ids = sorted({b["activity_id"] for b in recent_raw})
    users, activities = await asyncio.gather(
        _users_by_ids(user_ids), _activities_by_ids(activity_ids)
    )

    recent = [
        {
            "id": b["id"],
            "client": _client_name(users.get(b["user_id"])),
            "email": (users.get(b["user_id"]) or {}).get("email", "—"),
            "activity": (activities.get(b["activity_id"]) or {}).get("titre", "—"),
            "statut": b["statut"],
            "montant_total": b["montant_total"],
            "date_reservation": b["date_reservation"],
        }
        for b in recent_raw
    ]

    return {
        "bookings": booking_stats,
        "revenue": revenue,
        "users": user_stats,
        "activities": activity_stats,
        "recent_bookings": recent,
        "generated_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# Listes paginées
# ---------------------------------------------------------------------------

async def list_users(page: int, size: int, search: str | None) -> dict:
    params: dict = {"page": page, "size": size}
    if search:
        params["search"] = search
    return await _call("auth", auth.get("/internal/users", params=params))


async def list_bookings(page: int, size: int, statut: str | None) -> dict:
    params: dict = {"page": page, "size": size}
    if statut:
        params["statut"] = statut
    result = await _call("booking", booking.get("/internal/bookings", params=params))

    rows = result["items"]
    users, activities = await asyncio.gather(
        _users_by_ids(sorted({b["user_id"] for b in rows})),
        _activities_by_ids(sorted({b["activity_id"] for b in rows})),
    )

    result["items"] = [
        {
            "id": b["id"],
            "user_id": b["user_id"],
            "client": _client_name(users.get(b["user_id"])),
            "email": (users.get(b["user_id"]) or {}).get("email", "—"),
            "activity_id": b["activity_id"],
            "activity": (activities.get(b["activity_id"]) or {}).get("titre", "—"),
            "statut": b["statut"],
            "montant_total": b["montant_total"],
            "date_reservation": b["date_reservation"],
        }
        for b in rows
    ]
    return result


async def list_activities(page: int, size: int) -> dict:
    result = await _call("catalog", catalog.get("/internal/activities", params={"page": page, "size": size}))

    rows = result["items"]
    ids = [a["id"] for a in rows]
    counts: dict = {}
    if ids:
        counts = await _call(
            "booking",
            booking.get(
                "/internal/bookings/count-by-activity", params={"ids": ",".join(map(str, ids))}
            ),
        )

    result["items"] = [
        {**a, "bookings_count": int(counts.get(str(a["id"]), 0))}
        for a in rows
    ]
    return result


async def list_payments(page: int, size: int) -> dict:
    result = await _call("payment", payment.get("/internal/payments", params={"page": page, "size": size}))

    rows = result["items"]
    booking_ids = sorted({p["booking_id"] for p in rows})
    bookings_map: dict[int, dict] = {}
    if booking_ids:
        data = await _call(
            "booking",
            booking.get("/internal/bookings/batch", params={"ids": ",".join(map(str, booking_ids))}),
        )
        bookings_map = {b["id"]: b for b in data}

    user_ids = sorted({b["user_id"] for b in bookings_map.values()})
    users = await _users_by_ids(user_ids)

    result["items"] = [
        {
            **p,
            "client": _client_name(
                users.get((bookings_map.get(p["booking_id"]) or {}).get("user_id"))
            ),
        }
        for p in rows
    ]
    return result
