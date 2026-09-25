<template>
  <div ref="box" class="event-config-source">
    <input
      :value="modelValue"
      class="input event-config-source-input"
      role="combobox"
      :aria-label="ariaLabel"
      aria-haspopup="listbox"
      :aria-expanded="open ? 'true' : 'false'"
      :aria-controls="listId"
      :placeholder="placeholder"
      @focus="openMenu"
      @click="openMenu"
      @input="onInput"
      @keydown.down.prevent="move(1)"
      @keydown.up.prevent="move(-1)"
      @keydown.enter.prevent="commit"
      @keydown.esc="closeMenu"
    />
    <span class="event-config-source-caret" :class="{ open }" aria-hidden="true"></span>
    <ul v-if="open && suggestions.length" :id="listId" class="event-config-source-menu" role="listbox">
      <li
        v-for="(option, index) in suggestions"
        :key="option"
        role="option"
        :aria-selected="modelValue === option ? 'true' : 'false'"
        :class="{ active: index === activeIndex, selected: modelValue === option }"
        @mouseenter="activeIndex = index"
        @mousedown.prevent="pick(option)"
      >{{ option }}</li>
    </ul>
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

let seq = 0;

// 可输入下拉框（事件来源）：外形与页面上的原生 select 一致（复用 .event-config-source* 样式），
// 候选菜单与下拉框左对齐、等宽，支持手动输入、↑↓ + Enter、Esc 与点击空白收起。
// 复用方：事件配置 → 事件信息配置（新增/修改配置信息）、消息订阅配置。
export default defineComponent({
  name: "EventSourceSelect",
  props: {
    modelValue: { type: String, default: "" },
    options: { type: Array, default: () => ["中心推理平台", "云边协同平台"] },
    placeholder: { type: String, default: "请选择或输入事件来源" },
    ariaLabel: { type: String, default: "事件来源" }
  },
  emits: ["update:modelValue"],
  data() {
    return {
      open: false,
      activeIndex: -1,
      listId: `event-source-options-${(seq += 1)}`
    };
  },
  computed: {
    suggestions(): string[] {
      const value = String(this.modelValue || "").trim().toLowerCase();
      if (!value) return this.options as string[];
      // 已选中某个来源时展开全部候选，便于直接改选；只有输入了半截关键字才做过滤
      const exact = (this.options as string[]).some(option => option.toLowerCase() === value);
      if (exact) return this.options as string[];
      return (this.options as string[]).filter(option => option.toLowerCase().includes(value));
    }
  },
  mounted() {
    document.addEventListener("click", this.onDocumentClick);
  },
  unmounted() {
    document.removeEventListener("click", this.onDocumentClick);
  },
  methods: {
    openMenu() {
      this.open = true;
      this.activeIndex = this.suggestions.indexOf(this.modelValue);
    },
    closeMenu() {
      this.open = false;
      this.activeIndex = -1;
    },
    onInput(event: Event) {
      this.$emit("update:modelValue", (event.target as HTMLInputElement).value);
      this.open = true;
    },
    move(step: number) {
      const total = this.suggestions.length;
      if (!total) return;
      if (!this.open) { this.openMenu(); return; }
      const next = this.activeIndex + step;
      this.activeIndex = next < 0 ? total - 1 : (next >= total ? 0 : next);
    },
    commit() {
      const option = this.suggestions[this.activeIndex];
      if (this.open && option) { this.pick(option); return; }
      this.closeMenu();
    },
    pick(option: string) {
      this.$emit("update:modelValue", option);
      this.closeMenu();
    },
    onDocumentClick(event: MouseEvent) {
      const box = this.$refs.box as unknown as HTMLElement | undefined;
      if (!box || !box.contains(event.target as Node)) this.closeMenu();
    }
  }
});
</script>
