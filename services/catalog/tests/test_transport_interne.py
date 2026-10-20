"""Routes internes de l'étape 2-bis : export des séjours, recherche vols / voitures / transferts.

Données jetables sur des aéroports fictifs (ZZA, ZZB, ZZC) pour ne dépendre ni du
seed ni de la date du jour ; tout est annulé avec la transaction du test.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from voyara_common.internal import INTERNAL_HEADER

from app.models import Aeroport, CarRental, Flight, Stay, Transfer

URLS = [
    "/internal/airports",
    "/internal/stays/export",
    "/internal/flights/search?origine=ZZA&destination=ZZB&date=2030-01-01",
    "/internal/car-rentals/search?lieu_prise=ZZA&prise_le=2030-01-01T10:00&retour_le=2030-01-02T10:00",
    "/internal/transfers/search?depart=ZZA&arrivee=ZZB&date_heure=2030-01-01T10:00",
]

JOUR = date.today() + timedelta(days=10)


def _a(heure: str, jours: int = 0) -> datetime:
    return datetime.combine(JOUR + timedelta(days=jours), datetime.strptime(heure, "%H:%M").time())


# --- Protection par clé interne --------------------------------------------


@pytest.mark.parametrize("url", URLS)
def test_sans_cle_401(client, url):
    reponse = client.get(url)
    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Clé interne manquante"


@pytest.mark.parametrize("url", URLS)
def test_cle_invalide_403(client, url):
    assert client.get(url, headers={INTERNAL_HEADER: "mauvaise-cle"}).status_code == 403


# --- Jeu de données ---------------------------------------------------------


@pytest.fixture
def transport(db):
    db.add_all([
        Aeroport(code_iata="ZZA", nom="Test A", ville="Testville A", pays="TN", fuseau="Africa/Tunis"),
        Aeroport(code_iata="ZZB", nom="Test B", ville="Testville B", pays="TN", fuseau="Africa/Tunis"),
        # UTC+4 toute l'année : la durée réelle diffère de l'écart des heures locales.
        Aeroport(code_iata="ZZC", nom="Test C", ville="Testville C", pays="AE", fuseau="Asia/Dubai"),
    ])
    villes = {"ZZA": "Testville A", "ZZB": "Testville B", "ZZC": "Testville C"}

    def vol(numero, dep, arr, depart, arrivee, prix, places, classe="economy"):
        return Flight(
            compagnie="Test Air", numero_vol=numero, aeroport_depart=dep, aeroport_arrivee=arr,
            ville_depart=villes[dep], ville_arrivee=villes[arr], depart_le=depart, arrivee_le=arrivee,
            classe=classe, prix=prix, places_disponibles=places, places_totales=max(places, 10),
        )

    vols = {
        "direct": vol("ZZ1", "ZZA", "ZZB", _a("08:00"), _a("09:00"), 100, 10),
        "complet": vol("ZZ2", "ZZA", "ZZB", _a("15:00"), _a("16:00"), 90, 0),
        "une_place": vol("ZZ3", "ZZA", "ZZB", _a("18:00"), _a("19:00"), 80, 1),
        "j_plus_2": vol("ZZ4", "ZZA", "ZZB", _a("08:00", 2), _a("09:00", 2), 100, 10),
        "vers_c": vol("ZZ5", "ZZA", "ZZC", _a("07:00"), _a("08:00"), 50, 10),
        "c_attente_90": vol("ZZ6", "ZZC", "ZZB", _a("09:30"), _a("10:30"), 60, 10),
        "c_attente_30": vol("ZZ7", "ZZC", "ZZB", _a("08:30"), _a("09:30"), 55, 10),
        "c_attente_12h": vol("ZZ8", "ZZC", "ZZB", _a("20:00"), _a("21:00"), 40, 10),
        # 10:00 à Dubaï (06:00 UTC) -> 10:00 à Tunis (09:00 UTC) : 180 min de vol.
        "c_vers_a": vol("ZZ9", "ZZC", "ZZA", _a("10:00"), _a("10:00"), 300, 10),
    }
    voitures = {
        "aeroport": CarRental(marque="Kia", modele="Picanto", categorie="economique",
                              transmission="manuelle", carburant="essence", nb_places=4,
                              agence="Test Location aéroport", localisation="Testville A, aéroport Test A",
                              ville="Testville A", aeroport="ZZA", prix_jour=100),
        "centre": CarRental(marque="Hyundai", modele="Tucson", categorie="suv",
                            transmission="automatique", carburant="diesel", nb_places=7,
                            agence="Test Location centre", localisation="Testville A, centre",
                            ville="Testville A", prix_jour=200),
        "indisponible": CarRental(marque="Dacia", modele="Duster", categorie="suv",
                                  transmission="manuelle", carburant="diesel", nb_places=5,
                                  agence="Test Location centre", localisation="Testville A, centre",
                                  ville="Testville A", prix_jour=150, disponible=False),
    }

    def transfert(depart, arrivee, aero_dep, aero_arr, type_, capacite, bagages, prix, actif=True):
        return Transfer(
            depart=depart, arrivee=arrivee, ville_depart="Testville A", ville_arrivee="Testville A",
            aeroport_depart=aero_dep, aeroport_arrivee=aero_arr, type_vehicule=type_,
            capacite=capacite, bagages=bagages, duree=30, prix=prix, actif=actif,
        )

    transferts = {
        "berline": transfert("Aéroport Test A", "Testville A, centre", "ZZA", None, "berline", 3, 3, 90),
        "van": transfert("Aéroport Test A", "Testville A, centre", "ZZA", None, "van", 7, 7, 150),
        "inactif": transfert("Aéroport Test A", "Testville A, centre", "ZZA", None, "taxi", 4, 3, 30, False),
        "retour": transfert("Testville A, centre", "Aéroport Test A", None, "ZZA", "berline", 3, 3, 90),
    }
    db.add_all([*vols.values(), *voitures.values(), *transferts.values()])
    db.commit()
    return {"vols": vols, "voitures": voitures, "transferts": transferts}


def _get(client, cle, url, **params):
    reponse = client.get(url, headers=cle, params=params)
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


# --- Référentiel ------------------------------------------------------------


def test_airports(client, cle_interne, transport):
    corps = _get(client, cle_interne, "/internal/airports")
    assert set(corps) == {"items", "total", "page", "size", "pages"}
    zzc = next(a for a in corps["items"] if a["code_iata"] == "ZZC")
    assert zzc == {"code_iata": "ZZC", "nom": "Test C", "ville": "Testville C", "pays": "AE",
                   "fuseau": "Asia/Dubai"}


# --- Export des séjours -----------------------------------------------------


@pytest.fixture
def sejour(db) -> Stay:
    stay = Stay(nom="Séjour de test IA", type="riad", description="Riad de test au calme.",
                localisation="Testville A, médina", latitude=36.8, longitude=10.1, etoiles=None,
                prix_nuit=210, capacite=4, equipements="patio, wifi,,piscine", actif=False)
    db.add(stay)
    db.commit()
    return stay


def test_export_stays_champs(client, cle_interne, sejour):
    corps = _get(client, cle_interne, "/internal/stays/export", size=500)
    ligne = next(i for i in corps["items"] if i["id"] == sejour.id)
    for champ in ("nom", "nom_en", "nom_ar", "type", "description", "description_en",
                  "description_ar", "localisation", "ville", "latitude", "longitude", "etoiles",
                  "prix_nuit", "devise", "capacite", "equipements", "photos", "actif", "modifie_le"):
        assert champ in ligne, champ
    assert ligne["ville"] == "Testville A"
    assert ligne["equipements"] == ["patio", "wifi", "piscine"]
    assert ligne["prix_nuit"] == 210.0 and ligne["devise"] == "DT"
    # Inactifs exportés par défaut (l'index apprend les retraits), filtrables.
    actifs = _get(client, cle_interne, "/internal/stays/export", size=500, actif="true")
    assert sejour.id not in [i["id"] for i in actifs["items"]]


def test_export_stays_modifie_depuis_et_trigger(client, cle_interne, db, sejour):
    futur = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert _get(client, cle_interne, "/internal/stays/export", modifie_depuis=futur)["total"] == 0
    corps = _get(client, cle_interne, "/internal/stays/export",
                 modifie_depuis=sejour.modifie_le.isoformat(), size=500)
    assert sejour.id in [i["id"] for i in corps["items"]]
    assert _get(client, cle_interne, "/internal/stays/export",
                modifie_depuis="2000-01-01T00:00:00")["total"] >= 1  # sans fuseau = UTC

    db.execute(text("UPDATE stays SET prix_nuit = 1, modifie_le = '2000-01-01' WHERE id = :id"),
               {"id": sejour.id})
    modifie_le = db.execute(text("SELECT modifie_le FROM stays WHERE id = :id"),
                            {"id": sejour.id}).scalar_one()
    assert modifie_le.year > 2000


def test_export_stays_pagination(client, cle_interne, sejour):
    total = _get(client, cle_interne, "/internal/stays/export", size=1)["total"]
    vus = []
    for page in range(1, total + 1):
        vus += [i["id"] for i in _get(client, cle_interne, "/internal/stays/export",
                                       size=1, page=page)["items"]]
    assert len(vus) == len(set(vus)) == total
    assert client.get("/internal/stays/export", headers=cle_interne,
                      params={"size": 501}).status_code == 422


# --- Vols -------------------------------------------------------------------

VOLS = "/internal/flights/search"


def _numeros(corps) -> list[list[str]]:
    return [[s["numero_vol"] for s in i["segments"]] for i in corps["items"]]


def test_vols_direct_et_correspondance(client, cle_interne, transport):
    corps = _get(client, cle_interne, VOLS, origine="ZZA", destination="ZZB",
                 date=JOUR.isoformat(), nb_passagers=2)
    # Complet (ZZ2) et 1 place (ZZ3) exclus ; correspondances à 30 min et 12 h refusées.
    assert _numeros(corps) == [["ZZ1"], ["ZZ5", "ZZ6"]]
    direct, escale = corps["items"]
    assert direct["escales"] == 0 and direct["prix_par_passager"] == 100.0
    assert direct["prix_total"] == 200.0 and direct["devise"] == "DT"
    assert direct["depart_le"] == f"{JOUR.isoformat()}T08:00:00+01:00"
    assert escale["escales"] == 1 and escale["aeroports_escale"] == ["ZZC"]
    assert escale["attente_min"] == 90 and escale["prix_par_passager"] == 110.0
    assert escale["prix_total"] == 220.0 and escale["places_restantes"] == 10


def test_vols_jamais_complets_ni_sous_capacite(client, cle_interne, transport):
    corps = _get(client, cle_interne, VOLS, origine="ZZA", destination="ZZB",
                 date=JOUR.isoformat(), nb_passagers=1, escales_max=0)
    assert _numeros(corps) == [["ZZ3"], ["ZZ1"]]  # même jour, même nb d'escales : prix croissant
    assert all(s["places_disponibles"] >= 1 for i in corps["items"] for s in i["segments"])
    assert _get(client, cle_interne, VOLS, origine="ZZA", destination="ZZB",
                date=JOUR.isoformat(), nb_passagers=9, escales_max=0)["total"] == 1  # ZZ1 seul


def test_vols_tolerance_jours(client, cle_interne, transport):
    params = {"origine": "ZZA", "destination": "ZZB", "escales_max": 0, "nb_passagers": 2}
    assert _get(client, cle_interne, VOLS, date=(JOUR + timedelta(days=1)).isoformat(),
                tolerance_jours=0, **params)["total"] == 0
    corps = _get(client, cle_interne, VOLS, date=(JOUR + timedelta(days=1)).isoformat(),
                 tolerance_jours=1, **params)
    assert sorted(i["ecart_jours"] for i in corps["items"]) == [-1, 1]
    assert client.get(VOLS, headers=cle_interne, params={
        **params, "date": JOUR.isoformat(), "tolerance_jours": 4}).status_code == 422


def test_vols_duree_avec_fuseau(client, cle_interne, transport):
    item = _get(client, cle_interne, VOLS, origine="ZZC", destination="ZZA",
                date=JOUR.isoformat())["items"][0]
    assert item["duree_totale_min"] == 180  # et non 0 (écart des heures locales)
    assert item["depart_le"].endswith("+04:00") and item["arrivee_le"].endswith("+01:00")


def test_vols_ville_et_lieux(client, cle_interne, transport):
    corps = _get(client, cle_interne, VOLS, origine="testville a", destination="Testville B",
                 date=JOUR.isoformat(), nb_passagers=2)
    assert corps["total"] == 2
    inconnu = client.get(VOLS, headers=cle_interne, params={
        "origine": "Atlantide", "destination": "ZZB", "date": JOUR.isoformat()})
    assert inconnu.status_code == 404 and "Lieu inconnu" in inconnu.json()["detail"]
    assert client.get(VOLS, headers=cle_interne, params={
        "origine": "ZZA", "destination": "ZZA", "date": JOUR.isoformat()}).status_code == 422


def test_vols_pagination(client, cle_interne, transport):
    params = {"origine": "ZZA", "destination": "ZZB", "date": JOUR.isoformat(), "size": 1}
    p1 = _get(client, cle_interne, VOLS, page=1, **params)
    p2 = _get(client, cle_interne, VOLS, page=2, **params)
    assert p1["total"] == p2["total"] == 3 and p1["pages"] == 3
    assert _numeros(p1) != _numeros(p2)


# --- Voitures ---------------------------------------------------------------

VOITURES = "/internal/car-rentals/search"
PERIODE = {"prise_le": "2030-01-01T10:00:00", "retour_le": "2030-01-04T10:00:00"}


def _modeles(corps) -> list[str]:
    return [i["modele"] for i in corps["items"]]


def test_voitures_disponibles_et_prix_total(client, cle_interne, transport):
    corps = _get(client, cle_interne, VOITURES, lieu_prise="Testville A", **PERIODE)
    assert _modeles(corps) == ["Picanto", "Tucson"]  # le Duster indisponible n'apparaît pas
    picanto = corps["items"][0]
    assert picanto["nb_jours"] == 3 and picanto["prix_jour"] == 100.0
    assert picanto["prix_total"] == 300.0 and picanto["devise"] == "DT"


def test_voitures_filtres(client, cle_interne, transport):
    assert _modeles(_get(client, cle_interne, VOITURES, lieu_prise="ZZA", **PERIODE)) == ["Picanto"]
    assert _modeles(_get(client, cle_interne, VOITURES, lieu_prise="Testville A",
                         nb_places=5, **PERIODE)) == ["Tucson"]
    assert _modeles(_get(client, cle_interne, VOITURES, lieu_prise="Testville A",
                         transmission="automatique", **PERIODE)) == ["Tucson"]
    assert _modeles(_get(client, cle_interne, VOITURES, lieu_prise="Testville A",
                         categorie="economique", **PERIODE)) == ["Picanto"]
    assert _modeles(_get(client, cle_interne, VOITURES, lieu_prise="centre", **PERIODE)) == ["Tucson"]


def test_voitures_retour_et_dates(client, cle_interne, transport):
    # Retour à l'aéroport de la même ville : accepté ; dans une autre ville : aucun aller simple.
    assert _get(client, cle_interne, VOITURES, lieu_prise="Testville A", lieu_retour="ZZA",
                **PERIODE)["total"] == 2
    assert _get(client, cle_interne, VOITURES, lieu_prise="Testville A",
                lieu_retour="Testville B", **PERIODE)["total"] == 0
    assert client.get(VOITURES, headers=cle_interne, params={
        "lieu_prise": "ZZA", "prise_le": "2030-01-04T10:00", "retour_le": "2030-01-01T10:00",
    }).status_code == 422


# --- Transferts -------------------------------------------------------------

TRANSFERTS = "/internal/transfers/search"


def test_transferts_aeroport_vers_ville(client, cle_interne, transport):
    corps = _get(client, cle_interne, TRANSFERTS, depart="ZZA", arrivee="Testville A",
                 date_heure="2030-01-01T10:00:00", nb_passagers=2)
    # Taxi inactif exclu ; le trajet inverse (centre -> aéroport) n'est pas renvoyé.
    assert [i["type_vehicule"] for i in corps["items"]] == ["berline", "van"]
    berline = corps["items"][0]
    assert berline["prix_total"] == 90.0 and berline["prix_par_passager"] == 45.0
    assert berline["duree_min"] == 30 and berline["arrivee_estimee"] == "2030-01-01T10:30:00"
    assert _get(client, cle_interne, TRANSFERTS, depart="ZZA", arrivee="centre",
                date_heure="2030-01-01T10:00:00")["total"] == 2


def test_transferts_capacite_et_bagages(client, cle_interne, transport):
    base = {"depart": "ZZA", "arrivee": "Testville A", "date_heure": "2030-01-01T10:00:00"}
    assert [i["type_vehicule"] for i in _get(client, cle_interne, TRANSFERTS, nb_passagers=5,
                                             **base)["items"]] == ["van"]
    assert [i["type_vehicule"] for i in _get(client, cle_interne, TRANSFERTS, bagages=5,
                                             **base)["items"]] == ["van"]
    retour = _get(client, cle_interne, TRANSFERTS, depart="Testville A", arrivee="ZZA",
                  date_heure="2030-01-01T10:00:00")
    assert [i["depart"] for i in retour["items"]] == ["Testville A, centre"]
