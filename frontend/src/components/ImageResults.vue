<script lang="ts">
import { similarityColor } from "../utils/prototype-helpers";

// Injected functions are aliased (openResultImpl/setRouteImpl) and re-exposed
// as same-named methods so templates type-check; runtime behavior is identical
// to the prototype's `inject: ["openResult", "setRoute"]`.
export default {
  name: "ImageResults",
  props: ["items", "showScore", "selectable", "selectedIndexes", "indexOffset", "hideJump", "hideDescription", "showActions", "emitOpen", "mediaSwitchable", "showAttributes"],
  emits: ["toggle-selection", "image-action", "open-result"],
  inject: {
    openResultImpl: { from: "openResult" },
    setRouteImpl: { from: "setRoute" }
  },
  data() {
    return {
      // 卡片图/视频视图切换状态，以全局索引为 key
      mediaToggled: {} as Record<number, boolean>
    };
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
    isVideoView(index: number) {
      return !!this.mediaToggled[this.globalIndex(index)];
    },
    toggleMedia(index: number) {
      const key = this.globalIndex(index);
      this.mediaToggled = { ...this.mediaToggled, [key]: !this.mediaToggled[key] };
    },
    onCardClick(index: number, item: any) {
      // emitOpen：点击卡片由页面接管（图搜图页弹窗框选后再搜、文搜图页打开图片灯箱）
      if (this.emitOpen) {
        this.$emit("open-result", { item, index });
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
      <button v-if="mediaSwitchable" class="result-media-switch" type="button" aria-label="切换媒体视图" @click.stop="toggleMedia(index)">⇄</button>
      <div v-if="mediaSwitchable && isVideoView(index)" class="thumb thumb-video"><img :src="item.image" :alt="item.title" /><span class="play-dot">▶</span></div>
      <img v-else class="thumb" :src="item.image" :alt="item.title" />
      <div class="body">
        <div class="result-card-location"><strong>{{ item.location }}</strong><span>{{ item.date.slice(11, 19) }}</span></div>
        <div v-if="showAttributes && (item.age || item.accessory || item.topColor || item.action)" class="result-attrs">
          <span v-if="item.age"><span class="attr-label">年龄：</span>{{ item.age }}</span>
          <span v-if="item.accessory"><span class="attr-label">配饰：</span>{{ item.accessory }}</span>
          <span v-if="item.topColor"><span class="attr-label">衣服颜色：</span>{{ item.topColor }}</span>
          <span v-if="item.action"><span class="attr-label">行为：</span>{{ item.action }}</span>
        </div>
        <h4 v-if="!hideDescription">{{ item.title }}</h4>
        <p v-if="!hideDescription">{{ item.desc }}</p>
        <div v-if="showScore || !hideJump" class="result-card-footer"><span v-if="showScore" class="result-similarity" :style="{ color: similarityColor(item.score) }">相似度 {{ item.score }}%</span><span v-else>目标特征匹配</span><button v-if="!hideJump" class="result-jump-btn" title="以图搜图" @click.stop="setRoute('imageSearch', { prefill: item.image })">⌕</button></div>
        <div v-if="showActions" class="result-card-actions">
          <button class="btn" @click.stop="$emit('image-action', { action: 'imageSearch', item, index: globalIndex(index) })">以图搜图</button>
          <button class="btn primary" @click.stop="$emit('image-action', { action: 'quickDeploy', item, index: globalIndex(index) })">快速布防</button>
          <button class="btn" @click.stop="$emit('image-action', { action: 'track', item, index: globalIndex(index) })">轨迹还原</button>
        </div>
      </div>
    </article>
  </div>
</template>
