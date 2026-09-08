<template>
  <div class="dt-picker" @click.stop>
    <button type="button" class="input dt-picker-trigger" :class="{ placeholder: !modelValue }" :aria-label="ariaLabel" :aria-expanded="open" @click="toggle">
      <span>{{ modelValue || placeholder }}</span>
      <span class="dt-picker-caret">{{ open ? "▴" : "▾" }}</span>
    </button>
    <div v-if="open" class="dt-picker-panel" role="dialog" aria-label="日期时间选择">
      <div class="dt-picker-head">
        <button type="button" aria-label="上一月" @click="shiftMonth(-1)">‹</button>
        <b>{{ viewYear }}-{{ pad(viewMonth + 1) }}</b>
        <button type="button" aria-label="下一月" @click="shiftMonth(1)">›</button>
      </div>
      <div class="dt-picker-week"><span v-for="w in ['一', '二', '三', '四', '五', '六', '日']" :key="w">{{ w }}</span></div>
      <div class="dt-picker-grid">
        <button
          v-for="cell in calendarCells"
          :key="cell.key"
          type="button"
          class="dt-picker-day"
          :class="{ outside: cell.outside, active: cell.day === selectedDay && !cell.outside }"
          @click="pickDay(cell)"
        >{{ cell.label }}</button>
      </div>
      <div class="dt-picker-time">
        <select class="select" v-model.number="draftHour" aria-label="小时"><option v-for="h in 24" :key="h - 1" :value="h - 1">{{ pad(h - 1) }} 时</option></select>
        <select class="select" v-model.number="draftMinute" aria-label="分钟"><option v-for="m in 60" :key="m - 1" :value="m - 1">{{ pad(m - 1) }} 分</option></select>
      </div>
      <div class="dt-picker-actions">
        <button type="button" class="btn" @click="pickNow">此刻</button>
        <button type="button" class="btn" @click="clear">清空</button>
        <button type="button" class="btn primary" :disabled="selectedDay === null" @click="confirm">确定</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

const VALUE_RE = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/;

export default defineComponent({
  name: "DateTimePicker",
  props: {
    modelValue: { type: String, default: "" },
    placeholder: { type: String, default: "请选择时间" },
    ariaLabel: { type: String, default: "选择日期时间" }
  },
  emits: ["update:modelValue", "change"],
  data() {
    const now = new Date();
    return {
      open: false,
      viewYear: now.getFullYear(),
      viewMonth: now.getMonth(),
      selectedDay: null as number | null,
      draftHour: now.getHours(),
      draftMinute: now.getMinutes()
    };
  },
  computed: {
    calendarCells(): { key: string; label: number; day: number; outside: boolean }[] {
      // 周一开头的月历格子；不足行用上月尾部补齐
      const first = new Date(this.viewYear, this.viewMonth, 1);
      const leading = (first.getDay() + 6) % 7;
      const daysInMonth = new Date(this.viewYear, this.viewMonth + 1, 0).getDate();
      const prevDays = new Date(this.viewYear, this.viewMonth, 0).getDate();
      const cells: { key: string; label: number; day: number; outside: boolean }[] = [];
      for (let i = 0; i < leading; i += 1) {
        cells.push({ key: `p${i}`, label: prevDays - leading + i + 1, day: -1, outside: true });
      }
      for (let d = 1; d <= daysInMonth; d += 1) {
        cells.push({ key: `d${d}`, label: d, day: d, outside: false });
      }
      return cells;
    }
  },
  methods: {
    pad(n: number) {
      return String(n).padStart(2, "0");
    },
    toggle() {
      if (!this.open) this.syncDraftFromValue();
      this.open = !this.open;
    },
    close() {
      this.open = false;
    },
    syncDraftFromValue() {
      const match = VALUE_RE.exec(this.modelValue || "");
      if (match) {
        this.viewYear = Number(match[1]);
        this.viewMonth = Number(match[2]) - 1;
        this.selectedDay = Number(match[3]);
        this.draftHour = Number(match[4]);
        this.draftMinute = Number(match[5]);
      } else {
        const now = new Date();
        this.viewYear = now.getFullYear();
        this.viewMonth = now.getMonth();
        this.selectedDay = null;
        this.draftHour = now.getHours();
        this.draftMinute = now.getMinutes();
      }
    },
    shiftMonth(delta: number) {
      const next = new Date(this.viewYear, this.viewMonth + delta, 1);
      this.viewYear = next.getFullYear();
      this.viewMonth = next.getMonth();
    },
    pickDay(cell: { day: number; outside: boolean }) {
      if (cell.outside) return;
      this.selectedDay = cell.day;
    },
    emitValue(value: string) {
      this.$emit("update:modelValue", value);
      this.$emit("change", value);
    },
    pickNow() {
      const now = new Date();
      this.viewYear = now.getFullYear();
      this.viewMonth = now.getMonth();
      this.selectedDay = now.getDate();
      this.draftHour = now.getHours();
      this.draftMinute = now.getMinutes();
      this.confirm();
    },
    clear() {
      this.selectedDay = null;
      this.emitValue("");
      this.close();
    },
    confirm() {
      if (this.selectedDay === null) return;
      this.emitValue(`${this.viewYear}-${this.pad(this.viewMonth + 1)}-${this.pad(this.selectedDay)} ${this.pad(this.draftHour)}:${this.pad(this.draftMinute)}`);
      this.close();
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
.dt-picker {
  position: relative;
  flex: 1;
  min-width: 0;
}
.dt-picker-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  cursor: pointer;
  text-align: left;
  background: #fff;
}
.dt-picker-trigger.placeholder {
  color: #98a2b3;
}
.dt-picker-caret {
  color: #7890ae;
  font-size: 10px;
}
.dt-picker-panel {
  position: absolute;
  z-index: 30;
  top: calc(100% + 4px);
  left: 0;
  width: 248px;
  padding: 10px;
  border: 1px solid rgba(125, 165, 224, 0.35);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(16, 42, 80, 0.14);
}
.dt-picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.dt-picker-head button {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: #2b8bf4;
  padding: 2px 8px;
}
.dt-picker-head b {
  font-size: 13px;
  color: #344054;
}
.dt-picker-week,
.dt-picker-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  text-align: center;
}
.dt-picker-week span {
  font-size: 11px;
  color: #98a2b3;
  padding: 2px 0;
}
.dt-picker-day {
  border: none;
  background: transparent;
  padding: 4px 0;
  font-size: 12px;
  border-radius: 4px;
  cursor: pointer;
  color: #344054;
}
.dt-picker-day:hover {
  background: rgba(43, 139, 244, 0.12);
}
.dt-picker-day.outside {
  color: #cbd5e1;
  cursor: default;
  background: transparent;
}
.dt-picker-day.active {
  background: #2b8bf4;
  color: #fff;
}
.dt-picker-time {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.dt-picker-time .select {
  flex: 1;
  min-width: 0;
}
.dt-picker-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
