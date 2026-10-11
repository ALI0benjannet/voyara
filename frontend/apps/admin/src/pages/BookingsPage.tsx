import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { DataTable, type Column } from "@voyara/ui/components/admin/DataTable";
import { useAdminBookings } from "@/features/admin/hook/use-admin";
import type { AdminBookingRow } from "@/features/admin/types/admin.types";
import { formatCurrency, formatDateTime } from "@voyara/ui/lib/format";

export default function BookingsPage() {
  const { data, isLoading } = useAdminBookings({ page: 1, size: 50 });
  const { t } = useTranslation();

  // Recalculées à chaque changement de langue (les en-têtes sont traduits).
  const columns = useMemo<Column<AdminBookingRow>[]>(
    () => [
      { key: "id", header: "#", render: (b) => b.id },
      { key: "client", header: t("admin.bookings.colClient"), render: (b) => b.client },
      { key: "activity", header: t("admin.bookings.colActivity"), render: (b) => b.activity },
      {
        key: "date",
        header: t("admin.bookings.colDate"),
        render: (b) => formatDateTime(b.date_reservation),
      },
      { key: "statut", header: t("admin.bookings.colStatus"), render: (b) => b.statut },
      {
        key: "montant",
        header: t("admin.bookings.colAmount"),
        align: "end",
        render: (b) => formatCurrency(b.montant_total),
      },
    ],
    [t],
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t("admin.bookings.title")}</h1>

      <div className="bg-card rounded-lg border">
        <DataTable
          columns={columns}
          rows={data?.items}
          isLoading={isLoading}
          getRowId={(b) => b.id}
          emptyLabel={t("admin.bookings.empty")}
        />
      </div>
    </div>
  );
}
