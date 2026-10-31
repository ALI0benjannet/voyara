"""Client catalog : paramètres envoyés et erreurs typées, catalog simulé par httpx.MockTransport."""

from datetime import date, datetime, timezone

import httpx
import pytest

from voyara_common.internal import INTERNAL_HEADER

from app.clients.catalog import (
    CatalogAccesRefuse,
    CatalogIndisponible,
    CatalogLieuInconnu,
    CatalogRequeteInvalide,
    ClientCatalog,
)

pytestmark = pytest.mark.anyio
PAGE_VIDE = {"items": [], "total": 0, "page": 1, "size": 20, "pages": 0}


def catalog(gerer):
    requetes = []

    def enregistrer(requete: httpx.Request) -> httpx.Response:
        requetes.append(requete)
        return gerer(requete)

    return ClientCatalog("http://catalog.test", transport=httpx.MockTransport(enregistrer)), requetes


async def test_recherche_vols_parametres_et_cle():
    client, requetes = catalog(lambda r: httpx.Response(200, json=PAGE_VIDE))
    assert await client.rechercher_vols("Paris", "DJE", date(2026, 11, 7), tolerance_jours=1,
                                        nb_passagers=2) == PAGE_VIDE
    requete = requetes[0]
    assert requete.url.path == "/internal/flights/search"
    assert dict(requete.url.params) == {
        "origine": "Paris", "destination": "DJE", "date": "2026-11-07", "tolerance_jours": "1",
        "nb_passagers": "2", "escales_max": "1", "tri": "pertinence", "page": "1", "size": "20"}
    assert requete.headers[INTERNAL_HEADER]  # clé interne toujours envoyée


async def test_parametres_vides_non_envoyes_et_dates_iso():
    client, requetes = catalog(lambda r: httpx.Response(200, json=PAGE_VIDE))
    await client.rechercher_voitures("DJE", datetime(2026, 11, 7, 10), datetime(2026, 11, 10, 10))
    await client.rechercher_transferts("DJE", "Midoun", datetime(2026, 11, 7, 12, 30), nb_passagers=4)
    await client.exporter_sejours(modifie_depuis=datetime(2026, 10, 1, tzinfo=timezone.utc))
    voitures, transferts, sejours = (dict(r.url.params) for r in requetes)
    assert "lieu_retour" not in voitures and voitures["prise_le"] == "2026-11-07T10:00:00"
    assert transferts["date_heure"] == "2026-11-07T12:30:00" and transferts["bagages"] == "0"
    assert sejours == {"page": "1", "size": "100", "modifie_depuis": "2026-10-01T00:00:00+00:00"}
    assert [r.url.path for r in requetes] == [
        "/internal/car-rentals/search", "/internal/transfers/search", "/internal/stays/export"]


@pytest.mark.parametrize("code, erreur", [
    (404, CatalogLieuInconnu), (422, CatalogRequeteInvalide), (401, CatalogAccesRefuse),
    (403, CatalogAccesRefuse), (503, CatalogIndisponible),
])
async def test_codes_http_traduits(code, erreur):
    client, _ = catalog(lambda r: httpx.Response(code, json={"detail": "Lieu inconnu : Atlantide"}))
    with pytest.raises(erreur):
        await client.rechercher_vols("Atlantide", "DJE", date(2026, 11, 7))


async def test_lieu_inconnu_garde_le_detail():
    client, _ = catalog(lambda r: httpx.Response(404, json={"detail": "Lieu inconnu : Atlantide"}))
    with pytest.raises(CatalogLieuInconnu, match="Atlantide"):
        await client.rechercher_vols("Atlantide", "DJE", date(2026, 11, 7))


@pytest.mark.parametrize("exception", [httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError])
async def test_pannes_reseau(exception):
    def panne(requete):
        raise exception("panne simulée", request=requete)

    client, _ = catalog(panne)
    with pytest.raises(CatalogIndisponible):
        await client.aeroports()
