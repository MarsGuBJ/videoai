<template>
  <section class="content wide exact-page" @click="handleExactBlankClick">
    <div class="title-row"><div><h1 class="page-title">文搜视频</h1><p class="page-subtitle">通过自然语言描述搜索和分析监控视频片段。</p></div></div>
    <div class="panel exact-source-panel">
      <div class="exact-source-modebar"><div class="exact-mode-tabs" role="tablist"><button class="exact-mode-tab" :class="{ active: sourceMode === 'online' }" role="tab" :aria-selected="sourceMode === 'online'" @click="setSourceMode('online')">在线监控点</button><button class="exact-mode-tab" :class="{ active: sourceMode === 'upload' }" role="tab" :aria-selected="sourceMode === 'upload'" @click="setSourceMode('upload')">上传本地视频</button></div></div>
      <div v-if="sourceMode === 'online'" class="exact-online-pane">
        <div class="exact-source-form" @click.stop>
          <div class="deploy-field"><label>区域 / 监控点</label><div class="exact-tree-select"><button class="exact-tree-trigger" :class="{ open: pointDropdownOpen }" @click="togglePointDropdown"><span>{{ selectedPointLabel }}</span><span>{{ pointDropdownOpen ? '收起' : '展开' }}⌄</span></button><div v-if="pointDropdownOpen" class="exact-tree-dropdown"><div class="exact-tree-search"><input v-model="pointSearchQuery" type="text" placeholder="输入关键字搜索监控点" @click.stop /></div><div v-for="entry in pointAreaEntries" :key="entry.area.name"><button class="exact-tree-area-row" :class="{ active: selectedArea && selectedArea.name === entry.area.name }" @click="toggleArea(entry.area)"><span>{{ expandedAreas[entry.area.name] || pointSearchActive ? '⌄' : '›' }} {{ entry.area.name }}</span><span>{{ entry.cameras.length }} 台设备</span></button><div v-if="expandedAreas[entry.area.name] || pointSearchActive" class="exact-tree-children"><button v-for="camera in entry.cameras" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" @click="selectCamera(camera, entry.area)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button></div></div><div v-if="!pointAreaEntries.length" class="exact-tree-empty">未找到匹配的监控点</div></div></div></div>
          <div class="deploy-field"><date-time-range-picker v-model:start="onlineStart" v-model:end="onlineEnd" @change="markPendingSourceChange" /></div>
          <button class="btn primary" :disabled="searching" @click="searchOnlineSources">⌕ 搜索回放</button>
        </div>
      </div>
      <div v-else class="exact-last-video-panel">
        <input ref="exactVideoInput" class="hidden-file-input" type="file" accept="video/*,.mkv" @change="onFileChange" />
        <div v-if="localFileName" class="exact-last-video-card"><img :src="localVideoPoster || store.img.analyst" alt="已上传本地视频" /><div><div class="exact-last-video-title"><strong>{{ localFileName }}</strong><div class="exact-last-video-meta"><span class="tag blue">已上传</span><span v-if="localFileDuration" class="exact-last-video-duration">时长 {{ localFileDuration }}</span></div></div></div><button class="exact-video-delete-btn" type="button" aria-label="删除已上传视频" title="删除已上传视频" @click.stop="clearLocalVideo"><span aria-hidden="true"></span></button></div>
        <div v-else class="exact-upload-drop" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop"><div><span class="upload-mark">＋</span><strong>点击上传或拖拽视频到此处</strong><span class="hint-text">支持本地视频预览与时间定位</span></div></div>
      </div>
    </div>

    <!-- 与文搜图页一致的占位区域：确认视频源前提示操作路径 -->
    <div v-if="!sourceConfirmed" class="search-empty-state exact-source-empty"><strong>暂无搜索结果</strong><strong>选择在线监控点或上传本地视频后，点击「搜索回放」</strong></div>

    <div v-if="sourceConfirmed" class="exact-analysis-shell">
      <div v-if="pendingSourceChange" class="exact-pending-mask" @click="cancelPendingSourceChange"><div><strong>视频源已调整，尚未生效</strong><p>下方结果仍保留。点击「搜索回放」生效，点击空白区域可还原到之前的选择与结果</p></div></div>
    <div class="exact-analysis-layout">
      <div class="panel exact-left-workspace">
      <div class="exact-video-panel">
        <div class="exact-player" ref="exactPlayer">
          <div class="exact-player-media"><video v-if="selectedSource.videoUrl" ref="exactVideo" :src="selectedSource.videoUrl" muted playsinline @timeupdate="syncVideoTime" @loadedmetadata="syncVideoTime" @ended="playerPlaying = false"></video><video-player v-else-if="selectedSource.streamUrl" ref="exactStreamPlayer" :url="selectedSource.streamUrl" format="flv" :native-controls="false"></video-player><img v-else :src="selectedSource.image" :alt="selectedSource.name" /></div>
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
              <div v-if="message.role === 'assistant' && message.thinkingSeconds != null" class="exact-thinking-row"><span class="exact-thinking-tag done">已思考</span><span class="exact-thinking-timer">{{ formatThinkingSeconds(message.thinkingSeconds) }}</span></div>
              <div class="exact-chat-message" :class="message.role">{{ message.text }}</div>
              <div v-if="message.role === 'assistant' && message.analysisId" class="exact-message-actions">
                <button class="exact-message-analysis-btn" :class="{ active: activeAnalysisId === message.analysisId }" type="button" title="分析概要" aria-label="分析概要" @click="loadAnalysisSnapshot(message.analysisId)">&#xf080;</button>
                <button class="exact-message-reanalysis-btn" type="button" :disabled="questionBusy || analyzing" title="重新分析" aria-label="重新分析" @click="rerunMessageAnalysis(message)">&#xf021;</button>
                <button class="exact-message-detail-btn" type="button" title="分析详情" aria-label="分析详情" @click="openMessageDetail(message)">&#xf05a;</button>
              </div>
            </div>
            <div v-if="questionBusy" class="exact-chat-loading"><span class="exact-thinking-row"><span class="exact-thinking-tag">思考中</span><span class="exact-thinking-timer">{{ formatThinkingSeconds(thinkingElapsed) }}</span></span><div v-if="downloading || downloadSeconds != null" class="exact-phase-row"><span>正在智能分析中，请稍后</span><span class="exact-thinking-timer">{{ formatThinkingSeconds(downloadElapsed) }}</span></div><div v-if="analyzePhase" class="exact-phase-row"><span>开始分析...</span><span class="exact-thinking-timer">{{ formatThinkingSeconds(analyzeElapsed) }}</span></div><div v-if="analyzePhase">分析助手正在结合视频内容整理答案...</div></div>
          </div>
          <div class="exact-chat-quick"><button v-for="prompt in quickQuestions" :key="prompt.label" :class="{ active: activeQuickPrompt === prompt.label }" @click="fillQuickPrompt(prompt)">{{ prompt.label }}</button></div>
          <div class="exact-query-box"><textarea ref="exactQueryInput" class="textarea" v-model="query" :placeholder="queryPlaceholder" @keydown.enter.exact.prevent="submitVideoChat"></textarea><div class="exact-query-send"><button class="btn primary exact-send-btn" :disabled="questionBusy" aria-label="发送" title="发送" @click="submitVideoChat"><span class="send-icon" aria-hidden="true"></span></button></div></div>
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
              <div class="exact-summary-heading"><div class="exact-summary-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/></svg><strong>事件摘要</strong></div><details class="exact-export-menu"><summary class="btn">导出摘要</summary><div class="exact-export-options" role="menu"><button role="menuitem" @click="exportFromMenu('pdf', $event)">导出PDF</button><button role="menuitem" @click="exportFromMenu('word', $event)">导出Word</button><button role="menuitem" @click="exportFromMenu('md', $event)">导出MD</button></div></details></div>
              <div v-if="summary.overview" class="exact-summary-section"><div class="exact-summary-section-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>事件概况</div><div class="exact-markdown" v-html="renderMarkdown(summary.overview)"></div></div>
            </div>
            <div class="exact-section-title" style="margin-top:16px;"><div><h3>分析结果</h3><p>共识别 {{ events.length }} 个关键事件，点击卡片定位上方视频。</p></div></div>
            <div class="exact-event-list">
              <article v-for="(event, index) in events" :key="event.name" class="exact-event-card" :class="{ active: selectedEventIndex === index }" @click="selectEvent(index)">
                <img :src="event.image" :alt="event.name" @error="onEventImageError(event)" />
                <div>
                  <div class="exact-event-meta"><strong>发生时间 {{ event.time }}</strong><span>回放定位</span></div>
                  <h4>{{ event.name }}</h4>
                  <div class="exact-markdown exact-event-detail" v-html="renderMarkdown(event.detail)"></div>
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
          <image-results v-else-if="activeResultTabObj.items.length" :items="activeResultTabObj.items" :show-score="true" :selectable="false" :hide-jump="true" :hide-description="true" :show-actions="false" :disable-open="true" :show-full-date="true"></image-results>
          <div v-else class="track-empty">未找到相似目标，可在事件卡片重新框选后再次搜索。</div>
        </div>
        <div v-else-if="activeResultTabObj && activeResultTabObj.type === 'quickDeploy'" class="exact-dialog-body exact-quick-deploy-tab" role="tabpanel" aria-label="快速布防">
          <template v-if="activeResultTabObj.savedTask">
            <div class="detail-header-card exact-deploy-detail-header"><div><h2>{{ activeResultTabObj.savedTask.name }}</h2><p>{{ activeResultTabObj.savedTask.desc }}</p><div class="tags"><span class="tag blue">{{ activeResultTabObj.savedTask.algorithm }}</span><span class="status-pill pass">{{ activeResultTabObj.savedTask.status }}</span><span class="tag">{{ activeResultTabObj.savedTask.area }}</span></div></div></div>
            <div class="panel search-panel exact-deploy-task-info"><h3 class="form-section-title">任务信息</h3><dl class="info-list"><dt>任务ID</dt><dd>{{ activeResultTabObj.savedTask.id }}</dd><dt>算法类型</dt><dd>{{ activeResultTabObj.savedTask.algorithm }}</dd><dt>布控区域</dt><dd>{{ activeResultTabObj.savedTask.area }}</dd><dt>监控点位</dt><dd>{{ activeResultTabObj.savedTask.points }}</dd><dt>生效时间</dt><dd>{{ activeResultTabObj.savedTask.time }}</dd><dt>相似度</dt><dd>{{ activeResultTabObj.savedTask.threshold }}%</dd><dt>创建人</dt><dd>{{ activeResultTabObj.savedTask.owner }}</dd><dt>创建时间</dt><dd>{{ activeResultTabObj.savedTask.created }}</dd></dl></div>
          </template>
          <div v-else class="exact-quick-deploy-form">
            <div class="modal-form-row"><label><span class="required">*</span>任务名称：</label><input class="input" v-model="activeResultTabObj.deployTaskName" placeholder="请输入任务名称" /></div>
            <div class="modal-form-row"><label><span class="required">*</span>布控区域：</label>
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
                <input ref="deployTargetInput" class="hidden-file-input" type="file" accept="image/*" @change="handleDeployTargetUpload" />
                <div v-if="deployTargetSource(activeResultTabObj)" class="deploy-target-preview"><img :src="deployTargetSource(activeResultTabObj)" :alt="activeResultTabObj.deployTargetName || activeResultTabObj.payload.sourceName || '已框选布控目标'" /><span v-if="!activeResultTabObj.deployTargetUrl && activeResultTabObj.payload.crop" class="transferred-crop-box" :style="cropStyleOf(activeResultTabObj.payload.crop)"></span></div>
                <button v-else class="file-upload-tile" style="height:96px;" type="button" @click="triggerDeployTargetUpload"><span><b>＋ 点击上传布控图像</b><br />支持 jpg / png / jpeg</span></button>
                <button v-if="deployTargetSource(activeResultTabObj)" class="btn deploy-target-clear" type="button" @click="clearDeployTarget(activeResultTabObj)">清空</button>
              </div>
            </div>
            <div class="modal-form-row"><label><span class="required">*</span>布控算法：</label>
              <select class="select" v-model="activeResultTabObj.deployAlgorithmId"><option value="">请选择布控算法</option><option v-for="item in deployAlgorithmOptions" :key="item.id" :value="item.id">{{ item.name }}</option></select>
            </div>
            <div class="modal-form-row"><label><span class="required">*</span>生效时间：</label>
              <div class="effective-range"><input class="input" type="date" v-model="activeResultTabObj.deployEffectiveStart" aria-label="生效开始日期" /><span class="range-arrow">→</span><input class="input" type="date" v-model="activeResultTabObj.deployEffectiveEnd" aria-label="生效结束日期" /></div>
            </div>
            <div class="modal-form-row"><label><span class="required">*</span>循环周期：</label>
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
              <article class="timeline-card" v-for="(item, index) in activeResultTabObj.items" :key="item.title + item.date">
                <div><h4>{{ item.title }}</h4><p>{{ item.desc }}</p><div class="tags"><span class="tag blue">{{ item.location }}</span><span class="tag">相似度 {{ item.score }}%</span></div></div>
                <div class="timeline-card-controls"><span class="hint-text timeline-card-date">{{ item.date }}</span></div>
                <button class="timeline-image-button" type="button" title="查看图片详情" @click="openTrackResultModal(activeResultTabObj, index)"><img :src="item.image" :alt="item.title" /></button>
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
  <div v-if="trackResultModalItem" class="exact-result-modal-mask" @click.self="closeTrackResultModal">
    <section class="exact-result-modal" role="dialog" aria-modal="true" aria-label="轨迹结果详情">
      <div class="drawer-head"><h3>分析结果详情</h3><button class="close" aria-label="关闭" @click="closeTrackResultModal">×</button></div>
      <div class="drawer-body drawer-image-result-body exact-result-modal-body">
        <div class="drawer-media-tabs segmented" role="group" aria-label="结果媒体">
          <button class="btn" :class="{ ghost: trackResultMediaTab === 'image' }" :aria-pressed="trackResultMediaTab === 'image'" @click="trackResultMediaTab = 'image'">图片</button>
          <button class="btn" :class="{ ghost: trackResultMediaTab === 'video' }" :aria-pressed="trackResultMediaTab === 'video'" @click="trackResultMediaTab = 'video'">视频</button>
        </div>
        <div v-if="trackResultMediaTab === 'image'" class="drawer-hero-wrap">
          <img class="drawer-hero" :src="trackResultModalItem.image" :alt="trackResultModalItem.title" />
          <button class="drawer-hero-switch" type="button" aria-label="切换图片" @click="cycleTrackResultModal">切换图片</button>
        </div>
        <div v-else class="drawer-video-preview">
          <img :src="trackResultModalItem.image" :alt="trackResultModalItem.title + '监控视频画面'" />
          <span class="play-dot">▶</span>
          <div class="video-control-line"><span>00:08</span><span class="video-progress"><i></i></span><span>00:30</span></div>
        </div>
        <dl class="detail-list">
          <dt>结果名称</dt><dd>{{ trackResultModalItem.title }}</dd>
          <dt>时间</dt><dd>{{ trackResultModalItem.date }}</dd>
          <dt>位置</dt><dd>{{ trackResultModalItem.location }}</dd>
          <dt>相似度</dt><dd>{{ trackResultModalItem.score }}%</dd>
        </dl>
        <div class="panel drawer-image-result-actions" style="padding:12px;">
          <div class="drawer-image-result-action-buttons">
            <button class="btn primary" @click="openTrackResultCrop('imageSearch')">以图搜图</button>
            <button class="btn primary" @click="openTrackResultCrop('quickDeploy')">快速布防</button>
            <button class="btn primary" @click="openTrackResultCrop('track')">轨迹还原</button>
          </div>
        </div>
      </div>
    </section>
  </div>
  <div v-if="messageDetailSnapshot" class="exact-result-modal-mask" @click.self="closeMessageDetail">
    <section class="exact-result-modal" role="dialog" aria-modal="true" aria-label="分析详情">
      <div class="drawer-head"><h3>分析详情</h3><button class="close" aria-label="关闭" @click="closeMessageDetail">×</button></div>
      <div class="drawer-body exact-message-detail-body">
        <p class="exact-message-detail-query">检索内容：{{ messageDetailSnapshot.query || '-' }}</p>
        <div class="exact-message-detail-events">
          <article v-for="event in messageDetailSnapshot.events" :key="event.name" class="exact-message-detail-event">
            <img :src="event.image" :alt="event.name" />
            <div><h4>{{ event.time }} {{ event.name }}</h4><p>{{ event.detail }}</p></div>
          </article>
        </div>
        <dl class="detail-list" style="margin-top:12px;">
          <template v-for="result in messageDetailSnapshot.results" :key="result.title"><dt>{{ result.title }}</dt><dd>{{ result.value }}。{{ result.detail }}</dd></template>
        </dl>
        <div v-if="messageDetailSnapshot.raw" class="exact-message-detail-raw">
          <h4>接口返回全部字段</h4>
          <pre>{{ formatMessageDetailRaw(messageDetailSnapshot.raw) }}</pre>
        </div>
      </div>
    </section>
  </div>
  <div v-if="searchErrorDialog" class="exact-result-modal-mask" @click.self="closeSearchErrorDialog">
    <section class="exact-result-modal exact-search-error-modal" role="alertdialog" aria-modal="true" aria-label="查询录像失败">
      <div class="drawer-head"><h3>{{ searchErrorDialog.title }}</h3><button class="close" aria-label="关闭" @click="closeSearchErrorDialog">×</button></div>
      <div class="drawer-body exact-search-error-body">
        <p class="exact-search-error-message">{{ searchErrorDialog.message }}</p>
        <p v-if="searchErrorDialog.detail" class="exact-search-error-detail">错误详情：{{ searchErrorDialog.detail }}</p>
        <p class="exact-search-error-hint">{{ searchErrorDialog.hint }}</p>
        <div class="exact-search-error-actions"><button class="btn primary" @click="closeSearchErrorDialog">我知道了</button></div>
      </div>
    </section>
  </div>
  <div v-if="searching" class="search-loading-mask" @click.stop><div class="search-loading-box"><span class="search-loading-spinner"></span><p>正在搜索回放，请稍候...</p></div></div>
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
import { deviceStatusLabel } from "../utils/device-status";
import { cropImageToFile, cropToPixelBbox } from "../utils/person-search";
import type { ImageCropSelection } from "../utils/person-search";

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

