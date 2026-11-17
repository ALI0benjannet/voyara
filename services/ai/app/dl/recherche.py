"""Recherche d'activités en direct (travail d'Ons) : TF-IDF, e5 gelé, e5 fine-tuné.

Même catalogue (activites.json), mêmes textes et mêmes préfixes `query:` / `passage:`
que le notebook 05_dl_recherche : les classements affichés sont ceux qui ont été mesurés.
Les modèles sont chargés au premier appel (≈ 1,1 Go de RAM chacun), jamais au démarrage.
"""

import json
import logging
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from app.dl import chemins

logger = logging.getLogger(__name__)

METHODES = ("tfidf", "e5_gele", "e5_fine_tune")


def normaliser(texte: str) -> str:
    return " ".join(unicodedata.normalize("NFC", texte).lower().split())


@dataclass
class Catalogue:
    cles: list[str]
    textes: list[str]
    meta: dict[str, dict[str, Any]]
    requetes_test: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def charger(cls) -> "Catalogue":
        docs = json.loads(chemins.ACTIVITES.read_text(encoding="utf-8"))
        meta = {m["cle"]: m for m in json.loads(chemins.ACTIVITES_META.read_text(encoding="utf-8"))}
        test = {}
        if chemins.REQUETES_TEST.exists():
            for ligne in chemins.REQUETES_TEST.read_text(encoding="utf-8").splitlines():
                if ligne.strip():
                    q = json.loads(ligne)
                    test[normaliser(q["requete"])] = q
        return cls(list(docs), list(docs.values()), meta, test)


