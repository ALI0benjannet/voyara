"""Référentiel des villes (09/11/2026) : couverture des 24 gouvernorats, unicité,
coordonnées en Tunisie, rattachement unique d'un POI quand deux cercles se recouvrent.

Fonctions pures : ni base ni réseau.
"""

from datetime import UTC, datetime

from app.collecte import distance_km, selectionner, ville_de_rattachement
from app.villes import VILLES, normaliser, trouver_ville

# Gouvernorat -> villes du référentiel situées dans ce gouvernorat
GOUVERNORATS = {
    "Tunis": {"Tunis", "Sidi Bou Saïd"}, "Ariana": {"Ariana"}, "Ben Arous": {"Ben Arous"},
    "La Manouba": {"La Manouba"}, "Nabeul": {"Nabeul", "Hammamet"}, "Zaghouan": {"Zaghouan"},
    "Bizerte": {"Bizerte"}, "Béja": {"Béja"}, "Jendouba": {"Jendouba", "Tabarka"},
    "Le Kef": {"Le Kef"}, "Siliana": {"Siliana"}, "Sousse": {"Sousse"}, "Monastir": {"Monastir"},
    "Mahdia": {"Mahdia"}, "Sfax": {"Sfax"}, "Kairouan": {"Kairouan"}, "Kasserine": {"Kasserine"},
    "Sidi Bouzid": {"Sidi Bouzid"}, "Gabès": {"Gabès"}, "Médenine": {"Médenine", "Djerba"},
    "Tataouine": {"Tataouine"}, "Gafsa": {"Gafsa"}, "Tozeur": {"Tozeur"},
    "Kébili": {"Kébili", "Douz"},
}
MAINTENANT = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def test_les_24_gouvernorats_sont_couverts_par_les_29_villes():
    assert len(GOUVERNORATS) == 24
    noms = {v.nom for v in VILLES}
    assert len(VILLES) == 29
    assert set().union(*GOUVERNORATS.values()) == noms
    for gouvernorat, villes in GOUVERNORATS.items():
        assert villes, gouvernorat


def test_aucun_doublon_de_nom_meme_sans_accents():
    cles = [normaliser(v.nom) for v in VILLES]
    assert len(cles) == len(set(cles))
    assert trouver_ville("gabes").nom == "Gabès"
    assert trouver_ville("le-kef").nom == "Le Kef"


def test_coordonnees_et_rayons_plausibles():
    for v in VILLES:
        assert 30 <= v.latitude <= 37.5, v.nom
        assert 7.5 <= v.longitude <= 11.7, v.nom
        assert 1000 <= v.rayon_m <= 16000, v.nom


def test_seul_le_grand_tunis_a_des_cercles_qui_se_recouvrent():
    recouvrements = {
        frozenset((a.nom, b.nom))
        for i, a in enumerate(VILLES) for b in VILLES[i + 1:]
        if distance_km(a.latitude, a.longitude, b.latitude, b.longitude) * 1000 < a.rayon_m + b.rayon_m
    }
    assert recouvrements == {frozenset(("Tunis", autre)) for autre in ("Ariana", "Ben Arous", "La Manouba")}


def test_rattachement_au_centre_le_plus_proche_dans_la_zone_commune():
    tunis, ariana = trouver_ville("Tunis"), trouver_ville("Ariana")
    point = (36.8400, 10.1840)  # dans les deux cercles, plus près du centre d'Ariana
    assert distance_km(*point, tunis.latitude, tunis.longitude) * 1000 <= tunis.rayon_m
    assert distance_km(*point, ariana.latitude, ariana.longitude) * 1000 <= ariana.rayon_m
    assert ville_de_rattachement(*point, tunis) == ariana
    assert ville_de_rattachement(*point, ariana) == ariana


def test_point_hors_du_cercle_voisin_reste_a_la_ville_collectee():
    tunis, ariana = trouver_ville("Tunis"), trouver_ville("Ariana")
    point = (36.8300, 10.1950)  # cercle de Tunis seulement, mais plus près du centre d'Ariana
    assert distance_km(*point, ariana.latitude, ariana.longitude) * 1000 > ariana.rayon_m
    assert distance_km(*point, ariana.latitude, ariana.longitude) < distance_km(
        *point, tunis.latitude, tunis.longitude)
    assert ville_de_rattachement(*point, tunis) == tunis


def test_selection_sans_poi_rattache_a_deux_villes():
    def musee(identifiant, lat, lon):
        return {"type": "node", "id": identifiant, "lat": lat, "lon": lon,
                "tags": {"tourism": "museum", "name": f"Musée {identifiant}"}}

    elements = [musee(1, 36.8400, 10.1840),   # zone commune, plus près d'Ariana
                musee(2, 36.7990, 10.1700),   # centre de Tunis
                musee(3, 36.8587, 10.1882)]   # centre d'Ariana
    tunis = selectionner(elements, trouver_ville("Tunis"), 10, MAINTENANT)
    ariana = selectionner(elements, trouver_ville("Ariana"), 10, MAINTENANT)
    assert [p["source_id"] for p in tunis] == ["node/2"]
    assert [p["source_id"] for p in ariana] == ["node/1", "node/3"]
    assert not {p["source_id"] for p in tunis} & {p["source_id"] for p in ariana}
