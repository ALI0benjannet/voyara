"""Normalisation du module 1, appliquée après les règles **et** après le LLM.

- villes : accents, darija, arabe, noms de gouvernorat (« Kef » → « Le Kef ») → graphie du catalogue ;
- montants : « 300dt », « 1,5k », chiffres arabes ; par personne / nuit / jour → total du groupe ;
- durée : règle unique nuits ↔ jours (README §3) ;
- dates relatives à `date_reference` (demain, ce week-end, vendredi prochain, le 15 mars…) ;
- cohérence finale (voyageurs, transport, hors sujet), puis champs dérivés via `jeu_nlu`.

Aucune valeur n'est inventée : ce qui ne peut pas être déduit reste `None`.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from scripts import jeu_nlu

# --- Texte ----------------------------------------------------------------------

_CHIFFRES_ARABES = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_DIACRITIQUES_ARABES = re.compile(r"[ً-ْٰـ]")  # harakat, alif suscrit, tatweel


def chiffres_ascii(texte: str) -> str:
    return texte.translate(_CHIFFRES_ARABES).replace("٫", ",").replace("٬", " ")


def sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texte) if not unicodedata.combining(c))


def normaliser_arabe(texte: str) -> str:
    texte = _DIACRITIQUES_ARABES.sub("", texte)
    return (texte.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
            .replace("ى", "ي").replace("ة", "ه"))


_CARACTERES_EQUIVALENTS = {"’": "'", "‘": "'", "–": "-", "—": "-", " ": " ", "\xa0": " ",
                            "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "٫": ",", "٬": " "}


def _caractere_normalise(c: str) -> str:
    if c in _CARACTERES_EQUIVALENTS:
        return _CARACTERES_EQUIVALENTS[c]
    c = c.translate(_CHIFFRES_ARABES)
    bas = c.lower()
    if len(bas) == 1:
        c = bas
    if ord(c) < 0x0590:  # accents latins seulement : ئ ou ؤ ne sont pas des « lettres accentuées »
        decompose = unicodedata.normalize("NFKD", c)
        if len(decompose) > 1 and all(unicodedata.combining(x) for x in decompose[1:]):
            c = decompose[0]
    return c


def texte_normalise(texte: str) -> str:
    """Minuscules, sans accents, chiffres ASCII, arabe normalisé (ة → ه, أ → ا…), apostrophes et
    tirets unifiés. **Longueur conservée** (un caractère pour un caractère) : une position trouvée
    dans le texte normalisé désigne le même passage du texte d'origine, ce qui permet de recopier
    une activité telle que le client l'a écrite."""
    return "".join(_caractere_normalise(c) for c in texte)


def contient_arabe(texte: str) -> bool:
    return bool(re.search(r"[؀-ۿ]", texte))


# --- Villes ---------------------------------------------------------------------

