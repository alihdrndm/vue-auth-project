<script lang="ts">
import type { IconName } from "../ui/icons";

export type NavKey =
  "inbox" | "approvals" | "suppliers" | "exports" | "accuracy" | "settings";

export interface NavItem {
  key: NavKey;
  label: string;
  icon: IconName;
  to: string;
}

export const NAV_ITEMS: NavItem[] = [
  { key: "inbox", label: "Inbox", icon: "inbox", to: "/app/inbox" },
  {
    key: "approvals",
    label: "Approvals",
    icon: "check-check",
    to: "/app/approvals",
  },
  {
    key: "suppliers",
    label: "Suppliers",
    icon: "building",
    to: "/app/suppliers",
  },
  { key: "exports", label: "Exports", icon: "archive", to: "/app/exports" },
  { key: "accuracy", label: "Accuracy", icon: "gauge", to: "/app/accuracy" },
  { key: "settings", label: "Settings", icon: "sliders", to: "/app/settings" },
];

/** The phone tab bar shows the first four; More opens Accuracy and Settings. */
const TAB_BAR_KEYS: NavKey[] = ["inbox", "approvals", "suppliers", "exports"];
export const TAB_BAR_ITEMS = NAV_ITEMS.filter((item) =>
  TAB_BAR_KEYS.includes(item.key),
);
export const MORE_ITEMS = NAV_ITEMS.filter(
  (item) => !TAB_BAR_KEYS.includes(item.key),
);

/** Which nav item a path belongs to. Invoice pages belong to the Inbox. */
export function navKeyForPath(path: string): NavKey | undefined {
  if (path.startsWith("/app/invoices")) return "inbox";
  return NAV_ITEMS.find(
    (item) => path === item.to || path.startsWith(`${item.to}/`),
  )?.key;
}
</script>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useId,
  watch,
} from "vue";
import { RouterLink, useRoute } from "vue-router";

import Badge from "../ui/Badge.vue";
import Icon from "../ui/Icon.vue";
import Stamp from "../ui/Stamp.vue";

const props = withDefaults(
  defineProps<{
    /** The organisation's name, shown next to the wordmark. */
    orgName: string;
    /** Hours until the sandbox is deleted; shows "Sandbox, <n> h left" (sandbox only). */
    sandboxHoursLeft?: number;
    /** Counts shown next to nav items, e.g. invoices awaiting approval. */
    counts?: Partial<Record<NavKey, number>>;
    /** Overrides the active nav item derived from the route. */
    activeItem?: NavKey;
    /** The page title shown in the phone header. */
    phoneTitle?: string;
    searchLabel?: string;
    searchPlaceholder?: string;
  }>(),
  {
    sandboxHoursLeft: undefined,
    counts: () => ({}),
    activeItem: undefined,
    phoneTitle: undefined,
    searchLabel: "Search invoices",
    searchPlaceholder: "Search suppliers and numbers",
  },
);

const emit = defineEmits<{ search: [query: string] }>();

defineSlots<{
  default?: () => unknown;
  /** The sandbox banner (Inbox and Settings only). */
  banner?: () => unknown;
  /** The user menu button at the right of the top bar. */
  "user-menu"?: () => unknown;
  /** Icon buttons in the phone header, e.g. Upload. */
  "phone-actions"?: () => unknown;
}>();

const route = useRoute();
const active = computed(() => props.activeItem ?? navKeyForPath(route.path));

// Search: "/" focuses it from anywhere outside a text field; Esc leaves it.
const query = ref("");
const searchFocused = ref(false);
const searchRef = ref<HTMLInputElement | null>(null);

function onSearchInput(): void {
  emit("search", query.value);
}

function clearSearch(): void {
  query.value = "";
  emit("search", "");
  searchRef.value?.focus();
}

function onSearchKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    searchRef.value?.blur();
  }
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement
  );
}

function onGlobalKeydown(event: KeyboardEvent): void {
  if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey)
    return;
  if (isTyping(event.target)) return;
  event.preventDefault();
  searchRef.value?.focus();
}

