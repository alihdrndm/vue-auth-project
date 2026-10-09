<script lang="ts">
import type { components } from "../../api/schema";

type DocumentDetail = components["schemas"]["DocumentDetail"];

export type ViewerTab = "document" | "xml" | "text";

/** Kinds whose XML the API keeps (`GET /documents/{id}/xml`). */
const KINDS_WITH_XML = new Set(["xml", "hybrid_pdf"]);

export const NO_XML_REASON = "This PDF has no XML inside";
export const NO_TEXT_REASON = "This invoice is XML only, there is no PDF text";
export const NO_RENDERING_REASON = "There is no rendered view of this XML";

/** An XML file (not a PDF). Before detection finishes, the file name decides. */
export function isXmlDocument(document: DocumentDetail): boolean {
  if (document.kind) return document.kind === "xml";
  return document.original_filename.toLowerCase().endsWith(".xml");
}

export function hasXml(document: DocumentDetail): boolean {
  if (document.kind) return KINDS_WITH_XML.has(document.kind);
  return isXmlDocument(document);
}
</script>

<script setup lang="ts">
// DocumentViewer (design): tabs Document / XML / Text. Document is the PDF (PDF.js) or, for XML
// invoices, the API's visualisation in a sandboxed iframe; XML is the highlighted source; Text is
// the PDF's text layer with the selected field's evidence marked.
import { useQuery } from "@tanstack/vue-query";
import { computed, watch } from "vue";

import { ApiError } from "../../api/client";
import { queryKeys } from "../../api/query";
import ErrorState from "../../components/ui/ErrorState.vue";
import Tabs, { type TabItem } from "../../components/ui/Tabs.vue";
import { documentUrl, fetchRepresentation } from "./api";
import CodeView from "./CodeView.vue";
import PdfView from "./PdfView.vue";
import TextView from "./TextView.vue";

const props = withDefaults(
  defineProps<{
    document: DocumentDetail;
    /** The field picked in the Fields panel; its evidence is marked in the Text tab. */
    selectedField?: string | null;
  }>(),
  { selectedField: null },
);

const tab = defineModel<ViewerTab>("tab", { default: "document" });

const id = computed(() => props.document.id);
const xmlDocument = computed(() => isXmlDocument(props.document));
const withXml = computed(() => hasXml(props.document));
const number = computed(
  () => props.document.invoice_number ?? props.document.original_filename,
);

const visualization = useQuery({
  queryKey: computed(() => queryKeys.documents.visualization(id.value)),
  queryFn: () => fetchRepresentation(id.value, "visualization"),
  enabled: xmlDocument,
  staleTime: Infinity,
});
const noRendering = computed(
  () => xmlDocument.value && visualization.data.value === null,
);

const xml = useQuery({
  queryKey: computed(() => queryKeys.documents.xml(id.value)),
  queryFn: () => fetchRepresentation(id.value, "xml"),
  enabled: computed(() => withXml.value && tab.value === "xml"),
  staleTime: Infinity,
});

const text = useQuery({
  queryKey: computed(() => queryKeys.documents.text(id.value)),
  queryFn: () => fetchRepresentation(id.value, "text"),
  enabled: computed(() => !xmlDocument.value && tab.value === "text"),
  staleTime: Infinity,
});

const items = computed<TabItem[]>(() => [
  {
    key: "document",
    label: "Document",
    disabledReason: noRendering.value ? NO_RENDERING_REASON : undefined,
  },
  {
    key: "xml",
    label: "XML",
    disabledReason: withXml.value ? undefined : NO_XML_REASON,
  },
  {
    key: "text",
    label: "Text",
    disabledReason: xmlDocument.value ? NO_TEXT_REASON : undefined,
  },
]);

// A tab that does not apply falls back to one that does.
watch(
  [items, tab],
  () => {
    const current = items.value.find((item) => item.key === tab.value);
    if (current && !current.disabledReason) return;
    const first = items.value.find((item) => !item.disabledReason);
    if (first) tab.value = first.key as ViewerTab;
  },
  { immediate: true },
);

const evidence = computed(() => {
  const field = props.selectedField;
  if (!field) return null;
  return props.document.invoice?.field_evidence?.[field] ?? null;
});