# Graphies reconnues (minuscules, sans accents ; arabe normalisé par normaliser_arabe).
ALIAS_VILLES: dict[str, tuple[str, ...]] = {
    "Djerba": ("djerba", "jerba", "jarba", "djerbah", "جربه"),
    "Tunis": ("tunis", "tounes", "tunes", "tunis-carthage", "تونس العاصمه", "تونس"),
    "Sidi Bou Saïd": ("sidi bou said", "sidi bousaid", "sidi bou saad", "sidi bou sa3id", "sidi bouseid",
                      "sidi bou saïd", "سيدي بوسعيد", "سيدي بو سعيد"),
    "Sousse": ("sousse", "souse", "soussa", "sousa", "سوسه"),
    "Hammamet": ("hammamet", "hammamat", "hamamet", "hammemet", "hmamet", "الحمامات", "حمامات"),
    "Monastir": ("monastir", "monastire", "mestir", "monestir", "المنستير", "منستير"),
    "Tozeur": ("tozeur", "touzeur", "tozer", "tozur", "touzer", "توزر"),
    "Kairouan": ("kairouan", "kairaouan", "qairouan", "kerouan", "kairwan", "qayrawan", "القيروان", "قيروان"),
    "Tabarka": ("tabarka", "tbarka", "طبرقه"),
    "Ariana": ("ariana", "aryana", "اريانه"),
    "Ben Arous": ("ben arous", "benarous", "بن عروس"),
    "La Manouba": ("la manouba", "manouba", "منوبه"),
    "Nabeul": ("nabeul", "nabel", "نابل"),
    "Zaghouan": ("zaghouan", "zaghwan", "زغوان"),
    "Bizerte": ("bizerte", "bizerta", "benzart", "bnzart", "بنزرت"),
    "Béja": ("beja", "باجه"),
    "Jendouba": ("jendouba", "جندوبه"),
    "Le Kef": ("le kef", "el kef", "kef", "الكاف"),
    "Siliana": ("siliana", "سليانه"),
    "Mahdia": ("mahdia", "mehdia", "المهديه", "مهديه"),
    "Sfax": ("sfax", "sfaks", "صفاقس"),
    "Kasserine": ("kasserine", "gasrine", "القصرين"),
    "Sidi Bouzid": ("sidi bouzid", "sidi bouzaiene", "سيدي بوزيد"),
    "Gabès": ("gabes", "gabis", "قابس"),
    "Médenine": ("medenine", "mednine", "مدنين"),
    "Tataouine": ("tataouine", "tatouine", "تطاوين"),
    "Gafsa": ("gafsa", "قفصه"),
    "Kébili": ("kebili", "gbelli", "قبلي"),
    "Douz": ("douz", "دوز"),
}
assert set(ALIAS_VILLES) == set(jeu_nlu.VILLES_CATALOGUE)

# Villes de départ hors catalogue : graphie canonique française (README §2).
ALIAS_VILLES_DEPART: dict[str, tuple[str, ...]] = {
    "Paris": ("paris", "باريس"), "Lyon": ("lyon", "ليون"), "Marseille": ("marseille", "مرسيليا"),
    "Toulouse": ("toulouse",), "Nice": ("nice",), "Bordeaux": ("bordeaux",), "Lille": ("lille",),
    "Nantes": ("nantes",), "Strasbourg": ("strasbourg",), "Montpellier": ("montpellier",),
    "Mulhouse": ("mulhouse",), "Genève": ("geneve", "geneva", "جنيف"), "Zurich": ("zurich",),
    "Bruxelles": ("bruxelles", "brussels"), "Londres": ("londres", "london", "لندن"),
    "Milan": ("milan", "milano"), "Rome": ("rome", "roma", "روما"), "Berlin": ("berlin",),
    "Francfort": ("francfort", "frankfurt"), "Munich": ("munich", "munchen"),
    "Amsterdam": ("amsterdam",), "Madrid": ("madrid",), "Barcelone": ("barcelone", "barcelona"),
    "Casablanca": ("casablanca", "الدار البيضاء"), "Alger": ("alger", "algiers"),
    "Tripoli": ("tripoli", "طرابلس"), "Montréal": ("montreal",), "Istanbul": ("istanbul", "اسطنبول"),
    "Dubaï": ("dubai", "دبي"), "Doha": ("doha", "الدوحه"), "Le Caire": ("le caire", "cairo", "القاهره"),
    "Bruxelles-Charleroi": ("charleroi",), "Vienne": ("vienne", "vienna"), "Oran": ("oran", "وهران"),
}

_LETTRE_AR = "ء-ي"


def _motif_alias(alias: str) -> str:
    """Motif d'une graphie : bornes de mot latines ; en arabe, préfixes collés (و ف ب ل ك) admis,
    et « ل + ال » écrit « لل »."""
    echappe = re.escape(alias).replace(r"\ ", r"[\s\-]+")
    if contient_arabe(alias):
        if alias.startswith("ال"):
            corps = f"(?:[وفبك]?{echappe}|[وف]?لل{re.escape(alias[2:])})"
        else:
            corps = f"(?:[وفبلك]|ال)?{echappe}"
        return f"(?<![{_LETTRE_AR}]){corps}(?![{_LETTRE_AR}])"
    return rf"(?<![\w]){echappe}(?![\w])"


