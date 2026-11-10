import { useMutation } from "@tanstack/react-query";
import axios from "axios";

import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";

/** Sous-ensemble de `DemandeVoyage` (services/ai/app/nlu/schemas.py) affiché par l'accueil. */
export type Besoin = "oui" | "non" | "indifferent";

export interface DemandeVoyage {
  destination: string | null;
  autres_villes: string[];
  duree_jours: number | null;
  nb_nuits: number | null;
  budget_montant: number | null;
  budget_devise: string | null;
  budget_illimite: boolean;
  nb_voyageurs: number | null;
  nb_adultes: number | null;
  nb_enfants: number | null;
  type_voyage: "famille" | "couple" | "solo" | "amis" | "groupe" | null;
  preferences: string[];
  activites_souhaitees: string[];
  ville_depart: string | null;
  besoins_transport: { vol: Besoin; voiture: Besoin; transfert: Besoin };
  hors_sujet: boolean;
}

export interface ReponseComprendre {
  demande: DemandeVoyage;
  champs_manquants: string[];
  question_clarification: string | null;
  avertissements: string[];
  provider: string;
  latence_ms: number;
  methode: "regles" | "hybride" | "llm";
}

/** La route attend jusqu'à 25 s le LLM, le gateway et le proxy Next coupent à 30 s : on attend
 *  un peu plus qu'eux (le délai global d'axios, 20 s, couperait trop tôt). */
export const DELAI_COMPRENDRE_MS = 35_000;

export const comprendreApi = (texte: string) =>
  api
    .post<ReponseComprendre>(endpoints.ai.comprendre, { texte }, { timeout: DELAI_COMPRENDRE_MS })
    .then((r) => r.data);

/** Mutation TanStack Query : aucun nouvel essai automatique (pas de double appel au LLM). */
export function useComprendre() {
  return useMutation({ mutationFn: comprendreApi });
}

export type CleErreurComprendre = "rateLimited" | "unavailable" | "unexpected";

/** Erreur d'appel → clé i18n `home.aiPlanner.errors.*`. */
export function cleErreurComprendre(error: unknown): CleErreurComprendre {
  if (!axios.isAxiosError(error)) return "unexpected";
  const status = error.response?.status ?? 0;
  if (status === 429) return "rateLimited";
  // 0 : réseau ou délai dépassé ; 500 : proxy Next sans gateway ; 502-504 : gateway ou service ai.
  if (status === 0 || status === 500 || status === 502 || status === 503 || status === 504) {
    return "unavailable";
  }
  return "unexpected";
}