const EVENT_TIME_KEYS = ["start_time", "start", "time", "timestamp", "begin_time", "begin"];

// 视频理解结果缓存：同一视频 + 同一提问（含全量请求参数）直接命中，秒出结果
// 模块级 Map：组件切走再回来仍然有效；LRU 淘汰，最多保留 20 条
const ANALYSIS_CACHE_LIMIT = 20;
const analysisResponseCache = new Map<string, any>();

function analysisCacheKey(params: Record<string, any>): string {
  return JSON.stringify(params);
}

function getCachedAnalysis(params: Record<string, any>): any {
  const key = analysisCacheKey(params);
  if (!analysisResponseCache.has(key)) return undefined;
  const value = analysisResponseCache.get(key);
  // 命中后刷新插入顺序，让 LRU 淘汰最久未用的条目
  analysisResponseCache.delete(key);
  analysisResponseCache.set(key, value);
  return value;
}

function setCachedAnalysis(params: Record<string, any>, response: any) {
  const key = analysisCacheKey(params);
  analysisResponseCache.delete(key);
  analysisResponseCache.set(key, response);
  while (analysisResponseCache.size > ANALYSIS_CACHE_LIMIT) {
    const oldest = analysisResponseCache.keys().next().value;
    if (oldest === undefined) break;
    analysisResponseCache.delete(oldest);
  }
}

