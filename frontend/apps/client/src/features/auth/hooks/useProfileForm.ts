import { useCallback, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { authApi } from "@voyara/auth/api/auth.api";
import { changePasswordSchema, updateProfileSchema, type ChangePasswordInput, type UpdateProfileInput } from "@/features/auth/schemas/authSchemas";
import { useAuth } from "@voyara/auth/hooks/use-auth";
import { authStore } from "@voyara/auth/stores/auth.store";
import { getAuthErrorCode } from "@voyara/api/api-error";
import { toApiError } from "@voyara/api/errors";

export function useProfileForm() {
  const { t } = useTranslation();
  const { user, refreshUser } = useAuth();

  const profileForm = useForm<UpdateProfileInput>({
    resolver: zodResolver(updateProfileSchema),
    mode: "onTouched",
    defaultValues: { nom: "", prenom: "" },
  });

  const passwordForm = useForm<ChangePasswordInput>({
    resolver: zodResolver(changePasswordSchema),
    mode: "onTouched",
    defaultValues: { old_password: "", new_password: "", confirm_new_password: "" },
  });

  useEffect(() => {
    if (user) {
      profileForm.reset({ nom: user.nom ?? "", prenom: user.prenom ?? "" });
    }
  }, [profileForm, user]);

  const onSubmitProfile = useCallback(
    async (data: UpdateProfileInput) => {
      try {
        await authApi.updateProfile({ nom: data.nom, prenom: data.prenom });
        await refreshUser();
        toast.success(t("auth.profile.success"));
      } catch (error: unknown) {
        const apiError = toApiError(error);
        const message = apiError.message ?? t("errors.unknown");
        profileForm.setError("root.serverError", { type: "update_profile", message });
        toast.error(message);
      }
    },
    [profileForm, refreshUser, t],
  );

  const onSubmitPassword = useCallback(
    async (data: ChangePasswordInput) => {
      try {
        const tokens = await authApi.changePassword({
          old_password: data.old_password,
          new_password: data.new_password,
          refresh_token: authStore.getState().refreshToken ?? "",
        });
        authStore.getState().setTokens(tokens.access_token, tokens.refresh_token);
        await refreshUser();
        passwordForm.reset();
        toast.success(t("auth.password.success"));
      } catch (error: unknown) {
        const apiError = toApiError(error);
        const code = getAuthErrorCode(error);
        const message = apiError.message ?? t(`auth.errors.${code}`, { defaultValue: t("errors.unknown") });
        passwordForm.setError("root.serverError", { type: code, message });
        toast.error(message);
      }
    },
    [passwordForm, refreshUser, t],
  );

  return { profileForm, onSubmitProfile, passwordForm, onSubmitPassword };
}
