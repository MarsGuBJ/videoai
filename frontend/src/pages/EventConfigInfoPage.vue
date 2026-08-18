<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件信息配置</h1><p>复用能力仓事件信息，维护事件名称、编码、等级和状态</p></div></div>
    <div class="event-config-page-board">
      <div class="event-config-filter"><div class="event-config-filter-left"><button class="btn primary" @click="openCreate">＋ 新增</button><button class="btn" @click="reset">重置</button><button class="btn primary" @click="showToast('已按当前条件查询')">查询</button><input v-model="keyword" class="input" style="width:260px;" placeholder="请输入名称" /></div><button class="btn" @click="setRoute('eventConfig')">返回事件配置</button></div>
      <div class="table-wrap"><table class="prototype-table"><thead><tr><th class="left">名称</th><th>编码</th><th>事件等级</th><th>事件分类</th><th>状态</th><th>图标</th><th>排序(倒序)</th><th>操作</th></tr></thead><tbody><tr v-for="(row, index) in filteredRows" :key="row.code"><td class="left">{{ row.name }}</td><td><code>{{ row.code }}</code></td><td>{{ row.level }}</td><td>{{ row.category }}</td><td><span class="event-config-dot-status" :class="{ muted: !row.enabled }">{{ row.enabled ? "启用中" : "已停用" }}</span></td><td><span class="event-config-entry-icon event-config-icon-cell">&#xf03e;</span></td><td>{{ row.order }}⌄</td><td><div class="event-config-actions"><button class="link-blue" @click="openEdit(row)">修改</button><button class="link-blue" @click="toggle(row)">{{ row.enabled ? "停用" : "启用" }}</button><button class="link-blue danger" @click="remove(index)">删除</button></div></td></tr><tr v-if="!filteredRows.length"><td colspan="8" class="empty-cell">暂无匹配事件</td></tr></tbody></table></div>
      <div class="event-config-pagination"><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in [1, 2, 3]" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><span>…</span><button type="button" :class="{ active: activePage === 9 }" @click="activePage = 9">9</button><select class="select" aria-label="每页条数"><option>10条/页</option><option>20条/页</option></select><span>跳至</span><input class="input" type="number" min="1" value="5" aria-label="跳至页码" /><span>页</span></div>
    </div>
    <div v-if="modalOpen" class="event-config-modal-mask" @click.self="closeForm">
      <section class="event-config-modal wide" role="dialog" aria-modal="true" :aria-label="editing ? '修改配置信息' : '新增配置信息'">
        <div class="event-config-modal-head"><h3>{{ editing ? "修改配置信息" : "新增配置信息" }}</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeForm">×</button></div>
        <div class="event-config-form-grid cols-3">
          <label class="event-config-field"><span>* 事件名称</span><input v-model="form.name" class="input" placeholder="请输入内容" /></label>
          <label class="event-config-field"><span>* 事件编码</span><input v-model="form.code" class="input" placeholder="请输入内容" /></label>
          <label class="event-config-field"><span>事件等级</span><select v-model="form.level" class="select"><option>低</option><option>中</option><option>高</option></select></label>
          <label class="event-config-field"><span>标注方式</span><select v-model="form.mark" class="select"><option>多边形</option><option>关键点</option></select></label>
          <div class="event-config-field"><span>是否启用</span><div><button class="event-config-switch" :class="{ active: form.enabled }" type="button" :aria-label="form.enabled ? '已启用' : '已停用'" @click="form.enabled = !form.enabled"></button></div></div>
          <div class="event-config-field"><span>事件图标</span><label class="event-config-upload-tile" :class="{ 'has-file': form.iconName }"><input type="file" accept="image/*" hidden @change="pickIcon" /><span class="event-config-upload-icon">&#xf03e;</span><span>{{ form.iconName || "上传" }}</span></label></div>
          <div class="event-config-field wide">
            <div class="event-config-attr-editor"><span>事件属性</span><div class="event-config-attr-rows"><div v-for="(attr, index) in form.attrs" :key="index" class="event-config-attr-row"><input v-model="attr.key" class="input" :placeholder="index === 1 ? 'type' : 'confidence'" /><em>:</em><input v-model="attr.value" class="input" :placeholder="index === 1 ? '类型' : '置信度'" /><button class="btn" type="button" aria-label="删除属性" :disabled="form.attrs.length <= 1" @click="removeAttr(index)">⊖</button></div><button class="btn" type="button" @click="addAttr">＋ 添加属性</button></div></div>
          </div>
        </div>
        <div class="event-config-modal-actions"><button class="btn" @click="closeForm">取消</button><button class="btn primary" @click="save">保存</button></div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "EventConfigInfoPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      keyword: "",
      activePage: 1,
      modalOpen: false,
      editing: null as any,
      form: { name: "", code: "", level: "低", mark: "多边形", enabled: true, iconName: "", attrs: [] as any[] },
      rows: [
        { name: "家禽检测", code: "FOWL_DETECTION", level: "低", category: "待完成", order: 25, enabled: true },
        { name: "区域入侵", code: "INTRUSION_DEC", level: "低", category: "安防事件", order: 24, enabled: true },
        { name: "烟火识别", code: "SMOKE", level: "低", category: "消防事件", order: 23, enabled: true },
        { name: "RK_周界入侵", code: "RK_INTRUSION_DEC", level: "高", category: "安防事件", order: 22, enabled: true },
        { name: "污水应急监控", code: "PERSON_WADE", level: "低", category: "环境事件", order: 21, enabled: true },
        { name: "睡岗", code: "SLEEP", level: "低", category: "行为事件", order: 20, enabled: true },
        { name: "离岗", code: "LEAVE", level: "低", category: "行为事件", order: 19, enabled: true },
        { name: "RK_抽烟", code: "RK_SMOKING", level: "中", category: "行为事件", order: 18, enabled: true },
        { name: "RK_物品占用通道", code: "RK_OCCUPIED_AREA", level: "低", category: "安防事件", order: 17, enabled: true },
        { name: "非机动车识别", code: "NONVEHICLE", level: "低", category: "交通事件", order: 14, enabled: true }
      ]
    };
  },
  computed: {
    filteredRows(): any[] {
      const value = this.keyword.trim().toLowerCase();
      return value ? this.rows.filter(row => `${row.name}${row.code}`.toLowerCase().includes(value)) : this.rows;
    }
  },
  methods: {
    reset() { this.keyword = ""; },
    blankForm() {
      return { name: "", code: "", level: "低", mark: "多边形", enabled: true, iconName: "", attrs: [{ key: "", value: "" }, { key: "", value: "" }] };
    },
    openCreate() { this.editing = null; this.form = this.blankForm(); this.modalOpen = true; },
    openEdit(row: any) {
      this.editing = row;
      this.form = { name: row.name, code: row.code, level: row.level, mark: "多边形", enabled: row.enabled, iconName: "", attrs: [{ key: "", value: "" }, { key: "", value: "" }] };
      this.modalOpen = true;
    },
    closeForm() { this.modalOpen = false; },
    pickIcon(event: any) { this.form.iconName = event.target.files && event.target.files[0] ? event.target.files[0].name : ""; },
    addAttr() { this.form.attrs.push({ key: "", value: "" }); },
    removeAttr(index: number) { if (this.form.attrs.length > 1) this.form.attrs.splice(index, 1); },
    save() {
      if (!this.form.name.trim() || !this.form.code.trim()) { this.showToast("请填写事件名称和事件编码"); return; }
      if (this.editing) {
        Object.assign(this.editing, { name: this.form.name.trim(), code: this.form.code.trim(), level: this.form.level, enabled: this.form.enabled });
        this.showToast(`事件信息已更新：${this.form.name}`);
      } else {
        const nextOrder = Math.max(...this.rows.map(row => row.order)) + 1;
        this.rows.unshift({ name: this.form.name.trim(), code: this.form.code.trim(), level: this.form.level, category: "安防事件", order: nextOrder, enabled: this.form.enabled });
        this.showToast(`事件信息已保存：${this.form.name}`);
      }
      this.closeForm();
    },
    toggle(row: any) { row.enabled = !row.enabled; this.showToast(`${row.name}已${row.enabled ? "启用" : "停用"}`); },
    remove(index: number) { const [row] = this.rows.splice(index, 1); this.showToast(`已删除事件：${row.name}`); }
  }
});
</script>
