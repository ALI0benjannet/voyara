"""Extracteur déterministe du module 1 (fr / en / darija / ar), sans réseau ni LLM.

Rôle en mode hybride : les faits explicites (montants, devise, durée, nuits, dates, villes, langue,
mots-clés de transport). Il sert aussi de repli complet quand le LLM est absent, lent ou invalide.
Chaque champ trouvé par un motif explicite est marqué « sûr » : à la fusion, il l'emporte sur le LLM.

Motifs mis au point **uniquement sur le jeu dev** (nlu_dev.jsonl + 40 % des demandes humaines,
`jeu_nlu.repartir_dev_test`). Ils s'appliquent au texte normalisé (`texte_normalise` : minuscules,
sans accents, arabe normalisé, longueur conservée).
"""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.nlu import normalisation as n

# --- Nombres --------------------------------------------------------------------

NOMBRES = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8,
    "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "quinze": 15, "vingt": 20,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "twelve": 12, "fifteen": 15, "twenty": 20,
    "wa7ed": 1, "wahed": 1, "zouz": 2, "zouj": 2, "tlatha": 3, "tletha": 3, "thletha": 3, "tlata": 3,
    "arb3a": 4, "arba": 4, "5amsa": 5, "khamsa": 5, "setta": 6, "sab3a": 7, "thmanya": 8, "tes3a": 9,
    "3achra": 10,
    "واحد": 1, "اثنين": 2, "اثنان": 2, "زوز": 2, "ثلاثه": 3, "ثلاث": 3, "تلاثه": 3, "اربعه": 4, "اربع": 4,
    "خمسه": 5, "خمس": 5, "سته": 6, "ست": 6, "سبعه": 7, "سبع": 7, "ثمانيه": 8, "ثماني": 8, "تسعه": 9,
    "تسع": 9, "عشره": 10, "عشر": 10,
}
_PREFIXES_AR = ("ل", "و", "ب")
_MOTS_NOMBRES = sorted({*NOMBRES, *(p + m for m in NOMBRES if n.contient_arabe(m) for p in _PREFIXES_AR)},
                       key=len, reverse=True)
NUM = r"(\d+|" + "|".join(map(re.escape, _MOTS_NOMBRES)) + r")"


def nombre(jeton: str) -> int | None:
    if jeton.isdigit():
        return int(jeton)
    if jeton in NOMBRES:
        return NOMBRES[jeton]
    if jeton[:1] in _PREFIXES_AR and jeton[1:] in NOMBRES:
        return NOMBRES[jeton[1:]]
    return None


def _cherche(motif: str, texte: str) -> re.Match | None:
    return re.search(motif, texte)


def _variantes_ar(mot: str) -> str:
    """Mot arabe : préfixes collés admis (و ف ب ل), et « ل + ال » écrit « لل »."""
    if not n.contient_arabe(mot):
        return mot
    if mot.startswith("ال"):
        return f"(?:[وفب]?{mot}|[وف]?لل{mot[2:]})"
    return f"(?:[وفبل]?{mot})"


def _un_de(mots: list[str] | tuple[str, ...]) -> str:
    """Alternative de mots ou expressions, bornée (fonctionne aussi pour l'arabe : \\b Unicode)."""
    return r"(?<!\w)(?:" + "|".join(_variantes_ar(m) for m in sorted(mots, key=len, reverse=True)) + r")(?!\w)"


# --- Résultat -------------------------------------------------------------------

@dataclass
class ResultatRegles:
    brut: dict[str, Any]
    surs: set[str] = field(default_factory=set)  # champs (ou groupes) trouvés par un motif explicite


# --- Langue ---------------------------------------------------------------------

_DARIJA = ["n7eb", "nheb", "n7ebou", "nhebou", "n7ebbou", "nemchi", "nemchiw", "nemchou", "m3a", "s7abi",
           "s7abna", "wa7di", "wa7ed", "3aslema", "aslema", "ena", "ahna", "karhba", "lkol", "bghit", "chnowa",
           "chneya", "barcha", "mrati", "mrti", "5ti", "kraya", "nekri", "lilet", "iyem", "tayara", "fil", "mel",
           "ma3andnach", "wala", "zouz", "nhar", "sa7bti", "mte3na", "kifech", "9adech", "nsou9ou", "b7ar",
           "lb7ar", "sahra", "a7sen", "njik", "3ammi", "wled", "chwaya", "ya3tik", "kol wa7ed", "l wa7ed",
           "n7ebch", "n7ebouch", "lil", "program", "famille", "budjet"]
_DARIJA_FORTS = set(_DARIJA) - {"famille", "program", "budjet", "sahra", "fil", "lil", "mel", "wala", "nhar"}
_ANGLAIS = ["the", "and", "with", "for", "we", "i", "my", "me", "days", "day", "trip", "want", "need",
            "from", "to", "of", "in", "flying", "please", "kids", "around", "each", "friends", "nights",
            "week", "is", "are", "our", "us", "would", "like", "help", "can", "you", "love", "rent", "car"]
_FRANCAIS = ["je", "nous", "on", "avec", "pour", "jours", "le", "la", "les", "des", "une", "un", "et", "de",
             "du", "a", "au", "sur", "vol", "voiture", "souhaite", "voudrais", "cherche", "est", "sommes",
             "personnes", "nuits", "semaine", "depuis", "mon", "ma", "mes", "veux", "aimerait", "pas", "en"]


def detecter_langue(texte: str, t: str) -> str:
    lettres_ar = len(re.findall(r"[؀-ۿ]", texte))
    lettres_lat = len(re.findall(r"[A-Za-zÀ-ÿ]", texte))
    if lettres_ar > lettres_lat:
        return "ar"
    mots = re.findall(r"[\w']+", t)
    darija = sum(m in _DARIJA_FORTS for m in mots)
    darija += len(re.findall(r"(?<![\w])(?:[a-z]+[3579][a-z]+|[3579][a-z]{2,}|[a-z]{2,}[3579])(?![\w])", t))
    if darija >= 2 or (darija >= 1 and len(mots) <= 6):
        return "darija"
    anglais = sum(m in _ANGLAIS for m in mots)
    francais = sum(m.split("'")[-1] in _FRANCAIS or m.startswith(("j'", "l'", "d'", "c'", "qu'")) for m in mots)
    return "en" if anglais > francais else "fr"


