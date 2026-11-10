"""scripts/evaluer_nlu.py : métriques sur un mini-jeu, répartition dev/test, échantillon. Sans réseau."""

import copy

import pytest

from scripts import evaluer_nlu as ev
from scripts import jeu_nlu


def attendu(**champs):
    a = {
        "destination": None, "autres_villes": [], "date_debut": None, "duree_jours": None, "nb_nuits": None,
        "budget_montant": None, "budget_devise": None, "budget_base": None, "budget_illimite": False,
        "nb_voyageurs": None, "nb_adultes": None, "nb_enfants": None, "type_voyage": None, "preferences": [],
        "activites_souhaitees": [], "contraintes": {"niveau_marche_max": None, "mobilite_reduite": None, "horaires": None},
        "langue": "fr", "ville_depart": None,
        "besoins_transport": {"vol": "indifferent", "voiture": "indifferent", "transfert": "indifferent"},
        "preferences_transport": {"vol_direct": None, "boite_auto": None, "priorite": None},
        "budget_inclut_transport": False, "hors_sujet": False,
    }
    for cle, valeur in champs.items():
        if cle in ("vol", "voiture", "transfert"):
            a["besoins_transport"][cle] = valeur
        else:
            a[cle] = valeur
    jeu_nlu.deriver(a)
    return a


def test_f1_de_remplissage_scalaire():
    a1, a2 = attendu(destination="Djerba"), attendu(destination="Tunis")
    p1, p2 = attendu(destination="Djerba"), attendu(destination=None)
    c = ev.mesurer([(a1, p1), (a2, p2)])["destination"]
    assert (c.vp, c.predits, c.attendus) == (1, 1, 2)
    assert c.precision == 1.0 and c.rappel == 0.5 and c.f1 == pytest.approx(2 / 3) and c.exactitude == 0.5


def test_valeurs_par_defaut_comptees_comme_vides():
    c = ev.mesurer([(attendu(vol="indifferent"), attendu(vol="indifferent"))])["vol"]
    assert (c.predits, c.attendus, c.f1, c.exactitude) == (0, 0, None, 1.0)
    c = ev.mesurer([(attendu(vol="non"), attendu(vol="oui"))])["vol"]
    assert (c.vp, c.predits, c.attendus, c.f1) == (0, 1, 1, 0.0)


def test_listes_et_activites():
    a = attendu(preferences=["plage", "culture"], activites_souhaitees=["musée du Bardo", "quad dans les dunes"])
    p = attendu(preferences=["plage", "desert"], activites_souhaitees=["le musée du bardo", "jet ski"])
    c = ev.mesurer([(a, p)])
    assert (c["preferences"].vp, c["preferences"].predits, c["preferences"].attendus) == (1, 2, 2)
    assert c["activites_souhaitees"].vp == 1 and c["activites_souhaitees"].exactitude == 0.0
    assert c["champs_manquants"].attendus == 4  # destination, duree, budget, voyageurs


def test_macro_exclut_les_champs_de_faible_support_micro_les_garde():
    paires = [(attendu(destination="Djerba", priorite=None), attendu(destination="Djerba")) for _ in range(5)]
    paires[0][0]["preferences_transport"]["priorite"] = "prix"  # support 1
    compteurs = ev.mesurer(paires)
    s = ev.scores(compteurs)
    assert "destination" in s["champs_macro"] and "priorite" in s["exclus"]
    assert s["f1_micro"] < 1.0
    st = ev.scores(compteurs, ev.CHAMPS_TRANSPORT)
    assert st["f1_macro"] is None  # aucun champ transport de support ≥ 5


def test_budget_tolerance_et_28_champs():
    c = ev.mesurer([(attendu(budget_montant=300, budget_devise="TND"), attendu(budget_montant=300.2, budget_devise="TND"))])
    assert c["budget_montant"].vp == 1
    assert len(ev.CHAMPS) == 28 and "horaires" not in {nom for nom, _, _ in ev.CHAMPS}
    assert set(ev.CHAMPS_TRANSPORT) <= {nom for nom, _, _ in ev.CHAMPS} and len(ev.CHAMPS_TRANSPORT) == 8


