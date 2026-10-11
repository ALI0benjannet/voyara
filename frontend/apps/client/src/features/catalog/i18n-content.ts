import type { Activity, Category } from "./api";

/** Langues pour lesquelles le catalogue stocke des traductions en base. */
type ContentLang = "fr" | "en" | "ar";

const normalize = (lang?: string): ContentLang => {
  const base = lang?.split("-")[0];
  return base === "en" || base === "ar" ? base : "fr";
};

/** Titre de l'activité dans la langue demandée, avec repli sur le français.
 *  Le contenu métier vit en base (colonnes `titre_en` / `titre_ar`) : une
 *  activité créée sans traduction reste lisible au lieu d'afficher du vide. */
export function activityTitle(activity: Activity, lang?: string): string {
  const target = normalize(lang);
  if (target === "en") return activity.titre_en?.trim() || activity.titre;
  if (target === "ar") return activity.titre_ar?.trim() || activity.titre;
  return activity.titre;
}

/** Description de l'activité dans la langue demandée, repli français. */
export function activityDescription(activity: Activity, lang?: string): string {
  const target = normalize(lang);
  if (target === "en") return activity.description_en?.trim() || activity.description;
  if (target === "ar") return activity.description_ar?.trim() || activity.description;
  return activity.description;
}

/** Nom de catégorie traduit — d'abord la base, puis les clés i18n statiques
 *  (les 5 catégories du seed), sinon le nom d'origine. */
export function categoryName(category: Category, lang?: string): string {
  const target = normalize(lang);
  if (target === "en") return category.nom_en?.trim() || category.nom;
  if (target === "ar") return category.nom_ar?.trim() || category.nom;
  return category.nom;
}