// Phone: More opens Accuracy and Settings.
const moreId = useId();
const moreOpen = ref(false);
const moreButtonRef = ref<HTMLButtonElement | null>(null);
const moreActive = computed(() =>
  MORE_ITEMS.some((item) => item.key === active.value),
);

function toggleMore(): void {
  moreOpen.value = !moreOpen.value;
}

async function closeMore(returnFocus: boolean): Promise<void> {
  if (!moreOpen.value) return;
  moreOpen.value = false;
  if (returnFocus) {
    await nextTick();
    moreButtonRef.value?.focus();
  }
}

function onMoreKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    void closeMore(true);
  }
}

function onDocumentClick(event: MouseEvent): void {
  if (!moreOpen.value) return;
  const target = event.target;
  if (target instanceof Element && target.closest(".tabbar-more")) return;
  void closeMore(false);
}

watch(
  () => route.fullPath,
  () => {
    moreOpen.value = false;
  },
);

onMounted(() => {
  window.addEventListener("keydown", onGlobalKeydown);
  document.addEventListener("click", onDocumentClick);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onGlobalKeydown);
  document.removeEventListener("click", onDocumentClick);
});
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <Stamp
          class="brand-mark brand-mark--wide"
          size="mark"
          :mark-size="24"
        />
        <Stamp
          class="brand-mark brand-mark--phone"
          size="mark"
          :mark-size="28"
        />
        <span class="wordmark">Eingang</span>
      </div>
      <span class="org-sep" aria-hidden="true">/</span>
      <span class="org">{{ orgName }}</span>
      <label class="search" :class="{ 'is-focused': searchFocused }">
        <Icon name="search" />
        <input
          ref="searchRef"
          v-model="query"
          class="search-input"
          type="search"
          :aria-label="searchLabel"
          :placeholder="searchPlaceholder"
          @input="onSearchInput"
          @keydown="onSearchKeydown"
          @focus="searchFocused = true"
          @blur="searchFocused = false"
        />
        <button
          v-if="query"
          type="button"
          class="search-clear"
          aria-label="Clear search"
          @click="clearSearch"
        >
          <Icon name="x" :size="14" />
        </button>
        <kbd v-else class="search-kbd" :class="{ 'is-wide': searchFocused }">{{
          searchFocused ? "Esc" : "/"
        }}</kbd>
      </label>
      <span v-if="phoneTitle" class="phone-title" aria-hidden="true">{{
        phoneTitle
      }}</span>
      <span class="spacer" />
      <span v-if="sandboxHoursLeft !== undefined" class="sandbox-chip">
        <Icon name="clock" :size="14" />Sandbox, {{ sandboxHoursLeft }} h left
      </span>
      <span v-if="$slots['phone-actions']" class="phone-actions"
        ><slot name="phone-actions"
      /></span>
      <slot name="user-menu" />
    </header>

    <div class="body">
      <nav class="rail" aria-label="Main">
        <RouterLink
          v-for="item in NAV_ITEMS"
          :key="item.key"
          v-slot="{ href, navigate }"
          :to="item.to"
          custom
        >
          <a
            :href="href"
            class="rail-item"
            :class="{ 'is-active': active === item.key }"
            :aria-current="active === item.key ? 'page' : undefined"
            :title="item.label"
            @click="navigate"
          >
            <span class="rail-icon">
              <Icon :name="item.icon" :size="20" />
              <Badge v-if="counts[item.key] !== undefined" class="rail-count">{{
                counts[item.key]
              }}</Badge>
            </span>
            <span class="rail-label">{{ item.label }}</span>
          </a>
        </RouterLink>
      </nav>

      <main class="main">
        <slot name="banner" />
        <div class="page"><slot /></div>
      </main>
    </div>

    <nav class="tabbar" aria-label="Main">
      <RouterLink
        v-for="item in TAB_BAR_ITEMS"
        :key="item.key"
        v-slot="{ href, navigate }"
        :to="item.to"
        custom
      >
        <a
          :href="href"
          class="tabbar-item"
          :class="{ 'is-active': active === item.key }"
          :aria-current="active === item.key ? 'page' : undefined"
          @click="navigate"
        >
          <span class="tabbar-icon">
            <Icon :name="item.icon" :size="20" />
            <Badge v-if="counts[item.key] !== undefined" class="rail-count">{{
              counts[item.key]
            }}</Badge>
          </span>
          {{ item.label }}
        </a>
      </RouterLink>
      <div class="tabbar-more" @keydown="onMoreKeydown">
        <button
          ref="moreButtonRef"
          type="button"
          class="tabbar-item"
          :class="{ 'is-active': moreActive }"
          :aria-expanded="moreOpen ? 'true' : 'false'"
          :aria-controls="moreId"
          @click="toggleMore"
        >
          <span class="tabbar-icon"><Icon name="more" :size="20" /></span>
          More
        </button>
        <ul v-show="moreOpen" :id="moreId" class="more-menu">
          <li v-for="item in MORE_ITEMS" :key="item.key">
            <RouterLink v-slot="{ href, navigate }" :to="item.to" custom>
              <a
                :href="href"
                class="more-link"
                :aria-current="active === item.key ? 'page' : undefined"
                @click="navigate"
              >
                <Icon :name="item.icon" />{{ item.label }}
                <Badge v-if="counts[item.key] !== undefined">{{
                  counts[item.key]
                }}</Badge>
              </a>
            </RouterLink>
          </li>
        </ul>
      </div>
    </nav>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-rows: var(--size-topbar) minmax(0, 1fr);
  height: 100vh;
  height: 100dvh;
  background: var(--bar);
}

