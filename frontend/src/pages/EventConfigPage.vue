<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件配置</h1><p>配置事件字典、接入、去重和消息订阅</p></div></div>
    <div class="event-config-grid">
      <button v-for="entry in entries" :key="entry.title" class="event-config-entry" type="button" :aria-label="'打开' + entry.title" @click="setRoute(entry.route)">
        <span class="event-config-entry-icon" aria-hidden="true">{{ entry.icon }}</span>
        <span class="event-config-entry-copy"><strong>{{ entry.title }}</strong><span>{{ entry.desc }}</span></span>
        <span class="event-config-entry-arrow" aria-hidden="true">&#xf105;</span>
      </button>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

// App provides setRoute via inject; augment the instance type so vue-tsc
// accepts the template's `setRoute(entry.route)` call.
declare module "vue" {
  interface ComponentCustomProperties {
    setRoute: (route: string, options?: any) => void;
  }
}

export default defineComponent({
  name: "EventConfigPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
  },
  computed: {
    entries() {
      return [
        { icon: "", title: "事件信息配置", desc: "复用能力仓事件字典，维护事件等级、状态、图标和排序。", route: "eventConfigInfo" },
        { icon: "", title: "事件接入", desc: "管理外部告警数据源、接口地址、拉取方式和事件映射。", route: "eventConfigIngestion" },
        { icon: "", title: "事件去重配置", desc: "配置时间维度、区域重叠和实时图像相似度去重规则。", route: "eventConfigDedup" },
        { icon: "", title: "消息订阅配置", desc: "维护 MQ/HTTP 推送任务，查看推送日志。", route: "eventConfigSubscriptions" }
      ];
    }
  },
});
</script>
