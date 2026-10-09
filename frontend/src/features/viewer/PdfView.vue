<script setup lang="ts">
// The Document tab for PDFs: PDF.js renders one page at a time into a canvas, with page
// buttons, zoom and a download link (design "DocumentViewer").
import { useQuery } from "@tanstack/vue-query";
import { computed, onBeforeUnmount, ref, shallowRef, watch } from "vue";

import { ApiError } from "../../api/client";
import { queryKeys } from "../../api/query";
import ErrorState from "../../components/ui/ErrorState.vue";
import Icon from "../../components/ui/Icon.vue";
import { documentUrl, fetchFile } from "./api";
import { openPdf, type PDFDocumentProxy } from "./pdf";

const props = defineProps<{
  documentId: string;
  filename: string;
}>();

const ZOOM_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 2];
const PAGE_BUTTONS_MAX = 8;

const file = useQuery({
  queryKey: computed(() => queryKeys.documents.file(props.documentId)),
  queryFn: () => fetchFile(props.documentId),
  staleTime: Infinity,
});

const pdf = shallowRef<PDFDocumentProxy | null>(null);
const openError = ref<string | null>(null);
const page = ref(1);
const zoomIndex = ref(2);
const canvas = ref<HTMLCanvasElement | null>(null);
const rendering = ref(false);
let renderTask: { cancel: () => void; promise: Promise<unknown> } | null = null;

const pageCount = computed(() => pdf.value?.numPages ?? 0);
const zoom = computed(() => ZOOM_STEPS[zoomIndex.value] ?? 1);
const zoomLabel = computed(() => `${Math.round(zoom.value * 100)} %`);

watch(
  () => file.data.value,
  async (bytes) => {
    openError.value = null;
    if (!bytes) return;
    try {
      const opened = await openPdf(bytes);
      void pdf.value?.loadingTask.destroy();
      pdf.value = opened;
      page.value = 1;
    } catch {
      openError.value = "This PDF can't be shown here. Download it to open it.";
    }
  },
  { immediate: true },
);

async function render(): Promise<void> {
  const doc = pdf.value;
  const target = canvas.value;
  if (!doc || !target) return;
  renderTask?.cancel();
  rendering.value = true;
  try {
    const current = await doc.getPage(page.value);
    const ratio = globalThis.devicePixelRatio || 1;
    const viewport = current.getViewport({ scale: zoom.value * ratio });
    target.width = Math.floor(viewport.width);
    target.height = Math.floor(viewport.height);
    target.style.width = `${Math.floor(viewport.width / ratio)}px`;
    const task = current.render({ canvas: target, viewport });
    renderTask = task;
    await task.promise;
  } catch {
    // A cancelled render is replaced by the next one.
  } finally {
    rendering.value = false;
  }
}

watch([pdf, page, zoom, canvas], () => void render(), { flush: "post" });

onBeforeUnmount(() => {
  renderTask?.cancel();
  void pdf.value?.loadingTask.destroy();
});

function goTo(target: number): void {
  if (target >= 1 && target <= pageCount.value) page.value = target;
}

const loadError = computed(() => {
  const error = file.error.value;
  if (!error) return null;
  return error instanceof ApiError
    ? { title: error.title, detail: error.detail }
    : {
        title: "The file could not be loaded",
        detail: "Check your connection and try again.",
      };
});
</script>

