export type Role = "tourist" | "admin";

export type User = {
  id: string;
  email: string;
  full_name: string;
  nom: string;
  prenom: string;
  role: Role;
  is_verified: boolean;
  preferred_language?: string;
  phone?: string | null;
  avatar_url?: string | null;
};