import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { DataTable, type Column } from "@voyara/ui/components/admin/DataTable";
import { useAdminUsers } from "@/features/admin/hook/use-admin";
import type { AdminUserRow } from "@/features/admin/types/admin.types";
import { formatDateTime } from "@voyara/ui/lib/format";

export default function UsersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const { data, isLoading } = useAdminUsers({ page, size: 20, search: search || undefined });
  const { t } = useTranslation();

  const columns = useMemo<Column<AdminUserRow>[]>(
    () => [
      { key: "nom", header: t("admin.users.colName"), render: (u) => `${u.prenom} ${u.nom}` },
      { key: "email", header: t("admin.users.colEmail"), render: (u) => u.email },
      { key: "role", header: t("admin.users.colRole"), render: (u) => u.role },
      {
        key: "statut",
        header: t("admin.users.colStatus"),
        render: (u) =>
          !u.is_active
            ? t("admin.users.disabled")
            : u.is_verified
              ? t("admin.users.verified")
              : t("admin.users.unverified"),
      },
      {
        key: "date",
        header: t("admin.users.colSignup"),
        render: (u) => formatDateTime(u.date_inscription),
      },
    ],
    [t],
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t("admin.users.title")}</h1>

      <input
        value={search}
        onChange={(event) => {
          setSearch(event.target.value);
          setPage(1);
        }}
        placeholder={t("admin.users.search")}
        className="w-full max-w-sm rounded-md border px-3 py-2 text-sm"
      />

      <div className="bg-card rounded-lg border">
        <DataTable
          columns={columns}
          rows={data?.items}
          isLoading={isLoading}
          getRowId={(u) => u.id}
          emptyLabel={t("admin.users.empty")}
        />
      </div>

      <div className="text-muted-foreground flex items-center justify-between text-sm">
        {t("admin.users.count", { count: data?.total ?? 0 })}
        <div className="flex gap-2">
          <button
            className="rounded border px-3 py-1 disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            {t("admin.common.prev")}
          </button>
          <button
            className="rounded border px-3 py-1 disabled:opacity-40"
            disabled={!data || page >= data.pages}
            onClick={() => setPage((p) => p + 1)}
          >
            {t("admin.common.next")}
          </button>
        </div>
      </div>
    </div>
  );
}
