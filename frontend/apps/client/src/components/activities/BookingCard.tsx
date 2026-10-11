"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Minus, Plus } from "lucide-react";

import { api, getAuthErrorCode, toApiError } from "@voyara/api";
import { endpoints } from "@voyara/api/endpoints";
import { useAuth } from "@voyara/auth/hooks/use-auth";

import { formatPrice } from "@/features/catalog/format";
import { useAvailabilities } from "@/features/catalog/hooks";
import { useCreateBooking } from "@/features/bookings/hooks";
import { paths } from "@/routes/paths";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Carte de réservation (page détail) — créneaux réels + voyageurs + saga booking. */
export function BookingCard({ activityId, prix }: { activityId: number; prix: number }) {
  const { t, language } = useHydratedTranslation();
  const router = useRouter();
  const { isAuthenticated } = useAuth();

  const { data: availabilities } = useAvailabilities(activityId);
  const createBooking = useCreateBooking();

  const [availabilityId, setAvailabilityId] = useState<number | null>(null);
  const [guests, setGuests] = useState(2);
  const [bookedId, setBookedId] = useState<number | null>(null);
  const booked = bookedId != null;
  const setBooked = (v: boolean) => setBookedId(v ? bookedId : null);
  const [error, setError] = useState<string | null>(null);
  const [promoInput, setPromoInput] = useState("");
  const [promo, setPromo] = useState<{ code: string; reduction: number } | null>(null);
  const [promoError, setPromoError] = useState<string | null>(null);
  const [promoChecking, setPromoChecking] = useState(false);

  const applyPromo = async () => {
    const code = promoInput.trim();
    if (!code) return;
    setPromoChecking(true);
    setPromoError(null);
    try {
      const { data } = await api.post<{ code: string; reduction: number }>(
        endpoints.bookings.validatePromo,
        { code },
      );
      setPromo({ code: data.code, reduction: data.reduction });
    } catch {
      setPromo(null);
      setPromoError(t("detail.promoInvalid", "Code promo invalide ou expiré."));
    } finally {
      setPromoChecking(false);
    }
  };

  const openSlots = useMemo(
    () => (availabilities ?? []).filter((slot) => slot.places_disponibles > 0),
    [availabilities],
  );
  const selectedSlot = openSlots.find((slot) => slot.id === availabilityId) ?? openSlots[0] ?? null;

  const formatSlot = (date: string, seats: number) => {
    const label = new Date(`${date}T12:00:00`).toLocaleDateString(
      language === "en" ? "en-GB" : language === "ar" ? "ar-TN" : "fr-FR",
      { weekday: "short", day: "numeric", month: "short" },
    );
    return `${label} · ${t("detail.seatsLeft", { count: seats })}`;
  };

  const baseTotal = prix * guests;
  const total = promo ? Math.round(baseTotal * (1 - promo.reduction / 100) * 100) / 100 : baseTotal;

  const confirm = async () => {
    if (!isAuthenticated) {
      router.push(`${paths.login}?next=${encodeURIComponent(`/activities/${activityId}`)}`);
      return;
    }
    if (!selectedSlot) return;
    setError(null);
    try {
      const created = await createBooking.mutateAsync({
        activity_id: activityId,
        availability_id: selectedSlot.id,
        guests,
        ...(promo ? { promo_code: promo.code } : {}),
      });
      setBookedId(created.id);
    } catch (err) {
      const code = getAuthErrorCode(err);
      const { status } = toApiError(err);
      if (status === 409) setError(t("detail.noSeats"));
      else if (code === "rate_limited") setError(t("auth.errors.rate_limited"));
      else setError(t("errors.unknown"));
    }
  };

  return (
    <aside
      className="border-border bg-card overflow-hidden rounded-2xl border lg:sticky lg:top-32"
      style={{ boxShadow: "var(--shadow-card-hover)" }}
    >
      {/* Bandeau prix : détache l'information décisive du reste du formulaire. */}
      <div className="border-border bg-secondary/50 border-b px-6 py-5">
        <div className="flex items-baseline gap-1.5">
          <span className="text-primary-hover text-3xl font-bold">{formatPrice(prix)}</span>
          <span className="text-muted-foreground text-sm">{t("catalog.perPerson")}</span>
        </div>
      </div>

      <div className="p-6">
        <label className="mb-1.5 block text-[13px] font-semibold">{t("detail.dateL")}</label>
        {openSlots.length === 0 ? (
          <div className="border-input text-muted-foreground mb-4 rounded-xl border border-dashed px-4 py-3 text-sm">
            {t("detail.noAvailability")}
          </div>
        ) : (
          <select
            value={selectedSlot?.id ?? ""}
            onChange={(e) => setAvailabilityId(Number(e.target.value))}
            className="border-input bg-card focus:border-primary mb-4 w-full rounded-xl border px-3.5 py-3 text-[15px] focus:outline-none"
          >
            {openSlots.map((slot) => (
              <option key={slot.id} value={slot.id}>
                {formatSlot(slot.date, slot.places_disponibles)}
              </option>
            ))}
          </select>
        )}

        <label className="mb-1.5 block text-[13px] font-semibold">{t("detail.guestsL")}</label>
        <div className="border-input mb-5 flex items-center gap-3.5 rounded-xl border px-3 py-2">
          <button
            type="button"
            aria-label="-"
            onClick={() => {
              setGuests((g) => Math.max(1, g - 1));
              setBooked(false);
            }}
            className="border-input bg-card hover:border-primary hover:text-primary flex size-10 items-center justify-center rounded-full border transition-colors"
          >
            <Minus className="size-4" />
          </button>
          <span className="flex-1 text-center text-lg font-bold">{guests}</span>
          <button
            type="button"
            aria-label="+"
            onClick={() => {
              setGuests((g) => Math.min(8, selectedSlot?.places_disponibles ?? 8, g + 1));
              setBooked(false);
            }}
            className="border-input bg-card hover:border-primary hover:text-primary flex size-10 items-center justify-center rounded-full border transition-colors"
          >
            <Plus className="size-4" />
          </button>
        </div>

        <label className="mb-1.5 block text-[13px] font-semibold">
          {t("detail.promoLabel", "Code promo")}
        </label>
        <div className="mb-1 flex gap-2">
          <input
            value={promoInput}
            onChange={(e) => {
              setPromoInput(e.target.value);
              setPromo(null);
              setPromoError(null);
            }}
            placeholder={t("detail.promoPlaceholder", "BIENVENUE10")}
            className="border-input bg-card placeholder:text-foreground/40 focus:border-primary min-w-0 flex-1 rounded-xl border px-3.5 py-2.5 text-[14px] uppercase placeholder:normal-case focus:outline-none"
          />
          <button
            type="button"
            onClick={applyPromo}
            disabled={promoChecking || !promoInput.trim()}
            className="border-input hover:border-primary hover:text-primary rounded-xl border px-4 text-[13px] font-semibold disabled:opacity-50"
          >
            {t("detail.promoApply", "Appliquer")}
          </button>
        </div>
        {promoError && (
          <p className="text-destructive mb-2 text-[13px] font-medium">{promoError}</p>
        )}
        {promo && (
          <p className="text-primary mb-2 text-[13px] font-semibold">
            {t("detail.promoApplied", "Code {{code}} appliqué : -{{reduction}} %", {
              code: promo.code,
              reduction: promo.reduction,
            })}
          </p>
        )}

        <div className="border-border mb-4 flex justify-between border-t py-3.5">
          <span className="font-semibold">{t("detail.total")}</span>
          <span className="text-end">
            {promo && (
              <span className="text-muted-foreground me-2 text-sm line-through">
                {formatPrice(baseTotal)}
              </span>
            )}
            <span className="text-lg font-bold">{formatPrice(total)}</span>
          </span>
        </div>

        {error && (
          <div className="border-destructive/30 bg-destructive/5 text-destructive mb-3 rounded-xl border px-4 py-3 text-sm font-medium">
            {error}
          </div>
        )}

        {booked ? (
          <>
            <div className="border-primary/30 bg-primary/10 text-primary mb-3 rounded-xl border px-4 py-3.5 text-center font-semibold">
              {t("detail.bookedPayMsg", "Réservation enregistrée — payez pour la confirmer")}
            </div>
            <Link
              href={`/bookings/${bookedId}/pay`}
              className="bg-primary text-primary-foreground hover:bg-primary-hover mb-2 block w-full rounded-full py-3.5 text-center text-[15px] font-semibold transition-colors"
            >
              {t("payment.payNow", "Payer maintenant")}
            </Link>
            <Link
              href={paths.bookings}
              className="border-input hover:border-primary hover:text-primary block w-full rounded-full border py-3 text-center text-[14px] font-semibold transition-colors"
            >
              {t("detail.seeBookings")}
            </Link>
          </>
        ) : (
          <button
            type="button"
            onClick={confirm}
            disabled={createBooking.isPending || openSlots.length === 0}
            className="bg-primary text-primary-foreground hover:bg-primary-hover w-full rounded-full py-3.5 text-[15px] font-semibold transition-colors disabled:opacity-50"
          >
            {createBooking.isPending
              ? t("states.loading")
              : isAuthenticated
                ? t("detail.confirm")
                : t("detail.loginToBook")}
          </button>
        )}
        <div className="text-muted-foreground mt-3.5 text-center text-[13px]">
          {t("detail.freeCancel")}
        </div>
      </div>
    </aside>
  );
}
