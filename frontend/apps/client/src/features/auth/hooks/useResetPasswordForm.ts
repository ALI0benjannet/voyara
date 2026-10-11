import { useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { authApi } from "@voyara/auth/api/auth.api";
import { resetPasswordSchema, type ResetPasswordInput } from "@/features/auth/schemas/authSchemas";
import { paths } from "@/routes/paths";
import { getAuthErrorCode } from "@voyara/api/api-error";
import { toApiError } from "@voyara/api/errors";

export function useResetPasswordForm() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams?.get("token") ?? "";

  const form = useForm<ResetPasswordInput>({
    resolver: zodResolver(resetPasswordSchema),
    mode: "onTouched",
    defaultValues: { new_password: "", confirm_password: "" },
  });

  const { setError, watch } = form;
  const password = watch("new_password");

  const onSubmit = useCallback(
    async (data: ResetPasswordInput) => {
      if (!token) {
        setError("root.serverError", {
          type: "missing_token",
          message: t("auth.errors.invalid_token"),
        });
        return;
      }

      try {
        await authApi.resetPassword({ token, new_password: data.new_password });
        toast.success(t("auth.resetPassword.success"));
        router.replace(paths.login);
      } catch (error: unknown) {
        const apiError = toApiError(error);
        const code = getAuthErrorCode(error);
        const message = apiError.message ?? t(`auth.errors.${code}`, { defaultValue: t("errors.unknown") });

        setError("root.serverError", { type: code, message });
        toast.error(message);
      }
    },
    [router, setError, t, token],
  );

  return { form, onSubmit, tokenMissing: !token, password };
}