def _compiler(alias: dict[str, tuple[str, ...]]) -> list[tuple[re.Pattern, str]]:
    paires = [(a, ville) for ville, graphies in alias.items() for a in graphies]
    paires.sort(key=lambda p: -len(p[0]))  # la graphie la plus longue d'abord (« sidi bou said » avant « sidi »)
    return [(re.compile(_motif_alias(texte_normalise(a))), ville) for a, ville in paires]


_MOTIFS_VILLES = _compiler(ALIAS_VILLES)
_MOTIFS_DEPART = _compiler(ALIAS_VILLES_DEPART)


@dataclass(frozen=True)
class Mention:
    ville: str
    debut: int
    fin: int
    catalogue: bool


def trouver_villes(texte_norm: str) -> list[Mention]:
    """Villes citées dans un texte déjà normalisé, dans l'ordre, sans chevauchement."""
    trouvees: list[Mention] = []
    occupe: list[tuple[int, int]] = []
    for motifs, catalogue in ((_MOTIFS_VILLES, True), (_MOTIFS_DEPART, False)):
        for motif, ville in motifs:
            for m in motif.finditer(texte_norm):
                if any(m.start() < f and d < m.end() for d, f in occupe):
                    continue
                occupe.append((m.start(), m.end()))
                trouvees.append(Mention(ville, m.start(), m.end(), catalogue))
    return sorted(trouvees, key=lambda x: x.debut)


def ville_catalogue(nom: Any) -> str | None:
    """Nom libre (sortie du LLM, saisie) → ville du catalogue, ou None si hors catalogue."""
    if not isinstance(nom, str) or not nom.strip():
        return None
    if nom in jeu_nlu.VILLES_CATALOGUE:
        return nom
    norm = texte_normalise(nom.strip())
    for motif, ville in _MOTIFS_VILLES:
        m = motif.fullmatch(norm) or motif.search(norm)
        if m and len(m.group(0)) >= len(norm) - 4:  # le nom entier, pas un mot au milieu d'une phrase
            return ville
    return None


def ville_canonique(nom: Any) -> str | None:
    """Ville de départ : graphie du catalogue ou graphie française connue ; sinon le nom tel quel."""
    if not isinstance(nom, str) or not nom.strip():
        return None
    catalogue = ville_catalogue(nom)
    if catalogue:
        return catalogue
    norm = texte_normalise(nom.strip())
    for motif, ville in _MOTIFS_DEPART:
        if motif.fullmatch(norm):
            return ville
    return nom.strip()


# --- Montants -------------------------------------------------------------------

def parser_montant(texte: str) -> float | None:
    """« 300 », « 1,5k », « 1.5 k », « 3 500 », « ٣٠٠ » → nombre ; None si illisible."""
    t = chiffres_ascii(texte).strip().lower().replace(" ", " ").replace("\xa0", " ")
    mille = t.endswith("k")
    t = t.rstrip("k").strip()
    if re.fullmatch(r"\d{1,3}(?:[ .]\d{3})+", t):  # séparateur de milliers
        t = re.sub(r"[ .]", "", t)
    t = t.replace(",", ".")
    try:
        valeur = float(t)
    except ValueError:
        return None
    return valeur * 1000 if mille else valeur


def vers_total(montant: float | None, base: str | None, nb_voyageurs: int | None, nb_nuits: int | None,
               duree_jours: int | None, par_personne_aussi: bool = False) -> float | None:
    """Montant dit → total du groupe (README §3) ; None si le multiplicateur est inconnu."""
    if montant is None or base in (None, "total"):
        return montant
    total = montant
    if base == "par_personne" or par_personne_aussi:
        if not nb_voyageurs:
            return None
        total *= nb_voyageurs
    if base == "par_nuit":
        if nb_nuits is None:
            return None
        total *= max(nb_nuits, 1)
    elif base == "par_jour":
        if duree_jours is None:
            return None
        total *= duree_jours
    return total


# --- Durée ----------------------------------------------------------------------

def completer_duree(jours: int | None, nuits: int | None) -> tuple[int | None, int | None]:
    """Règle unique : si un seul est donné, l'autre lui est égal ; deux valeurs incohérentes
    (nuits ∉ {jours − 1, jours}) → les nuits suivent les jours."""
    if jours is None and nuits is None:
        return None, None
    if jours is None:
        return max(nuits, 1), nuits
    if nuits is None or nuits not in (jours - 1, jours):
        return jours, jours
    return jours, nuits


