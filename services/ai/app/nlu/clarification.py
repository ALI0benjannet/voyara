"""Question de clarification du module 1 : textes écrits à l'avance, jamais générés.

Une seule question à la fois, sur le premier champ manquant. Si un vol est demandé, la ville de
départ puis la date passent en premier (sans elles, aucune recherche de vol n'est possible). Une
demande hors sujet reçoit une réponse polie qui recadre. Rien n'est inventé : les villes proposées
viennent du catalogue (`jeu_nlu.VILLES_CATALOGUE`).
"""

from scripts import jeu_nlu

ORDRE = ("destination", "duree", "budget", "voyageurs", "ville_depart", "date_debut")
ORDRE_AVEC_VOL = ("ville_depart", "date_debut", "destination", "duree", "budget", "voyageurs")
EXEMPLES_VILLES = ", ".join(jeu_nlu.VILLES_CATALOGUE[:5])  # Djerba, Tunis, Sidi Bou Saïd, Sousse, Hammamet

QUESTIONS: dict[str, dict[str, str]] = {
    "destination": {
        "fr": f"Où souhaitez-vous aller en Tunisie ? Par exemple : {EXEMPLES_VILLES}…",
        "en": f"Where would you like to go in Tunisia? For example: {EXEMPLES_VILLES}…",
        "ar": "إلى أي مدينة تونسية تريد الذهاب؟ مثلاً: جربة، تونس، سيدي بوسعيد، سوسة، الحمامات…",
        "darija": f"Win t7eb temchi f Tounes ? Mathalan : {EXEMPLES_VILLES}…",
    },
    "duree": {
        "fr": "Combien de jours dure votre séjour ?",
        "en": "How many days will your trip last?",
        "ar": "كم يوماً ستدوم رحلتك؟",
        "darija": "9addech men nhar bech t9a3ed ?",
    },
    "budget": {
        "fr": "Quel est votre budget total, en dinars (DT) ?",
        "en": "What is your total budget, in dinars (TND)?",
        "ar": "ما هي ميزانيتك الإجمالية بالدينار؟",
        "darija": "9addech el budget mte3ek el kol, bel dinar ?",
    },
    "voyageurs": {
        "fr": "Combien de personnes voyagent, et y a-t-il des enfants ?",
        "en": "How many people are travelling, and are there any children?",
        "ar": "كم عدد المسافرين، وهل معكم أطفال؟",
        "darija": "9addech men wa7ed bech tsafrou, w famma sghar ?",
    },
    "ville_depart": {
        "fr": "De quelle ville partirait votre vol ?",
        "en": "Which city would your flight leave from?",
        "ar": "من أي مدينة ستنطلق رحلتك الجوية؟",
        "darija": "Men ama mdina bech ti9la3 el tayara ?",
    },
    "date_debut": {
        "fr": "À quelle date souhaitez-vous partir ?",
        "en": "On what date would you like to leave?",
        "ar": "في أي تاريخ تريد السفر؟",
        "darija": "Ama nhar t7eb tsafer ?",
    },
}

HORS_SUJET = {
    "fr": "Je suis l'assistant voyage de Voyara : je peux vous aider à préparer un séjour en Tunisie "
          "(destination, durée, budget, activités). Où aimeriez-vous partir ?",
    "en": "I'm Voyara's travel assistant: I can help you plan a trip in Tunisia (destination, length, "
          "budget, activities). Where would you like to go?",
    "ar": "أنا مساعد السفر في فويارا: يمكنني مساعدتك في تحضير رحلة في تونس (الوجهة، المدة، الميزانية، "
          "الأنشطة). إلى أين تحب أن تسافر؟",
    "darija": "Ena l'assistant mta3 Voyara lel voyage : najjem n3awnek t7adher sfra f Tounes (win, 9addech "
              "men nhar, el budget, el activités). Win t7eb temchi ?",
}


def question_clarification(champs_manquants: list[str], langue: str, vol_demande: bool,
                           hors_sujet: bool = False) -> str | None:
    """Question sur le premier champ manquant, dans la langue du client ; None si rien ne manque."""
    langue = langue if langue in HORS_SUJET else "fr"
    if hors_sujet:
        return HORS_SUJET[langue]
    for champ in ORDRE_AVEC_VOL if vol_demande else ORDRE:
        if champ in champs_manquants:
            return QUESTIONS[champ][langue]
    return None
