<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>复核类型管理</h1><p>维护复核类型配置与定时复核任务</p></div></div>
    <div class="exact-mode-tabs" style="margin-bottom: 14px" role="tablist">
      <button v-for="tab in tabs" :key="tab.key" class="exact-mode-tab" :class="{ active: activeTab === tab.key }" role="tab" :aria-selected="activeTab === tab.key" @click="activeTab = tab.key">{{ tab.title }}</button>
    </div>
    <review-type-list-page v-if="activeTab === 'types'" :embedded="true" :store="store" :state="state" :selected-version="selectedVersion" :selected-deploy-task="selectedDeployTask" :selected-event="selectedEvent" :selected-algorithm="selectedAlgorithm"></review-type-list-page>
    <review-schedules-page v-else :embedded="true" :store="store" :state="state" :selected-version="selectedVersion" :selected-deploy-task="selectedDeployTask" :selected-event="selectedEvent" :selected-algorithm="selectedAlgorithm"></review-schedules-page>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import ReviewTypeListPage from "./ReviewTypeListPage.vue";
import ReviewSchedulesPage from "./ReviewSchedulesPage.vue";

export default defineComponent({
  name: "ReviewTypesPage",
  components: { ReviewTypeListPage, ReviewSchedulesPage },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  data() {
    return {
      activeTab: "types",
      tabs: [
        { key: "types", title: "复核类型" },
        { key: "schedules", title: "定时任务" }
      ]
    };
  },
});
</script>
