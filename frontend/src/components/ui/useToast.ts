import { computed, type ComputedRef, ref } from "vue";

export type ToastKind = "success" | "info" | "error" | "rate-limit";

export interface ToastAction {
  label: string;
  run: () => void;
}

export interface ToastOptions {
  kind?: ToastKind;
  message: string;
  /** For example "Try again" on an error. */
  action?: ToastAction;
  /** Milliseconds before it leaves. Success and info default to 4 s; errors stay until dismissed. */
  duration?: number;
}

export interface ToastState {
  id: number;
  kind: ToastKind;
  message: string;
  action?: ToastAction;
}

export const TOAST_DURATION_MS = 4000;

// One toast at a time, shared by the whole app.
const current = ref<ToastState | null>(null);
let nextId = 1;
let timer: ReturnType<typeof setTimeout> | undefined;

function clearTimer(): void {
  if (timer !== undefined) {
    clearTimeout(timer);
    timer = undefined;
  }
}

function dismiss(): void {
  clearTimer();
  current.value = null;
}

function show(options: ToastOptions): number {
  clearTimer();
  const kind = options.kind ?? "success";
  const id = nextId;
  nextId += 1;
  current.value = {
    id,
    kind,
    message: options.message,
    action: options.action,
  };
  const stays = kind === "error" || kind === "rate-limit";
  const duration = options.duration ?? (stays ? undefined : TOAST_DURATION_MS);
  if (duration !== undefined) {
    timer = setTimeout(() => {
      if (current.value?.id === id) current.value = null;
      timer = undefined;
    }, duration);
  }
  return id;
}

const visible = computed(() => current.value);

export function useToast(): {
  toast: ComputedRef<ToastState | null>;
  show: (options: ToastOptions) => number;
  dismiss: () => void;
} {
  return { toast: visible, show, dismiss };
}
