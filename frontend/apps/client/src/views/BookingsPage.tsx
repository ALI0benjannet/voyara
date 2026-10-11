import { CalendarCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import Link from "next/link";

import { useAuth } from "@voyara/auth/hooks/use-auth";
import { cn } from "@voyara/ui/lib/utils";

import { ActivityImage } from "@/components/activities/ActivityImage";
import { formatPrice } from "@/features/catalog/format";
import { useCancelBooking, useMyBookings, type BookingItem } from "@/features/bookings/hooks";
import { paths } from "@/routes/paths";

const STATUS_STYLES: Record<BookingItem["statut"], string> = {
  confirmed: "bg-primary/12 text-primary",
  pending: "bg-gold/20 text-[#9A6E14]",
  cancelled: "bg-destructive/10 text-destructive",
};

/** Titre de l'activité réservée dans la langue active, avec repli sur le
 *  français puis sur l'identifiant si le catalogue n'a pas répondu. */
function bookingTitle(booking: BookingItem, lang?: string): string {
  const base = lang?.split("-")[0];
  if (base === "en" && booking.activity_titre_en?.trim()) return booking.activity_titre_en;
  if (base === "ar" && booking.activity_titre_ar?.trim()) return booking.activity_titre_ar;
  return booking.activity ?? `#${booking.activity_id}`;
}

export default function BookingsPage() {
  const { t, i18n } = useTranslation();
  const { isAuthenticated } = useAuth();
  const { data, isLoading } = useMyBookings();
  const cancelBooking = useCancelBooking();

  const bookings = data?.items ?? [];

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(
      i18n.resolvedLanguage === "en" ? "en-GB" : i18n.resolvedLanguage === "ar" ? "ar-TN" : "fr-FR",
      { day: "numeric", month: "short", year: "numeric" },
    );

  return (
    <main className="mx-auto max-w-4xl px-4 py-10 sm:px-8">
      <h1 className="font-display mb-2 text-4xl">{t("nav.bookings")}</h1>
      <p className="text-muted-foreground mb-8">{t("bookingsPage.subtitle")}</p>

      {!isAuthenticated ? (
        <div className="border-input bg-card rounded-2xl border border-dashed px-5 py-20 text-center">
          <CalendarCheck className="text-primary/40 mx-auto mb-3 size-10" />
          <div className="font-display mb-2 text-2xl">{t("bookingsPage.loginTitle")}</div>
          <div className="text-muted-foreground mb-6">{t("bookingsPage.loginSub")}</div>
          <Link
            href={paths.login}
            className="bg-primary text-primary-foreground hover:bg-primary-hover rounded-full px-6 py-3 font-semibold transition-colors"
          >
            {t("nav.login")}
          </Link>
        </div>
      ) : isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-muted h-28 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : bookings.length === 0 ? (
        <div className="border-input bg-card rounded-2xl border border-dashed px-5 py-20 text-center">
          <div className="font-display mb-2 text-2xl">{t("bookingsPage.emptyTitle")}</div>
          <div className="text-muted-foreground mb-6">{t("bookingsPage.emptySub")}</div>
          <Link
            href={paths.activities}
            className="bg-primary text-primary-foreground hover:bg-primary-hover rounded-full px-6 py-3 font-semibold transition-colors"
          >
            {t("favorites.cta")}
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {bookings.map((booking) => (
            <div
              key={booking.id}
              className="border-border bg-card flex items-center gap-4 rounded-2xl border p-4 transition-shadow hover:shadow-[0_10px_26px_rgba(28,54,65,.1)]"
            >
              <Link
                href={`/activities/${booking.activity_id}`}
                className="relative hidden h-20 w-28 shrink-0 overflow-hidden rounded-xl sm:block"
              >
                <ActivityImage
                  src={booking.activity_photo}
                  label={bookingTitle(booking, i18n.language)}
                />
              </Link>
              <div className="min-w-0 flex-1">
                <Link
                  href={`/activities/${booking.activity_id}`}
                  className="font-display hover:text-primary-hover text-lg"
                >
                  {bookingTitle(booking, i18n.language)}
                </Link>
                <div className="text-muted-foreground mt-1 text-[13px]">
                  {formatDate(booking.date_reservation)} ·{" "}
                  {t("bookingsPage.guests", { count: booking.nb_places })}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <span
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-bold",
                    STATUS_STYLES[booking.statut],
                  )}
                >
                  {t(`bookingsPage.status.${booking.statut}`)}
                </span>
                <span className="text-lg font-bold">{formatPrice(booking.montant_total)}</span>
                {booking.statut === "pending" && (
                  <Link
                    href={`/bookings/${booking.id}/pay`}
                    className="bg-primary text-primary-foreground hover:bg-primary-hover rounded-full px-4 py-1.5 text-xs font-bold transition-colors"
                  >
                    {t("payment.payNow", "Payer maintenant")}
                  </Link>
                )}
                {booking.statut === "confirmed" && (
                  <Link
                    href={`/bookings/${booking.id}/pay`}
                    className="border-primary text-primary hover:bg-primary rounded-full border px-4 py-1.5 text-xs font-bold transition-colors hover:text-white"
                  >
                    {t("payment.showQr", "QR code")}
                  </Link>
                )}
                {booking.statut !== "cancelled" && (
                  <button
                    type="button"
                    onClick={() => cancelBooking.mutate(booking.id)}
                    disabled={cancelBooking.isPending}
                    className="text-muted-foreground hover:text-destructive text-xs font-semibold underline-offset-2 hover:underline disabled:opacity-50"
                  >
                    {t("actions.cancel")}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
