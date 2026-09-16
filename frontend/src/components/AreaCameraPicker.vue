<template>
  <div class="exact-tree-select area-camera-picker" @click.stop>
    <button type="button" class="exact-tree-trigger" :class="{ open }" :aria-expanded="open" aria-label="区域 / 监控点" @click="toggle">
      <span>{{ selectedLabel }}</span><span>{{ open ? "收起" : "展开" }}⌄</span>
    </button>
    <div v-if="open" class="exact-tree-dropdown">
      <button v-if="showAll" type="button" class="exact-tree-device area-camera-picker-all" :class="{ active: !modelValue }" @click="selectAll">{{ allLabel }}</button>
      <div v-for="area in areas" :key="area.name">
        <button type="button" class="exact-tree-area-row" @click="toggleArea(area)">
          <span>{{ expandedAreas[area.name] ? "⌄" : "›" }} {{ area.name }}</span><span>{{ area.cameras.length }} 台设备</span>
        </button>
        <div v-if="expandedAreas[area.name]" class="exact-tree-children">
          <button
            v-for="camera in area.cameras"
            :key="camera.code"
            type="button"
            class="exact-tree-device"
            :class="{ active: modelValue === camera.name }"
            @click="selectCamera(camera)"
          ><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button>
        </div>
      </div>
      <div v-if="!areas.length" class="area-camera-picker-empty">暂无监控点数据</div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import { deviceStatusLabel } from "../utils/device-status";
import { loadRegionTree } from "../utils/regions";

type PickerCamera = { name: string; code: string; status: string; onlineStatus?: string | null };
type PickerArea = { name: string; cameras: PickerCamera[] };

// 「区域 / 监控点」树形下拉：与文搜视频页在线监控点选择器一致。
// 值为空字符串表示「全部地点」，选中监控点时为摄像头名称。
export default defineComponent({
  name: "AreaCameraPicker",
  props: {
    modelValue: { type: String, default: "" },
    showAll: { type: Boolean, default: true },
    allLabel: { type: String, default: "全部地点" }
  },
  emits: ["update:modelValue", "change"],
  data() {
    return {
      open: false,
      areas: [] as PickerArea[],
      expandedAreas: {} as Record<string, boolean>
    };
  },
  computed: {
    selectedLabel(): string {
      return this.modelValue || this.allLabel;
    }
  },
  mounted() {
    this.loadCameras();
    document.addEventListener("click", this.onDocumentClick);
  },
  beforeUnmount() {
    document.removeEventListener("click", this.onDocumentClick);
  },
  methods: {
    async loadCameras() {
      // 顶层区域顺序来自后端区域树；不在树中的分组排在最后并按名称排序
      let topNames: string[] = [];
      try {
        topNames = (await loadRegionTree()).map((node) => node.name);
      } catch {
        // 区域接口不可用时保持原有分组顺序
      }
      try {
        const cameras = await api.cameras();
        const grouped: Record<string, PickerCamera[]> = {};
        (cameras || []).forEach((cam: any) => {
          const areaName = (String(cam.area || "").split("/")[0] || "").trim() || "未分配";
          if (!grouped[areaName]) grouped[areaName] = [];
          grouped[areaName].push({
            name: cam.name,
            code: cam.id,
            status: deviceStatusLabel(cam),
            onlineStatus: cam.onlineStatus
          });
        });
        const order = new Map(topNames.map((name, index) => [name, index]));
        const areas = Object.keys(grouped).map(name => ({ name, cameras: grouped[name] }));
        areas.sort((a, b) => {
          const ia = order.has(a.name) ? (order.get(a.name) as number) : Number.MAX_SAFE_INTEGER;
          const ib = order.has(b.name) ? (order.get(b.name) as number) : Number.MAX_SAFE_INTEGER;
          if (ia !== ib) return ia - ib;
          return a.name.localeCompare(b.name, "zh");
        });
        this.areas = areas;
        const expanded: Record<string, boolean> = {};
        areas.forEach((area, index) => { expanded[area.name] = index === 0; });
        this.expandedAreas = expanded;
      } catch {
        // 后端不可用时保留空列表，面板显示「暂无监控点数据」
      }
    },
    toggle() {
      this.open = !this.open;
    },
    close() {
      this.open = false;
    },
    toggleArea(area: PickerArea) {
      this.expandedAreas[area.name] = !this.expandedAreas[area.name];
    },
    selectAll() {
      this.$emit("update:modelValue", "");
      this.$emit("change", "");
      this.close();
    },
    selectCamera(camera: PickerCamera) {
      this.$emit("update:modelValue", camera.name);
      this.$emit("change", camera.name);
      this.close();
    },
    onDocumentClick(event: MouseEvent) {
      if (this.open && !this.$el.contains(event.target)) this.close();
    }
  }
});
</script>

<style scoped>
.area-camera-picker {
  width: 100%;
}
.area-camera-picker-all {
  border-bottom: 1px solid rgba(125, 165, 224, 0.18);
  margin-bottom: 2px;
}
.area-camera-picker-empty {
  padding: 12px;
  color: #888;
  font-size: 12px;
}
</style>
