import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { toApiError } from "@voyara/api/errors";
import i18n from "@voyara/i18n";

const notify = (error: unknown) => {
  const { status, message } = toApiError(error);
  if (status === 401 || status === 422) return; // gérés localement
  toast.error(i18n.t(message, { defaultValue: i18n.t("errors.unknown") }));
};

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    // On n'alerte que si des données étaient déjà affichées (refetch raté)
    onError: (error, query) => { if (query.state.data !== undefined) notify(error); },
  }),
  mutationCache: new MutationCache({
    onError: (error, _v, _c, mutation) => { if (!mutation.options.onError) notify(error); },
  }),
  defaultOptions: { /* …comme à l'étape 6… */ },
});