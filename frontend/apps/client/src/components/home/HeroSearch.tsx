"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { cn } from "@voyara/ui/lib/utils";

import { paths } from "@/routes/paths";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Délai avant de répercuter la frappe dans l'URL. Assez court pour paraître
 *  instantané, assez long pour ne pas déclencher une requête par touche. */
const SEARCH_DEBOUNCE_MS = 300;

/** Barre de recherche destination / date / voyageurs.
 *
 *  Deux présentations pour un seul comportement :
 *  - `hero` : la grande barre posée sur l'image d'accueil ;
 *  - `compact` : la même, réduite, affichée dans l'en-tête sur l'accueil et le
 *    catalogue (voir `useCondensedHeader`).
 *
 *  La recherche se déclenche **dès la première lettre** : la saisie est
 *  répercutée dans l'URL du catalogue, que la page relit pour re-filtrer
 *  côté serveur. Valider le formulaire reste possible (touche Entrée). */
export function HeroSearch({ variant = "hero" }: { variant?: "hero" | "compact" }) {
  const { t } = useHydratedTranslation();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const onCatalog = pathname === paths.activities;
  const urlSearch = searchParams?.get("search") ?? "";

  const [search, setSearch] = useState(urlSearch);
  const [date, setDate] = useState("");
  const [guests, setGuests] = useState(2);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Ne pas naviguer tant que l'utilisateur n'a pas tapé : sans ce garde-fou,
  // le montage du composant redirigerait tout seul vers le catalogue.
  const typing = useRef(false);

  const compact = variant === "compact";

  // Resynchronise le champ quand l'URL change sans passer par la frappe
  // (retour arrière, bouton « Réinitialiser » des filtres…).
  useEffect(() => {
    if (!typing.current) setSearch(urlSearch);
  }, [urlSearch]);

  // Reprise du focus après une navigation.
  //
  // Taper depuis l'accueil fait changer de page : l'instance du hero est
  // démontée et celle de l'en-tête est montée à sa place. Comme ce sont deux
  // éléments DOM distincts, le navigateur perd le focus et la frappe est
  // interrompue. On le rend à la nouvelle instance, curseur en fin de texte,
  // pour que la saisie continue sans rupture.
  useEffect(() => {
    if (!urlSearch) return; // arrivée sans recherche : ne pas voler le focus
    const input = inputRef.current;
    if (!input || document.activeElement === input) return;

    // L'en-tête monte deux instances (une centrée pour le bureau, une repliée
    // pour le mobile) et n'en montre qu'une selon la largeur d'écran. Sans ce
    // test, l'instance masquée volerait le focus au profit d'un champ invisible.
    if (input.offsetParent === null) return;

    input.focus();
    const end = input.value.length;
    input.setSelectionRange(end, end);
    // Une seule reprise, au montage : réagir à chaque changement d'URL
    // ramènerait le focus alors que l'utilisateur est passé à autre chose.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Évite qu'un minuteur en attente navigue après le démontage.
  useEffect(() => () => void (debounce.current && clearTimeout(debounce.current)), []);

  /** Écrit le terme dans l'URL du catalogue — c'est elle qui pilote la liste. */
  const applySearch = (term: string) => {
    const params = new URLSearchParams(onCatalog ? (searchParams?.toString() ?? "") : "");
    if (term.trim()) params.set("search", term.trim());
    else params.delete("search");

    const url = `${paths.activities}?${params.toString()}`;
    // Sur le catalogue on remplace l'entrée d'historique (sinon chaque lettre
    // en créerait une) ; depuis l'accueil, la première frappe est une vraie
    // navigation que l'utilisateur doit pouvoir annuler avec « Précédent ».
    if (onCatalog) router.replace(url, { scroll: false });
    else router.push(url);
  };

  const onSearchChange = (value: string) => {
    setSearch(value);
    typing.current = true;
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      typing.current = false;
      applySearch(value);
    }, SEARCH_DEBOUNCE_MS);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    // Entrée : on n'attend pas le délai en cours.
    if (debounce.current) clearTimeout(debounce.current);
    typing.current = false;
    applySearch(search);
  };

  return (
    <form
      onSubmit={submit}
      role="search"
      className={cn(
        "border-border bg-card flex items-stretch gap-1 border text-start",
        compact
          ? "w-full rounded-full p-1 shadow-sm"
          : "mx-auto max-w-3xl rounded-3xl p-2 shadow-[0_18px_44px_rgba(28,54,65,.14)] sm:rounded-full",
      )}
    >
      <input
        ref={inputRef}
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        // Le champ n'est plus « en cours de frappe » dès qu'il perd le focus :
        // sans cela, `typing` resterait bloqué et le champ ne se
        // resynchroniserait plus avec l'URL.
        onBlur={() => {
          typing.current = false;
        }}
        placeholder={t("home.searchPh")}
        aria-label={t("home.searchPh")}
        className={cn(
          "text-foreground placeholder:text-foreground/40 min-w-0 flex-[2] bg-transparent focus:outline-none",
          compact ? "px-4 py-2 text-sm" : "px-5 py-3.5 text-base",
        )}
      />
      <div className={cn("bg-border hidden w-px sm:block", compact ? "my-1.5" : "my-2")} />
      <input
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value)}
        aria-label={t("detail.dateL")}
        className={cn(
          "text-foreground hidden min-w-0 flex-1 bg-transparent focus:outline-none md:block",
          compact ? "px-2 py-2 text-sm" : "px-3 py-3.5 text-[15px]",
        )}
      />
      <div className={cn("bg-border hidden w-px md:block", compact ? "my-1.5" : "my-2")} />
      <select
        value={guests}
        onChange={(e) => setGuests(Number(e.target.value))}
        aria-label={t("detail.guestsL")}
        className={cn(
          "text-foreground hidden min-w-0 flex-1 bg-transparent focus:outline-none sm:block",
          compact ? "px-2 py-2 text-sm" : "px-2 py-3.5 text-[15px]",
        )}
      >
        {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
          <option key={n} value={n}>
            {t("home.guests", { count: n })}
          </option>
        ))}
      </select>
      <button
        type="submit"
        className={cn(
          "bg-primary text-primary-foreground hover:bg-primary-hover shrink-0 rounded-full font-semibold transition-colors",
          compact ? "px-5 text-sm" : "px-6 text-base sm:px-8",
        )}
      >
        {t("actions.search")}
      </button>
    </form>
  );
}
