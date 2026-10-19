import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";
import type {
AdminActivityRow,
AdminBookingRow,
AdminPaymentRow,
AdminUserRow,
DashboardStats,
Page,
} from "@/features/admin/types/admin.types";
export type ListParams = { page?: number; size?: number; search?: string };
/** Filtres de la liste des activités (appliqués côté catalog). */
export type ActivityListParams = ListParams & {
category_id?: number;
statut?: "publiee" | "en_attente" | "refusee";
};
export const adminApi = {
stats: () =>
api.get<DashboardStats>(endpoints.admin.stats).then((r) => r.data),
users: (params: ListParams = {}) =>
api
.get<Page<AdminUserRow>>(endpoints.admin.users, { params })
.then((r) => r.data),
bookings: (params: ListParams & { statut?: string } = {}) =>
api
.get<Page<AdminBookingRow>>(endpoints.admin.bookings, { params })
.then((r) => r.data),
activities: (params: ActivityListParams = {}) =>
api
.get<Page<AdminActivityRow>>(endpoints.admin.activities, { params })
.then((r) => r.data),
payments: (params: ListParams = {}) =>
api
.get<Page<AdminPaymentRow>>(endpoints.admin.payments, { params })
.then((r) => r.data),
};