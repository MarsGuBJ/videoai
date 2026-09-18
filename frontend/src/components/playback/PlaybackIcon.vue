<template>
  <svg
    class="playback-icon"
    :viewBox="`0 0 ${def.viewBox} ${def.viewBox}`"
    aria-hidden="true"
  >
    <!-- 图标字体 glyph 为 y 轴向上的坐标系，渲染时翻转 -->
    <path :d="def.d" :transform="`translate(0, ${def.viewBox}) scale(1, -1)`" />
  </svg>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { PLAYBACK_ICONS } from './PlaybackIcons';

export default defineComponent({
  name: 'PlaybackIcon',
  props: {
    name: { type: String, required: true },
  },
  setup(props) {
    const def = computed(() => PLAYBACK_ICONS[props.name] || PLAYBACK_ICONS.close);
    return { def };
  },
});
</script>

<style scoped>
.playback-icon {
  display: inline-block;
  width: 24px;
  height: 24px;
  fill: currentColor;
  vertical-align: middle;
}
</style>
