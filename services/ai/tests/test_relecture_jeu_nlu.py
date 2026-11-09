"""Outils du jeu d'évaluation NLU : règles, validation, accord, relecture Excel aller-retour.

Ni base ni réseau : les JSONL sont copiés dans un dossier temporaire.
"""

import shutil
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jeu_nlu as j  # noqa: E402
from accord_annotateurs import kappa_cohen  # noqa: E402
from generer_relecture import EN_TETES, FEUILLE, RELECTEURS, ecrire_classeur, repartir  # noqa: E402
from importer_relecture import ValeurInvalide, depuis_cellule, importer  # noqa: E402


@pytest.fixture
def jeu_copie(tmp_path):
    dossier = tmp_path / "eval"
    dossier.mkdir()
    for nom in j.FICHIERS_JEU:
        shutil.copy(j.DOSSIER_EVAL / nom, dossier / nom)
    return dossier


def _toutes(dossier=j.DOSSIER_EVAL):
    return [d for lignes in j.charger_jeu(dossier).values() for d in lignes]


# --- Jeu versionné ---------------------------------------------------------------

def test_jeu_complet_valide_et_compose():
    demandes = _toutes()
    assert len(demandes) == 190  # 130 humaines (équipe v2) + 60 générées
    assert len({d["id"] for d in demandes}) == 190
    erreurs = {d["id"]: j.valider(d) for d in demandes if j.valider(d)}
    assert erreurs == {}
    test_genere = [d for d in demandes if d["jeu"] == "test"]
    hors_djerba = sum(d["attendu"]["destination"] != "Djerba" for d in test_genere)
    assert hors_djerba / len(test_genere) >= 0.70
    assert sum(d["attendu"]["langue"] in ("ar", "darija") for d in demandes) >= 20
    assert sum(d["attendu"]["besoins_transport"] != dict.fromkeys(("vol", "voiture", "transfert"), "indifferent")
               for d in demandes) >= 25


def test_budget_illimite_pas_de_question():
    index = {d["id"]: d for d in _toutes()}
    for ident in ("H-014", "H-036"):
        a = index[ident]["attendu"]
        assert a["budget_illimite"] is True and a["budget_montant"] is None
        assert "budget" not in a["champs_manquants"]


# --- Règles et validation ----------------------------------------------------------

def _demande(**attendu):
    base = {
        "destination": "Sousse", "autres_villes": [], "date_debut": None, "duree_jours": 3, "nb_nuits": 3,
        "budget_montant": 500, "budget_devise": "TND", "budget_base": "total", "budget_illimite": False,
        "budget_total_dt": 500, "nb_voyageurs": 2, "nb_adultes": 2, "nb_enfants": 0, "type_voyage": "couple",
        "preferences": [], "activites_souhaitees": [], "contraintes": {"niveau_marche_max": None, "mobilite_reduite": None, "horaires": None},
        "langue": "fr", "ville_depart": None,
        "besoins_transport": {"vol": "indifferent", "voiture": "indifferent", "transfert": "indifferent"},
        "preferences_transport": {"vol_direct": None, "boite_auto": None, "priorite": None},
        "budget_inclut_transport": False, "hors_sujet": False, "champs_manquants": [],
    }
    base.update(attendu)
    j.deriver(base)
    return {"id": "X-1", "source": "genere", "jeu": "dev", "date_reference": "2026-11-09", "statut": "a_relire",
            "tags": [], "texte": "…", "attendu": base}


def test_vol_sans_depart_ni_date_et_devise():
    d = _demande(besoins_transport={"vol": "oui", "voiture": "indifferent", "transfert": "indifferent"},
                 budget_devise="EUR")
    assert d["attendu"]["champs_manquants"] == ["ville_depart", "date_debut"]
    assert d["attendu"]["budget_total_dt"] is None  # pas de conversion
    assert j.valider(d) == []


@pytest.mark.parametrize("modif, extrait", [
    ({"destination": "Tabarka"}, "destination"),
    ({"duree_jours": 61, "nb_nuits": 61}, "hors limites"),
    ({"duree_jours": 3, "nb_nuits": 5}, "incohérents"),
    ({"preferences": ["ski"]}, "preferences"),
    ({"nb_voyageurs": 5}, "≠ adultes + enfants"),
    ({"date_debut": "2026-11-01"}, "antérieure"),
    ({"budget_illimite": True}, "budget_illimite"),
    ({"ville_depart": "Sousse"}, "identique"),
    ({"activites_souhaitees": ["quad", "Quad"]}, "doublon"),
    ({"activites_souhaitees": ["a ; b"]}, "réservé"),
])
def test_valider_signale_les_incoherences(modif, extrait):
    erreurs = j.valider(_demande(**modif))
    assert any(extrait in e for e in erreurs), erreurs


def test_duree_longue_acceptee():
    assert j.valider(_demande(duree_jours=30, nb_nuits=30)) == []


