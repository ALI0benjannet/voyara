"""Classification des demandes en direct (travail de Boutheina) : type_voyage, vol, voiture.

- `regles` : extracteur par règles de l'étape 4 (méthode « regles », sans LLM) — la baseline
  qui a obtenu le meilleur F1 ;
- `ml_tfidf` : TF-IDF (caractères 2-5) + régression logistique pondérée, entraînée au premier
  appel sur classif_train.jsonl (308 exemples), comme dans le notebook 05_dl_classif_demandes ;
- `xlmr_fine_tune` : modèles XLM-R fine-tunés s'ils ont été copiés dans modeles/ (Drive).
"""

import json
import logging
import threading
import time
from datetime import date
from typing import Any

from app.dl import chemins
from app.nlu.extraction import comprendre

logger = logging.getLogger(__name__)

CHAMPS = ("type_voyage", "vol", "voiture")
METHODES = ("regles", "ml_tfidf", "xlmr_fine_tune")


def etiquette(attendu: dict[str, Any], champ: str) -> str:
    """Même convention que le notebook et baseline_regles_classif.py (« groupe » → « amis »)."""
    if champ == "type_voyage":
        t = attendu.get("type_voyage")
        return "amis" if t == "groupe" else (t or "non_precise")
    return (attendu.get("besoins_transport") or {}).get(champ) or "indifferent"


class Classifieur:
    def __init__(self):
        self._ml: dict[str, Any] | None = None
        self._xlmr: dict[str, Any] | None = None
        self._verrou = threading.Lock()

    def disponibilites(self) -> dict[str, bool]:
        return {
            "regles": True,
            "ml_tfidf": chemins.CLASSIF_TRAIN.exists(),
            "xlmr_fine_tune": all((d / "config.json").exists() for d in chemins.XLMR_FINE_TUNE.values()),
        }

    def _modeles_ml(self) -> dict[str, Any]:
        with self._verrou:
            if self._ml is None:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.linear_model import LogisticRegression
                from sklearn.pipeline import make_pipeline

                lignes = [json.loads(l) for l in chemins.CLASSIF_TRAIN.read_text(encoding="utf-8").splitlines()
                          if l.strip()]
                textes = [e["texte"] for e in lignes]
                self._ml = {}
                for champ in CHAMPS:
                    modele = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5)),
                                           LogisticRegression(max_iter=2000, class_weight="balanced"))
                    self._ml[champ] = modele.fit(textes, [e[champ] for e in lignes])
                logger.info("DL classification : modèles TF-IDF + LogReg entraînés (%d exemples)", len(lignes))
            return self._ml

    def _modeles_xlmr(self) -> dict[str, Any]:
        with self._verrou:
            if self._xlmr is None:
                from transformers import pipeline

                self._xlmr = {champ: pipeline("text-classification", model=str(d), device=-1)
                              for champ, d in chemins.XLMR_FINE_TUNE.items()}
            return self._xlmr

    async def classifier(self, texte: str, methodes: list[str]) -> dict[str, Any]:
        sorties: dict[str, Any] = {}
        dispo = self.disponibilites()
        for methode in methodes:
            if not dispo.get(methode):
                sorties[methode] = {"disponible": False}
                continue
            debut = time.perf_counter()
            if methode == "regles":
                rep = await comprendre(texte, date.today(), methode="regles")
                attendu = rep.demande.vers_attendu()
                predictions = {c: {"etiquette": etiquette(attendu, c), "confiance": None} for c in CHAMPS}
            elif methode == "ml_tfidf":
                predictions = {}
                for champ, modele in self._modeles_ml().items():
                    probas = modele.predict_proba([texte])[0]
                    i = int(probas.argmax())
                    predictions[champ] = {"etiquette": str(modele.classes_[i]), "confiance": round(float(probas[i]), 3)}
            else:
                predictions = {}
                for champ, pipe in self._modeles_xlmr().items():
                    sortie = pipe(texte, truncation=True)[0]
                    predictions[champ] = {"etiquette": sortie["label"], "confiance": round(float(sortie["score"]), 3)}
            sorties[methode] = {"disponible": True, "latence_ms": round((time.perf_counter() - debut) * 1000, 1),
                                "predictions": predictions}
        return {"texte": texte, "methodes": sorties}

    def exemples(self, nombre: int = 16) -> list[dict[str, Any]]:
        """Demandes du jeu de test NLU (jamais vues à l'entraînement), réparties par langue."""
        if not chemins.DEMANDES_NLU.exists():
            return []
        lignes = [json.loads(l) for l in chemins.DEMANDES_NLU.read_text(encoding="utf-8").splitlines() if l.strip()]
        test = [r for r in lignes if r.get("jeu") == "test"]
        par_langue: dict[str, list] = {}
        for r in test:
            r["langue"] = r.get("langue") or r["attendu"].get("langue") or "?"
            par_langue.setdefault(r["langue"], []).append(r)
        choisis = []
        while len(choisis) < nombre and any(par_langue.values()):
            for liste in par_langue.values():
                if liste and len(choisis) < nombre:
                    r = liste.pop(0)
                    choisis.append({"id": r["id"], "langue": r.get("langue"), "texte": r["texte"],
                                    "attendu": {c: etiquette(r["attendu"], c) for c in CHAMPS}})
        return choisis
