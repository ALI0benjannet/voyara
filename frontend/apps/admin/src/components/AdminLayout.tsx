import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard,
  MapPin,
  BedDouble,
  Plane,
  Car,
  CarTaxiFront,
  Tags,
  CalendarCheck,
  CreditCard,
  Users,
  ExternalLink,
  LogOut,
} from "lucide-react";
import { Button } from "@voyara/ui/components/ui/button";
import { useAuth } from "@voyara/auth/hooks/use-auth";
import { cn } from "@voyara/ui/lib/utils";
import { env } from "@voyara/api/env";

import { AdminLanguageSwitcher } from "./AdminLanguageSwitcher";

/** Entrées de navigation : on stocke la clé i18n, pas le libellé. */
const NAV = [
  { to: "/dashboard", key: "admin.nav.dashboard", icon: LayoutDashboard },
  { to: "/activities", key: "admin.nav.activities", icon: MapPin },
  { to: "/categories", key: "admin.nav.categories", icon: Tags },
  { to: "/stays", key: "admin.nav.stays", icon: BedDouble },
  { to: "/flights", key: "admin.nav.flights", icon: Plane },
  { to: "/car-rentals", key: "admin.nav.carRentals", icon: Car },
  { to: "/transfers", key: "admin.nav.transfers", icon: CarTaxiFront },
  { to: "/bookings", key: "admin.nav.bookings", icon: CalendarCheck },
  { to: "/payments", key: "admin.nav.payments", icon: CreditCard },
  { to: "/users", key: "admin.nav.users", icon: Users },
];

export function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <div className="bg-muted/30 flex min-h-dvh">
      <aside className="bg-card hidden w-64 shrink-0 flex-col border-e md:flex">
        {/* Filet doré : seule touche décorative de l'admin — l'identité est
            rappelée, la lisibilité des données reste prioritaire. */}
        <div aria-hidden className="bg-gold h-0.5" />
        <div className="border-border flex h-16 items-center gap-2.5 border-b px-4 font-semibold">
          <span className="bg-card flex size-9 items-center justify-center rounded-xl p-1 shadow-sm">
            <img src="/admin/logo.png" alt="" className="size-full object-contain" />
          </span>
          <span className="text-primary-hover">{t("admin.brand")}</span>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {NAV.map(({ to, key, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              <Icon className="size-4" />
              {t(key)}
            </NavLink>
          ))}

          <a
            href={env.VITE_CLIENT_URL}
            className="text-muted-foreground hover:bg-muted hover:text-foreground flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors"
          >
            <ExternalLink className="size-4" />
            {t("admin.nav.viewSite")}
          </a>
        </nav>

        <div className="border-t p-3">
          <AdminLanguageSwitcher />
          <p className="text-muted-foreground truncate px-3 pb-2 text-xs">{user?.email}</p>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={() => {
              logout();
              navigate("/login", { replace: true });
            }}
          >
            <LogOut className="size-4" />
            <span className="ms-2">{t("admin.nav.logout")}</span>
          </Button>
        </div>
      </aside>

      <main className="flex-1 p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
}
