"""Cache météo : expiration 6 h, un seul appel par plage, repli sur le cache périmé.

Open-Meteo simulé (httpx.MockTransport) ; la base `voyara_ai` est annulée après chaque test.
"""

from datetime import date, timedelta

import httpx
import pytest

from app.meteo import MeteoIndisponible, obtenir_meteo
from app.models import MeteoCache

# Date lointaine : jamais présente dans le vrai cache rempli par rafraichir_meteo.py
JOUR = date(2099, 1, 5)


def reponse_open_meteo(debut: date, nb: int, base: float = 20.0) -> dict:
    jours = [debut + timedelta(days=i) for i in range(nb)]
    return {"daily": {
        "time": [j.isoformat() for j in jours],
        "temperature_2m_min": [base + i for i in range(nb)],
        "temperature_2m_max": [base + 8 + i for i in range(nb)],
        "precipitation_sum": [0.0] * nb,
        "weather_code": [1] * nb,
    }}


def client_compteur(corps=None, erreur=False):
    appels = []

    def gerer(requete: httpx.Request) -> httpx.Response:
        appels.append(requete)
        if erreur:
            raise httpx.ConnectError("hors-ligne")
        return httpx.Response(200, json=corps)

    return httpx.Client(transport=httpx.MockTransport(gerer)), appels


def test_premier_appel_interroge_open_meteo_et_remplit_le_cache(db):
    client, appels = client_compteur(reponse_open_meteo(JOUR, 3))
    jours = obtenir_meteo(db, "Djerba", JOUR, 3, client=client)

    assert len(appels) == 1
    params = appels[0].url.params
    assert params["latitude"] == "33.81" and params["timezone"] == "Africa/Tunis"
    assert params["start_date"] == "2099-01-05" and params["end_date"] == "2099-01-07"
    assert [j.temp_max for j in jours] == [28.0, 29.0, 30.0]
    assert not any(j.perime for j in jours)
    assert db.query(MeteoCache).filter(MeteoCache.ville == "Djerba", MeteoCache.date >= JOUR).count() == 3


def test_second_appel_avant_6h_sert_le_cache(db):
    client, appels = client_compteur(reponse_open_meteo(JOUR, 3))
    obtenir_meteo(db, "Djerba", JOUR, 3, client=client)
    jours = obtenir_meteo(db, "djerba", JOUR, 3, client=client)  # nom normalisé
    assert len(appels) == 1
    assert [j.date for j in jours] == [JOUR, JOUR + timedelta(days=1), JOUR + timedelta(days=2)]


def test_date_absente_du_cache_declenche_un_appel(db):
    client, _ = client_compteur(reponse_open_meteo(JOUR, 2))
    obtenir_meteo(db, "Djerba", JOUR, 2, client=client)
    client2, appels2 = client_compteur(reponse_open_meteo(JOUR, 3))
    obtenir_meteo(db, "Djerba", JOUR, 3, client=client2)
    assert len(appels2) == 1
    assert db.query(MeteoCache).filter(MeteoCache.ville == "Djerba", MeteoCache.date >= JOUR).count() == 3  # upsert, pas de doublon


def _vieillir_cache(db, heures: float):
    for ligne in db.query(MeteoCache).all():
        ligne.maj_le = ligne.maj_le - timedelta(hours=heures)
    db.commit()


def test_cache_de_plus_de_6h_est_rafraichi(db):
    client, _ = client_compteur(reponse_open_meteo(JOUR, 2))
    obtenir_meteo(db, "Djerba", JOUR, 2, client=client)
    _vieillir_cache(db, 6.1)

    client2, appels2 = client_compteur(reponse_open_meteo(JOUR, 2, base=10.0))
    jours = obtenir_meteo(db, "Djerba", JOUR, 2, client=client2)
    assert len(appels2) == 1
    assert jours[0].temp_min == 10.0
    db.expire_all()
    assert db.query(MeteoCache).filter_by(ville="Djerba", date=JOUR).one().temp_min == 10.0


def test_cache_de_5h_reste_valide(db):
    client, _ = client_compteur(reponse_open_meteo(JOUR, 1))
    obtenir_meteo(db, "Djerba", JOUR, 1, client=client)
    _vieillir_cache(db, 5)
    client2, appels2 = client_compteur(reponse_open_meteo(JOUR, 1))
    obtenir_meteo(db, "Djerba", JOUR, 1, client=client2)
    assert appels2 == []


def test_hors_ligne_avec_cache_perime_renvoie_le_cache_marque(db):
    client, _ = client_compteur(reponse_open_meteo(JOUR, 2))
    obtenir_meteo(db, "Djerba", JOUR, 2, client=client)
    _vieillir_cache(db, 24)

    hors_ligne, appels = client_compteur(erreur=True)
    attentes = []
    jours = obtenir_meteo(db, "Djerba", JOUR, 2, client=hors_ligne, dormir=attentes.append)
    assert len(appels) == 2 and attentes == [2]  # une nouvelle tentative avant le repli
    assert len(jours) == 2 and all(j.perime for j in jours)
    assert jours[0].temp_min == 20.0


def test_hors_ligne_sans_cache_leve_une_erreur(db):
    hors_ligne, _ = client_compteur(erreur=True)
    with pytest.raises(MeteoIndisponible, match="Tozeur"):
        obtenir_meteo(db, "Tozeur", JOUR, 2, client=hors_ligne, dormir=lambda s: None)


def test_503_passager_puis_succes(db):
    statuts = iter([503, 200])

    def gerer(requete: httpx.Request) -> httpx.Response:
        statut = next(statuts)
        return httpx.Response(statut, json=reponse_open_meteo(JOUR, 1) if statut == 200 else {})

    attentes = []
    client = httpx.Client(transport=httpx.MockTransport(gerer))
    jours = obtenir_meteo(db, "Djerba", JOUR, 1, client=client, dormir=attentes.append)
    assert attentes == [2] and jours[0].temp_max == 28.0 and not jours[0].perime


def test_parametres_invalides(db):
    with pytest.raises(ValueError, match="Ville inconnue"):
        obtenir_meteo(db, "Paris", JOUR, 1)
    with pytest.raises(ValueError, match="nb_jours"):
        obtenir_meteo(db, "Djerba", JOUR, 17)