def test_kappa():
    assert kappa_cohen(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert kappa_cohen(["a", "a"], ["a", "a"]) is None  # une seule catégorie : indéfini
    assert kappa_cohen(["a", "b", "a", "b"], ["b", "a", "b", "a"]) == -1.0


def test_ecarts_equipe_budget_par_personne():
    index = {d["id"]: d for d in _toutes()}
    assert any(e.startswith("budget_montant : 700 → 4200") for e in j.ecarts_equipe(index["H-015"]))


# --- Relecture Excel ---------------------------------------------------------------

def test_repartition_stratifiee_et_deterministe():
    demandes = _toutes()
    parts = repartir(demandes, RELECTEURS, 1)
    assert sorted(len(p) for p in parts.values()) == [47, 47, 48, 48]
    assert sorted(d["id"] for p in parts.values() for d in p) == sorted(d["id"] for d in demandes)
    for langue in j.LANGUES:
        effectifs = [sum(d["attendu"]["langue"] == langue for d in p) for p in parts.values()]
        assert max(effectifs) - min(effectifs) <= 1
    assert [d["id"] for d in repartir(demandes, RELECTEURS, 1)["ali"]] == [d["id"] for d in parts["ali"]]


@pytest.mark.parametrize("valeur, type_, attendu", [
    ("vrai", "bool", True), ("faux", "bool", False), (None, "bool", None),
    ("3", "entier", 3), (3.0, "entier", 3), ("1,5", "nombre", 1.5), ("plage, culture", "liste", ["plage", "culture"]),
    ("", "liste", []), ("eur", "texte", "eur"), ("quad ; nuit sous tente", "liste", ["quad", "nuit sous tente"]),
])
def test_depuis_cellule(valeur, type_, attendu):
    assert depuis_cellule(valeur, type_, "champ") == attendu


def test_depuis_cellule_refuse():
    with pytest.raises(ValeurInvalide):
        depuis_cellule("3 jours", "entier", "duree_jours")
    with pytest.raises(ValeurInvalide):
        depuis_cellule("peut-être", "bool", "vol_direct")


def test_aller_retour_excel(jeu_copie, tmp_path):
    demandes = _toutes(jeu_copie)
    index = {d["id"]: d for d in demandes}
    lot = [index["G-001"], index["H-015"], index["H-041"], index["G-101"], index["H-002"]]
    dossier = tmp_path / "relecture"
    dossier.mkdir()
    chemin = dossier / "relecture_ali.xlsx"
    ecrire_classeur(chemin, "ali", lot)

    classeur = load_workbook(chemin)
    feuille = classeur[FEUILLE]
    col = {nom: i for i, nom in enumerate(EN_TETES, start=1)}
    rangee = {feuille.cell(r, col["id"]).value: r for r in range(2, feuille.max_row + 1)}
    feuille.cell(rangee["G-001"], col["statut"]).value = "valide"
    # H-041 : cas « je » tranché en solo, corrigé
    for nom, valeur in (("nb_voyageurs", 1), ("nb_adultes", 1), ("nb_enfants", 0), ("type_voyage", "solo"),
                        ("activites_souhaitees", "medina ; sidi bou said, le soir"),
                        ("statut", "corrige"), ("commentaire", "un seul voyageur")):
        feuille.cell(rangee["H-041"], col[nom]).value = valeur
    # G-101 : modifié mais laissé « valide » → avertissement, passé en corrige
    feuille.cell(rangee["G-101"], col["duree_jours"]).value = 7
    feuille.cell(rangee["G-101"], col["nb_nuits"]).value = 7
    feuille.cell(rangee["G-101"], col["statut"]).value = "valide"
    # H-002 : valeur interdite → erreur, non appliquée
    feuille.cell(rangee["H-002"], col["preferences"]).value = "ski"
    feuille.cell(rangee["H-002"], col["statut"]).value = "valide"
    # H-015 : non relue
    classeur.save(chemin)

    simulation = importer(dossier, jeu_copie, appliquer=False)
    assert _toutes(jeu_copie) == demandes  # simulation : rien n'est écrit

    rapport = importer(dossier, jeu_copie, appliquer=True)
    assert rapport.appliquees == simulation.appliquees == {"valide": 1, "corrige": 2}
    assert rapport.non_relues == ["H-015 (ali)"]
    assert any("H-002" in e and "ski" in e for e in rapport.erreurs)
    assert any("G-101" in a for a in rapport.avertissements)
    assert len(rapport.non_distribuees) == 185

    apres = {d["id"]: d for d in _toutes(jeu_copie)}
    h041 = apres["H-041"]
    assert h041["statut"] == "corrige" and h041["relu_par"] == "ali" and "a_trancher" not in h041
    assert h041["attendu"]["champs_manquants"] == []  # recalculé : le nombre de voyageurs est connu
    assert h041["commentaire_relecture"] == "un seul voyageur"
    assert h041["attendu"]["activites_souhaitees"] == ["medina", "sidi bou said, le soir"]  # virgule conservée
    assert apres["G-101"]["statut"] == "corrige" and apres["G-101"]["attendu"]["duree_jours"] == 7
    assert apres["G-001"]["statut"] == "valide" and apres["G-001"]["attendu"] == index["G-001"]["attendu"]
    assert apres["H-002"]["statut"] == "a_relire" and apres["H-002"]["attendu"] == index["H-002"]["attendu"]


# --- Activités souhaitées (F1 tolérant) ----------------------------------------------

@pytest.mark.parametrize("a, b, attendu", [
    ("le musée du Bardo", "musée du bardo", True),          # articles, casse
    ("Carthage", "visite de Carthage", True),               # inclusion
    ("quad dans les dunes", "quad", True),
    ("المدينة العتيقة", "مدينة العتيقة", True),              # article arabe « ال »
    ("plongée", "kayak", False),
    ("nuit sous tente", "nuit en campement", False),        # 1 mot commun sur 4 : < 50 %
])
def test_activites_correspondent(a, b, attendu):
    assert j.activites_correspondent(a, b) is attendu


def test_apparier_activites_un_a_un():
    # « quad » ne peut servir qu'une fois ; F1 = 2·VP / (prédites + attendues)
    assert j.apparier_activites(["quad", "spa"], ["quad dans les dunes", "quad en soirée", "spa"]) == 2
    assert j.apparier_activites([], ["golf"]) == 0
