import { forwardRef, useId } from "react";
import type { InputHTMLAttributes, ReactNode } from "react";

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: ReactNode;
  error?: string;
  hint?: ReactNode;
};

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField(
  { label, error, hint, className, ...props },
  ref,
) {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-foreground/85 block text-sm font-medium">
        {label}
      </label>

      <input
        {...props}
        id={id}
        ref={ref}
        aria-invalid={Boolean(error) || undefined}
        aria-errormessage={error ? errorId : undefined}
        aria-describedby={hint ? hintId : undefined}
        className={[
          "w-full rounded-xl border px-4 py-3 text-sm transition",
          "focus-visible:ring-ring focus:outline-none focus-visible:ring-2",
          "disabled:cursor-not-allowed disabled:opacity-60",
          error ? "border-red-500" : "border-border",
          className ?? "",
        ].join(" ")}
      />

      {hint && (
        <p id={hintId} className="text-muted-foreground text-xs">
          {hint}
        </p>
      )}

      {error && (
        <p id={errorId} role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
});