class MoteurRecherche:
    """Un classement par méthode ; chaque méthode est construite à la demande puis gardée."""

    def __init__(self, catalogue: Catalogue | None = None,
                 chargeur_modele: Callable[[str], Any] | None = None):
        self._catalogue = catalogue
        self._chargeur = chargeur_modele or _charger_sentence_transformer
        self._index: dict[str, Callable[[str], np.ndarray]] = {}
        self._verrou = threading.Lock()          # protège les dictionnaires ci-dessous
        self._verrous: dict[str, threading.Lock] = {}
        self._en_cours: set[str] = set()
        self._erreurs: dict[str, str] = {}

    @property
    def catalogue(self) -> Catalogue:
        if self._catalogue is None:
            self._catalogue = Catalogue.charger()
        return self._catalogue

    def disponibilites(self) -> dict[str, bool]:
        return {
            "tfidf": True,
            "e5_gele": True,  # local (modeles/) ou téléchargé depuis le hub au premier appel
            "e5_fine_tune": (chemins.E5_FINE_TUNE / "config.json").exists(),
        }

    def _scoreur(self, methode: str) -> Callable[[str], np.ndarray]:
        # Un verrou par méthode : le chargement d'e5 (≈ 1 min) ne bloque pas TF-IDF.
        with self._verrou:
            verrou = self._verrous.setdefault(methode, threading.Lock())
        with verrou:
            if methode not in self._index:
                debut = time.perf_counter()
                self._index[methode] = self._construire(methode)
                logger.info("DL recherche : index %s prêt en %.1f s", methode, time.perf_counter() - debut)
            return self._index[methode]

    def est_pret(self, methode: str) -> bool:
        return methode in self._index

    def prechauffer(self, methodes: list[str] | None = None) -> dict[str, str]:
        """Construit en arrière-plan les index pas encore prêts (le chargement d'e5 dépasse le
        délai de 30 s du gateway sur CPU) ; renvoie l'état de chaque méthode."""
        for methode in methodes or list(METHODES):
            if not self.disponibilites().get(methode) or methode in self._index:
                continue
            with self._verrou:
                if methode in self._en_cours:
                    continue
                self._en_cours.add(methode)
            threading.Thread(target=self._construire_en_fond, args=(methode,), daemon=True).start()
        return self.etats()

    def _construire_en_fond(self, methode: str) -> None:
        try:
            self._scoreur(methode)
            self._erreurs.pop(methode, None)
        except Exception as exc:  # noqa: BLE001 — l'erreur est rapportée par /etat
            logger.exception("DL recherche : échec de construction de l'index %s", methode)
            self._erreurs[methode] = str(exc)[:200]
        finally:
            with self._verrou:
                self._en_cours.discard(methode)

    def etats(self) -> dict[str, str]:
        """`pret` · `chargement` · `erreur` · `a_charger` · `indisponible`."""
        sortie = {}
        for methode, dispo in self.disponibilites().items():
            if not dispo:
                sortie[methode] = "indisponible"
            elif methode in self._index:
                sortie[methode] = "pret"
            elif methode in self._en_cours:
                sortie[methode] = "chargement"
            elif methode in self._erreurs:
                sortie[methode] = "erreur"
            else:
                sortie[methode] = "a_charger"
        return sortie

    def _construire(self, methode: str) -> Callable[[str], np.ndarray]:
        textes = self.catalogue.textes
        if methode == "tfidf":
            from sklearn.feature_extraction.text import TfidfVectorizer

            tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit(textes)
            matrice = tfidf.transform(textes)
            return lambda r: (matrice @ tfidf.transform([r]).T).toarray().ravel()
        if methode == "e5_gele":
            # Copie bfloat16 (moitié moins de mémoire) si elle existe, sinon float32 local, sinon le hub.
            source = next((str(d) for d in (chemins.E5_LOCAL_BF16, chemins.E5_LOCAL)
                           if (d / "model.safetensors").exists()), chemins.E5_HUB)
        elif methode == "e5_fine_tune":
            source = str(chemins.E5_FINE_TUNE)
        else:
            raise ValueError(f"Méthode inconnue : {methode}")
        modele = self._chargeur(source)
        passages = modele.encode([f"passage: {t}" for t in textes], normalize_embeddings=True, batch_size=16)
        return lambda r: passages @ modele.encode([f"query: {r}"], normalize_embeddings=True)[0]

    def rechercher(self, requete: str, methodes: list[str], k: int = 10) -> dict[str, Any]:
        cat = self.catalogue
        attendue = cat.requetes_test.get(normaliser(requete))
        pertinentes = set(attendue["pertinentes"]) if attendue else set()
        sorties = {}
        for methode in methodes:
            if not self.disponibilites().get(methode):
                sorties[methode] = {"disponible": False, "resultats": []}
                continue
            if methode != "tfidf" and not self.est_pret(methode):
                # Modèle lourd pas encore en mémoire : on le charge en arrière-plan et on répond
                # tout de suite (le client relance la recherche une fois le modèle prêt).
                etat = self.prechauffer([methode]).get(methode)
                sorties[methode] = {"disponible": True, "en_chargement": etat == "chargement",
                                    "erreur": etat == "erreur", "resultats": []}
                continue
            debut = time.perf_counter()
            scores = self._scoreur(methode)(requete)
            latence_ms = (time.perf_counter() - debut) * 1000
            ordre = np.argsort(-scores)
            rang_pertinente = next((i + 1 for i, j in enumerate(ordre) if cat.cles[j] in pertinentes), None)
            resultats = []
            for rang, j in enumerate(ordre[:k], 1):
                cle = cat.cles[j]
                m = cat.meta.get(cle, {})
                resultats.append({"rang": rang, "titre": cle, "ville": m.get("ville"),
                                  "categorie": m.get("categorie"), "score": round(float(scores[j]), 4),
                                  "pertinente": cle in pertinentes})
            sorties[methode] = {"disponible": True, "latence_ms": round(latence_ms, 1),
                                "rang_premiere_pertinente": rang_pertinente if attendue else None,
                                "resultats": resultats}
        return {
            "requete": requete,
            "requete_test": ({"id": attendue["id"], "langue": attendue["langue"],
                              "pertinentes": attendue["pertinentes"]} if attendue else None),
            "methodes": sorties,
        }

    def exemples(self) -> list[dict[str, Any]]:
        return [{"id": q["id"], "langue": q["langue"], "requete": q["requete"]}
                for q in self.catalogue.requetes_test.values()]


def _charger_sentence_transformer(source: str | Path):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(str(source), device="cpu")
