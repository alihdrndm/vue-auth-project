// The inbox's list state lives in the route query so links, back and forward work:
//   tab      needs_review (default) | awaiting_approval | approved | exported | failed | all
//   q        search text (the top bar search arrives here with tab=all)
//   supplier supplier id from GET /suppliers
//   format   exact format label
//   ordering -received_at (default, left out of the URL) | received_at | -gross_total | due_date
//   page     1-based, 25 per page (left out when 1)
// The same state becomes the GET /documents parameters, and is handed to the review screen
// as `from` so j/k can walk the same list (see `serializeFrom` / `parseFrom`).
import type { LocationQuery, LocationQueryRaw } from "vue-router";

import type { DocumentListParams } from "../../api/query";
import type { IconName } from "../../components/ui/icons";

export type InboxTab =
  | "needs_review"
  | "awaiting_approval"
  | "approved"
  | "exported"
  | "failed"
  | "all";

export type Ordering = NonNullable<DocumentListParams["ordering"]>;

export const DEFAULT_TAB: InboxTab = "needs_review";
export const DEFAULT_ORDERING: Ordering = "-received_at";
export const PAGE_SIZE = 25;

export const TABS: { key: InboxTab; label: string }[] = [
  { key: "needs_review", label: "Needs review" },
  { key: "awaiting_approval", label: "Awaiting approval" },
  { key: "approved", label: "Approved" },
  { key: "exported", label: "Exported" },
  { key: "failed", label: "Failed" },
  { key: "all", label: "All" },
];

/** Empty state per tab, verbatim from the design. */
export const EMPTY_COPY: Record<
  InboxTab,
  { icon: IconName; title: string; body: string }
> = {
  needs_review: {
    icon: "inbox",
    title: "Nothing needs review",
    body: "New invoices land here once their checks have run.",
  },
  awaiting_approval: {
    icon: "hourglass",
    title: "Nothing is waiting for approval",
    body: "Invoices arrive here once someone marks them reviewed.",
  },
  approved: {
    icon: "circle-check",
    title: "Nothing approved yet",
    body: "Approved invoices wait here until you export them.",
  },
  exported: {
    icon: "archive",
    title: "Nothing exported yet",
    body: "Approved invoices move here once you export them for the tax advisor.",
  },
  failed: {
    icon: "circle-alert",
    title: "No failed files",
    body: "Files that can’t be read at all show up here, with the reason.",
  },
  all: {
    icon: "inbox",
    title: "No invoices yet",
    body: "Upload invoices or drop them anywhere on this page.",
  },
};

export const NO_RESULTS_COPY = {
  icon: "search" as IconName,
  title: "No invoices match",
  body: "Nothing in this tab matches your search and filters.",
  action: "Clear search and filters",
};

const ORDERINGS: readonly Ordering[] = [
  "-received_at",
  "received_at",
  "-gross_total",
  "due_date",
];

export interface InboxState {
  tab: InboxTab;
  q: string;
  supplier: string;
  format: string;
  ordering: Ordering;
  page: number;
}

function first(value: LocationQuery[string] | undefined): string {
  const item = Array.isArray(value) ? value[0] : value;
  return typeof item === "string" ? item : "";
}

function isTab(value: string): value is InboxTab {
  return TABS.some((tab) => tab.key === value);
}

function isOrdering(value: string): value is Ordering {
  return (ORDERINGS as readonly string[]).includes(value);
}

/** Reads the inbox state from the route query; unknown values fall back to the defaults. */
export function stateFromQuery(query: LocationQuery): InboxState {
  const tab = first(query.tab);
  const ordering = first(query.ordering);
  const page = Number.parseInt(first(query.page), 10);
  return {
    tab: isTab(tab) ? tab : DEFAULT_TAB,
    q: first(query.q).trim(),
    supplier: first(query.supplier),
    format: first(query.format),
    ordering: isOrdering(ordering) ? ordering : DEFAULT_ORDERING,
    page: Number.isFinite(page) && page > 1 ? page : 1,
  };
}

/** The route query for a state, leaving out defaults so URLs stay short. */
export function queryFromState(state: InboxState): LocationQueryRaw {
  const query: LocationQueryRaw = { tab: state.tab };
  if (state.q) query.q = state.q;
  if (state.supplier) query.supplier = state.supplier;
  if (state.format) query.format = state.format;
  if (state.ordering !== DEFAULT_ORDERING) query.ordering = state.ordering;
  if (state.page > 1) query.page = String(state.page);
  return query;
}

/** The GET /documents parameters for a state. */
export function listParams(state: InboxState): DocumentListParams {
  const params: DocumentListParams = { ordering: state.ordering };
  if (state.tab !== "all") params.status = state.tab;
  if (state.q) params.q = state.q;
  if (state.supplier) params.supplier = state.supplier;
  if (state.format) params.format = state.format;
  if (state.page > 1) params.page = state.page;
  return params;
}

/** Search or a filter narrows the list (as opposed to the tab simply being empty). */
export function isFiltered(state: InboxState): boolean {
  return Boolean(state.q || state.supplier || state.format);
}

const STATUSES: readonly NonNullable<DocumentListParams["status"]>[] = [
  "received",
  "processing",
  "needs_review",
  "awaiting_approval",
  "approved",
  "rejected",
  "exported",
  "failed",
];

const KINDS: readonly NonNullable<DocumentListParams["kind"]>[] = [
  "xml",
  "hybrid_pdf",
  "legacy_zugferd1",
  "hybrid_pdf_unsupported",
  "pdf_text",
  "pdf_no_text",
];

const FROM_KEYS = [
  "status",
  "q",
  "supplier",
  "format",
  "einvoice",
  "kind",
  "ordering",
  "page",
] as const;

/**
 * The list parameters as one URL-encoded string, passed to the review screen as the route
 * query `from`, e.g. `status=needs_review&ordering=-received_at&page=2`.
 */
export function serializeFrom(params: DocumentListParams): string {
  const search = new URLSearchParams();
  for (const key of FROM_KEYS) {
    const value = params[key];
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  return search.toString();
}

/** Reads `from` back into GET /documents parameters; unknown keys and values are dropped. */
export function parseFrom(from: string): DocumentListParams {
  const search = new URLSearchParams(from);
  const params: DocumentListParams = {};
  const status = search.get("status");
  const knownStatus = STATUSES.find((item) => item === status);
  if (knownStatus) params.status = knownStatus;
  for (const key of ["q", "supplier", "format"] as const) {
    const value = search.get(key);
    if (value) params[key] = value;
  }
  const einvoice = search.get("einvoice");
  if (einvoice === "true" || einvoice === "false") params.einvoice = einvoice;
  const kind = KINDS.find((item) => item === search.get("kind"));
  if (kind) params.kind = kind;
  const ordering = search.get("ordering");
  if (ordering && isOrdering(ordering)) params.ordering = ordering;
  const page = Number.parseInt(search.get("page") ?? "", 10);
  if (Number.isFinite(page) && page > 1) params.page = page;
  return params;
}