# --- Hors sujet -----------------------------------------------------------------

_SIGNAUX_VOYAGE = _un_de([
    "voyage", "voyager", "sejour", "sejourner", "vacances", "partir", "pars", "part", "aller", "visiter",
    "visite", "decouvrir", "excursion", "circuit", "week-?end", "hotel", "nuits?", "jours?", "trip", "travel",
    "holiday", "vacation", "visit", "stay", "fly", "flight", "flying", "nemchi", "nemchiw", "n7eb nemchi",
    "rihla", "رحله", "سفر", "عطله", "زياره", "نزور", "نمشي", "نمشيو", "برنامج", "program", "plage", "desert",
    "vol", "transfert", "budget", "dt", "dinars?", "دينار", "ميزانيه", "اريد زياره", "lune de miel",
])
_INJECTION = _un_de([
    r"ignore[sz]? (?:all |toutes |les |previous |the |tes |vos )*(?:instructions|consignes|regles)",
    r"system prompt", r"prompt systeme", r"tu es maintenant", r"you are now", r"oublie (?:tes|vos) (?:instructions|consignes)",
])


def est_hors_sujet(t: str, villes: list[n.Mention]) -> bool:
    if re.search(_INJECTION, t):
        return True
    return not villes and not re.search(_SIGNAUX_VOYAGE, t)


# --- Villes ---------------------------------------------------------------------

_AVANT_DEPART = re.compile(
    r"(?:depuis|de|d'|from|men|mel|min|من|du|partir de|part de|arrive de|arrivons de|venons de|vient de|"
    r"venir de|en provenance de|flying from|fly from|vol depuis)\s*$")
_AVANT_RESIDENCE = re.compile(
    r"(?:j'habite|habite|je vis|je vis a|vivant|etudiant(?: \w+)? a|i live in|based in|live in|je suis a|resident a|"
    r"installe a|sakn f|nskon f)\s*(?:a|à|in|f)?\s*$")
_AVANT_PROXIMITE = re.compile(r"(?:autour|pres|proche|cote|loin|environs|region|alentours) d(?:e |e|')\s*$|around\s*$|near\s*$")
_AVANT_EXCLU = re.compile(r"(?:aeroport(?: de| d'|)|airport|مطار|via|sinon via|escale a|escale en)\s*$")
_APRES_EXCLU = re.compile(r"^\s*(?:airport|aeroport)")


def extraire_villes(t: str, villes: list[n.Mention]) -> tuple[str | None, list[str], str | None, bool]:
    """(destination, autres_villes, ville_depart, depart_sur)."""
    depart: str | None = None
    destinations: list[str] = []
    aeroports: list[str] = []  # « aéroport de Djerba » : destination seulement si aucune autre ville
    for i, m in enumerate(villes):
        avant = t[max(0, m.debut - 30):m.debut]
        apres = t[m.fin:m.fin + 15]
        if _AVANT_EXCLU.search(avant) or _APRES_EXCLU.search(apres):
            if m.catalogue and not re.search(r"(?:via|sinon via|escale a|escale en)\s*$", avant):
                aeroports.append(m.ville)
            continue
        if _AVANT_RESIDENCE.search(avant) and depart is None:
            depart = m.ville
            continue
        if _AVANT_PROXIMITE.search(avant):
            if m.catalogue and m.ville not in destinations and m.ville != depart:
                destinations.append(m.ville)
            continue
        # « Paris-Tozeur », « Toulouse → Djerba » : la première est le départ
        suivante = villes[i + 1] if i + 1 < len(villes) else None
        tiret = suivante is not None and re.fullmatch(r"\s*(?:-|→|->|>|vers|to|الى|إلى)\s*", t[m.fin:suivante.debut])
        if (tiret or _AVANT_DEPART.search(avant)) and depart is None:
            # « kraya karhba men sousse » : une ville aussi citée comme destination n'est pas le départ
            ailleurs = any(v.ville == m.ville and v is not m and not _AVANT_DEPART.search(t[max(0, v.debut - 30):v.debut])
                           for v in villes)
            if not ailleurs:
                depart = m.ville
                continue
        if m.catalogue and m.ville not in destinations and m.ville != depart:
            destinations.append(m.ville)
    if not destinations:
        destinations = [v for v in dict.fromkeys(aeroports) if v != depart]
    destination = destinations[0] if destinations else None
    return destination, destinations[1:], depart, depart is not None


# --- Durée ----------------------------------------------------------------------

_JOURS = r"(?:jours?|j|days?|iyem|iyam|ayem|ayam|ايام|يوم|نهارات|يام)"
_NUITS = r"(?:nuits?|nuitees?|nights?|lilet|lyali|ليال|ليالي|ليله|nuitee)"


