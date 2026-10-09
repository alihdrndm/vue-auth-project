<script setup lang="ts">
// Settings (design "Eingang App Screens" ?screen=settings, HANDOFF `/app/settings`): the
// organisation's name and VAT ID, four-eyes and the two windows (admins only; in a sandbox only
// the name), Save when something changed; members; and the AI budget meters from /stats.
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, ref, watch } from "vue";

import { api, ApiError, unwrap } from "../api/client";
import { queryKeys } from "../api/query";
import Button from "../components/ui/Button.vue";
import ErrorState from "../components/ui/ErrorState.vue";
import Icon from "../components/ui/Icon.vue";
import Skeleton, { type SkeletonColumn } from "../components/ui/Skeleton.vue";
import TextInput from "../components/ui/TextInput.vue";
import { useToast } from "../components/ui/useToast";
import MembersSection from "../features/settings/MembersSection.vue";
import MeterBar from "../features/settings/MeterBar.vue";
import SettingSwitch from "../features/settings/SettingSwitch.vue";
import {
  ADMIN_REASON,
  type DraftErrors,
  draftFrom,
  lockReason,
  type OrgDraft,
  type Organization,
  patchFrom,
  SANDBOX_REASON,
  validateDraft,
} from "../features/settings/settings";
import { problemMessage } from "../features/review-screen/actions";
import { plural } from "../features/review-screen/format";
import { useSessionStore } from "../stores/session";

const session = useSessionStore();
const queryClient = useQueryClient();
const toast = useToast();

const org = useQuery({
  queryKey: queryKeys.organization(),
  queryFn: async () => unwrap(await api.GET("/api/v1/organization")),
});

const stats = useQuery({
  queryKey: queryKeys.stats(),
  queryFn: async () => unwrap(await api.GET("/api/v1/stats")),
});

const sandbox = computed(
  () => org.data.value?.kind === "sandbox" || session.isSandbox,
);

// --- Organisation form ---------------------------------------------------------------------

const draft = ref<OrgDraft | null>(null);
const tried = ref(false);
const saving = ref(false);
const serverErrors = ref<DraftErrors>({});

const dirty = computed(() => {
  if (!org.data.value || !draft.value) return false;
  return Object.keys(patchFrom(org.data.value, draft.value)).length > 0;
});

watch(
  () => org.data.value,
  (value) => {
    // Fresh data replaces the form unless the viewer is in the middle of a change.
    if (value && (!draft.value || !dirty.value)) draft.value = draftFrom(value);
  },
  { immediate: true },
);

const errors = computed<DraftErrors>(() => ({
  ...(tried.value && draft.value ? validateDraft(draft.value) : {}),
  ...serverErrors.value,
}));

watch(
  draft,
  () => {
    serverErrors.value = {};
  },
  { deep: true },
);

function reason(field: keyof OrgDraft): string | null {
  return lockReason(field, session.role, sandbox.value);
}

function hint(field: keyof OrgDraft, help?: string): string | undefined {
  const why = reason(field);
  if (why && help) return `${why} ${help}`;
  return why ?? help;
}

const formNote = computed(() => {
  if (session.role !== "admin") return ADMIN_REASON;
  if (sandbox.value) return `${SANDBOX_REASON} Only the name can change here.`;
  return null;
});

async function save(): Promise<void> {
  const current = org.data.value;
  if (!current || !draft.value || saving.value) return;
  tried.value = true;
  serverErrors.value = {};
  if (Object.keys(validateDraft(draft.value)).length > 0) return;
  const body = patchFrom(current, draft.value);
  if (Object.keys(body).length === 0) return;
  saving.value = true;
  try {
    const updated: Organization = unwrap(
      await api.PATCH("/api/v1/organization", { body }),
    );
    queryClient.setQueryData(queryKeys.organization(), updated);
    draft.value = draftFrom(updated);
    tried.value = false;
    if (session.me) {
      session.me = {
        ...session.me,
        organization: {
          ...session.me.organization,
          name: updated.name,
          vat_id: updated.vat_id,
          four_eyes: updated.four_eyes,
        },
      };
    }
    toast.show({ kind: "success", message: "Settings saved." });
    // Four-eyes changes who may approve what.
    void queryClient.invalidateQueries({ queryKey: queryKeys.documents.all() });
  } catch (caught) {
    if (caught instanceof ApiError && caught.errors.length > 0) {
      serverErrors.value = Object.fromEntries(
        caught.errors.map((entry) => [
          entry.path.split(".").pop() ?? entry.path,
          entry.message,
        ]),
      ) as DraftErrors;
    } else {
      toast.show({ kind: "error", message: problemMessage(caught) });
    }
  } finally {
    saving.value = false;
  }
}

const orgError = computed(() => {
  if (!org.isError.value || org.data.value) return null;
  const value = org.error.value;
  if (value instanceof ApiError)
    return { title: value.title, detail: value.detail };
  return {
    title: "Couldn’t load the settings",
    detail: value instanceof Error ? value.message : undefined,
  };
});

const SKELETON_COLUMNS: SkeletonColumn[] = [
  { track: "minmax(0, 1fr)" },
  { track: "minmax(0, 1fr)" },
];

// --- Members and AI budget -------------------------------------------------------------------

