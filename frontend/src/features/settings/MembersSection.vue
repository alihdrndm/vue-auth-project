<script setup lang="ts">
// Settings › Members (HANDOFF: admins only, not in a sandbox — `403 SANDBOX_RESTRICTED`):
// the people of the organisation, their roles, deactivation, and inviting someone. The
// one-time password of a new member is shown once, in the invite dialog, and then forgotten.
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, reactive, ref } from "vue";

import { api, ApiError, unwrap } from "../../api/client";
import { queryKeys } from "../../api/query";
import type { components } from "../../api/schema";
import Badge from "../../components/ui/Badge.vue";
import Button from "../../components/ui/Button.vue";
import DataTable, {
  type DataTableColumn,
} from "../../components/ui/DataTable.vue";
import Dialog from "../../components/ui/Dialog.vue";
import ErrorState from "../../components/ui/ErrorState.vue";
import Icon from "../../components/ui/Icon.vue";
import Select from "../../components/ui/Select.vue";
import Skeleton, {
  type SkeletonColumn,
} from "../../components/ui/Skeleton.vue";
import TextInput from "../../components/ui/TextInput.vue";
import { useToast } from "../../components/ui/useToast";
import { useSessionStore } from "../../stores/session";
import { ROLE_LABEL } from "../exports/exports";
import { problemMessage } from "../review-screen/actions";

type Member = components["schemas"]["Member"];
type Role = components["schemas"]["RoleEnum"];

const props = defineProps<{
  /** Why members can't be managed here (not an admin, or a sandbox); null when they can. */
  lockedReason: string | null;
}>();

const session = useSessionStore();
const queryClient = useQueryClient();
const toast = useToast();

const ROLE_OPTIONS = (Object.keys(ROLE_LABEL) as Role[]).map((role) => ({
  value: role,
  label: ROLE_LABEL[role],
}));

const enabled = computed(() => props.lockedReason === null);

const members = useQuery({
  queryKey: queryKeys.membersPage(1),
  queryFn: async () => {
    const all: Member[] = [];
    for (let page = 1; page <= 20; page += 1) {
      const data = unwrap(
        await api.GET("/api/v1/members", {
          params: { query: page > 1 ? { page } : {} },
        }),
      );
      all.push(...data.results);
      if (!data.next) break;
    }
    return all;
  },
  enabled,
});

const error = computed(() => {
  if (!members.isError.value || members.data.value) return null;
  const value = members.error.value;
  if (value instanceof ApiError)
    return { title: value.title, detail: value.detail };
  return {
    title: "Couldn’t load the members",
    detail: value instanceof Error ? value.message : undefined,
  };
});

function isMe(member: Member): boolean {
  const me = session.me?.user;
  return me !== undefined && (member.id === me.id || member.email === me.email);
}

// --- Changing a member ---------------------------------------------------------------------

const busyId = ref<string | null>(null);

async function update(
  member: Member,
  body: components["schemas"]["PatchedMemberUpdate"],
  message: string,
): Promise<void> {
  if (busyId.value) return;
  busyId.value = member.id;
  try {
    unwrap(
      await api.PATCH("/api/v1/members/{member_id}", {
        params: { path: { member_id: member.id } },
        body,
      }),
    );
    toast.show({ kind: "success", message });
    await queryClient.invalidateQueries({ queryKey: queryKeys.members() });
  } catch (caught) {
    toast.show({ kind: "error", message: problemMessage(caught) });
  } finally {
    busyId.value = null;
  }
}

function changeRole(member: Member, role: string): void {
  if (role === member.role) return;
  const next = role as Role;
  void update(
    member,
    { role: next },
    `${member.name} is now ${ROLE_LABEL[next].toLowerCase()}.`,
  );
}

function toggleActive(member: Member): void {
  void update(
    member,
    { is_active: !member.is_active },
    member.is_active
      ? `${member.name} can no longer sign in.`
      : `${member.name} can sign in again.`,
  );
}

