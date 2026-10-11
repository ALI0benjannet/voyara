import {
  type ReactNode,
  type ReactElement,
  cloneElement,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type ReactMouseEvent<T = Element> = import("react").MouseEvent<T>;

type DropdownMenuContextValue = {
  open: boolean;
  toggleOpen: () => void;
  close: () => void;
};

const DropdownMenuContext = createContext<DropdownMenuContextValue | null>(null);

function useDropdownMenu() {
  const context = useContext(DropdownMenuContext);
  if (!context) {
    throw new Error("DropdownMenu components must be used inside DropdownMenu");
  }
  return context;
}

export function DropdownMenu({
  children,
  openOnHover = false,
  hoverCloseDelay = 180,
}: {
  children: ReactNode;
  /** Ouvre le menu au survol (le clic reste actif : tactile et clavier). */
  openOnHover?: boolean;
  /** Délai de grâce avant fermeture, le temps de traverser l'espace
   *  entre le déclencheur et le menu sans qu'il disparaisse. */
  hoverCloseDelay?: number;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const onClickOutside = (event: Event) => {
      if (!ref.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  // Évite qu'un minuteur en attente ferme un menu déjà démonté.
  useEffect(() => () => void (closeTimer.current && clearTimeout(closeTimer.current)), []);

  const cancelClose = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const value = useMemo(
    () => ({
      open,
      toggleOpen: () => setOpen((prev) => !prev),
      close: () => setOpen(false),
    }),
    [open],
  );

  // Le survol n'a de sens qu'avec une souris : sur mobile, `mouseenter` est
  // émis au tap et rendrait le menu impossible à fermer.
  const hoverHandlers = openOnHover
    ? {
        onMouseEnter: () => {
          cancelClose();
          setOpen(true);
        },
        onMouseLeave: () => {
          cancelClose();
          closeTimer.current = setTimeout(() => setOpen(false), hoverCloseDelay);
        },
        // Ouvre aussi à la tabulation, et ferme quand le focus quitte le menu.
        onFocus: () => {
          cancelClose();
          setOpen(true);
        },
        onBlur: (event: import("react").FocusEvent<HTMLDivElement>) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node)) {
            setOpen(false);
          }
        },
      }
    : {};

  return (
    <DropdownMenuContext.Provider value={value}>
      <div ref={ref} className="relative inline-block text-left" {...hoverHandlers}>
        {children}
      </div>
    </DropdownMenuContext.Provider>
  );
}

export function DropdownMenuTrigger({
  children,
  asChild,
}: {
  children: ReactNode;
  asChild?: boolean;
}) {
  const { toggleOpen } = useDropdownMenu();

  if (asChild && typeof children !== "string" && isReactElement(children)) {
    const child = children as ReactElement<{
      onClick?: (event: ReactMouseEvent<HTMLElement>) => void;
    }>;

    return cloneElement(child, {
      onClick: (event: ReactMouseEvent<HTMLElement>) => {
        child.props.onClick?.(event);
        toggleOpen();
      },
    });
  }

  return (
    <button type="button" onClick={toggleOpen} className="inline-flex items-center">
      {children}
    </button>
  );
}

export function DropdownMenuContent({
  children,
  align = "end",
}: {
  children: ReactNode;
  align?: "end" | "start";
}) {
  const { open } = useDropdownMenu();
  if (!open) return null;

  return (
    <div className={`absolute top-full z-20 w-56 pt-2 ${align === "end" ? "right-0" : "left-0"}`}>
      {/* Le `pt-2` du conteneur fait pont : sans lui, l'espace entre le
          déclencheur et le panneau coupe le survol et le menu se referme. */}
      <div className="bg-card rounded-2xl border p-2 shadow-lg">{children}</div>
    </div>
  );
}

export function DropdownMenuItem({
  children,
  className,
  onSelect,
}: {
  children: ReactNode;
  className?: string;
  onSelect?: () => void;
}) {
  const { close } = useDropdownMenu();

  const handleSelect = () => {
    onSelect?.();
    close();
  };

  return (
    <button
      type="button"
      className={`hover:bg-muted w-full rounded-xl px-3 py-2 text-left text-sm transition ${className ?? ""}`}
      onClick={handleSelect}
    >
      {children}
    </button>
  );
}

function isReactElement(value: unknown): value is ReactElement {
  return typeof value === "object" && value !== null && "type" in value && "props" in value;
}
