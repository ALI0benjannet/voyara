import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";

import { useCategories, useCategoryMutations } from "@/features/catalog/hooks";

export default function CategoriesPage() {
  const { t } = useTranslation();
  const { data: categories, isLoading } = useCategories();
  const { create, rename, remove } = useCategoryMutations();

  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

  const submitNew = (event: FormEvent) => {
    event.preventDefault();
    const nom = newName.trim();
    if (nom.length < 2) return;
    create.mutate(nom, { onSuccess: () => setNewName("") });
  };

  const startEdit = (id: number, nom: string) => {
    setEditingId(id);
    setEditName(nom);
  };

  const submitEdit = (id: number) => {
    const nom = editName.trim();
    if (nom.length < 2) return;
    rename.mutate({ id, nom }, { onSuccess: () => setEditingId(null) });
  };

  const confirmDelete = (id: number, nom: string) => {
    if (window.confirm(t("admin.categories.deleteConfirmNamed", { name: nom }))) remove.mutate(id);
  };

  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl font-semibold">{t("admin.categories.title")}</h1>

      {/* Ajout */}
      <form onSubmit={submitNew} className="flex max-w-md gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={t("admin.categories.placeholder")}
          className="border-input bg-card min-w-0 flex-1 rounded-md border px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={create.isPending || newName.trim().length < 2}
          className="bg-primary inline-flex items-center gap-1.5 rounded-md px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          <Plus className="size-4" />
          {t("admin.categories.add")}
        </button>
      </form>

      {/* Liste */}
      <div className="bg-card max-w-2xl rounded-lg border">
        {isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-muted h-10 animate-pulse rounded" />
            ))}
          </div>
        ) : (categories ?? []).length === 0 ? (
          <p className="text-muted-foreground p-6 text-center text-sm">
            {t("admin.categories.empty")}
          </p>
        ) : (
          <ul className="divide-border divide-y">
            {(categories ?? []).map((cat) => (
              <li key={cat.id} className="flex items-center gap-3 px-4 py-2.5">
                {editingId === cat.id ? (
                  <>
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter") submitEdit(cat.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                      className="border-input bg-card focus:border-primary min-w-0 flex-1 rounded-md border px-3 py-1.5 text-sm focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => submitEdit(cat.id)}
                      className="text-primary hover:bg-primary/10 rounded-md p-1.5"
                      aria-label={t("admin.common.validate")}
                    >
                      <Check className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingId(null)}
                      className="text-muted-foreground hover:bg-muted rounded-md p-1.5"
                      aria-label={t("admin.common.cancel")}
                    >
                      <X className="size-4" />
                    </button>
                  </>
                ) : (
                  <>
                    <span className="flex-1 text-sm font-medium">{cat.nom}</span>
                    <button
                      type="button"
                      onClick={() => startEdit(cat.id, cat.nom)}
                      className="text-muted-foreground hover:bg-muted hover:text-foreground rounded-md p-1.5"
                      aria-label={t("admin.categories.rename", { name: cat.nom })}
                    >
                      <Pencil className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => confirmDelete(cat.id, cat.nom)}
                      className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive rounded-md p-1.5"
                      aria-label={t("admin.categories.deleteAria", { name: cat.nom })}
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="text-muted-foreground text-xs">
        Une catégorie utilisée par des activités ne peut pas être supprimée.
      </p>
    </div>
  );
}
