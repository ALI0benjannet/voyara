import { useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { authApi } from "@voyara/auth/api/auth.api";
import { forgotPasswordSchema, type ForgotPasswordInput } from "@/features/auth/schemas/authSchemas";
import { paths } from "@/routes/paths";
import { getAuthErrorCode } from "@voyara/api/api-error";
import { toApiError } from "@voyara/api/errors";

export function useForgotPasswordForm() {
  const { t } = useTranslation();
  const router = useRouter();

  const form = useForm<ForgotPasswordInput>({
    resolver: zodResolver(forgotPasswordSchema),
    mode: "onTouched",
    defaultValues: { email: "" },
  });

  const { setError } = form;

  const onSubmit = useCallback(
    async (data: ForgotPasswordInput) => {
      try {
        await authApi.forgotPassword({ email: data.email });
        router.replace(`${paths.checkEmail}?email=${encodeURIComponent(data.email)}`);
      } catch (error: unknown) {
        const apiError = toApiError(error);
        const code = getAuthErrorCode(error);
        const message = apiError.message ?? t(`auth.errors.${code}`, { defaultValue: t("errors.unknown") });

        setError("root.serverError", { type: code, message });
        toast.error(message);
      }
    },
    [router, setError, t],
  );

  return { form, onSubmit };
}
