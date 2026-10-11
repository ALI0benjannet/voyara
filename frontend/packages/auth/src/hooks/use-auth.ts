import { useContext } from "react";
import { AuthContext } from "@voyara/auth/context/AuthProvider";

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside AuthProvider");
  return auth;
}