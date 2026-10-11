export const queryKeys = {
  auth: { me: ["auth", "me"] as const },
  activities: {
    all: ["activities"] as const,
    list: (filters: Record<string, unknown>) => ["activities", "list", filters] as const,
    detail: (id: string) => ["activities", "detail", id] as const,
  },
  bookings: { all: ["bookings"] as const },
  favorites: { all: ["favorites"] as const },
} as const;