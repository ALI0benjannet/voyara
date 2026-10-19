import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ImageOff, Pencil, Plus, Trash2 } from "lucide-react";

import { DataTable, type Column } from "@voyara/ui/components/admin/DataTable";
import { formatCurrency } from "@voyara/ui/lib/format";
import { cn } from "@voyara/ui/lib/utils";

import { ListToolbar, Pagination, SELECT_CLASS, useDebouncedValue } from "@/components/ListToolbar";
import type { ActivityListParams } from "@/features/admin/api/admin.api";
import { useAdminActivities } from "@/features/admin/hook/use-admin";
import type { AdminActivityRow } from "@/features/admin/types/admin.types";
import { useActivityMutations, useCategories } from "@/features/catalog/hooks";

const PAGE_SIZE = 20;

const STATUT_STYLES: Record<AdminActivityRow["statut"], string> = {
  publiee: "bg-emerald-100 text-emerald-700",
  en_attente: "bg-amber-100 text-amber-700",
  refusee: "bg-rose-100 text-rose-700",
};

/** Liste des activités : recherche (titre, ville, catégorie) et filtres
 *  appliqués côté catalog, pour que la pagination reste exacte. */
export default function AdminActivitiesPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [statut, setStatut] = useState("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search.trim());

  const params: ActivityListParams = {
    page,
    size: PAGE_SIZE,
    search: debouncedSearch || undefined,
    category_id: categoryId ? Number(categoryId) : undefined,
    statut: (statut || undefined) as ActivityListParams["statut"],
  };
  const { data, isLoading, isFetching } = useAdminActivities(params);
  const { data: categories } = useCategories();
  const { remove } = useActivityMutations();

  // Tout changement de filtre ramène à la première page.
  const filter =
    <T,>(setter: (v: T) => void) =>
    (value: T) => {
      setter(value);
      setPage(1);
    };

  const confirmDelete = (row: AdminActivityRow) => {
    if (row.bookings_count > 0) {
      window.alert(
        t("admin.activities.hasBookings", { name: row.titre, count: row.bookings_count }),
      );
      return;
    }
    if (window.confirm(t("admin.activities.deleteConfirmNamed", { name: row.titre }))) {
      remove.mutate(row.id);
    }
  };

  const columns: Column<AdminActivityRow>[] = [
    {
      key: "photo",
      header: "",
      render: (a) =>
        a.photos ? (
          <img src={a.photos} alt="" className="h-10 w-14 rounded object-cover" loading="lazy" />
        ) : (
          <span className="bg-muted text-muted-foreground flex h-10 w-14 items-center justify-center rounded">
            <ImageOff className="size-4" />
          </span>
        ),
    },
    {
      key: "titre",
      header: t("admin.activities.colTitle"),
      render: (a) => <span className="font-medium">{a.titre}</span>,
    },
    {
      key: "category",
      header: t("admin.activities.colCategory"),
      render: (a) => a.category ?? "—",
    },
    { key: "localisation", header: t("admin.activities.colPlace"), render: (a) => a.localisation },
    {
      key: "statut",
      header: t("admin.activities.colStatus"),
      render: (a) => (
        <span
          className={cn("rounded-full px-2 py-0.5 text-xs font-medium", STATUT_STYLES[a.statut])}
        >
          {t(`admin.activities.statut.${a.statut}`)}
        </span>
      ),
    },
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

  const filtered = Boolean(debouncedSearch || categoryId || statut);

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

      <ListToolbar
        search={search}
        onSearch={filter(setSearch)}
        placeholder={t("admin.activities.searchPlaceholder")}
        count={data?.total}
      >
        <select
          value={categoryId}
          onChange={(e) => filter(setCategoryId)(e.target.value)}
          className={SELECT_CLASS}
          aria-label={t("admin.activities.colCategory")}
        >
          <option value="">{t("admin.list.allCategories")}</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nom}
            </option>
          ))}
        </select>
        <select
          value={statut}
          onChange={(e) => filter(setStatut)(e.target.value)}
          className={SELECT_CLASS}
          aria-label={t("admin.activities.colStatus")}
        >
          <option value="">{t("admin.list.allStatuses")}</option>
          {(["publiee", "en_attente", "refusee"] as const).map((s) => (
            <option key={s} value={s}>
              {t(`admin.activities.statut.${s}`)}
            </option>
          ))}
        </select>
      </ListToolbar>

      <div
        className={cn("bg-card rounded-lg border transition-opacity", isFetching && "opacity-70")}
      >
        <DataTable
          columns={columns}
          rows={data?.items}
          isLoading={isLoading}
          getRowId={(a) => a.id}
          emptyLabel={filtered ? t("admin.list.noMatch") : t("admin.activities.empty")}
        />
      </div>

      <Pagination page={data?.page ?? page} pages={data?.pages ?? 1} onPage={setPage} />
    </div>
  );
}
