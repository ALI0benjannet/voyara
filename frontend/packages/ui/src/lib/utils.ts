import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getInitials(name?: string | null, email?: string | null) {
  const source = name?.trim() || email?.split("@")[0] || "";
  const parts = source.split(/[\s._-]+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const firstPart = parts[0]!;
  if (parts.length === 1) return firstPart.slice(0, 2).toUpperCase();
  const secondPart = parts[1]!;
  return ((firstPart[0] ?? "") + (secondPart[0] ?? "")).toUpperCase();
}