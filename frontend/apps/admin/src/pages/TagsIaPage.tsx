import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Check, ImageOff, Info, Pencil, Sparkles, Undo2 } from "lucide-react";

import { cn } from "@voyara/ui/lib/utils";

import { ListToolbar, Pagination, SELECT_CLASS, useDebouncedValue } from "@/components/ListToolbar";
import { useCategories } from "@/features/catalog/hooks";
import {
  CHAMPS,
  MOMENTS,
  NIVEAUX,
  PUBLICS,
  THEMES,
  differe,
  type ActiviteTags,
  type ChampTag,
  type TagsIA,
  type TagsParams,
} from "@/features/tags-ia/api";
import { useSaveTags, useTagsList, useTagsStats } from "@/features/tags-ia/hooks";

const PAGE_SIZE = 10;

/** Validation humaine des tags IA (étape 2 du moteur IA) : l'admin relit la
 *  proposition automatique, corrige et valide. Le moteur IA n'utilise que des
 *  tags validés. */
export default function TagsIaPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [etat, setEtat] = useState<"" | "todo" | "done">("todo");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search.trim());

  const params: TagsParams = {
    page,
    size: PAGE_SIZE,
    search: debouncedSearch || undefined,
    category_id: categoryId ? Number(categoryId) : undefined,
    tags_valides: etat === "" ? undefined : etat === "done",
  };
  const { data, isLoading, isFetching } = useTagsList(params);
  const { data: categories } = useCategories();

  const filter =
    <T,>(setter: (v: T) => void) =>
    (value: T) => {
      setter(value);
      setPage(1);
    };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-display flex items-center gap-2 text-2xl font-semibold">
          <Sparkles className="text-primary size-5" />
          {t("admin.tagsIa.title")}
        </h1>
        <p className="text-muted-foreground mt-1 max-w-3xl text-sm">{t("admin.tagsIa.subtitle")}</p>
      </div>

      <Avancement />

      <ListToolbar
        search={search}
        onSearch={filter(setSearch)}
        placeholder={t("admin.tagsIa.searchPlaceholder")}
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
          value={etat}
          onChange={(e) => filter(setEtat)(e.target.value as typeof etat)}
          className={SELECT_CLASS}
          aria-label={t("admin.activities.colStatus")}
        >
          <option value="todo">{t("admin.tagsIa.filterTodo")}</option>
          <option value="done">{t("admin.tagsIa.filterDone")}</option>
          <option value="">{t("admin.tagsIa.filterAll")}</option>
        </select>
      </ListToolbar>

      <div className={cn("space-y-3 transition-opacity", isFetching && "opacity-70")}>
        {isLoading && <p className="text-muted-foreground text-sm">{t("admin.common.loading")}</p>}
        {data?.items.length === 0 && (
          <p className="bg-card text-muted-foreground rounded-lg border p-6 text-center text-sm">
            {debouncedSearch || categoryId ? t("admin.list.noMatch") : t("admin.tagsIa.empty")}
          </p>
        )}
        {data?.items.map((activite) => (
          // `key` inclut modifie_le : la carte repart des valeurs serveur après enregistrement.
          <CarteActivite key={`${activite.id}-${activite.modifie_le}`} activite={activite} />
        ))}
      </div>

      <Pagination page={data?.page ?? page} pages={data?.pages ?? 1} onPage={setPage} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Avancement : x / y validées + part des valeurs corrigées par l'humain
// ---------------------------------------------------------------------------

