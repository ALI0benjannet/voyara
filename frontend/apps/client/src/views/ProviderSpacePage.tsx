import { useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { FerrisWheel, ListChecks, Trash2 } from "lucide-react";

import { toApiError } from "@voyara/api/errors";
import { cn } from "@voyara/ui/lib/utils";

import { useCategories } from "@/features/catalog/hooks";
import { categoryName } from "@/features/catalog/i18n-content";
import { formatPrice } from "@/features/catalog/format";
import {
  useCreateActivity,
  useDeleteActivity,
  useMyActivities,
  type Statut,
} from "@/features/prestataire/hooks";

type Tab = "activity" | "mine";

const FIELD_CLASS =
  "border-border bg-card w-full rounded-xl border px-4 py-3 text-sm transition focus-visible:ring-ring focus:outline-none focus-visible:ring-2";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-foreground/85 block text-sm font-medium">{label}</span>
      {children}
    </label>
  );
}

function StatutBadge({ statut }: { statut: Statut }) {
  const { t } = useTranslation();
  const tone = {
    en_attente: "bg-amber-100 text-amber-800",
    publiee: "bg-emerald-100 text-emerald-800",
    refusee: "bg-red-100 text-red-700",
  }[statut];
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", tone)}>
      {t(`provider.statut.${statut}`)}
    </span>
  );
}

/** Champ fichier traduit : le texte natif (« Aucun fichier choisi »…) suit la
 *  langue du navigateur, pas celle du site — l'input est donc masqué derrière
 *  un bouton et le nom du fichier, libellés via i18n. */
function PhotoInput({ name }: { name: string }) {
  const { t } = useTranslation();
  const [fileName, setFileName] = useState<string | null>(null);
  return (
    <span
      className={cn(
        FIELD_CLASS,
        "focus-within:ring-ring flex items-center gap-3 py-2 focus-within:ring-2",
      )}
    >
      <input
        name={name}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={(event) => setFileName(event.currentTarget.files?.[0]?.name ?? null)}
      />
      <span className="bg-secondary text-foreground hover:bg-secondary/80 shrink-0 cursor-pointer rounded-lg px-3 py-1.5 font-medium transition-colors">
        {t("provider.fields.chooseFile")}
      </span>
      <span className="text-muted-foreground truncate">
        {fileName ?? t("provider.fields.noFile")}
      </span>
    </span>
  );
}

function SubmitButton({ pending, children }: { pending: boolean; children: ReactNode }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="bg-primary text-primary-foreground hover:bg-primary-hover rounded-lg px-6 py-3 text-sm font-semibold transition-colors disabled:opacity-60"
    >
      {children}
    </button>
  );
}

function errorMessage(t: (key: string) => string, error: unknown) {
  const { message } = toApiError(error);
  return message.startsWith("errors.") ? t(message) : message;
}

