<script lang="ts">
import { statusClass } from "../utils/prototype-helpers";

export default {
  name: "DrawerHost",
  props: ["drawer", "store"],
  inject: ["openResult"],
  emits: ["close", "route", "action", "quick-deploy", "crop-action"],
  data() {
    return {
      resultMediaTab: "image"
    };
  },
  watch: {
    "drawer.open"(open: boolean) {
      if (open) this.resultMediaTab = "image";
    },
    "drawer.item"() {
      this.resultMediaTab = "image";
    }
  },
  computed: {
    source() {
      if (!this.drawer.item) return null;
      return this.store.results[this.drawer.item.resultIndex] || this.store.results[0];
    },
    isImageResultContext() {
      return ["imageSearch", "textImage"].includes(this.drawer.contextRoute);
    },
    isTrackResultContext() {
      return this.drawer.contextRoute === "track";
    }
  },
  methods: {
    statusClass,
    cycleResult() {
      // Only the prototype's mock gallery supports cycling; backend-loaded
      // result items (resultIndex -1) have no next entry to switch to.
      if (this.drawer.resultIndex < 0) return;
      const total = this.store.results.length;
      if (!total) return;
      const next = (this.drawer.resultIndex + 1) % total;
      this.openResult(next);
    }
  }
};
</script>

<template>
  <div class="drawer-mask" :class="{ open: drawer.open }" :aria-hidden="drawer.open ? 'false' : 'true'" @click.self="$emit('close')">
    <aside class="drawer" aria-label="详情抽屉">
      <div class="drawer-head">
        <h3>{{ drawer.title }}</h3>
        <button class="close" aria-label="关闭" @click="$emit('close')">×</button>
      </div>
      <div class="drawer-body" :class="{ 'drawer-image-result-body': isImageResultContext }" v-if="drawer.type === 'result' && drawer.item">
        <div v-if="isImageResultContext" class="drawer-media-tabs segmented" role="group" aria-label="结果媒体">
          <button class="btn" :class="{ ghost: resultMediaTab === 'image' }" :aria-pressed="resultMediaTab === 'image'" @click="resultMediaTab = 'image'">图片</button>
          <button class="btn" :class="{ ghost: resultMediaTab === 'video' }" :aria-pressed="resultMediaTab === 'video'" @click="resultMediaTab = 'video'">视频</button>
        </div>
        <div v-else-if="drawer.contextRoute !== 'textImage' && !isImageResultContext && !isTrackResultContext" class="drawer-media-tabs segmented">
          <button class="btn" :class="{ ghost: resultMediaTab === 'image' }" @click="resultMediaTab = 'image'">抓拍图片</button>
          <button v-if="!isImageResultContext && !isTrackResultContext" class="btn" :class="{ ghost: resultMediaTab === 'video' }" @click="resultMediaTab = 'video'">监控视频</button>
        </div>
        <div v-if="resultMediaTab === 'image'" class="drawer-hero-wrap">
          <img class="drawer-hero" :src="drawer.item.image" :alt="drawer.item.title" />
          <button v-if="isImageResultContext && drawer.resultIndex >= 0" class="drawer-hero-switch" type="button" aria-label="切换图片" @click="cycleResult">切换图片</button>
        </div>
        <div v-else class="drawer-video-preview">
          <img :src="drawer.item.image" :alt="drawer.item.title + '监控视频画面'" />
          <span class="play-dot">▶</span>
          <div class="video-control-line"><span>00:08</span><span class="video-progress"><i></i></span><span>00:30</span></div>
        </div>
        <dl class="detail-list">
          <dt>{{ drawer.contextRoute === 'textImage' ? '名称' : '结果名称' }}</dt><dd>{{ drawer.item.title }}</dd>
          <dt>时间</dt><dd>{{ drawer.item.date }}</dd>
          <dt>位置</dt><dd>{{ drawer.item.location }}</dd>
          <dt>相似度</dt><dd>{{ drawer.item.score == null ? "—" : drawer.item.score + "%" }}</dd>
          <template v-if="drawer.contextRoute !== 'textImage' && !isImageResultContext && !isTrackResultContext"><dt>分析说明</dt><dd>{{ drawer.item.desc }}</dd></template>
        </dl>
        <div class="panel" :class="{ 'drawer-image-result-actions': isImageResultContext, 'drawer-track-result-actions': isTrackResultContext }" style="padding:12px;">
          <div v-if="!isImageResultContext && !isTrackResultContext" style="font-weight:700; margin-bottom:8px;">可继续操作</div>
          <div v-if="!isImageResultContext && !isTrackResultContext" class="hint-text">搜索结果可继续进入以图搜图、快速布防、轨迹还原或提交人工复核。</div>
          <div v-if="isImageResultContext || isTrackResultContext" class="drawer-image-result-action-buttons">
            <button class="btn primary" @click="$emit('crop-action', 'imageSearch')">以图搜图</button>
            <button class="btn primary" @click="$emit('crop-action', 'quickDeploy')">快速布防</button>
            <button class="btn primary" @click="$emit('crop-action', 'track')">轨迹还原</button>
          </div>
          <div v-else class="action-grid four">
              <button class="btn primary" @click="$emit('route', 'imageSearch')">以图搜图</button>
              <button class="btn primary" @click="$emit('quick-deploy')">快速布防</button>
              <button class="btn primary" @click="$emit('route', 'track')">轨迹还原</button>
              <button v-if="!isImageResultContext" class="btn primary" @click="$emit('route', 'reviewTasks')">提交复核</button>
          </div>
        </div>
      </div>
      <div class="drawer-body" v-if="drawer.type === 'reviewTask' && drawer.item">
        <div class="review-target">
          <img :src="drawer.item.image" :alt="drawer.item.title" />
          <div>
            <h4>{{ drawer.item.title }}</h4>
            <p>{{ drawer.item.desc }}</p>
            <div class="tags">
              <span class="tag blue">{{ drawer.item.type }}</span>
              <span class="tag">{{ drawer.item.source }}</span>
              <span class="tag">{{ drawer.item.priority }}优先级</span>
            </div>
          </div>
        </div>
        <dl class="detail-list">
          <dt>任务编号</dt><dd>{{ drawer.item.id }}</dd>
          <dt>当前状态</dt><dd><span class="status-pill" :class="statusClass(drawer.item.status)">{{ drawer.item.status }}</span></dd>
          <dt>处理人</dt><dd>{{ drawer.item.owner }}</dd>
          <dt>创建时间</dt><dd>{{ drawer.item.date }}</dd>
          <dt>AI结论</dt><dd>{{ drawer.item.ai }}</dd>
        </dl>
        <div class="panel" style="padding:12px;" v-if="source">
          <div style="font-weight:700; margin-bottom:8px;">证据材料</div>
          <div class="evidence-list">
            <div class="evidence-item">
              <img :src="source.image" :alt="source.title" />
              <div><h5>{{ source.title }}</h5><p>{{ source.date }} · {{ source.location }} · 相似度 {{ source.score }}%</p></div>
            </div>
          </div>
        </div>
        <div class="action-grid four">
          <button class="btn primary" @click="$emit('action', 'approveReview')">通过复核</button>
          <button class="btn" @click="$emit('action', 'rejectReview')">驳回复核</button>
          <button class="btn" @click="$emit('action', 'generateReviewReport')">生成报告</button>
          <button class="btn" @click="$emit('close')">关闭</button>
        </div>
      </div>
    </aside>
  </div>
</template>
