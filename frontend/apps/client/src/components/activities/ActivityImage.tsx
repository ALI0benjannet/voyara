import { cn } from "@voyara/ui/lib/utils";

/** Photo de l'activité, ou placeholder dégradé (équivalent de l'image-slot du design).
 *
 *  `key={src}` + `decoding="async"` évitent que l'image soit redécodée à chaque
 *  re-render de l'arbre React — c'est ce qui la faisait « clignoter » puis
 *  réapparaître lentement au changement de langue. */
export function ActivityImage({
  src,
  label,
  className,
  priority = false,
}: {
  src?: string | null;
  label: string;
  className?: string;
  /** Image au-dessus de la ligne de flottaison (hero de la page détail) :
   *  chargée sans attendre, les autres en `lazy`. */
  priority?: boolean;
}) {
  if (src) {
    return (
      <img
        key={src}
        src={src}
        alt={label}
        loading={priority ? "eager" : "lazy"}
        decoding="async"
        fetchPriority={priority ? "high" : "auto"}
        className={cn("size-full object-cover", className)}
      />
    );
  }
  return (
    <div
      aria-hidden
      className={cn(
        "from-background to-secondary flex size-full items-center justify-center bg-gradient-to-br",
        className,
      )}
    >
      <span className="text-foreground/40 px-4 text-center text-sm font-medium">{label}</span>
    </div>
  );
}
