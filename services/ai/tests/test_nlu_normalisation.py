"""Module 1 : normalisation (villes, montants, durées, dates, total, cohérence) et validateurs.
Aucun réseau ni base."""

from datetime import date

import pytest
from pydantic import ValidationError

import app.nlu  # noqa: F401 — le paquet s'importe (dont `from scripts import jeu_nlu`)
from app.nlu import normalisation as n
from app.nlu.schemas import (
    AVERTISSEMENT_DUREE,
    VOCABULAIRES_LITERAL,
    DemandeVoyage,
    avertissements_demande,
    schema_llm_complet,
    schema_llm_hybride,
)
from scripts import jeu_nlu


# --- Villes ---------------------------------------------------------------------

@pytest.mark.parametrize("nom, attendu", [
    ("djerba", "Djerba"), ("Jerba", "Djerba"), ("جربة", "Djerba"), ("Sidi Bou Said", "Sidi Bou Saïd"),
    ("hammamat", "Hammamet"), ("الحمامات", "Hammamet"), ("Kef", "Le Kef"), ("El Kef", "Le Kef"),
    ("Manouba", "La Manouba"), ("gabes", "Gabès"), ("القيروان", "Kairouan"), ("Douz", "Douz"),
    ("Matmata", None), ("Ksar Ghilane", None), ("Paris", None), ("", None), (None, None),
])
def test_ville_catalogue(nom, attendu):
    assert n.ville_catalogue(nom) == attendu


def test_ville_canonique_de_depart():
    assert n.ville_canonique("brussels") == "Bruxelles"
    assert n.ville_canonique("Tunis-Carthage") == "Tunis"
    assert n.ville_canonique("طرابلس") == "Tripoli"
    assert n.ville_canonique("Oslo") == "Oslo"  # inconnue : gardée telle quelle, jamais inventée


def test_trouver_villes_arabe_avec_prefixe_et_ordre():
    t = n.texte_normalise("نحب نمشي لجربة ومن بعد للحمامات")
    assert [m.ville for m in n.trouver_villes(t)] == ["Djerba", "Hammamet"]


def test_sidi_bouzid_n_est_pas_sidi_bou_said():
    t = n.texte_normalise("3 jours à Sidi Bouzid")
    assert [m.ville for m in n.trouver_villes(t)] == ["Sidi Bouzid"]


def test_texte_normalise_conserve_la_longueur():
    for texte in ("Évasion à Sidi Bou Saïd", "أبحث عن رحلة إلى سوسة", "١٢٠٠ دينار", "l’été – 3 jours"):
        assert len(n.texte_normalise(texte)) == len(texte)
    assert n.texte_normalise("١٢٠٠ دينار") == "1200 دينار"


# --- Montants et total ----------------------------------------------------------

@pytest.mark.parametrize("texte, attendu", [
    ("300", 300), ("1,5k", 1500), ("1.5 k", 1500), ("3 500", 3500), ("3.500", 3500), ("٣٠٠", 300),
    ("12,5", 12.5), ("abc", None),
])
def test_parser_montant(texte, attendu):
    assert n.parser_montant(texte) == attendu


@pytest.mark.parametrize("montant, base, voyageurs, nuits, jours, aussi, attendu", [
    (900, "total", 2, 3, 3, False, 900),
    (900, "par_personne", 12, 7, 7, False, 10800),
    (80, "par_nuit", 8, 3, 3, True, 1920),       # par personne et par nuit (H-018 du README)
    (100, "par_jour", None, 4, 4, False, 400),
    (200, "par_personne", None, 2, 2, False, None),  # multiplicateur inconnu → null
    (None, "total", 2, 2, 2, False, None),
])
def test_vers_total(montant, base, voyageurs, nuits, jours, aussi, attendu):
    assert n.vers_total(montant, base, voyageurs, nuits, jours, aussi) == attendu


# --- Durée et dates -------------------------------------------------------------

@pytest.mark.parametrize("jours, nuits, attendu", [
    (3, None, (3, 3)), (None, 3, (3, 3)), (4, 3, (4, 3)), (1, 0, (1, 0)), (6, 2, (6, 6)), (None, None, (None, None)),
])
def test_completer_duree(jours, nuits, attendu):
    assert n.completer_duree(jours, nuits) == attendu


def test_dates_relatives():
    lundi = date(2026, 11, 9)
    assert n.prochaine_occurrence(15, 3, lundi) == date(2027, 3, 15)
    assert n.prochaine_occurrence(20, 12, lundi) == date(2026, 12, 20)
    assert n.prochaine_occurrence(9, 11, lundi) == lundi                      # ≥ référence
    assert n.jour_semaine_suivant(4, lundi) == date(2026, 11, 13)              # vendredi prochain
    assert n.jour_semaine_suivant(0, lundi) == date(2026, 11, 16)              # strictement après
    assert n.ce_week_end(lundi) == date(2026, 11, 14)
    assert n.ce_week_end(date(2026, 11, 14)) == date(2026, 11, 14)             # samedi lui-même
    assert n.semaine_prochaine(lundi) == date(2026, 11, 16)
    assert n.mois_prochain(date(2026, 12, 5)) == date(2027, 1, 1)


