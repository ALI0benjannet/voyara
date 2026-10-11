import { api } from "@voyara/api/axios";
import { endpoints } from "@voyara/api/endpoints";
import type {
  ChangePasswordPayload,
  ForgotPasswordPayload,
  LoginPayload,
  RefreshPayload,
  RegisterPayload,
  ResendVerificationPayload,
  ResetPasswordPayload,
  Token,
  UpdateProfilePayload,
  UserRead,
  VerifyEmailPayload,
} from "@voyara/auth/types/auth.types";

export const authApi = {
  login: (payload: LoginPayload) =>
    api.post<Token>(endpoints.auth.login, payload).then((response) => response.data),
  logout: (refreshToken?: string) =>
    api.post(endpoints.auth.logout, { token: refreshToken }).then((response) => response.data),
  me: () => api.get<UserRead>(endpoints.auth.me).then((response) => response.data),
  register: (payload: RegisterPayload) =>
    api.post<UserRead>(endpoints.auth.register, payload).then((response) => response.data),
  refresh: (payload: RefreshPayload) =>
    api.post<Token>(endpoints.auth.refresh, payload).then((response) => response.data),
  verifyEmail: (payload: VerifyEmailPayload) =>
    api.post(endpoints.auth.verifyEmail, payload).then((response) => response.data),
  resendVerification: (payload: ResendVerificationPayload) =>
    api.post(endpoints.auth.resendVerification, payload).then((response) => response.data),
  forgotPassword: (payload: ForgotPasswordPayload) =>
    api.post(endpoints.auth.forgotPassword, payload).then((response) => response.data),
  validateResetToken: (token: string) =>
    api
      .get<{ message: string }>(endpoints.auth.validateResetToken, { params: { token } })
      .then((response) => response.data),
  resetPassword: (payload: ResetPasswordPayload) =>
    api.post(endpoints.auth.resetPassword, payload).then((response) => response.data),
  updateProfile: (payload: UpdateProfilePayload) =>
    api.patch<UserRead>(endpoints.auth.me, payload).then((response) => response.data),
  changePassword: (payload: ChangePasswordPayload) =>
    api.post<Token>(endpoints.auth.changePassword, payload).then((response) => response.data),
    async uploadAvatar(file: File): Promise<{ avatar_url: string }> {
    const formData = new FormData();
    formData.append("avatar", file);
    const { data } = await api.post<{ avatar_url: string }>("/api/v1/auth/me/avatar", formData);
    return data;
  },

  async deleteAvatar(): Promise<void> {
    await api.delete("/api/v1/auth/me/avatar");
  },

  /** Suppression de compte (RGPD) : anonymisation côté serveur. */
  async deleteAccount(): Promise<void> {
    await api.delete(endpoints.auth.me);
  },
};