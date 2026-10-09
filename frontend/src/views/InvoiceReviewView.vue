<script setup lang="ts">
// Invoice review (HANDOFF "Frontend (Vue)", design "Eingang App Review"): the document viewer
// next to the data panel (status header with the allowed actions, Validation, Checks, Fields,
// Lines, VAT breakdown, Timeline). ≥ 1280 px two columns; 768–1279 px the data first and the
// document in a collapsible section; ≤ 767 px tabs Data / Document / Activity.
// j / k open the next / previous invoice of the inbox list (see features/review-screen/navigation).
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { api, ApiError, unwrap } from "../api/client";
import { queryKeys } from "../api/query";
import type { components } from "../api/schema";
import ErrorState from "../components/ui/ErrorState.vue";
import Icon from "../components/ui/Icon.vue";
import Skeleton from "../components/ui/Skeleton.vue";
import { useToast } from "../components/ui/useToast";
import ChecksPanel from "../features/review/ChecksPanel.vue";
import FieldsPanel from "../features/review/FieldsPanel.vue";
import { isEnabled } from "../features/review-screen/actions";
import { isCreditNote } from "../features/review-screen/format";
import LinesSection from "../features/review-screen/LinesSection.vue";
import {
  inboxList,
  isTyping,
  neighbour,
  stepMessage,
} from "../features/review-screen/navigation";
import ReviewHeader from "../features/review-screen/ReviewHeader.vue";
import TimelineSection from "../features/review-screen/TimelineSection.vue";
import { useMediaQuery } from "../features/review-screen/useMediaQuery";
import ValidationSection from "../features/review-screen/ValidationSection.vue";
import VatSection from "../features/review-screen/VatSection.vue";
import DocumentViewer, {
  hasXml,
  type ViewerTab,
} from "../features/viewer/DocumentViewer.vue";

type DocumentDetail = components["schemas"]["DocumentDetail"];
type PhoneTab = "data" | "document" | "activity";

const props = defineProps<{ id: string }>();

const POLL_MS = 2000;
const STEP_TOAST_MS = 2500;

const route = useRoute();
const router = useRouter();
const queryClient = useQueryClient();
const toast = useToast();
const uid = useId();

const detail = useQuery({
  queryKey: computed(() => queryKeys.documents.detail(props.id)),
  queryFn: async () =>
    unwrap(
      await api.GET("/api/v1/documents/{document_id}", {
        params: { path: { document_id: props.id } },
      }),
    ),
  // While the invoice is still being read, poll every 2 s (stops when the tab is hidden).
  refetchInterval: (query) => {
    const status = query.state.data?.status;
    return status === "received" || status === "processing" ? POLL_MS : false;
  },
});

const doc = computed(() => detail.data.value);
const notFound = computed(
  () =>
    detail.error.value instanceof ApiError && detail.error.value.status === 404,
);
const problem = computed(() => {
  const error = detail.error.value;
  if (!error) return null;
  return error instanceof ApiError
    ? { title: error.title, detail: error.detail }
    : {
        title: "The invoice could not be loaded",
        detail: "Check your connection and try again.",
      };
});

const canEdit = computed(() =>
  doc.value ? isEnabled(doc.value.allowed_actions, "edit_fields") : false,
);
const credit = computed(() =>
  isCreditNote(doc.value?.type_code ?? doc.value?.invoice?.type_code),
);
const currency = computed(
  () => doc.value?.invoice?.currency ?? doc.value?.currency ?? "EUR",
);

// ---------------------------------------------------------------------------
// Layout state

const phone = useMediaQuery("(max-width: 767px)");
const tablet = useMediaQuery("(min-width: 768px) and (max-width: 1279px)");
const phoneTab = ref<PhoneTab>("data");
const docOpen = ref(false);
const viewerTab = ref<ViewerTab>("document");
const selectedField = ref<string | null>(null);

const viewerShown = computed(() => {
  if (phone.value) return phoneTab.value === "document";
  if (tablet.value) return docOpen.value;
  return true;
});

watch(
  () => props.id,
  () => {
    selectedField.value = null;
    viewerTab.value = "document";
  },
);

const PHONE_TABS: { key: PhoneTab; label: string }[] = [
  { key: "data", label: "Data" },
  { key: "document", label: "Document" },
  { key: "activity", label: "Activity" },
];
const phoneTabRefs = ref<HTMLButtonElement[]>([]);

function onPhoneTabKey(event: KeyboardEvent, index: number): void {
  const step =
    event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
  if (step === 0) return;
  event.preventDefault();
  const next = (index + step + PHONE_TABS.length) % PHONE_TABS.length;
  const tab = PHONE_TABS[next];
  if (!tab) return;
  phoneTab.value = tab.key;
  phoneTabRefs.value[next]?.focus();
}

