import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Check, X } from "lucide-react";

import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";

import type { Activity } from "@/features/catalog/api";

type Decision = "publiee" | "refusee";

type PendingActivity = Activity & { prestataire_id: number | null };

const moderationKeys = {
  activities: ["moderation", "activities"] as const,
};

/** Activités proposées depuis l'espace prestataire : l'admin publie ou refuse.
 *  Une activité publiée n'a pas encore de créneaux : les ajouter depuis « Activités ». */
export default function ModerationPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const activities = useQuery({
    queryKey: moderationKeys.activities,
    queryFn: () => api.get<PendingActivity[]>(endpoints.moderation.activities).then((r) => r.data),
  });

  const moderateActivity = useMutation({
    mutationFn: ({ id, statut }: { id: number; statut: Decision }) =>
      api.patch(endpoints.moderation.activity(id), { statut }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: moderationKeys.activities }),
  });

  const actions = (onDecide: (statut: Decision) => void) => (
    <div className="flex shrink-0 gap-2">
      <button
        type="button"
        onClick={() => onDecide("publiee")}
        className="bg-primary inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90"
      >
        <Check className="size-4" />
        {t("admin.moderation.approve")}
      </button>
      <button
        type="button"
        onClick={() => onDecide("refusee")}
        className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-semibold text-red-600 hover:bg-red-50"
      >
        <X className="size-4" />
        {t("admin.moderation.reject")}
      </button>
    </div>
  );

  const items = activities.data ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold">{t("admin.moderation.title")}</h1>
        <p className="text-muted-foreground text-sm">{t("admin.moderation.subtitle")}</p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">
          {t("admin.moderation.activities")}{" "}
          <span className="text-muted-foreground text-sm">({items.length})</span>
        </h2>
        <div className="bg-card rounded-lg border">
          {activities.isLoading ? (
            <div className="bg-muted m-4 h-16 animate-pulse rounded" />
          ) : items.length === 0 ? (
            <p className="text-muted-foreground p-6 text-center text-sm">
              {t("admin.moderation.empty")}
            </p>
          ) : (
            <ul className="divide-border divide-y">
              {items.map((a) => (
                <li key={a.id} className="flex items-start gap-4 px-4 py-3">
                  {a.photos && (
                    <img src={a.photos} alt="" className="size-16 shrink-0 rounded object-cover" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold">{a.titre}</div>
                    <div className="text-muted-foreground text-sm">
                      {a.localisation} · {a.prix} DT · {a.duree} min · {a.category?.nom}
                    </div>
                    <p className="text-foreground/80 mt-1 line-clamp-2 text-sm">{a.description}</p>
                  </div>
                  {actions((statut) => moderateActivity.mutate({ id: a.id, statut }))}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
