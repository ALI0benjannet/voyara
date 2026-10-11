import { useState } from "react";
import { cn, getInitials } from "@voyara/ui/lib/utils";

type AvatarProps = {
  src?: string | null;
  name?: string | null;
  email?: string | null;
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
};

const sizes = {
  sm: "size-8 text-xs",
  md: "size-10 text-sm",
  lg: "size-16 text-lg",
  xl: "size-24 text-2xl",
} as const;

export function Avatar({ src, name, email, size = "md", className }: AvatarProps) {
  const [broken, setBroken] = useState(false);
  const showImage = Boolean(src) && !broken;

  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full",
        "from-secondary to-muted text-foreground/85 ring-ring/5 bg-gradient-to-br font-semibold ring-1",
        sizes[size],
        className,
      )}
    >
      {showImage ? (
        <img
          src={src as string}
          alt={name ?? email ?? "Avatar"}
          onError={() => setBroken(true)}
          className="size-full object-cover"
        />
      ) : (
        <span aria-hidden>{getInitials(name, email)}</span>
      )}
    </span>
  );
}
