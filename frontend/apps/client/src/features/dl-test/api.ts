import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";

/** Page temporaire « DL test » : résultats et tests en direct de la validation Deep Learning
 *  (services/ai/app/dl), sans LLM. */

export type MethodeRecherche = "tfidf" | "e5_gele" | "e5_fine_tune";
export type MethodeClassif = "regles" | "ml_tfidf" | "xlmr_fine_tune";
export const METHODES_RECHERCHE: MethodeRecherche[] = ["tfidf", "e5_gele", "e5_fine_tune"];
export const METHODES_CLASSIF: MethodeClassif[] = ["regles", "ml_tfidf", "xlmr_fine_tune"];
export const CHAMPS_CLASSIF = ["type_voyage", "vol", "voiture"] as const;
export type ChampClassif = (typeof CHAMPS_CLASSIF)[number];
export const LANGUES = ["fr", "en", "ar", "darija"] as const;

/** Une ligne de CSV de résultats : nombres déjà convertis, cellules vides → null. */
export type LigneResultat = Record<string, string | number | null>;

export interface Resultats {
  recherche: {
    global: LigneResultat[];
    choix_modele: LigneResultat[];
    pertes: LigneResultat[];
    rangs: LigneResultat[];
  };
  classification: { global: LigneResultat[]; regles: LigneResultat[] };
}

export interface Exemples {
  recherche: { id: string; langue: string; requete: string }[];
  classification: { id: string; langue: string; texte: string; attendu: Record<ChampClassif, string> }[];
}

export interface ResultatActivite {
  rang: number;
  titre: string;
  ville: string | null;
  categorie: string | null;
  score: number;
  pertinente: boolean;
}

export interface ReponseRecherche {
  requete: string;
  requete_test: { id: string; langue: string; pertinentes: string[] } | null;
  methodes: Record<
    MethodeRecherche,
    {
      disponible: boolean;
      /** Modèle en cours de chargement en arrière-plan : relancer la recherche un peu plus tard. */
      en_chargement?: boolean;
      erreur?: boolean;
      latence_ms?: number;
      rang_premiere_pertinente?: number | null;
      resultats: ResultatActivite[];
    }
  >;
}

export interface ReponseClassif {
  texte: string;
  methodes: Record<
    MethodeClassif,
    {
      disponible: boolean;
      latence_ms?: number;
      predictions?: Record<ChampClassif, { etiquette: string; confiance: number | null }>;
    }
  >;
}

/** Le premier appel à e5 charge le modèle (≈ 1,1 Go) : il peut prendre une minute sur CPU. */
const DELAI_DL_MS = 180_000;

export function useResultatsDl() {
  return useQuery({
    queryKey: ["dl", "resultats"],
    queryFn: () => api.get<Resultats>(endpoints.ai.dl.resultats).then((r) => r.data),
    staleTime: Infinity,
  });
}

export function useExemplesDl() {
  return useQuery({
    queryKey: ["dl", "exemples"],
    queryFn: () => api.get<Exemples>(endpoints.ai.dl.exemples).then((r) => r.data),
    staleTime: Infinity,
  });
}

/** Démarre le chargement des modèles d'embeddings dès l'ouverture de la page (réponse immédiate). */
export function usePrechaufferDl() {
  return useQuery({
    queryKey: ["dl", "prechauffer"],
    queryFn: () => api.post<Record<MethodeRecherche, string>>(endpoints.ai.dl.prechauffer).then((r) => r.data),
    staleTime: Infinity,
    retry: false,
  });
}

export function useRechercheDl() {
  return useMutation({
    mutationFn: (requete: string) =>
      api
        .post<ReponseRecherche>(endpoints.ai.dl.rechercher, { requete }, { timeout: DELAI_DL_MS })
        .then((r) => r.data),
  });
}

export function useClassifDl() {
  return useMutation({
    mutationFn: (texte: string) =>
      api
        .post<ReponseClassif>(endpoints.ai.dl.classifier, { texte }, { timeout: DELAI_DL_MS })
        .then((r) => r.data),
  });
}