def extraire_duree(t: str) -> tuple[int | None, int | None]:
    jours = nuits = None
    # Fourchette « 2 ou 3 jours », « nhar wala zouz » → borne haute
    m = re.search(rf"(?<!\w){NUM}\s*(?:ou|or|wala|ولا|او|-|a)\s*{NUM}\s*{_JOURS}(?!\w)", t)
    if m and nombre(m.group(2)):
        jours = nombre(m.group(2))
    elif re.search(r"nhar (?:wala|ou|or) (?:zouz|2|joj)|نهار ولا زوز|نهار والا نهارين", t):
        jours = 2
    if jours is None:
        m = re.search(rf"(?<![\w/-]){NUM}\s*-?\s*{_JOURS}(?!\w)", t)
        if m and not re.search(r"(?:dans|il y a|in|after)\s*$", t[:m.start()]):
            jours = nombre(m.group(1))
    if jours is None and re.search(r"(?<!\w)(?:يومان|يومين|نهارين|jourin)(?!\w)", t):
        jours = 2
    m = re.search(rf"(?<!\w){NUM}\s*-?\s*{_NUITS}(?!\w)", t)
    if m:
        nuits = nombre(m.group(1))
    elif re.search(r"(?<!\w)(?:ليلتين|ليلتان)(?!\w)", t):
        nuits = 2
    if jours is None and nuits is None:
        if re.search(r"(?<!\w)(?:deux|2|two) (?:semaines|weeks)|اسبوعين|جمعتين|zouz jem3at", t):
            jours = 14
        elif re.search(r"(?<!\w)(?:une|1|one|a) (?:semaine|week)(?!\w)|(?<!\w)(?:اسبوع|جمعه كامله|simana|semaine)(?!\w)", t):
            jours = 7
        elif re.search(r"(?<!\w)(?:un|1|one|a) (?:mois|month)(?!\w)|(?<!\w)شهر(?! عسل)(?!\w)", t):
            jours = 30
        elif re.search(r"week-?end|wikend|ويكاند|ويك اند|ويكند|ويك-اند", t):
            jours = 2
        elif re.search(r"une journee|day trip|dans la journee|in one day|in a day|nhar wa7ed|نهار واحد|"
                       r"نفس النهار|نفس اليوم|(?<!\w)نهار(?! ال)(?!\w)|aller-retour dans la journee", t):
            return 1, 0
    return jours, nuits


# --- Dates ----------------------------------------------------------------------

_MOIS_MOTIF = {mot: num for num, mots in n.MOIS.items() for mot in mots}
_RE_MOIS = "|".join(sorted(map(re.escape, _MOIS_MOTIF), key=len, reverse=True))
_JOUR_MOTIF = {mot: num for num, mots in n.JOURS_SEMAINE.items() for mot in mots}
_RE_JOURS = "|".join(sorted(map(re.escape, _JOUR_MOTIF), key=len, reverse=True))


def extraire_date(t: str, reference: date) -> date | None:
    m = re.search(rf"(?<![\w/])(\d{{1,2}})(?:er|st|nd|rd|th)?\s+({_RE_MOIS})\.?(?:\s+(20\d\d))?(?!\w)", t)
    if not m:
        m2 = re.search(rf"(?<!\w)({_RE_MOIS})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?(?![\w])", t)
        if m2:
            jour, mois, annee = int(m2.group(2)), _MOIS_MOTIF[m2.group(1)], m2.group(3)
        else:
            jour = mois = annee = None
    else:
        jour, mois, annee = int(m.group(1)), _MOIS_MOTIF[m.group(2)], m.group(3)
    if jour and mois:
        if annee:
            try:
                return date(int(annee), mois, jour)
            except ValueError:
                return None
        return n.prochaine_occurrence(jour, mois, reference)
    m = re.search(r"(?<!\w)(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?![\w/])", t)
    if m:
        jour, mois = int(m.group(1)), int(m.group(2))
        if 1 <= mois <= 12:
            if m.group(3):
                annee = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
                try:
                    return date(annee, mois, jour)
                except ValueError:
                    return None
            return n.prochaine_occurrence(jour, mois, reference)
    if re.search(r"(?<!\w)(?:apres-demain|apres demain|ba3d ghodwa|بعد غدوه|بعد غد)(?!\w)", t):
        return reference + timedelta(days=2)
    if re.search(r"(?<!\w)(?:demain|tomorrow|ghodwa|غدوه|غدا)(?!\w)", t):
        return reference + timedelta(days=1)
    if re.search(r"(?<!\w)(?:ce|this|cette fin de semaine|had el|hal|had|hedha el) ?week-?end|هالويكاند|هذا الويكاند|"
                 r"this coming weekend|cette fin de semaine", t):
        return n.ce_week_end(reference)
    if re.search(r"(?<!\w)(?:la semaine prochaine|next week|الاسبوع القادم|الجمعه الجايه|semaine jaya)(?!\w)", t):
        return n.semaine_prochaine(reference)
    if re.search(r"(?<!\w)(?:le mois prochain|next month|الشهر القادم|الشهر الجاي)(?!\w)", t):
        return n.mois_prochain(reference)
    m = re.search(rf"(?<!\w)(?:next |نهار |يوم )?({_RE_JOURS})(?: prochain| prochaine| jay| ejjay| القادم)?(?!\w)", t)
    if m:
        mot = m.group(1)
        # « الجمعه » seul = vendredi ; mais « جمعه » sans article = semaine en darija (exclu du motif)
        return n.jour_semaine_suivant(_JOUR_MOTIF[mot], reference)
    return None


# --- Budget ---------------------------------------------------------------------

_DEVISES = [
    ("TND", r"dt|tnd|dinars?|dinar|dinnar|د\.?ت|دت|دينار|دنانير|دينارا|mille dinars"),
    ("EUR", r"€|eur|euros?|euro|يورو|اورو"),
    ("USD", r"\$|usd|dollars?|دولار"),
    ("CHF", r"chf|francs? suisses?"),
    ("MAD", r"mad|dirhams?|درهم"),
    ("CAD", r"cad|dollars? canadiens?"),
    ("GBP", r"£|gbp|pounds?|livres? sterling"),
]
_RE_DEVISE = "|".join(f"(?P<{code}>{motif})" for code, motif in _DEVISES)
_MONTANT = r"(\d{1,3}(?:[ .]\d{3})+|\d+(?:[.,]\d+)?)\s*(k)?"
_MOTS_BUDGET = (r"budget|budjet|bujet|budg|max(?:imum)?|environ|around|about|approx(?:imativement)?|"
                r"حوالي|ميزانيه|الميzانيه|الميزانيه|ميزانيتي|بميزانيه|prix|moins de|under|less than|jusqu'a|"
                r"up to|pas plus de|entre")