/* Top bar */
.topbar {
  display: flex;
  align-items: center;
  gap: var(--space-16);
  min-width: 0;
  padding: 0 var(--space-12) 0 var(--space-16);
  border-bottom: 1px solid var(--line);
  background: var(--bar);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  flex: none;
}

.brand-mark--phone {
  display: none;
}

.wordmark {
  font-family: var(--font-head);
  font-size: var(--fs-16);
  font-weight: 700;
  letter-spacing: var(--tracking-head);
  line-height: 1;
  color: var(--ink);
}

.org-sep {
  color: var(--muted);
}

.org {
  overflow: hidden;
  font-size: var(--fs-14);
  font-weight: 500;
  color: var(--ink);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  gap: var(--space-8);
  max-width: var(--size-search-max);
  height: var(--size-md);
  margin-left: var(--space-24);
  padding: 0 var(--space-4) 0 var(--space-12);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--win);
  color: var(--muted);
}

.search:hover {
  border-color: var(--muted);
}

.search.is-focused {
  border-color: var(--ink);
  outline: var(--focus-width) solid var(--focus);
  outline-offset: var(--focus-offset);
}

.search.is-focused > .icon {
  color: var(--ink);
}

.search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: var(--fs-14);
  color: var(--ink);
}

.search-input::placeholder {
  color: var(--muted);
}

.search-input::-webkit-search-cancel-button {
  appearance: none;
}

.search-clear {
  display: inline-grid;
  place-items: center;
  width: var(--size-chip);
  height: var(--size-chip);
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text);
  cursor: pointer;
}

.search-clear:hover {
  background: var(--soft);
}

.search-kbd {
  display: inline-grid;
  place-items: center;
  min-width: var(--size-chip);
  height: var(--size-chip);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--bar);
  font-size: var(--fs-12);
  line-height: 1;
  color: var(--muted);
}

.search-kbd.is-wide {
  min-width: var(--size-md);
}

.phone-title,
.phone-actions {
  display: none;
}

.spacer {
  flex: 1;
}

.sandbox-chip {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: var(--space-4);
  height: var(--size-chip);
  padding: 0 var(--space-8);
  border-radius: var(--r-pill);
  background: var(--stamp-soft);
  color: var(--stamp);
  font-size: var(--fs-12);
  font-weight: 500;
  white-space: nowrap;
}

/* Body: rail + content */
.body {
  display: grid;
  grid-template-columns: var(--size-rail) minmax(0, 1fr);
  min-height: 0;
}

