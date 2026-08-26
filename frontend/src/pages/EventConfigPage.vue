<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件配置</h1><p>配置事件字典、去重和消息订阅</p></div></div>
    <div class="exact-mode-tabs" style="margin-bottom: 14px" role="tablist">
      <button v-for="tab in tabs" :key="tab.key" class="exact-mode-tab" :class="{ active: activeTab === tab.key }" role="tab" :aria-selected="activeTab === tab.key" @click="activeTab = tab.key">{{ tab.title }}</button>
    </div>
    <event-config-info-page v-if="activeTab === 'info'" :embedded="true" :store="store" :state="state" :selected-version="selectedVersion" :selected-deploy-task="selectedDeployTask" :selected-event="selectedEvent" :selected-algorithm="selectedAlgorithm"></event-config-info-page>
    <event-config-dedup-page v-else-if="activeTab === 'dedup'" :embedded="true" :store="store" :state="state" :selected-version="selectedVersion" :selected-deploy-task="selectedDeployTask" :selected-event="selectedEvent" :selected-algorithm="selectedAlgorithm"></event-config-dedup-page>
    <event-config-subscriptions-page v-else :embedded="true" :store="store" :state="state" :selected-version="selectedVersion" :selected-deploy-task="selectedDeployTask" :selected-event="selectedEvent" :selected-algorithm="selectedAlgorithm"></event-config-subscriptions-page>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import EventConfigInfoPage from "./EventConfigInfoPage.vue";
import EventConfigDedupPage from "./EventConfigDedupPage.vue";
import EventConfigSubscriptionsPage from "./EventConfigSubscriptionsPage.vue";

export default defineComponent({
  name: "EventConfigPage",
  components: { EventConfigInfoPage, EventConfigDedupPage, EventConfigSubscriptionsPage },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  data() {
    return {
      activeTab: "info",
      tabs: [
        { key: "info", title: "事件信息配置" },
        { key: "dedup", title: "事件去重配置" },
        { key: "subscriptions", title: "消息订阅配置" }
      ]
    };
  },
});
</script>
