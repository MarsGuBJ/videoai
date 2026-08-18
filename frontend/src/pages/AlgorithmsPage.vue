<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";

export default defineComponent({
  name: "AlgorithmsPage",
  components: { SummaryCards },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  // Aliased injection + same-named method wrappers (see ImageResults.vue note);
  // matches the prototype's `inject: ["openModal", "openVersionManager", "showToast"]`.
  inject: {
    openModalImpl: { from: "openModal" },
    openVersionManagerImpl: { from: "openVersionManager" },
    showToastImpl: { from: "showToast" }
  },
  methods: {
    openModal(key: string) {
      (this as any).openModalImpl(key);
    },
    openVersionManager(row: any) {
      (this as any).openVersionManagerImpl(row);
    },
    showToast(m: string) {
      (this as any).showToastImpl(m);
    }
  },
  computed: {
    cards(): any[] {
      return [
        { label: "算法总数", value: (this as any).store.algorithmManageRows.length },
        { label: "运行中", value: (this as any).store.algorithmManageRows.filter((row: any) => row.status === "运行中").length },
        { label: "待发布", value: (this as any).store.algorithmManageRows.filter((row: any) => row.status === "待发布").length },
        { label: "已停用", value: (this as any).store.algorithmManageRows.filter((row: any) => row.status === "已停用").length }
      ];
    }
  }
});
</script>

<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>算法管理</h1><p>维护算法基础信息、运行状态与当前版本</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions">
        <div class="left"><button class="btn primary" @click="openModal('algorithm')">新增算法</button><button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button><button class="btn">重置</button><input class="input" style="width:260px;" placeholder="搜索算法名称、算法编码" /><select class="select" style="width:150px;"><option>全部状态</option><option>运行中</option><option>待发布</option><option>已停用</option></select><select class="select" style="width:170px;"><option>全部场景</option><option>园区周界</option><option>停车场/道路</option><option>仓储/楼宇</option></select></div>
      </div>
      <table class="prototype-table">
        <colgroup><col style="width:110px;" /><col style="width:150px;" /><col style="width:165px;" /><col style="width:120px;" /><col style="width:80px;" /><col style="width:80px;" /><col style="width:80px;" /><col style="width:150px;" /><col style="width:170px;" /></colgroup>
        <thead><tr><th>算法ID</th><th class="left">算法名称</th><th class="left">算法编码</th><th>应用场景</th><th>当前版本</th><th>状态</th><th>创建人</th><th>更新时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in store.algorithmManageRows" :key="row.id">
            <td>{{ row.id }}</td><td class="left">{{ row.name }}</td><td class="left">{{ row.code }}</td><td>{{ row.scene }}</td><td><button class="link-blue" @click="openVersionManager(row)">{{ row.version }}</button></td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td><td>{{ row.owner }}</td><td>{{ row.updated }}</td>
            <td><button class="link-blue" @click="openVersionManager(row)">版本号</button><button class="link-blue" @click="openModal('algorithm')">编辑</button><button class="link-red" @click="showToast('已模拟停用该算法')">停用</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
