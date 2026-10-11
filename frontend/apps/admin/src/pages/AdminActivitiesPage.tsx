import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { DataTable, type Column } from "@voyara/ui/components/admin/DataTable";

import { useAdminActivities } from "@/features/admin/hook/use-admin";
import type { AdminActivityRow } from "@/features/admin/types/admin.types";
import { useActivityMutations } from "@/features/catalog/hooks";
import { formatCurrency } from "@voyara/ui/lib/format";

export default function AdminActivitiesPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useAdminActivities({ page: 1, size: 50 });
  const { remove } = useActivityMutations();

  const confirmDelete = (row: AdminActivityRow) => {
    if (row.bookings_count > 0) {
      window.alert(
        `« ${row.titre} » a ${row.bookings_count} réservation(s) — suppression impossible.`,
      );
      return;
    }
    if (window.confirm(t("admin.activities.deleteConfirmNamed", { name: row.titre }))) {
      remove.mutate(row.id);
    }
  };

  const columns: Column<AdminActivityRow>[] = [
    { key: "titre", header: t("admin.activities.colTitle"), render: (a) => a.titre },
    {
      key: "category",
      header: t("admin.activities.colCategory"),
      render: (a) => a.category ?? "—",
    },
    { key: "localisation", header: t("admin.activities.colPlace"), render: (a) => a.localisation },
    {
      key: "duree",
      header: t("admin.activities.colDuration"),
      render: (a) => t("admin.activities.minutes", { count: a.duree }),
    },
    { key: "bookings", header: t("admin.activities.colBookings"), render: (a) => a.bookings_count },
    {
      key: "prix",
      header: t("admin.activities.colPrice"),
      align: "end",
      render: (a) => formatCurrency(a.prix),
    },
    {
      key: "actions",
      header: t("admin.common.actions"),
      align: "end",
      render: (a) => (
        <span className="inline-flex gap-1">
          <Link
            to={`/activities/${a.id}/edit`}
            className="text-muted-foreground hover:bg-muted hover:text-foreground rounded-md p-1.5"
            aria-label={t("admin.activities.editAria", { name: a.titre })}
          >
            <Pencil className="size-4" />
          </Link>
          <button
            type="button"
            onClick={() => confirmDelete(a)}
            className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive rounded-md p-1.5"
            aria-label={t("admin.activities.deleteAria", { name: a.titre })}
          >
            <Trash2 className="size-4" />
          </button>
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-2xl font-semibold">{t("admin.activities.title")}</h1>
        <Link
          to="/activities/new"
          className="bg-primary inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
        >
          <Plus className="size-4" />
          {t("admin.activities.new")}
        </Link>
      </div>

      <div className="bg-card rounded-lg border">
        <DataTable
          columns={columns}
          rows={data?.items}
          isLoading={isLoading}
          getRowId={(a) => a.id}
          emptyLabel={t("admin.activities.empty")}
        />
      </div>
    </div>
  );
}