# --- Dates relatives ------------------------------------------------------------

MOIS = {
    1: ("janvier", "january", "jan", "janv", "جانفي", "يناير", "janfi"),
    2: ("fevrier", "february", "feb", "fev", "فيفري", "فبراير", "fivri"),
    3: ("mars", "march", "mar", "مارس"),
    4: ("avril", "april", "apr", "افريل", "ابريل"),
    5: ("mai", "may", "ماي", "مايو"),
    6: ("juin", "june", "jun", "جوان", "يونيو"),
    7: ("juillet", "july", "jul", "جويليه", "يوليو"),
    8: ("aout", "august", "aug", "اوت", "اغسطس"),
    9: ("septembre", "september", "sept", "sep", "سبتمبر"),
    10: ("octobre", "october", "oct", "اكتوبر"),
    11: ("novembre", "november", "nov", "نوفمبر"),
    12: ("decembre", "december", "dec", "ديسمبر"),
}
JOURS_SEMAINE = {
    0: ("lundi", "monday", "الاثنين", "الاتنين", "tnin", "ltnin"),
    1: ("mardi", "tuesday", "الثلاثاء", "tlatha"),
    2: ("mercredi", "wednesday", "الاربعاء", "larb3a"),
    3: ("jeudi", "thursday", "الخميس", "lkhmis"),
    4: ("vendredi", "friday", "الجمعه", "jem3a"),
    5: ("samedi", "saturday", "السبت", "sebt", "essebt"),
    6: ("dimanche", "sunday", "الاحد", "a7ad", "la7ad"),
}


def prochaine_occurrence(jour: int, mois: int, reference: date) -> date | None:
    """Date sans année → prochaine occurrence ≥ référence (None si le jour n'existe pas)."""
    for annee in (reference.year, reference.year + 1):
        try:
            candidate = date(annee, mois, jour)
        except ValueError:
            continue
        if candidate >= reference:
            return candidate
    return None


def jour_semaine_suivant(jour_semaine: int, reference: date) -> date:
    """Première occurrence strictement après la référence."""
    ecart = (jour_semaine - reference.weekday()) % 7 or 7
    return reference + timedelta(days=ecart)


def ce_week_end(reference: date) -> date:
    """Samedi de la semaine en cours (la référence elle-même si c'est un samedi)."""
    return reference + timedelta(days=(5 - reference.weekday()) % 7)


def semaine_prochaine(reference: date) -> date:
    return reference + timedelta(days=7 - reference.weekday())