_UNITES_NON_BUDGET = re.compile(
    rf"^\s*(?:{_JOURS}|{_NUITS}|personnes?|pers|adultes?|adults?|enfants?|kids?|ans|years?|mois|months?|km|"
    r"h|heures?|%|semaines?|weeks?|etoiles?|stars?|amis|amies|friends|people|persons|eleves|etudiants|"
    r"collegues|seniors|potes|اشخاص|افراد|اطفال|سنوات|سنه|نجوم|x\d)(?!\w)")
_PAR_PERSONNE = (r"par personne|par pers|/ ?personne|/ ?pers|par tete|par adulte|par eleve|par etudiant|chacune?|"
                 r"each|per person|per head|a head|pp|l wa7ed|kol wa7ed|lel wa7ed|للشخص|لكل شخص|للفرد|على الشخص|"
                 r"لكل واحد|par participant")
_PAR_NUIT = r"par nuit|/ ?nuit|per night|a night|la nuit|par nuitee|فالليله|لليله|في الليله|bel lila|fel lila"
_PAR_JOUR = r"par jour|/ ?jour|per day|a day|fel nhar|في اليوم|لليوم|par journee|/ ?j(?!\w)"
_PAR_MOIS = r"par mois|/ ?mois|per month|a month|في الشهر"
_ILLIMITE = _un_de([
    "pas de limite", "sans limite", "budget illimite", "illimite", "no budget limit", "no limit",
    "budget sans probleme", "money is no object", "budget n'est pas un probleme", "peu importe le prix",
    "ma yhemech el flous", "flous mouch mochkla", "ما يهمش الفلوس", "الفلوس موش مشكله", "بلا حدود",
    "sans contrainte de budget", "unlimited budget",
])
_HORS_TRANSPORT = _un_de(["hors vol", "hors vols", "vol non compris", "vols non compris", "sans le vol",
                          "sans les vols", "not including flights", "excluding flights", "hors transport",
                          "flights not included", "billets non compris"])


@dataclass
class Montant:
    valeur: float
    devise: str | None
    debut: int
    fin: int
    mot_budget: bool


def _montants(t: str) -> list[Montant]:
    sortie = []
    for m in re.finditer(rf"(?<![\w.,/:-]){_MONTANT}", t):
        valeur = n.parser_montant(m.group(1) + (m.group(2) or ""))
        if valeur is None or valeur <= 0:
            continue
        apres = t[m.end():]
        devise_m = re.match(rf"\s*(?:{_RE_DEVISE})(?!\w)", apres)
        devise = next((code for code, _ in _DEVISES if devise_m and devise_m.group(code)), None)
        fin = m.end() + (devise_m.end() if devise_m else 0)
        avant = t[max(0, m.start() - 25):m.start()]
        devise_avant = re.search(rf"(?<!\w)(?:{_RE_DEVISE})\s*$", avant)  # pas le « eur » de « Tozeur »
        if devise is None and devise_avant:
            devise = next(code for code, _ in _DEVISES if devise_avant.group(code))
        if devise is None and _UNITES_NON_BUDGET.match(apres):
            continue
        if devise is None and re.match(rf"\s*(?:{_RE_MOIS})(?!\w)", apres):
            continue  # une date (« le 20 décembre »)
        if devise is None and re.search(r"(?:nhar|le|on|the|du|au|اليوم|يوم|نهار|en|in|de)\s*$", avant):
            continue
        mot_budget = bool(re.search(rf"(?:{_MOTS_BUDGET})\W*(?:\w+\W+){{0,2}}$", avant))
        if devise is None and not mot_budget:
            continue
        sortie.append(Montant(valeur, devise, m.start(), fin, mot_budget))
    return sortie


def extraire_budget(t: str) -> dict[str, Any]:
    vide = {"budget_montant": None, "budget_devise": None, "budget_base": None,
            "budget_illimite": bool(re.search(_ILLIMITE, t)), "_budget_par_personne_aussi": False,
            "_budget_hors_transport": bool(re.search(_HORS_TRANSPORT, t))}
    montants = _montants(t)
    if not montants:
        return vide
    # Fourchette « entre 800 et 1000 dt », « 800-1000 dt » → borne haute
    choisi = next((m for m in montants if m.devise), montants[0])
    i = montants.index(choisi)
    if i > 0 and re.fullmatch(r"\s*(?:-|a|à|et|to|and|ou|or|الى|و)\s*", t[montants[i - 1].fin:choisi.debut]):
        choisi = Montant(max(choisi.valeur, montants[i - 1].valeur), choisi.devise, choisi.debut, choisi.fin, True)
    elif i + 1 < len(montants) and re.fullmatch(r"\s*(?:-|a|à|et|to|and|ou|or|الى|و)\s*", t[choisi.fin:montants[i + 1].debut]):
        suivant = montants[i + 1]
        choisi = Montant(max(choisi.valeur, suivant.valeur), suivant.devise or choisi.devise, choisi.debut, suivant.fin, True)
    fenetre = t[choisi.fin:choisi.fin + 30]
    base = "total"
    par_personne = bool(re.match(rf"\s*(?:{_PAR_PERSONNE})(?!\w)", fenetre) or re.search(rf"^.{{0,12}}(?:{_PAR_PERSONNE})(?!\w)", fenetre))
    par_nuit = bool(re.search(rf"^.{{0,20}}(?:{_PAR_NUIT})(?!\w)", fenetre))
    par_jour = bool(re.search(rf"^.{{0,20}}(?:{_PAR_JOUR})(?!\w)", fenetre))
    if par_nuit:
        base = "par_nuit"
    elif par_jour:
        base = "par_jour"
    elif par_personne:
        base = "par_personne"
    return {
        "budget_montant": choisi.valeur, "budget_devise": choisi.devise or "TND", "budget_base": base,
        "budget_illimite": False, "_budget_par_personne_aussi": par_personne and base in ("par_nuit", "par_jour"),
        "_budget_hors_transport": vide["_budget_hors_transport"],
    }


# --- Voyageurs ------------------------------------------------------------------

