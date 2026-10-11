export type UserRole = "tourist" | "admin";

export interface UserRead {
  id: number;
  email: string;
  nom: string;
  prenom: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  avatar_url: string | null;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  nom: string;
  prenom: string;
}

export interface RefreshPayload {
  refresh_token: string;
}

export interface ForgotPasswordPayload {
  email: string;
}

export interface ResetPasswordPayload {
  token: string;
  new_password: string;
}

export interface VerifyEmailPayload {
  email: string;
  token: string;
}

export interface ResendVerificationPayload {
  email: string;
}

export interface UpdateProfilePayload {
  nom?: string | null;
  prenom?: string | null;
  preferences?: string | null;
}

export interface ChangePasswordPayload {
  old_password: string;
  new_password: string;
  refresh_token: string;
}
