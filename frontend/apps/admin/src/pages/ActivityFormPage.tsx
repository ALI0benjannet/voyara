import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ImagePlus, Plus, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";

import {
  useActivity,
  useActivityMutations,
  useAvailabilities,
  useAvailabilityMutations,
  useCategories,
  type ActivityPayload,
} from "@/features/catalog/hooks";

const EMPTY: ActivityPayload = {
  titre: "",
  description: "",
  titre_en: "",
  titre_ar: "",
  description_en: "",
  description_ar: "",
  prix: 0,
  duree: 60,
  localisation: "",
  latitude: null,
  longitude: null,
  category_id: 0,
};

function Field({
  label,
  children,
  className = "",
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-[13px] font-semibold">{label}</span>
      {children}
    </label>
  );
}

const inputClass =
  "w-full rounded-md border border-input bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none";

/** Création (/activities/new) et édition (/activities/:id/edit) d'une activité. */
export default function ActivityFormPage() {
  const { t, i18n } = useTranslation();
  const params = useParams<{ id: string }>();
  const navigate = useNavigate();
  const activityId = params.id ? Number(params.id) : null;
  const isEdit = activityId != null;

  const { data: categories } = useCategories();
  const { data: activity, isLoading } = useActivity(activityId);
  const { data: slots } = useAvailabilities(activityId);
  const { create, update, uploadPhoto, deletePhoto } = useActivityMutations();
  const slotMutations = useAvailabilityMutations();

  const [form, setForm] = useState<ActivityPayload>(EMPTY);
  const fileRef = useRef<HTMLInputElement | null>(null);

  // Nouveau créneau
  const [slotDate, setSlotDate] = useState("");
  const [slotHour, setSlotHour] = useState("09:00");
  const [slotSeats, setSlotSeats] = useState(8);

  useEffect(() => {
    if (activity) {
      setForm({
        titre: activity.titre,
        description: activity.description,
        // Sans ces champs, un enregistrement écraserait les traductions.
        titre_en: activity.titre_en ?? "",
        titre_ar: activity.titre_ar ?? "",
        description_en: activity.description_en ?? "",
        description_ar: activity.description_ar ?? "",
        prix: activity.prix,
        duree: activity.duree,
        localisation: activity.localisation,
        latitude: activity.latitude,
        longitude: activity.longitude,
        category_id: activity.category_id,
      });
    }
  }, [activity]);

  const set = <K extends keyof ActivityPayload>(key: K, value: ActivityPayload[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!form.category_id) {
      toast.error(t("admin.form.errNoCategory"));
      return;
    }
    // Un champ de traduction laissé vide vaut « pas de traduction » : on envoie
    // null plutôt qu'une chaîne vide, pour que le repli français s'applique.
    const payload: ActivityPayload = {
      ...form,
      titre_en: form.titre_en?.trim() || null,
      titre_ar: form.titre_ar?.trim() || null,
      description_en: form.description_en?.trim() || null,
      description_ar: form.description_ar?.trim() || null,
    };

    if (isEdit) {
      update.mutate({ id: activityId, payload });
    } else {
      create.mutate(payload, {
        onSuccess: (created) => {
          toast.success(t("admin.form.createdToast"));
          navigate(`/activities/${created.id}/edit`, { replace: true });
        },
      });
    }
  };

  const onPhotoPicked = (file?: File) => {
    if (!file || !isEdit) return;
    if (file.size > 5 * 1024 * 1024) {
      toast.error("5 Mo maximum");
      return;
    }
    uploadPhoto.mutate({ id: activityId, file });
    if (fileRef.current) fileRef.current.value = "";
  };

  const addSlot = () => {
    if (!isEdit || !slotDate) {
      toast.error(t("admin.form.errNoDate"));
      return;
    }
    slotMutations.create.mutate(
      {
        activity_id: activityId as number,
        date: slotDate,
        heure: `${slotHour}:00`,
        places_disponibles: slotSeats,
      },
      { onSuccess: () => setSlotDate("") },
    );
  };

  if (isEdit && isLoading) {
    return <div className="bg-muted h-64 animate-pulse rounded-lg" />;
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          to="/activities"
          className="text-muted-foreground hover:bg-muted hover:text-foreground rounded-md p-1.5"
          aria-label={t("admin.form.backAria")}
        >
          <ArrowLeft className="size-5" />
        </Link>
        <h1 className="font-display text-2xl font-semibold">
          {isEdit
            ? t("admin.form.editTitle", { name: activity?.titre ?? "" })
            : t("admin.form.titleNew")}
        </h1>
      </div>

      {/* ---- Informations ---- */}
      <form onSubmit={submit} className="bg-card space-y-4 rounded-lg border p-5">
        <Field label={t("admin.form.fieldTitle")}>
          <input
            required
            minLength={3}
            value={form.titre}
            onChange={(e) => set("titre", e.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label={t("admin.form.fieldDescription")}>
          <textarea
            required
            minLength={10}
            rows={4}
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
            className={inputClass}
          />
        </Field>

        {/* ---- Traductions (facultatives : repli automatique sur le français) ---- */}
        <fieldset className="border-input rounded-lg border p-4">
          <legend className="px-1 text-[13px] font-semibold">{t("admin.form.translations")}</legend>
          <p className="text-muted-foreground mb-3 text-xs">{t("admin.form.translationsHint")}</p>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={`${t("admin.form.fieldTitle")} — ${t("admin.form.tabEn")}`}>
              <input
                value={form.titre_en ?? ""}
                onChange={(e) => set("titre_en", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label={`${t("admin.form.fieldTitle")} — ${t("admin.form.tabAr")}`}>
              <input
                dir="rtl"
                value={form.titre_ar ?? ""}
                onChange={(e) => set("titre_ar", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label={`${t("admin.form.fieldDescription")} — ${t("admin.form.tabEn")}`}>
              <textarea
                rows={3}
                value={form.description_en ?? ""}
                onChange={(e) => set("description_en", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label={`${t("admin.form.fieldDescription")} — ${t("admin.form.tabAr")}`}>
              <textarea
                dir="rtl"
                rows={3}
                value={form.description_ar ?? ""}
                onChange={(e) => set("description_ar", e.target.value)}
                className={inputClass}
              />
            </Field>
          </div>
        </fieldset>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label={t("admin.form.fieldPricePer")}>
            <input
              required
              type="number"
              min={1}
              step="0.5"
              value={form.prix || ""}
              onChange={(e) => set("prix", Number(e.target.value))}
              className={inputClass}
            />
          </Field>
          <Field label={t("admin.form.fieldDuration")}>
            <input
              required
              type="number"
              min={15}
              step={15}
              value={form.duree || ""}
              onChange={(e) => set("duree", Number(e.target.value))}
              className={inputClass}
            />
          </Field>
          <Field label={t("admin.form.fieldCategory")}>
            <select
              required
              value={form.category_id || ""}
              onChange={(e) => set("category_id", Number(e.target.value))}
              className={inputClass}
            >
              <option value="" disabled>
                Choisir…
              </option>
              {(categories ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nom}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label={t("admin.form.fieldPlaceCity")}>
            <input
              required
              value={form.localisation}
              onChange={(e) => set("localisation", e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label={t("admin.form.fieldLatMap")}>
            <input
              type="number"
              step="any"
              value={form.latitude ?? ""}
              onChange={(e) =>
                set("latitude", e.target.value === "" ? null : Number(e.target.value))
              }
              className={inputClass}
            />
          </Field>
          <Field label={t("admin.form.fieldLngMap")}>
            <input
              type="number"
              step="any"
              value={form.longitude ?? ""}
              onChange={(e) =>
                set("longitude", e.target.value === "" ? null : Number(e.target.value))
              }
              className={inputClass}
            />
          </Field>
        </div>
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={create.isPending || update.isPending}
            className="bg-primary inline-flex items-center gap-2 rounded-md px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            <Save className="size-4" />
            {isEdit ? t("admin.common.save") : t("admin.form.submitCreate")}
          </button>
        </div>
      </form>

      {/* ---- Photo (édition uniquement) ---- */}
      {isEdit && (
        <section className="bg-card rounded-lg border p-5">
          <h2 className="mb-3 font-semibold">{t("admin.form.photoSection")}</h2>
          <div className="flex items-center gap-4">
            <div className="bg-muted h-24 w-36 shrink-0 overflow-hidden rounded-md border">
              {activity?.photos ? (
                <img src={activity.photos} alt="" className="size-full object-cover" />
              ) : (
                <div className="text-muted-foreground flex size-full items-center justify-center text-xs">
                  {t("admin.form.photoNone")}
                </div>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={uploadPhoto.isPending}
                className="border-input hover:border-primary hover:text-primary inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-semibold disabled:opacity-50"
              >
                <ImagePlus className="size-4" />
                {uploadPhoto.isPending
                  ? t("admin.form.photoUploading")
                  : activity?.photos
                    ? t("admin.form.photoReplace")
                    : t("admin.form.photoAdd")}
              </button>
              {activity?.photos && (
                <button
                  type="button"
                  onClick={() => deletePhoto.mutate(activityId)}
                  className="text-destructive hover:bg-destructive/10 inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold"
                >
                  <Trash2 className="size-4" />
                  {t("admin.common.delete")}
                </button>
              )}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              onChange={(e) => onPhotoPicked(e.target.files?.[0])}
            />
          </div>
          <p className="text-muted-foreground mt-2 text-xs">{t("admin.form.photoHint")}</p>
        </section>
      )}

      {/* ---- Créneaux (édition uniquement) ---- */}
      {isEdit && (
        <section className="bg-card rounded-lg border p-5">
          <h2 className="mb-3 font-semibold">Créneaux de disponibilité</h2>

          <div className="mb-4 flex flex-wrap items-end gap-2">
            <Field label={t("admin.form.slotDate")}>
              <input
                type="date"
                value={slotDate}
                onChange={(e) => setSlotDate(e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label={t("admin.form.slotTime")}>
              <input
                type="time"
                value={slotHour}
                onChange={(e) => setSlotHour(e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label={t("admin.form.slotSeats")}>
              <input
                type="number"
                min={1}
                max={100}
                value={slotSeats}
                onChange={(e) => setSlotSeats(Number(e.target.value))}
                className={`${inputClass} w-24`}
              />
            </Field>
            <button
              type="button"
              onClick={addSlot}
              disabled={slotMutations.create.isPending}
              className="bg-primary inline-flex h-[38px] items-center gap-1.5 rounded-md px-4 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
            >
              <Plus className="size-4" />
              {t("admin.categories.add")}
            </button>
          </div>

          {(slots ?? []).length === 0 ? (
            <p className="text-muted-foreground text-sm">{t("admin.form.slotsEmpty")}</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted-foreground border-b text-left text-xs">
                  <th className="py-2 font-medium">{t("admin.form.slotDate")}</th>
                  <th className="py-2 font-medium">{t("admin.form.slotTime")}</th>
                  <th className="py-2 font-medium">{t("admin.form.slotSeatsLeft")}</th>
                  <th className="py-2 text-right font-medium">{t("admin.form.slotAction")}</th>
                </tr>
              </thead>
              <tbody>
                {(slots ?? []).map((slot) => (
                  <tr key={slot.id} className="border-b last:border-0">
                    <td className="py-2">
                      {new Date(`${slot.date}T12:00:00`).toLocaleDateString(i18n.language, {
                        weekday: "short",
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </td>
                    <td className="py-2">{slot.heure.slice(0, 5)}</td>
                    <td className="py-2">
                      <input
                        type="number"
                        min={0}
                        max={100}
                        defaultValue={slot.places_disponibles}
                        onBlur={(e) => {
                          const v = Number(e.target.value);
                          if (v !== slot.places_disponibles) {
                            slotMutations.update.mutate({
                              id: slot.id,
                              payload: { places_disponibles: v },
                            });
                          }
                        }}
                        className="border-input bg-card focus:border-primary w-20 rounded-md border px-2 py-1 text-sm focus:outline-none"
                      />
                    </td>
                    <td className="py-2 text-right">
                      <button
                        type="button"
                        onClick={() => {
                          if (window.confirm(t("admin.form.slotDeleteConfirm"))) {
                            slotMutations.remove.mutate(slot.id);
                          }
                        }}
                        className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive rounded-md p-1.5"
                        aria-label={t("admin.form.slotDeleteAria")}
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