function showXml(): void {
  viewerTab.value = "xml";
  phoneTab.value = "document";
  docOpen.value = true;
}

function selectField(name: string): void {
  selectedField.value = name;
}

// ---------------------------------------------------------------------------
// Keeping the data fresh

function invalidateLists(): void {
  void queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
  void queryClient.invalidateQueries({ queryKey: queryKeys.stats() });
}

/** After a field edit or a resolved check: the detail (only it, not the file) and the lists. */
function refresh(): void {
  void queryClient.invalidateQueries({
    queryKey: queryKeys.documents.detail(props.id),
    exact: true,
  });
  invalidateLists();
}

function onChanged(updated: DocumentDetail): void {
  queryClient.setQueryData(queryKeys.documents.detail(props.id), updated);
  refresh();
}

function onDeleted(): void {
  queryClient.removeQueries({ queryKey: queryKeys.documents.detail(props.id) });
  invalidateLists();
  void router.push({ name: "inbox" });
}

// ---------------------------------------------------------------------------
// j / k: next and previous invoice of the inbox list

let stepping = false;

async function step(direction: 1 | -1): Promise<void> {
  if (stepping) return;
  stepping = true;
  try {
    const list = await inboxList(queryClient, props.id, route.query.from);
    const target = neighbour(list, props.id, direction);
    if (!target) {
      toast.show({
        kind: "success",
        message: "This is the only invoice in this list.",
        duration: STEP_TOAST_MS,
      });
      return;
    }
    await router.push({
      name: "invoice",
      params: { id: target.document.id },
      query: route.query,
    });
    toast.show({
      kind: "success",
      message: stepMessage(target, direction),
      duration: STEP_TOAST_MS,
    });
  } catch (error) {
    toast.show({
      kind: "error",
      message:
        error instanceof ApiError
          ? `${error.title}. ${error.detail}`
          : "The inbox list could not be loaded.",
    });
  } finally {
    stepping = false;
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key !== "j" && event.key !== "k") return;
  if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey)
    return;
  if (isTyping(event.target)) return;
  if (document.querySelector("dialog[open]")) return;
  event.preventDefault();
  void step(event.key === "j" ? 1 : -1);
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));
</script>

<template>
  <div v-if="doc" class="review" :class="`review--tab-${phoneTab}`">
    <div class="pane pane--data">
      <ReviewHeader
        class="area-head"
        :document="doc"
        :phone="phone"
        @changed="onChanged"
        @deleted="onDeleted"
      />

      <div class="phone-tabs" role="tablist" aria-label="Invoice views">
        <button
          v-for="(tab, index) in PHONE_TABS"
          :id="`${uid}-mtab-${tab.key}`"
          :key="tab.key"
          ref="phoneTabRefs"
          type="button"
          role="tab"
          class="phone-tab"
          :aria-selected="phoneTab === tab.key ? 'true' : 'false'"
          :aria-controls="
            tab.key === 'document' ? `${uid}-document` : `${uid}-data`
          "
          :tabindex="phoneTab === tab.key ? 0 : -1"
          @click="phoneTab = tab.key"
          @keydown="onPhoneTabKey($event, index)"
        >
          {{ tab.label }}
        </button>
      </div>

      <div :id="`${uid}-data`" class="panel-body">
        <p v-if="doc.text_truncated" class="truncated" role="note">
          <Icon name="info" />Only the first 12,000 characters were read.
        </p>
        <div class="data-sections">
          <ValidationSection
            :document="doc"
            :can-show-xml="hasXml(doc)"
            @show-xml="showXml"
          />
          <ChecksPanel :document="doc" @resolved="refresh" />
          <FieldsPanel
            :document="doc"
            :can-edit="canEdit"
            @select-field="selectField"
            @saved="refresh"
          />
          <LinesSection
            :lines="doc.lines"
            :currency="currency"
            :credit="credit"
          />
          <VatSection :invoice="doc.invoice" :credit="credit" />
        </div>
        <TimelineSection class="activity" :document="doc" />
      </div>
    </div>

    <button
      type="button"
      class="doc-toggle"
      :aria-expanded="docOpen ? 'true' : 'false'"
      :aria-controls="`${uid}-document`"
      @click="docOpen = !docOpen"
    >
      {{ docOpen ? "Hide document" : "Show document" }}
      <Icon
        name="chevron-down"
        class="chevron"
        :class="{ 'is-open': docOpen }"
      />
    </button>

    <section
      :id="`${uid}-document`"
      class="pane pane--doc"
      :class="{ 'is-open': docOpen }"
      aria-label="Document"
    >
      <DocumentViewer
        v-if="viewerShown"
        v-model:tab="viewerTab"
        :document="doc"
        :selected-field="selectedField"
      />
    </section>
  </div>

  <main v-else-if="notFound" class="not-found">
    <p class="not-found-code">404</p>
    <h1 class="not-found-title">Nothing at this address</h1>
    <p class="not-found-lead">
      The link may be old, or the sandbox it pointed to has been deleted.
    </p>
    <RouterLink :to="{ name: 'inbox' }">Go to the Inbox</RouterLink>
  </main>

  <div v-else-if="problem" class="review review--state">
    <div class="pane pane--data">
      <h1 class="sr-only">Invoice review</h1>
      <ErrorState
        :title="problem.title"
        :detail="problem.detail"
        :retrying="detail.isFetching.value"
        @retry="detail.refetch()"
      />
    </div>
  </div>

  <div v-else class="review review--state">
    <h1 class="sr-only">Invoice review</h1>
    <div class="pane pane--data">
      <Skeleton
        label="Loading the invoice"
        header
        :rows="10"
        :columns="[
          { track: '128px' },
          { track: 'minmax(0, 1fr)' },
          { track: '64px', shape: 'chip' },
        ]"
      />
    </div>
    <div class="pane pane--doc is-open" aria-hidden="true">
      <Skeleton
        label="Loading the document"
        header
        :rows="14"
        :columns="[{ track: 'minmax(0, 1fr)' }, { track: '96px' }]"
      />
    </div>
  </div>
