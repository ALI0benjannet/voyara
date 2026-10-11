import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { DataTable, type Column } from "@voyara/ui/components/admin/DataTable";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@voyara/ui/components/ui/sheet";
import { formatCurrency, formatDateTime } from "@voyara/ui/lib/format";
import { cn } from "@voyara/ui/lib/utils";

import type { TravelItem, TravelPayload } from "@/features/travel/api";
import {
  TRAVEL_CONFIG,
  type FieldDef,
  type TravelConfig,
  type TravelResource,
} from "@/features/travel/config";
import { useTravelItems, useTravelMutations } from "@/features/travel/hooks";

type FormValues = Record<string, string | boolean>;

const INPUT_CLASS =
  "border-input bg-card focus:border-primary w-full rounded-md border px-3 py-2 text-sm focus:outline-none";

/** Valeurs du formulaire : les champs texte sont des chaînes, même les nombres
 *  (un champ vidé doit rester vide, pas devenir 0). */
function toFormValues(fields: FieldDef[], item: TravelItem | null): FormValues {
  const values: FormValues = {};
  for (const field of fields) {
    const raw = item ? item[field.name] : field.initial;
    if (field.type === "checkbox") {
      values[field.name] = raw === undefined ? false : Boolean(raw);
    } else if (raw === null || raw === undefined) {
      values[field.name] = "";
    } else if (field.type === "datetime") {
      // L'API renvoie « 2026-11-01T08:00:00 » ; datetime-local attend « 2026-11-01T08:00 ».
      values[field.name] = String(raw).slice(0, 16);
    } else {
      values[field.name] = String(raw);
    }
  }
  return values;
}

function toPayload(fields: FieldDef[], values: FormValues): TravelPayload {
  const payload: TravelPayload = {};
  for (const field of fields) {
    const value = values[field.name];
    if (field.type === "checkbox") {
      payload[field.name] = Boolean(value);
      continue;
    }
    const text = String(value).trim();
    if (text === "") payload[field.name] = null;
    else if (field.type === "number") payload[field.name] = Number(text);
    else payload[field.name] = text;
  }
  return payload;
}

