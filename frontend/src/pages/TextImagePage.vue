<template>
  <section class="content wide text-image-page sxin-workspace">
    <!-- 左侧：万物搜会话面板（历史/分组暂无接口，占位） -->
    <aside class="sxin-session-panel">
      <h2 class="sxin-panel-title">万物搜</h2>
      <button class="sxin-new-session" type="button" @click="resetSession">＋ 新建会话</button>
      <input class="sxin-history-search" placeholder="搜索历史记录..." @keyup.enter="placeholderFeature" />
      <p class="sxin-panel-label">对话分组</p>
      <button class="sxin-add-group" type="button" @click="placeholderFeature">⊕ 新增分组</button>
      <button v-for="group in sessionGroups" :key="group" class="sxin-group-item" type="button" @click="placeholderFeature">
        <span class="sxin-folder-icon">📁</span>{{ group }}
      </button>
      <p class="sxin-panel-label">最近对话</p>
      <button v-for="item in recentChats" :key="item" class="sxin-history-item" type="button" :title="item" @click="placeholderFeature">{{ item }}</button>
    </aside>

    <!-- 中间：聊天区 + 底部输入 -->
    <div class="sxin-main">
      <div class="sxin-chat" ref="chatScroll">
        <div class="sxin-msg assistant">
          <div class="sxin-avatar">SXin</div>
          <div class="sxin-bubble sxin-greeting">
            👋 您好！我是视觉大模型助手，可以通过自然语言帮您查找视频、定位目标、分析内容。例如：<span class="sxin-greeting-example">"帮我查找今天下午14点到18点B2层停车场的监控"</span>
          </div>
        </div>

        <template v-for="(round, ri) in rounds" :key="ri">
          <div class="sxin-msg user">
            <div class="sxin-user-side">
              <div class="sxin-bubble sxin-bubble-user">{{ round.query }}</div>
              <span class="sxin-msg-time">{{ round.time }}</span>
            </div>
            <div class="sxin-user-avatar">User</div>
          </div>

          <div class="sxin-msg assistant">
            <div class="sxin-avatar">SXin</div>
            <div class="sxin-assistant-body">
              <!-- 思考过程卡：数据来自 textSearchQuery 响应 process 字段 -->
              <div class="sxin-think-card">
                <button class="sxin-think-toggle" type="button" :aria-expanded="!round.thinkCollapsed" @click="round.thinkCollapsed = !round.thinkCollapsed">
                  <span>这是思考过程</span>
                  <span class="sxin-think-caret">{{ round.thinkCollapsed ? '⌄' : '⌃' }}</span>
                </button>
                <div v-show="!round.thinkCollapsed" class="sxin-think-body">
                  <div class="sxin-think-progress">
                    <span>{{ round.loading ? '深度特征提取中...' : '深度特征提取完成' }}</span>
                    <span class="sxin-think-progress-value">{{ round.loading ? '' : '100' }}</span>
                  </div>
                  <div class="sxin-think-bar"><i :style="{ width: round.loading ? '60%' : '100%' }"></i></div>
                  <p class="sxin-think-subtitle">⛶ 意图拆解</p>
                  <div v-if="round.loading" class="sxin-think-loading"><span class="search-loading-spinner"></span>正在检索，请稍候…</div>
                  <template v-else>
                    <div v-for="(step, si) in roundSteps(round)" :key="step.key || si" class="sxin-think-step">
                      <span class="sxin-think-step-name">{{ step.title }}</span>
                      <em class="sxin-think-step-pct">100%</em>
                    </div>
                    <ul v-if="roundUnderstanding(round).length" class="sxin-think-understanding">
                      <li v-for="(msg, mi) in roundUnderstanding(round)" :key="mi">{{ msg }}</li>
                    </ul>
                  </template>
                </div>
              </div>

              <template v-if="round.done">
                <p class="sxin-analysis-head">视觉分析结果 <em class="sxin-done-badge">完成</em></p>
                <div class="sxin-result-card">
                  <div class="sxin-result-divider"><span>分析完成</span></div>
                  <p class="sxin-result-summary">✅ {{ round.resultMessage || `检测到${round.items.length}张目标图像` }}</p>
                  <div v-if="round.items.length" class="sxin-result-thumbs">
                    <img v-for="thumb in round.items.slice(0, 3)" :key="thumb.desc || thumb.image" :src="thumb.image" alt="" />
                    <span v-if="round.items.length > 3" class="sxin-result-ellipsis">……</span>
                    <span class="sxin-result-total">（共{{ round.items.length }}张）</span>
                  </div>
                  <p class="sxin-result-tip">💡 您可以点击分析结果查看详细画面，或将直接点击功能按钮进行下一步操作</p>
                </div>
                <div class="sxin-action-card">
                  <div class="sxin-action-info">
                    <strong>分析结果</strong>
                    <span>发现 {{ round.items.length }} 张相似图像……</span>
                    <time>{{ round.time }}</time>
                  </div>
                  <button class="sxin-action-btn" type="button" :disabled="!round.items.length" @click="jumpImageSearch(round)">以图搜图</button>
                  <button class="sxin-action-btn" type="button" :disabled="!round.items.length" @click="jumpTrack(round)">轨迹还原</button>
                  <button class="sxin-action-more" type="button" @click="placeholderFeature">···</button>
                </div>
                <p class="sxin-drag-tip">💡 您可以点击右侧关键帧查看详细画面，或将关键帧拖拽到输入框进行进一步操作</p>
                <div class="sxin-feedback">
                  <button type="button" @click="placeholderFeature">👍 有用</button>
                  <button type="button" @click="placeholderFeature">👎 无用</button>
                  <button type="button" :disabled="searching" @click="regenerate(round)">🔄 重新生成</button>
                </div>
              </template>
              <p v-else-if="round.error" class="sxin-error">{{ round.error }}</p>
            </div>
          </div>
        </template>
      </div>

      <!-- 底部输入区：文搜视频/图搜图 chips 跳转对应页面，附件/语音占位 -->
      <div class="sxin-input-bar">
        <div class="sxin-input-top">
          <button class="sxin-input-icon" type="button" title="附件（即将上线）" @click="placeholderFeature">📎</button>
          <button class="sxin-input-icon" type="button" title="上传图片（即将上线）" @click="placeholderFeature">🖼</button>
          <input v-model="query" class="sxin-input" placeholder="支持拖拽图片或视频上传 (Max 50MB)" @keyup.enter="send" />
        </div>
        <div class="sxin-input-bottom">
          <div class="sxin-mode-chips">
            <button type="button" @click="goTextVideo">🔍 文搜视频</button>
            <button type="button" class="active">📊 文搜图</button>
            <button type="button" @click="goImageSearch">📐 图搜图</button>
          </div>
          <div class="sxin-input-actions">
            <button class="sxin-input-icon" type="button" title="语音输入（即将上线）" @click="placeholderFeature">🎤</button>
            <button class="sxin-send" type="button" :disabled="searching" @click="send">发送指令 ➤</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：分析结果面板（展示最近一轮检索结果） -->
    <aside class="sxin-result-panel">
      <div class="sxin-result-head">
        <h3>分析结果</h3>
        <span class="sxin-count-badge">{{ latestItems.length }} 个事件</span>
      </div>
      <div v-if="latestItems.length" class="sxin-card-grid">
        <div v-for="(item, index) in latestItems" :key="item.desc || index" class="sxin-card" :class="{ selected: item.checked }">
          <label class="sxin-card-check" @click.stop>
            <input type="checkbox" v-model="item.checked" aria-label="选择该结果" />
          </label>
          <div class="sxin-card-tools">
            <button type="button" title="图像布控" @click="openCrop(item, 'quickDeploy')">🛡</button>
            <button type="button" title="监控回放" @click="playVideo(item)">🎥</button>
            <button type="button" title="以图搜图" @click="openCrop(item, 'imageSearch')">🔍</button>
          </div>
          <img class="sxin-card-img" :src="item.image" :alt="item.title" @click="openCrop(item, 'imageSearch')" />
          <span class="sxin-card-match">匹配度&nbsp;&nbsp;{{ item.score }}%</span>
          <p class="sxin-card-loc">📍 {{ item.location }}</p>
          <p class="sxin-card-time">🕐 {{ item.date }}</p>
        </div>
      </div>
      <div v-else class="sxin-result-empty">
        <strong>暂无分析结果</strong>
        <span>在底部输入框描述目标特征，点击「发送指令」开始检索</span>
      </div>
      <button class="sxin-track-btn" type="button" :disabled="!checkedItems.length" @click="jumpTrackSelection">轨迹还原</button>
    </aside>

    <!-- 框选目标弹窗：以图搜图 / 图像布控 / 轨迹还原共用，确认后跳转对应页面 -->
    <image-crop-dialog :open="cropDialogOpen" :item="cropTarget" :action="cropAction" :initial-bbox="cropTarget?.position" :confirm-label="cropConfirmLabel" @close="closeCrop" @confirm="confirmCrop"></image-crop-dialog>

    <!-- 监控回放弹层（条目带 video_url 时可用） -->
    <div v-if="videoPreviewUrl" class="sxin-video-mask" @click.self="videoPreviewUrl = ''">
      <div class="sxin-video-box">
        <button class="sxin-video-close" type="button" @click="videoPreviewUrl = ''">✕</button>
        <video :src="videoPreviewUrl" controls autoplay></video>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import ImageCropDialog from "../components/ImageCropDialog.vue";
