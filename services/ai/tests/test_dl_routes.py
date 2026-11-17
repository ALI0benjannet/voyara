"""Routes /api/ai/dl/* : sans base ni LLM ; e5 remplacé par un faux encodeur (aucun téléchargement)."""

import numpy as np
from fastapi.testclient import TestClient

from app.dl import classification as clf
from app.dl import recherche as rech
from app.dl.resultats import tous_les_resultats
from app.main import app

client = TestClient(app)  # sans `with` : pas de lifespan (pas de base postgres-ai)

CATALOGUE = rech.Catalogue(
    cles=["Plongée aux récifs de Tabarka", "Bivouac dans le désert de Douz", "Cours de cuisine tunisienne"],
    textes=["Plongée sous-marine, corail, Tabarka", "Nuit sous la tente dans les dunes du Sahara, Douz",
            "Apprendre le couscous et la brik, Tunis"],
    meta={"Plongée aux récifs de Tabarka": {"ville": "Tabarka", "categorie": "Mer"}},
    requetes_test={"plongée à tabarka": {"id": "R-002", "langue": "fr", "requete": "plongée à Tabarka",
                                         "pertinentes": ["Plongée aux récifs de Tabarka"]}},
)


class FauxEncodeur:
    """Encode par mots-clés : suffisant pour vérifier le classement et les préfixes e5."""
    MOTS = ("plong", "dune", "couscous")

    def __init__(self):
        self.vus: list[str] = []

    def encode(self, textes, normalize_embeddings=True, batch_size=16):
        self.vus += textes
        v = np.array([[1.0 if m in t.lower() else 0.0 for m in self.MOTS] + [0.1] for t in textes])
        return v / np.linalg.norm(v, axis=1, keepdims=True)


def setup_function():
    encodeur = FauxEncodeur()
    app.state.dl_recherche = rech.MoteurRecherche(CATALOGUE, chargeur_modele=lambda source: encodeur)
    app.state.dl_encodeur = encodeur
    app.state.dl_classif = clf.Classifieur()


def teardown_function():
    for nom in ("dl_recherche", "dl_encodeur", "dl_classif"):
        delattr(app.state, nom)


def test_resultats_lit_les_csv_du_depot():
    r = client.get("/api/ai/dl/resultats")
    assert r.status_code == 200
    corps = r.json()
    approches = {l["approche"] for l in corps["recherche"]["global"]}
    assert "DL Transfer Learning (e5 gelé)" in approches
    assert {l["champ"] for l in corps["classification"]["global"]} == {"type_voyage", "vol", "voiture"}


def test_resultats_dossier_absent_renvoie_des_listes_vides(tmp_path):
    vide = tous_les_resultats(tmp_path)
    assert vide["recherche"]["global"] == [] and vide["classification"]["regles"] == []


def test_recherche_requete_du_test_marque_les_pertinentes():
    app.state.dl_recherche._scoreur("e5_gele")  # modèle déjà en mémoire
    r = client.post("/api/ai/dl/rechercher", json={"requete": "  Plongée à Tabarka ", "methodes": ["tfidf", "e5_gele"], "k": 3})
    assert r.status_code == 200
    corps = r.json()
    assert corps["requete_test"]["id"] == "R-002"
    for methode in ("tfidf", "e5_gele"):
        m = corps["methodes"][methode]
        assert m["disponible"] and len(m["resultats"]) == 3
        assert m["resultats"][0]["titre"] == "Plongée aux récifs de Tabarka"
        assert m["resultats"][0]["pertinente"] and m["rang_premiere_pertinente"] == 1
    vus = app.state.dl_encodeur.vus
    assert all(t.startswith("passage: ") for t in vus[:3]) and vus[3] == "query: Plongée à Tabarka"


def test_modele_pas_pret_repond_tout_de_suite_puis_se_charge_en_fond():
    import threading

    feu = threading.Event()
    encodeur = FauxEncodeur()

    def chargeur_lent(source):
        feu.wait(5)
        return encodeur

    app.state.dl_recherche = rech.MoteurRecherche(CATALOGUE, chargeur_modele=chargeur_lent)
    corps = client.post("/api/ai/dl/rechercher", json={"requete": "plongée", "methodes": ["tfidf", "e5_gele"]}).json()
    assert corps["methodes"]["tfidf"]["resultats"]                       # TF-IDF répond sans attendre
    assert corps["methodes"]["e5_gele"] == {"disponible": True, "en_chargement": True, "erreur": False,
                                             "resultats": []}
    assert client.get("/api/ai/dl/etat").json()["recherche_etats"]["e5_gele"] == "chargement"
    feu.set()
    for _ in range(50):
        if app.state.dl_recherche.est_pret("e5_gele"):
            break
        threading.Event().wait(0.1)
    assert client.post("/api/ai/dl/prechauffer").json()["e5_gele"] == "pret"
    corps = client.post("/api/ai/dl/rechercher", json={"requete": "plongée", "methodes": ["e5_gele"]}).json()
    assert corps["methodes"]["e5_gele"]["resultats"][0]["titre"] == "Plongée aux récifs de Tabarka"


def test_recherche_hors_test_et_fine_tune_absent():
    app.state.dl_recherche._scoreur("e5_gele")
    r = client.post("/api/ai/dl/rechercher", json={"requete": "dormir dans les dunes"})
    corps = r.json()
    assert corps["requete_test"] is None
    assert corps["methodes"]["e5_gele"]["resultats"][0]["titre"] == "Bivouac dans le désert de Douz"
    assert corps["methodes"]["e5_gele"]["rang_premiere_pertinente"] is None
    assert corps["methodes"]["e5_fine_tune"] == {"disponible": False, "resultats": []}


def test_classification_regles_et_ml():
    texte = "Je vais à Djerba avec ma femme, on prend l'avion depuis Tunis"
    r = client.post("/api/ai/dl/classifier", json={"texte": texte})
    assert r.status_code == 200
    m = r.json()["methodes"]
    assert m["regles"]["predictions"]["type_voyage"]["etiquette"] == "couple"
    assert m["regles"]["predictions"]["vol"]["etiquette"] == "oui"
    ml = m["ml_tfidf"]["predictions"]
    assert set(ml) == {"type_voyage", "vol", "voiture"} and 0 < ml["vol"]["confiance"] <= 1
    assert m["xlmr_fine_tune"] == {"disponible": False}


def test_exemples_et_etat():
    corps = client.get("/api/ai/dl/exemples").json()
    assert corps["recherche"][0]["id"] == "R-002"
    assert len(corps["classification"]) == 16
    assert {e["langue"] for e in corps["classification"]} == {"fr", "en", "ar", "darija"}
    etat = client.get("/api/ai/dl/etat").json()
    assert etat["recherche"]["tfidf"] and etat["classification"]["regles"]


def test_corps_invalides_422():
    assert client.post("/api/ai/dl/rechercher", json={"requete": "   "}).status_code == 422
    assert client.post("/api/ai/dl/rechercher", json={"requete": "x", "methodes": ["bm25"]}).status_code == 422
    assert client.post("/api/ai/dl/classifier", json={"texte": ""}).status_code == 422
