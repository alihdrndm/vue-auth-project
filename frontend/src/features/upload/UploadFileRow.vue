<script setup lang="ts">
// One file in the upload list: its upload progress, then the document's processing steps
// (detect → validate → extract → check, refreshed every 2 s), or its own error.
import { useQuery } from "@tanstack/vue-query";
import { computed } from "vue";

import { api, unwrap } from "../../api/client";
import { queryKeys } from "../../api/query";
import Button from "../../components/ui/Button.vue";
import Icon from "../../components/ui/Icon.vue";
import type { IconName } from "../../components/ui/icons";
import type { UploadRow } from "./uploadQueue";

const props = defineProps<{ row: Readonly<UploadRow> }>();
defineEmits<{ remove: []; retry: [] }>();

const PROCESSING = new Set(["received", "processing"]);
const STEPS = [
  { key: "detect", label: "Detect", tip: "What kind of file is it?" },
  { key: "validate", label: "Validate", tip: "Is it a valid e-invoice?" },
  { key: "extract", label: "Read", tip: "Read the fields from the PDF" },
  { key: "check", label: "Check", tip: "Duplicates, bank details, totals" },
] as const;
const ORDER = ["detect", "validate", "extract", "check", "done"];

const documentId = computed(() => props.row.documentId);
const document = useQuery({
  queryKey: computed(() => queryKeys.documents.detail(documentId.value ?? "")),
  queryFn: async () =>
    unwrap(
      await api.GET("/api/v1/documents/{document_id}", {
        params: { path: { document_id: documentId.value ?? "" } },
      }),
    ),
  enabled: computed(
    () => props.row.state === "done" && documentId.value !== null,
  ),
  refetchInterval: (query) =>
    query.state.data && !PROCESSING.has(query.state.data.status) ? false : 2000,
});

const status = computed(() => document.data.value?.status ?? null);
const step = computed(() => document.data.value?.processing_step ?? null);

function stepIcon(key: string): {
  icon: IconName;
  spin: boolean;
  label: string;
} {
  const reached = ORDER.indexOf(step.value ?? "detect");
  const index = ORDER.indexOf(key);
  if (!PROCESSING.has(status.value ?? "received") || index < reached) {
    return { icon: "circle-check", spin: false, label: "done" };
  }
  if (index === reached)
    return { icon: "loader", spin: true, label: "in progress" };
  return { icon: "circle", spin: false, label: "waiting" };
}

const STATUS_TEXT: Record<string, string> = {
  needs_review: "Needs review",
  awaiting_approval: "Awaiting approval",
  approved: "Approved",
  rejected: "Rejected",
  exported: "Exported",
  failed: "Failed",
};

const statusText = computed(() => {
  switch (props.row.state) {
    case "queued":
      return "Waiting";
    case "uploading":
      return `Uploading ${Math.round(props.row.progress * 100)} %`;
    case "duplicate":
      return "Already in the inbox";
    case "failed":
      return "Not uploaded";
    default:
      return status.value && !PROCESSING.has(status.value)
        ? (STATUS_TEXT[status.value] ?? status.value)
        : "Processing";
  }
});

const fileIcon = computed<IconName>(() =>
  props.row.name.toLowerCase().endsWith(".xml") ? "file-code" : "file-text",
);
const finished = computed(
  () =>
    props.row.state === "done" &&
    status.value !== null &&
    !PROCESSING.has(status.value),
);
</script>

<template>
  <li class="row" :class="`row--${row.state}`">
    <Icon :name="fileIcon" :size="20" class="row__icon" />
    <div class="row__body">
      <div class="row__head">
        <span class="row__name">{{ row.name }}</span>
        <span class="row__status">{{ statusText }}</span>
      </div>
      <progress
        v-if="row.state === 'uploading'"
        class="row__progress"
        :value="row.progress"
        max="1"
        :aria-label="`Uploading ${row.name}`"
      ></progress>
      <ol
        v-if="row.state === 'done'"
        class="steps"
        aria-label="Processing steps"
      >
        <li v-for="item in STEPS" :key="item.key" class="steps__item">
          <Icon
            :name="stepIcon(item.key).icon"
            :spin="stepIcon(item.key).spin"
            :size="16"
            :class="`steps__icon steps__icon--${stepIcon(item.key).label.replace(' ', '-')}`"
          />
          <span>
            <span class="steps__label">{{ item.label }}</span>
            <span class="visually-hidden"
              >: {{ stepIcon(item.key).label }}</span
            >
            <span class="steps__tip">{{ item.tip }}</span>
          </span>
        </li>
      </ol>
      <p v-if="row.error" class="row__error" role="alert">
        <Icon name="octagon" :size="16" />
        <span>
          <strong>{{ row.error.title }}</strong>
          <template v-if="row.error.detail"> {{ row.error.detail }}</template>
        </span>
      </p>
    </div>
    <div class="row__actions">
      <RouterLink
        v-if="(finished || row.state === 'duplicate') && row.documentId"
        :to="{ name: 'invoice', params: { id: row.documentId } }"
        class="row__open"
      >
        <Icon name="eye" :size="14" />Open
      </RouterLink>
      <Button
        v-if="row.state === 'failed'"
        size="sm"
        variant="ghost"
        @click="$emit('remove')"
      >
        Remove
      </Button>
    </div>
  </li>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--space-12);
  align-items: start;
  padding: var(--space-12) 0;
  border-bottom: 1px solid var(--line);
}

.row__icon {
  color: var(--muted);
  margin-top: 2px;
}

.row__head {
  display: flex;
  justify-content: space-between;
  gap: var(--space-8);
}

.row__name {
  font-weight: 500;
  overflow-wrap: anywhere;
}

.row__status {
  color: var(--muted);
  font-size: var(--fs-13);
  white-space: nowrap;
}

.row__progress {
  width: 100%;
  height: 4px;
  margin-top: var(--space-8);
  accent-color: var(--stamp);
}

.steps {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8) var(--space-16);
  margin: var(--space-8) 0 0;
  padding: 0;
  list-style: none;
  font-size: var(--fs-13);
}

.steps__item {
  display: flex;
  gap: var(--space-4);
  align-items: center;
}

.steps__icon--done {
  color: var(--ok);
}

.steps__icon--in-progress {
  color: var(--stamp);
}

.steps__icon--waiting {
  color: var(--muted);
}

.steps__tip {
  display: block;
  color: var(--muted);
  font-size: var(--fs-12);
}

.row__error {
  display: flex;
  gap: var(--space-8);
  margin: var(--space-8) 0 0;
  color: var(--block);
  font-size: var(--fs-13);
}

.row__open {
  display: inline-flex;
  gap: var(--space-4);
  align-items: center;
  font-size: var(--fs-13);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>
