import { api } from "@voyara/api/axios";

/** Ligne d'une offre de voyage telle que renvoyée par le catalog-service. Les
 *  colonnes varient selon l'offre : la page générique les lit via sa config. */
export type TravelItem = { id: number } & Record<string, unknown>;

export type TravelPayload = Record<string, string | number | boolean | null>;

/** CRUD des offres de voyage — endpoints admin du catalog-service (JWT admin). */
export const travelAdminApi = {
  list: (path: string) => api.get<TravelItem[]>(`/api/v1/${path}`).then((r) => r.data),
  create: (path: string, payload: TravelPayload) =>
    api.post<TravelItem>(`/api/v1/${path}`, payload).then((r) => r.data),
  update: (path: string, id: number, payload: TravelPayload) =>
    api.put<TravelItem>(`/api/v1/${path}/${id}`, payload).then((r) => r.data),
  remove: (path: string, id: number) => api.delete(`/api/v1/${path}/${id}`),
};
