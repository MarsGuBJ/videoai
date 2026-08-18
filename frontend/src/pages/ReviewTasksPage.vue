<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>任务管理</h1><p>异常事件复查、人工补核、离线分析与效果测试</p></div></div>
    <div class="review-board">
      <div class="prototype-filter">
        <div class="review-task-filter-actions"><button class="btn primary" @click="openModal('reviewTask')">上传复核任务</button><button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button><button class="btn">重置</button></div>
        <div class="filter-item"><span>搜索：</span><input class="input" placeholder="搜索任务ID、事件类型" /></div>
        <div class="filter-item"><span>状态：</span><select class="select"><option>请选择</option><option>已完成</option><option>进行中</option><option>待处理</option></select></div>
        <div class="filter-item"><span>创建时间：</span><div class="date-range"><input class="input" value="2024-9-10" /><span>→</span><input class="input" value="2024-11-24" /></div></div>
      </div>
      <table class="prototype-table">
        <colgroup><col style="width:46px;" /><col style="width:180px;" /><col style="width:230px;" /><col style="width:220px;" /><col style="width:120px;" /><col style="width:140px;" /></colgroup>
        <thead><tr><th><input type="checkbox" /></th><th>任务ID</th><th>事件类型</th><th>创建时间</th><th>事件有效</th><th>任务状态</th></tr></thead>
        <tbody><tr v-for="row in store.prototypeTaskRows" :key="row.id" class="review-task-row" @click="openModal('eventDetail', row)"><td @click.stop><input type="checkbox" /></td><td>{{ row.id }}</td><td>{{ row.type }}</td><td>{{ row.created }}</td><td><span class="status-pill" :class="statusClass(row.timeValid)">{{ row.timeValid }}</span></td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td></tr></tbody>
      </table>
      <div class="table-footer"><span>显示 1-5 共 127 条记录</span><div class="pagination"><button class="page-btn">上一页</button><button class="page-btn active">1</button><button class="page-btn">2</button><button class="page-btn">3</button><button class="page-btn">下一页</button></div></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";

// NOTE: options cast to `any` so vue-tsc does not reject injected members
// (openModal/showToast) in the template — the prototype's inject declarations
// are kept verbatim.
export default defineComponent({
  name: "ReviewTasksPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { SummaryCards },
  inject: ["openModal", "showToast"],
} as any);
</script>
