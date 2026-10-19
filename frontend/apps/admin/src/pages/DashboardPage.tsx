import {
  AlertCircle,
  BedDouble,
  CalendarCheck,
  Car,
  CarTaxiFront,
  MapPin,
  Plane,
  RefreshCw,
  ShieldCheck,
  Users,
  Wallet,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "@voyara/ui/components/ui/button";
import { useAdminStats } from "@/features/admin/hook/use-admin";
import { formatCurrency, formatDateTime, formatNumber } from "@voyara/ui/lib/format";
import { cn } from "@voyara/ui/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  confirmed: "bg-emerald-100 text-emerald-700",
  pending: "bg-amber-100 text-amber-700",
  cancelled: "bg-rose-100 text-rose-700",
};

const STATUS_KEYS: Record<string, string> = {
  confirmed: "admin.status.confirmed",
  pending: "admin.status.pending",
  cancelled: "admin.status.cancelled",
};

function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  loading,
  to,
}: {
  label: string;
  value: string;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  loading?: boolean;
  /** Carte cliquable vers la liste correspondante. */
  to?: string;
}) {
  const body = (
    <div
      className={cn(
        "bg-card h-full rounded-lg border p-4 shadow-sm",
        to && "hover:border-primary/50 transition-colors",
      )}
    >
      <div className="flex items-center justify-between">
        <p className="text-muted-foreground text-sm">{label}</p>
        <Icon className="text-muted-foreground size-4" />
      </div>
      {loading ? (
        <div className="bg-muted mt-2 h-7 w-24 animate-pulse rounded" />
      ) : (
        <p className="mt-1 text-2xl font-semibold">{value}</p>
      )}
      {hint && !loading && <p className="text-muted-foreground mt-1 text-xs">{hint}</p>}
    </div>
  );
  return to ? (
    <Link
      to={to}
      className="focus-visible:ring-primary rounded-lg focus-visible:ring-2 focus-visible:outline-none"
    >
      {body}
    </Link>
  ) : (
    body
  );
}

