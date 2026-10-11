"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CalendarCheck,
  ChevronDown,
  Heart,
  LayoutDashboard,
  LogOut,
  Settings,
  UserRound,
} from "lucide-react";

import { Avatar } from "@voyara/ui/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@voyara/ui/components/ui/dropdown-menu";
import { useAuth } from "@voyara/auth/hooks/use-auth";
import { env } from "@voyara/api/env";

import { paths } from "@/routes/paths";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

export function UserMenu() {
  const { t } = useHydratedTranslation();
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push(paths.login);
  };

  return (
    // `openOnHover` : le menu s'ouvre au survol, sans clic ni changement de page.
    // Le clic reste opérationnel pour le tactile et le clavier.
    <DropdownMenu openOnHover>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={t("nav.account", "Mon compte")}
          aria-haspopup="menu"
          className="group hover:bg-muted focus-visible:ring-ring inline-flex items-center gap-2.5 rounded-full py-1 ps-1 pe-2.5 transition-colors focus-visible:ring-2 focus-visible:outline-none"
        >
          <Avatar
            src={user?.avatar_url}
            name={user?.full_name}
            email={user?.email}
            size="md"
            className="group-hover:ring-primary/30 ring-2 ring-transparent transition"
          />
          <span className="text-foreground hidden max-w-[10rem] truncate text-sm font-medium lg:inline">
            {user?.full_name ?? user?.email}
          </span>
          <ChevronDown
            className="text-foreground/40 group-hover:text-foreground/70 hidden size-4 transition-transform lg:inline"
            strokeWidth={2}
          />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end">
        <div className="border-border flex items-center gap-3 border-b px-3 pt-1 pb-3">
          <Avatar src={user?.avatar_url} name={user?.full_name} email={user?.email} size="md" />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">
              {user?.full_name ?? t("nav.account", "Mon compte")}
            </p>
            <p className="text-muted-foreground truncate text-xs">{user?.email}</p>
          </div>
        </div>

        <div className="pt-2">
          <DropdownMenuItem onSelect={() => router.push(paths.profile)}>
            <span className="flex items-center gap-2">
              <UserRound className="text-muted-foreground size-4" />
              {t("nav.profile", "Mon profil")}
            </span>
          </DropdownMenuItem>

          <DropdownMenuItem onSelect={() => router.push(paths.bookings)}>
            <span className="flex items-center gap-2">
              <CalendarCheck className="text-muted-foreground size-4" />
              {t("nav.bookings", "Mes réservations")}
            </span>
          </DropdownMenuItem>

          <DropdownMenuItem onSelect={() => router.push(paths.favorites)}>
            <span className="flex items-center gap-2">
              <Heart className="text-muted-foreground size-4" />
              {t("nav.favorites", "Mes favoris")}
            </span>
          </DropdownMenuItem>

          <DropdownMenuItem onSelect={() => router.push(paths.profile)}>
            <span className="flex items-center gap-2">
              <Settings className="text-muted-foreground size-4" />
              {t("nav.settings", "Paramètres")}
            </span>
          </DropdownMenuItem>

          {user?.role === "admin" && (
            <DropdownMenuItem onSelect={() => window.location.assign(env.VITE_ADMIN_URL)}>
              <span className="flex items-center gap-2">
                <LayoutDashboard className="text-muted-foreground size-4" />
                Tableau de bord admin
              </span>
            </DropdownMenuItem>
          )}
        </div>

        <div className="border-border mt-2 border-t pt-2">
          <DropdownMenuItem
            className="text-destructive hover:bg-destructive/10"
            onSelect={() => void handleLogout()}
          >
            <span className="flex items-center gap-2">
              <LogOut className="size-4" />
              {t("nav.logout", "Déconnexion")}
            </span>
          </DropdownMenuItem>
        </div>

        <Link href={paths.profile} className="sr-only">
          {t("nav.profile", "Mon profil")}
        </Link>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
