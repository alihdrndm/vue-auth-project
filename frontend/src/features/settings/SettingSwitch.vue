<script setup lang="ts">
// The design system's Switch (off, on, hover, focus, disabled, disabled-on) with its On / Off
// word. Not in components/ui yet, so it lives with the one screen that uses it.
import { useId } from "vue";

withDefaults(
  defineProps<{
    label: string;
    description?: string;
    disabled?: boolean;
    /** Why it can't be changed; shown under the description. */
    reason?: string;
  }>(),
  { description: undefined, disabled: false, reason: undefined },
);

const checked = defineModel<boolean>({ required: true });

const id = useId();
</script>

<template>
  <div class="switch-row">
    <div class="switch-text">
      <span :id="`${id}-label`" class="switch-label">{{ label }}</span>
      <span v-if="description" :id="`${id}-description`" class="switch-help">{{
        description
      }}</span>
      <span v-if="reason" :id="`${id}-reason`" class="switch-help">{{
        reason
      }}</span>
    </div>
    <button
      type="button"
      role="switch"
      class="switch"
      :class="{ 'is-on': checked }"
      :aria-checked="checked ? 'true' : 'false'"
      :aria-labelledby="`${id}-label`"
      :aria-describedby="
        [description ? `${id}-description` : '', reason ? `${id}-reason` : '']
          .filter(Boolean)
          .join(' ') || undefined
      "
      :disabled="disabled"
      @click="checked = !checked"
    >
      <span class="track" aria-hidden="true"><span class="thumb" /></span>
      <span class="word">{{ checked ? "On" : "Off" }}</span>
    </button>
  </div>
</template>

<style scoped>
.switch-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-16);
}

.switch-text {
  display: grid;
  gap: var(--space-4);
}

.switch-label {
  color: var(--ink);
  font-size: var(--fs-14);
  font-weight: 500;
}

.switch-help {
  color: var(--muted-strong);
  font-size: var(--fs-12);
}

.switch {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: var(--space-8);
  min-height: var(--size-md);
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--ink);
  font-size: var(--fs-13);
  font-weight: 500;
  cursor: pointer;
}

.track {
  position: relative;
  width: 36px;
  height: 20px;
  border-radius: var(--r-pill);
  background: var(--line-strong);
  box-shadow: inset 0 0 0 1px var(--muted);
  transition: background var(--dur-fast) var(--ease-out);
}

.thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: var(--r-pill);
  background: var(--win);
  transition: transform var(--dur-fast) var(--ease-out);
}

.switch.is-on .track {
  background: var(--ink);
  box-shadow: none;
}

.switch.is-on .thumb {
  transform: translateX(16px);
}

.switch:hover:not(:disabled) .track {
  box-shadow: inset 0 0 0 1px var(--ink);
}

.switch:disabled {
  color: var(--muted);
  cursor: not-allowed;
}

.switch:disabled .track {
  background: var(--soft);
  box-shadow: inset 0 0 0 1px var(--line-strong);
}

.switch:disabled.is-on .track {
  background: var(--muted);
}
</style>
