<!-- eslint-disable vue/multi-word-component-names -- named after the design system component -->
<script lang="ts">
export interface TabItem {
  key: string;
  label: string;
  /** Shown as a count badge after the label. */
  count?: number;
  disabled?: boolean;
  /** Why the tab is unavailable, e.g. "This PDF has no XML inside". */
  disabledReason?: string;
}
</script>

<script setup lang="ts">
import { nextTick, ref, useId } from "vue";

import Badge from "./Badge.vue";
import Icon from "./Icon.vue";

const props = withDefaults(
  defineProps<{
    /** Accessible name of the tab list, e.g. "Inbox filters". */
    label: string;
    items: TabItem[];
    /** underline: filters; segmented: views inside a pane. */
    variant?: "underline" | "segmented";
  }>(),
  { variant: "underline" },
);

const selected = defineModel<string>({ required: true });

defineSlots<{ default?: (props: { selected: string }) => unknown }>();

const id = useId();
const tabRefs = ref<HTMLButtonElement[]>([]);

const tabId = (key: string): string => `${id}-tab-${key}`;
const panelId = `${id}-panel`;

function isDisabled(item: TabItem): boolean {
  return item.disabled === true || item.disabledReason !== undefined;
}

function select(item: TabItem): void {
  if (isDisabled(item)) return;
  selected.value = item.key;
}

async function move(from: number, step: number): Promise<void> {
  const count = props.items.length;
  for (let offset = 1; offset <= count; offset += 1) {
    const index = (from + step * offset + count * offset) % count;
    const item = props.items[index];
    if (item && !isDisabled(item)) {
      selected.value = item.key;
      await nextTick();
      tabRefs.value[index]?.focus();
      return;
    }
  }
}

async function onKeydown(event: KeyboardEvent, index: number): Promise<void> {
  if (event.key === "ArrowRight") {
    event.preventDefault();
    await move(index, 1);
  } else if (event.key === "ArrowLeft") {
    event.preventDefault();
    await move(index, -1);
  } else if (event.key === "Home") {
    event.preventDefault();
    await move(-1, 1);
  } else if (event.key === "End") {
    event.preventDefault();
    await move(props.items.length, -1);
  }
}
</script>

<template>
  <div class="tabs" :class="`tabs--${variant}`">
    <div role="tablist" class="tabs-list" :aria-label="label">
      <button
        v-for="(item, index) in items"
        :id="tabId(item.key)"
        :key="item.key"
        ref="tabRefs"
        type="button"
        role="tab"
        class="tab"
        :class="{ 'is-selected': item.key === selected }"
        :aria-selected="item.key === selected ? 'true' : 'false'"
        :aria-controls="panelId"
        :aria-disabled="isDisabled(item) ? 'true' : undefined"
        :tabindex="item.key === selected ? 0 : -1"
        :title="item.disabledReason"
        @click="select(item)"
        @keydown="onKeydown($event, index)"
      >
        <Icon v-if="item.disabledReason" name="lock" :size="14" />{{ item.label
        }}<Badge
          v-if="item.count !== undefined"
          class="tab-count"
          :class="{ 'is-zero': item.count === 0 }"
          :selected="item.key === selected"
          >{{ item.count }}</Badge
        ><span v-if="item.disabledReason" class="sr-only"
          >. {{ item.disabledReason }}</span
        >
      </button>
    </div>
    <div
      v-if="$slots.default"
      :id="panelId"
      role="tabpanel"
      class="tabs-panel"
      :aria-labelledby="tabId(selected)"
    >
      <slot :selected="selected" />
    </div>
  </div>
</template>

<style scoped>
.tabs-list {
  display: flex;
  gap: var(--space-4);
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-8);
  flex: none;
  border: 0;
  background: transparent;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
}

.tab[aria-disabled="true"] {
  color: var(--muted);
  cursor: not-allowed;
}

/* Underline */
.tabs--underline .tab {
  height: var(--size-tab);
  padding: 0 var(--space-8);
  font-size: var(--fs-14);
  color: var(--muted);
}

.tabs--underline .tab:hover:not([aria-disabled="true"]) {
  color: var(--ink);
  box-shadow: inset 0 -2px 0 var(--line-strong);
}

.tabs--underline .tab.is-selected,
.tabs--underline .tab.is-selected:hover {
  color: var(--ink);
  box-shadow: inset 0 -2px 0 var(--ink);
}

.tabs--underline .tab:focus-visible {
  outline-offset: var(--focus-offset-inset);
}

.tab-count.is-zero {
  color: var(--muted);
}

/* Segmented */
.tabs--segmented .tabs-list {
  display: inline-flex;
  padding: var(--space-4);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--bar);
}

.tabs--segmented .tab {
  gap: var(--space-4);
  height: var(--size-sm);
  padding: 0 var(--space-12);
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  font-size: var(--fs-13);
  color: var(--text);
}

.tabs--segmented .tab:hover:not([aria-disabled="true"], .is-selected) {
  background: var(--soft);
  color: var(--ink);
}

.tabs--segmented .tab.is-selected {
  border-color: var(--line);
  background: var(--win);
  box-shadow: var(--shadow-raised);
  color: var(--ink);
}

.tabs--segmented .tab[aria-disabled="true"] {
  color: var(--muted);
}
</style>
