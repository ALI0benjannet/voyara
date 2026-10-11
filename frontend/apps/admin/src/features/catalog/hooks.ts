import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { toApiError } from "@voyara/api";

import {
  catalogAdminApi,
  type Activity,
  type ActivityPayload,
} from "./api";

export const catalogKeys = {
  all: ["catalog-admin"] as const,
  categories: () => [...catalogKeys.all, "categories"] as const,
  activity: (id: number) => [...catalogKeys.all, "activity", id] as const,
  availabilities: (id: number) => [...catalogKeys.all, "availabilities", id] as const,
};

/** Invalide à la fois le cache local et les listes du BFF admin. */
function useInvalidateCatalog() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: catalogKeys.all });
    queryClient.invalidateQueries({ queryKey: ["admin"] });
  };
}

function showError(error: unknown, fallback: string) {
  const { message } = toApiError(error);
  toast.error(message.startsWith("errors.") ? fallback : message);
}

// ---------------------------------------------------------------------------
// Catégories
// ---------------------------------------------------------------------------

export function useCategories() {
  return useQuery({ queryKey: catalogKeys.categories(), queryFn: catalogAdminApi.categories });
}

export function useCategoryMutations() {
  const invalidate = useInvalidateCatalog();

  const create = useMutation({
    mutationFn: (nom: string) => catalogAdminApi.createCategory(nom),
    onSuccess: () => {
      toast.success("Catégorie créée");
      invalidate();
    },
    onError: (e) => showError(e, "Création impossible"),
  });

  const rename = useMutation({
    mutationFn: ({ id, nom }: { id: number; nom: string }) =>
      catalogAdminApi.updateCategory(id, nom),
    onSuccess: () => {
      toast.success("Catégorie renommée");
      invalidate();
    },
    onError: (e) => showError(e, "Renommage impossible"),
  });

  const remove = useMutation({
    mutationFn: (id: number) => catalogAdminApi.deleteCategory(id),
    onSuccess: () => {
      toast.success("Catégorie supprimée");
      invalidate();
    },
    onError: (e) => showError(e, "Suppression impossible"),
  });

  return { create, rename, remove };
}

// ---------------------------------------------------------------------------
// Activités
// ---------------------------------------------------------------------------

export function useActivity(id: number | null) {
  return useQuery({
    queryKey: catalogKeys.activity(id ?? 0),
    queryFn: () => catalogAdminApi.activity(id as number),
    enabled: id != null && id > 0,
  });
}

export function useActivityMutations() {
  const invalidate = useInvalidateCatalog();

  const create = useMutation({
    mutationFn: (payload: ActivityPayload) => catalogAdminApi.createActivity(payload),
    onSuccess: () => invalidate(),
    onError: (e) => showError(e, "Création impossible"),
  });

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<ActivityPayload> }) =>
      catalogAdminApi.updateActivity(id, payload),
    onSuccess: () => {
      toast.success("Activité enregistrée");
      invalidate();
    },
    onError: (e) => showError(e, "Enregistrement impossible"),
  });

  const remove = useMutation({
    mutationFn: (id: number) => catalogAdminApi.deleteActivity(id),
    onSuccess: () => {
      toast.success("Activité supprimée");
      invalidate();
    },
    onError: (e) => showError(e, "Suppression impossible (réservations existantes ?)"),
  });

  const uploadPhoto = useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) =>
      catalogAdminApi.uploadPhoto(id, file),
    onSuccess: () => {
      toast.success("Photo mise à jour");
      invalidate();
    },
    onError: (e) => showError(e, "Envoi de la photo impossible"),
  });

  const deletePhoto = useMutation({
    mutationFn: (id: number) => catalogAdminApi.deletePhoto(id),
    onSuccess: () => {
      toast.success("Photo supprimée");
      invalidate();
    },
    onError: (e) => showError(e, "Suppression impossible"),
  });

  return { create, update, remove, uploadPhoto, deletePhoto };
}

// ---------------------------------------------------------------------------
// Créneaux
// ---------------------------------------------------------------------------

export function useAvailabilities(activityId: number | null) {
  return useQuery({
    queryKey: catalogKeys.availabilities(activityId ?? 0),
    queryFn: () => catalogAdminApi.availabilities(activityId as number),
    enabled: activityId != null && activityId > 0,
  });
}

export function useAvailabilityMutations() {
  const invalidate = useInvalidateCatalog();

  const create = useMutation({
    mutationFn: catalogAdminApi.createAvailability,
    onSuccess: () => {
      toast.success("Créneau ajouté");
      invalidate();
    },
    onError: (e) => showError(e, "Ajout impossible"),
  });

  const update = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: Partial<{ date: string; heure: string; places_disponibles: number }>;
    }) => catalogAdminApi.updateAvailability(id, payload),
    onSuccess: () => invalidate(),
    onError: (e) => showError(e, "Modification impossible"),
  });

  const remove = useMutation({
    mutationFn: (id: number) => catalogAdminApi.deleteAvailability(id),
    onSuccess: () => {
      toast.success("Créneau supprimé");
      invalidate();
    },
    onError: (e) => showError(e, "Suppression impossible"),
  });

  return { create, update, remove };
}

export type { Activity, ActivityPayload };
