/** Accès au catalogue depuis les Server Components (SSR/SEO).
 *
 * Côté serveur, Next parle directement au gateway des microservices
 * (`API_INTERNAL_URL`) — pas de proxy, pas d'axios. Les réponses sont mises
 * en cache et revalidées toutes les 60 s (ISR).
 */

import type { Activity, Availability, Category, PageOf } from "@/features/catalog/api";
import type { CarRental, Flight, Stay, Transfer } from "@/features/offres/api";

const GATEWAY = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const REVALIDATE = { next: { revalidate: 60 } } as const;

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${GATEWAY}${path}`, REVALIDATE);
  if (!res.ok) throw new Error(`Gateway ${res.status} on ${path}`);
  return res.json() as Promise<T>;
}

export async function fetchCategories(): Promise<Category[]> {
  try {
    return await get<Category[]>("/api/v1/categories");
  } catch {
    return [];
  }
}

export async function fetchActivities(params: {
  search?: string;
  category_id?: number;
  size?: number;
}): Promise<PageOf<Activity>> {
  const qs = new URLSearchParams({ size: String(params.size ?? 50) });
  if (params.search) qs.set("search", params.search);
  if (params.category_id) qs.set("category_id", String(params.category_id));
  try {
    return await get<PageOf<Activity>>(`/api/v1/activities?${qs}`);
  } catch {
    return { items: [], total: 0, page: 1, size: params.size ?? 50, pages: 0 };
  }
}

/** Catalogue complet (l'API pagine à 100 au plus) : sert aux agrégats de
 *  l'accueil (compteurs par région et par catégorie, classement par avis). */
export async function fetchAllActivities(): Promise<Activity[]> {
  const size = 100;
  const firstPage = await get<PageOf<Activity>>(`/api/v1/activities?size=${size}&page=1`).catch(
    () => null,
  );
  if (!firstPage) return [];
  const rest = await Promise.all(
    Array.from({ length: Math.max(0, firstPage.pages - 1) }, (_, i) =>
      get<PageOf<Activity>>(`/api/v1/activities?size=${size}&page=${i + 2}`).catch(() => null),
    ),
  );
  return [firstPage, ...rest].flatMap((p) => p?.items ?? []);
}

export async function fetchActivity(id: number): Promise<Activity | null> {
  try {
    return await get<Activity>(`/api/v1/activities/${id}`);
  } catch {
    return null;
  }
}

export async function fetchAvailabilities(id: number): Promise<Availability[]> {
  try {
    return await get<Availability[]>(`/api/v1/activities/${id}/availabilities`);
  } catch {
    return [];
  }
}

/** Offres de voyage publiques. Paramètres vides ignorés ; panne = liste vide. */
async function fetchOffres<T>(
  segment: string,
  params: Record<string, string | undefined>,
): Promise<T[]> {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value) qs.set(key, value);
  try {
    return await get<T[]>(`/api/v1/offres/${segment}${qs.size ? `?${qs}` : ""}`);
  } catch {
    return [];
  }
}

export const fetchStays = (params: { ville?: string; type?: string }) =>
  fetchOffres<Stay>("sejours", params);

export const fetchFlights = (params: {
  depart?: string;
  arrivee?: string;
  jour?: string;
  /** 200 par défaut côté API ; l'accueil demande tout pour un compte exact. */
  limite?: string;
}) => fetchOffres<Flight>("vols", params);

export const fetchCarRentals = (params: { ville?: string; categorie?: string }) =>
  fetchOffres<CarRental>("voitures", params);

export const fetchTransfers = (params: { depart?: string }) =>
  fetchOffres<Transfer>("transferts", params);

export interface ReviewStat {
  average: number;
  count: number;
}

/** Moyennes d'avis par activité (review-service). Tolérant aux pannes. */
export async function fetchReviewStats(ids: number[]): Promise<Record<string, ReviewStat>> {
  if (ids.length === 0) return {};
  try {
    return await get<Record<string, ReviewStat>>(
      `/api/v1/reviews/stats?activity_ids=${ids.join(",")}`,
    );
  } catch {
    return {};
  }
}
