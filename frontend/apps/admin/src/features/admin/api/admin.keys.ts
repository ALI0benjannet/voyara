import type { ListParams } from "@/features/admin/api/admin.api";
export const adminKeys = {
all: ["admin"] as const,
stats: () => [...adminKeys.all, "stats"] as const,
users: (params: ListParams) => [...adminKeys.all, "users", params] as const,
bookings: (params: ListParams) => [...adminKeys.all, "bookings", params] as const,
activities: (params: ListParams) => [...adminKeys.all, "activities", params] as const,
payments: (params: ListParams) => [...adminKeys.all, "payments", params] as const,
};