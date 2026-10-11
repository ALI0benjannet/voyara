import { z } from "zod";

export const passwordSchema = z
  .string()
  .min(8, "auth.password.min")
  .max(128, "auth.password.max")
  .regex(/[A-Z]/, "auth.password.upper")
  .regex(/[a-z]/, "auth.password.lower")
  .regex(/[0-9]/, "auth.password.digit")
  .regex(/[^A-Za-z0-9]/, "auth.password.special");

export const registerSchema = z
  .object({
    prenom: z.string().trim().min(2, "auth.name.min").max(100, "auth.name.max"),
    nom: z.string().trim().min(2, "auth.name.min").max(100, "auth.name.max"),
    email: z.string().trim().email("auth.email.invalid"),
    password: passwordSchema,
    confirm: z.string().trim(),
  })
  .refine((data) => data.password === data.confirm, {
    path: ["confirm"],
    message: "auth.password.mismatch",
  });

export const loginSchema = z.object({
  email: z.string().trim().email("auth.email.invalid"),
  password: z.string().min(1, "auth.password.required"),
});

export const forgotPasswordSchema = z.object({
  email: z.string().trim().email("auth.email.invalid"),
});

export const resetPasswordSchema = z
  .object({
    new_password: passwordSchema,
    confirm_password: z.string().trim(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    path: ["confirm_password"],
    message: "auth.password.mismatch",
  });

export const updateProfileSchema = z.object({
  nom: z.string().trim().min(2, "auth.name.min").max(100, "auth.name.max"),
  prenom: z.string().trim().min(2, "auth.name.min").max(100, "auth.name.max"),
});

export const changePasswordSchema = z
  .object({
    old_password: z.string().min(1, "auth.password.required"),
    new_password: passwordSchema,
    confirm_new_password: z.string().trim(),
  })
  .refine((data) => data.new_password === data.confirm_new_password, {
    path: ["confirm_new_password"],
    message: "auth.password.mismatch",
  })
  .refine((data) => data.new_password !== data.old_password, {
    path: ["new_password"],
    message: "auth.password.same_as_old",
  });

export const verifyEmailSchema = z.object({
  email: z.string().trim().email("auth.email.invalid"),
  token: z.string().trim().regex(/^[0-9]{4}$/, "auth.token.invalid"),
});

export const verifyCodeSchema = z.object({
  code: z.string()
    .trim()
    .regex(/^[0-9]{4}$/, "auth.token.invalid"),
});

export const forgotSchema = forgotPasswordSchema;
export const resetSchema = resetPasswordSchema;
export const profileSchema = updateProfileSchema;

export type RegisterInput = z.infer<typeof registerSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type ForgotPasswordInput = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordInput = z.infer<typeof resetPasswordSchema>;
export type UpdateProfileInput = z.infer<typeof updateProfileSchema>;
export type ChangePasswordInput = z.infer<typeof changePasswordSchema>;
export type VerifyEmailInput = z.infer<typeof verifyEmailSchema>;
export type VerifyCodeInput = z.infer<typeof verifyCodeSchema>;
export type ForgotInput = ForgotPasswordInput;
export type ResetInput = ResetPasswordInput;
export type ProfileInput = UpdateProfileInput;