# --- Normalisation d'une demande brute ------------------------------------------

def brut(**champs):
    base = n.demande_hors_sujet("fr") | {"hors_sujet": False}
    base.update(champs)
    return base


def test_normaliser_budget_par_personne_et_villes():
    d = n.normaliser_demande(brut(destination="jerba", autres_villes=["Djerba", "kef", "Matmata"],
                                  budget_montant=250, budget_base="par_personne", nb_voyageurs=4,
                                  duree_jours=3, ville_depart="djerba"))
    assert d["destination"] == "Djerba"
    assert d["autres_villes"] == ["Le Kef"]          # doublon et hors catalogue retirés
    assert d["ville_depart"] is None                 # identique à la destination
    assert (d["budget_montant"], d["budget_devise"], d["budget_base"]) == (1000, "TND", "par_personne")
    assert (d["duree_jours"], d["nb_nuits"]) == (3, 3)


def test_normaliser_transport_et_budget_inclus():
    d = n.normaliser_demande(brut(besoins_transport={"vol": "yes", "voiture": False, "transfert": None}))
    assert d["besoins_transport"] == {"vol": "oui", "voiture": "non", "transfert": "indifferent"}
    assert d["budget_inclut_transport"] is True
    d = n.normaliser_demande(brut(besoins_transport={"vol": "oui"}, _budget_hors_transport=True))
    assert d["budget_inclut_transport"] is False


@pytest.mark.parametrize("champs, attendu", [
    ({"type_voyage": "couple"}, (2, 2, 0, "couple")),
    ({"type_voyage": "solo"}, (1, 1, 0, "solo")),
    ({"type_voyage": "solo", "nb_voyageurs": 3}, (3, None, None, None)),
    ({"nb_adultes": 2, "nb_enfants": 1}, (3, 2, 1, None)),
    ({"nb_voyageurs": 5, "nb_adultes": 2, "nb_enfants": 1}, (5, None, None, None)),
    ({"nb_voyageurs": 4, "nb_adultes": 4}, (4, 4, 0, None)),
])
def test_coherence_voyageurs(champs, attendu):
    d = n.normaliser_demande(brut(**champs))
    assert (d["nb_voyageurs"], d["nb_adultes"], d["nb_enfants"], d["type_voyage"]) == attendu


def test_hors_sujet_vide_tout():
    d = n.normaliser_demande(brut(hors_sujet=True, destination="Djerba", budget_montant=300))
    assert d["hors_sujet"] is True and d["destination"] is None and d["budget_montant"] is None
    assert jeu_nlu.champs_manquants(d) == []


def test_activites_sans_ville_ni_theme():
    d = n.normaliser_demande(brut(activites_souhaitees=["quad", "Djerba", "plage", "QUAD", "x" * 81, "musée; bardo"]))
    assert d["activites_souhaitees"] == ["quad", "musée, bardo"]


# --- Schémas et validateurs -----------------------------------------------------

def test_literal_alignes_sur_le_vocabulaire_du_jeu():
    for literal, vocabulaire in VOCABULAIRES_LITERAL.values():
        assert set(literal.__args__) == set(vocabulaire)


@pytest.mark.parametrize("champs", [
    {"budget_montant": 0, "budget_devise": "TND"},
    {"budget_montant": -5, "budget_devise": "TND"},
    {"duree_jours": 0}, {"duree_jours": 61},
    {"destination": "Matmata"},
    {"destination": "Tunis", "ville_depart": "Tunis"},
    {"autres_villes": ["Paris"]},
])
def test_validateurs_refusent(champs):
    with pytest.raises(ValidationError):
        DemandeVoyage(**champs)


def test_avertissement_au_dela_de_14_jours():
    assert avertissements_demande(DemandeVoyage(duree_jours=30, nb_nuits=30)) == [AVERTISSEMENT_DUREE]
    assert avertissements_demande(DemandeVoyage(duree_jours=14, nb_nuits=14)) == []
    assert avertissements_demande(DemandeVoyage(duree_jours=60, nb_nuits=60)) == [AVERTISSEMENT_DUREE]


def test_vers_attendu_recalcule_les_derives():
    a = DemandeVoyage(destination="Djerba", duree_jours=3, nb_nuits=3, budget_montant=300.0,
                      budget_devise="TND", budget_base="total", nb_voyageurs=2).vers_attendu()
    assert a["budget_montant"] == 300 and isinstance(a["budget_montant"], int)
    assert a["budget_total_dt"] == 300 and a["champs_manquants"] == []
    assert jeu_nlu.valider({"source": "genere", "statut": "valide", "date_reference": "2026-11-09", "attendu": a}) == []


def test_schemas_llm():
    hybride = schema_llm_hybride()
    assert set(hybride["required"]) == set(hybride["properties"])
    assert "budget_montant" not in hybride["properties"]  # les faits viennent des règles
    complet = schema_llm_complet()
    assert set(hybride["properties"]) < set(complet["properties"])
    assert "$ref" not in str(complet) and "$defs" not in complet
