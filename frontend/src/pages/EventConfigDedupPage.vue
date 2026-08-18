<template>
  <section class="content review-wide">
    <template v-if="view === 'cards'">
      <div class="review-titlebar"><div><h1>事件去重配置</h1><p>维护事件去重规则、执行策略和规则日志</p></div><button class="btn" @click="setRoute('eventConfig')">返回事件配置</button></div>
      <div class="event-config-rule-grid"><button class="event-config-rule-create" type="button" @click="openCreate"><span style="font-size:24px;">＋</span><span>点击创建事件过滤规则</span></button><article v-for="(card, index) in cards" :key="card.key" class="event-config-rule-card"><div class="event-config-rule-head"><strong>{{ card.name }}</strong><div class="event-config-rule-menu"><button type="button" aria-label="规则菜单">☰</button><div class="event-config-rule-menu-drop"><button type="button" @click="modal = 'detail'">详情</button><button type="button" @click="modal = 'logs'">日志</button><button type="button" @click="openCreate">编辑</button><button type="button" class="danger" @click="removeCard(index)">删除</button></div></div></div><span><em v-if="card.effective">已生效</em></span><p>{{ card.strategy }}：{{ card.params }}</p><button class="event-config-switch" :class="{ active: card.enabled }" type="button" :aria-label="card.enabled ? '已启用' : '已停用'" @click="card.enabled = !card.enabled"></button></article></div>
    </template>
    <template v-else>
      <div class="review-titlebar"><div><h1>新增去重规则</h1><p>配置事件属性、关联算法、摄像头范围和执行策略</p></div><button class="btn" @click="view = 'cards'">← 返回</button></div>
      <div class="event-config-page-board" style="min-height:0;margin-bottom:14px;">
        <h4 class="event-config-section-title">事件属性</h4>
        <div class="event-config-form-grid">
          <label class="event-config-field"><span>* 名称</span><input v-model="form.name" class="input" /></label>
          <label class="event-config-field"><span>* 关联算法</span><select v-model="form.algorithm" class="select"><option>区域入侵</option><option>车辆违停</option><option>垃圾识别</option></select></label>
          <label class="event-config-field"><span>* 摄像头</span><input v-model="form.camera" class="input" placeholder="搜索摄像头" /></label>
          <div class="event-config-field"><span>摄像头范围</span><div class="event-config-radio-row"><label><input type="checkbox" v-model="form.allChecked" @change="toggleAllCameras" /> 全选</label><label><input type="checkbox" value="test01" v-model="form.cameras" /> test01</label></div></div>
        </div>
      </div>
      <div class="event-config-page-board" style="min-height:0;margin-bottom:14px;">
        <h4 class="event-config-section-title">执行策略</h4>
        <div class="event-config-tabs"><button v-for="tab in tabs" :key="tab" type="button" :class="{ active: form.tab === tab }" @click="form.tab = tab">{{ tab }}</button></div>
        <div class="event-config-form-grid">
          <label class="event-config-field"><span>* 时间长度</span><span class="event-config-input-group"><input v-model="form.duration" class="input" /><em class="event-config-input-addon">分钟</em></span></label>
          <label class="event-config-field"><span>* 相似度</span><input v-model="form.similarity" class="input" /></label>
        </div>
      </div>
      <div class="event-config-page-board" style="min-height:0;">
        <h4 class="event-config-section-title">备注说明</h4>
        <textarea v-model="form.remark" placeholder="请填写说明，最多不超过200字" style="width:100%;min-height:86px;padding:8px 10px;border:1px solid #cbd5df;border-radius:6px;font:inherit;resize:vertical;"></textarea>
      </div>
      <div class="event-config-modal-actions"><button class="btn" @click="resetForm">重置</button><button class="btn primary" @click="submit">提交</button><button class="btn" @click="view = 'cards'">返回</button></div>
    </template>
    <div v-if="modal === 'logs'" class="event-config-modal-mask" @click.self="modal = null">
      <section class="event-config-modal" role="dialog" aria-modal="true" aria-label="规则日志">
        <div class="event-config-modal-head"><h3>规则日志</h3><button class="event-config-modal-close" aria-label="关闭" @click="modal = null">×</button></div>
        <div class="event-config-log-filters"><select v-model="logFilters.eventType" class="select"><option value="">事件类型</option></select><input v-model="logFilters.ruleName" class="input" placeholder="规则名称" /><select v-model="logFilters.device" class="select"><option value="">设备名称</option></select><select v-model="logFilters.ruleType" class="select"><option value="">规则类型</option></select><select v-model="logFilters.status" class="select"><option value="">执行状态</option></select><input v-model="logFilters.range" class="input" placeholder="开始日期  ->  结束日期" /><button class="btn" @click="resetLogFilters">重置</button><button class="btn primary" @click="showToast('已按当前条件查询')">查询</button></div>
        <div class="table-wrap"><table class="prototype-table"><thead><tr><th class="left">设备名称</th><th>规则名称</th><th>算法类型</th><th>规则类型</th><th>执行状态</th><th>过滤数量</th><th>执行时间</th><th>操作</th></tr></thead><tbody><tr v-for="(row, index) in logRows" :key="index"><td class="left">{{ row.device }}</td><td>{{ row.rule }}</td><td>{{ row.algo }}</td><td>{{ row.type }}</td><td><span class="event-config-status" :class="{ error: row.status === '执行失败' }">{{ row.status }}</span></td><td>{{ row.count }}</td><td>{{ row.time }}</td><td><button class="link-blue" @click="modal = 'detail'">详情</button></td></tr></tbody></table></div>
        <div class="event-config-pagination"><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in [1, 2, 3]" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><span>…</span><button type="button" :class="{ active: activePage === 9 }" @click="activePage = 9">9</button><select class="select" aria-label="每页条数"><option>10条/页</option><option>20条/页</option></select><span>跳至</span><input class="input" type="number" min="1" value="5" aria-label="跳至页码" /><span>页</span></div>
      </section>
    </div>
    <div v-if="modal === 'detail'" class="event-config-modal-mask" @click.self="modal = null">
      <section class="event-config-modal" role="dialog" aria-modal="true" aria-label="事件规则详情">
        <div class="event-config-modal-head"><h3><button class="link-blue" style="padding:0;" aria-label="返回规则日志" @click="modal = 'logs'">←</button> 事件规则详情</h3><button class="event-config-modal-close" aria-label="关闭" @click="modal = null">×</button></div>
        <div class="event-config-detail-grid"><span><b>规则名称：</b>车辆违停算法过滤车辆违停算法过滤</span><span><b>规则状态：</b>已生效</span><span><b>关联算法：</b>车辆违停乱放</span><span><b>过滤类型：</b>实时重叠图像去重</span><span><b>相似度：</b>0.95</span><span><b>设备名称：</b>室外-B1北侧道路2</span></div>
        <h4 class="event-config-section-title">过滤详情</h4>
        <div class="event-config-filter-preview"><em>已保留</em><b><span>相似度</span><span>95</span></b><strong>2024-09-27 13:33:46</strong></div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "EventConfigDedupPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    const baseRules = [
      { name: "1221", algorithm: "测试图像过滤", strategy: "时间维度去重", params: "过滤时长 23.0m", enabled: true, effective: true },
      { name: "1221", algorithm: "测试图像过滤", strategy: "时间维度去重", params: "过滤时长 23.0m", enabled: true, effective: true },
      { name: "123", algorithm: "区域入侵", strategy: "时间维度去重", params: "过滤时长 2.0h", enabled: false, effective: false },
      { name: "123", algorithm: "区域入侵", strategy: "时间维度去重", params: "过滤时长 10.0m", enabled: false, effective: false },
      { name: "车辆违停算法过滤车辆违停", algorithm: "车辆违停乱放", strategy: "实时重叠图像去重", params: "相似度 0.95", enabled: true, effective: true },
      { name: "垃圾识别过滤", algorithm: "垃圾识别", strategy: "区间重叠图像去重", params: "过滤时长 2.0h  相似度 0.5", enabled: true, effective: true }
    ];
    return {
      view: "cards",
      modal: null as string | null,
      activePage: 1,
      tabs: ["时间维度去重", "区间重叠图像去重", "实时重叠图像去重"],
      cards: baseRules.concat(baseRules, baseRules.slice(0, 5)).map((rule, index) => ({ ...rule, key: index as number | string })),
      form: { name: "去重", algorithm: "区域入侵", camera: "", allChecked: true, cameras: ["test01"], tab: "时间维度去重", duration: "", similarity: "", remark: "" },
      logFilters: { eventType: "", ruleName: "", device: "", ruleType: "", status: "", range: "" },
      logRows: Array.from({ length: 10 }, (_, t) => ({ device: "室外-B1北侧道路2", rule: "测试图像过滤", algo: "车辆违停乱放", type: "实时重叠图像去重", status: t <= 5 ? "执行成功" : "执行失败", count: t <= 5 ? 1 : 0, time: `2024-09-27 15:${57 - t}:34` }))
    };
  },
  methods: {
    openCreate() { this.view = "create"; },
    toggleAllCameras() { this.form.cameras = this.form.allChecked ? ["test01"] : []; },
    resetForm() { Object.assign(this.form, { name: "去重", algorithm: "区域入侵", camera: "", allChecked: true, cameras: ["test01"], tab: "时间维度去重", duration: "", similarity: "", remark: "" }); },
    submit() {
      if (!this.form.name.trim()) { this.showToast("请填写规则名称"); return; }
      const params = this.form.tab === "时间维度去重" ? `过滤时长 ${this.form.duration || 0}m` : `相似度 ${this.form.similarity || "-"}`;
      this.cards.unshift({ name: this.form.name.trim(), algorithm: this.form.algorithm, strategy: this.form.tab, params, enabled: true, effective: false, key: `new-${Date.now()}` });
      this.view = "cards";
      this.showToast(`去重规则已提交：${this.form.name}`);
    },
    removeCard(index: number) { const [card] = this.cards.splice(index, 1); this.showToast(`已删除规则：${card.name}`); },
    resetLogFilters() { this.logFilters = { eventType: "", ruleName: "", device: "", ruleType: "", status: "", range: "" }; }
  }
});
</script>
