import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";

import { cn } from "@voyara/ui/lib/utils";

/** Délai avant de lancer la recherche : assez court pour paraître instantané,
 *  assez long pour ne pas envoyer une requête par touche. */
const DEBOUNCE_MS = 300;

/** Valeur stabilisée après `delay` ms sans changement. */
export function useDebouncedValue<T>(value: T, delay = DEBOUNCE_MS): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

export const SELECT_CLASS =
  "border-input bg-background focus-visible:ring-primary h-9 rounded-md border px-2.5 text-sm focus-visible:ring-2 focus-visible:outline-none";

/** Barre d'outils d'une liste admin : recherche plein texte, filtres libres
 *  (`children`, en général des `<select>`) et compteur de résultats. */
export function ListToolbar({
  search,
  onSearch,
  placeholder,
  count,
  total,
  children,
}: {
  search: string;
  onSearch: (value: string) => void;
  placeholder: string;
  /** Résultats affichés (après filtres). */
  count?: number;
  /** Total sans filtre ; affiché « count / total » quand il diffère. */
  total?: number;
  children?: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <div className="bg-card flex flex-wrap items-center gap-2 rounded-lg border p-3">
      <div className="relative min-w-60 flex-1">
        <Search className="text-muted-foreground pointer-events-none absolute start-2.5 top-1/2 size-4 -translate-y-1/2" />
        <input
          type="search"
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
          className="border-input bg-background focus-visible:ring-primary h-9 w-full rounded-md border ps-8 pe-8 text-sm focus-visible:ring-2 focus-visible:outline-none"
        />
        {search && (
          <button
            type="button"
            onClick={() => onSearch("")}
            className="text-muted-foreground hover:text-foreground absolute end-2 top-1/2 -translate-y-1/2 rounded p-0.5"
            aria-label={t("admin.list.clear")}
          >
            <X className="size-4" />
          </button>
        )}
      </div>
      {children}
      {count !== undefined && (
        <span className="text-muted-foreground ms-auto text-sm whitespace-nowrap">
          {total !== undefined && total !== count
            ? t("admin.list.countOf", { count, total })
            : t("admin.list.count", { count })}
        </span>
      )}
    </div>
  );
}

/** Pagination « Précédent · page x / n · Suivant ». */
export function Pagination({
  page,
  pages,
  onPage,
}: {
  page: number;
  pages: number;
  onPage: (page: number) => void;
}) {
  const { t } = useTranslation();
  if (pages <= 1) return null;
  const button =
    "inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted disabled:pointer-events-none disabled:opacity-40";
  return (
    <nav className="flex items-center justify-end gap-2" aria-label={t("admin.list.pagination")}>
      <button
        type="button"
        className={button}
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
      >
        <ChevronLeft className="size-4 rtl:rotate-180" />
        {t("admin.common.prev")}
      </button>
      <span className={cn("text-muted-foreground px-2 text-sm")}>
        {t("admin.list.page", { page, pages })}
      </span>
      <button
        type="button"
        className={button}
        disabled={page >= pages}
        onClick={() => onPage(page + 1)}
      >
        {t("admin.common.next")}
        <ChevronRight className="size-4 rtl:rotate-180" />
      </button>
    </nav>
  );
}
