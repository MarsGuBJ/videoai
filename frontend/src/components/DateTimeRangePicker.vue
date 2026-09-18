<template>
  <div class="dt-range-picker" @click.stop>
    <button type="button" class="input dt-range-trigger" :class="{ placeholder: !start && !end }" :aria-label="ariaLabel" :aria-expanded="open" @click="toggle">
      <span class="dt-range-text">{{ displayValue }}</span>
      <span class="dt-range-caret">{{ open ? "▴" : "▾" }}</span>
    </button>
    <div v-if="open" class="dt-range-panel" role="dialog" aria-label="选择时间段">
      <div class="dt-range-tabs" role="tablist">
        <button type="button" role="tab" class="dt-range-tab" :class="{ active: editing === 'start' }" :aria-selected="editing === 'start'" @click="setEditing('start')">
          <span>开始时间</span><b>{{ draftLabel('start') }}</b>
        </button>
        <button type="button" role="tab" class="dt-range-tab" :class="{ active: editing === 'end' }" :aria-selected="editing === 'end'" @click="setEditing('end')">
          <span>结束时间</span><b>{{ draftLabel('end') }}</b>
        </button>
      </div>
      <div class="dt-range-cal-head">
        <button type="button" aria-label="上一月" @click="shiftMonth(-1)">‹</button>
        <b>{{ viewYear }}-{{ pad2(viewMonth + 1) }}</b>
        <button type="button" aria-label="下一月" @click="shiftMonth(1)">›</button>
      </div>
      <div class="dt-range-week"><span v-for="w in ['一', '二', '三', '四', '五', '六', '日']" :key="w">{{ w }}</span></div>
      <div class="dt-range-grid">
        <button
          v-for="cell in calendarCells"
          :key="cell.key"
          type="button"
          class="dt-range-day"
          :class="{ outside: !cell.dateStr, active: !!cell.dateStr && cell.dateStr === currentDraft.date }"
          :disabled="!cell.dateStr || isDayDisabled(cell.dateStr)"
          @click="pickDay(cell)"
        >{{ cell.label }}</button>
      </div>
      <div class="dt-range-time">
        <span class="dt-range-time-label">小时</span>
        <select class="select dt-range-hour" :value="currentDraft.hour === null ? '' : currentDraft.hour" aria-label="小时" @change="onHourChange">
          <option value="" disabled>--</option>
          <option v-for="h in 24" :key="h - 1" :value="h - 1" :disabled="isHourDisabled(h - 1)">{{ pad2(h - 1) }} 时</option>
        </select>
      </div>
      <div class="dt-range-minutes" aria-label="分钟">
        <button
          v-for="m in 60"
          :key="m - 1"
          type="button"
          class="dt-range-minute"
          :class="{ active: currentDraft.minute === m - 1 }"
          :disabled="isMinuteDisabled(m - 1)"
          @click="pickMinute(m - 1)"
        >{{ pad2(m - 1) }}</button>
      </div>
      <div class="dt-range-actions">
        <button type="button" class="btn" @click="clearAll">清空</button>
        <button type="button" class="btn primary" @click="confirm">确定</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

type DraftPart = { date: string; hour: number | null; minute: number | null };

function emptyDraft(): DraftPart {
  return { date: "", hour: null, minute: null };
}

// "2026-07-12T08:30" / "2026-07-12 08:30" -> { date, hour, minute }
function parseDraft(value: string): DraftPart {
  const match = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})/.exec(value || "");
  if (!match) return emptyDraft();
  return { date: match[1], hour: Number(match[2]), minute: Number(match[3]) };
}

// 草稿完整时组合为 datetime-local 格式 "YYYY-MM-DDTHH:mm"，否则返回空串
function draftValue(draft: DraftPart): string {
  if (!draft.date || draft.hour === null || draft.minute === null) return "";
  return `${draft.date}T${pad2(draft.hour)}:${pad2(draft.minute)}`;
}