_PARTENAIRE = _un_de([
    "mon mari", "ma femme", "ma copine", "mon copain", "mon conjoint", "ma conjointe", "mon epoux", "mon epouse",
    "mrati", "mrti", "marti", "rajli", "sa7bti", "my wife", "my husband", "my girlfriend", "my boyfriend",
    "my partner", "زوجتي", "زوجي", "مرتي", "ومرتي", "راجلي", "وراجلي", "مع زوجتي", "ma moitie",
])
_COUPLE = _un_de(["couple", "en couple", "lune de miel", "honeymoon", "شهر عسل", "زوجان", "زوجين", "amoureux",
                  "pour mes parents", "for my parents", "لوالدي"])
_FAMILLE = _un_de([
    "famille", "family", "familial", "familiale", "عائله", "عائليه", "عايله", "l famille", "lfamille",
    "ma fille", "mon fils", "ma mere", "mon pere", "ma soeur", "mon frere", "mes parents", "cousins?", "cousines?",
    "grand-mere", "grand-pere", "grands-parents", "امي", "وامي", "اختي", "واختي", "اخي", "واخي", "بنتي", "ولدي",
    "بنات عمي", "ولاد عمي", "wled 3ammi", "wled kh?ali", "5ti", "o5ti", "khti", "khouya", "ommi", "bebe", "baby",
    "enfants?", "kids?", "children", "اطفال", "طفل", "طفلين", "طفلينا", "ولدين", "ولدنا", "صغار", "wlidi", "sghar",
    "neveu", "niece", "tante", "oncle",
])
_AMIS = _un_de(["amis", "amies", "ami", "copains", "copines", "potes", "friends", "s7abi", "s7abna", "s7abat",
                "صحابي", "اصدقاء", "اصدقائي", "entre filles", "entre potes", "entre amis", r"\d+ couples",
                "deux couples", "enterrement de vie", "girls trip"])
_GROUPE = _un_de(["collegues", "colleagues", "eleves", "etudiants", "students", "equipe", "team building", "team",
                  "seniors", "groupe", "group", "زملاء", "طلبه", "تلاميذ", "مجموعه", "association", "club",
                  "classe", "entreprise", "seminaire"])
_SOLO = _un_de(["seul", "seule", "en solo", "solo", "wa7di", "alone", "by myself", "on my own", "وحدي",
                "لشخص واحد", "شخص واحد", "ena wa7di", "انا وحدي"])
_ADULTES_SURS = _un_de(["ma mere", "mon pere", "ma mere", "امي", "وامي", "ommi", "grand-mere", "grand-pere"])
_INDIVIDU_FAMILLE = _un_de(["ma fille", "mon fils", "ma soeur", "mon frere", "اختي", "واختي", "اخي", "واخي",
                            "بنتي", "5ti", "o5ti", "khti", "khouya", "ma mere", "mon pere", "امي", "وامي", "ommi"])
_PERSONNES = r"(?:personnes?|persons?|people|pax|ashkhas|اشخاص|افراد|نفر|personnes adultes|voyageurs|travellers|travelers)"
_GROUPE_NOMS = (r"(?:amis|amies|copains|copines|potes|friends|etudiants|students|collegues|colleagues|seniors|"
                r"eleves|s7abi|personnes|adultes|filles|garcons|cousins|cousines|retraites|اصدقاء|صحابي|بنات عمي|ولاد عمي)")


def extraire_voyageurs(t: str) -> tuple[dict[str, Any], set[str]]:
    surs: set[str] = set()
    adultes = enfants = total = None

    m = re.search(rf"(?<!\w){NUM}\s*(?:adultes?|adults?|grown-ups|كبار|بالغين)(?!\w)", t)
    if m:
        adultes = nombre(m.group(1))
    m = re.search(rf"(?<!\w){NUM}\s*(?:petits? )?(?:enfants?|kids?|children|child|bebes?|ados?|اطفال|طفل|صغار|wled|sghar)(?!\w)", t)
    if m:
        enfants = nombre(m.group(1))
    elif re.search(_un_de(["طفلين", "طفلينا", "ولدين", "صغيرين", "nos deux enfants", "our two kids", "2 wled", "zouz sghar"]), t):
        enfants = 2
    elif re.search(_un_de(["un bebe", "a baby", "bebe", "baby", "ولدنا", "ولدي", "بنتنا", "طفلي", "طفلنا", "wlidna",
                           "notre fils", "notre fille", "our son", "our daughter", "un enfant", "an? child", "one kid"]), t):
        enfants = 1
    if adultes is not None and enfants is not None:
        total = adultes + enfants  # « 2 adultes et 2 enfants » prime sur « pour 2 »

    partenaire = bool(re.search(_PARTENAIRE, t))
    couple = bool(re.search(_COUPLE, t))
    famille = bool(re.search(_FAMILLE, t)) or enfants not in (None, 0)
    amis = bool(re.search(_AMIS, t))
    groupe = bool(re.search(_GROUPE, t)) and not re.search(r"(?:je suis|ena|انا|i'm|i am) (?:un |une )?etudiant", t)
    solo = bool(re.search(_SOLO, t))

    # Effectif explicite
    m = re.search(rf"(?:famille|family|famiily|عائله)(?: nombreuse)?(?: de| of| من)?\s*{NUM}(?!\w)", t)
    if m:
        total = nombre(m.group(1))
    m = re.search(rf"(?<!\w){NUM}\s*{_PERSONNES}(?!\w)", t)
    if total is None and m:
        total = nombre(m.group(1))
    if total is None and re.search(r"(?<!\w)(?:شخصان|شخصين|زوز اشخاص)(?!\w)", t):
        total = 2
    # « ena w s7abi 5 », « avec 3 amis », « me and 2 friends » : le locuteur en plus
    m = re.search(rf"(?:ena w|ana w|moi et|me and|انا و)\s*(?:\w+\s){{0,2}}?(?:{_GROUPE_NOMS})?\s*{NUM}(?!\w)", t) \
        or re.search(rf"(?:avec|with|m3a|مع)\s+(?:mes\s+|my\s+)?{NUM}\s*{_GROUPE_NOMS}(?!\w)", t) \
        or re.search(rf"(?:me and|moi et|ena w)\s+{NUM}\s*{_GROUPE_NOMS}(?!\w)", t)
    if total is None and m:
        k = nombre(m.group(1))
        if k:
            total = k + 1
    m = re.search(rf"(?<!\w){NUM}\s*(?:amis|amies|copains|copines|potes|friends|etudiants|students|collegues|"
                  rf"colleagues|seniors|eleves|retraites)(?!\w)", t)
    if total is None and m:
        total = nombre(m.group(1))
    m = re.search(rf"(?:groupe|group) (?:de |of )?{NUM}(?!\w)", t)
    if total is None and m:
        total = nombre(m.group(1))
    if total is None and re.search(r"(?<!\w)(?:pour|for|a|à) (?:2|deux|two)(?!\w)|a deux|two of us|nous deux|"
                                   r"tous les deux|both of us|ahna zouz", t):
        total = 2

    # Type de voyage (README §3 Voyageurs) : famille > couple > amis > groupe > solo
    type_voyage = None
    if famille and not (re.search(_INDIVIDU_FAMILLE, t) is None and re.fullmatch(r".*\b(?:enfants?|kids?)\b.*", t) and groupe):
        type_voyage = "famille"
    elif couple or partenaire:
        type_voyage = "couple"
    elif amis:
        type_voyage = "amis"
    elif groupe:
        type_voyage = "groupe"
    elif solo:
        type_voyage = "solo"
    if type_voyage == "famille" and re.search(r"pour mes parents|for my parents", t) and enfants is None:
        type_voyage = "couple"
    if type_voyage:
        surs.add("type_voyage")

    # Composition
    if (partenaire or couple) and type_voyage == "famille" and enfants not in (None, 0):
        adultes = adultes or 2
        total = adultes + enfants if total is None or total < adultes + enfants else total
    if partenaire and type_voyage == "famille":
        adultes = adultes or 2
        if enfants is not None and total is None:
            total = adultes + enfants
    if type_voyage == "couple":
        total, adultes, enfants = total or 2, 2, 0
    if type_voyage == "solo":
        total, adultes, enfants = 1, 1, 0
    if adultes is not None and enfants is None and type_voyage != "famille":
        enfants = 0
    if adultes is not None and enfants is not None and total is None:
        total = adultes + enfants
    if total is None and type_voyage == "famille" and re.search(_INDIVIDU_FAMILLE, t) and not partenaire:
        total = 2  # « avec ma fille », « أنا وأمي » : le locuteur + un proche
        if re.search(_ADULTES_SURS, t):
            adultes, enfants = 2, 0
    if total is not None and adultes is None and enfants is None and type_voyage in (None, "amis", "groupe"):
        adultes, enfants = total, 0
    if total is not None:
        surs.add("voyageurs")
    return {"nb_voyageurs": total, "nb_adultes": adultes, "nb_enfants": enfants, "type_voyage": type_voyage}, surs


