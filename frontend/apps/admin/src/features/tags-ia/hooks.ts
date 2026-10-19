import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { toApiError } from "@voyara/api";

import { tagsIaApi, type TagsParams, type TagsPayload } from "./api";

export const tagsIaKeys = {
  all: ["tags-ia"] as const,
  list: (params: TagsParams) => [...tagsIaKeys.all, "list", params] as const,
  stats: () => [...tagsIaKeys.all, "stats"] as const,
};

export function useTagsList(params: TagsParams) {
  return useQuery({
    queryKey: tagsIaKeys.list(params),
    queryFn: () => tagsIaApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useTagsStats() {
  return useQuery({ queryKey: tagsIaKeys.stats(), queryFn: tagsIaApi.stats });
}

export function useSaveTags() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: TagsPayload }) =>
      tagsIaApi.save(id, payload),
    onSuccess: (_data, { payload }) => {
      toast.success(t(payload.tags_valides ? "admin.tagsIa.validatedToast" : "admin.tagsIa.savedToast"));
      queryClient.invalidateQueries({ queryKey: tagsIaKeys.all });
    },
    onError: (error) => {
      const { message } = toApiError(error);
      toast.error(message.startsWith("errors.") ? t("admin.tagsIa.errorToast") : message);
    },
  });
}
