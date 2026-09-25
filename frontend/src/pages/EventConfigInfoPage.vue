<template>
  <section :class="embedded ? 'event-config-tab-pane' : 'content review-wide'">
    <div v-if="!embedded" class="review-titlebar"><div><h1>事件信息配置</h1><p>复用能力仓事件信息，维护事件名称、编码、等级和状态</p></div></div>
    <div class="event-config-page-board">
      <div class="event-config-filter"><div class="event-config-filter-left"><button class="btn primary" @click="openCreate">＋ 新增</button><button class="btn" @click="reset">重置</button><button class="btn primary" @click="showToast('已按当前条件查询')">查询</button><input v-model="keyword" class="input" style="width:260px;" placeholder="请输入名称" /></div><button v-if="!embedded" class="btn" @click="setRoute('eventConfig')">返回事件配置</button></div>
      <div class="table-wrap"><table class="prototype-table"><thead><tr><th class="left">名称</th><th>编码</th><th>事件等级</th><th>事件分类</th><th>状态</th><th>图标</th><th>排序(倒序)</th><th>操作</th></tr></thead><tbody><tr v-for="row in paginatedRows" :key="row.id"><td class="left">{{ row.name }}</td><td><code>{{ row.code }}</code></td><td>{{ row.level }}</td><td>{{ row.category }}</td><td><span class="event-config-dot-status" :class="{ muted: !row.enabled }">{{ row.enabled ? "启用中" : "已停用" }}</span></td><td><img v-if="iconUrl(row.iconName)" class="event-config-icon-img" :src="iconUrl(row.iconName)" :alt="row.name + ' 图标'" /><span v-else class="event-config-entry-icon event-config-icon-cell">&#xf03e;</span></td><td>{{ row.sortOrder }}</td><td><div class="event-config-actions"><button class="link-blue" @click="openEdit(row)">修改</button><button class="link-blue" @click="toggle(row)">{{ row.enabled ? "停用" : "启用" }}</button><button class="link-blue danger" @click="remove(row)">删除</button></div></td></tr><tr v-if="!loading && !paginatedRows.length"><td colspan="8" class="empty-cell">暂无匹配事件</td></tr><tr v-if="loading"><td colspan="8" class="empty-cell">加载中...</td></tr></tbody></table></div>
      <div class="event-config-pagination"><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in leadingPages" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><span v-if="pageCount > 4">…</span><button v-if="pageCount > 3" type="button" :class="{ active: activePage === pageCount }" @click="activePage = pageCount">{{ pageCount }}</button><select class="select" v-model.number="pageSize" aria-label="每页条数" @change="activePage = 1"><option :value="10">10条/页</option><option :value="20">20条/页</option></select><span>跳至</span><input class="input" type="number" min="1" v-model="jumpTarget" aria-label="跳至页码" @keyup.enter="jumpTo" @change="jumpTo" /><span>页</span></div>
    </div>
    <div v-if="modalOpen" class="event-config-modal-mask" @click.self="closeForm">
      <section class="event-config-modal wide" role="dialog" aria-modal="true" :aria-label="editing ? '修改配置信息' : '新增配置信息'">
        <div class="event-config-modal-head"><h3>{{ editing ? "修改配置信息" : "新增配置信息" }}</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeForm">×</button></div>
        <div class="event-config-form-grid cols-3">
          <div class="event-config-field"><span>事件来源</span><div ref="sourceBox" class="event-config-source"><input v-model="form.source" class="input event-config-source-input" role="combobox" aria-label="事件来源" aria-haspopup="listbox" :aria-expanded="sourceOpen ? 'true' : 'false'" aria-controls="event-source-options" placeholder="请选择或输入事件来源" @focus="openSourceMenu" @click="openSourceMenu" @input="openSourceMenu" @keydown.down.prevent="moveSource(1)" @keydown.up.prevent="moveSource(-1)" @keydown.enter.prevent="commitSource" @keydown.esc="closeSourceMenu" /><span class="event-config-source-caret" :class="{ open: sourceOpen }" aria-hidden="true"></span><ul v-if="sourceOpen && sourceSuggestions.length" id="event-source-options" class="event-config-source-menu" role="listbox"><li v-for="(option, index) in sourceSuggestions" :key="option" role="option" :aria-selected="form.source === option ? 'true' : 'false'" :class="{ active: index === sourceActiveIndex, selected: form.source === option }" @mouseenter="sourceActiveIndex = index" @mousedown.prevent="pickSource(option)">{{ option }}</li></ul></div></div>
          <label class="event-config-field"><span><span class="required">*</span>事件名称</span><input v-model="form.name" class="input" placeholder="请输入内容" /></label>
          <label class="event-config-field"><span><span class="required">*</span>事件编码</span><input v-model="form.code" class="input" placeholder="请输入内容" /></label>
          <label class="event-config-field"><span>算法编码</span><select v-model="form.algorithmCode" class="select" aria-label="算法编码"><option value="">不绑定算法</option><option v-for="item in algorithmOptions" :key="item.id" :value="item.code">{{ item.code }}（{{ item.name }}）</option></select></label>
          <label class="event-config-field"><span>事件等级</span><select v-model="form.level" class="select"><option>低</option><option>中</option><option>高</option></select></label>
          <label class="event-config-field"><span>事件分类</span><select v-model="form.category" class="select"><option>安防事件</option><option>消防事件</option><option>环境事件</option><option>行为事件</option><option>交通事件</option></select></label>
          <label class="event-config-field"><span>标注方式</span><select v-model="form.mark" class="select"><option>多边形</option><option>关键点</option></select></label>
          <div class="event-config-field"><span>是否启用</span><div><button class="event-config-switch" :class="{ active: form.enabled }" type="button" :aria-label="form.enabled ? '已启用' : '已停用'" @click="form.enabled = !form.enabled"></button></div></div>
          <div class="event-config-field"><span>事件图标</span><label class="event-config-upload-tile" :class="{ 'has-file': form.iconName }"><input type="file" accept="image/*" hidden @change="pickIcon" /><img v-if="iconUrl(form.iconName)" class="event-config-upload-preview" :src="iconUrl(form.iconName)" alt="事件图标" /><template v-else><span class="event-config-upload-icon">&#xf03e;</span><span>{{ iconUploading ? '上传中…' : '上传' }}</span></template></label></div>
          <div class="event-config-field wide">
            <div class="event-config-attr-editor"><span>事件属性</span><div class="event-config-attr-rows"><div v-for="(attr, index) in form.attrs" :key="index" class="event-config-attr-row"><input v-model="attr.key" class="input" :placeholder="index === 1 ? 'type' : 'confidence'" /><em>:</em><input v-model="attr.value" class="input" :placeholder="index === 1 ? '类型' : '置信度'" /><button class="btn" type="button" aria-label="删除属性" :disabled="form.attrs.length <= 1" @click="removeAttr(index)">⊖</button></div><button class="btn" type="button" @click="addAttr">＋ 添加属性</button></div></div>
          </div>
        </div>
        <div class="event-config-modal-actions"><button class="btn" @click="closeForm">取消</button><button class="btn primary" :disabled="saving" @click="save">保存</button></div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api, sameOriginAssetUrl } from "../api";
