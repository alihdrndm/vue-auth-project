// The document actions of the review screen's status header. Which actions exist, and whether
// this user may run them, comes from the API's `allowed_actions`; the browser never decides.
import { ApiError } from "../../api/client";
import type { components } from "../../api/schema";
import type { IconName } from "../../components/ui/icons";

type AllowedAction = components["schemas"]["AllowedAction"];

export type DocumentAction =
  | "mark_reviewed"
  | "approve"
  | "reject"
  | "send_back"
  | "reopen"
  | "retry"
  | "delete";

/** The header's buttons, in this order. `edit_fields` and `resolve_check` live in their panels. */
export const ACTION_ORDER: DocumentAction[] = [
  "mark_reviewed",
  "approve",
  "reject",
  "send_back",
  "reopen",
  "retry",
  "delete",
];

export interface ActionLook {
  label: string;
  /** Label while the request runs. */
  busyLabel: string;
  variant: "primary" | "secondary" | "ghost" | "danger";
  icon?: IconName;
  /** Opens a dialog first (comment or confirmation). */
  dialog: boolean;
}

export const ACTION_LOOK: Record<DocumentAction, ActionLook> = {
  mark_reviewed: {
    label: "Mark reviewed",
    busyLabel: "Saving…",
    variant: "primary",
    dialog: false,
  },
  approve: {
    label: "Approve",
    busyLabel: "Approving…",
    variant: "primary",
    icon: "check",
    dialog: false,
  },
  reject: {
    label: "Reject…",
    busyLabel: "Rejecting…",
    variant: "danger",
    dialog: true,
  },
  send_back: {
    label: "Send back…",
    busyLabel: "Sending back…",
    variant: "secondary",
    dialog: true,
  },
  reopen: {
    label: "Reopen",
    busyLabel: "Reopening…",
    variant: "secondary",
    icon: "refresh",
    dialog: false,
  },
  retry: {
    label: "Retry",
    busyLabel: "Retrying…",
    variant: "secondary",
    icon: "refresh",
    dialog: false,
  },
  delete: {
    label: "Delete…",
    busyLabel: "Deleting…",
    variant: "ghost",
    dialog: true,
  },
};

export interface HeaderAction extends AllowedAction {
  action: DocumentAction;
}

/** The header actions present in `allowed_actions`, in the design's order. */
export function headerActions(
  allowed: readonly AllowedAction[],
): HeaderAction[] {
  return ACTION_ORDER.flatMap((name) => {
    const entry = allowed.find((item) => item.action === name);
    return entry ? [{ ...entry, action: name }] : [];
  });
}

/** True when `allowed_actions` has `name` and it is enabled. */
export function isEnabled(
  allowed: readonly AllowedAction[],
  name: string,
): boolean {
  return allowed.some((item) => item.action === name && item.enabled);
}

/** The success toast after an action ("You approved RE-2026-0412."). */
export function successMessage(action: DocumentAction, number: string): string {
  switch (action) {
    case "mark_reviewed":
      return "Marked reviewed. It goes to approval next.";
    case "approve":
      return `You approved ${number}.`;
    case "reject":
      return `You rejected ${number}.`;
    case "send_back":
      return `${number} is back in review.`;
    case "reopen":
      return `${number} is open for review again.`;
    case "retry":
      return `Processing ${number} again.`;
    case "delete":
      return `${number} was deleted.`;
  }
}

/** The error toast: the problem's title and detail; `BLOCKING_CHECKS` says how many remain. */
export function problemMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "BLOCKING_CHECKS") {
      const checks = error.extra.checks;
      if (Array.isArray(checks)) {
        const noun = checks.length === 1 ? "check" : "checks";
        return `${error.title}. Resolve ${checks.length} blocking ${noun} first.`;
      }
    }
    return error.detail ? `${error.title}. ${error.detail}` : error.title;
  }
  return "Something went wrong. Check your connection and try again.";
}
