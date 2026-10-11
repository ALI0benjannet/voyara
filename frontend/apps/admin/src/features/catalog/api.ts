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

export interface Availability {
  id: number;
  activity_id: number;
  date: string;
  heure: string;
  places_disponibles: number;
}

export interface ActivityPayload {
  titre: string;
  description: string;
  /** Traductions facultatives — vides, le client affiche le texte français. */
  titre_en?: string | null;
  titre_ar?: string | null;
  description_en?: string | null;
  description_ar?: string | null;
  prix: number;
  duree: number;
  localisation: string;
  latitude: number | null;
  longitude: number | null;
  category_id: number;
}

/** CRUD catalogue — endpoints admin du catalog-service (JWT admin). */
export const catalogAdminApi = {
  // Catégories
  categories: () => api.get<Category[]>(endpoints.categories.list).then((r) => r.data),
  createCategory: (nom: string) =>
    api.post<Category>("/api/v1/categories", { nom }).then((r) => r.data),
  updateCategory: (id: number, nom: string) =>
    api.put<Category>(`/api/v1/categories/${id}`, { nom }).then((r) => r.data),
  deleteCategory: (id: number) => api.delete(`/api/v1/categories/${id}`),

  // Activités
  activity: (id: number) =>
    api.get<Activity>(endpoints.activities.detail(id)).then((r) => r.data),
  createActivity: (payload: ActivityPayload) =>
    api.post<Activity>("/api/v1/activities", payload).then((r) => r.data),
  updateActivity: (id: number, payload: Partial<ActivityPayload>) =>
    api.put<Activity>(`/api/v1/activities/${id}`, payload).then((r) => r.data),
  deleteActivity: (id: number) => api.delete(`/api/v1/activities/${id}`),

  // Photo
  uploadPhoto: (id: number, file: File) => {
    const form = new FormData();
    form.append("photo", file);
    return api.post<Activity>(`/api/v1/activities/${id}/photo`, form).then((r) => r.data);
  },
  deletePhoto: (id: number) => api.delete(`/api/v1/activities/${id}/photo`),

  // Créneaux
  availabilities: (activityId: number) =>
    api
      .get<Availability[]>(endpoints.activities.availabilities(activityId))
      .then((r) => r.data),
  createAvailability: (payload: {
    activity_id: number;
    date: string;
    heure: string;
    places_disponibles: number;
  }) => api.post<Availability>("/api/v1/availabilities", payload).then((r) => r.data),
  updateAvailability: (
    id: number,
    payload: Partial<{ date: string; heure: string; places_disponibles: number }>,
  ) => api.put<Availability>(`/api/v1/availabilities/${id}`, payload).then((r) => r.data),
  deleteAvailability: (id: number) => api.delete(`/api/v1/availabilities/${id}`),
};