const COLUMNS: DataTableColumn<Member>[] = [
  { key: "name", label: "Name" },
  { key: "email", label: "Email", value: (row) => row.email },
  { key: "role", label: "Role", width: "168px" },
  { key: "status", label: "Status", width: "200px" },
];

const SKELETON_COLUMNS: SkeletonColumn[] = [
  { track: "minmax(0, 1fr)" },
  { track: "minmax(0, 1fr)" },
  { track: "168px" },
  { track: "200px" },
];

// --- Inviting ----------------------------------------------------------------------------

const inviteOpen = ref(false);
const inviting = ref(false);
const tried = ref(false);
const form = reactive({ email: "", name: "", role: "" });
const serverErrors = ref<Record<string, string>>({});
/** The new member and their one-time password; cleared when the dialog closes. */
const created = ref<{ name: string; email: string; password: string } | null>(
  null,
);

const dialogOpen = computed({
  get: () => inviteOpen.value,
  set: (value: boolean) => {
    if (value || inviting.value) return;
    inviteOpen.value = false;
    created.value = null;
  },
});

const formErrors = computed(() => {
  const errors: Record<string, string | undefined> = {
    email: serverErrors.value.email,
    name: serverErrors.value.name,
    role: serverErrors.value.role,
  };
  if (tried.value) {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim()))
      errors.email ??= "Enter an email address.";
    if (form.name.trim() === "") errors.name ??= "Enter their name.";
    if (form.role === "")
      errors.role ??= "Choose a role before you invite someone.";
  }
  return errors;
});

function openInvite(): void {
  form.email = "";
  form.name = "";
  form.role = "";
  tried.value = false;
  serverErrors.value = {};
  created.value = null;
  inviteOpen.value = true;
}

async function invite(): Promise<void> {
  tried.value = true;
  serverErrors.value = {};
  if (Object.values(formErrors.value).some(Boolean)) return;
  inviting.value = true;
  try {
    const result = unwrap(
      await api.POST("/api/v1/members", {
        body: {
          email: form.email.trim(),
          name: form.name.trim(),
          role: form.role as Role,
        },
      }),
    );
    created.value = {
      name: result.name,
      email: result.email,
      password: result.one_time_password,
    };
    void queryClient.invalidateQueries({ queryKey: queryKeys.members() });
  } catch (caught) {
    if (caught instanceof ApiError && caught.errors.length > 0) {
      serverErrors.value = Object.fromEntries(
        caught.errors.map((entry) => [
          entry.path.split(".").pop() ?? entry.path,
          entry.message,
        ]),
      );
    } else {
      toast.show({ kind: "error", message: problemMessage(caught) });
    }
  } finally {
    inviting.value = false;
  }
}

const copied = ref(false);

async function copyPassword(): Promise<void> {
  const password = created.value?.password;
  if (!password || !navigator.clipboard) return;
  try {
    await navigator.clipboard.writeText(password);
    copied.value = true;
    setTimeout(() => {
      copied.value = false;
    }, 2000);
  } catch {
    // The password stays on screen to copy by hand.
  }
}
</script>

