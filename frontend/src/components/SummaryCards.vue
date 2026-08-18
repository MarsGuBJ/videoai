<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  props: ["cards"]
});
</script>

<template>
  <div class="version-summary">
    <div class="summary-card" v-for="card in cards" :key="card.label">
      <h4>{{ card.label }}</h4>
      <strong>{{ card.value }}</strong>
    </div>
  </div>
</template>
