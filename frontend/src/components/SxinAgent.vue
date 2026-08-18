<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "SxinAgent",
  emits: ["close"]
});
</script>

<template>
  <section class="sxin-embed-fullscreen" aria-label="SXin智能体-视觉多模态2">
    <iframe class="sxin-embed-frame" src="/sxin-agent.html" title="SXin智能体-视觉多模态2"></iframe>
    <button class="sxin-embed-exit" @click="$emit('close')">退出SXin</button>
  </section>
</template>