# --- Préférences et activités ---------------------------------------------------

THEMES_MOTS: dict[str, list[str]] = {
    "plage": ["plages?", "mer", "b7ar", "lb7ar", "bhar", "البحر", "بحر", "beach(?:es)?", "sea", "شاطئ", "baignade"],
    "culture": ["culture", "culturel(?:le)?s?", "musees?", "medina", "traditions?", "mosquees?", "mouled", "mawlid",
                "fete religieuse", "جامع", "مسجد", "متحف", "المولد", "مهرجان", "galerie d'art", "festival", "museums?",
                "المدينه العتيقه", "روحاني"],
    "histoire": ["histoire", "historiques?", "ruines?", "romaine?s?", "patrimoine", "ribat", "رباط", "history",
                 "historical", "roman", "اثار", "تاريخ", "amphitheatre"],
    "nature": ["oasis", "nature", "randonnees?", "rando", "paysages?", "hiking", "chebika", "tamerza", "mides",
               "الشبيكه", "تمغزه", "طبيعه"],
    "gastronomie": ["gastronomie", "cuisine", "street food", "restaurants?", "diner", "food", "طبخ", "ماكله",
                    "gastronomy", "degustation"],
    "aventure": ["sensations?", "quad", "parachute", "karting", "paintball", "aventure", "adventure", "كواد"],
    "detente": ["detente", "repos", "spa", "hammam", "thalasso", "massages?", "relax(?:ation)?", "pas trop bouger",
                "استرخاء", "الاسترخاء", "راحه", "حمام", "تدليك"],
    "shopping": ["souks?", "shopping", "artisanat", "tapis", "سوق", "souvenirs"],
    "nautique": ["plongee", "jet[ -]?ski", "kitesurf", "sports nautiques", "parc aquatique", "water ?parks?",
                 "snorkeling", "scuba", "diving", "kayak", "voilier", "boat trip", "جوله بحريه", "بارك اكواتيك",
                 "اكواتيك", "aquapark", "planche a voile", "windsurf", "paddle", "غوص"],
    "desert": ["desert", "sahara", "dunes?", "sahra", "nuit sous tente", "صحراء", "الصحراء", "star wars",
               "dromadaires?", "campement", "bivouac"],
}
_MOTIFS_THEMES = {theme: re.compile(_un_de(mots)) for theme, mots in THEMES_MOTS.items()}

