<template>
  <div class="dt-range-picker" @click.stop>
    <button type="button" class="input dt-range-trigger" :class="{ placeholder: !start && !end }" :aria-label="ariaLabel" :aria-expanded="open" @click="toggle">
      <span class="dt-range-text">{{ displayValue }}</span>
      <span class="dt-range-caret">{{ open ? "▴" : "▾" }}</span>
    </button>
    <div v-if="open" class="dt-range-panel" role="dialog" aria-label="选择时间段">
      <label class="dt-range-row">
        <span>开始时间</span>
        <input class="input" type="datetime-local" :value="start" :max="maxDateTime" aria-label="开始时间" @change="onStartChange" />
      </label>
      <label class="dt-range-row">
        <span>结束时间</span>
        <input class="input" type="datetime-local" :value="end" :min="start || undefined" :max="maxDateTime" aria-label="结束时间" @change="onEndChange" />
      </label>
      <div class="dt-range-actions">
        <button type="button" class="btn" @click="clearAll">清空</button>
        <button type="button" class="btn primary" @click="close">确定</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

// datetime-local 输入框的最大可选时间：当前时刻（禁止选择未来时间）
function nowLocalDateTime(): string {
  const now = new Date();
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}T${pad2(now.getHours())}:${pad2(now.getMinutes())}`;
}

// "2026-07-12T08:30" -> "2026-07-12 08:30"
function displayDateTime(value: string): string {
  return value ? value.replace("T", " ") : "";
}

export default defineComponent({
  name: "DateTimeRangePicker",
  props: {
    start: { type: String, default: "" },
    end: { type: String, default: "" },
    placeholder: { type: String, default: "开始时间 ~ 结束时间" },
    ariaLabel: { type: String, default: "选择时间段" }
  },
  emits: ["update:start", "update:end", "change"],
  data() {
    return {
      open: false,
      maxDateTime: nowLocalDateTime()
    };
  },
  computed: {
    displayValue(): string {
      if (!this.start && !this.end) return this.placeholder;
      return `${displayDateTime(this.start) || "开始时间"} ~ ${displayDateTime(this.end) || "结束时间"}`;
    }
  },
  methods: {
    toggle() {
      if (!this.open) {
        // 每次打开时刷新上限，保证长时间停留的页面也不能选未来时间
        this.maxDateTime = nowLocalDateTime();
      }
      this.open = !this.open;
    },
    close() {
      this.open = false;
    },
    onStartChange(event: Event) {
      const value = (event.target as HTMLInputElement).value;
      this.$emit("update:start", value);
      if (value && this.end && this.end < value) {
        this.$emit("update:end", "");
      }
      this.$emit("change", value);
    },
    onEndChange(event: Event) {
      const value = (event.target as HTMLInputElement).value;
      this.$emit("update:end", value);
      this.$emit("change", value);
    },
    clearAll() {
      this.$emit("update:start", "");
      this.$emit("update:end", "");
      this.$emit("change", "");
    },
    onDocumentClick(event: MouseEvent) {
      if (this.open && !this.$el.contains(event.target)) this.close();
    }
  },
  mounted() {
    document.addEventListener("click", this.onDocumentClick);
  },
  beforeUnmount() {
    document.removeEventListener("click", this.onDocumentClick);
  }
});
</script>

<style scoped>
.dt-range-picker {
  position: relative;
  flex: 1;
  min-width: 0;
}
.dt-range-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  cursor: pointer;
  text-align: left;
  background: #fff;
}
.dt-range-trigger.placeholder {
  color: #98a2b3;
}
.dt-range-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dt-range-caret {
  color: #7890ae;
  font-size: 10px;
  flex: 0 0 auto;
}
.dt-range-panel {
  position: absolute;
  z-index: 30;
  top: calc(100% + 4px);
  left: 0;
  width: 280px;
  padding: 10px;
  border: 1px solid rgba(125, 165, 224, 0.35);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(16, 42, 80, 0.14);
}
.dt-range-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.dt-range-row span {
  flex: 0 0 auto;
  font-size: 12px;
  color: #344054;
}
.dt-range-row .input {
  flex: 1;
  min-width: 0;
}
.dt-range-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
