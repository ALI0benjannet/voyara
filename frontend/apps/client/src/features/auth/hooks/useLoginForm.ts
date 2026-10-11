import { useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { authApi } from "@voyara/auth/api/auth.api";
import { getAuthErrorCode } from "@voyara/api/api-error";
import { loginSchema, type LoginInput } from "@/features/auth/schemas/authSchemas";
import { authStore } from "@voyara/auth/stores/auth.store";

const DEFAULT_REDIRECT = "/";

const AUTH_PATHS = ["/login", "/register", "/verify-email", "/forgot-password", "/reset-password", "/check-email"];

/** Destination apres connexion. Les admins restent sur le site public :
 *  l'espace admin (micro-frontend separe) est accessible via le menu profil. */
export function resolvePostLoginRedirect(from: string | undefined) {
  // Une page d'auth ou un chemin admin n'est jamais une destination valable ici
  const target =
    from && !AUTH_PATHS.some((p) => from.startsWith(p)) && !from.startsWith("/admin")
      ? from
      : undefined;
  return target ?? DEFAULT_REDIRECT;
}

export function useLoginForm() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const setTokens = authStore((state) => state.setTokens);

  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    mode: "onTouched",
    defaultValues: { email: "", password: "" },
  });

  const { setError } = form;

  const onSubmit = useCallback(
    async (data: LoginInput) => {
      try {
        const tokens = await authApi.login(data);
        setTokens(tokens.access_token, tokens.refresh_token);

        await authApi.me(); // pre-charge le profil (cache axios/react-query cote provider)

        const from = searchParams?.get("next") ?? undefined;
        router.replace(resolvePostLoginRedirect(from));
      } catch (error: unknown) {
        const code = getAuthErrorCode(error);
        const message = t(`auth.errors.${code}`, {
          defaultValue: t("errors.unknown"),
        });

        if (code === "invalid_credentials") {
          setError("root.serverError", { type: code, message });
          return;
        }

        toast.error(message);
      }
    },
    [searchParams, router, setError, setTokens, t],
  );

  return { form, onSubmit };
}
