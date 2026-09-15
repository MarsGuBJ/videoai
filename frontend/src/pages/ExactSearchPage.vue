<template>
  <section class="content wide exact-page" @click="handleExactBlankClick">
    <div class="title-row"><div><h1 class="page-title">文搜视频</h1><p class="page-subtitle">通过自然语言描述搜索和分析监控视频片段。</p></div></div>
    <div class="panel exact-source-panel">
      <div class="exact-source-modebar"><div class="exact-mode-tabs" role="tablist"><button class="exact-mode-tab" :class="{ active: sourceMode === 'online' }" role="tab" :aria-selected="sourceMode === 'online'" @click="setSourceMode('online')">在线监控点</button><button class="exact-mode-tab" :class="{ active: sourceMode === 'upload' }" role="tab" :aria-selected="sourceMode === 'upload'" @click="setSourceMode('upload')">上传本地视频</button></div></div>
      <div v-if="sourceMode === 'online'" class="exact-online-pane">
        <div class="exact-source-form" @click.stop>
          <div class="deploy-field"><label>区域 / 监控点</label><div class="exact-tree-select"><button class="exact-tree-trigger" :class="{ open: pointDropdownOpen }" @click="togglePointDropdown"><span>{{ selectedPointLabel }}</span><span>{{ pointDropdownOpen ? '收起' : '展开' }}⌄</span></button><div v-if="pointDropdownOpen" class="exact-tree-dropdown"><div v-for="area in areas" :key="area.name"><button class="exact-tree-area-row" :class="{ active: selectedArea && selectedArea.name === area.name }" @click="toggleArea(area)"><span>{{ expandedAreas[area.name] ? '⌄' : '›' }} {{ area.name }}</span><span>{{ area.count }} 台设备</span></button><div v-if="expandedAreas[area.name]" class="exact-tree-children"><button v-for="camera in area.cameras" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" @click="selectCamera(camera, area)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button></div></div></div></div></div>
          <div class="deploy-field"><date-time-range-picker v-model:start="onlineStart" v-model:end="onlineEnd" @change="markPendingSourceChange" /></div>
          <button class="btn primary" :disabled="searching" @click="searchOnlineSources">⌕ 搜索回放</button>
        </div>
      </div>
      <div v-else class="exact-last-video-panel">
        <input ref="exactVideoInput" class="hidden-file-input" type="file" accept="video/*,.mkv" @change="onFileChange" />
        <div class="exact-upload-actions" @click.stop><button class="btn" @click="clearLocalVideo">清空已上传视频</button><button class="btn" @click="triggerUpload">重新上传视频</button><button class="btn primary" :disabled="!localVideoUrl" @click="useLastLocalVideo">使用已上传视频</button></div>
        <div v-if="localFileName" class="exact-last-video-card"><img :src="store.img.analyst" alt="已上传本地视频" /><div><strong>{{ localFileName }}</strong><p>{{ localFileSize }} · 已载入本地预览</p><div class="tags"><span class="tag blue">已上传</span><span class="tag">支持时间定位</span></div></div></div>
        <div v-else class="exact-upload-drop" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop"><div><span class="upload-mark">＋</span><strong>点击上传或拖拽视频到此处</strong><span class="hint-text">支持本地视频预览与时间定位</span></div></div>
      </div>
    </div>

    <!-- 与文搜图页一致的占位区域：确认视频源前提示操作路径 -->
    <div v-if="!sourceConfirmed" class="search-empty-state exact-source-empty"><strong>还没有开始检索</strong><span>选择在线监控点或上传本地视频后，点击「搜索回放」</span></div>

    <div v-if="sourceConfirmed" class="exact-analysis-shell">
      <div v-if="pendingSourceChange" class="exact-pending-mask" @click="cancelPendingSourceChange"><div><strong>视频源已调整，尚未生效</strong><p>下方结果仍保留。点击「搜索回放」生效，点击空白区域可还原到之前的选择与结果</p></div></div>
    <div class="exact-analysis-layout">
      <div class="panel exact-left-workspace">
      <div class="exact-video-panel">
        <div class="exact-player" ref="exactPlayer">
          <div class="exact-player-media"><video v-if="selectedSource.videoUrl" ref="exactVideo" :src="selectedSource.videoUrl" muted playsinline @timeupdate="syncVideoTime" @loadedmetadata="syncVideoTime" @ended="playerPlaying = false"></video><video-player v-else-if="selectedSource.streamUrl" ref="exactStreamPlayer" :url="selectedSource.streamUrl"></video-player><img v-else :src="selectedSource.image" :alt="selectedSource.name" /></div>
          <button class="exact-fullscreen-btn" type="button" :title="playerFullscreen ? '退出全屏' : '全屏播放'" :aria-label="playerFullscreen ? '退出全屏' : '全屏播放'" @click="togglePlayerFullscreen">
            <svg v-if="!playerFullscreen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="4 14 10 14 10 20"></polyline><polyline points="20 10 14 10 14 4"></polyline><line x1="14" y1="10" x2="21" y2="3"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>
          </button>
          <template v-if="analyzed"><span v-for="event in events" :key="event.name" class="exact-event-marker" :style="{ left: ((event.start / playerDuration) * 100) + '%' }" :title="event.name"></span></template>
          <div class="exact-player-controls"><button @click="togglePlay">{{ playerPlaying ? '暂停' : '播放' }}</button><span>{{ formatTime(currentTime) }}</span><input type="range" min="0" :max="playerDuration" step="1" :value="currentTime" @input="seekVideo($event)" /><span>{{ formatTime(playerDuration) }}</span><select v-model.number="playbackRate" class="exact-rate-select" @change="changePlaybackRate"><option :value="0.5">0.5x</option><option :value="1">1x</option><option :value="1.5">1.5x</option><option :value="2">2x</option></select></div>
        </div>
      </div>
      <section class="exact-query-panel">
        <div class="exact-query-workspace">
          <div class="exact-dialog-chat-head"><strong>视频问答</strong></div>
          <div class="exact-chat-messages">
            <div v-for="(message, index) in questionMessages" :key="index" class="exact-chat-item" :class="message.role">
              <div class="exact-chat-message" :class="message.role">{{ message.text }}</div>
              <div v-if="message.role === 'assistant' && message.analysisId" class="exact-message-actions">
                <button class="exact-message-analysis-btn" :class="{ active: activeAnalysisId === message.analysisId }" type="button" title="分析概要" aria-label="分析概要" @click="loadAnalysisSnapshot(message.analysisId)">&#xf080;</button>
                <button class="exact-message-reanalysis-btn" type="button" :disabled="questionBusy || analyzing" title="重新分析" aria-label="重新分析" @click="rerunMessageAnalysis(message)">&#xf021;</button>
                <button class="exact-message-detail-btn" type="button" title="分析详情" aria-label="分析详情" @click="openMessageDetail(message)">&#xf05a;</button>
              </div>
            </div>
            <div v-if="questionBusy" class="exact-chat-loading">分析助手正在结合视频内容整理答案...</div>
          </div>
          <div class="exact-chat-quick"><button v-for="prompt in quickQuestions" :key="prompt" :class="{ active: activeQuickPrompt === prompt || query === prompt }" @click="fillQuickPrompt(prompt)">{{ prompt }}</button></div>
          <div class="exact-query-box"><textarea ref="exactQueryInput" class="textarea" v-model="query" :placeholder="analyzed ? '可继续围绕当前视频事件、车辆、人员与时间线提问' : '输入目标、场景、行为或时间特征，系统将生成事件结论。'" @keydown.enter.exact.prevent="submitVideoChat"></textarea><button class="exact-query-send-btn" type="button" :disabled="questionBusy" aria-label="发送" @click="submitVideoChat"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg></button></div>
        </div>
      </section>
      </div>
      <aside class="panel exact-dialog-panel">
        <div class="exact-dialog-head">
          <div class="exact-mode-tabs exact-analysis-tabs" role="tablist" aria-label="分析结果视图">
            <button class="exact-mode-tab" :class="{ active: activeResultTab === 'summary' }" type="button" role="tab" :aria-selected="activeResultTab === 'summary'" @click="activeResultTab = 'summary'">分析概要</button>
            <button v-for="tab in resultTabs" :key="tab.id" class="exact-mode-tab" :class="{ active: activeResultTab === tab.id }" type="button" role="tab" :aria-selected="activeResultTab === tab.id" @click="activeResultTab = tab.id">{{ tab.title }}<span class="exact-tab-close" role="button" tabindex="0" :aria-label="'关闭' + tab.title + '标签页'" title="关闭" @click.stop="closeResultTab(tab.id)" @keydown.enter.stop.prevent="closeResultTab(tab.id)">×</span></button>
          </div>
          <span v-if="activeResultTab === 'summary'" class="status-pill" :class="analyzed ? 'pass' : 'waiting'">{{ analyzed ? '分析完成' : '待分析' }}</span>
        </div>
        <div v-if="activeResultTab === 'summary'" class="exact-dialog-body" role="tabpanel" aria-label="分析概要">
          <div v-if="!analyzed" class="exact-empty-state"><div><strong>等待开始文搜</strong><br /><span>确认视频源后，输入描述并开始分析</span></div></div>
          <template v-else>
            <div class="exact-conclusion">
              <div class="exact-summary-heading"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/></svg><strong>事件摘要</strong><details class="exact-export-menu"><summary class="btn">导出摘要</summary><div class="exact-export-options" role="menu"><button role="menuitem" @click="exportFromMenu('pdf', $event)">导出PDF</button><button role="menuitem" @click="exportFromMenu('word', $event)">导出Word</button><button role="menuitem" @click="exportFromMenu('md', $event)">导出MD</button></div></details></div>
              <div class="exact-summary-section"><div class="exact-summary-section-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>事件概况</div><p>{{ summary.overview }}</p></div>
              <div v-if="summary.persons.length" class="exact-summary-section"><div class="exact-summary-section-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="7" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>涉及人员</div><ul><li v-for="person in summary.persons" :key="person">{{ person }}</li></ul></div>
              <div v-if="summary.vehicles.length" class="exact-summary-section"><div class="exact-summary-section-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="6" width="18" height="11" rx="2"/><circle cx="8" cy="19" r="2"/><circle cx="16" cy="19" r="2"/></svg>涉及车辆</div><ul><li v-for="vehicle in summary.vehicles" :key="vehicle">{{ vehicle }}</li></ul></div>
            </div>
            <div class="exact-section-title" style="margin-top:16px;"><div><h3>分析结果</h3><p>共识别 {{ events.length }} 个关键事件，点击卡片定位上方视频。</p></div></div>
            <div class="exact-event-list">
              <article v-for="(event, index) in events" :key="event.name" class="exact-event-card" :class="{ active: selectedEventIndex === index }" @click="selectEvent(index)">
                <img :src="event.image" :alt="event.name" @error="onEventImageError(event)" />
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
        <div v-else-if="activeResultTabObj && activeResultTabObj.type === 'imageSearch'" class="exact-dialog-body exact-image-search-tab" role="tabpanel" aria-label="以图搜图">
          <div class="panel search-panel i2i-search-panel exact-i2i-search-panel">
            <input ref="exactImageSearchInput" class="hidden-file-input" type="file" accept="image/*" @change="handleImageSearchUpload" />
            <div class="i2i-form-grid exact-i2i-form-grid">
              <button class="i2i-upload-zone" type="button" :title="activeResultTabObj.payload.image ? '点击替换参考图片' : '点击或拖拽图片到此处'" @click="triggerImageSearchUpload" @dragover.prevent @drop.prevent="handleImageSearchUpload">
                <img v-if="activeResultTabObj.payload.image" :src="activeResultTabObj.payload.image" alt="参考图" />
                <span v-if="activeResultTabObj.payload.image && activeResultTabObj.payload.crop" class="i2i-crop-box" :style="cropStyleOf(activeResultTabObj.payload.crop)"></span>
                <span v-if="activeResultTabObj.payload.image" class="i2i-reupload-hint">点击替换图片</span>
                <span v-if="!activeResultTabObj.payload.image"><span class="upload-mark">☁</span><strong>上传图片</strong><small>点击或拖拽图片到此处</small></span>
              </button>
              <div class="exact-i2i-filter-area">
                <div class="exact-i2i-attribute-grid">
                  <div class="deploy-field"><date-time-range-picker v-model:start="activeResultTabObj.start" v-model:end="activeResultTabObj.end" /></div>
                  <div class="deploy-field"><select class="select" v-model="activeResultTabObj.place" aria-label="区域"><option>全部区域</option><option v-for="area in areas" :key="area.name" :value="area.name">{{ area.name }}</option></select></div>
                  <div class="deploy-field similarity-field"><label>相似度：<b>{{ activeResultTabObj.similarity }}%</b></label><input type="range" min="0" max="100" v-model.number="activeResultTabObj.similarity" /></div>
                  <div class="i2i-actions"><button class="btn primary" type="button" :disabled="activeResultTabObj.loading" @click="runImageSearchTab(activeResultTabObj)">⌕ 搜索</button></div>
                </div>
              </div>
            </div>
          </div>
          <div class="result-toolbar exact-i2i-result-toolbar"><div class="result-count">共找到 <b>{{ activeResultTabObj.items.length }}</b> 条相似结果</div></div>
          <div v-if="activeResultTabObj.loading" class="track-empty">正在搜索相似目标，请稍候...</div>
          <image-results v-else-if="activeResultTabObj.items.length" :items="activeResultTabObj.items" :show-score="true" :selectable="false" :hide-jump="true" :show-actions="true" @image-action="onImageSearchAction"></image-results>
          <div v-else class="track-empty">未找到相似目标，可在事件卡片重新框选后再次搜索。</div>
        </div>
        <div v-else-if="activeResultTabObj && activeResultTabObj.type === 'quickDeploy'" class="exact-dialog-body exact-quick-deploy-tab" role="tabpanel" aria-label="快速布防">
          <template v-if="activeResultTabObj.savedTask">
            <div class="detail-header-card exact-deploy-detail-header"><div><h2>{{ activeResultTabObj.savedTask.name }}</h2><p>{{ activeResultTabObj.savedTask.desc }}</p><div class="tags"><span class="tag blue">{{ activeResultTabObj.savedTask.algorithm }}</span><span class="status-pill pass">{{ activeResultTabObj.savedTask.status }}</span><span class="tag">{{ activeResultTabObj.savedTask.area }}</span></div></div></div>
            <div class="panel search-panel exact-deploy-task-info"><h3 class="form-section-title">任务信息</h3><dl class="info-list"><dt>任务ID</dt><dd>{{ activeResultTabObj.savedTask.id }}</dd><dt>算法类型</dt><dd>{{ activeResultTabObj.savedTask.algorithm }}</dd><dt>布控区域</dt><dd>{{ activeResultTabObj.savedTask.area }}</dd><dt>监控点位</dt><dd>{{ activeResultTabObj.savedTask.points }}</dd><dt>生效时间</dt><dd>{{ activeResultTabObj.savedTask.time }}</dd><dt>相似度</dt><dd>{{ activeResultTabObj.savedTask.threshold }}%</dd><dt>创建人</dt><dd>{{ activeResultTabObj.savedTask.owner }}</dd><dt>创建时间</dt><dd>{{ activeResultTabObj.savedTask.created }}</dd></dl></div>
          </template>
          <div v-else class="exact-quick-deploy-form">
            <div class="modal-form-row"><label><span class="required">*</span>任务名称：</label><input class="input" v-model="activeResultTabObj.deployTaskName" placeholder="请输入任务名称" /></div>
            <div class="modal-form-row"><label><span class="required">*</span>布控点位：</label>
              <div class="exact-tree-select" @click.stop>
                <button class="exact-tree-trigger" :class="{ open: activeResultTabObj.deployAreaOpen }" type="button" @click="activeResultTabObj.deployAreaOpen = !activeResultTabObj.deployAreaOpen"><span>{{ deployAreaLabel(activeResultTabObj) }}</span><span>{{ activeResultTabObj.deployAreaOpen ? '收起' : '展开' }}⌄</span></button>
                <div v-if="activeResultTabObj.deployAreaOpen" class="exact-tree-dropdown">
                  <div v-for="area in areas" :key="area.name">
                    <button class="exact-tree-area-row" type="button" @click="toggleDeployArea(activeResultTabObj, area)"><span>{{ activeResultTabObj.deployAreaExpanded[area.name] ? '⌄' : '›' }} {{ area.name }}</span><span>{{ area.count }} 台设备</span></button>
                    <div v-if="activeResultTabObj.deployAreaExpanded[area.name]" class="exact-tree-children">
                      <label v-for="camera in area.cameras" :key="camera.code" class="exact-tree-device deploy-camera-option"><input type="checkbox" :checked="activeResultTabObj.deployCameraSelections.includes(camera.code)" @change="toggleDeployCamera(activeResultTabObj, camera)" /><span>{{ camera.name }}</span><span>{{ camera.status }}</span></label>
                    </div>
                  </div>
                  <div v-if="!areas.length" class="exact-tree-empty">暂无监控点数据</div>
                </div>
              </div>
            </div>
            <div class="modal-form-row"><label>布控目标：</label>
              <div class="deploy-target-field">
                <div v-if="activeResultTabObj.payload.image" class="deploy-target-preview"><img :src="activeResultTabObj.payload.image" :alt="activeResultTabObj.payload.sourceName || '已框选布控目标'" /><span v-if="activeResultTabObj.payload.crop" class="transferred-crop-box" :style="cropStyleOf(activeResultTabObj.payload.crop)"></span></div>
                <span v-else class="hint-text">未带入布控目标图</span>
              </div>
            </div>
            <div class="modal-form-row"><label><span class="required">*</span>布控算法：</label>
              <select class="select" v-model="activeResultTabObj.deployAlgorithmId"><option value="">请选择布控算法</option><option v-for="item in deployAlgorithmOptions" :key="item.id" :value="item.id">{{ item.name }}</option></select>
            </div>
            <div class="modal-form-row"><label><span class="required">*</span>生效日期：</label>
              <div class="effective-range"><input class="input" type="date" v-model="activeResultTabObj.deployEffectiveStart" aria-label="生效开始日期" /><span class="range-arrow">→</span><input class="input" type="date" v-model="activeResultTabObj.deployEffectiveEnd" aria-label="生效结束日期" /></div>
            </div>
            <div class="modal-form-row"><label><span class="required">*</span>循环时段：</label>
              <div class="effective-range"><input class="input" type="time" v-model="activeResultTabObj.deployCycleStart" aria-label="循环开始时间" /><span class="range-arrow">→</span><input class="input" type="time" v-model="activeResultTabObj.deployCycleEnd" aria-label="循环结束时间" /></div>
            </div>
            <div class="modal-form-row"><label><span class="required">*</span>置信度：</label>
              <div class="deploy-similarity-field"><input type="range" min="0" max="100" step="1" v-model.number="activeResultTabObj.deploySimilarity" aria-label="置信度" /><output>{{ activeResultTabObj.deploySimilarity }}%</output></div>
            </div>
            <div class="modal-form-row"><label>任务描述：</label><textarea class="textarea" style="height:96px;" v-model="activeResultTabObj.deployDescription" placeholder="请输入任务描述"></textarea></div>
            <div class="exact-quick-deploy-actions"><button class="btn" type="button" @click="closeResultTab(activeResultTabObj.id)">取消</button><button class="btn primary" type="button" :disabled="activeResultTabObj.deploySaving" @click="saveQuickDeploy(activeResultTabObj)">保存</button></div>
          </div>
        </div>
        <div v-else-if="activeResultTabObj && activeResultTabObj.type === 'track'" class="exact-dialog-body exact-track-tab" role="tabpanel" aria-label="轨迹图">
          <div class="panel search-panel i2i-search-panel exact-i2i-search-panel exact-track-search-panel">
            <input ref="exactTrackTargetInput" class="hidden-file-input" type="file" accept="image/*" @change="handleTrackTargetUpload" />
            <div class="i2i-form-grid exact-i2i-form-grid">
              <button class="i2i-upload-zone" type="button" :title="activeResultTabObj.payload.image ? '点击替换目标图片' : '点击或拖拽图片到此处'" @click="triggerTrackTargetUpload" @dragover.prevent @drop.prevent="handleTrackTargetUpload">
                <img v-if="activeResultTabObj.payload.image" :src="activeResultTabObj.payload.image" alt="目标参考图" />
                <span v-if="activeResultTabObj.payload.image && activeResultTabObj.payload.crop" class="i2i-crop-box" :style="cropStyleOf(activeResultTabObj.payload.crop)"></span>
                <span v-if="activeResultTabObj.payload.image" class="i2i-reupload-hint">点击替换图片</span>
                <span v-if="!activeResultTabObj.payload.image"><span class="upload-mark">☁</span><strong>目标参考图</strong><small>点击或拖拽图片到此处</small></span>
              </button>
              <div class="exact-i2i-filter-area">
                <div class="exact-i2i-attribute-grid">
                  <div class="deploy-field"><date-time-range-picker v-model:start="activeResultTabObj.start" v-model:end="activeResultTabObj.end" /></div>
                  <div class="deploy-field" @click.stop>
                    <div class="exact-tree-select">
                      <button class="exact-tree-trigger" :class="{ open: activeResultTabObj.pointDropdownOpen }" type="button" @click="toggleTrackPointDropdown(activeResultTabObj)"><span>{{ trackSearchPointLabel(activeResultTabObj) }}</span><span>{{ activeResultTabObj.pointDropdownOpen ? '收起' : '展开' }}⌄</span></button>
                      <div v-if="activeResultTabObj.pointDropdownOpen" class="exact-tree-dropdown">
                        <div v-for="area in areas" :key="area.name">
                          <button class="exact-tree-area-row" :class="{ active: activeResultTabObj.searchArea && activeResultTabObj.searchArea.name === area.name }" type="button" @click="toggleTrackSearchArea(activeResultTabObj, area)"><span>{{ activeResultTabObj.expandedAreas[area.name] ? '⌄' : '›' }} {{ area.name }}</span><span>{{ area.count }} 台设备</span></button>
                          <div v-if="activeResultTabObj.expandedAreas[area.name]" class="exact-tree-children">
                            <button v-for="camera in area.cameras" :key="camera.code" class="exact-tree-device" :class="{ active: activeResultTabObj.searchCamera && activeResultTabObj.searchCamera.code === camera.code }" type="button" @click="selectTrackSearchCamera(activeResultTabObj, camera, area)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button>
                          </div>
                        </div>
                        <div v-if="!areas.length" class="exact-tree-empty">暂无监控点数据</div>
                      </div>
                    </div>
                  </div>
                  <div class="deploy-field similarity-field"><label>相似度阈值：<b>{{ activeResultTabObj.threshold }}%</b></label><input type="range" min="0" max="100" v-model.number="activeResultTabObj.threshold" /></div>
                  <div class="i2i-actions"><button class="btn primary" type="button" :disabled="activeResultTabObj.loading" @click="runTrackSearch(activeResultTabObj)">⌕ 搜索候选图片</button></div>
                </div>
              </div>
            </div>
          </div>
          <div v-if="activeResultTabObj.loading" class="track-empty">正在搜索目标轨迹，请稍候...</div>
          <div v-else-if="activeResultTabObj.items.length" class="track-result-content exact-track-result-content">
            <div class="metric-row"><span class="metric">总时长：<b>{{ trackDurationOf(activeResultTabObj.items) }}</b></span><span class="metric">经过点位：<b>{{ trackPointCountOf(activeResultTabObj.items) }}</b></span><span class="metric">轨迹置信：<b>{{ trackConfidenceOf(activeResultTabObj.items) }}%</b></span></div>
            <div class="timeline">
              <article class="timeline-card" v-for="item in activeResultTabObj.items" :key="item.title + item.date">
                <div><h4>{{ item.title }}</h4><p>{{ item.desc }}</p><div class="tags"><span class="tag blue">{{ item.location }}</span><span class="tag">相似度 {{ item.score }}%</span></div></div>
                <div class="timeline-card-controls"><span class="hint-text timeline-card-date">{{ item.date }}</span></div>
                <button class="timeline-image-button" type="button" title="查看图片详情" @click="openResult(-1, item)"><img :src="item.image" :alt="item.title" /></button>
              </article>
            </div>
          </div>
          <div class="track-empty" v-else>未匹配到可用于轨迹还原的相似目标。</div>
        </div>
      </aside>
    </div>
    </div>
  </section>
  <image-crop-dialog :open="cropDialogOpen" :item="cropTarget" :action="cropAction" :item-index="cropTargetIndex" @close="closeResultCrop" @confirm="confirmResultCrop"></image-crop-dialog>
  <div v-if="messageDetailSnapshot" class="exact-result-modal-mask" @click.self="closeMessageDetail">
    <section class="exact-result-modal" role="dialog" aria-modal="true" aria-label="分析详情">
      <div class="drawer-head"><h3>分析详情</h3><button class="close" aria-label="关闭" @click="closeMessageDetail">×</button></div>
      <div class="drawer-body exact-message-detail-body">
        <p class="exact-message-detail-query">检索内容：{{ messageDetailSnapshot.query || '-' }}</p>
        <div v-if="messageDetailSnapshot.events.length" class="exact-message-detail-events">
          <article v-for="event in messageDetailSnapshot.events" :key="event.name + event.time" class="exact-message-detail-event">
            <img :src="event.image" :alt="event.name" />
            <div><h4>{{ event.time }} {{ event.name }}</h4><p>{{ event.detail }}</p></div>
          </article>
        </div>
        <dl class="detail-list" style="margin-top:12px;">
          <dt>分析结论</dt><dd>{{ messageDetailSnapshot.answer }}</dd>
          <dt>事件分段</dt><dd>共 {{ messageDetailSnapshot.events.length }} 个</dd>
          <dt>涉及人员</dt><dd>{{ messageDetailSnapshot.summary.persons.join('；') || '无' }}</dd>
          <dt>涉及车辆</dt><dd>{{ messageDetailSnapshot.summary.vehicles.join('；') || '无' }}</dd>
          <template v-for="result in messageDetailSnapshot.results" :key="result.title"><dt>{{ result.title }}</dt><dd>{{ result.value }}。{{ result.detail }}</dd></template>
        </dl>
      </div>
    </section>
  </div>
  <div v-if="searching || analyzing || uploadingVideo || preparingRecording" class="search-loading-mask" @click.stop><div class="search-loading-box"><span class="search-loading-spinner"></span><p>{{ uploadingVideo ? '正在上传视频到分析服务，请稍候...' : (analyzing ? '正在分析视频，请稍候...' : (preparingRecording ? '正在从 NVR 导出录像，时长较长时请耐心等待...' : '正在搜索回放，请稍候...')) }}</p></div></div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import ImageCropDialog from "../components/ImageCropDialog.vue";
