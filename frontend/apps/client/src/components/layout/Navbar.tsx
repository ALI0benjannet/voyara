"use client";

import {
  BedDouble,
  Car,
  CarTaxiFront,
  Briefcase,
  FerrisWheel,
  Heart,
  LogIn,
  Plane,
  ShoppingCart,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { cn } from "@voyara/ui/lib/utils";
import { useAuth } from "@voyara/auth/hooks/use-auth";

import { LanguageMenu } from "./LanguageMenu";
import { UserMenu } from "./UserMenu";
import { HeroSearch } from "@/components/home/HeroSearch";
import { useFavorites } from "@/features/favorites/hooks";
import { useMyBookings } from "@/features/bookings/hooks";
import { useCondensedHeader } from "@/features/layout/use-condensed-header";
import { paths } from "@/routes/paths";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

function Badge({ count, tone }: { count: number; tone: "accent" | "primary" }) {
  if (!count) return null;
  return (
    <span
      className={cn(
        "absolute -end-2 -top-2 min-w-[18px] rounded-full px-1 text-center text-[10px] leading-[18px] font-bold text-white",
        tone === "accent" ? "bg-primary" : "bg-accent",
      )}
    >
      {count}
    </span>
  );
}

/** Onglets des offres de voyage, dans l'ordre des grands sites de réservation.
 *  Seules les Activités sont réservables en ligne ; les autres offres sont
 *  consultables (catalog `/api/v1/offres/*`). */
const TRAVEL_TABS = [
  { href: paths.stays, labelKey: "nav.stays", Icon: BedDouble },
  { href: paths.flights, labelKey: "nav.flights", Icon: Plane },
  { href: paths.carRentals, labelKey: "nav.carRentals", Icon: Car },
  { href: paths.activities, labelKey: "nav.activities", Icon: FerrisWheel },
  { href: paths.transfers, labelKey: "nav.transfers", Icon: CarTaxiFront },
] as const;

const ICON_TAB_CLASS =
  "flex flex-col items-center gap-1 text-foreground/70 transition-colors hover:text-primary";

/** Onglet icône + libellé de l'en-tête. Rendu en lien, ou en bouton quand
 *  l'action n'est pas une navigation (panier à venir, sélecteur de langue). */
function IconTab({
  href,
  onClick,
  icon,
  label,
  badge,
  title,
}: {
  href?: string;
  onClick?: () => void;
  icon: React.ReactNode;
  label: string;
  badge?: React.ReactNode;
  title?: string;
}) {
  const content = (
    <>
      <span className="relative leading-none">
        {icon}
        {badge}
      </span>
      <span className="text-xs font-medium">{label}</span>
    </>
  );

  if (href) {
    return (
      <Link href={href} className={ICON_TAB_CLASS} title={title}>
        {content}
      </Link>
    );
  }
  return (
    <button type="button" onClick={onClick} className={ICON_TAB_CLASS} title={title}>
      {content}
    </button>
  );
}

export function Navbar() {
  const { t } = useHydratedTranslation();
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const { data: favorites } = useFavorites();
  const { data: bookings } = useMyBookings();

  // Au défilement, seule la rangée des espaces se replie ; la navigation reste.
  const { condensed, showSearch } = useCondensedHeader();

  // Un onglet reste actif sur ses sous-pages (fiche activité, etc.).
  const isActive = (href: string) =>
    href === paths.home ? pathname === href : pathname === href || pathname?.startsWith(`${href}/`);

  const tabClass = (active: boolean) =>
    cn(
      "shrink-0 border-b-2 px-3 pb-2.5 pt-1 text-[15px] font-semibold transition-colors",
      active
        ? "border-primary text-primary"
        : "border-transparent text-foreground/70 hover:border-border hover:text-foreground",
    );

  // Deux espaces : voyageur (le site de réservation) et prestataire (publication
  // d'activités, soumises à la modération admin).
  const inProviderSpace = pathname?.startsWith(paths.provider) ?? false;
  const spaceClass = (active: boolean) =>
    cn(
      "focus-visible:ring-primary flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:outline-none",
      active
        ? "bg-primary text-primary-foreground shadow-sm"
        : "text-foreground/80 hover:bg-card hover:text-primary",
    );

  return (
    // Au défilement, l'en-tête entier glisse vers le haut de la hauteur de la
    // rangée 0 (h-14) : un `transform` est animé par le compositeur, sans
    // recalcul de mise en page ni décalage du contenu — contrairement à une
    // animation de hauteur, qui saccade et fait sauter la page.
    <header
      className={cn(
        "border-border bg-card sticky top-0 z-50 border-b shadow-sm will-change-transform",
        "transition-transform duration-300 ease-out motion-reduce:transition-none",
        condensed && "-translate-y-14",
      )}
    >
      {/* Rangée 0 : bascule entre l'espace voyageur et l'espace prestataire
          (sélecteur segmenté). Hauteur fixe, pour que le glissement corresponde
          exactement ; `inert` une fois masquée : plus atteignable au clavier. */}
      <div
        inert={condensed}
        className={cn(
          "border-border flex h-14 items-center border-b transition-opacity duration-300 motion-reduce:transition-none",
          condensed ? "opacity-0" : "opacity-100",
        )}
      >
        <div className="mx-auto flex max-w-7xl justify-center px-4 sm:px-8">
          <div className="border-border bg-muted flex items-center gap-1 rounded-full border p-1">
            <Link href={paths.home} className={spaceClass(!inProviderSpace)}>
              <FerrisWheel className="size-4" />
              {t("nav.travelerSpace")}
            </Link>
            <Link href={paths.provider} className={spaceClass(inProviderSpace)}>
              <Briefcase className="size-4" />
              {t("nav.providerSpace")}
            </Link>
          </div>
        </div>
      </div>

      {/* Rangée 1 : logo — recherche (une fois condensé) — actions du compte. */}
      <div className="mx-auto flex h-[72px] max-w-7xl items-center gap-6 px-4 sm:px-8">
        <Link
          href={paths.home}
          className="focus-visible:ring-primary flex shrink-0 items-center gap-2.5 rounded-lg focus-visible:ring-2 focus-visible:outline-none"
        >
          <img src="/logo.png" alt="Voyara" className="size-10 object-contain" />
          {/* Le libellé s'efface en mode condensé : seul le logo reste, comme
              sur les grands sites de réservation. */}
          <span
            className={cn(
              "font-display text-[22px] leading-none tracking-wide transition-opacity",
              condensed ? "hidden lg:inline" : "inline",
            )}
          >
            Voyara
          </span>
        </Link>

        {/* Recherche centrée : n'occupe l'espace que lorsqu'elle est visible. */}
        {showSearch && (
          <div className="mx-auto hidden w-full max-w-xl md:block">
            <HeroSearch variant="compact" />
          </div>
        )}

        <div className={cn("flex items-center gap-4 sm:gap-6", !showSearch && "ms-auto")}>
          <IconTab
            href={paths.favorites}
            icon={<Heart className="size-[21px]" strokeWidth={1.7} />}
            label={t("nav.favoritesShort")}
            badge={<Badge count={favorites?.length ?? 0} tone="accent" />}
          />

          {/* Panier : mène aux réservations (la réservation multiple viendra
              s'y greffer après la soutenance). */}
          <IconTab
            href={paths.bookings}
            icon={<ShoppingCart className="size-[21px]" strokeWidth={1.7} />}
            label={t("nav.cart")}
            badge={<Badge count={bookings?.total ?? 0} tone="primary" />}
          />

          <LanguageMenu />

          {/* Séparateur : distingue les raccourcis du bloc identité. */}
          <span aria-hidden className="bg-border hidden h-8 w-px sm:block" />

          {isAuthenticated ? (
            <UserMenu />
          ) : (
            <button
              type="button"
              onClick={() => router.push(paths.login)}
              className="bg-primary text-primary-foreground hover:bg-primary-hover focus-visible:ring-primary flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
            >
              <LogIn className="size-4" />
              <span className="hidden sm:inline">{t("nav.login")}</span>
            </button>
          )}
        </div>
      </div>

      {/* Recherche repliée sous le logo sur petits écrans : la rangée 1 n'y a
          pas la place de l'accueillir au centre. */}
      {showSearch && (
        <div className="mx-auto max-w-7xl px-4 pb-3 md:hidden">
          <HeroSearch variant="compact" />
        </div>
      )}

      {/* Rangée 2 : navigation principale, visible sur toutes les pages et à
          tout moment du défilement. Les catégories sont des filtres de la page
          Activités, pas des entrées de menu ; le profil vit dans le menu du
          compte (un seul point d'accès). */}
      <nav
        aria-label={t("nav.menu")}
        className="mx-auto flex max-w-7xl [scrollbar-width:none] gap-1 overflow-x-auto px-4 sm:px-8"
      >
        <Link
          href={paths.home}
          aria-current={isActive(paths.home) ? "page" : undefined}
          className={tabClass(isActive(paths.home))}
        >
          {t("nav.home")}
        </Link>
        {TRAVEL_TABS.map(({ href, labelKey, Icon }) => (
          <Link
            key={href}
            href={href}
            aria-current={isActive(href) ? "page" : undefined}
            className={cn(tabClass(isActive(href)), "flex items-center gap-2")}
          >
            <Icon className="size-[18px]" strokeWidth={1.7} />
            {t(labelKey)}
          </Link>
        ))}
      </nav>
    </header>
  );
}
