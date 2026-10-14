import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";

import type { Activity } from "@/features/catalog/api";

export type Statut = "en_attente" | "publiee" | "refusee";
export type AnnonceType = "partenariat" | "emploi" | "evenement" | "autre";

export const ANNONCE_TYPES: AnnonceType[] = ["partenariat", "emploi", "evenement", "autre"];

export interface Annonce {
  id: number;
  prestataire_id: number;
  titre: string;
  type: AnnonceType;
  description: string;
  localisation: string | null;
  contact: string;
  date_limite: string | null;
  statut: Statut;
  cree_le: string;
}

export type ProviderActivity = Activity & { statut: Statut };

export interface ActivityInput {
  titre: string;
  description: string;
  prix: number;
  duree: number;
  localisation: string;
  category_id: number;
}

export interface AnnonceInput {
  titre: string;
  type: AnnonceType;
  description: string;
  localisation: string | null;
  contact: string;
  date_limite: string | null;
}

export const prestataireKeys = {
  activities: ["prestataire", "activities"] as const,
  annonces: ["prestataire", "annonces"] as const,
  publicAnnonces: ["annonces"] as const,
};

const prestataireApi = {
  activities: () =>
    api.get<ProviderActivity[]>(endpoints.prestataire.activities).then((r) => r.data),
  createActivity: (payload: ActivityInput) =>
    api.post<ProviderActivity>(endpoints.prestataire.activities, payload).then((r) => r.data),
  uploadPhoto: (id: number, photo: File) => {
    const form = new FormData();
    form.append("photo", photo);
    return api.post(endpoints.prestataire.activityPhoto(id), form).then((r) => r.data);
  },
  deleteActivity: (id: number) => api.delete(endpoints.prestataire.activity(id)),
  annonces: () => api.get<Annonce[]>(endpoints.prestataire.annonces).then((r) => r.data),
  createAnnonce: (payload: AnnonceInput) =>
    api.post<Annonce>(endpoints.prestataire.annonces, payload).then((r) => r.data),
  deleteAnnonce: (id: number) => api.delete(endpoints.prestataire.annonce(id)),
  publicAnnonces: () => api.get<Annonce[]>(endpoints.annonces.list).then((r) => r.data),
};

export function useMyActivities() {
  return useQuery({ queryKey: prestataireKeys.activities, queryFn: prestataireApi.activities });
}

export function useMyAnnonces() {
  return useQuery({ queryKey: prestataireKeys.annonces, queryFn: prestataireApi.annonces });
}

export function usePublicAnnonces() {
  return useQuery({
    queryKey: prestataireKeys.publicAnnonces,
    queryFn: prestataireApi.publicAnnonces,
    staleTime: 60_000,
  });
}

/** Crée l'activité puis, si fournie, envoie sa photo (deux appels : JSON puis multipart). */
export function useCreateActivity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ payload, photo }: { payload: ActivityInput; photo: File | null }) => {
      const activity = await prestataireApi.createActivity(payload);
      if (photo) await prestataireApi.uploadPhoto(activity.id, photo);
      return activity;
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: prestataireKeys.activities }),
  });
}

export function useDeleteActivity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: prestataireApi.deleteActivity,
    onSettled: () => queryClient.invalidateQueries({ queryKey: prestataireKeys.activities }),
  });
}

export function useCreateAnnonce() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: prestataireApi.createAnnonce,
    onSettled: () => queryClient.invalidateQueries({ queryKey: prestataireKeys.annonces }),
  });
}

export function useDeleteAnnonce() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: prestataireApi.deleteAnnonce,
    onSettled: () => queryClient.invalidateQueries({ queryKey: prestataireKeys.annonces }),
  });
}
