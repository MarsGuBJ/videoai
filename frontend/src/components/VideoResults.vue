<script lang="ts">
export default {
  name: "VideoResults",
  props: ["items"],
  // Aliased injection + same-named method wrapper (see ImageResults.vue note).
  inject: {
    openResultImpl: { from: "openResult" }
  },
  methods: {
    openResult(index: number) {
      (this as any).openResultImpl(index);
    }
  }
};
</script>

<template>
  <div class="list-results">
    <article class="video-result" v-for="(item, index) in items" :key="item.title">
      <div class="video-thumb"><img :src="item.image" :alt="item.title" /><span class="play-dot">▶</span></div>
      <div>
        <h4>{{ item.title }}</h4>
        <div class="meta"><span>{{ item.type }}</span><span>{{ item.date }}</span><span>{{ item.location }}</span><span>相似度 {{ item.score }}%</span></div>
        <p class="analysis-text">分析说明：{{ item.desc }}</p>
        <div class="tags"><span class="tag blue">目标识别</span></div>
      </div>
      <div style="text-align:right;"><button class="btn primary" @click="openResult(index)">查看详情</button></div>
    </article>
  </div>
</template>
