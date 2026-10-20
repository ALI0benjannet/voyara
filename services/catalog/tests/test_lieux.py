"""Déduction et résolution des lieux du transport (app/lieux.py) — sans base."""

import pytest
from seed_offres_voyage_demo import AEROPORTS, AGENCES, TRANSFERTS

from app.lieux import AEROPORTS_REFERENCE, deduire_lieu, resoudre_lieu, ville_de_localisation
from app.recherche_transport import nb_jours_location

REF = list(AEROPORTS_REFERENCE)


def test_referentiel_couvre_tous_les_aeroports_des_vols():
    codes = {a["code_iata"] for a in REF}
    assert codes == set(AEROPORTS)
    # La ville du référentiel est celle que le seed écrit dans flights.ville_*.
    assert all(a["ville"] == AEROPORTS[a["code_iata"]] for a in REF)


@pytest.mark.parametrize(
    "texte, attendu",
    [
        ("Tunis, aéroport Tunis-Carthage", ("Tunis", "TUN")),
        ("Monastir, aéroport Habib-Bourguiba", ("Monastir", "MIR")),
        ("Aéroport Monastir Habib-Bourguiba", ("Monastir", "MIR")),
        ("Aéroport Enfidha-Hammamet", ("Enfidha", "NBE")),
        ("Djerba, zone touristique de Midoun", ("Djerba", None)),
        ("Tunis, Gammarth / La Marsa", ("Tunis", None)),
        ("Hôtel sans ville", (None, None)),  # rien n'est inventé
        (None, (None, None)),
    ],
)
def test_deduire_lieu(texte, attendu):
    assert deduire_lieu(texte, REF) == attendu


def test_toutes_les_localisations_du_seed_sont_resolues():
    for _agence, localisation, aeroport, _modeles in AGENCES:
        ville, code = deduire_lieu(localisation, REF)
        assert ville == localisation.split(",")[0], localisation
        assert (code is not None) == aeroport, localisation
    for depart, arrivee, *_ in TRANSFERTS:
        for texte in (depart, arrivee):
            ville, code = deduire_lieu(texte, REF)
            assert ville, texte
            assert (code is not None) == texte.startswith("Aéroport"), texte


def test_resoudre_lieu():
    assert resoudre_lieu("dje", REF).codes == {"DJE"}
    paris = resoudre_lieu("paris", REF)
    assert paris.mode == "ville" and paris.codes == {"ORY", "CDG"} and paris.ville == "Paris"
    assert resoudre_lieu("Genève", REF).codes == {"GVA"}
    assert resoudre_lieu("Hammamet", REF, {"Hammamet"}).mode == "ville"
    midoun = resoudre_lieu("Midoun", REF, {"Djerba"})
    assert midoun.mode == "texte" and midoun.correspond_au_texte("Djerba, zone touristique de Midoun")
    # Un mot de 3 lettres qui n'est pas un code connu reste du texte.
    assert resoudre_lieu("Lac", REF).mode == "texte"


def test_ville_de_localisation_et_jours_factures():
    assert ville_de_localisation("Tunis, Sidi Bou Saïd") == "Tunis"
    assert ville_de_localisation("Djerba") == "Djerba"
    from datetime import datetime

    debut = datetime(2026, 11, 1, 10)
    assert nb_jours_location(debut, datetime(2026, 11, 1, 12)) == 1
    assert nb_jours_location(debut, datetime(2026, 11, 4, 10)) == 3
    assert nb_jours_location(debut, datetime(2026, 11, 4, 11)) == 4  # 24 h entamées dues