def mois_prochain(reference: date) -> date:
    return date(reference.year + reference.month // 12, reference.month % 12 + 1, 1)


# --- Valeurs du LLM -------------------------------------------------------------

def besoin(valeur: Any) -> str:
    """« yes », true, « oui »… → vocabulaire `oui | non | indifferent`."""
    if valeur is True:
        return "oui"
    if valeur is False:
        return "non"
    texte = texte_normalise(str(valeur or ""))
    if texte in ("oui", "yes", "true", "y", "1"):
        return "oui"
    if texte in ("non", "no", "false", "n", "0"):
        return "non"
    return "indifferent"


def entier_ou_none(valeur: Any) -> int | None:
    if isinstance(valeur, bool) or valeur is None:
        return None
    try:
        nombre = float(valeur)
    except (TypeError, ValueError):
        return None
    return int(nombre) if nombre.is_integer() else None


def booleen_ou_none(valeur: Any) -> bool | None:
    if isinstance(valeur, bool) or valeur is None:
        return valeur
    texte = texte_normalise(str(valeur))
    return True if texte in ("true", "vrai", "oui", "yes") else False if texte in ("false", "faux", "non", "no") else None


# --- Cohérence finale -----------------------------------------------------------

def _voyageurs_coherents(d: dict) -> None:
    n, a, e, t = d.get("nb_voyageurs"), d.get("nb_adultes"), d.get("nb_enfants"), d.get("type_voyage")
    for cle, mini in (("nb_voyageurs", 1), ("nb_adultes", 1), ("nb_enfants", 0)):
        valeur = d.get(cle)
        if valeur is not None and not (mini <= valeur <= 500):
            d[cle] = None
    n, a, e = d.get("nb_voyageurs"), d.get("nb_adultes"), d.get("nb_enfants")
    if t == "solo":
        if n in (None, 1):
            n, a, e = 1, 1, 0
        else:
            t = None
    if t == "couple" and n in (None, 2) and a in (None, 2) and e in (None, 0):
        n, a, e = 2, 2, 0
    if t == "couple" and a not in (None, 2):
        t = None
    if a is not None and e is not None:
        if n is None:
            n = a + e
        elif n != a + e:
            a = e = None
    elif (a is None) != (e is None):
        if n is not None and a is not None and a <= n:
            e = n - a
        elif n is not None and e is not None and e < n:
            a = n - e
        else:
            a = e = None
    d.update(nb_voyageurs=n, nb_adultes=a, nb_enfants=e, type_voyage=t)


def _nettoyer_liste(valeurs: Any, autorisees: tuple | None = None) -> list:
    sortie: list = []
    vus: set[str] = set()
    for v in valeurs or []:
        if not isinstance(v, str):
            continue
        v = v.strip().strip(".,;:!?«»\"'").strip()
        cle = v.lower()
        if not v or cle in vus:
            continue
        if autorisees is not None and v not in autorisees:
            continue
        vus.add(cle)
        sortie.append(v)
    return sortie


def _activites_propres(valeurs: Any) -> list[str]:
    sortie = []
    for activite in _nettoyer_liste(valeurs):
        activite = activite.replace(";", ",")
        if len(activite) > jeu_nlu.LONGUEUR_MAX_ACTIVITE:
            continue
        # Une ville du catalogue n'est pas une activité (README §3) ; un thème seul non plus.
        if ville_catalogue(activite) == activite or ville_catalogue(activite) and len(activite.split()) <= 2:
            continue
        if texte_normalise(activite) in _THEMES_SEULS:
            continue
        sortie.append(activite)
    return sortie


_THEMES_SEULS = {"plage", "mer", "desert", "sahra", "culture", "histoire", "nature", "detente", "gastronomie",
                 "shopping", "sports nautiques", "visites culturelles", "beach", "sea", "البحر", "بحر", "الصحراء"}


def normaliser_demande(brut: dict[str, Any]) -> dict[str, Any]:
    """Dictionnaire brut (règles, LLM ou fusion) → dictionnaire cohérent, prêt pour la validation.

    Clés internes facultatives : `_budget_par_personne_aussi` (« par personne et par nuit »).
    `budget_montant` y est le montant **tel que dit** ; il devient ici le total du groupe."""
    d = dict(brut)
    par_personne_aussi = bool(d.pop("_budget_par_personne_aussi", False))
    hors_transport = bool(d.pop("_budget_hors_transport", False))
    for cle in [k for k in d if k.startswith("_")]:
        d.pop(cle)

    if d.get("hors_sujet"):
        return demande_hors_sujet(d.get("langue") or "fr")

    # Villes
    destination = ville_catalogue(d.get("destination"))
    autres = []
    for ville in d.get("autres_villes") or []:
        canon = ville_catalogue(ville)
        if canon and canon != destination and canon not in autres:
            autres.append(canon)
    if destination is None:
        autres = []  # pas de circuit sans destination principale
    depart = ville_canonique(d.get("ville_depart"))
    if depart is not None and depart == destination:
        depart = None
    d.update(destination=destination, autres_villes=autres, ville_depart=depart)

    # Durée
    jours, nuits = entier_ou_none(d.get("duree_jours")), entier_ou_none(d.get("nb_nuits"))
    if jours is not None and not 1 <= jours <= jeu_nlu.DUREE_MAX_JOURS:
        jours = None
    if nuits is not None and not 0 <= nuits <= jeu_nlu.DUREE_MAX_JOURS:
        nuits = None
    d["duree_jours"], d["nb_nuits"] = completer_duree(jours, nuits)

    # Voyageurs
    for cle in ("nb_voyageurs", "nb_adultes", "nb_enfants"):
        d[cle] = entier_ou_none(d.get(cle))
    if d.get("type_voyage") not in jeu_nlu.TYPES_VOYAGE:
        d["type_voyage"] = None
    _voyageurs_coherents(d)

    # Budget : montant dit → total
    montant = d.get("budget_montant")
    if isinstance(montant, str):
        montant = parser_montant(montant)
    if isinstance(montant, bool) or not isinstance(montant, (int, float)) or montant <= 0:
        montant = None
    base = d.get("budget_base") if d.get("budget_base") in jeu_nlu.BASES_BUDGET else "total"
    devise = (d.get("budget_devise") or "TND").upper() if montant is not None else None
    if devise is not None and not re.fullmatch(r"[A-Z]{3}", devise):
        devise = "TND"
    total = vers_total(montant, base, d["nb_voyageurs"], d["nb_nuits"], d["duree_jours"], par_personne_aussi)
    if total is not None:
        total = round(total, 2)
        total = int(total) if float(total).is_integer() else total
    illimite = bool(d.get("budget_illimite")) and total is None
    d.update(budget_montant=total, budget_devise=devise if total is not None else None,
             budget_base=base if total is not None else None, budget_illimite=illimite)

    # Listes
    d["preferences"] = _nettoyer_liste(d.get("preferences"), jeu_nlu.THEMES)
    d["activites_souhaitees"] = _activites_propres(d.get("activites_souhaitees"))

    # Contraintes
    c = dict(d.get("contraintes") or {})
    niveau = entier_ou_none(c.get("niveau_marche_max"))
    mobilite = booleen_ou_none(c.get("mobilite_reduite"))
    if mobilite is False:
        mobilite = None  # README : `true` ou `null`
    if mobilite and niveau is None:
        niveau = 1
    horaires = c.get("horaires") if isinstance(c.get("horaires"), str) and c.get("horaires").strip() else None
    d["contraintes"] = {"niveau_marche_max": niveau if niveau in (1, 2, 3) else None,
                        "mobilite_reduite": mobilite, "horaires": horaires[:120] if horaires else None}

    # Transport
    b = dict(d.get("besoins_transport") or {})
    d["besoins_transport"] = {k: besoin(b.get(k)) for k in ("vol", "voiture", "transfert")}
    p = dict(d.get("preferences_transport") or {})
    priorite = p.get("priorite") if p.get("priorite") in jeu_nlu.PRIORITES else None
    d["preferences_transport"] = {"vol_direct": booleen_ou_none(p.get("vol_direct")),
                                  "boite_auto": booleen_ou_none(p.get("boite_auto")), "priorite": priorite}
    besoin_oui = "oui" in d["besoins_transport"].values()
    # README : vrai si au moins un besoin vaut « oui », sauf si le texte dit le contraire.
    if hors_transport or not besoin_oui:
        d["budget_inclut_transport"] = False
    else:
        d["budget_inclut_transport"] = True
    if d.get("langue") not in jeu_nlu.LANGUES:
        d["langue"] = "fr"
    d["hors_sujet"] = False
    return d


def demande_hors_sujet(langue: str) -> dict[str, Any]:
    """Demande hors sujet : tous les champs `null` ou par défaut (README §3)."""
    return {
        "destination": None, "autres_villes": [], "date_debut": None, "duree_jours": None, "nb_nuits": None,
        "budget_montant": None, "budget_devise": None, "budget_base": None, "budget_illimite": False,
        "nb_voyageurs": None, "nb_adultes": None, "nb_enfants": None, "type_voyage": None,
        "preferences": [], "activites_souhaitees": [],
        "contraintes": {"niveau_marche_max": None, "mobilite_reduite": None, "horaires": None},
        "langue": langue if langue in jeu_nlu.LANGUES else "fr", "ville_depart": None,
        "besoins_transport": {"vol": "indifferent", "voiture": "indifferent", "transfert": "indifferent"},
        "preferences_transport": {"vol_direct": None, "boite_auto": None, "priorite": None},
        "budget_inclut_transport": False, "hors_sujet": True,
    }


def champs_manquants(demande: dict[str, Any]) -> list[str]:
    """Règle des champs essentiels : celle du jeu d'évaluation, importée."""
    return jeu_nlu.champs_manquants(demande)