.rail {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  padding: var(--space-8);
  border-right: 1px solid var(--line);
  background: var(--bar);
}

.rail-item {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: var(--space-4);
  min-height: var(--size-tabbar-item);
  padding: var(--space-8) var(--space-4);
  border: 1px solid transparent;
  border-radius: var(--r-md);
  color: var(--muted);
  font-size: var(--fs-12);
  font-weight: 500;
  text-decoration: none;
}

.rail-item:hover {
  background: var(--soft);
  color: var(--ink);
}

.rail-item.is-active {
  border-color: var(--line);
  background: var(--win);
  box-shadow: var(--shadow-raised);
  color: var(--ink);
}

.rail-icon,
.tabbar-icon {
  position: relative;
  display: grid;
  place-items: center;
}

.rail-count {
  position: absolute;
  top: calc(-1 * var(--space-8));
  left: 100%;
  transform: translateX(-40%);
}

.main {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
  min-width: 0;
  min-height: 0;
  padding: var(--space-16);
  overflow: auto;
}

.page {
  display: grid;
  flex: 1 1 auto;
  min-height: 0;
}

/* Phone tab bar */
.tabbar {
  display: none;
}

.tabbar-item {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: var(--space-4);
  width: 100%;
  min-height: var(--size-tabbar-item);
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: var(--fs-12);
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
}

.tabbar-item:focus-visible {
  outline-offset: var(--focus-offset-inset);
}

.tabbar-icon {
  width: var(--size-icon-disc);
  height: var(--size-sm);
  border: 1px solid transparent;
  border-radius: var(--r-pill);
}

.tabbar-item.is-active {
  color: var(--ink);
  font-weight: 600;
}

.tabbar-item.is-active .tabbar-icon {
  border-color: var(--line);
  background: var(--win);
  box-shadow: var(--shadow-raised);
}

.tabbar-more {
  position: relative;
  display: grid;
}

.more-menu {
  position: absolute;
  right: var(--space-8);
  bottom: calc(100% + var(--space-8));
  z-index: 20;
  display: grid;
  min-width: 180px;
  padding: var(--space-4);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--win);
  box-shadow: var(--shadow-window);
  list-style: none;
}

.more-link {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  min-height: var(--size-lg);
  padding: 0 var(--space-12);
  border-radius: var(--r-sm);
  color: var(--ink);
  font-size: var(--fs-14);
  text-decoration: none;
}

.more-link:hover,
.more-link[aria-current="page"] {
  background: var(--soft);
}

.more-link:focus-visible {
  outline-offset: var(--focus-offset-inset);
}

/* 768–1279 px: rail with icons only, tooltips */
@media (max-width: 1279px) {
  .body {
    grid-template-columns: var(--size-rail-icons) minmax(0, 1fr);
  }

  .rail-item {
    min-height: var(--size-lg);
    padding: 0;
  }

  .rail-label {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }
}

/* 767 px and below: bottom tab bar, phone header */
@media (max-width: 767px) {
  .shell {
    grid-template-rows: var(--size-phone-header) minmax(0, 1fr) var(
        --size-tabbar
      );
  }

  .topbar {
    gap: var(--space-8);
    padding: 0 var(--space-4) 0 var(--space-16);
  }

  .brand-mark--wide,
  .wordmark,
  .org-sep,
  .org,
  .search,
  .sandbox-chip {
    display: none;
  }

  .brand-mark--phone {
    display: inline-grid;
  }

  .phone-title {
    display: block;
    overflow: hidden;
    font-family: var(--font-head);
    font-size: var(--fs-21);
    font-weight: 700;
    letter-spacing: var(--tracking-head);
    line-height: 1;
    color: var(--ink);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .phone-actions {
    display: flex;
    align-items: center;
  }

  .body {
    grid-template-columns: minmax(0, 1fr);
  }

  .rail {
    display: none;
  }

  .main {
    gap: var(--space-12);
    padding: var(--space-12) var(--space-16) var(--space-24);
  }

  .tabbar {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    border-top: 1px solid var(--line);
    background: var(--bar);
  }
}
</style>
