<script lang="ts">
import { defineComponent } from "vue";
import NavSubGroup from "./NavSubGroup.vue";
import { isActiveNav } from "../store";

export default defineComponent({
  props: ["groups", "route", "collapsed"],
  emits: ["navigate", "toggle-sidebar"],
  components: { NavSubGroup },
  data() {
    return {
      collapsedGroups: {} as Record<string, boolean>
    };
  },
  mountedLegacy() {
    this.$nextTick(() => {
      const page = this.$el;
      const labels = page.querySelectorAll('.exact-source-form .deploy-field > label, .exact-source-switch-form .deploy-field > label');
      labels.forEach((label: any) => { label.hidden = true; });
      const placeholders = [
        ['input[v-model="onlineStart"]', '开始时间'],
        ['input[v-model="onlineEnd"]', '结束时间']
      ];
      placeholders.forEach(([selector, text]) => {
        page.querySelectorAll(selector).forEach((input: any) => {
          input.placeholder = text;
          input.setAttribute('aria-label', text);
        });
      });
      page.querySelectorAll('.exact-source-form .exact-tree-trigger').forEach((button: any) => {
        button.setAttribute('aria-label', '区域 / 监控点');
      });
      page.querySelectorAll('.exact-source-switch-form .exact-tree-trigger').forEach((button: any) => {
        button.setAttribute('aria-label', '录像设备');
      });
    });
  },
  methods: {
    isActiveNav,
    isGroupCollapsed(title: string) {
      return Boolean(this.collapsedGroups[title]);
    },
    toggleGroup(title: string) {
      this.collapsedGroups[title] = !this.collapsedGroups[title];
    },
    itemTitle(item: any) {
      return this.collapsed ? item.label : "";
    }
  }
});
</script>

<template>
  <aside class="sidebar" :class="{ 'sidebar-collapsed': collapsed }" aria-label="系统菜单">
    <div class="brand" :title="collapsed ? '视觉大模型平台' : ''">
      <img class="brand-mark" src="/sdlogo.png" alt="" aria-hidden="true" />
      <span class="brand-text">视觉大模型平台</span>
    </div>
    <button class="sidebar-toggle" type="button" :title="collapsed ? '展开菜单' : '收起菜单'" :aria-label="collapsed ? '展开菜单' : '收起菜单'" @click="$emit('toggle-sidebar')">{{ collapsed ? '&#xf054;' : '&#xf053;' }}</button>
    <nav class="nav">
      <template v-for="group in groups" :key="group.key || group.title">
        <button v-if="group.key" class="nav-item nav-top-item" type="button" :class="{ active: isActiveNav(group.key, route) }" :title="itemTitle(group)" @click="$emit('navigate', group)">
          <span class="ico" aria-hidden="true">{{ group.icon }}</span>
          <span class="nav-label">{{ group.label }}</span>
        </button>
        <div v-else class="nav-group" :class="{ collapsed: isGroupCollapsed(group.title) }">
          <button class="nav-section" type="button" :aria-expanded="!isGroupCollapsed(group.title)" :aria-label="(isGroupCollapsed(group.title) ? '展开' : '收起') + group.title" @click="toggleGroup(group.title)">
            <span class="ico" aria-hidden="true">{{ group.icon }}</span>
            <span class="nav-section-label">{{ group.title }}</span>
            <span class="nav-caret" aria-hidden="true">&#xf078;</span>
          </button>
          <nav-sub-group :items="group.items" :route="route" :collapsed="collapsed" :collapsed-groups="collapsedGroups" @navigate="$emit('navigate', $event)" @toggle-group="toggleGroup"></nav-sub-group>
        </div>
      </template>
    </nav>
  </aside>
</template>
