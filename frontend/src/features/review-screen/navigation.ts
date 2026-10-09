// `j` / `k` on the review screen: next / previous invoice in the inbox list the user came from.
//
// How the list is found (kept simple on purpose):
// 1. The inbox links to a review with `?from=<list params>`, the `GET /documents` query of the
//    list it shows as one URL-encoded string (features/inbox/listParams `serializeFrom`). When the route has `from`,
//    the list is that query's cached page (`queryKeys.documents.list(params)`), or, if nothing is
//    cached, it is fetched once with those params.
// 2. Without `from`, the most recently fetched cached list that contains this invoice is used;
//    if there is none, `GET /documents` with no filter (the inbox's "All" order).
// Only the list's first page (25 invoices) is walked; at either end it wraps around.
import type { QueryClient } from "@tanstack/vue-query";

import { api, unwrap } from "../../api/client";
import { type DocumentListParams, queryKeys } from "../../api/query";
import type { components } from "../../api/schema";
import { parseFrom } from "../inbox/listParams";

type DocumentPage = components["schemas"]["DocumentPage"];
type DocumentSummary = components["schemas"]["DocumentSummary"];

/** The `from` query value → list params (the inbox's `parseFrom`), or null when there is none. */
export function decodeFrom(from: unknown): DocumentListParams | null {
  const value = Array.isArray(from) ? from[0] : from;
  return typeof value === "string" ? parseFrom(value) : null;
}

export interface Neighbour {
  document: DocumentSummary;
  /** The step went past the end (or start) of the list and came round. */
  wrapped: boolean;
}

/** The next (`step` 1) or previous (`step` −1) invoice after `id`, or null if there is none. */
export function neighbour(
  list: readonly DocumentSummary[],
  id: string,
  step: 1 | -1,
): Neighbour | null {
  const others = list.filter((item) => item.id !== id);
  if (others.length === 0) return null;
  const index = list.findIndex((item) => item.id === id);
  if (index === -1) {
    // This invoice left the list (for example after approval): start from the near end.
    const document = step === 1 ? list[0] : list[list.length - 1];
    return document ? { document, wrapped: false } : null;
  }
  const target = index + step;
  const wrapped = target < 0 || target >= list.length;
  const document = list[(target + list.length) % list.length];
  return document ? { document, wrapped } : null;
}

function cachedListContaining(
  queryClient: QueryClient,
  id: string,
): DocumentSummary[] | null {
  const lists = queryClient
    .getQueryCache()
    .findAll({ queryKey: queryKeys.documents.all() })
    .filter((query) => query.queryKey[1] === "list" && query.state.data)
    .sort((a, b) => b.state.dataUpdatedAt - a.state.dataUpdatedAt);
  for (const query of lists) {
    const page = query.state.data as DocumentPage;
    if (
      Array.isArray(page.results) &&
      page.results.some((item) => item.id === id)
    ) {
      return page.results;
    }
  }
  return null;
}

async function fetchList(
  queryClient: QueryClient,
  params: DocumentListParams,
): Promise<DocumentSummary[]> {
  const page = await queryClient.fetchQuery({
    queryKey: queryKeys.documents.list(params),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/documents", { params: { query: params } })),
  });
  return page.results;
}

/** The list `j` / `k` walk through (see the comment at the top of this file). */
export async function inboxList(
  queryClient: QueryClient,
  id: string,
  from: unknown,
): Promise<DocumentSummary[]> {
  const params = decodeFrom(from);
  if (params) {
    const cached = queryClient.getQueryData<DocumentPage>(
      queryKeys.documents.list(params),
    );
    return cached?.results ?? fetchList(queryClient, params);
  }
  return cachedListContaining(queryClient, id) ?? fetchList(queryClient, {});
}

/** The toast after `j` / `k` (design: "Next: Elektro Kessler GmbH, RE-2026-0412"). */
export function stepMessage(target: Neighbour, step: 1 | -1): string {
  const { document } = target;
  const name = [document.supplier_name, document.invoice_number]
    .filter(Boolean)
    .join(", ");
  const label = name || document.original_filename;
  const head = step === 1 ? "Next" : "Previous";
  if (!target.wrapped) return `${head}: ${label}`;
  return step === 1
    ? `Back to the start of the list. ${head}: ${label}`
    : `Back to the end of the list. ${head}: ${label}`;
}

/** True while the user types in a field: `j` and `k` are letters then, not shortcuts. */
export function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  return ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}
