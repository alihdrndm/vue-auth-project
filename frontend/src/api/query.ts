import { QueryClient } from "@tanstack/vue-query";

import { ApiError } from "./client";
import type { operations } from "./schema";

/** Client errors (4xx) are final; network failures and 5xx get one more try. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 1;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: shouldRetry,
        // Polling stops while the browser tab is hidden.
        refetchIntervalInBackground: false,
        refetchOnWindowFocus: true,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export type DocumentListParams = NonNullable<
  operations["api_v1_documents_list"]["parameters"]["query"]
>;
export type SupplierListParams = NonNullable<
  operations["api_v1_suppliers_list"]["parameters"]["query"]
>;

/** Query keys for every endpoint the app reads. Invalidate a whole group with its first element. */
export const queryKeys = {
  me: () => ["me"] as const,
  stats: () => ["stats"] as const,
  documents: {
    all: () => ["documents"] as const,
    list: (params: DocumentListParams = {}) =>
      ["documents", "list", params] as const,
    detail: (id: string) => ["documents", "detail", id] as const,
    text: (id: string) => ["documents", "detail", id, "text"] as const,
    xml: (id: string) => ["documents", "detail", id, "xml"] as const,
    file: (id: string) => ["documents", "detail", id, "file"] as const,
    visualization: (id: string) =>
      ["documents", "detail", id, "visualization"] as const,
  },
  suppliers: {
    all: () => ["suppliers"] as const,
    list: (params: SupplierListParams = {}) =>
      ["suppliers", "list", params] as const,
    detail: (id: string) => ["suppliers", "detail", id] as const,
    /** Every supplier (all pages), for filter menus. */
    options: () => ["suppliers", "options"] as const,
  },
  exports: () => ["exports"] as const,
  /** One page of `GET /exports`. */
  exportsPage: (page: number) => ["exports", "list", page] as const,
  organization: () => ["organization"] as const,
  members: () => ["members"] as const,
  /** One page of `GET /members`. */
  membersPage: (page: number) => ["members", "list", page] as const,
  accuracy: () => ["accuracy"] as const,
  rule: (ruleId: string) => ["rules", ruleId] as const,
};
