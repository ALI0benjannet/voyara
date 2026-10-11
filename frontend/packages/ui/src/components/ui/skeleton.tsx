import { cn } from "@voyara/ui/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("bg-input animate-pulse rounded-xl", className)} {...props} />;
}