<template>
  <section class="pane" aria-labelledby="members-title">
    <div class="pane-head">
      <h2 id="members-title" class="pane-title">Members</h2>
      <Badge variant="label">Admins only</Badge>
      <span class="spacer" />
      <Button
        size="sm"
        icon="plus"
        :disabled-reason="lockedReason ?? undefined"
        @click="openInvite"
        >Invite member</Button
      >
    </div>

    <p v-if="lockedReason" class="note locked" role="note">
      <Icon name="lock" :size="16" class="note-icon" />{{ lockedReason }}
    </p>
    <template v-else>
      <Skeleton
        v-if="members.isPending.value"
        label="Loading members"
        :columns="SKELETON_COLUMNS"
        :rows="3"
      />
      <ErrorState
        v-else-if="error"
        :level="3"
        :title="error.title"
        :detail="error.detail"
        :retrying="members.isFetching.value"
        @retry="members.refetch()"
      />
      <p v-else-if="(members.data.value ?? []).length === 0" class="empty-line">
        No members yet.
      </p>
      <DataTable
        v-else
        caption="Members"
        :columns="COLUMNS"
        :rows="members.data.value ?? []"
        :row-key="(row) => row.id"
        :clickable-rows="false"
      >
        <template #cell-name="{ row }">
          <span class="name"
            >{{ row.name
            }}<Badge v-if="isMe(row)" variant="label">You</Badge></span
          >
        </template>
        <template #cell-role="{ row }">
          <span class="role-cell"
            ><Select
              :model-value="row.role"
              :label="`Role of ${row.name}`"
              :options="ROLE_OPTIONS"
              :disabled="isMe(row) || busyId !== null"
              :hint="isMe(row) ? 'You can’t change your own role.' : undefined"
              @update:model-value="changeRole(row, $event)"
          /></span>
        </template>
        <template #cell-status="{ row }">
          <span class="status">
            <span :class="row.is_active ? 'active' : 'muted'">{{
              row.is_active ? "Active" : "Inactive"
            }}</span>
            <Button
              v-if="!isMe(row)"
              size="sm"
              variant="ghost"
              :loading="busyId === row.id"
              :disabled="busyId !== null && busyId !== row.id"
              @click="toggleActive(row)"
              >{{ row.is_active ? "Deactivate" : "Reactivate" }}</Button
            >
          </span>
        </template>
      </DataTable>
    </template>

    <Dialog
      v-model:open="dialogOpen"
      :title="created ? `${created.name} can sign in now` : 'Invite a member'"
      :description="
        created
          ? 'This password is shown only once. Give it to them now; they sign in with it and their email address.'
          : 'They sign in with their email address and a one-time password shown after this step.'
      "
      size="md"
    >
      <div v-if="created" class="password">
        <span class="small muted">{{ created.email }}</span>
        <code class="password-value">{{ created.password }}</code>
        <Button size="sm" icon="copy" @click="copyPassword">{{
          copied ? "Copied" : "Copy password"
        }}</Button>
      </div>
      <form v-else class="invite" novalidate @submit.prevent="invite">
        <TextInput
          v-model="form.email"
          label="Email"
          type="email"
          autocomplete="off"
          :error="formErrors.email"
        />
        <TextInput
          v-model="form.name"
          label="Name"
          autocomplete="off"
          :error="formErrors.name"
        />
        <Select
          v-model="form.role"
          label="Role"
          placeholder="Choose a role"
          :options="ROLE_OPTIONS"
          :error="formErrors.role"
        />
      </form>
      <template #footer>
        <template v-if="created">
          <Button variant="primary" @click="dialogOpen = false">Done</Button>
        </template>
        <template v-else>
          <Button
            variant="ghost"
            :disabled="inviting"
            @click="dialogOpen = false"
            >Cancel</Button
          >
          <Button variant="primary" :loading="inviting" @click="invite">{{
            inviting ? "Inviting…" : "Invite member"
          }}</Button>
        </template>
      </template>
    </Dialog>
  </section>
</template>

<style scoped src="../approvals/pane.css"></style>
<style scoped>
.locked {
  padding: var(--space-16) var(--space-20);
}

.name {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-8);
  color: var(--ink);
  font-weight: 500;
}

.role-cell :deep(.field-label) {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-8);
}

.active {
  color: var(--ok);
  font-size: var(--fs-13);
}

.invite {
  display: grid;
  gap: var(--space-16);
}

.password {
  display: grid;
  justify-items: start;
  gap: var(--space-8);
}

.password-value {
  padding: var(--space-8) var(--space-12);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--soft);
  color: var(--ink);
  font: 500 var(--fs-16) / var(--lh-app) var(--font-mono);
  overflow-wrap: anywhere;
  user-select: all;
}
</style>