function ActivityForm({ onDone }: { onDone: () => void }) {
  const { t, i18n } = useTranslation();
  const { data: categories } = useCategories();
  const createActivity = useCreateActivity();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const photo = form.get("photo");
    createActivity.mutate(
      {
        payload: {
          titre: String(form.get("titre")),
          description: String(form.get("description")),
          prix: Number(form.get("prix")),
          duree: Number(form.get("duree")),
          localisation: String(form.get("localisation")),
          category_id: Number(form.get("category_id")),
        },
        photo: photo instanceof File && photo.size > 0 ? photo : null,
      },
      {
        onSuccess: () => {
          toast.success(t("provider.submitted"));
          onDone();
        },
        onError: (error) => toast.error(errorMessage(t, error)),
      },
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <Field label={t("provider.fields.title")}>
        <input name="titre" required minLength={3} maxLength={200} className={FIELD_CLASS} />
      </Field>
      <Field label={t("provider.fields.description")}>
        <textarea name="description" required minLength={10} rows={5} className={FIELD_CLASS} />
      </Field>
      <div className="grid gap-5 sm:grid-cols-3">
        <Field label={t("provider.fields.price")}>
          <input name="prix" type="number" required min={1} step="0.5" className={FIELD_CLASS} />
        </Field>
        <Field label={t("provider.fields.duration")}>
          <input name="duree" type="number" required min={1} className={FIELD_CLASS} />
        </Field>
        <Field label={t("provider.fields.category")}>
          <select name="category_id" required className={FIELD_CLASS}>
            {(categories ?? []).map((category) => (
              <option key={category.id} value={category.id}>
                {categoryName(category, i18n.language)}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field label={t("provider.fields.location")}>
        <input
          name="localisation"
          required
          minLength={2}
          maxLength={255}
          placeholder={t("provider.fields.locationPlaceholder")}
          className={FIELD_CLASS}
        />
      </Field>
      <Field label={t("provider.fields.photo")}>
        <PhotoInput name="photo" />
      </Field>
      <div className="flex justify-end">
        <SubmitButton pending={createActivity.isPending}>{t("provider.submit")}</SubmitButton>
      </div>
    </form>
  );
}

function MyPublications() {
  const { t } = useTranslation();
  const { data: activities, isLoading } = useMyActivities();
  const deleteActivity = useDeleteActivity();

  const onDeleteError = (error: unknown) => toast.error(errorMessage(t, error));

  if (isLoading) {
    return <div className="bg-muted h-40 animate-pulse rounded-2xl" />;
  }

  const rows = (activities ?? []).map((a) => ({
    key: `a-${a.id}`,
    kind: t("provider.kind.activity"),
    title: a.titre,
    detail: formatPrice(a.prix),
    statut: a.statut,
    // Une activité publiée peut avoir des réservations : suppression via l'admin.
    onDelete:
      a.statut === "publiee"
        ? null
        : () => deleteActivity.mutate(a.id, { onError: onDeleteError }),
  }));

  if (rows.length === 0) {
    return (
      <p className="border-input text-muted-foreground rounded-2xl border border-dashed px-5 py-12 text-center">
        {t("provider.empty")}
      </p>
    );
  }

  return (
    <ul className="divide-border border-border bg-card divide-y rounded-2xl border">
      {rows.map((row) => (
        <li key={row.key} className="flex items-center gap-4 px-5 py-4">
          <div className="min-w-0 flex-1">
            <div className="text-muted-foreground text-xs font-medium uppercase">{row.kind}</div>
            <div className="truncate font-semibold">{row.title}</div>
            <div className="text-muted-foreground truncate text-sm">{row.detail}</div>
          </div>
          <StatutBadge statut={row.statut} />
          {row.onDelete && (
            <button
              type="button"
              onClick={row.onDelete}
              title={t("provider.delete")}
              className="text-muted-foreground rounded-lg p-2 transition-colors hover:bg-red-50 hover:text-red-600"
            >
              <Trash2 className="size-4" />
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

export default function ProviderSpacePage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("activity");

  const tabs = [
    { id: "activity" as const, label: t("provider.tabs.activity"), Icon: FerrisWheel },
    { id: "mine" as const, label: t("provider.tabs.mine"), Icon: ListChecks },
  ];

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-8">
      <h1 className="font-display mb-2 text-4xl">{t("provider.title")}</h1>
      <p className="text-muted-foreground mb-8">{t("provider.subtitle")}</p>

      <div className="border-border mb-6 flex gap-1 overflow-x-auto border-b">
        {tabs.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={cn(
              "flex shrink-0 items-center gap-2 border-b-2 px-3 pt-1 pb-2.5 text-[15px] font-semibold transition-colors",
              tab === id
                ? "border-primary text-primary"
                : "text-foreground/70 hover:text-foreground border-transparent",
            )}
          >
            <Icon className="size-[18px]" strokeWidth={1.7} />
            {label}
          </button>
        ))}
      </div>

      {tab === "activity" && <ActivityForm onDone={() => setTab("mine")} />}
      {tab === "mine" && <MyPublications />}

      {tab !== "mine" && (
        <p className="text-muted-foreground mt-6 text-sm">{t("provider.moderationNote")}</p>
      )}
    </main>
  );
}