const membersReason = computed(() => {
  if (session.role !== "admin") return "Only admins can manage members.";
  if (sandbox.value) return SANDBOX_REASON;
  return null;
});

const llm = computed(() => stats.data.value?.llm ?? null);
const statsError = computed(() => {
  if (!stats.isError.value || stats.data.value) return null;
  const value = stats.error.value;
  if (value instanceof ApiError)
    return { title: value.title, detail: value.detail };
  return { title: "Couldn’t load the AI budget", detail: undefined };
});
</script>

<template>
  <section class="page settings" aria-labelledby="settings-title">
    <h1 id="settings-title" class="page-title">Settings</h1>

    <Skeleton
      v-if="org.isPending.value"
      label="Loading the settings"
      header
      :columns="SKELETON_COLUMNS"
      :rows="3"
    />
    <div v-else-if="orgError" class="pane">
      <ErrorState
        :title="orgError.title"
        :detail="orgError.detail"
        :retrying="org.isFetching.value"
        @retry="org.refetch()"
      />
    </div>

    <form
      v-else-if="draft"
      class="page"
      novalidate
      aria-label="Organisation settings"
      @submit.prevent="save"
    >
      <p v-if="formNote" class="note" role="note">
        <Icon name="lock" :size="16" class="note-icon" />{{ formNote }}
      </p>

      <section class="pane" aria-labelledby="org-title">
        <div class="pane-head">
          <h2 id="org-title" class="pane-title">Organisation</h2>
        </div>
        <div class="pane-body grid-2">
          <TextInput
            v-model="draft.name"
            label="Name"
            :disabled="reason('name') !== null"
            :hint="hint('name')"
            :error="errors.name"
          />
          <TextInput
            v-model="draft.vat_id"
            label="VAT ID"
            mono
            :disabled="reason('vat_id') !== null"
            :hint="
              hint('vat_id', 'Used to match the buyer on incoming invoices.')
            "
            :error="errors.vat_id"
          />
        </div>
      </section>

      <section class="pane" aria-labelledby="rules-title">
        <div class="pane-head">
          <h2 id="rules-title" class="pane-title">Review and approval</h2>
        </div>
        <div class="pane-body">
          <SettingSwitch
            v-model="draft.four_eyes"
            label="Four-eyes approval"
            description="Whoever reviews an invoice can’t also approve it."
            :disabled="reason('four_eyes') !== null"
            :reason="reason('four_eyes') ?? undefined"
          />
        </div>
        <div class="pane-body grid-2 rules">
          <TextInput
            v-model="draft.duplicate_window_days"
            label="Duplicate window (days)"
            :disabled="reason('duplicate_window_days') !== null"
            :hint="
              hint(
                'duplicate_window_days',
                'Flag an invoice when the same supplier sends the same number within this many days.',
              )
            "
            :error="errors.duplicate_window_days"
          />
          <TextInput
            v-model="draft.reminder_after_days"
            label="Reminder after (days)"
            :disabled="reason('reminder_after_days') !== null"
            :hint="
              hint(
                'reminder_after_days',
                'Remind the approver when an invoice has waited this long.',
              )
            "
            :error="errors.reminder_after_days"
          />
        </div>
      </section>

      <div class="save-bar">
        <span v-if="dirty" class="muted">You have unsaved changes.</span>
        <Button
          type="submit"
          variant="primary"
          :loading="saving"
          :disabled="!dirty"
          >{{ saving ? "Saving…" : "Save changes" }}</Button
        >
      </div>
    </form>

    <MembersSection :locked-reason="membersReason" />

    <section class="pane" aria-labelledby="ai-title">
      <div class="pane-head">
        <h2 id="ai-title" class="pane-title">AI budget</h2>
      </div>
      <div class="pane-body">
        <Skeleton
          v-if="stats.isPending.value"
          label="Loading the AI budget"
          :columns="[{ track: '120px' }, { track: 'minmax(0, 1fr)' }]"
          :rows="2"
        />
        <ErrorState
          v-else-if="statsError"
          :level="3"
          :title="statsError.title"
          :detail="statsError.detail"
          :retrying="stats.isFetching.value"
          @retry="stats.refetch()"
        />
        <template v-else-if="llm">
          <MeterBar
            label="Spent so far"
            name="AI budget spent so far"
            :spent="llm.lifetime_spent_usd"
            :budget="llm.lifetime_budget_usd"
          />
          <MeterBar
            label="This month"
            name="AI budget this month"
            :spent="llm.month_spent_usd"
            :budget="llm.month_budget_usd"
          />
          <p v-if="llm.sandbox_calls_left !== undefined" class="muted">
            {{ plural(llm.sandbox_calls_left, "AI call") }} left in this
            sandbox.
          </p>
          <p class="small muted">
            The budget pays for reading PDF invoices with AI. When it is used
            up, fields are entered by hand.
          </p>
        </template>
      </div>
    </section>
  </section>
</template>

<style scoped src="../features/approvals/pane.css"></style>
<style scoped>
.settings {
  max-width: 880px;
}

.grid-2 {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.rules {
  padding-top: 0;
}

.save-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-12);
}

@media (max-width: 767px) {
  .grid-2 {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
