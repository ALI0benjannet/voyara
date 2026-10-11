import { Loader2 } from "lucide-react";

export function FullPageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Loader2 className="text-foreground size-8 animate-spin" />
    </div>
  );
}
