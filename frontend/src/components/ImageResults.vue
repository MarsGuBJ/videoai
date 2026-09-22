<script lang="ts">
import { similarityColor } from "../utils/prototype-helpers";
import { attributeText } from "../utils/attributes";

// Injected functions are aliased (openResultImpl/setRouteImpl) and re-exposed
// as same-named methods so templates type-check; runtime behavior is identical
// to the prototype's `inject: ["openResult", "setRoute"]`.
export default {
  name: "ImageResults",
  props: ["items", "showScore", "selectable", "selectedIndexes", "indexOffset", "hideJump", "hideDescription", "showActions", "emitOpen", "disableOpen", "showFullDate", "mediaSwitchable", "showAttributes"],
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
    // 属性行：去掉方括号与引号只留文字，值为空的字段（连同字段名）不展示
    attributeList(item: any) {
      return [
        { label: "年龄", value: attributeText(item.age) },
        { label: "配饰", value: attributeText(item.accessory) },
        { label: "衣服颜色", value: attributeText(item.topColor) },
        { label: "行为", value: attributeText(item.action) }
      ].filter((attr) => attr.value);
    },
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
      // disableOpen：卡片纯展示（文搜视频页以图搜图 tab），点击不打开详情
      if (this.disableOpen) return;
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
    <article class="result-card" :class="{ clickable: !disableOpen, selected: selectable && isSelected(index) }" v-for="(item, index) in items" :key="globalIndex(index)" @click="onCardClick(globalIndex(index), item)">
      <label v-if="selectable" class="result-select" @click.stop>
        <input type="checkbox" :checked="isSelected(index)" :aria-label="'选择' + item.title" @change.stop="$emit('toggle-selection', globalIndex(index))" />
      </label>
      <button v-if="mediaSwitchable && item.video" class="result-media-switch" type="button" :aria-label="isVideoView(index) ? '切换为图片' : '切换为视频'" :title="isVideoView(index) ? '切换为图片' : '切换为视频'" @click.stop="toggleMedia(index)">⇄</button>
      <!-- 视频视图：播放后端 video_url；@click.stop 避免播放器控制条冒泡触发卡片点击 -->
      <video v-if="mediaSwitchable && item.video && isVideoView(index)" class="thumb thumb-video" :src="item.video" controls autoplay muted loop playsinline @click.stop></video>
      <img v-else class="thumb" :src="item.image" :alt="item.title" />
      <div class="body">
        <div class="result-card-location"><strong>{{ item.location }}</strong><span>{{ showFullDate ? item.date : item.date.slice(11, 19) }}</span></div>
        <div v-if="showAttributes && attributeList(item).length" class="result-attrs">
          <span v-for="attr in attributeList(item)" :key="attr.label"><span class="attr-label">{{ attr.label }}：</span>{{ attr.value }}</span>
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