_ARRET_AR = r"(?!(?:و|في|مع|ثم|من|الى|بعد|حتى)(?:\s|$))(?!و)"
_MOT_AR = r"[^\s،,.:؛!?()]+"
ACTIVITES_MOTIFS = [
    r"quad(?: dans les dunes| sur les dunes| in the dunes)?", r"jet[ -]?ski", r"parachute ascensionnel|parasailing",
    r"plongee(?: sous-marine)?|scuba diving|snorkell?ing|diving", r"kayak", r"paddle", r"kitesurf", r"windsurf",
    r"sortie en (?:voilier|bateau|mer)|voilier", r"boat trip(?: to the \w+ islands?)?|balade en bateau|excursion en bateau",
    r"karting", r"paintball", r"escape game", r"cinema", r"bowling", r"laser game",
    r"equitation(?: sur la plage)?|horse riding|balade a cheval", r"balade en dromadaire|camel ride|dromadaire",
    r"montgolfiere|hot air balloon", r"hammam", r"thalasso(?:therapie)?", r"massages?", r"spa", r"yoga",
    r"nuit (?:sous (?:la )?tente|en campement|dans le desert|au desert)", r"campement", r"bivouac",
    r"rando(?:nnee)?s?", r"hiking", r"cours de \w+", r"atelier \w+", r"galerie d'art",
    r"musees?(?: (?:du|de la|des|de) \w+)?", r"diner (?:avec vue sur (?:le|la) \w+|dans le desert|spectacle)",
    r"water ?parks?|parc aquatique|aquapark", r"carthageland", r"friguia(?: park)?", r"golf",
    r"street food", r"(?:decors|sites|lieux) de (?:tournage de )?star wars|star wars", r"(?:train )?lezard rouge",
    r"team building", r"visite guidee|guide", r"soiree en boite|boite de nuit|boite(?! (?:manuelle|auto|automatique|de vitesse))",
    r"shopping (?:au|a|f|fel|in the|in) \w+", r"ribat", r"chebika", r"tamerza", r"mides", r"ong (?:el )?jemel",
    r"kuriat", r"el jem", r"carthage", r"bardo", r"mouled", r"festival \w+",
    rf"جامع(?: {_ARRET_AR}{_MOT_AR})", rf"مقام(?: {_ARRET_AR}{_MOT_AR}){{1,3}}", r"المدينه العتيقه",
    rf"متحف(?: {_ARRET_AR}{_MOT_AR}){{1,2}}", rf"رباط(?: {_ARRET_AR}{_MOT_AR})?", r"جوله بحريه", r"بارك اكواتيك",
    r"العاب", r"الشبيكه", r"تمغزه", r"اونغ جمل", r"كورس طبخ(?: تونسي)?", rf"سوق(?: {_ARRET_AR}{_MOT_AR})?",
    rf"مهرجان(?: {_ARRET_AR}{_MOT_AR}){{1,3}}", r"حمام", r"تدليك", r"غوص", r"كواد", r"ركوب (?:الخيل|الجمال)",
]
# Début de mot, ou juste après un préfixe arabe collé (« ورباط هرثمة » → « رباط هرثمة »)
_MOTIF_ACTIVITES = re.compile(r"(?:(?<!\w)|(?<=(?<!\w)[وفب]))(?:" + "|".join(f"(?:{m})" for m in ACTIVITES_MOTIFS) + r")(?!\w)")


def extraire_preferences(t: str) -> list[str]:
    return [theme for theme, motif in _MOTIFS_THEMES.items() if motif.search(t)]


def extraire_activites(texte: str, t: str, villes: list[n.Mention]) -> list[str]:
    """Activités recopiées du texte d'origine (même position que dans le texte normalisé)."""
    sortie: list[str] = []
    for m in _MOTIF_ACTIVITES.finditer(t):
        # « Tunis-Carthage » : un morceau de nom de ville n'est pas une activité
        if any(v.debut <= m.start() and m.end() <= v.fin for v in villes):
            continue
        extrait = texte[m.start():m.end()].strip(" ,.;:!?()«»\"'")
        if extrait and extrait.lower() not in {s.lower() for s in sortie}:
            sortie.append(extrait)
    return sortie


# --- Contraintes ----------------------------------------------------------------

_NIVEAU_1 = _un_de(["mobilite reduite", "fauteuil roulant", "wheelchair", "pmr", "marche mal", "marche difficilement",
                    "difficulte a marcher", "difficultes a marcher", "reduced mobility", "كرسي متحرك", "اعاقه",
                    "حركه محدوده", "ما نجمش نمشي", "ma nejjemch nemchi barcha", "handicap(?:e|ee)?"])
_NIVEAU_2 = _un_de(["pas trop fatigant", "nothing too tiring", "not too tiring", "on marche peu", "marcher peu",
                    "eviter les longues marches", "evite les longues marches", "pas de longues marches",
                    "pas d'escaliers", "no stairs", "sans trop marcher", "pas trop de marche", "little walking",
                    "موش برشا مشي", "بلا مشي برشا"])
_HORAIRES = [("coucher du soleil", "coucher du soleil"), ("lever du soleil", "lever du soleil"),
             ("sunset", "sunset"), ("sunrise", "sunrise"), ("fil lil", "nuit"), ("le matin", "matin"),
             ("le soir", "soir"), ("pas avant", "pas avant")]


def extraire_contraintes(t: str) -> dict[str, Any]:
    niveau = mobilite = None
    if re.search(_NIVEAU_1, t):
        niveau, mobilite = 1, True
    elif re.search(_NIVEAU_2, t):
        niveau = 2
    horaires = next((valeur for motif, valeur in _HORAIRES if motif in t), None)
    return {"niveau_marche_max": niveau, "mobilite_reduite": mobilite, "horaires": horaires}


# --- Transport ------------------------------------------------------------------

_VOL_NON = _un_de([
    "pas besoin de vol", "pas besoin d'avion", "no flight needed", "deja (?:nos|mes|les) billets",
    "billets deja", "already have (?:our|my) tickets", "en train", "bel train", "bel tran", "par le train",
    "by train", "train", "بالقطار", "القطار", "بالتران", "التران", "louage", "بالواج", "en voiture", "en bus",
    "bel karhba", "بالكرهبه", "بكرهبتنا", "كرهبتنا", "notre (?:propre )?voiture", "ma voiture", "our car", "by car",
    "road trip", "en bateau", "en ferry", "by ferry", "par la route",
])
_VOL_OUI = _un_de([r"vols?", "flights?", "flying", "fly", "en avion", "avion", "bel tayara", "tayara", "طياره",
                   "بالطائره", "بالطياره", "الطائره", "رحله جويه", "طيران", "plane", "airfare", "billets? d'avion"])
