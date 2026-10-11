import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { DataTable, type Column } from "@voyara/ui/components/admin/DataTable";
import { useAdminPayments } from "@/features/admin/hook/use-admin";
import type { AdminPaymentRow } from "@/features/admin/types/admin.types";
import { formatCurrency, formatDateTime } from "@voyara/ui/lib/format";

export default function PaymentsPage() {
  const { data, isLoading } = useAdminPayments({ page: 1, size: 50 });
  const { t } = useTranslation();

  const columns = useMemo<Column<AdminPaymentRow>[]>(
    () => [
      { key: "id", header: "#", render: (p) => p.id },
      { key: "client", header: t("admin.payments.colClient"), render: (p) => p.client },
      { key: "booking", header: t("admin.payments.colBooking"), render: (p) => `#${p.booking_id}` },
      { key: "methode", header: t("admin.payments.colMethod"), render: (p) => p.methode },
      { key: "statut", header: t("admin.payments.colStatus"), render: (p) => p.statut },
      {
        key: "date",
        header: t("admin.payments.colDate"),
        render: (p) => formatDateTime(p.date_paiement),
      },
      {
        key: "montant",
        header: t("admin.payments.colAmount"),
        align: "end",
        render: (p) => formatCurrency(p.montant),
      },
    ],
    [t],
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t("admin.payments.title")}</h1>

      <div className="bg-card rounded-lg border">
        <DataTable
          columns={columns}
          rows={data?.items}
          isLoading={isLoading}
          getRowId={(p) => p.id}
          emptyLabel={t("admin.payments.empty")}
        />
      </div>
    </div>
  );
}