import type { Algorithm, EventInfo, EventInfoPayload } from "../types";

export default defineComponent({
  name: "EventConfigInfoPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "embedded"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      keyword: "",
      activePage: 1,
      pageSize: 10,
      jumpTarget: "",
      rows: [] as EventInfo[],
      loading: false,
      saving: false,
      iconUploading: false,
      modalOpen: false,
      sourceOpen: false,
      sourceActiveIndex: -1,
      sourceOptions: ["中心推理平台", "云边协同平台"] as string[],
      algorithmOptions: [] as Algorithm[],
      editing: null as EventInfo | null,
      form: { name: "", code: "", level: "低", category: "安防事件", mark: "多边形", enabled: true, iconName: "", source: "", eventSource: "", algorithmCode: "", attrs: [] as { key: string; value: string }[] }
    };
  },
  computed: {
    filteredRows(): EventInfo[] {
      const value = this.keyword.trim().toLowerCase();
      return value ? this.rows.filter(row => `${row.name}${row.code}`.toLowerCase().includes(value)) : this.rows;
    },
    pageCount(): number {
      return Math.max(1, Math.ceil(this.filteredRows.length / this.pageSize));
    },
    leadingPages(): number[] {
      return [1, 2, 3].filter(page => page <= this.pageCount);
    },
    paginatedRows(): EventInfo[] {
      const start = (this.activePage - 1) * this.pageSize;
      return this.filteredRows.slice(start, start + this.pageSize);
    },
    sourceSuggestions(): string[] {
      const value = this.form.source.trim().toLowerCase();
      if (!value) return this.sourceOptions;
      // 已选中某个来源时展开全部候选，便于直接改选；只有输入了半截关键字才做过滤
      const exact = this.sourceOptions.some(option => option.toLowerCase() === value);
      if (exact) return this.sourceOptions;
      return this.sourceOptions.filter(option => option.toLowerCase().includes(value));
    }
  },
  mounted() {
    this.loadRows();
    this.loadAlgorithmOptions();
    document.addEventListener("click", this.onSourceDocumentClick);
  },
  unmounted() {
    document.removeEventListener("click", this.onSourceDocumentClick);
  },
  methods: {
    reset() { this.keyword = ""; this.activePage = 1; },
    jumpTo() {
      const target = Math.floor(Number(this.jumpTarget));
      if (target >= 1) this.activePage = Math.min(target, this.pageCount);
      this.jumpTarget = "";
    },
    async loadRows() {
      if (this.loading) return;
      this.loading = true;
      try {
        this.rows = await api.eventInfos();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "事件信息加载失败");
      } finally {
        this.loading = false;
      }
    },
    async loadAlgorithmOptions() {
      try {
        this.algorithmOptions = await api.algorithms();
      } catch {
        // 算法列表不可用时算法编码下拉只保留「不绑定算法」
      }
    },
    blankForm() {
      return { name: "", code: "", level: "低", category: "安防事件", mark: "多边形", enabled: true, iconName: "", source: "", eventSource: "", algorithmCode: "", attrs: [{ key: "", value: "" }, { key: "", value: "" }] };
    },
    openCreate() { this.editing = null; this.form = this.blankForm(); this.modalOpen = true; },
    openEdit(row: EventInfo) {
      this.editing = row;
      const attrs = (row.attrs || []).map(attr => ({ key: attr.key, value: attr.value }));
      this.form = {
        name: row.name,
        code: row.code,
        level: row.level,
        category: row.category || "安防事件",
        mark: row.mark || "多边形",
        enabled: row.enabled,
        iconName: row.iconName || "",
        source: row.source || "",
        eventSource: row.eventSource || "",
        algorithmCode: row.algorithmCode || "",
        attrs: attrs.length ? attrs : [{ key: "", value: "" }]
      };
      this.modalOpen = true;
    },
    closeForm() { this.modalOpen = false; this.closeSourceMenu(); },
    openSourceMenu() {
      this.sourceOpen = true;
      this.sourceActiveIndex = this.sourceSuggestions.indexOf(this.form.source);
    },
    closeSourceMenu() { this.sourceOpen = false; this.sourceActiveIndex = -1; },
    moveSource(step: number) {
      const total = this.sourceSuggestions.length;
      if (!total) return;
      if (!this.sourceOpen) { this.openSourceMenu(); return; }
      const next = this.sourceActiveIndex + step;
      this.sourceActiveIndex = next < 0 ? total - 1 : (next >= total ? 0 : next);
    },
    commitSource() {
      const option = this.sourceSuggestions[this.sourceActiveIndex];
      if (this.sourceOpen && option) { this.pickSource(option); return; }
      this.closeSourceMenu();
    },
    pickSource(option: string) { this.form.source = option; this.closeSourceMenu(); },
    onSourceDocumentClick(event: MouseEvent) {
      const box = this.$refs.sourceBox as unknown as HTMLElement | undefined;
      if (!box || !box.contains(event.target as Node)) this.closeSourceMenu();
    },
    // 图标值统一取可访问地址：老数据存的是纯文件名（无路径），无法解析时回落默认图标
    iconUrl(value: any) {
      const text = String(value == null ? "" : value).trim();
      if (!text) return "";
      return /^(https?:|data:|\/)/i.test(text) ? sameOriginAssetUrl(text) : "";
    },
    // 事件图标：先上传拿到可访问地址再保存（原来只存文件名，页面上无法显示）
    async pickIcon(event: any) {
      const input = event.target as HTMLInputElement;
      const file = input.files && input.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        this.showToast("请选择图片文件");
        input.value = "";
        return;
      }
      this.iconUploading = true;
      try {
        const uploaded = await api.uploadImage(file);
        this.form.iconName = uploaded.imageUrl;
        this.showToast("事件图标已上传");
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "事件图标上传失败");
      } finally {
        this.iconUploading = false;
        input.value = "";
      }
    },
    addAttr() { this.form.attrs.push({ key: "", value: "" }); },
    removeAttr(index: number) { if (this.form.attrs.length > 1) this.form.attrs.splice(index, 1); },
    async save() {
      if (!this.form.name.trim() || !this.form.code.trim()) { this.showToast("请填写事件名称和事件编码"); return; }
      const payload: EventInfoPayload = {
        name: this.form.name.trim(),
        code: this.form.code.trim(),
        level: this.form.level,
        category: this.form.category,
        mark: this.form.mark,
        iconName: this.form.iconName.trim(),
        source: this.form.source.trim(),
        eventSource: this.form.eventSource.trim(),
        algorithmCode: this.form.algorithmCode,
        attrs: this.form.attrs.filter(attr => attr.key.trim() || attr.value.trim()).map(attr => ({ key: attr.key.trim(), value: attr.value.trim() })),
        enabled: this.form.enabled
      };
      if (this.editing) payload.sortOrder = this.editing.sortOrder;
      if (this.saving) return;
      this.saving = true;
      try {
        if (this.editing) {
          await api.updateEventInfo(this.editing.id, payload);
          this.showToast(`事件信息已更新：${payload.name}`);
        } else {
          await api.createEventInfo(payload);
          this.showToast(`事件信息已保存：${payload.name}`);
        }
        this.closeForm();
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "事件信息保存失败");
      } finally {
        this.saving = false;
      }
    },
    async toggle(row: EventInfo) {
      try {
        await api.updateEventInfo(row.id, {
          name: row.name,
          code: row.code,
          level: row.level,
          category: row.category,
          mark: row.mark,
          iconName: row.iconName,
          source: row.source,
          eventSource: row.eventSource,
          algorithmCode: row.algorithmCode,
          attrs: row.attrs || [],
          sortOrder: row.sortOrder,
          enabled: !row.enabled
        });
        this.showToast(`${row.name}已${row.enabled ? "停用" : "启用"}`);
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "事件状态更新失败");
      }
    },
    async remove(row: EventInfo) {
      if (!window.confirm(`确认删除事件「${row.name}」？`)) return;
      try {
        await api.deleteEventInfo(row.id);
        this.showToast(`已删除事件：${row.name}`);
        if (this.activePage > 1 && this.paginatedRows.length === 1) this.activePage--;
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "事件信息删除失败");
      }
    }
  }
});
</script>