_VOITURE_INDIFF = _un_de(["n'a pas de voiture", "n'avons pas de voiture", "on n'a pas de voiture", "ma3andnach karhba",
                          "ما عندناش كرهبه", "ma 3andich karhba", "we don't have a car", "ما عنديش كرهبه"])
_VOITURE_NON = _un_de([
    "sans voiture", "pas de voiture", "no car", "without (?:a )?car", "ma n7ebch karhba", "ma n7ebouch karhba",
    "ma nhebch karhba", "ma n7ebouch nsou9ou", "ma n7ebch nsou9", "on ne veut pas conduire", "pas conduire",
    "don't want to drive", "بدون سياره", "بلا كرهبه", "en taxi", "notre (?:propre )?voiture", "propre voiture",
    "our own car", "بكرهبتنا", "كرهبتنا", "الكرهبه متاعنا", "karhbetna", "ni de voiture", "pas besoin de voiture",
])
_VOITURE_OUI = _un_de([
    r"location (?:d'une |de |d'un |de la )?(?:voiture|vehicule|van|4x4|auto)", "voiture de location", "louer une voiture",
    "loue une voiture", "louer un \\w+", "rent(?:ing)? a car", "car rental", "rental car", "rent a car", "rent a 4x4",
    "kraya karhba", "kra karhba", "nekri karhba", "nkri karhba", "nekriw", "نكريو", "نكري", "استئجار سياره",
    "تاجير سياره", "كراء سياره", "4x4", "van",
    # Exemple 2 du guide : « avec une voiture » dans une demande = une location
    "avec une voiture", "besoin d'une voiture", "need a car", "with a car", "نحتاج سياره", "نحب كرهبه",
])
_TRANSFERT_OUI = _un_de([r"transferts?", "navette", "chauffeur", "driver", "minibus", "bus prive", "bus avec chauffeur",
                         "airport transfer", "سائق", "بسائق", "شوفور", "نافيت", "vehicule", "pick-?up", "shuttle"])
_DIRECT_NON = _un_de(["escale acceptee", "escale ok", "avec escale", "sinon via", "stopover ok", "escale possible",
                      "with a stopover", "une escale", "connection ok", "via \\w+"])
_DIRECT_OUI = _un_de(["vol direct", "vols directs", "direct flight", "nonstop", "non-stop", "directe?", "مباشره"])
_AUTO_OUI = _un_de(["automatique", "automatic", "auto", "اوتوماتيك", "boite auto"])
_AUTO_NON = _un_de(["manuelle", "manual", "boite manuelle"])
_PRIX = _un_de(["le moins cher", "moins chere?", "priorite au prix", "cheapest", "pas cher", "petit prix", "ارخص",
                "اقل سعر", "budget serre", "economique", "low cost"])
_CONFORT = _un_de(["luxe", "luxury", "luxueux", "priorite au confort", "confort", "premium", "haut de gamme", "فاخر",
                   "فاخره", "vip"])


def extraire_transport(t: str) -> tuple[dict[str, str], dict[str, Any]]:
    vol = voiture = transfert = "indifferent"
    if re.search(_VOL_NON, t):
        vol = "non"
    elif re.search(_VOL_OUI, t):
        vol = "oui"
    if re.search(_VOITURE_INDIFF, t):
        voiture = "indifferent"
    elif re.search(_VOITURE_NON, t):
        voiture = "non"
    elif re.search(_VOITURE_OUI, t) and not re.search(r"سياره بسائق|voiture avec chauffeur|car with (?:a )?driver", t):
        voiture = "oui"
    if re.search(_TRANSFERT_OUI, t) and not re.search(r"pas (?:de|besoin de) transfert", t):
        transfert = "oui"
    vol_direct = False if re.search(_DIRECT_NON, t) else True if re.search(_DIRECT_OUI, t) else None
    if vol != "oui" and not re.search(r"vol|flight|طيران|طائره", t):
        vol_direct = None
    boite_auto = False if re.search(_AUTO_NON, t) else True if re.search(_AUTO_OUI, t) else None
    if voiture != "oui":
        boite_auto = None
    priorite = None
    if "oui" in (vol, voiture, transfert):
        priorite = "prix" if re.search(_PRIX, t) else "confort" if re.search(_CONFORT, t) else None
    return ({"vol": vol, "voiture": voiture, "transfert": transfert},
            {"vol_direct": vol_direct, "boite_auto": boite_auto, "priorite": priorite})


# --- Point d'entrée -------------------------------------------------------------

def extraire(texte: str, date_reference: date) -> ResultatRegles:
    """Texte libre → dictionnaire brut (montant tel que dit) + champs sûrs. Ne lève jamais."""
    t = n.texte_normalise(texte)
    langue = detecter_langue(texte, t)
    villes = n.trouver_villes(t)
    if est_hors_sujet(t, villes):
        return ResultatRegles(n.demande_hors_sujet(langue), {"hors_sujet"})

    surs = {"langue", "hors_sujet"}
    destination, autres, depart, _ = extraire_villes(t, villes)
    jours, nuits = extraire_duree(t)
    budget = extraire_budget(t)
    voyageurs, surs_voyageurs = extraire_voyageurs(t)
    besoins, prefs_transport = extraire_transport(t)
    preferences = extraire_preferences(t)
    activites = extraire_activites(texte, t, villes)
    contraintes = extraire_contraintes(t)
    surs |= surs_voyageurs
    if preferences:
        surs.add("preferences")
    if contraintes["niveau_marche_max"] is not None:
        surs.add("contraintes")
    brut = {
        "destination": destination, "autres_villes": autres, "date_debut": None,
        "duree_jours": jours, "nb_nuits": nuits, **budget, **voyageurs,
        "preferences": preferences, "activites_souhaitees": activites, "contraintes": contraintes,
        "langue": langue, "ville_depart": depart, "besoins_transport": besoins,
        "preferences_transport": prefs_transport, "hors_sujet": False,
    }
    debut = extraire_date(t, date_reference)
    brut["date_debut"] = debut.isoformat() if debut and debut >= date_reference else None
    return ResultatRegles(brut, surs)
