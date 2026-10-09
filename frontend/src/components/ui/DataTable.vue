<script lang="ts">
export interface DataTableColumn<T> {
  key: string;
  label: string;
  sortable?: boolean;
  align?: "left" | "right";
  /** CSS width, e.g. "96px" or "20%". */
  width?: string;
  /** Mono numbers (amounts, invoice numbers). */
  mono?: boolean;
  /** Plain-text cell content when no `cell-<key>` slot is given. */
  value?: (row: T) => string;
}

export interface DataTableSort {
  key: string;
  direction: "ascending" | "descending";
}
</script>

<script setup lang="ts" generic="T">
import Icon from "./Icon.vue";

const props = withDefaults(
  defineProps<{
    /** Read out as the table's caption. */
    caption: string;
    columns: DataTableColumn<T>[];
    rows: T[];
    rowKey: (row: T) => string;
    /** Rows open something when clicked or when Enter is pressed on them. */
    clickableRows?: boolean;
    selectedKeys?: string[];
  }>(),
  { clickableRows: true, selectedKeys: () => [] },
);

const sort = defineModel<DataTableSort | null>("sort", { default: null });

const emit = defineEmits<{ "row-click": [row: T] }>();

defineSlots<
  {
    [name: `cell-${string}`]: (props: { row: T }) => unknown;
  } & { empty?: () => unknown }
>();

function ariaSort(
  column: DataTableColumn<T>,
): "ascending" | "descending" | "none" | undefined {
  if (!column.sortable) return undefined;
  return sort.value?.key === column.key ? sort.value.direction : "none";
}

function toggleSort(column: DataTableColumn<T>): void {
  const current = sort.value;
  if (current?.key === column.key) {
    sort.value = {
      key: column.key,
      direction: current.direction === "ascending" ? "descending" : "ascending",
    };
  } else {
    sort.value = { key: column.key, direction: "ascending" };
  }
}

function isSelected(row: T): boolean {
  return props.selectedKeys.includes(props.rowKey(row));
}

function onRowClick(row: T, event: MouseEvent): void {
  if (!props.clickableRows) return;
  const target = event.target;
  if (
    target instanceof Element &&
    target.closest("button, a, input, select, textarea, label")
  ) {
    return;
  }
  emit("row-click", row);
}

function onRowKeydown(row: T, event: KeyboardEvent): void {
  if (!props.clickableRows || event.target !== event.currentTarget) return;
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    emit("row-click", row);
  }
}
</script>

<template>
  <div class="data-table">
    <table class="table">
      <caption class="sr-only">
        {{
          caption
        }}
      </caption>
      <thead>
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            scope="col"
            class="table-head"
            :class="{ 'is-right': column.align === 'right' }"
            :style="column.width ? { width: column.width } : undefined"
            :aria-sort="ariaSort(column)"
          >
            <button
              v-if="column.sortable"
              type="button"
              class="table-sort"
              :class="{ 'is-sorted': sort?.key === column.key }"
              @click="toggleSort(column)"
            >
              {{ column.label
              }}<Icon
                class="table-sort-icon"
                :class="{
                  'is-up':
                    sort?.key === column.key && sort.direction === 'ascending',
                }"
                name="chevron-down"
                :size="14"
              />
            </button>
            <span v-else>{{ column.label }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="rowKey(row)"
          class="table-row"
          :class="{
            'is-clickable': clickableRows,
            'is-selected': isSelected(row),
          }"
          :tabindex="clickableRows ? 0 : undefined"
          :aria-selected="selectedKeys.length > 0 ? isSelected(row) : undefined"
          @click="onRowClick(row, $event)"
          @keydown="onRowKeydown(row, $event)"
        >
          <td
            v-for="column in columns"
            :key="column.key"
            class="table-cell"
            :class="{
              'is-right': column.align === 'right',
              'is-mono': column.mono,
            }"
          >
            <slot :name="`cell-${column.key}`" :row="row">{{
              column.value?.(row) ?? ""
            }}</slot>
          </td>
        </tr>
      </tbody>
    </table>
    <slot v-if="rows.length === 0" name="empty" />
  </div>
</template>

<style scoped>
.table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--fs-13);
  color: var(--text);
}

.table-head {
  position: sticky;
  top: 0;
  z-index: 1;
  height: var(--size-row-header);
  padding: 0 var(--space-8);
  border-bottom: 1px solid var(--line);
  background: var(--bar);
  font-size: var(--fs-12);
  font-weight: 500;
  color: var(--muted);
  text-align: left;
  white-space: nowrap;
}

.table-head:first-child,
.table-cell:first-child {
  padding-left: var(--space-16);
}

.table-head:last-child,
.table-cell:last-child {
  padding-right: var(--space-16);
}

.table-sort {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--size-sm);
  margin: 0 calc(-1 * var(--space-4));
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--muted);
  font-size: var(--fs-12);
  font-weight: 500;
  cursor: pointer;
}

.table-sort:hover,
.table-sort.is-sorted {
  color: var(--ink);
}

.table-sort:hover {
  background: var(--soft);
}

.table-sort-icon {
  opacity: 0.4;
}

.table-sort.is-sorted .table-sort-icon {
  opacity: 1;
}

.table-sort-icon.is-up {
  transform: rotate(180deg);
}

.table-cell {
  height: var(--size-row);
  padding: var(--space-4) var(--space-8);
  border-bottom: 1px solid var(--line);
}

.is-right {
  text-align: right;
}

.is-mono {
  font-family: var(--font-mono);
  white-space: nowrap;
}

.table-cell.is-mono.is-right {
  color: var(--ink);
}

.table-row.is-clickable {
  cursor: pointer;
}

.table-row.is-clickable:hover,
.table-row.is-selected {
  background: var(--soft);
}

.table-row:focus-visible {
  outline-offset: var(--focus-offset-inset);
}
</style>
