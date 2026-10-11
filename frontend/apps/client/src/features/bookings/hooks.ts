import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";
import { useAuth } from "@voyara/auth/hooks/use-auth";

import type { PageOf } from "@/features/catalog/api";

export interface BookingItem {
  id: number;
  user_id: number;
  activity_id: number;
  activity: string | null;
  /** Enrichis par le booking-service depuis le catalogue (titre traduit + vignette). */
  activity_titre_en?: string | null;
  activity_titre_ar?: string | null;
  activity_photo?: string | null;
  availability_id: number;
  statut: "pending" | "confirmed" | "cancelled";
  montant_total: number;
  nb_places: number;
  qr_code: string | null;
  date_reservation: string;
}

export const bookingKeys = { all: ["bookings"] as const };

export function useMyBookings() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: bookingKeys.all,
    queryFn: () =>
      api
        .get<PageOf<BookingItem>>(endpoints.bookings.list, { params: { size: 50 } })
        .then((r) => r.data),
    enabled: isAuthenticated,
    staleTime: 30_000,
  });
}

export function useCreateBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      activity_id: number;
      availability_id: number;
      guests: number;
      promo_code?: string;
    }) =>
      api.post<BookingItem>(endpoints.bookings.create, payload).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: bookingKeys.all });
      queryClient.invalidateQueries({ queryKey: ["catalog"] });
    },
  });
}

export function useCancelBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (bookingId: number) =>
      api.delete(endpoints.bookings.cancel(bookingId)).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: bookingKeys.all });
      queryClient.invalidateQueries({ queryKey: ["catalog"] });
    },
  });
}

export function useBooking(id: number, options?: { refetchInterval?: number | false }) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: [...bookingKeys.all, id],
    queryFn: () =>
      api.get<BookingItem>(endpoints.bookings.detail(id)).then((r) => r.data),
    enabled: isAuthenticated && Number.isFinite(id) && id > 0,
    refetchInterval: options?.refetchInterval ?? false,
  });
}

/** SVG du QR code (endpoint authentifie — un <img> ne peut pas envoyer le JWT). */
export function useBookingQr(id: number, enabled: boolean) {
  return useQuery({
    queryKey: [...bookingKeys.all, id, "qr"],
    queryFn: () =>
      api
        .get<string>(endpoints.bookings.qrcode(id), { responseType: "text" })
        .then((r) => r.data),
    enabled,
    staleTime: Infinity,
  });
}
