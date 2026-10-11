import axios, { AxiosError } from "axios";

export type AuthErrorCode =
  | "invalid_credentials"
  | "email_not_verified"
  | "email_already_exists"
  | "invalid_token"
  | "expired_token"
  | "rate_limited"
  | "not_admin"
  | "account_disabled"
  | "unknown";

export type ApiError = {
  status: number;
  message: string;
  fieldErrors?: Record<string, string>;
};

const normalizeAuthErrorCode = (code: string): AuthErrorCode => {
  const normalized = code.toLowerCase();
  const allowedCodes: AuthErrorCode[] = [
    "invalid_credentials",
    "email_not_verified",
    "email_already_exists",
    "invalid_token",
    "expired_token",
    "rate_limited",
    "not_admin",
    "account_disabled",
    "unknown",
  ];

  return allowedCodes.includes(normalized as AuthErrorCode)
    ? (normalized as AuthErrorCode)
    : "unknown";
};

export function getAuthErrorCode(error: unknown): AuthErrorCode {
  if (!axios.isAxiosError(error)) return "unknown";
  const status = error.response?.status;
  const data = error.response?.data as any;
  const code = data?.detail?.code ?? data?.code;

  if (typeof code === "string") {
    return normalizeAuthErrorCode(code);
  }

  if (status === 401) return "invalid_credentials";
  if (status === 403) {
    const detail = data?.detail;
    if (typeof detail === "string") {
      if (/désactivé|disabled/i.test(detail)) return "account_disabled";
      if (/confirmez|verify/i.test(detail)) return "email_not_verified";
    }
    return "unknown";
  }
  if (status === 409) return "email_already_exists";
  if (status === 429) return "rate_limited";
  if (status === 400 || status === 410) return "invalid_token";
  return "unknown";
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof AxiosError) {
    const status = error.response?.status ?? 0;
    const data = error.response?.data as any;

    // 422 Pydantic → map champ → message
    if (status === 422 && Array.isArray(data?.detail)) {
      const fieldErrors: Record<string, string> = {};
      for (const e of data.detail) {
        const field = e.loc?.filter((l: unknown) => l !== "body").join(".");
        if (field) fieldErrors[field] = e.msg;
      }
      return { status, message: "errors.validation", fieldErrors };
    }

    if (typeof data?.detail === "string") return { status, message: data.detail };
    if (status === 0) return { status, message: "errors.network" };
    return { status, message: "errors.unexpected" };
  }
  return { status: 0, message: "errors.unexpected" };
}