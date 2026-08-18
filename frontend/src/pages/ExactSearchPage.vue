<template>
  <section class="content wide exact-page" @click="handleExactBlankClick">
    <div class="title-row"><div><h1 class="page-title">文搜视频</h1><p class="page-subtitle">通过自然语言描述搜索和分析监控视频片段。</p></div></div>
    <div class="panel exact-source-panel">
      <div class="exact-source-modebar"><div class="exact-mode-tabs" role="tablist"><button class="exact-mode-tab" :class="{ active: sourceMode === 'online' }" role="tab" :aria-selected="sourceMode === 'online'" @click="setSourceMode('online')">在线监控点</button><button class="exact-mode-tab" :class="{ active: sourceMode === 'upload' }" role="tab" :aria-selected="sourceMode === 'upload'" @click="setSourceMode('upload')">上传本地视频</button></div></div>
      <div v-if="sourceMode === 'online'" class="exact-online-pane">
        <div class="exact-source-form" @click.stop>
          <div class="deploy-field"><label>区域 / 监控点</label><div class="exact-tree-select"><button class="exact-tree-trigger" :class="{ open: pointDropdownOpen }" @click="togglePointDropdown"><span>{{ selectedPointLabel }}</span><span>{{ pointDropdownOpen ? '收起' : '展开' }}⌄</span></button><div v-if="pointDropdownOpen" class="exact-tree-dropdown"><div v-for="area in areas" :key="area.name"><button class="exact-tree-area-row" :class="{ active: selectedArea && selectedArea.name === area.name }" @click="toggleArea(area)"><span>{{ expandedAreas[area.name] ? '⌄' : '›' }} {{ area.name }}</span><span>{{ area.count }} 台设备</span></button><div v-if="expandedAreas[area.name]" class="exact-tree-children"><button v-for="camera in area.cameras" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" @click="selectCamera(camera, area)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button></div></div></div></div></div>
          <div class="deploy-field"><label>开始时间</label><input class="input" v-model="onlineStart" :placeholder="currentTimePlaceholder" aria-label="开始时间" @input="markPendingSourceChange" /></div>
          <div class="deploy-field"><label>结束时间</label><input class="input" v-model="onlineEnd" :placeholder="currentTimePlaceholder" aria-label="结束时间" @input="markPendingSourceChange" /></div>
          <button class="btn primary" @click="searchOnlineSources">⌕ 搜索回放</button>
        </div>
        <div v-if="selectedCamera" class="hint-text" style="padding:0 16px 14px;">已选择：{{ selectedArea.name }} / {{ selectedCamera.name }} · {{ selectedArea.count }} 台设备区域</div>
      </div>
      <div v-else class="exact-last-video-panel">
        <input ref="exactVideoInput" class="hidden-file-input" type="file" accept="video/*,.mkv" @change="onFileChange" />
        <div class="exact-upload-actions" @click.stop><button class="btn" @click="clearLocalVideo">清空已上传视频</button><button class="btn" @click="triggerUpload">重新上传视频</button><button class="btn primary" :disabled="!localVideoUrl" @click="useLastLocalVideo">使用已上传视频</button></div>
        <div v-if="localFileName" class="exact-last-video-card"><img :src="store.img.analyst" alt="已上传本地视频" /><div><strong>{{ localFileName }}</strong><p>{{ localFileSize }} · 已载入本地预览</p><div class="tags"><span class="tag blue">已上传</span><span class="tag">支持时间定位</span></div></div></div>
        <div v-else class="exact-upload-drop" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop"><div><span class="upload-mark">＋</span><strong>点击上传或拖拽视频到此处</strong><span class="hint-text">支持本地视频预览与时间定位</span></div></div>
      </div>
    </div>

    <div v-if="sourceConfirmed" class="exact-analysis-shell">
      <div v-if="pendingSourceChange" class="exact-pending-mask" @click="cancelPendingSourceChange"><div><strong>视频源已调整，尚未生效</strong><p>下方结果仍保留。点击「搜索回放」生效，点击空白区域可还原到之前的选择与结果</p></div></div>
    <div class="exact-analysis-layout">
      <div class="panel exact-left-workspace">
      <div class="exact-video-panel">
        <div class="exact-player">
          <div class="exact-player-media"><video v-if="selectedSource.videoUrl" ref="exactVideo" :src="selectedSource.videoUrl" muted playsinline @timeupdate="syncVideoTime" @loadedmetadata="syncVideoTime" @ended="playerPlaying = false"></video><img v-else :src="selectedSource.image" :alt="selectedSource.name" /></div>
          <div class="exact-player-overlay"><span class="exact-live-dot"></span><span>{{ videoViewLabel }} · {{ selectedSource.cameraName || selectedSource.camera }}</span></div>
          <template v-if="analyzed"><span v-for="event in events" :key="event.name" class="exact-event-marker" :style="{ left: ((event.start / playerDuration) * 100) + '%' }" :title="event.name"></span></template>
          <div class="exact-player-controls"><button @click="togglePlay">{{ playerPlaying ? '暂停' : '播放' }}</button><span>{{ formatTime(currentTime) }}</span><input type="range" min="0" :max="playerDuration" step="1" :value="currentTime" @input="seekVideo($event)" /><span>{{ formatTime(playerDuration) }}</span><select v-model.number="playbackRate" class="exact-rate-select" @change="changePlaybackRate"><option :value="0.5">0.5x</option><option :value="1">1x</option><option :value="1.5">1.5x</option><option :value="2">2x</option></select></div>
        </div>
      </div>
      <section class="exact-query-panel">
        <div class="exact-query-workspace">
          <div class="exact-dialog-chat-head"><strong>视频问答</strong></div>
          <div class="exact-chat-messages">
            <div v-for="(message, index) in questionMessages" :key="index" class="exact-chat-message" :class="message.role">{{ message.text }}</div>
            <div v-if="questionBusy" class="exact-chat-loading">分析助手正在结合视频内容整理答案...</div>
          </div>
          <div class="exact-chat-quick"><button v-for="prompt in quickQuestions" :key="prompt" :class="{ active: activeQuickPrompt === prompt || query === prompt }" @click="fillQuickPrompt(prompt)">{{ prompt }}</button></div>
          <div class="exact-query-box"><textarea ref="exactQueryInput" class="textarea" v-model="query" :placeholder="analyzed ? '可继续围绕当前视频事件、车辆、人员与时间线提问' : '输入目标、场景、行为或时间特征，系统将生成事件结论。'" @keydown.enter.exact.prevent="submitVideoChat"></textarea><div class="exact-query-send"><button class="btn primary" :disabled="questionBusy" @click="submitVideoChat">发送</button></div></div>
        </div>
      </section>
      </div>
      <aside class="panel exact-dialog-panel">
        <div class="exact-dialog-head"><span class="status-pill" :class="analyzed ? 'pass' : 'waiting'">{{ analyzed ? '分析完成' : '待分析' }}</span><details v-if="analyzed" class="exact-export-menu"><summary class="btn">导出摘要</summary><div class="exact-export-options" role="menu"><button role="menuitem" @click="exportFromMenu('pdf', $event)">导出PDF</button><button role="menuitem" @click="exportFromMenu('word', $event)">导出Word</button><button role="menuitem" @click="exportFromMenu('md', $event)">导出MD</button></div></details></div>
        <div class="exact-dialog-body">
          <div v-if="!analyzed" class="exact-empty-state"><div><strong>等待开始文搜</strong><br /><span>确认视频源后，输入描述并开始分析</span></div></div>
          <template v-else>
            <div class="exact-conclusion">
              <div class="exact-summary-heading"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/></svg><strong>事件摘要</strong></div>
              <div class="exact-summary-section"><div class="exact-summary-section-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>事件概况</div><p>{{ summary.overview }}</p></div>
              <div class="exact-summary-section"><div class="exact-summary-section-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="7" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>涉及人员</div><ul><li v-for="person in summary.persons" :key="person">{{ person }}</li></ul></div>
              <div class="exact-summary-section"><div class="exact-summary-section-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="6" width="18" height="11" rx="2"/><circle cx="8" cy="19" r="2"/><circle cx="16" cy="19" r="2"/></svg>涉及车辆</div><ul><li v-for="vehicle in summary.vehicles" :key="vehicle">{{ vehicle }}</li></ul></div>
            </div>
            <div class="exact-section-title" style="margin-top:16px;"><div><h3>分析结果</h3><p>共识别 {{ events.length }} 个关键事件，点击卡片定位上方视频。</p></div></div>
            <div class="exact-event-list">
              <article v-for="(event, index) in events" :key="event.name" class="exact-event-card" :class="{ active: selectedEventIndex === index }" @click="selectEvent(index)">
                <img :src="event.image" :alt="event.name" />
                <div>
                  <div class="exact-event-meta"><strong>发生时间 {{ event.time }}</strong><span>回放定位</span></div>
                  <h4>{{ event.name }}</h4>
                  <p>{{ event.detail }}</p>
                  <div class="exact-event-actions"><button class="btn" @click.stop="openResultCrop('imageSearch', event, index)">以图搜图</button><button class="btn primary" @click.stop="openResultCrop('quickDeploy', event, index)">快速布防</button><button class="btn" @click.stop="openResultCrop('track', event, index)">轨迹还原</button></div>
                </div>
              </article>
            </div>
          </template>
        </div>
      </aside>
    </div>
    </div>
  </section>
  <image-crop-dialog :open="cropDialogOpen" :item="cropTarget" :action="cropAction" :item-index="cropTargetIndex" @close="closeResultCrop" @confirm="confirmResultCrop"></image-crop-dialog>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import ImageCropDialog from "../components/ImageCropDialog.vue";

