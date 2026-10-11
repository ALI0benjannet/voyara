import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { catalogApi, type ActivityFilters } from "./api";

export const catalogKeys = {
  all: ["catalog"] as const,
  categories: () => [...catalogKeys.all, "categories"] as const,
  activities: (filters: ActivityFilters) => [...catalogKeys.all, "activities", filters] as const,
  activity: (id: number) => [...catalogKeys.all, "activity", id] as const,
  availabilities: (id: number) => [...catalogKeys.all, "availabilities", id] as const,
};

export function useCategories() {
  return useQuery({
    queryKey: catalogKeys.categories(),
    queryFn: catalogApi.categories,
    staleTime: 10 * 60_000,
  });
}

export function useActivities(filters: ActivityFilters = {}) {
  return useQuery({
    queryKey: catalogKeys.activities(filters),
    queryFn: () => catalogApi.activities(filters),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}

export function useActivity(id: number) {
  return useQuery({
    queryKey: catalogKeys.activity(id),
    queryFn: () => catalogApi.activity(id),
    enabled: Number.isFinite(id) && id > 0,
    staleTime: 60_000,
  });
}

export function useAvailabilities(id: number) {
  return useQuery({
    queryKey: catalogKeys.availabilities(id),
    queryFn: () => catalogApi.availabilities(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}