def test_repartition_dev_test_deterministe_et_stratifiee():
    demandes = [{"id": f"H-{i:03d}", "jeu": None, "attendu": {"langue": "fr" if i % 3 else "ar"}} for i in range(1, 31)]
    demandes.append({"id": "G-900", "jeu": "test", "attendu": {"langue": "fr"}})
    r1 = jeu_nlu.repartir_dev_test(demandes)
    r2 = jeu_nlu.repartir_dev_test(list(reversed(copy.deepcopy(demandes))))
    assert r1 == r2 and r1["G-900"] == "test"
    fr = [d["id"] for d in demandes[:-1] if d["attendu"]["langue"] == "fr"]
    assert sum(r1[i] == "dev" for i in fr) == round(0.4 * len(fr))


def test_jeu_reel_test_et_dev_disjoints():
    dev = {d["id"] for d in jeu_nlu.demandes_du_jeu("dev", relues_seulement=False)}
    test = {d["id"] for d in jeu_nlu.demandes_du_jeu("test", relues_seulement=False)}
    assert not dev & test and len(dev) + len(test) == 192


def test_provenance_sans_llm():
    run = ev.Run("regles", "dev", resultats=[ev.Resultat({}, {}, 1, "regles", False)])
    texte = "\n".join(ev.provenance(run, "v1", "essai", avec_llm=False))
    for attendu in ("Commit Git", "Modifications non commitées", "Variante | —", "aucun (règles seules)",
                    "Demandes évaluées | 1", "Replis sur les règles | 0", "Note | essai"):
        assert attendu in texte


def test_conditions_api_remplace_les_appels_trop_lents_par_les_regles():
    texte = "Je vais à Djerba 3 jours, 300 DT, en famille, culture et plage"
    d = {"texte": texte, "date_reference": "2026-11-09", "attendu": attendu(destination="Djerba", nb_voyageurs=4)}
    bon = attendu(destination="Djerba", nb_voyageurs=4)
    run = ev.Run("hybride", "test", resultats=[ev.Resultat(d, bon, 30000, "hybride", False, 30000),
                                               ev.Resultat(d, bon, 10000, "hybride", False, 10000)])
    api = ev.conditions_api(run, 25.0)
    assert (api["concernes"], api["n"]) == (1, 2)
    c = ev.mesurer([(d["attendu"], bon), (d["attendu"], bon)])
    assert api["scores"]["f1_micro"] < ev.scores(c)["f1_micro"]  # les règles ignorent « 4 voyageurs »
    assert "Conditions API" in "\n".join(ev.lignes_conditions_api(api))


def test_ic_bootstrap_deterministe_et_encadre_le_score():
    paires = [(attendu(destination="Djerba", vol="oui"), attendu(destination="Djerba" if i % 3 else None, vol="oui"))
              for i in range(12)]
    retenus = {"destination", "vol"}
    ic1 = ev.ic_bootstrap(paires, retenus, tirages=200)
    assert ic1 == ev.ic_bootstrap(paires, retenus, tirages=200)
    bas, haut = ic1["f1_macro"]
    s = ev.scores(ev.mesurer(paires), retenus=retenus)["f1_macro"]
    assert bas <= s <= haut and haut <= 1.0
    assert ic1["f1_transport"] == (1.0, 1.0)


def test_echantillon_stratifie():
    demandes = [{"id": f"X-{i:03d}", "attendu": {"langue": lg}} for i, lg in enumerate(["fr"] * 56 + ["ar"] * 23 + ["darija"] * 23 + ["en"] * 13)]
    e = ev.echantillon_stratifie(demandes, 30)
    assert len(e) == 30 and e == ev.echantillon_stratifie(list(reversed(demandes)), 30)
    langues = {lg: sum(d["attendu"]["langue"] == lg for d in e) for lg in ("fr", "ar", "darija", "en")}
    assert langues == {"fr": 15, "ar": 6, "darija": 6, "en": 3}