<template>
  <div class="pdf">
    <div class="pdf-tools">
      <nav v-if="pageCount > 1" class="pdf-pages" aria-label="Pages">
        <button
          type="button"
          class="tool"
          aria-label="Previous page"
          title="Previous page"
          :disabled="page <= 1"
          @click="goTo(page - 1)"
        >
          <Icon name="chevron-left" />
        </button>
        <template v-if="pageCount <= PAGE_BUTTONS_MAX">
          <button
            v-for="number in pageCount"
            :key="number"
            type="button"
            class="tool tool--page"
            :aria-current="number === page ? 'page' : undefined"
            :aria-label="`Page ${number}`"
            @click="goTo(number)"
          >
            {{ number }}
          </button>
        </template>
        <button
          type="button"
          class="tool"
          aria-label="Next page"
          title="Next page"
          :disabled="page >= pageCount"
          @click="goTo(page + 1)"
        >
          <Icon name="chevron-right" />
        </button>
      </nav>
      <span class="pdf-spacer" />
      <div class="pdf-zoom" role="group" aria-label="Zoom">
        <button
          type="button"
          class="tool"
          aria-label="Zoom out"
          title="Zoom out"
          :disabled="zoomIndex === 0"
          @click="zoomIndex -= 1"
        >
          <Icon name="zoom-out" />
        </button>
        <span class="pdf-zoom-value" aria-live="polite">{{ zoomLabel }}</span>
        <button
          type="button"
          class="tool"
          aria-label="Zoom in"
          title="Zoom in"
          :disabled="zoomIndex === ZOOM_STEPS.length - 1"
          @click="zoomIndex += 1"
        >
          <Icon name="zoom-in" />
        </button>
      </div>
      <a
        class="tool tool--link"
        :href="documentUrl(documentId, 'file')"
        :download="filename"
        :aria-label="`Download ${filename}`"
        title="Download"
      >
        <Icon name="download" />
      </a>
    </div>

    <div class="pdf-stage">
      <ErrorState
        v-if="loadError"
        :title="loadError.title"
        :detail="loadError.detail"
        :level="3"
        :retrying="file.isFetching.value"
        @retry="file.refetch()"
      />
      <p v-else-if="openError" class="pdf-note" role="alert">{{ openError }}</p>
      <p v-else-if="!pdf" class="pdf-note" aria-busy="true">Loading the PDF…</p>
      <template v-else>
        <canvas
          ref="canvas"
          class="pdf-canvas"
          role="img"
          :aria-label="`Page ${page} of ${pageCount} of ${filename}. The Text tab has the text.`"
          :aria-busy="rendering ? 'true' : undefined"
        />
        <span class="pdf-caption"
          >Page {{ page }} of {{ pageCount }}, original PDF.</span
        >
      </template>
    </div>
  </div>
</template>

<style scoped>
.pdf {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  height: 100%;
}

.pdf-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-8) var(--space-12);
  border-bottom: 1px solid var(--line);
  background: var(--win);
}

.pdf-pages,
.pdf-zoom {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
}

.pdf-spacer {
  flex: 1;
}

.pdf-zoom-value {
  min-width: var(--space-40);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  color: var(--muted);
  text-align: center;
}

.tool {
  display: inline-grid;
  place-items: center;
  min-width: var(--size-sm);
  height: var(--size-sm);
  padding: 0 var(--space-4);
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  cursor: pointer;
}

.tool:hover:not(:disabled) {
  background: var(--soft);
  color: var(--ink);
}

.tool:disabled {
  color: var(--muted);
  cursor: not-allowed;
}

.tool--page[aria-current="page"] {
  border-color: var(--line);
  background: var(--bar);
  box-shadow: var(--shadow-raised);
  color: var(--ink);
}

.tool--link {
  text-decoration: none;
}

.pdf-stage {
  display: grid;
  justify-items: safe center;
  align-content: start;
  gap: var(--space-12);
  min-height: 0;
  padding: var(--space-32) var(--space-24);
  overflow: auto;
  background: var(--soft);
}

.pdf-canvas {
  max-width: none;
  border: 1px solid var(--line);
  background: var(--win);
}

.pdf-caption,
.pdf-note {
  font-size: var(--fs-12);
  color: var(--muted);
}

@media (max-width: 767px) {
  .tool {
    min-width: var(--size-lg);
    height: var(--size-lg);
  }

  .pdf-stage {
    padding: var(--space-16);
  }
}
</style>