export default defineComponent({
  name: "ExactSearchPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { ImageCropDialog },
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
  },
  mounted() {
    this.$nextTick(() => this.applySourceFieldHints());
  },
  updated() {
    this.$nextTick(() => this.applySourceFieldHints());
  },
  data() {
    const img = (this as any).store.img;
    const lastLocalVideo = this.store && this.store.lastLocalVideo ? this.store.lastLocalVideo : {};
    return {
      sourceMode: "online",
      selectedArea: null,
      selectedCamera: null,
      pointDropdownOpen: false,
      expandedAreas: {
        "园区南门": true,
        "A座停车区": false,
        "生产通道": false,
        "仓储区域": false,
        "外围周界": false
      },
      onlineSearched: false,
      onlineSources: [],
      sourcePage: 1,
      sourcePageSize: 2,
      onlineStart: "",
      onlineEnd: "",
      localFileName: lastLocalVideo.name || "",
      localFileSize: lastLocalVideo.size || "",
      localVideoUrl: lastLocalVideo.url || "",
      selectedSource: null,
      sourceConfirmed: false,
      pendingSourceChange: false,
      cropDialogOpen: false,
      cropAction: "",
      cropTarget: null,
      cropTargetIndex: -1,
      activeQuickPrompt: "",
      query: "查找视频中出现的白色车辆，以及人员进入限制区域的情况",
      analyzed: false,
      videoView: "record",
      questionInput: "",
      questionBusy: false,
      questionMessages: [],
      quickQuestions: ["这段视频发生了什么？", "车辆的特征是什么？", "按时间梳理事件", "是否需要布控？"],
      lastQuery: "",
      selectedEventIndex: 0,
      currentTime: 0,
      playerDuration: 3600,
      playerPlaying: false,
      playbackRate: 1,
      playTimer: null,
      areas: [
        {
          name: "园区南门",
          count: 12,
          cameras: [
            { name: "南门入口枪机", code: "CAM-001", type: "枪机", status: "在线", image: img.car },
            { name: "南门广角球机", code: "CAM-002", type: "球机", status: "在线", image: img.target },
            { name: "访客通道半球", code: "CAM-009", type: "半球", status: "在线", image: img.portrait }
          ]
        },
        {
          name: "A座停车区",
          count: 8,
          cameras: [
            { name: "A1停车场东侧", code: "CAM-003", type: "枪机", status: "在线", image: img.car },
            { name: "A2停车场出口", code: "CAM-008", type: "枪机", status: "在线", image: img.target }
          ]
        },
        {
          name: "生产通道",
          count: 6,
          cameras: [
            { name: "生产通道1号门", code: "CAM-004", type: "半球", status: "在线", image: img.analyst },
            { name: "生产通道东侧", code: "CAM-010", type: "枪机", status: "在线", image: img.map }
          ]
        },
        {
          name: "仓储区域",
          count: 10,
          cameras: [
            { name: "仓储区西门", code: "CAM-005", type: "枪机", status: "连接异常", image: img.ai },
            { name: "仓储装卸口", code: "CAM-011", type: "热成像", status: "在线", image: img.mountain }
          ]
        },
        {
          name: "外围周界",
          count: 7,
          cameras: [
            { name: "外围周界北侧", code: "CAM-006", type: "热成像", status: "连接异常", image: img.mountain },
            { name: "东侧围栏通道", code: "CAM-012", type: "枪机", status: "在线", image: img.map }
          ]
        }
      ],
      events: [
        { name: "人员进入禁区", time: "09:15:26", start: 16, image: img.portrait, detail: "检测到一名人员从园区南门入口进入限制区域，停留约 12 秒后向东侧通道移动。" },
        { name: "白色车辆停留", time: "09:16:42", start: 92, image: img.car, detail: "识别到一辆白色车辆在南门入口短暂停留，未观察到明显上下客动作。" },
        { name: "目标离开画面", time: "09:18:08", start: 178, image: img.target, detail: "目标沿访客通道方向离开当前监控画面，建议结合相邻点位继续追踪。" }
      ],
      results: [
        { title: "目标提取", value: "白色车辆 1 辆、人员 1 名", detail: "系统已从视频片段中提取主要目标，并关联到 3 个关键时间点。" },
        { title: "场景判断", value: "园区南门 / 访客通道", detail: "视频画面与所选点位、时间范围匹配，光照和画面质量满足分析条件。" },
        { title: "行为分析", value: "进入限制区域后短暂停留", detail: "人员进入禁区后，白色车辆在入口附近停留，存在时序关联，建议人工复核。" }
      ],
      summary: {
        overview: "2026-07-24 09:15:26 - 09:18:08，园区南门访客通道内，一名人员进入限制区域，白色车辆在入口附近短暂停留，随后目标沿东侧通道离开画面。",
        persons: ["男性 1 名，约 30-45 岁，中等身材，深色外套。"],
        vehicles: ["白色车辆 1 辆，停留于南门入口附近。", "未发现明显上下客动作，建议结合相邻点位复核。"]
      }
    };
  },
  computed: {
    activeCameras() {
      return this.selectedArea ? (this.selectedArea as any).cameras : [];
    },
    selectedEvent() {
      return this.events[this.selectedEventIndex] || this.events[0];
    },
    selectedPointLabel() {
      if (this.selectedArea && this.selectedCamera) return `${(this.selectedArea as any).name} / ${(this.selectedCamera as any).name}`;
      if (this.selectedArea) return `${(this.selectedArea as any).name} / 请选择监控点`;
      return "请选择区域 / 监控点";
    },
    paginatedSources() {
      const start = (this.sourcePage - 1) * this.sourcePageSize;
      return this.onlineSources.slice(start, start + this.sourcePageSize);
    },
    sourcePageCount() {
      return Math.max(1, Math.ceil(this.onlineSources.length / this.sourcePageSize));
    },
    currentTimePlaceholder() {
      const now = new Date();
      const pad = (value) => String(value).padStart(2, '0');
      return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
    },
    processText() {
      if (this.analyzed) return "已完成视频分析，可点击事件卡片定位视频画面";
      if (this.sourceConfirmed) return "视频源已确认，请输入描述开始文搜";
      return this.sourceMode === "online" ? "选择在线监控点并搜索回放片段" : "上传本地视频后进入文搜";
    },
    sourceTypeLabel() {
      return this.selectedSource && (this.selectedSource as any).sourceType === "本地上传" ? "本地视频" : "在线监控";
    },
    videoViewLabel() {
      return this.videoView === "live" ? "实时视频" : "录像回放";
    }
  },
  methods: {
    applySourceFieldHints() {
      const root = this.$el as any;
      const page = root && typeof root.querySelectorAll === 'function'
        ? root
        : (root && root.nextElementSibling ? root.nextElementSibling : document.querySelector('.exact-page'));
      if (!page) return;
      (page.querySelectorAll('.exact-source-form .deploy-field > label') as NodeListOf<HTMLElement>).forEach((label) => { label.hidden = true; });
      const now = new Date();
      const pad = (value) => String(value).padStart(2, '0');
      const currentTime = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
      const fieldHints = [currentTime, currentTime];
      (page.querySelectorAll('.exact-source-form .deploy-field input.input') as NodeListOf<HTMLInputElement>).forEach((input, index) => {
        const placeholder = fieldHints[index];
        if (placeholder) { input.placeholder = placeholder; input.setAttribute('aria-label', placeholder); }
      });
      page.querySelectorAll('.exact-source-form .exact-tree-trigger').forEach((button) => button.setAttribute('aria-label', '区域 / 监控点'));
    },
    setSourceMode(mode) {
      this.sourceMode = mode;
      this.pointDropdownOpen = false;
      this.onlineSearched = false;
      this.onlineSources = [];
    },
    togglePointDropdown() {
      this.pointDropdownOpen = !this.pointDropdownOpen;
    },
    toggleArea(area) {
      const nextExpanded = !this.expandedAreas[area.name];
      if (!this.selectedArea || (this.selectedArea as any).name !== area.name) {
        this.selectedArea = area;
        if (!this.sourceConfirmed) {
          this.selectedCamera = null;
          this.onlineSearched = false;
          this.onlineSources = [];
        } else if (!this.selectedCamera) {
          this.pendingSourceChange = true;
        }
      }
      this.expandedAreas[area.name] = nextExpanded;
    },
    selectArea(area) {
      this.selectedArea = area;
      this.selectedCamera = null;
      this.expandedAreas[area.name] = true;
      this.onlineSearched = false;
      this.onlineSources = [];
      if (this.sourceConfirmed) this.pendingSourceChange = true;
    },
    selectCamera(camera, area) {
      if (area) this.selectedArea = area;
      this.selectedCamera = camera;
      this.pointDropdownOpen = false;
      if (this.sourceConfirmed) this.pendingSourceChange = true;
    },
    markPendingSourceChange() {
      if (this.sourceConfirmed) this.pendingSourceChange = true;
    },
    cancelPendingSourceChange() {
      if (!this.pendingSourceChange || !this.selectedSource) return;
      const selectedSource = this.selectedSource as any;
      if (selectedSource.sourceType !== "本地上传") {
        const area = this.areas.find(item => item.name === selectedSource.areaName)
          || this.areas.find(item => item.cameras.some(camera => camera.code === selectedSource.camera));
        if (area) {
          this.selectedArea = area;
          this.selectedCamera = area.cameras.find(camera => camera.code === selectedSource.camera) || null;
          this.expandedAreas[area.name] = true;
        }
        if (selectedSource.time && selectedSource.time.indexOf(" - ") > -1) {
          const parts = selectedSource.time.split(" - ");
          this.onlineStart = parts[0];
          this.onlineEnd = parts[1];
        }
      }
      this.pointDropdownOpen = false;
      this.pendingSourceChange = false;
      this.showToast("已还原到当前生效的视频源与结果");
    },
    handleExactBlankClick(event) {
      if (!this.pendingSourceChange) return;
      const target = event.target as HTMLElement;
      if (target && target.closest(".exact-source-form")) return;
      this.cancelPendingSourceChange();
    },
    fillQuickPrompt(prompt) {
      this.query = prompt;
      this.activeQuickPrompt = prompt;
      this.$nextTick(() => {
        const input = this.$refs.exactQueryInput as HTMLTextAreaElement;
        if (input && input.focus) input.focus();
      });
    },
    searchOnlineSources() {
      if (!this.selectedArea || !this.selectedCamera) {
        this.showToast("请先选择区域和监控点位");
        return;
      }
      this.onlineSearched = true;
      this.sourcePage = 1;
      const selectedArea = this.selectedArea as any;
      const selectedCamera = this.selectedCamera as any;
      const source = {
        id: "SRC-" + selectedCamera.code,
        name: selectedCamera.name + " · 监控回放",
        camera: selectedCamera.code,
        cameraName: selectedCamera.name,
        areaName: selectedArea.name,
        time: this.onlineStart + " - " + this.onlineEnd,
        clipTime: this.onlineStart + " - " + this.onlineEnd,
        duration: "03:20",
        durationSeconds: 200,
        image: selectedCamera.image,
        sourceType: "在线监控"
      };
      this.onlineSources = [source];
      if (this.sourceConfirmed) {
        this.applyOnlineSource(source);
        this.showToast("已切换录像回放，下方结果已更新");
      } else {
        this.useOnlineSource(source);
        this.showToast("已找到该监控点回放画面");
      }
    },
    goSourcePage(page) {
      this.sourcePage = Math.min(Math.max(page, 1), this.sourcePageCount);
    },
    useOnlineSource(source) {
      this.applyOnlineSource(source);
      this.showToast("视频源已确定，可以开始文搜");
    },
    applyOnlineSource(source) {
      this.stopSimulation();
      this.selectedSource = source;
      this.sourceConfirmed = true;
      this.pendingSourceChange = false;
      this.analyzed = false;
      this.videoView = "record";
      this.currentTime = 0;
      this.playerDuration = source.durationSeconds || 200;
      this.seedQuestionMessages();
    },
    seedQuestionMessages() {
      this.questionMessages = [{
        role: "assistant",
        text: `已连接${this.videoViewLabel}：${this.selectedSource ? (this.selectedSource as any).name : "当前视频源"}。完成文搜后可继续提问，我会结合当前回放时间和事件结果回答。`
      }];
      this.questionInput = "";
      this.questionBusy = false;
    },
    switchVideoView(view) {
      this.videoView = view;
      this.stopSimulation();
      this.showToast(view === "live" ? "已切换到实时视频视图" : "已切换到录像回放视图");
    },
    triggerUpload() {
      (this.$refs.exactVideoInput as HTMLInputElement).click();
    },
    handleDrop(event) {
      const file = event.dataTransfer.files && event.dataTransfer.files[0];
      if (file) this.loadLocalVideo(file);
    },
    onFileChange(event) {
      const file = event.target.files && event.target.files[0];
      if (file) this.loadLocalVideo(file);
    },
    loadLocalVideo(file) {
      const valid = file.type.startsWith("video/") || /\.(mp4|mov|avi|mkv)$/i.test(file.name);
      if (!valid) {
        this.showToast("请选择 mp4、mov、avi 或 mkv 视频文件");
        return;
      }
      if (this.store.lastLocalVideo && this.store.lastLocalVideo.url) URL.revokeObjectURL(this.store.lastLocalVideo.url);
      this.localVideoUrl = URL.createObjectURL(file);
      this.localFileName = file.name;
      this.localFileSize = `${(file.size / 1024 / 1024).toFixed(1)} MB`;
      this.store.lastLocalVideo = { name: this.localFileName, size: this.localFileSize, url: this.localVideoUrl };
      this.showToast("本地视频已载入，请确认视频源");
    },
    useLastLocalVideo() {
      if (!this.localVideoUrl) {
        this.showToast("还没有可用的本地视频");
        return;
      }
      this.confirmLocalSource();
    },
    confirmLocalSource() {
      if (!this.localVideoUrl) {
        this.showToast("请先上传一段视频");
        return;
      }
      this.stopSimulation();
      this.selectedSource = {
        id: "LOCAL-001",
        name: this.localFileName,
        camera: "本地视频文件",
        time: "本地上传 · 待分析",
        duration: "00:45",
        durationSeconds: 2700,
        image: (this as any).store.img.analyst,
        videoUrl: this.localVideoUrl,
        sourceType: "本地上传"
      };
      this.sourceConfirmed = true;
      this.pendingSourceChange = false;
      this.analyzed = false;
      this.videoView = "record";
      this.currentTime = 0;
      this.playerDuration = 2700;
      this.seedQuestionMessages();
      this.showToast("视频源已确定，可以开始文搜");
    },
    clearLocalVideo() {
      if (this.localVideoUrl) URL.revokeObjectURL(this.localVideoUrl);
      this.localVideoUrl = "";
      this.localFileName = "";
      this.localFileSize = "";
      this.store.lastLocalVideo = null;
      if (this.$refs.exactVideoInput) (this.$refs.exactVideoInput as HTMLInputElement).value = "";
    },
    backToSource() {
      this.stopSimulation();
      this.sourceConfirmed = false;
      this.pendingSourceChange = false;
      this.analyzed = false;
      this.questionMessages = [];
      this.questionInput = "";
      this.currentTime = 0;
    },
    resetSearch() {
      this.stopSimulation();
      this.sourceMode = "online";
      this.pointDropdownOpen = false;
      this.selectedArea = null;
      this.selectedCamera = null;
      this.onlineSearched = false;
      this.onlineSources = [];
      this.sourcePage = 1;
      this.onlineStart = "2026-07-24 09:00";
      this.onlineEnd = "2026-07-24 10:00";
      this.selectedSource = null;
      this.sourceConfirmed = false;
      this.pendingSourceChange = false;
      this.analyzed = false;
      this.videoView = "record";
      this.questionMessages = [];
      this.questionInput = "";
      this.currentTime = 0;
      this.query = "查找视频中出现的白色车辆，以及人员进入限制区域的情况";
    },
    startAnalysis() {
      if (!this.selectedSource) {
        this.showToast("请先确定视频源");
        return;
      }
      if (!this.query.trim()) {
        this.showToast("请输入需要检索的内容");
        return;
      }
      const question = this.query.trim();
      this.lastQuery = question;
      this.questionMessages.push({ role: "user", text: question });
      this.analyzed = true;
      this.selectedEventIndex = 0;
      this.currentTime = this.events[0].start;
      this.seekVideo(this.currentTime);
      this.questionMessages.push({
        role: "assistant",
        text: `已完成视频源文搜。\n\n事件摘要：${this.summary.overview}\n\n已识别 ${this.events.length} 个关键事件，右侧可查看事件摘要、分析结果，并继续对视频提问。`
      });
      this.query = "";
      this.showToast("文搜分析完成，已生成事件结论");
    },
    submitVideoChat() {
      this.activeQuickPrompt = "";
      if (this.analyzed) this.askVideoQuestion(this.query);
      else this.startAnalysis();
    },
    formatTime(seconds) {
      const value = Math.max(0, Math.floor(Number(seconds) || 0));
      const h = Math.floor(value / 3600);
      const m = Math.floor((value % 3600) / 60);
      const s = value % 60;
      return h ? `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    },
    syncVideoTime(event) {
      this.currentTime = event.target.currentTime;
      if (event.target.duration && Number.isFinite(event.target.duration)) this.playerDuration = event.target.duration;
    },
    seekVideo(value) {
      const next = typeof value === "number" ? value : Number(value.target.value);
      this.currentTime = next;
      const video = this.$refs.exactVideo as HTMLVideoElement;
      if (video) video.currentTime = next;
    },
    togglePlay() {
      const video = this.$refs.exactVideo as HTMLVideoElement;
      if (video) {
        if (video.paused) {
          video.playbackRate = this.playbackRate;
          video.play();
          this.playerPlaying = true;
        } else {
          video.pause();
          this.playerPlaying = false;
        }
        return;
      }
      if (this.playerPlaying) this.stopSimulation();
      else {
        this.playerPlaying = true;
        this.playTimer = window.setInterval(() => {
          this.currentTime += this.playbackRate;
          if (this.currentTime >= this.playerDuration) {
            this.currentTime = this.playerDuration;
            this.stopSimulation();
          }
        }, 1000);
      }
    },
    stopSimulation() {
      if (this.playTimer) window.clearInterval(this.playTimer);
      this.playTimer = null;
      this.playerPlaying = false;
      const video = this.$refs.exactVideo as HTMLVideoElement;
      if (video && !video.paused) video.pause();
    },
    changePlaybackRate() {
      const video = this.$refs.exactVideo as HTMLVideoElement;
      if (video) video.playbackRate = this.playbackRate;
    },
    selectEvent(index) {
      const event = this.events[index];
      if (!event) return;
      this.selectedEventIndex = index;
      this.seekVideo(event.start);
      this.showToast(`已定位到 ${event.time} 事件画面`);
    },
    askVideoQuestion(text) {
      const question = String(typeof text === "string" ? text : (this.questionInput || "")).trim();
      if (!this.selectedSource) {
        this.showToast("请先确定视频源");
        return;
      }
      if (!this.analyzed) {
        this.query = question;
        this.startAnalysis();
        return;
      }
      if (!question || this.questionBusy) return;
      this.questionMessages.push({ role: "user", text: question });
      this.query = "";
      this.questionInput = "";
      this.questionBusy = true;
      window.setTimeout(() => {
        const lower = question.toLowerCase();
        let answer = `已结合当前${this.videoViewLabel}进行分析：${this.summary.overview}`;
        if (question.includes("时间") || question.includes("什么时候") || question.includes("几点")) {
          answer = `事件时间线：${this.events.map(item => `${item.time} ${item.name}`).join("；")}。点击右侧事件卡片可直接定位回放。`;
        } else if (question.includes("车") || lower.includes("plate")) {
          answer = `车辆分析：${this.summary.vehicles.join(" ")} 当前重点事件为“${this.events[1].name}”，发生时间 ${this.events[1].time}。`;
        } else if (question.includes("人") || question.includes("人员") || question.includes("特征")) {
          answer = `人员分析：${this.summary.persons[0]} 该人员从南门入口进入限制区域，约停留 12 秒后向东侧通道移动。`;
        } else if (question.includes("布控") || question.includes("布防")) {
          answer = "可以对识别到的白色车辆创建布控任务，系统会带入对应事件的车辆特征和时间，点击分析结果条目后的“快速布防”即可继续。";
        }
        this.questionMessages.push({ role: "assistant", text: answer });
        this.questionBusy = false;
      }, 480);
    },
    openResultCrop(action, event, index) {
      this.cropAction = action;
      this.cropTarget = {
        ...event,
        title: event.name,
        date: `2026-07-24 ${event.time}`
      };
      this.cropTargetIndex = index;
      this.cropDialogOpen = true;
    },
    closeResultCrop() {
      this.cropDialogOpen = false;
      this.cropAction = "";
      this.cropTarget = null;
      this.cropTargetIndex = -1;
    },
    confirmResultCrop(payload) {
      const { action, item, index, crop: selection } = payload;
      const crop = { ...selection, sourceName: item.title, sourceTime: item.date, sourceIndex: index };
      const matchingResultIndex = this.store.results.findIndex(result => result.image === item.image);
      this.closeResultCrop();
      if (action === "imageSearch") {
        this.setRoute("imageSearch", { prefill: item.image, imageCrop: crop });
      } else if (action === "quickDeploy") {
        this.setRoute("newDeployTask", { prefill: item.image, imageCrop: crop });
      } else if (action === "track") {
        this.setRoute("track", {
          prefill: item.image,
          imageCrop: crop,
          selectedIndexes: matchingResultIndex >= 0 ? [matchingResultIndex] : [],
          trackView: "timeline"
        });
      }
    },
    exportFromMenu(type, event) {
      const menu = (event.currentTarget as HTMLElement).closest("details") as HTMLDetailsElement;
      if (menu) menu.open = false;
      this.exportReport(type);
    },
    reportContent() {
      return `文搜视频分析报告\n\n视频源：${this.selectedSource ? (this.selectedSource as any).name : "-"}\n来源：${this.selectedSource ? this.sourceTypeLabel : "-"}\n检索内容：${this.lastQuery || this.query || "-"}\n\n事件摘要：\n${this.summary.overview}\n涉及人员：${this.summary.persons.join("；")}\n涉及车辆：${this.summary.vehicles.join("；")}\n\n分析事件：\n${this.events.map(item => `${item.time} ${item.name}：${item.detail}`).join("\n")}\n\n分析结果：\n${this.results.map(item => `${item.title}：${item.value}。${item.detail}`).join("\n")}`;
    },
    exportReport(type) {
      if (!this.analyzed) {
        this.showToast("请先完成文搜分析");
        return;
      }
      const labels = { pdf: "PDF", word: "Word", md: "Markdown" };
      if (type === "pdf") {
        this.showToast("PDF 报告已生成，可通过浏览器打印保存");
        return;
      }
      const content = type === "word" ? `<html><meta charset="utf-8"><body><h1>文搜视频分析报告</h1><pre>${this.reportContent()}</pre></body></html>` : `# 文搜视频分析报告\n\n${this.reportContent()}`;
      const blob = new Blob([content], { type: type === "word" ? "application/msword" : "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `文搜视频分析报告.${type === "word" ? "doc" : "md"}`;
      link.click();
      URL.revokeObjectURL(url);
      this.showToast(`${labels[type]} 报告已下载`);
    }
  },
  beforeUnmount() {
    this.stopSimulation();
  }
});
</script>
