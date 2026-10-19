import { api } from "@voyara/api/axios";

/** Vocabulaire des tags IA — miroir de services/catalog/app/tags_ia.py.
 *  Le backend refuse (422) toute valeur absente de ces listes. */
export const THEMES = [
  "plage",
  "culture",
  "histoire",
  "nature",
  "gastronomie",
  "aventure",
  "detente",
  "shopping",
  "nautique",
  "desert",
] as const;
export const PUBLICS = ["famille", "couple", "solo", "groupe", "enfants"] as const;
export const MOMENTS = ["matin", "apres_midi", "soir", "indifferent"] as const;
export const NIVEAUX = [1, 2, 3] as const;

export type Theme = (typeof THEMES)[number];
export type Public = (typeof PUBLICS)[number];
export type Moment = (typeof MOMENTS)[number];
export type NiveauMarche = (typeof NIVEAUX)[number];

export interface TagsIA {
  themes: Theme[];
  public: Public[];
  niveau_marche: NiveauMarche | null;
  interieur: boolean | null;
  moment_ideal: Moment | null;
}

export type ChampTag = keyof TagsIA;
export const CHAMPS: ChampTag[] = ["themes", "public", "niveau_marche", "interieur", "moment_ideal"];

export interface PropositionTags extends Partial<TagsIA> {
  source?: string;
  modele?: string;
  confiance?: "haute" | "moyenne" | "faible" | null;
  raisons?: string | null;
}

export interface ActiviteTags extends TagsIA {
  id: number;
  titre: string;
  titre_en: string | null;
  titre_ar: string | null;
  description: string;
  localisation: string;
  duree: number;
  photos: string | null;
  statut: "publiee" | "en_attente" | "refusee";
  category: { id: number; nom: string; nom_en: string | null; nom_ar: string | null } | null;
  tags_valides: boolean;
  tags_proposes: PropositionTags | null;
  modifie_le: string | null;
}

export interface PageTags {
  items: ActiviteTags[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface StatsTags {
  total: number;
  publiees: number;
  validees: number;
  publiees_validees: number;
  avec_proposition: number;
  sources: Record<string, number>;
  comparables: number;
  corrections: Record<ChampTag, number | null>;
  inchangees: number;
}

export interface TagsParams {
  page: number;
  size: number;
  search?: string;
  category_id?: number;
  tags_valides?: boolean;
}

/** Corps du PUT : tags complets + état de validation voulu. */
export interface TagsPayload {
  themes: Theme[];
  public: Public[];
  niveau_marche: NiveauMarche;
  interieur: boolean;
  moment_ideal: Moment;
  tags_valides: boolean;
}

/** Endpoints admin du catalog-service (gateway : /api/v1/etiquetage, JWT admin). */
export const tagsIaApi = {
  list: (params: TagsParams) =>
    api.get<PageTags>("/api/v1/etiquetage/activities", { params }).then((r) => r.data),
  stats: () => api.get<StatsTags>("/api/v1/etiquetage/stats").then((r) => r.data),
  save: (id: number, payload: TagsPayload) =>
    api.put<ActiviteTags>(`/api/v1/etiquetage/activities/${id}`, payload).then((r) => r.data),
};

/** Vrai si la valeur validée diffère de la proposition automatique. */
export function differe(activite: ActiviteTags, champ: ChampTag, valeur = activite[champ]): boolean {
  const propose = activite.tags_proposes?.[champ];
  if (activite.tags_proposes == null || propose === undefined) return false;
  if (Array.isArray(valeur) || Array.isArray(propose)) {
    const a = [...((valeur as string[] | null) ?? [])].sort().join("|");
    const b = [...((propose as string[] | null) ?? [])].sort().join("|");
    return a !== b;
  }
  return propose !== valeur;
}
