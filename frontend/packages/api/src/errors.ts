import { AxiosError } from "axios";

export type ApiError = {
  status: number;
  message: string;
  fieldErrors?: Record<string, string>;
};

export function toApiError(error: unknown): ApiError {
  if (error instanceof AxiosError) {
    const status = error.response?.status ?? 0;
    const data = error.response?.data as { detail?: unknown } | undefined;

    if (status === 422 && Array.isArray((data as { detail?: unknown })?.detail)) {
      const fieldErrors: Record<string, string> = {};
      for (const item of (data?.detail as Array<{ loc?: unknown[]; msg?: string }>)) {
        const field = item.loc?.filter((l) => l !== "body").join(".");
        if (field && item.msg) fieldErrors[field] = item.msg;
      }
      return { status, message: "errors.validation", fieldErrors };
    }

    if (typeof data?.detail === "string") return { status, message: data.detail };
    if (status === 0) return { status, message: "errors.network" };
    return { status, message: "errors.unexpected" };
  }

  return { status: 0, message: "errors.unexpected" };
}
