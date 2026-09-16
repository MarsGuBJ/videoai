<template>
  <div class="ip-input">
    <template v-for="(seg, i) in segments" :key="i">
      <span v-if="i > 0" class="ip-input-dot">.</span>
      <input
        :ref="(el) => setSegmentRef(el, i)"
        class="input ip-input-segment"
        type="text"
        inputmode="numeric"
        maxlength="3"
        :value="seg"
        :aria-label="`IP地址第${i + 1}段`"
        @input="onInput(i, $event)"
        @keydown="onKeydown(i, $event)"
        @paste="onPaste"
      />
    </template>
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

/**
 * IP 地址专用输入框：四段 0-255 数字，段间自动跳转，支持粘贴完整 IP。
 * v-model 值为 "a.b.c.d" 字符串；四段全空时回传空串。
 */
export default defineComponent({
  name: "IpInput",
  props: {
    modelValue: { type: String, default: "" }
  },
  emits: ["update:modelValue"],
  data() {
    return {
      segments: ["", "", "", ""] as string[],
      segmentEls: [] as (HTMLInputElement | null)[]
    };
  },
  watch: {
    modelValue: {
      immediate: true,
      handler(value: string) {
        const parts = (value || "").split(".");
        const next = [0, 1, 2, 3].map((i) => (/^\d{1,3}$/.test(parts[i] || "") ? parts[i] : ""));
        if (next.join(".") !== this.segments.join(".")) {
          this.segments = next;
        }
      }
    }
  },
  methods: {
    setSegmentRef(el: any, index: number) {
      this.segmentEls[index] = el as HTMLInputElement | null;
    },
    focusSegment(index: number) {
      const el = this.segmentEls[index];
      if (el) {
        el.focus();
        el.select();
      }
    },
    onInput(index: number, event: Event) {
      const target = event.target as HTMLInputElement;
      let value = target.value.replace(/\D/g, "").slice(0, 3);
      if (value && parseInt(value, 10) > 255) {
        value = "255";
      }
      this.segments.splice(index, 1, value);
      if (target.value !== value) {
        target.value = value;
      }
      if (value.length === 3 && index < 3) {
        this.focusSegment(index + 1);
      }
      this.emitValue();
    },
    onKeydown(index: number, event: KeyboardEvent) {
      if (event.key === "." || event.key === "。" || event.key === "Decimal") {
        event.preventDefault();
        if (index < 3) this.focusSegment(index + 1);
        return;
      }
      if (event.key === "Backspace" && !this.segments[index] && index > 0) {
        event.preventDefault();
        this.focusSegment(index - 1);
      }
    },
    onPaste(event: ClipboardEvent) {
      const text = (event.clipboardData ? event.clipboardData.getData("text") : "").trim();
      const parts = text.split(".");
      if (parts.length === 4 && parts.every((part) => /^\d{1,3}$/.test(part) && parseInt(part, 10) <= 255)) {
        event.preventDefault();
        this.segments = parts;
        this.emitValue();
      }
    },
    emitValue() {
      const joined = this.segments.join(".");
      this.$emit("update:modelValue", this.segments.every((seg) => seg === "") ? "" : joined);
    }
  }
});
</script>