function Avancement() {
  const { t } = useTranslation();
  const { data } = useTagsStats();
  if (!data) return null;
  const ratio = data.publiees ? data.publiees_validees / data.publiees : 0;
  return (
    <div className="bg-card space-y-3 rounded-lg border p-4">
      <div className="flex items-center justify-between gap-4 text-sm">
        <span className="font-medium">
          {t("admin.tagsIa.progress", { done: data.publiees_validees, total: data.publiees })}
        </span>
        <span className="text-muted-foreground tabular-nums">{Math.round(ratio * 100)} %</span>
      </div>
      <div
        className="bg-muted h-2 overflow-hidden rounded-full"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={data.publiees}
        aria-valuenow={data.publiees_validees}
      >
        <div className="bg-primary h-full rounded-full transition-all" style={{ width: `${ratio * 100}%` }} />
      </div>
      {data.comparables > 0 && (
        <div className="text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
          <span>{t("admin.tagsIa.corrections", { count: data.comparables })}</span>
          {CHAMPS.map((champ) => (
            <span key={champ}>
              {t(`admin.tagsIa.fields.${champ}`)} :{" "}
              <strong className="text-foreground tabular-nums">
                {Math.round((data.corrections[champ] ?? 0) * 100)} %
              </strong>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Carte d'une activité : lecture, puis édition des tags
// ---------------------------------------------------------------------------

function titreLocal(a: ActiviteTags, langue: string): string {
  if (langue.startsWith("en")) return a.titre_en || a.titre;
  if (langue.startsWith("ar")) return a.titre_ar || a.titre;
  return a.titre;
}

function CarteActivite({ activite }: { activite: ActiviteTags }) {
  const { t, i18n } = useTranslation();
  const save = useSaveTags();
  const [edition, setEdition] = useState(false);
  const valeursServeur: TagsIA = {
    themes: activite.themes,
    public: activite.public,
    niveau_marche: activite.niveau_marche,
    interieur: activite.interieur,
    moment_ideal: activite.moment_ideal,
  };
  const [tags, setTags] = useState<TagsIA>(valeursServeur);
  const annuler = () => {
    setTags(valeursServeur);
    setEdition(false);
  };

  const complet =
    tags.themes.length > 0 &&
    tags.public.length > 0 &&
    tags.niveau_marche != null &&
    tags.interieur != null &&
    tags.moment_ideal != null;

  const enregistrer = (valider: boolean) => {
    if (!complet || tags.niveau_marche == null || tags.interieur == null || tags.moment_ideal == null) {
      return;
    }
    save.mutate({
      id: activite.id,
      payload: {
        themes: tags.themes,
        public: tags.public,
        niveau_marche: tags.niveau_marche,
        interieur: tags.interieur,
        moment_ideal: tags.moment_ideal,
        tags_valides: valider,
      },
    });
  };

  const basculer = <K extends "themes" | "public">(champ: K, valeur: TagsIA[K][number]) =>
    setTags((courant) => {
      const liste = courant[champ] as string[];
      const suivante = liste.includes(valeur) ? liste.filter((v) => v !== valeur) : [...liste, valeur];
      return { ...courant, [champ]: suivante };
    });

  const proposition = activite.tags_proposes;
  const modifie = (champ: ChampTag) => differe(activite, champ, tags[champ]);

  return (
    <article className="bg-card rounded-lg border p-4">
      <header className="flex flex-wrap items-start gap-3">
        {activite.photos ? (
          <img src={activite.photos} alt="" className="h-14 w-20 rounded object-cover" loading="lazy" />
        ) : (
          <span className="bg-muted text-muted-foreground flex h-14 w-20 items-center justify-center rounded">
            <ImageOff className="size-4" />
          </span>
        )}
        <div className="min-w-0 flex-1">
          <h2 className="font-medium">{titreLocal(activite, i18n.language)}</h2>
          <p className="text-muted-foreground text-xs">
            #{activite.id} · {activite.category?.nom ?? "—"} · {activite.localisation} ·{" "}
            {t("admin.activities.minutes", { count: activite.duree })}
          </p>
          <p className="text-muted-foreground mt-1 line-clamp-2 text-sm">{activite.description}</p>
        </div>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            activite.tags_valides ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700",
          )}
        >
          {t(activite.tags_valides ? "admin.tagsIa.validated" : "admin.tagsIa.toValidate")}
        </span>
      </header>

      <div className="mt-3 space-y-2">
        <Champ label={t("admin.tagsIa.fields.themes")} modifie={modifie("themes")}>
          {edition
            ? THEMES.map((v) => (
                <Puce key={v} actif={tags.themes.includes(v)} onClick={() => basculer("themes", v)}>
                  {t(`admin.tagsIa.theme.${v}`)}
                </Puce>
              ))
            : tags.themes.map((v) => <Puce key={v}>{t(`admin.tagsIa.theme.${v}`)}</Puce>)}
        </Champ>
        <Champ label={t("admin.tagsIa.fields.public")} modifie={modifie("public")}>
          {edition
            ? PUBLICS.map((v) => (
                <Puce key={v} actif={tags.public.includes(v)} onClick={() => basculer("public", v)}>
                  {t(`admin.tagsIa.public.${v}`)}
                </Puce>
              ))
            : tags.public.map((v) => <Puce key={v}>{t(`admin.tagsIa.public.${v}`)}</Puce>)}
        </Champ>
        <Champ label={t("admin.tagsIa.fields.niveau_marche")} modifie={modifie("niveau_marche")}>
          {(edition ? NIVEAUX : NIVEAUX.filter((n) => n === tags.niveau_marche)).map((n) => (
            <Puce
              key={n}
              actif={edition ? tags.niveau_marche === n : undefined}
              onClick={edition ? () => setTags({ ...tags, niveau_marche: n }) : undefined}
            >
              {n} · {t(`admin.tagsIa.niveau.${n}`)}
            </Puce>
          ))}
        </Champ>
        <Champ label={t("admin.tagsIa.fields.interieur")} modifie={modifie("interieur")}>
          {(edition ? [true, false] : [tags.interieur].filter((v) => v != null)).map((v) => (
            <Puce
              key={String(v)}
              actif={edition ? tags.interieur === v : undefined}
              onClick={edition ? () => setTags({ ...tags, interieur: v }) : undefined}
            >
              {t(`admin.tagsIa.interieur.${String(v)}`)}
            </Puce>
          ))}
        </Champ>
        <Champ label={t("admin.tagsIa.fields.moment_ideal")} modifie={modifie("moment_ideal")}>
          {(edition ? MOMENTS : MOMENTS.filter((m) => m === tags.moment_ideal)).map((m) => (
            <Puce
              key={m}
              actif={edition ? tags.moment_ideal === m : undefined}
              onClick={edition ? () => setTags({ ...tags, moment_ideal: m }) : undefined}
            >
              {t(`admin.tagsIa.moment.${m}`)}
            </Puce>
          ))}
        </Champ>
      </div>

      {proposition ? (
        <details className="text-muted-foreground mt-3 text-xs">
          <summary className="flex cursor-pointer items-center gap-1.5">
            <Info className="size-3.5" />
            {t("admin.tagsIa.proposedBy", { source: proposition.modele ?? proposition.source })}
            {proposition.confiance && (
              <>
                {" · "}
                {t("admin.tagsIa.confidence", {
                  level: t(`admin.tagsIa.confidenceLevel.${proposition.confiance}`),
                })}
              </>
            )}
            {" · "}
            {t("admin.tagsIa.reasons")}
          </summary>
          {/* Raisons produites par le script (en français, langue du code). */}
          <p className="mt-1 ps-5" dir="ltr">
            {proposition.raisons ?? "—"}
          </p>
        </details>
      ) : (
        <p className="text-muted-foreground mt-3 text-xs">{t("admin.tagsIa.noProposal")}</p>
      )}

      {edition && !complet && (
        <p className="text-destructive mt-2 text-xs">{t("admin.tagsIa.incomplete")}</p>
      )}

      <footer className="mt-3 flex flex-wrap justify-end gap-2">
        {edition ? (
          <>
            <Bouton onClick={annuler} disabled={save.isPending}>
              {t("admin.tagsIa.cancel")}
            </Bouton>
            <Bouton onClick={() => enregistrer(false)} disabled={!complet || save.isPending}>
              {t("admin.tagsIa.saveDraft")}
            </Bouton>
          </>
        ) : (
          <>
            <Bouton onClick={() => setEdition(true)}>
              <Pencil className="size-4" />
              {t("admin.tagsIa.edit")}
            </Bouton>
            {activite.tags_valides && (
              <Bouton onClick={() => enregistrer(false)} disabled={save.isPending}>
                <Undo2 className="size-4" />
                {t("admin.tagsIa.unvalidate")}
              </Bouton>
            )}
          </>
        )}
        {(edition || !activite.tags_valides) && (
          <Bouton principal onClick={() => enregistrer(true)} disabled={!complet || save.isPending}>
            <Check className="size-4" />
            {t("admin.tagsIa.validate")}
          </Bouton>
        )}
      </footer>
    </article>
  );
}

function Champ({ label, modifie, children }: { label: string; modifie: boolean; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-muted-foreground w-28 shrink-0 text-xs font-medium">
        {label}
        {modifie && (
          <span className="ms-1 rounded bg-sky-100 px-1 text-[10px] text-sky-700">
            {t("admin.tagsIa.changed")}
          </span>
        )}
      </span>
      {children}
    </div>
  );
}

/** Puce : lecture seule (sans `onClick`) ou interrupteur (`aria-pressed`). */
function Puce({
  actif,
  onClick,
  children,
}: {
  actif?: boolean;
  onClick?: () => void;
  children: ReactNode;
}) {
  if (!onClick) {
    return (
      <span className="bg-primary/10 text-primary rounded-full px-2.5 py-0.5 text-xs font-medium">
        {children}
      </span>
    );
  }
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={actif}
      className={cn(
        "focus-visible:ring-primary rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none",
        actif
          ? "border-primary bg-primary text-white"
          : "text-muted-foreground hover:bg-muted border-input bg-background",
      )}
    >
      {children}
    </button>
  );
}

function Bouton({
  principal,
  onClick,
  disabled,
  children,
}: {
  principal?: boolean;
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition disabled:pointer-events-none disabled:opacity-50",
        principal ? "bg-primary text-white hover:opacity-90" : "hover:bg-muted border",
      )}
    >
      {children}
    </button>
  );
}