function FieldInput({
  field,
  value,
  onChange,
  resource,
}: {
  field: FieldDef;
  value: string | boolean;
  onChange: (value: string | boolean) => void;
  resource: TravelResource;
}) {
  const { t } = useTranslation();
  const label = t(`admin.travel.${resource}.fields.${field.name}`);
  const id = `travel-${field.name}`;

  if (field.type === "checkbox") {
    return (
      <label htmlFor={id} className="col-span-2 flex items-center gap-2 text-sm font-medium">
        <input
          id={id}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          className="accent-primary size-4"
        />
        {label}
      </label>
    );
  }

  return (
    <div className={cn("space-y-1", field.wide && "col-span-2")}>
      <label htmlFor={id} className="text-sm font-medium">
        {label}
        {field.required && <span className="text-destructive"> *</span>}
      </label>
      {field.type === "textarea" ? (
        <textarea
          id={id}
          value={String(value)}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
          rows={3}
          className={INPUT_CLASS}
        />
      ) : field.type === "select" ? (
        <select
          id={id}
          value={String(value)}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
          className={INPUT_CLASS}
        >
          {field.options?.map((option) => (
            <option key={option} value={option}>
              {t(`admin.travel.options.${option}`)}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={id}
          type={
            field.type === "number"
              ? "number"
              : field.type === "datetime"
                ? "datetime-local"
                : "text"
          }
          value={String(value)}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
          min={field.min}
          max={field.max}
          step={field.step}
          className={INPUT_CLASS}
        />
      )}
    </div>
  );
}

function formatCell(
  column: TravelConfig["columns"][number],
  row: TravelItem,
  t: (key: string) => string,
) {
  const value = row[column.field];
  if (value === null || value === undefined || value === "") return "—";
  switch (column.format) {
    case "currency":
      return formatCurrency(Number(value));
    case "datetime":
      return formatDateTime(String(value));
    case "option":
      return t(`admin.travel.options.${value}`);
    case "bool":
      return value ? t("admin.common.yes") : t("admin.common.no");
    default:
      return String(value);
  }
}

/** Page d'administration commune aux séjours, vols, voitures et transferts :
 *  tableau + panneau latéral de création / modification, pilotés par la config. */
export default function TravelOffersPage({ resource }: { resource: TravelResource }) {
  const { t } = useTranslation();
  const config = TRAVEL_CONFIG[resource];
  const { data, isLoading } = useTravelItems(config.path);
  const { create, update, remove } = useTravelMutations(config.path);

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<TravelItem | null>(null);
  const [values, setValues] = useState<FormValues>({});

  const openForm = (item: TravelItem | null) => {
    setEditing(item);
    setValues(toFormValues(config.fields, item));
    setOpen(true);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const payload = toPayload(config.fields, values);
    const done = { onSuccess: () => setOpen(false) };
    if (editing) update.mutate({ id: editing.id, payload }, done);
    else create.mutate(payload, done);
  };

  const confirmDelete = (row: TravelItem) => {
    if (window.confirm(t("admin.travel.deleteConfirm", { name: config.label(row) }))) {
      remove.mutate(row.id);
    }
  };

  const columns: Column<TravelItem>[] = [
    ...config.columns.map((column) => ({
      key: column.field,
      header: t(`admin.travel.${resource}.fields.${column.field}`),
      align: column.format === "currency" ? ("end" as const) : undefined,
      render: (row: TravelItem) => formatCell(column, row, t),
    })),
    {
      key: "actions",
      header: t("admin.common.actions"),
      align: "end",
      render: (row) => (
        <span className="inline-flex gap-1">
          <button
            type="button"
            onClick={() => openForm(row)}
            className="text-muted-foreground hover:bg-muted hover:text-foreground rounded-md p-1.5"
            aria-label={`${t("admin.common.edit")} ${config.label(row)}`}
          >
            <Pencil className="size-4" />
          </button>
          <button
            type="button"
            onClick={() => confirmDelete(row)}
            className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive rounded-md p-1.5"
            aria-label={`${t("admin.common.delete")} ${config.label(row)}`}
          >
            <Trash2 className="size-4" />
          </button>
        </span>
      ),
    },
  ];

  const pending = create.isPending || update.isPending;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-2xl font-semibold">
          {t(`admin.travel.${resource}.title`)}
        </h1>
        <button
          type="button"
          onClick={() => openForm(null)}
          className="bg-primary inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
        >
          <Plus className="size-4" />
          {t(`admin.travel.${resource}.new`)}
        </button>
      </div>

      <div className="bg-card rounded-lg border">
        <DataTable
          columns={columns}
          rows={data}
          isLoading={isLoading}
          getRowId={(row) => row.id}
          emptyLabel={t(`admin.travel.${resource}.empty`)}
        />
      </div>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>
              {editing ? t("admin.travel.editTitle") : t(`admin.travel.${resource}.new`)}
            </SheetTitle>
            <SheetDescription>{t("admin.travel.requiredHint")}</SheetDescription>
          </SheetHeader>

          <form onSubmit={submit} className="grid grid-cols-2 gap-4">
            {config.fields.map((field) => (
              <FieldInput
                key={field.name}
                field={field}
                resource={resource}
                value={values[field.name] ?? ""}
                onChange={(value) => setValues((prev) => ({ ...prev, [field.name]: value }))}
              />
            ))}

            <div className="col-span-2 flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="hover:bg-muted rounded-md border px-4 py-2 text-sm font-medium"
              >
                {t("admin.common.cancel")}
              </button>
              <button
                type="submit"
                disabled={pending}
                className="bg-primary rounded-md px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
              >
                {t("admin.common.save")}
              </button>
            </div>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  );
}