import { api, assetUrl } from "../api";
import type { TextSearchItem, TextSearchProcess, TextSearchProcessStep } from "../api";

// 卡片图标的下一步动作：以图搜图 / 图像布控 / 轨迹还原（均先打开框选弹窗）
type CropAction = "imageSearch" | "quickDeploy" | "track";

type ChatRound = {
  query: string;
  time: string;
  loading: boolean;
  done: boolean;
  error: string;
  process: TextSearchProcess | null;
  resultMessage: string;
  items: any[];
  thinkCollapsed: boolean;
};

function pad2(n: number) {
  return n.toString().padStart(2, "0");
}

// create_time (epoch seconds/ms or string) -> "YYYY-MM-DD HH:mm:ss"
function formatCreateTime(value?: number | string | null): string {
  let d: Date | null = null;
  if (value !== undefined && value !== null && value !== "") {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      d = new Date(numeric > 10_000_000_000 ? numeric : numeric * 1000);
    } else {
      const parsed = new Date(String(value));
      if (!Number.isNaN(parsed.getTime())) {
        d = parsed;
      }
    }
  }
  if (!d || Number.isNaN(d.getTime())) {
    return value ? String(value) : "未知时间";
  }
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

// 对话气泡时间 -> "YYYY/MM/DD HH:mm"
function formatChatTime(d: Date): string {
  return `${d.getFullYear()}/${pad2(d.getMonth() + 1)}/${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

// 相似度 0~1 -> 百分比字符串
function similarityToPercent(value?: number | null): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "0";
  }
  return (Number(value) * 100).toFixed(2);
}

// Map a retrieve API item to the card shape used by the result panel / crop dialog.
// exact/balanced 返回完整 ES 文档（payload），fuzzy 只返回 es_id/image_url/create_time/camera_locate/similarity 精简字段。
function mapTextSearchItem(item: TextSearchItem, index: number) {
  const payload = item.payload ?? {};
  const isFlatItem = !item.payload;
  const titleParts = [
    payload.sex,
    payload.top_color?.[0] && payload.top_type ? `${payload.top_color[0]}${payload.top_type}` : payload.top_color?.[0],
    payload.bottom_color?.[0] && payload.bottom_type ? `${payload.bottom_color[0]}${payload.bottom_type}` : payload.bottom_color?.[0]
  ].filter(Boolean);
  return {
    title: titleParts.join("·") || `检索结果 ${index + 1}`,
    image: assetUrl(isFlatItem ? item.image_url : payload.image_url),
    video: assetUrl(payload.video_url),
    location: (isFlatItem ? item.camera_locate : payload.camera_locate || payload.camera_id) || "未知摄像头",
    date: formatCreateTime(isFlatItem ? item.create_time : payload.create_time),
    score: similarityToPercent(item.similarity),
    desc: item.esid || item.document_id || item.es_id || "",
    // 目标在原图中的像素框：框选弹窗的默认框选范围（fuzzy 精简模式可能不返回）
    position: isFlatItem ? item.position : payload.position,
    // 结果面板左上角批量勾选
    checked: false
  };
}

export default defineComponent({
  name: "TextImagePage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { ImageCropDialog },
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} }
  },
  data() {
    return {
      query: "",
      searching: false,
      rounds: [] as ChatRound[],
      // 会话分组 / 最近对话：无接口，静态占位
      sessionGroups: ["分组会话文件夹1", "分组会话文件夹2", "分组会话文件夹3"],
      recentChats: ["关于视觉大模型的应用方法…", "帮我查询昨天下午四点的金…", "问题咨询", "万物搜应用于什么时候合…"],
      // 框选弹窗
      cropDialogOpen: false,
      cropTarget: null as any,
      cropAction: "imageSearch" as CropAction,
      // 监控回放弹层
      videoPreviewUrl: ""
    };
  },
  computed: {
    // 右侧面板展示最近一轮已完成检索的结果
    latestItems(): any[] {
      for (let i = this.rounds.length - 1; i >= 0; i--) {
        if (this.rounds[i].done && this.rounds[i].items.length) {
          return this.rounds[i].items;
        }
      }
      return [];
    },
    checkedItems(): any[] {
      return this.latestItems.filter((item) => item.checked);
    },
    cropConfirmLabel(): string {
      const labels: Record<CropAction, string> = { imageSearch: "搜索图像", quickDeploy: "执行布控", track: "还原轨迹" };
      return labels[this.cropAction];
    }
  },
  methods: {
    roundSteps(round: ChatRound): TextSearchProcessStep[] {
      return round.process?.steps ?? [];
    },
    roundUnderstanding(round: ChatRound): string[] {
      return round.process?.understanding?.messages ?? [];
    },
    placeholderFeature() {
      (this as any).showToast("该功能即将上线，敬请期待");
    },
    resetSession() {
      if (this.searching) return;
      this.rounds = [];
      this.query = "";
    },
    goTextVideo() {
      (this as any).setRoute("exact");
    },
    goImageSearch() {
      (this as any).setRoute("imageSearch");
    },
    send() {
      const message = this.query.trim();
      if (!message) {
        (this as any).showToast("请输入目标描述后再发送");
        return;
      }
      if (this.searching) return;
      const round: ChatRound = {
        query: message,
        time: formatChatTime(new Date()),
        loading: true,
        done: false,
        error: "",
        process: null,
        resultMessage: "",
        items: [],
        thinkCollapsed: false
      };
      this.rounds.push(round);
      this.query = "";
      this.scrollChatToBottom();
      this.runQuery(this.rounds.length - 1);
    },
    regenerate(round: ChatRound) {
      const index = this.rounds.indexOf(round);
      if (this.searching || index < 0 || this.rounds[index].loading) return;
      this.runQuery(index);
    },
    // 注意：必须通过 this.rounds[index] 代理改写字段，直接改入参原始对象会绕过 Vue 响应式触发
    async runQuery(index: number) {
      const round = this.rounds[index];
      if (!round) return;
      this.searching = true;
      round.loading = true;
      round.done = false;
      round.error = "";
      try {
        const response = await api.textSearchQuery({ message: round.query, pageSize: 24 });
        const data = response.data ?? {};
        const items = data.items ?? [];
        round.items = items.map(mapTextSearchItem);
        round.process = data.process ?? null;
        round.resultMessage = response.message || `检测到${items.length}张目标图像`;
        round.done = true;
      } catch (error) {
        round.items = [];
        round.process = null;
        round.error = error instanceof Error ? error.message : "文搜图检索失败";
        (this as any).showToast(round.error);
      } finally {
        round.loading = false;
        this.searching = false;
        this.scrollChatToBottom();
      }
    },
    scrollChatToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.chatScroll as HTMLElement | undefined;
        if (el) {
          el.scrollTop = el.scrollHeight;
        }
      });
    },
    // 打开框选弹窗（默认框选范围取条目 position 像素框）
    openCrop(item: any, action: CropAction) {
      if (!item || !item.image) return;
      this.cropTarget = item;
      this.cropAction = action;
      this.cropDialogOpen = true;
    },
    closeCrop() {
      this.cropDialogOpen = false;
      this.cropTarget = null;
    },
    // 框选确认：携结果图与框选区域跳转对应页面
    confirmCrop(payload: any) {
      const item = this.cropTarget;
      const crop = payload?.crop;
      const action = this.cropAction;
      this.closeCrop();
      if (!item || !item.image || !crop) return;
      if (action === "quickDeploy") {
        (this as any).setRoute("newDeployTask", { prefill: item.image, imageCrop: crop });
      } else if (action === "track") {
        (this as any).setRoute("track", { prefill: item.image, imageCrop: crop, trackView: "timeline" });
      } else {
        (this as any).setRoute("imageSearch", { prefill: item.image, imageCrop: crop });
      }
    },
    jumpImageSearch(round: ChatRound) {
      if (!round.items.length) {
        (this as any).showToast("暂无可用的检索结果");
        return;
      }
      this.openCrop(round.items[0], "imageSearch");
    },
    jumpTrack(round: ChatRound) {
      if (!round.items.length) {
        (this as any).showToast("暂无可用的检索结果");
        return;
      }
      this.openCrop(round.items[0], "track");
    },
    // 面板级轨迹还原：取首张勾选的图像
    jumpTrackSelection() {
      if (!this.checkedItems.length) {
        (this as any).showToast("请先勾选目标图像");
        return;
      }
      this.openCrop(this.checkedItems[0], "track");
    },
    playVideo(item: any) {
      if (item && item.video) {
        this.videoPreviewUrl = item.video;
      } else {
        (this as any).showToast("该结果暂无监控视频");
      }
    }
  }
});
</script>
