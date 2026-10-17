import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";

import type { Activity } from "@/features/catalog/api";

export type Statut = "en_attente" | "publiee" | "refusee";

export type ProviderActivity = Activity & { statut: Statut };

export interface ActivityInput {
  titre: string;
  description: string;
  prix: number;
  duree: number;
  localisation: string;
  category_id: number;
}

export const prestataireKeys = {
  activities: ["prestataire", "activities"] as const,
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
};

export function useMyActivities() {
  return useQuery({ queryKey: prestataireKeys.activities, queryFn: prestataireApi.activities });
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
