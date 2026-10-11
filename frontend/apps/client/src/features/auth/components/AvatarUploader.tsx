import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Camera, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { Avatar } from "@voyara/ui/components/ui/avatar";
import { Button } from "@voyara/ui/components/ui/button";

const MAX_SIZE = 2 * 1024 * 1024; // 2 Mo
const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];

type Props = {
  currentUrl?: string | null;
  name?: string | null;
  email?: string | null;
  onUpload: (file: File) => Promise<void>;
  onRemove?: () => Promise<void>;
};

export function AvatarUploader({ currentUrl, name, email, onUpload, onRemove }: Props) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // libère l'URL objet pour éviter les fuites mémoire
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );

  const handleFile = async (file?: File) => {
    if (!file) return;

    if (!ACCEPTED.includes(file.type)) {
      toast.error(t("auth.profile.avatar_type_error", "Format non supporté (JPG, PNG ou WebP)."));
      return;
    }
    if (file.size > MAX_SIZE) {
      toast.error(t("auth.profile.avatar_size_error", "L’image ne doit pas dépasser 2 Mo."));
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreview(objectUrl);
    setBusy(true);
    try {
      await onUpload(file);
      toast.success(t("auth.profile.avatar_success", "Photo de profil mise à jour."));
    } catch {
      setPreview(null);
      toast.error(t("auth.profile.avatar_error", "Échec de l’envoi de la photo."));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleRemove = async () => {
    if (!onRemove) return;
    setBusy(true);
    try {
      await onRemove();
      setPreview(null);
      toast.success(t("auth.profile.avatar_removed", "Photo supprimée."));
    } catch {
      toast.error(t("errors.unexpected"));
    } finally {
      setBusy(false);
    }
  };

  const src = preview ?? currentUrl ?? null;

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
      <div className="relative">
        <Avatar
          src={src}
          name={name}
          email={email}
          size="xl"
          className="shadow-lg ring-4 ring-white"
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          aria-label={t("auth.profile.change_photo", "Changer la photo")}
          className="bg-primary hover:bg-primary-hover focus-visible:ring-ring absolute -end-1 -bottom-1 grid size-9 place-items-center rounded-full text-white shadow-md transition focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:opacity-60"
        >
          <Camera aria-hidden className="size-4" />
        </button>
      </div>

      <div className="space-y-2 text-center sm:text-start">
        <p className="text-foreground text-sm font-medium">
          {t("auth.profile.photo", "Photo de profil")}
        </p>
        <p className="text-muted-foreground text-xs">
          {t("auth.profile.photo_hint", "JPG, PNG ou WebP — 2 Mo maximum.")}
        </p>

        <div className="flex flex-wrap justify-center gap-2 sm:justify-start">
          <Button
            size="sm"
            variant="secondary"
            loading={busy}
            leftIcon={<Upload className="size-4" />}
            onClick={() => inputRef.current?.click()}
          >
            {t("auth.profile.upload", "Téléverser")}
          </Button>

          {src && onRemove && (
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              leftIcon={<Trash2 className="size-4" />}
              onClick={handleRemove}
              className="text-red-600 hover:bg-red-50"
            >
              {t("auth.profile.remove", "Supprimer")}
            </Button>
          )}
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(",")}
        className="sr-only"
        onChange={(e) => void handleFile(e.target.files?.[0])}
      />
    </div>
  );
}