export default function DashboardPage() {
  const { data, isLoading, isFetching, isError, error, refetch } = useAdminStats();
  const { t } = useTranslation();

  if (isError) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">{t("admin.dashboard.title")}</h1>
        <div className="border-destructive/30 bg-destructive/5 flex items-start gap-3 rounded-lg border p-4">
          <AlertCircle className="text-destructive mt-0.5 size-5" />
          <div className="space-y-2">
            <p className="text-destructive font-medium">{t("admin.dashboard.statsError")}</p>
            <p className="text-muted-foreground text-sm">
              {(error as Error)?.message ?? t("admin.common.error")}
            </p>
            <Button size="sm" variant="outline" onClick={() => refetch()}>
              <RefreshCw className="size-4" />
              {t("admin.common.retry")}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{t("admin.dashboard.title")}</h1>
          {data && (
            <p className="text-muted-foreground text-sm">
              {t("admin.dashboard.updatedAt", { date: formatDateTime(data.generated_at) })}
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={cn("size-4", isFetching && "animate-spin")} />
          {t("admin.dashboard.refresh")}
        </Button>
      </div>

      {/* Alerte de modération : seulement quand il y a quelque chose à faire. */}
      {!!data?.activities.en_attente && (
        <Link
          to="/moderation"
          className="flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 hover:bg-amber-100"
        >
          <ShieldCheck className="size-5 shrink-0" />
          <span className="font-medium">
            {t("admin.dashboard.pendingModeration", { count: data.activities.en_attente })}
          </span>
          <span className="ms-auto font-semibold underline">{t("admin.dashboard.moderate")}</span>
        </Link>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={t("admin.dashboard.bookings")}
          icon={CalendarCheck}
          loading={isLoading}
          to="/bookings"
          value={formatNumber(data?.bookings.total ?? 0)}
          hint={t("admin.dashboard.bookingsHint", {
            last30: formatNumber(data?.bookings.last_30_days ?? 0),
            pending: formatNumber(data?.bookings.pending ?? 0),
          })}
        />
        <StatCard
          label={t("admin.dashboard.revenue")}
          icon={Wallet}
          loading={isLoading}
          to="/payments"
          value={formatCurrency(data?.revenue.total ?? 0)}
          hint={t("admin.dashboard.revenueHint", {
            last30: formatCurrency(data?.revenue.last_30_days ?? 0),
            basket: formatCurrency(data?.revenue.average_basket ?? 0),
          })}
        />
        <StatCard
          label={t("admin.dashboard.clients")}
          icon={Users}
          loading={isLoading}
          to="/users"
          value={formatNumber(data?.users.total ?? 0)}
          hint={t("admin.dashboard.clientsHint", {
            active: formatNumber(data?.users.active ?? 0),
            fresh: formatNumber(data?.users.new_30_days ?? 0),
          })}
        />
        <StatCard
          label={t("admin.dashboard.activities")}
          icon={MapPin}
          loading={isLoading}
          to="/activities"
          value={formatNumber(data?.activities.total ?? 0)}
          hint={t("admin.dashboard.activitiesHint", {
            categories: formatNumber(data?.activities.categories ?? 0),
            slots: formatNumber(data?.activities.upcoming_availabilities ?? 0),
          })}
        />
      </div>

      {/* Offres de voyage + répartition du catalogue par catégorie. */}
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <h2 className="text-muted-foreground mb-2 text-sm font-semibold">
            {t("admin.dashboard.offersTitle")}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <StatCard
              label={t("admin.nav.stays")}
              icon={BedDouble}
              loading={isLoading}
              to="/stays"
              value={formatNumber(data?.activities.offres.sejours ?? 0)}
            />
            <StatCard
              label={t("admin.nav.flights")}
              icon={Plane}
              loading={isLoading}
              to="/flights"
              value={formatNumber(data?.activities.offres.vols_a_venir ?? 0)}
              hint={t("admin.dashboard.flightsHint")}
            />
            <StatCard
              label={t("admin.nav.carRentals")}
              icon={Car}
              loading={isLoading}
              to="/car-rentals"
              value={formatNumber(data?.activities.offres.voitures ?? 0)}
            />
            <StatCard
              label={t("admin.nav.transfers")}
              icon={CarTaxiFront}
              loading={isLoading}
              to="/transfers"
              value={formatNumber(data?.activities.offres.transferts ?? 0)}
            />
          </div>
        </section>

        <section>
          <h2 className="text-muted-foreground mb-2 text-sm font-semibold">
            {t("admin.dashboard.byCategory")}
          </h2>
          <div className="bg-card space-y-2.5 rounded-lg border p-4 shadow-sm">
            {isLoading
              ? Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="bg-muted h-5 animate-pulse rounded" />
                ))
              : (() => {
                  const rows = data?.activities.par_categorie ?? [];
                  const max = Math.max(1, ...rows.map((r) => r.total));
                  return rows.map((r) => (
                    <div key={r.nom} className="text-sm">
                      <div className="mb-1 flex justify-between gap-2">
                        <span>{r.nom}</span>
                        <span className="text-muted-foreground tabular-nums">{r.total}</span>
                      </div>
                      <div className="bg-muted h-1.5 overflow-hidden rounded-full">
                        <div
                          className="bg-primary h-full rounded-full"
                          style={{ width: `${(r.total / max) * 100}%` }}
                        />
                      </div>
                    </div>
                  ));
                })()}
          </div>
        </section>
      </div>

      <section className="bg-card rounded-lg border">
        <header className="border-b px-4 py-3">
          <h2 className="font-semibold">{t("admin.dashboard.latest")}</h2>
        </header>
        {isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="bg-muted h-10 animate-pulse rounded" />
            ))}
          </div>
        ) : data && data.recent_bookings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted-foreground border-b text-left text-xs">
                  <th className="px-4 py-2 font-medium">{t("admin.dashboard.colClient")}</th>
                  <th className="px-4 py-2 font-medium">{t("admin.dashboard.colActivity")}</th>
                  <th className="px-4 py-2 font-medium">{t("admin.dashboard.colDate")}</th>
                  <th className="px-4 py-2 font-medium">{t("admin.dashboard.colStatus")}</th>
                  <th className="px-4 py-2 text-right font-medium">
                    {t("admin.dashboard.colAmount")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.recent_bookings.map((booking) => (
                  <tr key={booking.id} className="border-b last:border-0">
                    <td className="px-4 py-3">
                      <div className="font-medium">{booking.client}</div>
                      <div className="text-muted-foreground text-xs">{booking.email}</div>
                    </td>
                    <td className="px-4 py-3">{booking.activity}</td>
                    <td className="px-4 py-3">{formatDateTime(booking.date_reservation)}</td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                          STATUS_STYLES[booking.statut] ?? "bg-muted text-muted-foreground",
                        )}
                      >
                        {STATUS_KEYS[booking.statut]
                          ? t(STATUS_KEYS[booking.statut]!)
                          : booking.statut}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatCurrency(booking.montant_total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-muted-foreground p-6 text-center text-sm">
            {t("admin.dashboard.empty")}
          </p>
        )}
      </section>
    </div>
  );
}
