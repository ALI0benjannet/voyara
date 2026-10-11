import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { adminApi, type ListParams } from "@/features/admin/api/admin.api";
import { adminKeys } from "@/features/admin/api/admin.keys";
export function useAdminStats() {
return useQuery({
queryKey: adminKeys.stats(),
queryFn: adminApi.stats,
staleTime: 60_000,
refetchOnWindowFocus: true,
});
}
export function useAdminUsers(params: ListParams = { page: 1, size: 20 }) {
return useQuery({
queryKey: adminKeys.users(params),
queryFn: () => adminApi.users(params),
placeholderData: keepPreviousData,
});
}
export function useAdminBookings(params: ListParams = { page: 1, size: 20 }) {
return useQuery({
queryKey: adminKeys.bookings(params),
queryFn: () => adminApi.bookings(params),
placeholderData: keepPreviousData,
});
}
export function useAdminActivities(params: ListParams = { page: 1, size: 20 }) {
return useQuery({
queryKey: adminKeys.activities(params),
queryFn: () => adminApi.activities(params),
placeholderData: keepPreviousData,
});
}
export function useAdminPayments(params: ListParams = { page: 1, size: 20 }) {
return useQuery({
queryKey: adminKeys.payments(params),
queryFn: () => adminApi.payments(params),
placeholderData: keepPreviousData,
});
}