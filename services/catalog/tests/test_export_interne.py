"""Export interne des activités pour le moteur IA (/internal/activities/export)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from voyara_common.internal import INTERNAL_HEADER

URL = "/internal/activities/export"


# --- Protection par clé interne --------------------------------------------


def test_export_sans_cle_401(client):
    reponse = client.get(URL)
    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Clé interne manquante"


def test_export_cle_invalide_403(client):
    reponse = client.get(URL, headers={INTERNAL_HEADER: "mauvaise-cle"})
    assert reponse.status_code == 403


def test_autres_routes_internes_aussi_protegees(client):
    # La correction 422 → 401 vit dans voyara_common : elle vaut pour toutes les routes /internal.
    assert client.get("/internal/activities/batch?ids=1").status_code == 401
    assert client.get("/internal/stats/activities").status_code == 401


# --- Contenu et pagination ----------------------------------------------------


def test_export_champs_complets(client, cle_interne, activite):
    reponse = client.get(URL, headers=cle_interne, params={"size": 500})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert set(corps) == {"items", "total", "page", "size", "pages"}
    ligne = next(i for i in corps["items"] if i["id"] == activite.id)
    for champ in (
        "titre", "titre_en", "titre_ar", "description", "description_en", "description_ar",
        "prix", "duree", "localisation", "latitude", "longitude", "photos", "statut",
        "category", "themes", "public", "niveau_marche", "interieur", "moment_ideal",
        "tags_valides", "modifie_le",
    ):
        assert champ in ligne, champ
    assert ligne["category"]["nom"] == "Catégorie de test IA"
    assert ligne["themes"] == [] and ligne["tags_valides"] is False
    assert ligne["latitude"] == 33.8


def test_export_pagination_sans_doublon(client, cle_interne):
    total = client.get(URL, headers=cle_interne, params={"size": 1}).json()["total"]
    vus = []
    for page in range(1, 4):
        corps = client.get(URL, headers=cle_interne, params={"size": 2, "page": page}).json()
        assert corps["total"] == total and corps["size"] == 2
        vus += [i["id"] for i in corps["items"]]
    assert len(vus) == len(set(vus))  # tri stable (modifie_le, id)


def test_export_taille_maximale_500(client, cle_interne):
    assert client.get(URL, headers=cle_interne, params={"size": 501}).status_code == 422


# --- Synchronisation incrémentale (modifie_depuis) ---------------------------


def test_modifie_depuis_filtre(client, cle_interne, activite):
    futur = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert client.get(URL, headers=cle_interne, params={"modifie_depuis": futur}).json()["total"] == 0

    depuis = activite.modifie_le.isoformat()
    corps = client.get(URL, headers=cle_interne, params={"modifie_depuis": depuis, "size": 500}).json()
    assert activite.id in [i["id"] for i in corps["items"]]
    assert all(
        datetime.fromisoformat(i["modifie_le"]) >= activite.modifie_le for i in corps["items"]
    )


def test_modifie_depuis_sans_fuseau_est_utc(client, cle_interne):
    reponse = client.get(URL, headers=cle_interne, params={"modifie_depuis": "2000-01-01T00:00:00"})
    assert reponse.status_code == 200
    assert reponse.json()["total"] >= 1


def test_trigger_met_a_jour_modifie_le(db, activite):
    # Même une écriture SQL brute qui force une vieille date est corrigée par le trigger.
    db.execute(
        text("UPDATE activities SET prix = prix + 1, modifie_le = '2000-01-01' WHERE id = :id"),
        {"id": activite.id},
    )
    modifie_le = db.execute(
        text("SELECT modifie_le FROM activities WHERE id = :id"), {"id": activite.id}
    ).scalar_one()
    assert modifie_le.year > 2000


# --- Filtres ----------------------------------------------------------------


def test_filtres_statut_et_tags_valides(client, cle_interne, db, activite):
    activite.statut = "en_attente"
    db.commit()
    corps = client.get(URL, headers=cle_interne, params={"statut": "en_attente", "size": 500}).json()
    assert activite.id in [i["id"] for i in corps["items"]]
    assert all(i["statut"] == "en_attente" for i in corps["items"])

    corps = client.get(URL, headers=cle_interne, params={"tags_valides": "true", "size": 500}).json()
    assert activite.id not in [i["id"] for i in corps["items"]]
    assert client.get(URL, headers=cle_interne, params={"statut": "inconnu"}).status_code == 422
