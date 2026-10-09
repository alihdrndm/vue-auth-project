<script setup lang="ts">
// Uploading from the inbox: the "Upload" button, the drop overlay over the whole window and
// one progress row per file; built out in the next commits.
defineEmits<{ uploaded: [documentId: string] }>();
</script>

<template>
  <div class="upload-zone"></div>
</template>
