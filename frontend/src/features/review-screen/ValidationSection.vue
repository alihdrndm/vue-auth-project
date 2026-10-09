<script setup lang="ts">
// The Validation section (design "IssueList"): the verdict, which rules checked it, and the
// issues grouped by severity with the rule ID in mono, the plain explanation, the official
// message on expand and the location.
import { computed, ref, useId } from "vue";

import type { components } from "../../api/schema";
import Icon from "../../components/ui/Icon.vue";
import SeverityChip from "../../components/ui/SeverityChip.vue";
import ValidationChip from "./ValidationChip.vue";
import {
  issueGroups,
  messageLang,
  officialSource,
  validationLook,
  validationText,
} from "./validation";

type DocumentDetail = components["schemas"]["DocumentDetail"];

const props = withDefaults(
  defineProps<{
    document: DocumentDetail;
    /** Offers "Show in XML" on each issue. */
    canShowXml?: boolean;
  }>(),
  { canShowXml: false },
);

const emit = defineEmits<{ "show-xml": [] }>();

const id = useId();
const look = computed(() => validationLook(props.document));
const text = computed(() => validationText(props.document));
const groups = computed(() =>
  issueGroups(props.document.validation?.issues ?? []),
);
const checked = computed(
  () =>
    props.document.validation !== undefined &&
    props.document.validation.status !== "not_applicable",
);

const open = ref(new Set<string>());

function key(groupIndex: number, index: number): string {
  return `${groupIndex}-${index}`;
}

function toggle(name: string): void {
  const next = new Set(open.value);
  if (next.has(name)) next.delete(name);
  else next.add(name);
  open.value = next;
}
</script>

<template>
  <section class="section" :aria-labelledby="`${id}-title`">
    <div class="section-head">
      <h2 :id="`${id}-title`" class="section-title">Validation</h2>
      <ValidationChip v-if="look" :look="look" />
    </div>
    <p class="validation-text">
      <Icon :name="checked ? 'file-code' : 'info'" class="validation-icon" />
      <span>{{ text }}</span>
    </p>

    <div
      v-for="(group, groupIndex) in groups"
      :key="group.severity"
      class="issue-group"
    >
      <h3 class="group-title">
        {{ group.title }}
        <span class="group-count">{{ group.issues.length }}</span>
      </h3>
      <article
        v-for="(issue, index) in group.issues"
        :key="key(groupIndex, index)"
        class="issue"
        :class="`issue--${issue.severity}`"
      >
        <header class="issue-head">
          <SeverityChip :severity="issue.severity" />
          <code class="issue-rule">{{ issue.rule_id }}</code>
        </header>
        <div class="issue-body">
          <template v-if="issue.explanation">
            <p class="issue-plain">{{ issue.explanation.plain_text }}</p>
            <p v-if="issue.explanation.fix_hint" class="issue-plain">
              {{ issue.explanation.fix_hint }}
            </p>
          </template>
          <div class="issue-tools">
            <span class="issue-location"
              >Location <code>{{ issue.location || "—" }}</code></span
            >
            <span class="issue-spacer" />
            <button
              v-if="canShowXml"
              type="button"
              class="link-button"
              @click="emit('show-xml')"
            >
              <Icon name="file-code" />Show in XML
            </button>
            <button
              v-if="issue.explanation"
              type="button"
              class="link-button"
              :aria-expanded="
                open.has(key(groupIndex, index)) ? 'true' : 'false'
              "
              :aria-controls="`${id}-msg-${key(groupIndex, index)}`"
              @click="toggle(key(groupIndex, index))"
            >
              {{
                open.has(key(groupIndex, index))
                  ? "Hide official message"
                  : "Show official message"
              }}<Icon
                name="chevron-down"
                class="chevron"
                :class="{ 'is-open': open.has(key(groupIndex, index)) }"
              />
            </button>
          </div>
          <div
            v-if="!issue.explanation || open.has(key(groupIndex, index))"
            :id="`${id}-msg-${key(groupIndex, index)}`"
            class="issue-official"
          >
            <span class="issue-source">{{ officialSource(issue) }}</span>
            <blockquote class="issue-message" :lang="messageLang(issue)">
              {{ issue.message }}
            </blockquote>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped src="./section.css"></style>

<style scoped>
.validation-text {
  display: flex;
  align-items: flex-start;
  gap: var(--space-8);
  font-size: var(--fs-13);
  color: var(--text);
}

.validation-icon {
  flex: none;
  margin-top: 1px;
  color: var(--muted);
}

.issue-group {
  display: grid;
  gap: var(--space-8);
}

.group-title {
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
}

.group-count {
  font-family: var(--font-mono);
  font-weight: 400;
  color: var(--muted);
}

.issue {
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  overflow: hidden;
}

.issue-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-8) var(--space-12);
  padding: var(--space-12) var(--space-16);
  background: var(--soft);
}

.issue--fatal .issue-head {
  background: var(--block-soft);
}

.issue--warning .issue-head {
  background: var(--warn-soft);
}

.issue--information .issue-head {
  background: var(--info-soft);
}

.issue-rule {
  font-size: var(--fs-13);
  font-weight: 500;
  color: var(--ink);
}

.issue-body {
  display: grid;
  gap: var(--space-12);
  padding: var(--space-12) var(--space-16) var(--space-16);
}

.issue-plain {
  font-size: var(--fs-14);
  text-wrap: pretty;
}

.issue-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-8) var(--space-16);
}

.issue-spacer {
  flex: 1;
}

.issue-location {
  font-size: var(--fs-12);
  color: var(--muted);
  overflow-wrap: anywhere;
}

.issue-location code {
  font-size: var(--fs-12);
  color: var(--ink);
}

.link-button {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--size-sm);
  padding: 0 var(--space-8);
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text);
  font-size: var(--fs-13);
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
}

.link-button:hover {
  background: var(--soft);
  color: var(--ink);
}

.chevron.is-open {
  transform: rotate(180deg);
}

.issue-official {
  display: grid;
  gap: var(--space-4);
}

.issue-source {
  font-size: var(--fs-12);
  color: var(--muted);
}

.issue-message {
  margin: 0;
  padding: var(--space-12);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bar);
  font-family: var(--font-mono);
  font-size: var(--fs-13);
  color: var(--ink);
  overflow-wrap: anywhere;
}

@media (max-width: 767px) {
  .link-button {
    height: var(--size-lg);
  }
}
</style>