// 本地时区今日 "YYYY-MM-DD"
function todayStr(): string {
  const now = new Date();
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
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
    const now = new Date();
    return {
      open: false,
      editing: "start" as "start" | "end",
      viewYear: now.getFullYear(),
      viewMonth: now.getMonth(),
      drafts: { start: emptyDraft(), end: emptyDraft() }
    };
  },
  computed: {
    displayValue(): string {
      if (!this.start && !this.end) return this.placeholder;
      return `${displayDateTime(this.start) || "开始时间"} ~ ${displayDateTime(this.end) || "结束时间"}`;
    },
    currentDraft(): DraftPart {
      return this.drafts[this.editing];
    },
    calendarCells(): { key: string; label: number; dateStr: string }[] {
      // 周一开头的月历格子；不足行用上月尾部占位（不可点）
      const first = new Date(this.viewYear, this.viewMonth, 1);
      const leading = (first.getDay() + 6) % 7;
      const daysInMonth = new Date(this.viewYear, this.viewMonth + 1, 0).getDate();
      const prevDays = new Date(this.viewYear, this.viewMonth, 0).getDate();
      const cells: { key: string; label: number; dateStr: string }[] = [];
      for (let i = 0; i < leading; i += 1) {
        cells.push({ key: `p${i}`, label: prevDays - leading + i + 1, dateStr: "" });
      }
      for (let d = 1; d <= daysInMonth; d += 1) {
        cells.push({ key: `d${d}`, label: d, dateStr: `${this.viewYear}-${pad2(this.viewMonth + 1)}-${pad2(d)}` });
      }
      return cells;
    }
  },
  methods: {
    pad2,
    toggle() {
      if (!this.open) {
        // 每次打开时从外部值同步草稿，并默认编辑开始时间
        this.drafts.start = parseDraft(this.start);
        this.drafts.end = parseDraft(this.end);
        this.setEditing("start");
      }
      this.open = !this.open;
    },
    close() {
      this.open = false;
    },
    setEditing(which: "start" | "end") {
      this.editing = which;
      // 日历视图跟随当前端点的日期，未选则回到当前月
      const date = this.drafts[which].date;
      if (date) {
        this.viewYear = Number(date.slice(0, 4));
        this.viewMonth = Number(date.slice(5, 7)) - 1;
      } else {
        const now = new Date();
        this.viewYear = now.getFullYear();
        this.viewMonth = now.getMonth();
      }
    },
    shiftMonth(delta: number) {
      const next = new Date(this.viewYear, this.viewMonth + delta, 1);
      this.viewYear = next.getFullYear();
      this.viewMonth = next.getMonth();
    },
    draftLabel(which: "start" | "end"): string {
      const draft = this.drafts[which];
      if (!draft.date) return "未选择";
      const hh = draft.hour === null ? "--" : pad2(draft.hour);
      const mm = draft.minute === null ? "--" : pad2(draft.minute);
      return `${draft.date} ${hh}:${mm}`;
    },
    // 约束：不能选未来时间；设置结束时间时不能早于开始时间（同一天再逐级卡小时/分钟）
    isDayDisabled(dateStr: string): boolean {
      if (dateStr > todayStr()) return true;
      const startDate = this.drafts.start.date;
      if (this.editing === "end" && startDate && dateStr < startDate) return true;
      return false;
    },
    isHourDisabled(hour: number): boolean {
      const date = this.currentDraft.date;
      if (!date) return false;
      const now = new Date();
      if (date === todayStr() && hour > now.getHours()) return true;
      const start = this.drafts.start;
      if (this.editing === "end" && start.date === date && start.hour !== null && hour < start.hour) return true;
      return false;
    },
    isMinuteDisabled(minute: number): boolean {
      const draft = this.currentDraft;
      if (!draft.date || draft.hour === null) return false;
      const now = new Date();
      if (draft.date === todayStr() && draft.hour === now.getHours() && minute > now.getMinutes()) return true;
      const start = this.drafts.start;
      if (this.editing === "end" && start.date === draft.date && start.hour === draft.hour && start.minute !== null && minute <= start.minute) return true;
      return false;
    },
    pickDay(cell: { dateStr: string }) {
      if (!cell.dateStr || this.isDayDisabled(cell.dateStr)) return;
      this.currentDraft.date = cell.dateStr;
    },
    onHourChange(event: Event) {
      const hour = Number((event.target as HTMLSelectElement).value);
      if (Number.isNaN(hour) || this.isHourDisabled(hour)) return;
      this.currentDraft.hour = hour;
    },
    pickMinute(minute: number) {
      if (this.isMinuteDisabled(minute)) return;
      this.currentDraft.minute = minute;
      // 便捷完成：日期与小时都已选时，点击分钟数即完成当前端点 —
      // 开始时间完成后切换到结束时间；结束时间完成后等同点击「确定」关闭面板
      if (this.currentDraft.date && this.currentDraft.hour !== null) this.completeEditing();
    },
    completeEditing() {
      const value = draftValue(this.currentDraft);
      if (!value || !this.emitEditing(value)) return;
      if (this.editing === "start") {
        // 结束时间草稿默认带上开始日期，减少一次点选
        if (!this.drafts.end.date) this.drafts.end.date = this.drafts.start.date;
        this.setEditing("end");
      } else {
        this.close();
      }
    },
    // 提交当前端点草稿；返回 false 表示被约束拦截（正常路径下禁用态已挡住，这里是兜底）
    emitEditing(value: string): boolean {
      if (this.editing === "start") {
        this.$emit("update:start", value);
        const endValue = draftValue(this.drafts.end);
        if (endValue && endValue <= value) {
          this.$emit("update:end", "");
          this.drafts.end = emptyDraft();
        }
      } else {
        const startValue = draftValue(this.drafts.start);
        if (startValue && value <= startValue) return false;
        this.$emit("update:end", value);
      }
      this.$emit("change", value);
      return true;
    },
    confirm() {
      const value = draftValue(this.currentDraft);
      if (value) this.emitEditing(value);
      this.close();
    },
    clearAll() {
      this.drafts.start = emptyDraft();
      this.drafts.end = emptyDraft();
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
.dt-range-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}
.dt-range-tab {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 6px 8px;
  border: 1px solid rgba(125, 165, 224, 0.35);
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  text-align: left;
}
.dt-range-tab span {
  font-size: 11px;
  color: #98a2b3;
}
.dt-range-tab b {
  font-size: 12px;
  font-weight: 500;
  color: #344054;
}
.dt-range-tab.active {
  border-color: #2b8bf4;
  background: rgba(43, 139, 244, 0.06);
}
.dt-range-tab.active b {
  color: #2b8bf4;
}
.dt-range-cal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.dt-range-cal-head button {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: #2b8bf4;
  padding: 2px 8px;
}
.dt-range-cal-head b {
  font-size: 13px;
  color: #344054;
}
.dt-range-week,
.dt-range-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  text-align: center;
}
.dt-range-week span {
  font-size: 11px;
  color: #98a2b3;
  padding: 2px 0;
}
.dt-range-day {
  border: none;
  background: transparent;
  padding: 4px 0;
  font-size: 12px;
  border-radius: 4px;
  cursor: pointer;
  color: #344054;
}
.dt-range-day:hover:not(:disabled) {
  background: rgba(43, 139, 244, 0.12);
}
.dt-range-day.outside {
  color: #cbd5e1;
  cursor: default;
}
.dt-range-day:disabled {
  color: #cbd5e1;
  cursor: not-allowed;
}
.dt-range-day.active {
  background: #2b8bf4;
  color: #fff;
}
.dt-range-time {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.dt-range-time-label {
  flex: 0 0 auto;
  font-size: 12px;
  color: #344054;
}
.dt-range-hour {
  flex: 1;
  min-width: 0;
}
.dt-range-minutes {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 2px;
  margin-top: 8px;
}
.dt-range-minute {
  border: none;
  background: transparent;
  padding: 3px 0;
  font-size: 11px;
  border-radius: 4px;
  cursor: pointer;
  color: #344054;
}
.dt-range-minute:hover:not(:disabled) {
  background: rgba(43, 139, 244, 0.12);
}
.dt-range-minute:disabled {
  color: #cbd5e1;
  cursor: not-allowed;
}
.dt-range-minute.active {
  background: #2b8bf4;
  color: #fff;
}
.dt-range-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
