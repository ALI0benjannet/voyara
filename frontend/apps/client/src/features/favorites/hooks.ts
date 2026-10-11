import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";
import { useAuth } from "@voyara/auth/hooks/use-auth";

export interface FavoriteItem {
  id: number;
  activity_id: number;
  activity: { id: number; titre: string; prix: number } | null;
}

export const favoriteKeys = { all: ["favorites"] as const };

const favoritesApi = {
  list: () => api.get<FavoriteItem[]>(endpoints.favorites.list).then((r) => r.data),
  add: (activityId: number) =>
    api.post(endpoints.favorites.add, { activity_id: activityId }).then((r) => r.data),
  remove: (activityId: number) =>
    api.delete(endpoints.favorites.remove(activityId)).then((r) => r.data),
};

export function useFavorites() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: favoriteKeys.all,
    queryFn: favoritesApi.list,
    enabled: isAuthenticated,
    staleTime: 60_000,
  });
}

/** Ensemble des activity_id favoris (vide si non connecté). */
export function useFavoriteIds(): Set<number> {
  const { data } = useFavorites();
  return new Set((data ?? []).map((f) => f.activity_id));
}

/** Toggle favori — redirige vers /login si l'utilisateur n'est pas connecté. */
export function useToggleFavorite() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const favoriteIds = useFavoriteIds();

  const mutation = useMutation({
    mutationFn: async (activityId: number) => {
      if (favoriteIds.has(activityId)) {
        await favoritesApi.remove(activityId);
      } else {
        await favoritesApi.add(activityId);
      }
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: favoriteKeys.all }),
  });

  return {
    isFavorite: (activityId: number) => favoriteIds.has(activityId),
    toggle: (activityId: number) => {
      if (!isAuthenticated) {
        router.push("/login");
        return;
      }
      mutation.mutate(activityId);
    },
    isPending: mutation.isPending,
  };
}
