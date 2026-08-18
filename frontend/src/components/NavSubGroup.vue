<script lang="ts">
import { defineComponent } from "vue";
import { isActiveNav } from "../store";

export default defineComponent({
  name: "NavSubGroup",
  props: ["items", "route", "collapsed", "collapsedGroups"],
  emits: ["navigate", "toggle-group"],
  computed: {
    itemsHeight() {
      const leafHeight = 34;
      const groupHeaderHeight = 32;
      const groupMargin = 10;
      return this.items.reduce((sum: number, item: any) => {
        if (item.key) return sum + leafHeight;
        return sum + groupHeaderHeight + groupMargin + this.computeSubHeight(item);
      }, 0);
    }
  },
  methods: {
    isActiveNav,
    isCollapsed(title: string) {
      return Boolean(this.collapsedGroups[title]);
    },
    computeSubHeight(group: any): number {
      const leafHeight = 34;
      const groupHeaderHeight = 32;
      const groupMargin = 10;
      return (group.items || []).reduce((sum: number, item: any) => {
        if (item.key) return sum + leafHeight;
        return sum + groupHeaderHeight + groupMargin + this.computeSubHeight(item);
      }, 0);
    }
  }
});
</script>

<template>
  <div class="nav-sub-items" :style="{ '--nav-items-height': itemsHeight + 'px' }">
    <template v-for="item in items" :key="item.key || item.title">
      <button v-if="item.key" class="nav-item" type="button" :class="{ active: isActiveNav(item.key, route) }" :title="item.label" @click="$emit('navigate', item)">
        <span class="ico" aria-hidden="true">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
      <div v-else class="nav-group nav-sub-group" :class="{ collapsed: isCollapsed(item.title) }">
        <button class="nav-section nav-sub-section" type="button" :aria-expanded="!isCollapsed(item.title)" :aria-label="(isCollapsed(item.title) ? '展开' : '收起') + item.title" @click="$emit('toggle-group', item.title)">
          <span class="ico" aria-hidden="true">{{ item.icon }}</span>
          <span class="nav-section-label">{{ item.title }}</span>
          <span class="nav-caret" aria-hidden="true">&#xf078;</span>
        </button>
        <nav-sub-group :items="item.items" :route="route" :collapsed="collapsed" :collapsed-groups="collapsedGroups" @navigate="$emit('navigate', $event)" @toggle-group="$emit('toggle-group', $event)"></nav-sub-group>
      </div>
    </template>
  </div>
</template>
