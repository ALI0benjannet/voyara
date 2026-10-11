import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { toApiError } from "@voyara/api";

import { travelAdminApi, type TravelPayload } from "./api";

export const travelKeys = {
  all: ["travel-admin"] as const,
  list: (path: string) => [...travelKeys.all, path] as const,
};

function showError(error: unknown, fallback: string) {
  const { message } = toApiError(error);
  toast.error(message.startsWith("errors.") ? fallback : message);
}

export function useTravelItems(path: string) {
  return useQuery({ queryKey: travelKeys.list(path), queryFn: () => travelAdminApi.list(path) });
}

export function useTravelMutations(path: string) {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: travelKeys.list(path) });

  const create = useMutation({
    mutationFn: (payload: TravelPayload) => travelAdminApi.create(path, payload),
    onSuccess: () => {
      toast.success("Élément créé");
      invalidate();
    },
    onError: (e) => showError(e, "Création impossible"),
  });

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: TravelPayload }) =>
      travelAdminApi.update(path, id, payload),
    onSuccess: () => {
      toast.success("Modifications enregistrées");
      invalidate();
    },
    onError: (e) => showError(e, "Enregistrement impossible"),
  });

  const remove = useMutation({
    mutationFn: (id: number) => travelAdminApi.remove(path, id),
    onSuccess: () => {
      toast.success("Élément supprimé");
      invalidate();
    },
    onError: (e) => showError(e, "Suppression impossible"),
  });

  return { create, update, remove };
}