import ImageResults from "../components/ImageResults.vue";
import DateTimeRangePicker from "../components/DateTimeRangePicker.vue";
import VideoPlayer from "../components/VideoPlayer.vue";
import { api, assetUrl, videoAnalysisFrameUrl } from "../api";
import type { PersonSearchBboxPoint, SimilarPersonResult } from "../api";
import type { DeploymentTaskCreate } from "../types";
import { cropImageToFile, cropToPixelBbox } from "../utils/person-search";
import type { ImageCropSelection } from "../utils/person-search";

function statusLabel(status?: string): string {
  const value = (status || "").toUpperCase();
  if (value === "RUNNING") return "在线";
  if (value === "STOPPED") return "离线";
  if (value === "DISABLED") return "停用";
  return "未成功连接";
}

function isHttpUrl(url?: string | null): boolean {
  return !!url && /^https?:\/\//i.test(url);
}

// FLV/HLS/MJPEG 流地址不能作为分析接口的视频文件地址
function isStreamUrl(url: string): boolean {
  return /\.(flv|m3u8|mjpeg)(\?|#|$)/i.test(url);
}

// <video> 可直接播放的文件格式
function isPlayableFileUrl(url: string): boolean {
  return /\.(mp4|mov|m4v|webm)(\?|#|$)/i.test(url);
}

// 摄像头可分析视频地址：回放地址优先，其次源地址；均为流地址时返回空
function analysisUrlFor(camera: any): string {
  if (camera && isHttpUrl(camera.playbackUrl) && !isStreamUrl(camera.playbackUrl)) return camera.playbackUrl;
  if (camera && isHttpUrl(camera.sourceUrl) && !isStreamUrl(camera.sourceUrl)) return camera.sourceUrl;
  return "";
}

const ANALYSIS_TEXT_KEYS = ["result", "text", "analysis", "summary", "answer", "content", "description"];
const EVENT_TIME_KEYS = ["start_time", "start", "time", "timestamp", "begin_time", "begin"];
const EVENT_DESC_KEYS = ["description", "content", "summary", "text", "result", "detail"];
const EVENT_NAME_KEYS = ["title", "name", "event", "label", "type"];

// 宽容提取响应中的文本结论：先查当前层已知字段，再递归嵌套对象，最后兜底 message
function findAnalysisText(node: any, depth = 0): string {
  if (node === null || node === undefined || depth > 4) return "";
  if (typeof node === "string") return node.trim();
  if (Array.isArray(node)) {
    for (const item of node) {
      const found = findAnalysisText(item, depth + 1);
      if (found) return found;
    }
    return "";
  }
  if (typeof node === "object") {
    for (const key of ANALYSIS_TEXT_KEYS) {
      const value = node[key];
      if (typeof value === "string" && value.trim()) return value.trim();
    }
    for (const value of Object.values(node)) {
      if (value && typeof value === "object") {
        const found = findAnalysisText(value, depth + 1);
        if (found) return found;
      }
    }
    if (typeof node.message === "string" && node.message.trim()) return node.message.trim();
  }
  return "";
}

function looksLikeEvent(item: any): boolean {
  if (!item || typeof item !== "object" || Array.isArray(item)) return false;
  return EVENT_TIME_KEYS.some(key => key in item) || EVENT_DESC_KEYS.some(key => key in item);
}

// 在响应里找第一个"像事件列表"的数组（元素含时间/描述字段，或纯字符串分段）
function findAnalysisEvents(node: any, depth = 0): any[] {
  if (node === null || node === undefined || depth > 4) return [];
  if (Array.isArray(node)) {
    if (node.length && node.every(item => typeof item === "string")) return node;
    if (node.some(looksLikeEvent)) return node;
    for (const item of node) {
      const found = findAnalysisEvents(item, depth + 1);
      if (found.length) return found;
    }
    return [];
  }
  if (typeof node === "object") {
    for (const value of Object.values(node)) {
      const found = findAnalysisEvents(value, depth + 1);
      if (found.length) return found;
    }
  }
  return [];
}

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

// 录像接口时间与 datetime-local 输入均按本地时区解析："YYYY-MM-DD HH:mm:ss" / "YYYY-MM-DDTHH:mm" -> epoch ms
function parseLocalMs(value?: string): number {
  const ms = value ? new Date(String(value).trim().replace(" ", "T")).getTime() : NaN;
  return Number.isNaN(ms) ? 0 : ms;
}

// epoch ms -> "YYYY-MM-DD HH:mm:ss"（与 getRecordingFileUrl/startRecordingStream 入参格式一致）
function toLocalDateTimeSeconds(ms: number): string {
  const date = new Date(ms);
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())} ${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}`;
}

// MinIO 视频分析服务实际响应：{ code, segments: [{ segment_index, segment_start_seconds, raw_text, result }] }
// 优先按分段生成事件卡片与结论文本；无分段时返回空，交由通用解析兜底
function mapAnalysisSegments(response: any, images: string[]) {
  const list = response && Array.isArray(response.segments) ? response.segments : [];
  const events: any[] = [];
  const texts: string[] = [];
  list.forEach((segment: any, index: number) => {
    if (!segment || typeof segment !== "object") return;
    const start = clockToSeconds(segment.segment_start_seconds ?? index * 60);
    const raw = typeof segment.raw_text === "string" ? segment.raw_text.trim() : "";
    const text = raw || findAnalysisText(segment.result);
    if (text) texts.push(text);
    events.push({
      name: `分段 ${index + 1}`,
      time: formatHms(start),
      start,
      image: images[index % images.length],
      detail: text || "该分段无详细描述"
    });
  });
  return { events, texts };
}

// 上游分析服务以 HTTP 200 包裹业务错误（code>=400 + error/message），需识别为失败
function findAnalysisError(node: any): string {
  if (!node || typeof node !== "object" || Array.isArray(node)) return "";
  const code = Number(node.code);
  if (!Number.isFinite(code) || code < 400) return "";
  const detail = node.error || node.message;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  return `分析服务返回错误码 ${code}`;
}

function formatHms(seconds: number): string {
  const value = Math.max(0, Math.floor(seconds));
  return `${pad2(Math.floor(value / 3600))}:${pad2(Math.floor((value % 3600) / 60))}:${pad2(value % 60)}`;
}

// 数字按秒偏移处理；"HH:mm:ss"/"mm:ss" 字符串解析为秒
function clockToSeconds(value: any): number {
  if (typeof value === "number" && Number.isFinite(value)) return Math.max(0, Math.floor(value));
  const match = String(value || "").match(/(?:(\d+):)?(\d{1,2}):(\d{1,2})/);
  if (!match) return 0;
  return Number(match[1] || 0) * 3600 + Number(match[2]) * 60 + Number(match[3]);
}

function mapAnalysisEvent(item: any, index: number, images: string[], segmentSeconds: number) {
  const image = images[index % images.length];
  if (typeof item === "string") {
    return { name: `分段 ${index + 1}`, time: formatHms(index * segmentSeconds), start: index * segmentSeconds, image, detail: item };
  }
  const rawTime = EVENT_TIME_KEYS.map(key => item[key]).find(value => value !== undefined && value !== null && value !== "");
  const start = clockToSeconds(rawTime);
  const time = typeof rawTime === "string" && rawTime.trim() ? rawTime.trim() : formatHms(start);
  const desc = EVENT_DESC_KEYS.map(key => item[key]).find(value => typeof value === "string" && value.trim());
  const title = EVENT_NAME_KEYS.map(key => item[key]).find(value => typeof value === "string" && value.trim());
  return { name: title || `事件 ${index + 1}`, time, start, image, detail: desc || title || "该分段无详细描述" };
}

const RESULT_TAB_TITLES: Record<string, string> = {
  imageSearch: "以图搜图",
  quickDeploy: "快速布防",
  track: "轨迹图"
};

const PERSON_SEARCH_POLL_INTERVAL_MS = 1500;
const PERSON_SEARCH_POLL_MAX_ATTEMPTS = 60;

function delay(ms: number) {
  return new Promise(resolve => {
    window.setTimeout(resolve, ms);
  });
}

// "2026-07-12T08:30" -> "2026-07-12 08:30:00" (person-search API format)
function toPersonApiDateTime(value: string): string | undefined {
  if (!value) {
    return undefined;
  }
  const [date, rawTime = "00:00"] = value.split("T");
  const time = rawTime.length === 5 ? `${rawTime}:00` : rawTime;
  return `${date} ${time}`;
}

// create_time (epoch 秒/毫秒或字符串) -> "YYYY-MM-DD HH:mm:ss"
function formatCreateTime(value?: number | string): string {
  let d: Date | null = null;
  if (value !== undefined && value !== null && value !== "") {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      d = new Date(numeric > 10_000_000_000 ? numeric : numeric * 1000);
    } else {
      const parsed = new Date(String(value));
      if (!Number.isNaN(parsed.getTime())) d = parsed;
    }
  }
  if (!d || Number.isNaN(d.getTime())) return value ? String(value) : "未知时间";
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

function personSearchResultPayload(response: any) {
  const payload = response && response.data && response.data.data;
  return (payload && payload.result) || payload || null;
}

// 后端 similar_persons 条目 -> 结果卡片/轨迹条目（与 TrackPage.mapSimilarPerson 同形）
function mapSimilarPerson(result: SimilarPersonResult, index: number) {
  const raw = result.similarity_score;
  const score = raw === undefined || Number.isNaN(Number(raw)) ? 0 : Math.round(Number(raw) <= 1 ? Number(raw) * 100 : Number(raw));
  return {
    title: `相似人员 ${index + 1}`,
    image: assetUrl(result.image_url),
    location: result.camera_locate || result.camera_id || "未知摄像头",
    date: formatCreateTime(result.create_time),
    score,
    desc: result.es_doc_id || ""
  };
}

// 模板中直接使用注入的 openResult；vue-tsc 不会把 inject 键推导到模板 this 上，
// 因此以类型补丁形式合并进 ComponentCustomProperties（运行时 inject 声明保持不变）。
declare module "vue" {
  interface ComponentCustomProperties {
    openResult: (index: number, item?: any) => void;
  }
}

export default defineComponent({
  name: "ExactSearchPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { ImageCropDialog, ImageResults, DateTimeRangePicker, VideoPlayer },
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
    openResult: { from: "openResult", default: (index: number, item?: any) => {} },
  },
  mounted() {
    this.loadCameras();
    this.$nextTick(() => this.applySourceFieldHints());
    document.addEventListener("fullscreenchange", this.syncFullscreenState);
  },
  updated() {
    this.$nextTick(() => this.applySourceFieldHints());
  },
  data() {
    const lastLocalVideo = this.store && this.store.lastLocalVideo ? this.store.lastLocalVideo : {};
    return {
      sourceMode: "online",
      selectedArea: null,
      selectedCamera: null,
      pointDropdownOpen: false,
      expandedAreas: {},
      onlineSearched: false,
      onlineSources: [],
      searching: false,
      preparingRecording: false,
      streamBusy: false,
      pendingStreamOffset: null as number | null,
      analyzing: false,
      onlineStart: "",
      onlineEnd: "",
      localFileName: lastLocalVideo.name || "",
      localFileSize: lastLocalVideo.size || "",
      localVideoUrl: lastLocalVideo.url || "",
      localVideoFile: null as File | null,
      uploadingVideo: false,
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
      analysisSnapshots: [] as any[],
      activeAnalysisId: null as string | null,
      analysisSnapshotCounter: 0,
      messageDetailSnapshot: null as any,
      resultTabs: [] as any[],
      activeResultTab: "summary",
      resultTabSeq: 0,
      deployAlgorithmOptions: [] as any[],
      quickQuestions: ["这段视频发生了什么？", "车辆的特征是什么？", "按时间梳理事件", "是否需要布控？"],
      lastQuery: "",
      selectedEventIndex: 0,
      currentTime: 0,
      playerDuration: 3600,
      playerPlaying: false,
      playerFullscreen: false,
      playbackRate: 1,
      playTimer: null,
      areas: [],
      events: [],
      results: [],
      summary: {
        overview: "",
        persons: [],
        vehicles: []
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
    activeResultTabObj(): any {
      return this.resultTabs.find(item => item.id === this.activeResultTab) || null;
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
    // 真实监控点树：按设备 area 顶层分段聚合，失败时显示错误，不回退到示例点位
    async loadCameras() {
      try {
        const cameras = await api.cameras();
        const grouped: Record<string, any[]> = {};
        (cameras || []).forEach((cam: any) => {
          const areaName = (String(cam.area || "").split("/")[0] || "").trim() || "未分配";
          if (!grouped[areaName]) grouped[areaName] = [];
          grouped[areaName].push({
            name: cam.name,
            code: cam.id,
            type: cam.protocol || cam.streamApp || "IPC",
            status: statusLabel(cam.status),
            image: (this as any).store.img.car,
            playbackUrl: cam.playbackUrl,
            sourceUrl: cam.sourceUrl,
            nvrTrackId: cam.nvrTrackId
          });
        });
        const areas = Object.keys(grouped).map(name => ({ name, count: grouped[name].length, cameras: grouped[name] }));
        if (!areas.length) return;
        this.areas = areas as any;
        const expanded: Record<string, boolean> = {};
        areas.forEach((area, index) => { expanded[area.name] = index === 0; });
        this.expandedAreas = expanded;
      } catch (error) {
        this.areas = [];
        this.expandedAreas = {};
        const message = error instanceof Error ? error.message : "监控点加载失败";
        this.showToast(`监控点加载失败：${message}`);
      }
    },
    // 由开始/结束时间估算最大分段数（60 秒一段，clamp 1-20，解析不出取 1）
    estimateMaxSegments() {
      const parse = (value: string) => {
        const text = String(value || "").trim().replace("T", " ");
        if (!text) return null;
        const normalized = text.length === 16 ? `${text}:00` : text;
        const time = new Date(normalized.replace(" ", "T")).getTime();
        return Number.isNaN(time) ? null : time;
      };
      const start = parse(this.onlineStart);
      const end = parse(this.onlineEnd);
      if (start === null || end === null || end <= start) return 1;
      return Math.min(20, Math.max(1, Math.ceil((end - start) / 60000)));
    },
    applySourceFieldHints() {
      const root = this.$el as any;
      const page = root && typeof root.querySelectorAll === 'function'
        ? root
        : (root && root.nextElementSibling ? root.nextElementSibling : document.querySelector('.exact-page'));
      if (!page) return;
      (page.querySelectorAll('.exact-source-form .deploy-field > label') as NodeListOf<HTMLElement>).forEach((label) => { label.hidden = true; });
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
    async searchOnlineSources() {
      if (!this.selectedArea || !this.selectedCamera) {
        this.showToast("请先选择区域和监控点位");
        return;
      }
      if (this.searching) return;
      const selectedCamera = this.selectedCamera as any;
      const analysisUrl = analysisUrlFor(selectedCamera);
      let streamUrl = "";
      let recordingParams = null as any;
      let durationSeconds = 200;
      if (!analysisUrl) {
        // 摄像头只有流地址（flv/rtsp）时：先起 NVR 回放流即时播放（与录像回放页一致），
        // 录像 MP4 的导出推迟到首个视频问答提示词发送时再进行
        if (!selectedCamera.nvrTrackId) {
          this.showToast("该点位暂无可分析的视频文件地址");
          return;
        }
        if (!this.onlineStart.trim() || !this.onlineEnd.trim()) {
          this.showToast("请先填写开始时间和结束时间");
          return;
        }
        const startTime = this.onlineStart.trim().replace("T", " ");
        const endTime = this.onlineEnd.trim().replace("T", " ");
        const startMs = parseLocalMs(startTime);
        const endMs = parseLocalMs(endTime);
        if (!startMs || !endMs || endMs <= startMs) {
          this.showToast("开始时间必须早于结束时间");
          return;
        }
        durationSeconds = Math.max(1, Math.round((endMs - startMs) / 1000));
        this.searching = true;
        try {
          const stream = await api.startRecordingStream({
            cameraId: selectedCamera.code,
            startTime,
            endTime,
            speed: 1
          });
          streamUrl = stream.url || "";
        } catch (error: any) {
          this.searching = false;
          this.showToast(`回放流启动失败：${(error && error.message) || "请稍后重试"}`);
          return;
        }
        if (!streamUrl) {
          this.searching = false;
          this.showToast("该时段未获取到回放流地址");
          return;
        }
        recordingParams = { cameraId: selectedCamera.code, startTime, endTime };
      }
      this.searching = true;
      window.setTimeout(() => {
        this.searching = false;
        this.onlineSearched = true;
        const selectedArea = this.selectedArea as any;
        const source = {
          id: "SRC-" + selectedCamera.code,
          name: selectedCamera.name + " · 监控回放",
          camera: selectedCamera.code,
          cameraName: selectedCamera.name,
          areaName: selectedArea.name,
          time: this.onlineStart + " - " + this.onlineEnd,
          clipTime: this.onlineStart + " - " + this.onlineEnd,
          duration: "03:20",
          durationSeconds,
          image: selectedCamera.image,
          sourceType: "在线监控",
          analysisUrl,
          videoUrl: isPlayableFileUrl(analysisUrl) ? analysisUrl : undefined,
          streamUrl: streamUrl || undefined,
          recordingParams
        };
        this.onlineSources = [source];
        if (this.sourceConfirmed) {
          this.applyOnlineSource(source);
          this.showToast("已切换录像回放，下方结果已更新");
        } else {
          this.useOnlineSource(source);
          this.showToast("已找到该监控点回放画面");
        }
      }, 600);
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
      if ((source as any).streamUrl) {
        // 流模式：VideoPlayer 自动起播，进度用墙钟 × 倍速模拟
        this.playerPlaying = true;
        this.startPlayTimer();
      }
    },
    // 无原生 <video> 时的进度模拟：每秒按倍速推进，到顶停止
    startPlayTimer() {
      if (this.playTimer) window.clearInterval(this.playTimer);
      this.playTimer = window.setInterval(() => {
        this.currentTime += this.playbackRate;
        if (this.currentTime >= this.playerDuration) {
          this.currentTime = this.playerDuration;
          this.stopSimulation();
        }
      }, 1000);
    },
    // 流模式（NVR 推送流无法原生 seek）：定位/倍速 = 以「开始时间 + 偏移」为新起点重新起流。
    // 拖动进度条会连续触发：起流期间只记录最新目标位置，完成后补一次，避免打满 NVR
    async restartStreamAt(offsetSeconds) {
      const selectedSource = this.selectedSource as any;
      const params = selectedSource && selectedSource.recordingParams;
      if (!params || !selectedSource.streamUrl) return;
      const offset = Math.max(0, Math.min(Math.max(this.playerDuration - 1, 0), Math.round(offsetSeconds)));
      this.currentTime = offset;
      if (this.streamBusy) {
        this.pendingStreamOffset = offset;
        return;
      }
      const startMs = parseLocalMs(params.startTime) + offset * 1000;
      this.streamBusy = true;
      try {
        const result = await api.startRecordingStream({
          cameraId: params.cameraId,
          startTime: toLocalDateTimeSeconds(startMs),
          endTime: params.endTime,
          speed: Number(this.playbackRate)
        });
        this.currentTime = offset;
        this.playerPlaying = true;
        this.startPlayTimer();
        if (selectedSource.streamUrl === result.url) {
          // URL 相同不会触发 VideoPlayer 的 watch，先卸载再在下一帧重建流
          selectedSource.streamUrl = undefined;
          this.$nextTick(() => {
            if (this.selectedSource === selectedSource) selectedSource.streamUrl = result.url;
          });
        } else {
          selectedSource.streamUrl = result.url;
        }
      } catch (error) {
        this.showToast(`回放流启动失败：${error instanceof Error ? error.message : error}`);
      } finally {
        this.streamBusy = false;
        if (this.pendingStreamOffset !== null) {
          const pending = this.pendingStreamOffset;
          this.pendingStreamOffset = null;
          this.restartStreamAt(pending);
        }
      }
    },
    seedQuestionMessages() {
      this.questionMessages = [{
        role: "assistant",
        text: `已连接${this.videoViewLabel}：${this.selectedSource ? (this.selectedSource as any).name : "当前视频源"}。完成文搜后可继续提问，我会结合当前回放时间和事件结果回答。`
      }];
      this.questionInput = "";
      this.questionBusy = false;
      // 切换视频源后清空分析快照与右侧动态页签（各页签的轮询随页签移除而作废）
      this.analysisSnapshots = [];
      this.activeAnalysisId = null;
      this.analysisSnapshotCounter = 0;
      this.messageDetailSnapshot = null;
      this.resultTabs = [];
      this.activeResultTab = "summary";
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
      this.localVideoFile = file;
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
      this.localVideoFile = null;
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
      this.onlineStart = "2026-07-24T09:00";
      this.onlineEnd = "2026-07-24T10:00";
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
    async startAnalysis() {
      if (!this.selectedSource) {
        this.showToast("请先确定视频源");
        return;
      }
      const selectedSource = this.selectedSource as any;
      if (!this.query.trim()) {
        this.showToast("请输入需要检索的内容");
        return;
      }
      if (this.analyzing || this.uploadingVideo || this.preparingRecording) return;
      // 本地视频：首次分析前上传到 MinIO，换取分析服务可拉取的 videoUrl
      if (selectedSource.sourceType === "本地上传" && !selectedSource.analysisUrl) {
        if (!this.localVideoFile) {
          this.showToast("请重新上传本地视频");
          return;
        }
        this.uploadingVideo = true;
        try {
          const uploaded = await api.uploadAnalysisVideo(this.localVideoFile);
          selectedSource.analysisUrl = uploaded.videoUrl;
        } catch (error) {
          this.showToast(error instanceof Error ? error.message : "视频上传失败");
          return;
        } finally {
          this.uploadingVideo = false;
        }
      }
      // 在线监控仅有流地址时：首个问答提示词发出后才从 NVR 导出录像 MP4，
      // 导出成功后播放器切换为该文件；后续对话复用同一 analysisUrl，不再重复导出
      if (selectedSource.sourceType === "在线监控" && !selectedSource.analysisUrl && selectedSource.recordingParams) {
        this.preparingRecording = true;
        try {
          const exported = await api.getRecordingFileUrl(selectedSource.recordingParams);
          selectedSource.analysisUrl = exported.videoUrl || "";
          if (exported.videoUrl && isPlayableFileUrl(exported.videoUrl)) {
            this.stopSimulation();
            selectedSource.streamUrl = undefined;
            selectedSource.videoUrl = exported.videoUrl;
            this.currentTime = 0;
            if (exported.durationSeconds) this.playerDuration = exported.durationSeconds;
          }
        } catch (error: any) {
          this.showToast(`录像导出失败：${(error && error.message) || "请稍后重试"}`);
          return;
        } finally {
          this.preparingRecording = false;
        }
      }
      if (!selectedSource.analysisUrl) {
        this.showToast("当前视频源不可分析，请重新搜索回放");
        return;
      }
      const question = this.query.trim();
      this.lastQuery = question;
      this.questionMessages.push({ role: "user", text: question });
      this.analyzing = true;
      this.questionBusy = true;
      try {
        const response = await api.analyzeMinioVideo({
          videoUrl: selectedSource.analysisUrl,
          prompt: question,
          fps: 1,
          segmentSeconds: 60,
          maxSegments: selectedSource.sourceType === "本地上传"
            ? Math.min(20, Math.max(1, Math.ceil((selectedSource.durationSeconds || 60) / 60)))
            : this.estimateMaxSegments(),
          height: 480
        });
        const img = (this as any).store.img;
        const images = [img.portrait, img.car, img.target];
        const segments = mapAnalysisSegments(response, images);
        const overview = segments.texts.length ? segments.texts.join("\n\n") : findAnalysisText(response);
        const upstreamError = findAnalysisError(response);
        if (upstreamError || (!overview && !segments.events.length && !findAnalysisEvents(response).length)) {
          const message = upstreamError || "接口未返回有效分析结果，请检查视频分析服务后重试";
          this.questionMessages.push({ role: "assistant", text: `分析失败：${message}` });
          this.showToast(`分析失败：${message}`);
          return;
        }
        this.events = (segments.events.length
          ? segments.events
          : findAnalysisEvents(response).map((item, index) => mapAnalysisEvent(item, index, images, 60))) as any;
        this.applyEventFrameImages(this.events, selectedSource.analysisUrl);
        this.summary = { overview, persons: [], vehicles: [] };
        this.results = [];
        this.analyzed = true;
        this.selectedEventIndex = 0;
        if (this.events.length) {
          this.currentTime = (this.events[0] as any).start;
          this.seekVideo(this.currentTime);
        }
        const answerText = `已完成视频源文搜。\n\n事件摘要：${overview}\n\n已识别 ${this.events.length} 个关键事件，右侧可查看事件摘要、分析结果，并继续对视频提问。`;
        const snapshot = this.saveAnalysisSnapshot(answerText, question);
        this.questionMessages.push({ role: "assistant", text: answerText, analysisId: snapshot.id });
        this.activeAnalysisId = snapshot.id;
        this.query = "";
        this.showToast("文搜分析完成，已生成事件结论");
      } catch (error) {
        const message = error instanceof Error ? error.message : "视频分析失败";
        this.questionMessages.push({ role: "assistant", text: `分析失败：${message}` });
        this.showToast(message);
      } finally {
        this.analyzing = false;
        this.questionBusy = false;
      }
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
      const video = this.$refs.exactVideo as HTMLVideoElement;
      if (video) {
        this.currentTime = next;
        video.currentTime = next;
        return;
      }
      const selectedSource = this.selectedSource as any;
      if (selectedSource && selectedSource.streamUrl) {
        // 流模式：拖动进度 = 以新起点重新起流
        this.restartStreamAt(next);
        return;
      }
      this.currentTime = next;
    },
    // 播放器全屏：对整个播放器容器（含控制条）调用 Fullscreen API
    togglePlayerFullscreen() {
      const panel = this.$refs.exactPlayer as HTMLElement;
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else if (panel && panel.requestFullscreen) {
        panel.requestFullscreen();
      }
    },
    syncFullscreenState() {
      this.playerFullscreen = !!document.fullscreenElement;
    },
    togglePlay() {
      const video = this.$refs.exactVideo as HTMLVideoElement;
      if (video) {        if (video.paused) {
          video.playbackRate = this.playbackRate;
          video.play();
          this.playerPlaying = true;
        } else {
          video.pause();
          this.playerPlaying = false;
        }
        return;
      }
      const selectedSource = this.selectedSource as any;
      if (selectedSource && selectedSource.streamUrl) {
        // 流模式：暂停即停流（进度停留）；连续推送流无法续播，从当前位置重新起流
        if (this.playerPlaying) {
          this.stopSimulation();
          return;
        }
        if (this.currentTime >= this.playerDuration) this.currentTime = 0;
        this.restartStreamAt(this.currentTime);
        return;
      }
      if (this.playerPlaying) this.stopSimulation();
      else {
        this.playerPlaying = true;
        this.startPlayTimer();
      }
    },
    stopSimulation() {
      if (this.playTimer) window.clearInterval(this.playTimer);
      this.playTimer = null;
      this.playerPlaying = false;
      this.pendingStreamOffset = null;
      const video = this.$refs.exactVideo as HTMLVideoElement;
      if (video && !video.paused) video.pause();
      const streamPlayer = this.$refs.exactStreamPlayer as any;
      if (streamPlayer && streamPlayer.stop) streamPlayer.stop();
    },
    changePlaybackRate() {
      const video = this.$refs.exactVideo as HTMLVideoElement;
      if (video) {
        video.playbackRate = this.playbackRate;
        return;
      }
      const selectedSource = this.selectedSource as any;
      if (selectedSource && selectedSource.streamUrl && this.playerPlaying) {
        // 流模式：倍速随重新起流生效
        this.restartStreamAt(this.currentTime);
      }
    },
    selectEvent(index) {
      const event = this.events[index];
      if (!event) return;
      this.selectedEventIndex = index;
      this.seekVideo(event.start);
      this.showToast(`已定位到 ${event.time} 事件画面`);
    },
    // 分析结果事件卡片用真实截图：按事件起点从视频文件截帧；失败时回退到原占位图
    applyEventFrameImages(events, videoUrl) {
      (events as any[]).forEach(event => {
        if (!event.fallbackImage) event.fallbackImage = event.image;
        const frameUrl = videoAnalysisFrameUrl(videoUrl, event.start);
        if (frameUrl) event.image = frameUrl;
      });
    },
    onEventImageError(event) {
      if (event.fallbackImage && event.image !== event.fallbackImage) event.image = event.fallbackImage;
    },
    async askVideoQuestion(text) {
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
      const selectedSource = this.selectedSource as any;
      if (!selectedSource.analysisUrl) {
        this.showToast("当前视频源不可分析，请重新搜索回放");
        return;
      }
      this.questionMessages.push({ role: "user", text: question });
      this.query = "";
      this.questionInput = "";
      this.questionBusy = true;
      try {
        // 追问同样走视频分析接口：以问题为 prompt 重新分析当前视频源
        const response = await api.analyzeMinioVideo({
          videoUrl: selectedSource.analysisUrl,
          prompt: question,
          fps: 1,
          segmentSeconds: 60,
          maxSegments: selectedSource.sourceType === "本地上传"
            ? Math.min(20, Math.max(1, Math.ceil((selectedSource.durationSeconds || 60) / 60)))
            : this.estimateMaxSegments(),
          height: 480
        });
        const img = (this as any).store.img;
        const images = [img.portrait, img.car, img.target];
        const segments = mapAnalysisSegments(response, images);
        const answer = segments.texts.length ? segments.texts.join("\n\n") : findAnalysisText(response);
        const upstreamError = findAnalysisError(response);
        if (upstreamError || (!answer && !segments.events.length && !findAnalysisEvents(response).length)) {
          const message = upstreamError || "接口未返回有效分析结果，请检查视频分析服务后重试";
          this.questionMessages.push({ role: "assistant", text: `分析失败：${message}` });
          this.showToast(`分析失败：${message}`);
          return;
        }
        const parsedEvents = segments.events.length
          ? segments.events
          : findAnalysisEvents(response).map((item, index) => mapAnalysisEvent(item, index, images, 60));
        if (parsedEvents.length) {
          this.applyEventFrameImages(parsedEvents, selectedSource.analysisUrl);
          this.events = parsedEvents as any;
          this.selectedEventIndex = 0;
          this.currentTime = (this.events[0] as any).start;
          this.seekVideo(this.currentTime);
        }
        this.summary = { overview: answer, persons: [], vehicles: [] };
        this.results = [];
        const snapshot = this.saveAnalysisSnapshot(answer, question);
        this.questionMessages.push({ role: "assistant", text: answer, analysisId: snapshot.id });
        this.activeAnalysisId = snapshot.id;
      } catch (error) {
        const message = error instanceof Error ? error.message : "视频分析失败";
        this.questionMessages.push({ role: "assistant", text: `分析失败：${message}` });
        this.showToast(message);
      } finally {
        this.questionBusy = false;
      }
    },
    openResultCrop(action, event, index) {
      this.cropAction = action;
      this.cropTarget = {
        ...event,
        title: event.name || event.title,
        date: event.date || (event.time ? `2026-07-24 ${event.time}` : "")
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
      const crop = selection ? { ...selection, sourceName: item.title, sourceTime: item.date, sourceIndex: index } : null;
      this.closeResultCrop();
      // 裁图确认后不再跨页跳转，改为在右侧栏打开对应的页内 tab
      if (action === "imageSearch" || action === "quickDeploy" || action === "track") {
        this.openResultTab(action, { image: item.image, crop, sourceName: item.title });
      }
    },
    // 页签默认值：以图搜图/轨迹图带检索表单状态，快速布防带布控表单与已存任务
    resultTabDefaults(type) {
      if (type === "imageSearch") {
        return { items: [] as any[], loading: false, runId: 0, fileName: "", start: this.onlineStart || "", end: this.onlineEnd || "", place: "全部区域", similarity: 50 };
      }
      if (type === "quickDeploy") {
        return { savedTask: null, deployTaskName: "", deployAlgorithmId: "", deployCameraSelections: [] as string[], deployAreaOpen: false, deployAreaExpanded: {} as Record<string, boolean>, deployEffectiveStart: "", deployEffectiveEnd: "", deployCycleStart: "00:00", deployCycleEnd: "23:59", deploySimilarity: 50, deployDescription: "", deploySaving: false };
      }
      const expandedAreas: Record<string, boolean> = {};
      (this.areas as any[]).forEach((area, index) => { expandedAreas[area.name] = index === 0; });
      return { items: [] as any[], loading: false, runId: 0, fileName: "", start: "", end: "", threshold: 50, searchArea: null, searchCamera: null, pointDropdownOpen: false, expandedAreas };
    },
    // 同类页签可开多个，标题按类型编号（参照原型 openAnalysisTab）
    openResultTab(type, payload) {
      this.resultTabSeq += 1;
      const tab: any = { id: `result-tab-${this.resultTabSeq}`, type, title: RESULT_TAB_TITLES[type] || type, payload, ...this.resultTabDefaults(type) };
      const count = this.resultTabs.filter(item => item.type === type).length;
      if (count) tab.title = `${tab.title} ${count + 1}`;
      if (type === "quickDeploy" && payload && payload.sourceName) tab.deployTaskName = `布控-${payload.sourceName}`;
      this.resultTabs.push(tab);
      this.activeResultTab = tab.id;
      if (type === "imageSearch") this.runImageSearchTab(tab);
      else if (type === "quickDeploy") this.prepareQuickDeployTab();
      else if (type === "track") this.runTrackSearch(tab);
    },
    closeResultTab(id) {
      this.resultTabs = this.resultTabs.filter(tab => tab.id !== id);
      if (this.activeResultTab === id) this.activeResultTab = "summary";
    },
    // 页签内轮询的作废判定：页签被关闭，或被同页签发起的新检索顶掉
    isTabRunStale(tab, runId) {
      return !this.resultTabs.includes(tab) || tab.runId !== runId;
    },
    cropStyleOf(crop) {
      const value = crop || { x: 0, y: 0, width: 0, height: 0 };
      return {
        left: `${value.x}%`,
        top: `${value.y}%`,
        width: `${value.width}%`,
        height: `${value.height}%`
      };
    },
    // 本地裁剪框选区域并上传为检索图；失败时退回原图 URL + 像素 bbox 模式
    async preparePersonSearchTarget(image: string, crop: ImageCropSelection | null): Promise<{ imageUrl: string; bbox?: PersonSearchBboxPoint[] }> {
      if (crop) {
        try {
          const file = await cropImageToFile(image, crop, "exact-target.jpg");
          const uploaded = await api.uploadPersonSearchImage(file);
          return { imageUrl: uploaded.imageUrl };
        } catch {
          const bbox = await cropToPixelBbox(image, crop);
          if (bbox) return { imageUrl: image, bbox };
        }
      }
      return { imageUrl: image };
    },
    // 以图搜图/轨迹图共用的行人检索流程：提交任务并轮询结果（参照 TrackPage.runCandidateSearch）；
    // stale() 返回 true 表示页签已关闭或任务已被取代，返回 null
    async runPersonSearch(image: string, crop: ImageCropSelection | null, stale: () => boolean, options: { startTime?: string; endTime?: string; threshold?: number } = {}): Promise<SimilarPersonResult[] | null> {
      const target = await this.preparePersonSearchTarget(image, crop);
      if (stale()) return null;
      let bbox = target.bbox;
      if (!bbox) {
        const detectResponse = await api.detectPersons(target.imageUrl);
        if (stale()) return null;
        const detected = detectResponse.data?.detected_persons ?? [];
        if (detectResponse.data?.status !== "success" || !detected.length) {
          throw new Error(detectResponse.data?.message || "未检测到目标，请调整框选区域后重试");
        }
        bbox = detected[0]?.bbox;
      }
      const submitResponse = await api.searchPersonByBbox({
        imageUrl: target.imageUrl,
        bbox,
        searchMethod: "reid",
        startTime: toPersonApiDateTime(options.startTime || ""),
        endTime: toPersonApiDateTime(options.endTime || ""),
        similarityThreshold: (options.threshold ?? 50) / 100,
        topK: 50
      });
      if (stale()) return null;
      const taskId = submitResponse.data?.task_id ?? submitResponse.data?.data?.task_id;
      if (!taskId) throw new Error(submitResponse.data?.message || "搜索任务提交失败");
      for (let attempt = 0; attempt < PERSON_SEARCH_POLL_MAX_ATTEMPTS; attempt += 1) {
        if (stale()) return null;
        const response = await api.personSearchResult(taskId);
        if (stale()) return null;
        const taskStatus = response.data?.status;
        if (taskStatus === "success") {
          const resultPayload = personSearchResultPayload(response);
          return (resultPayload && resultPayload.similar_persons) || [];
        }
        if (taskStatus === "error") throw new Error(response.data?.message || "搜索任务失败");
        await delay(PERSON_SEARCH_POLL_INTERVAL_MS);
      }
      throw new Error("搜索任务超时，请稍后重试");
    },
    // 按区域客户端过滤检索结果：camera_id/camera_locate 匹配该区域下摄像机
    filterPersonsByArea(persons, areaName) {
      if (!areaName || areaName === "全部区域") return persons;
      const area = (this.areas as any[]).find(item => item.name === areaName);
      if (!area) return persons;
      const tokens: string[] = [];
      area.cameras.forEach((camera: any) => { tokens.push(camera.code, camera.name); });
      return (persons as any[]).filter(person => tokens.includes(person.camera_id) || tokens.includes(person.camera_locate));
    },
    async runImageSearchTab(tab) {
      if (!tab || !tab.payload || !tab.payload.image) {
        this.showToast("请先上传参考图片");
        return;
      }
      const runId = ++tab.runId;
      const stale = () => this.isTabRunStale(tab, runId);
      tab.loading = true;
      tab.items = [];
      try {
        let persons = await this.runPersonSearch(tab.payload.image, tab.payload.crop, stale, { startTime: tab.start, endTime: tab.end, threshold: tab.similarity });
        if (persons === null || stale()) return;
        persons = this.filterPersonsByArea(persons, tab.place);
        tab.items = persons.map((person, index) => mapSimilarPerson(person, index));
        this.showToast(tab.items.length ? `找到 ${tab.items.length} 条相似结果` : "未找到相似目标");
      } catch (error) {
        if (stale()) return;
        this.showToast(error instanceof Error ? error.message : "以图搜图失败");
      } finally {
        if (!stale()) tab.loading = false;
      }
    },
    triggerImageSearchUpload() {
      const input = this.$refs.exactImageSearchInput as HTMLInputElement;
      if (input) input.click();
    },
    triggerTrackTargetUpload() {
      const input = this.$refs.exactTrackTargetInput as HTMLInputElement;
      if (input) input.click();
    },
    // 页签内替换参考图/目标图：上传到检索服务，清掉原框选（参照原型 handleImageSearchUpload）
    async handleResultTabImageUpload(event, expectedType) {
      const input = event.target as HTMLInputElement;
      const file = input && input.files && input.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        this.showToast("请选择图片文件");
        return;
      }
      const tab = this.activeResultTabObj;
      if (!tab || tab.type !== expectedType) return;
      try {
        const uploaded = await api.uploadPersonSearchImage(file);
        tab.payload = { ...tab.payload, image: assetUrl(uploaded.imageUrl), crop: null };
        tab.fileName = file.name;
        this.showToast(expectedType === "track" ? "目标图片已载入" : "参考图已载入，请设置筛选条件后搜索");
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "图片上传失败");
      } finally {
        if (input) input.value = "";
      }
    },
    handleImageSearchUpload(event) {
      this.handleResultTabImageUpload(event, "imageSearch");
    },
    handleTrackTargetUpload(event) {
      this.handleResultTabImageUpload(event, "track");
    },
    // 以图搜图结果卡片上的三个动作：把检索结果规整为事件结构后走同一套裁图流转
    onImageSearchAction(payload) {
      const item = payload && payload.item;
      if (!item || !payload.action) return;
      this.openResultCrop(payload.action, {
        name: item.title,
        title: item.title,
        time: item.date ? item.date.slice(11, 19) : "",
        start: 0,
        image: item.image,
        detail: item.desc || "",
        date: item.date
      }, -1);
    },
    prepareQuickDeployTab() {
      if (this.deployAlgorithmOptions.length) return;
      api.algorithms().then(list => {
        this.deployAlgorithmOptions = (list || []) as any;
      }).catch(() => {
        this.showToast("算法列表加载失败");
      });
    },
    deployAreaLabel(tab) {
      if (!tab.deployCameraSelections.length) return "请选择布控点位（可多选摄像机）";
      const names: string[] = [];
      (this.areas as any[]).forEach(area => area.cameras.forEach((camera: any) => {
        if (tab.deployCameraSelections.includes(camera.code)) names.push(`${area.name} / ${camera.name}`);
      }));
      return names.length <= 2 ? names.join("、") : `已选 ${names.length} 台摄像机`;
    },
    toggleDeployArea(tab, area) {
      tab.deployAreaExpanded = { ...tab.deployAreaExpanded, [area.name]: !tab.deployAreaExpanded[area.name] };
    },
    toggleDeployCamera(tab, camera) {
      if (tab.deployCameraSelections.includes(camera.code)) {
        tab.deployCameraSelections = tab.deployCameraSelections.filter(code => code !== camera.code);
      } else {
        tab.deployCameraSelections = [...tab.deployCameraSelections, camera.code];
      }
    },
    // 保存布控任务：payload 字段映射参照 App.vue submitDeployTask；成功后页签切换为任务详情视图（参照原型 handleQuickDeploySaved）
    async saveQuickDeploy(tab) {
      if (!tab.deployTaskName.trim()) {
        this.showToast("请输入任务名称");
        return;
      }
      if (!tab.deployCameraSelections.length) {
        this.showToast("请选择布控点位");
        return;
      }
      if (!tab.deployAlgorithmId) {
        this.showToast("请选择布控算法");
        return;
      }
      if (!tab.deployEffectiveStart || !tab.deployEffectiveEnd) {
        this.showToast("请选择生效日期");
        return;
      }
      if (tab.deploySaving) return;
      const algorithm = this.deployAlgorithmOptions.find(item => item.id === tab.deployAlgorithmId);
      const areaNames: string[] = [];
      const pointNames: string[] = [];
      (this.areas as any[]).forEach(area => area.cameras.forEach((camera: any) => {
        if (tab.deployCameraSelections.includes(camera.code)) {
          if (!areaNames.includes(area.name)) areaNames.push(area.name);
          pointNames.push(camera.name);
        }
      }));
      const body: DeploymentTaskCreate = {
        name: tab.deployTaskName.trim(),
        pipeline: algorithm ? algorithm.name : "",
        algorithmId: algorithm ? algorithm.id : null,
        algorithmName: algorithm ? algorithm.name : null,
        algorithmCode: algorithm ? algorithm.code : null,
        engineType: algorithm ? algorithm.engineType : null,
        cameraIds: [...tab.deployCameraSelections],
        desc: tab.deployDescription.trim(),
        area: areaNames.length ? areaNames.join("、") : null,
        areaCount: tab.deployCameraSelections.length
      };
      tab.deploySaving = true;
      try {
        const created = await api.createDeploymentTask(body);
        const now = new Date();
        const createdText = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())} ${pad2(now.getHours())}:${pad2(now.getMinutes())}`;
        const effectiveDates = `${tab.deployEffectiveStart} ~ ${tab.deployEffectiveEnd}`;
        const cycle = `${tab.deployCycleStart}~${tab.deployCycleEnd}`;
        tab.savedTask = {
          id: (created && (created as any).id) || "-",
          name: body.name,
          desc: body.desc || "暂无任务描述",
          algorithm: algorithm ? algorithm.name : "未选择算法",
          status: "运行中",
          area: areaNames.length ? areaNames.join("、") : "全部区域",
          points: pointNames.length ? pointNames.join("、") : "全部点位",
          time: [effectiveDates, cycle].filter(Boolean).join(" "),
          threshold: tab.deploySimilarity,
          owner: (created && (created as any).owner) || "—",
          created: createdText
        };
        this.showToast("布控任务已创建");
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "布控任务保存失败");
      } finally {
        tab.deploySaving = false;
      }
    },
    trackSearchPointLabel(tab) {
      if (!tab) return "请选择区域 / 监控点";
      if (tab.searchArea && tab.searchCamera) return `${tab.searchArea.name} / ${tab.searchCamera.name}`;
      if (tab.searchArea) return `${tab.searchArea.name} / 请选择监控点`;
      return "请选择区域 / 监控点";
    },
    toggleTrackPointDropdown(tab) {
      tab.pointDropdownOpen = !tab.pointDropdownOpen;
    },
    toggleTrackSearchArea(tab, area) {
      if (!tab.searchArea || tab.searchArea.name !== area.name) {
        tab.searchArea = area;
        tab.searchCamera = null;
      }
      tab.expandedAreas = { ...tab.expandedAreas, [area.name]: !tab.expandedAreas[area.name] };
    },
    selectTrackSearchCamera(tab, camera, area) {
      tab.searchArea = area;
      tab.searchCamera = camera;
      tab.pointDropdownOpen = false;
    },
    async runTrackSearch(tab) {
      if (!tab || !tab.payload || !tab.payload.image) {
        this.showToast("请先上传目标参考图");
        return;
      }
      const runId = ++tab.runId;
      const stale = () => this.isTabRunStale(tab, runId);
      tab.loading = true;
      tab.items = [];
      try {
        let persons = await this.runPersonSearch(tab.payload.image, tab.payload.crop, stale, { startTime: tab.start, endTime: tab.end, threshold: tab.threshold });
        if (persons === null || stale()) return;
        // 选中监控点时按 TrackPage.applyTrackResults 同样方式客户端过滤
        if (tab.searchCamera) {
          const { code, name } = tab.searchCamera as any;
          persons = (persons as any[]).filter(person =>
            person.camera_id === code || person.camera_id === name ||
            person.camera_locate === name || person.camera_locate === code
          ) as SimilarPersonResult[];
        }
        tab.items = persons
          .map((person, index) => mapSimilarPerson(person, index))
          .sort((a, b) => a.date.localeCompare(b.date));
        this.showToast(tab.items.length ? "已根据搜索结果生成轨迹图" : "未匹配到可用于轨迹还原的相似目标");
      } catch (error) {
        if (stale()) return;
        this.showToast(error instanceof Error ? error.message : "轨迹搜索任务失败");
      } finally {
        if (!stale()) tab.loading = false;
      }
    },
    trackDurationOf(items): string {
      if (!items || items.length < 2) return "0min";
      const parse = (value: string) => new Date(value.replace(" ", "T")).getTime();
      const first = parse(items[0].date);
      const last = parse(items[items.length - 1].date);
      if (Number.isNaN(first) || Number.isNaN(last) || last < first) return "-";
      const minutes = Math.round((last - first) / 60000);
      const hours = Math.floor(minutes / 60);
      return hours > 0 ? `${hours}h ${minutes % 60}min` : `${minutes}min`;
    },
    trackPointCountOf(items): number {
      return new Set((items || []).map(item => item.location)).size;
    },
    trackConfidenceOf(items): number {
      if (!items || !items.length) return 0;
      const total = items.reduce((sum, item) => sum + (Number(item.score) || 0), 0);
      return Math.round(total / items.length);
    },
    cloneAnalysisData(value) {
      return JSON.parse(JSON.stringify(value));
    },
    // 每轮分析/追问完成后留存快照：摘要、事件列表、选中事件下标的深拷贝
    saveAnalysisSnapshot(answer, query) {
      this.analysisSnapshotCounter += 1;
      const snapshot = {
        id: `analysis-${this.analysisSnapshotCounter}`,
        answer,
        query,
        summary: this.cloneAnalysisData(this.summary),
        events: this.cloneAnalysisData(this.events),
        results: this.cloneAnalysisData(this.results),
        selectedEventIndex: this.selectedEventIndex
      };
      this.analysisSnapshots.push(snapshot);
      return snapshot;
    },
    loadAnalysisSnapshot(snapshotId) {
      const snapshot = this.analysisSnapshots.find(item => item.id === snapshotId);
      if (!snapshot) return;
      this.activeAnalysisId = snapshot.id;
      this.summary = this.cloneAnalysisData(snapshot.summary);
      this.events = this.cloneAnalysisData(snapshot.events);
      this.results = this.cloneAnalysisData(snapshot.results);
      this.lastQuery = snapshot.query || this.lastQuery;
      this.analyzed = true;
      this.activeResultTab = "summary";
      const maxIndex = Math.max(this.events.length - 1, 0);
      this.selectedEventIndex = Math.min(snapshot.selectedEventIndex || 0, maxIndex);
      if (this.events.length) this.selectEvent(this.selectedEventIndex);
    },
    // 以该轮问题重新发起分析（未分析时走首次分析流程）
    rerunMessageAnalysis(message) {
      const snapshot = this.analysisSnapshots.find(item => item.id === message.analysisId);
      const question = snapshot ? snapshot.query : "";
      if (!question || this.questionBusy || this.analyzing) return;
      this.activeQuickPrompt = "";
      this.askVideoQuestion(question);
    },
    openMessageDetail(message) {
      const snapshot = this.analysisSnapshots.find(item => item.id === message.analysisId);
      if (snapshot) this.messageDetailSnapshot = snapshot;
    },
    closeMessageDetail() {
      this.messageDetailSnapshot = null;
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
    document.removeEventListener("fullscreenchange", this.syncFullscreenState);
  }
});
</script>