// 视频理解结构化接口（POST /api/v1/video-understanding/structure）的 data 层
function understandingData(response: any): any {
  const data = response && typeof response === "object" ? response.data : null;
  return data && typeof data === "object" ? data : null;
}

// 事件摘要：仅取 data.summary（兜底顶层 summary）
function findVideoUnderstanding(response: any): { overview: string } {
  const data = understandingData(response);
  const summary = (data && typeof data.summary === "string" ? data.summary : "")
    || (response && typeof response.summary === "string" ? response.summary : "");
  return { overview: summary.trim() };
}

// 结构化事件列表：data.events（event_name / time_range / description / key_frame，见接口文档）
function findUnderstandingEvents(response: any): any[] {
  const data = understandingData(response);
  return data && Array.isArray(data.events) ? data.events : [];
}

function escapeHtml(value: string): string {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderMarkdownInline(text: string): string {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
}

// 轻量 Markdown 渲染：支持 # 标题、**加粗**、*斜体*、`行内代码`、无序/有序列表、空行分段与段内换行；先转义 HTML 再替换，避免注入
function markdownToHtml(text: string): string {
  const blocks = String(text || "").replace(/\r\n?/g, "\n").split(/\n{2,}/);
  const html: string[] = [];
  for (const block of blocks) {
    const lines = block.split("\n").map(line => line.trimEnd()).filter(line => line.trim());
    if (!lines.length) continue;
    const heading = lines.length === 1 ? lines[0].match(/^(#{1,4})\s+(.*)$/) : null;
    if (heading) {
      const level = Math.min(heading[1].length, 4);
      html.push(`<div class="md-h md-h${level}">${renderMarkdownInline(heading[2])}</div>`);
      continue;
    }
    const isUl = lines.every(line => /^[-*•]\s+/.test(line.trim()));
    const isOl = lines.every(line => /^\d+[.、)]\s*/.test(line.trim()));
    if (isUl || isOl) {
      const items = lines.map(line => `<li>${renderMarkdownInline(line.trim().replace(/^[-*•]\s+|^\d+[.、)]\s*/, ""))}</li>`).join("");
      html.push(isUl ? `<ul>${items}</ul>` : `<ol>${items}</ol>`);
      continue;
    }
    html.push(`<p>${lines.map(line => renderMarkdownInline(line)).join("<br />")}</p>`);
  }
  return html.join("");
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
  const keyFrame = item && typeof item.key_frame === "object" && item.key_frame ? item.key_frame : null;
  const frameImage = keyFrame && typeof keyFrame.image_url === "string" && keyFrame.image_url.trim() ? keyFrame.image_url.trim() : "";
  const image = frameImage || images[index % images.length];
  if (typeof item === "string") {
    return { name: `分段 ${index + 1}`, time: formatHms(index * segmentSeconds), start: index * segmentSeconds, image, detail: item };
  }
  const range = item.time_range && typeof item.time_range === "object" ? item.time_range : null;
  let rawTime = EVENT_TIME_KEYS.map(key => item[key]).find(value => value !== undefined && value !== null && value !== "");
  if ((rawTime === undefined || rawTime === null || rawTime === "") && range && range.start_seconds !== undefined && range.start_seconds !== null) {
    rawTime = range.start_seconds;
  }
  const start = clockToSeconds(rawTime);
  const time = typeof rawTime === "string" && rawTime.trim() ? rawTime.trim() : formatHms(start);
  const desc = typeof item.description === "string" ? item.description.trim() : "";
  const title = typeof item.event_name === "string" ? item.event_name.trim() : "";
  return { name: title || `事件 ${index + 1}`, time, start, image, detail: desc || "该分段无详细描述" };
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
      pointSearchQuery: "",
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
      localFileDuration: lastLocalVideo.duration || "",
      localVideoUrl: lastLocalVideo.url || "",
      localVideoPoster: lastLocalVideo.poster || "",
      localVideoFile: null as File | null,
      uploadingVideo: false,
      selectedSource: null,
      sourceConfirmed: false,
      pendingSourceChange: false,
      cropDialogOpen: false,
      trackResultModalItem: null as any,
      trackResultModalIndex: -1,
      trackResultModalTab: null as any,
      trackResultMediaTab: "image",
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
      thinkingStartedAt: 0,
      thinkingElapsed: 0,
      thinkingTimer: null as any,
      // 问答阶段计时：视频下载（首次需下载时）与分析接口调用
      downloading: false,
      downloadBaseAt: 0,
      downloadElapsed: 0,
      downloadSeconds: null as number | null,
      analyzePhase: false,
      analyzeBaseAt: 0,
      analyzeElapsed: 0,
      analysisSnapshots: [] as any[],
      activeAnalysisId: null as string | null,
      analysisSnapshotCounter: 0,
      messageDetailSnapshot: null as any,
      searchErrorDialog: null as any,
      resultTabs: [] as any[],
      activeResultTab: "summary",
      resultTabSeq: 0,
      deployAlgorithmOptions: [] as any[],
      quickQuestions: [
        { label: "提问画面", placeholder: "请描述当前视频画面中的内容，包括人物、车辆、物体、场景以及正在发生的行为" },
        { label: "查找目标", placeholder: "请输入目标特征，例如：穿红色上衣的人、白色轿车、背双肩包的人" },
        { label: "重点事件摘要", placeholder: "这段视频发生了哪些重点事件？" }
      ],
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
    pointSearchActive(): boolean {
      return this.pointSearchQuery.trim().length > 0;
    },
    // 监控点模糊查询：命中区域名显示该区域全部设备，否则按设备名称/编号过滤；保持原 area 引用供选中逻辑使用
    pointAreaEntries(): Array<{ area: any; cameras: any[] }> {
      const query = this.pointSearchQuery.trim().toLowerCase();
      const entries = (this.areas as any[]).map(area => {
        if (!query || area.name.toLowerCase().includes(query)) return { area, cameras: area.cameras };
        const cameras = area.cameras.filter((camera: any) =>
          String(camera.name || "").toLowerCase().includes(query) || String(camera.code || "").toLowerCase().includes(query));
        return { area, cameras };
      });
      return query ? entries.filter(entry => entry.cameras.length) : entries;
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
    },
    queryPlaceholder() {
      const quick = this.quickQuestions.find(item => item.label === this.activeQuickPrompt);
      if (quick) return quick.placeholder;
      return this.analyzed ? "可继续围绕当前视频事件、车辆、人员与时间线提问" : "输入目标、场景、行为或时间特征，系统将生成事件结论。";
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
            status: deviceStatusLabel(cam),
            onlineStatus: cam.onlineStatus,
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
      if (this.pointDropdownOpen) this.pointSearchQuery = "";
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
      this.query = "";
      this.activeQuickPrompt = prompt.label;
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
      // 时间段约束兜底（控件已做交互限制，这里防手动输入绕过）：
      // 开始时间必须早于结束时间，且开始/结束时间都不能晚于当前时间
      const rangeStart = this.onlineStart.trim().replace("T", " ");
      const rangeEnd = this.onlineEnd.trim().replace("T", " ");
      const rangeStartMs = parseLocalMs(rangeStart);
      const rangeEndMs = parseLocalMs(rangeEnd);
      if (rangeStartMs && rangeEndMs) {
        if (rangeStartMs >= rangeEndMs) {
          this.showToast("开始时间必须早于结束时间");
          return;
        }
        const nowMs = Date.now();
        if (rangeStartMs > nowMs || rangeEndMs > nowMs) {
          this.showToast("开始时间和结束时间不能晚于当前时间");
          return;
        }
      }
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
          this.openSearchErrorDialog(
            "回放流启动失败，未能查询到该监控点在所选时段的录像。",
            (error && error.message) || "服务未返回具体错误信息"
          );
          return;
        }
        if (!streamUrl) {
          this.searching = false;
          this.openSearchErrorDialog("该时段未查询到录像，请调整时间范围后重试。");
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
      this.stopThinkingTimer();
      this.resetPhaseTimers();
      // 切换视频源后清空分析快照与右侧动态页签（各页签的轮询随页签移除而作废）
      this.analysisSnapshots = [];
      this.activeAnalysisId = null;
      this.analysisSnapshotCounter = 0;
      this.messageDetailSnapshot = null;
      this.resultTabs = [];
      this.activeResultTab = "summary";
      this.closeTrackResultModal();
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
      this.localFileDuration = "";
      this.localVideoPoster = "";
      this.store.lastLocalVideo = { name: this.localFileName, size: this.localFileSize, url: this.localVideoUrl, poster: "", duration: "" };
      this.captureLocalVideoPoster(this.localVideoUrl);
      this.probeLocalVideoDuration(this.localVideoUrl);
      // 上传后立即确认视频源：播放器载入该视频，右侧展示视频问答信息栏
      this.confirmLocalSource();
    },
    // 截取上传视频的第一帧作为卡片缩略图；失败时保留占位图
    captureLocalVideoPoster(url) {
      const video = document.createElement("video");
      video.muted = true;
      video.playsInline = true;
      video.preload = "auto";
      const cleanup = () => {
        video.removeAttribute("src");
        video.load();
      };
      video.addEventListener("loadeddata", () => {
        try {
          const canvas = document.createElement("canvas");
          canvas.width = video.videoWidth || 320;
          canvas.height = video.videoHeight || 180;
          const ctx = canvas.getContext("2d");
          if (!ctx) return;
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          const poster = canvas.toDataURL("image/jpeg", 0.7);
          this.localVideoPoster = poster;
          if (this.store.lastLocalVideo && this.store.lastLocalVideo.url === url) this.store.lastLocalVideo.poster = poster;
          const source = this.selectedSource as any;
          if (source && source.sourceType === "本地上传" && source.videoUrl === url) source.image = poster;
        } catch {
          // 截帧失败保留占位图
        } finally {
          cleanup();
        }
      });
      video.addEventListener("error", cleanup);
      video.src = url;
    },
    // 探测上传视频时长，用于已上传卡片展示「时长 xx:xx」
    probeLocalVideoDuration(url) {
      const probe = document.createElement("video");
      probe.preload = "metadata";
      probe.onloadedmetadata = () => {
        const seconds = Math.round(probe.duration);
        if (Number.isFinite(seconds) && seconds > 0) {
          this.localFileDuration = this.formatTime(seconds);
          if (this.store.lastLocalVideo) this.store.lastLocalVideo.duration = this.localFileDuration;
        }
        if (probe.removeAttribute) probe.removeAttribute("src");
      };
      probe.src = url;
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
        image: this.localVideoPoster || (this as any).store.img.analyst,
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
      this.localFileDuration = "";
      this.localVideoPoster = "";
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
    startThinkingTimer() {
      this.stopThinkingTimer();
      this.thinkingStartedAt = Date.now();
      this.thinkingElapsed = 0;
      this.thinkingTimer = setInterval(() => {
        const now = Date.now();
        this.thinkingElapsed = (now - this.thinkingStartedAt) / 1000;
        if (this.downloadBaseAt) this.downloadElapsed = (now - this.downloadBaseAt) / 1000;
        if (this.analyzeBaseAt) this.analyzeElapsed = (now - this.analyzeBaseAt) / 1000;
      }, 100);
    },
    stopThinkingTimer() {
      if (this.thinkingTimer) {
        clearInterval(this.thinkingTimer);
        this.thinkingTimer = null;
      }
      if (!this.thinkingStartedAt) return 0;
      const seconds = (Date.now() - this.thinkingStartedAt) / 1000;
      this.thinkingStartedAt = 0;
      this.thinkingElapsed = seconds;
      return seconds;
    },
    formatThinkingSeconds(seconds) {
      const value = Math.max(0, Number(seconds) || 0);
      return `${value.toFixed(1)}s`;
    },
    // 每轮问答开始前重置阶段计时（下载/分析）
    resetPhaseTimers() {
      this.downloading = false;
      this.downloadBaseAt = 0;
      this.downloadElapsed = 0;
      this.downloadSeconds = null;
      this.analyzePhase = false;
      this.analyzeBaseAt = 0;
      this.analyzeElapsed = 0;
    },
    // 首次需下载视频（本地上传 MinIO / 在线监控 NVR 导出）时开始下载计时
    startDownloadPhase() {
      this.downloading = true;
      this.downloadElapsed = 0;
      this.downloadBaseAt = Date.now();
    },
    // 下载完成后停止计时，downloadSeconds 留存最终耗时
    stopDownloadPhase() {
      if (this.downloadBaseAt) {
        this.downloadSeconds = (Date.now() - this.downloadBaseAt) / 1000;
        this.downloadElapsed = this.downloadSeconds;
        this.downloadBaseAt = 0;
      }
      this.downloading = false;
    },
    // 调用分析接口前开始分析计时
    startAnalyzePhase() {
      this.analyzePhase = true;
      this.analyzeElapsed = 0;
      this.analyzeBaseAt = Date.now();
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
      // 从用户发送提示词起计时，直到本次 AI 消息完成
      this.startThinkingTimer();
      this.resetPhaseTimers();
      this.questionBusy = true;
      // 本地视频：首次分析前上传到 MinIO，换取分析服务可拉取的 videoUrl
      if (selectedSource.sourceType === "本地上传" && !selectedSource.analysisUrl) {
        if (!this.localVideoFile) {
          this.showToast("请重新上传本地视频");
          this.stopThinkingTimer();
          this.questionBusy = false;
          return;
        }
        this.uploadingVideo = true;
        this.startDownloadPhase();
        try {
          const uploaded = await api.uploadAnalysisVideo(this.localVideoFile);
          selectedSource.analysisUrl = uploaded.videoUrl;
        } catch (error) {
          this.showToast(error instanceof Error ? error.message : "视频上传失败");
          this.stopThinkingTimer();
          this.questionBusy = false;
          return;
        } finally {
          this.uploadingVideo = false;
          this.stopDownloadPhase();
        }
      }
      // 在线监控仅有流地址时：首个问答提示词发出后才从 NVR 导出录像 MP4，
      // 导出成功后播放器切换为该文件；后续对话复用同一 analysisUrl，不再重复导出
      if (selectedSource.sourceType === "在线监控" && !selectedSource.analysisUrl && selectedSource.recordingParams) {
        this.preparingRecording = true;
        this.startDownloadPhase();
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
          this.stopThinkingTimer();
          this.questionBusy = false;
          return;
        } finally {
          this.preparingRecording = false;
          this.stopDownloadPhase();
        }
      }
      if (!selectedSource.analysisUrl) {
        this.showToast("当前视频源不可分析，请重新搜索回放");
        this.stopThinkingTimer();
        this.questionBusy = false;
        return;
      }
      this.startAnalyzePhase();
      const question = this.query.trim();
      this.lastQuery = question;
      this.questionMessages.push({ role: "user", text: question });
      this.analyzing = true;
      try {
        const requestParams = {
          videoUrl: selectedSource.analysisUrl,
          prompt: question,
          question,
          fps: 1,
          segmentSeconds: 60,
          maxSegments: selectedSource.sourceType === "本地上传"
            ? Math.min(20, Math.max(1, Math.ceil((selectedSource.durationSeconds || 60) / 60)))
            : this.estimateMaxSegments(),
          height: 480
        };
        let response = getCachedAnalysis(requestParams);
        if (response === undefined) {
          response = await api.analyzeMinioVideo(requestParams);
          setCachedAnalysis(requestParams, response);
        }
        const img = (this as any).store.img;
        const images = [img.portrait, img.car, img.target];
        const understanding = findVideoUnderstanding(response);
        const overview = understanding.overview;
        const upstreamError = findAnalysisError(response);
        if (upstreamError || (!overview && !findUnderstandingEvents(response).length)) {
          const message = upstreamError || "接口未返回有效分析结果，请检查视频分析服务后重试";
          this.questionMessages.push({ role: "assistant", text: `分析失败：${message}`, thinkingSeconds: this.stopThinkingTimer() });
          this.showToast(`分析失败：${message}`);
          return;
        }
        this.events = findUnderstandingEvents(response).map((item, index) => mapAnalysisEvent(item, index, images, 60)) as any;
        this.applyEventFrameImages(this.events, selectedSource.analysisUrl);
        this.summary = {
          overview: understanding.overview,
          persons: [],
          vehicles: []
        };
        this.results = [];
        this.analyzed = true;
        this.selectedEventIndex = 0;
        if (this.events.length) {
          this.currentTime = (this.events[0] as any).start;
          this.seekVideo(this.currentTime);
        }
        const answerText = `已完成视频源文搜。\n\n事件摘要：${overview}\n\n已识别 ${this.events.length} 个关键事件，右侧可查看事件摘要、分析结果，并继续对视频提问。`;
        const snapshot = this.saveAnalysisSnapshot(answerText, question, response);
        this.questionMessages.push({ role: "assistant", text: answerText, analysisId: snapshot.id, thinkingSeconds: this.stopThinkingTimer() });
        this.activeAnalysisId = snapshot.id;
        this.query = "";
        this.showToast("文搜分析完成，已生成事件结论");
      } catch (error) {
        const message = error instanceof Error ? error.message : "视频分析失败";
        this.questionMessages.push({ role: "assistant", text: `分析失败：${message}`, thinkingSeconds: this.stopThinkingTimer() });
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
    renderMarkdown(text) {
      return markdownToHtml(text);
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
      // 从用户发送提示词起计时，直到本次 AI 消息完成
      this.startThinkingTimer();
      // 视频已下载，直接进入分析阶段计时
      this.resetPhaseTimers();
      this.startAnalyzePhase();
      try {
        // 追问同样走视频理解结构化接口：以问题为 prompt/question 重新分析当前视频源
        const requestParams = {
          videoUrl: selectedSource.analysisUrl,
          prompt: question,
          question,
          fps: 1,
          segmentSeconds: 60,
          maxSegments: selectedSource.sourceType === "本地上传"
            ? Math.min(20, Math.max(1, Math.ceil((selectedSource.durationSeconds || 60) / 60)))
            : this.estimateMaxSegments(),
          height: 480
        };
        let response = getCachedAnalysis(requestParams);
        if (response === undefined) {
          response = await api.analyzeMinioVideo(requestParams);
          setCachedAnalysis(requestParams, response);
        }
        const img = (this as any).store.img;
        const images = [img.portrait, img.car, img.target];
        const understanding = findVideoUnderstanding(response);
        const answer = understanding.overview;
        const upstreamError = findAnalysisError(response);
        if (upstreamError || (!answer && !findUnderstandingEvents(response).length)) {
          const message = upstreamError || "接口未返回有效分析结果，请检查视频分析服务后重试";
          this.questionMessages.push({ role: "assistant", text: `分析失败：${message}`, thinkingSeconds: this.stopThinkingTimer() });
          this.showToast(`分析失败：${message}`);
          return;
        }
        const parsedEvents = findUnderstandingEvents(response).map((item, index) => mapAnalysisEvent(item, index, images, 60));
        if (parsedEvents.length) {
          this.applyEventFrameImages(parsedEvents, selectedSource.analysisUrl);
          this.events = parsedEvents as any;
          this.selectedEventIndex = 0;
          this.currentTime = (this.events[0] as any).start;
          this.seekVideo(this.currentTime);
        }
        this.summary = {
          overview: understanding.overview,
          persons: [],
          vehicles: []
        };
        this.results = [];
        const snapshot = this.saveAnalysisSnapshot(answer, question, response);
        this.questionMessages.push({ role: "assistant", text: answer, analysisId: snapshot.id, thinkingSeconds: this.stopThinkingTimer() });
        this.activeAnalysisId = snapshot.id;
      } catch (error) {
        const message = error instanceof Error ? error.message : "视频分析失败";
        this.questionMessages.push({ role: "assistant", text: `分析失败：${message}`, thinkingSeconds: this.stopThinkingTimer() });
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
        return { savedTask: null, deployTaskName: "", deployAlgorithmId: "", deployCameraSelections: [] as string[], deployAreaOpen: false, deployAreaExpanded: {} as Record<string, boolean>, deployEffectiveStart: "", deployEffectiveEnd: "", deployCycleStart: "00:00", deployCycleEnd: "23:59", deploySimilarity: 50, deployDescription: "", deploySaving: false, deployTargetUrl: "", deployTargetName: "", deployTargetCleared: false };
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
      const closing = this.resultTabs.find(tab => tab.id === id);
      if (closing && closing.deployTargetUrl) URL.revokeObjectURL(closing.deployTargetUrl);
      if (closing && this.trackResultModalTab === closing) this.closeTrackResultModal();
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
    prepareQuickDeployTab() {
      if (this.deployAlgorithmOptions.length) return;
      api.algorithms().then(list => {
        this.deployAlgorithmOptions = (list || []) as any;
      }).catch(() => {
        this.showToast("算法列表加载失败");
      });
    },
    // 布控目标：优先显示本地上传图，否则显示页签带入的框选图；清空后显示上传入口（参照原型 ExactQuickDeployPanel）
    deployTargetSource(tab) {
      if (tab.deployTargetCleared) return "";
      return tab.deployTargetUrl || (tab.payload && tab.payload.image) || "";
    },
    resetDeployTargetUpload(tab) {
      if (tab.deployTargetUrl) URL.revokeObjectURL(tab.deployTargetUrl);
      tab.deployTargetUrl = "";
      tab.deployTargetName = "";
      const input = this.$refs.deployTargetInput as HTMLInputElement | undefined;
      if (input) input.value = "";
    },
    triggerDeployTargetUpload() {
      const input = this.$refs.deployTargetInput as HTMLInputElement | undefined;
      if (input) input.click();
    },
    handleDeployTargetUpload(event) {
      const tab = this.activeResultTabObj;
      if (!tab || tab.type !== "quickDeploy") return;
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        this.showToast("请选择图片文件");
        event.target.value = "";
        return;
      }
      if (tab.deployTargetUrl) URL.revokeObjectURL(tab.deployTargetUrl);
      tab.deployTargetUrl = URL.createObjectURL(file);
      tab.deployTargetName = file.name;
      tab.deployTargetCleared = false;
      this.showToast("布控目标已添加");
    },
    clearDeployTarget(tab) {
      this.resetDeployTargetUpload(tab);
      tab.deployTargetCleared = true;
      this.showToast("布控目标已清空");
    },
    deployAreaLabel(tab) {
      if (!tab.deployCameraSelections.length) return "请选择布控区域（可多选摄像机）";
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
        this.showToast("请选择布控区域");
        return;
      }
      if (!tab.deployAlgorithmId) {
        this.showToast("请选择布控算法");
        return;
      }
      if (!tab.deployEffectiveStart || !tab.deployEffectiveEnd) {
        this.showToast("请选择生效时间");
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
    // 轨迹结果详情弹窗（参照原型 imageResultModal）：页内居中弹窗，不跳转全局抽屉
    openTrackResultModal(tab, index) {
      const item = tab.items[index];
      if (!item) return;
      this.trackResultModalTab = tab;
      this.trackResultModalItem = item;
      this.trackResultModalIndex = index;
      this.trackResultMediaTab = "image";
    },
    closeTrackResultModal() {
      this.trackResultModalItem = null;
      this.trackResultModalIndex = -1;
      this.trackResultModalTab = null;
      this.trackResultMediaTab = "image";
    },
    cycleTrackResultModal() {
      const items = this.trackResultModalTab ? this.trackResultModalTab.items : [];
      if (!items.length) return;
      const next = (this.trackResultModalIndex + 1) % items.length;
      this.trackResultModalIndex = next;
      this.trackResultModalItem = items[next];
    },
    openTrackResultCrop(action) {
      const item = this.trackResultModalItem;
      if (!item) return;
      this.closeTrackResultModal();
      this.openResultCrop(action, item, -1);
    },
    cloneAnalysisData(value) {
      return JSON.parse(JSON.stringify(value));
    },
    // 每轮分析/追问完成后留存快照：摘要、事件列表、选中事件下标、接口原始返回的深拷贝
    saveAnalysisSnapshot(answer, query, rawResponse = null) {
      this.analysisSnapshotCounter += 1;
      const snapshot = {
        id: `analysis-${this.analysisSnapshotCounter}`,
        answer,
        query,
        summary: this.cloneAnalysisData(this.summary),
        events: this.cloneAnalysisData(this.events),
        results: this.cloneAnalysisData(this.results),
        selectedEventIndex: this.selectedEventIndex,
        raw: rawResponse ? this.cloneAnalysisData(rawResponse) : null
      };
      this.analysisSnapshots.push(snapshot);
      return snapshot;
    },
    // 分析详情弹窗：格式化展示接口返回的全部字段
    formatMessageDetailRaw(raw) {
      try {
        return JSON.stringify(raw, null, 2);
      } catch {
        return String(raw);
      }
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
    openSearchErrorDialog(message, detail = "") {
      this.searchErrorDialog = {
        title: "查询录像失败",
        message,
        detail: String(detail || "").trim(),
        hint: "建议：确认监控点在线、所选时段存在录像后重试；若多次失败请联系管理员检查 NVR 回放服务。"
      };
    },
    closeSearchErrorDialog() {
      this.searchErrorDialog = null;
    },
    exportFromMenu(type, event) {
      const menu = (event.currentTarget as HTMLElement).closest("details") as HTMLDetailsElement;
      if (menu) menu.open = false;
      this.exportReport(type);
    },
    reportContent() {
      return `文搜视频分析报告\n\n视频源：${this.selectedSource ? (this.selectedSource as any).name : "-"}\n来源：${this.selectedSource ? this.sourceTypeLabel : "-"}\n检索内容：${this.lastQuery || this.query || "-"}\n\n事件摘要：\n${this.summary.overview || "-"}\n\n分析事件：\n${this.events.map(item => `${item.time} ${item.name}：${item.detail}`).join("\n")}\n\n分析结果：\n${this.results.map(item => `${item.title}：${item.value}。${item.detail}`).join("\n")}`;
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
    if (this.thinkingTimer) {
      clearInterval(this.thinkingTimer);
      this.thinkingTimer = null;
    }
    document.removeEventListener("fullscreenchange", this.syncFullscreenState);
  }
});
</script>
