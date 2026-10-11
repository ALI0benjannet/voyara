import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";

export interface Category {
  id: number;
  nom: string;
  nom_en?: string | null;
  nom_ar?: string | null;
}

export interface Activity {
  id: number;
  titre: string;
  description: string;
  titre_en?: string | null;
  titre_ar?: string | null;
  description_en?: string | null;
  description_ar?: string | null;
  prix: number;
  duree: number; // minutes
  localisation: string;
  latitude: number | null;
  longitude: number | null;
  photos: string | null;
  category_id: number;
  category: Category | null;
}

export interface PageOf<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface Availability {
  id: number;
  activity_id: number;
  date: string; // ISO date
  heure: string; // HH:MM:SS
  places_disponibles: number;
}

export interface ActivityFilters {
  page?: number;
  size?: number;
  category_id?: number;
  search?: string;
}

export const catalogApi = {
  categories: () =>
    api.get<Category[]>(endpoints.categories.list).then((r) => r.data),
  activities: (params: ActivityFilters = {}) =>
    api.get<PageOf<Activity>>(endpoints.activities.list, { params }).then((r) => r.data),
  activity: (id: number) =>
    api.get<Activity>(endpoints.activities.detail(id)).then((r) => r.data),
  availabilities: (id: number) =>
    api.get<Availability[]>(endpoints.activities.availabilities(id)).then((r) => r.data),
};
