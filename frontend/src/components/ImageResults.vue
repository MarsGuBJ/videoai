<script lang="ts">
import { similarityColor } from "../utils/prototype-helpers";

// Injected functions are aliased (openResultImpl/setRouteImpl) and re-exposed
// as same-named methods so templates type-check; runtime behavior is identical
// to the prototype's `inject: ["openResult", "setRoute"]`.
export default {
  name: "ImageResults",
  props: ["items", "showScore", "selectable", "selectedIndexes", "indexOffset", "hideJump", "hideDescription", "showActions", "clickCropSearch"],
  emits: ["toggle-selection", "image-action", "card-click"],
  inject: {
    openResultImpl: { from: "openResult" },
    setRouteImpl: { from: "setRoute" }
  },
  methods: {
    similarityColor,
    openResult(index: number, item?: any) {
      (this as any).openResultImpl(index, item);
    },
    setRoute(route: string, options?: any) {
      (this as any).setRouteImpl(route, options);
    },
    globalIndex(index: number) {
      return (this.indexOffset || 0) + index;
    },
    isSelected(index: number) {
      return (this.selectedIndexes || []).includes(this.globalIndex(index));
    },
    onCardClick(index: number, item: any) {
      // clickCropSearch：点击卡片交给页面处理（图搜图页用于弹窗框选后再次搜图）
      if (this.clickCropSearch) {
        this.$emit("card-click", { item, index });
        return;
      }
      this.openResult(index, item);
    }
  }
};
</script>

<template>
  <div class="result-grid">
    <article class="result-card clickable" :class="{ selected: selectable && isSelected(index) }" v-for="(item, index) in items" :key="globalIndex(index)" @click="onCardClick(globalIndex(index), item)">
      <label v-if="selectable" class="result-select" @click.stop>
        <input type="checkbox" :checked="isSelected(index)" :aria-label="'选择' + item.title" @change.stop="$emit('toggle-selection', globalIndex(index))" />
      </label>
      <img class="thumb" :src="item.image" :alt="item.title" />
      <div class="body">
        <div class="result-card-location"><strong>{{ item.location }}</strong><span>{{ item.date.slice(11, 19) }}</span></div>
        <h4 v-if="!hideDescription">{{ item.title }}</h4>
        <p v-if="!hideDescription">{{ item.desc }}</p>
        <div class="result-card-footer"><span v-if="showScore" class="result-similarity" :style="{ color: similarityColor(item.score) }">相似度 {{ item.score }}%</span><span v-else>目标特征匹配</span><button v-if="!hideJump" class="result-jump-btn" title="以图搜图" @click.stop="setRoute('imageSearch', { prefill: item.image })">⌕</button></div>
        <div v-if="showActions" class="result-card-actions">
          <button class="btn" @click.stop="$emit('image-action', { action: 'imageSearch', item, index: globalIndex(index) })">以图搜图</button>
          <button class="btn primary" @click.stop="$emit('image-action', { action: 'quickDeploy', item, index: globalIndex(index) })">快速布防</button>
          <button class="btn" @click.stop="$emit('image-action', { action: 'track', item, index: globalIndex(index) })">轨迹还原</button>
        </div>
      </div>
    </article>
  </div>
</template>