</template>

<style scoped>
/* ≥ 1280 px: the document on the left, the data panel on the right; each scrolls on its own. */
.review {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 600px);
  grid-template-areas: "doc data";
  gap: var(--space-16);
  height: 100%;
  min-height: 0;
}

.pane {
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--win);
  overflow: hidden;
}

.pane--data {
  grid-area: data;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.review--state .pane--data {
  display: block;
  padding: var(--space-16);
}

.pane--doc {
  grid-area: doc;
}

.review--state .pane--doc {
  padding: var(--space-16);
}

.panel-body {
  min-height: 0;
  overflow: auto;
}

.truncated {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-8) var(--space-20);
  border-bottom: 1px solid var(--line);
  background: var(--info-soft);
  color: var(--info);
  font-size: var(--fs-13);
}

.phone-tabs,
.doc-toggle {
  display: none;
}

.chevron.is-open {
  transform: rotate(180deg);
}

/* 768–1279 px: the data panel first, the document collapsed below it. */
@media (max-width: 1279px) {
  .review {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      "data"
      "toggle"
      "doc";
    align-content: start;
    height: auto;
  }

  .pane--data {
    overflow: visible;
  }

  .panel-body {
    overflow: visible;
  }

  .doc-toggle {
    grid-area: toggle;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: var(--size-lg);
    padding: 0 var(--space-16);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    background: var(--win);
    color: var(--ink);
    font-size: var(--fs-14);
    font-weight: 500;
    cursor: pointer;
  }

  .doc-toggle:hover {
    background: var(--soft);
  }

  .pane--doc {
    display: none;
    height: 480px;
  }

  .pane--doc.is-open {
    display: block;
  }

  .review--state .pane--doc {
    display: none;
  }
}

/* ≤ 767 px: one column with the tabs Data / Document / Activity. */
@media (max-width: 767px) {
  .review {
    gap: 0;
    grid-template-areas:
      "data"
      "doc";
    margin: calc(-1 * var(--space-12)) calc(-1 * var(--space-16)) 0;
  }

  .pane {
    border: 0;
    border-radius: 0;
  }

  .doc-toggle {
    display: none;
  }

  .phone-tabs {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    border-bottom: 1px solid var(--line);
    background: var(--win);
  }

  .phone-tab {
    height: var(--size-lg);
    border: 0;
    background: transparent;
    color: var(--muted);
    font-size: var(--fs-14);
    font-weight: 500;
    cursor: pointer;
  }

  .phone-tab[aria-selected="true"] {
    color: var(--ink);
    box-shadow: inset 0 -2px 0 var(--ink);
  }

  .phone-tab:focus-visible {
    outline-offset: var(--focus-offset-inset);
  }

  .pane--data {
    grid-template-rows: auto auto auto;
  }

  .pane--doc,
  .pane--doc.is-open {
    display: none;
    height: auto;
  }

  .review--tab-document .pane--doc {
    display: block;
    min-height: 480px;
  }

  .review--tab-document .panel-body,
  .review--tab-activity .data-sections,
  .review--tab-activity .truncated,
  .review--tab-data .activity {
    display: none;
  }
}

/* Not found */
.not-found {
  display: grid;
  gap: var(--space-12);
  justify-items: center;
  align-content: start;
  padding: var(--space-72) var(--space-16);
  text-align: center;
}

.not-found-code {
  font-family: var(--font-mono);
  color: var(--muted);
}

.not-found-title {
  font-family: var(--font-head);
  font-size: var(--fs-21);
  letter-spacing: var(--tracking-head);
  color: var(--ink);
}

.not-found-lead {
  color: var(--muted);
}
</style>