// Picking a field with evidence shows where it came from: the Text tab of the PDF.
watch(
  () => props.selectedField,
  (field) => {
    if (field && evidence.value && !xmlDocument.value) tab.value = "text";
  },
);

const meta = computed(() => {
  if (tab.value === "xml") return `${number.value}.xml`;
  if (tab.value === "text") return "Text layer";
  return xmlDocument.value ? "Rendered from XML" : "Original PDF";
});

function problem(error: unknown): { title: string; detail?: string } {
  return error instanceof ApiError
    ? { title: error.title, detail: error.detail }
    : {
        title: "This view could not be loaded",
        detail: "Check your connection and try again.",
      };
}
</script>

<template>
  <div class="viewer">
    <span class="viewer-meta">{{ meta }}</span>
    <Tabs
      :model-value="tab"
      class="viewer-tabs"
      label="Document views"
      variant="segmented"
      :items="items"
      @update:model-value="tab = $event as ViewerTab"
    >
      <template v-if="tab === 'document'">
        <PdfView
          v-if="!xmlDocument"
          :document-id="document.id"
          :filename="document.original_filename"
        />
        <ErrorState
          v-else-if="visualization.error.value"
          v-bind="problem(visualization.error.value)"
          :level="3"
          :retrying="visualization.isFetching.value"
          @retry="visualization.refetch()"
        />
        <p
          v-else-if="visualization.data.value === undefined"
          class="viewer-note"
          aria-busy="true"
        >
          Loading the rendered invoice…
        </p>
        <div v-else class="viewer-rendering">
          <iframe
            class="viewer-frame"
            :src="documentUrl(document.id, 'visualization')"
            sandbox=""
            referrerpolicy="no-referrer"
            :title="`Rendered view of invoice ${number}`"
          />
          <span class="viewer-caption"
            >Rendered from the XML. The XML is the invoice.</span
          >
        </div>
      </template>

      <template v-else-if="tab === 'xml'">
        <ErrorState
          v-if="xml.error.value"
          v-bind="problem(xml.error.value)"
          :level="3"
          :retrying="xml.isFetching.value"
          @retry="xml.refetch()"
        />
        <p
          v-else-if="xml.data.value === undefined"
          class="viewer-note"
          aria-busy="true"
        >
          Loading the XML…
        </p>
        <p v-else-if="xml.data.value === null" class="viewer-note">
          {{ NO_XML_REASON }}.
        </p>
        <CodeView v-else :source="xml.data.value" :label="`XML of ${number}`" />
      </template>

      <template v-else>
        <ErrorState
          v-if="text.error.value"
          v-bind="problem(text.error.value)"
          :level="3"
          :retrying="text.isFetching.value"
          @retry="text.refetch()"
        />
        <p
          v-else-if="text.data.value === undefined"
          class="viewer-note"
          aria-busy="true"
        >
          Loading the text…
        </p>
        <TextView v-else :text="text.data.value ?? ''" :evidence="evidence" />
      </template>
    </Tabs>
  </div>
</template>

<style scoped>
.viewer {
  position: relative;
  min-height: 0;
  height: 100%;
}

.viewer-tabs {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  background: var(--bar);
}

/* The pane's tab bar: the segmented control on --bar, the meta text to its right. */
.viewer-tabs :deep(.tabs-list) {
  width: max-content;
  margin: var(--space-8) var(--space-12);
}

.viewer-tabs :deep(.tabs-panel) {
  min-height: 0;
  overflow: auto;
  border-top: 1px solid var(--line);
  background: var(--soft);
}

.viewer-meta {
  position: absolute;
  top: var(--space-16);
  right: var(--space-12);
  font-size: var(--fs-12);
  color: var(--muted);
  white-space: nowrap;
}

.viewer-note {
  padding: var(--space-24);
  font-size: var(--fs-13);
  color: var(--muted);
}

.viewer-rendering {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  justify-items: center;
  gap: var(--space-12);
  height: 100%;
  /* The design's document height on tablets. */
  min-height: 480px;
  padding: var(--space-24);
}

.viewer-frame {
  width: 100%;
  height: 100%;
  border: 1px solid var(--line);
  background: var(--win);
}

.viewer-caption {
  font-size: var(--fs-12);
  color: var(--muted);
}
</style>
