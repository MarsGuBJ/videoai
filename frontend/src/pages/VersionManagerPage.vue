<template>
  <section class="content review-wide">
    <div class="review-titlebar">
      <div><h1>{{ titleText }}</h1><p>版本号管理作为算法管理二级页面，从算法列表的版本号入口进入</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('algorithms')">返回算法管理</button><button class="btn primary" @click="openModal('version')">新增版本号</button></div>
    </div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions"><div class="left"><input class="input" style="width:260px;" placeholder="搜索版本号、版本名称" /><select class="select" style="width:150px;"><option>全部状态</option><option>已发布</option><option>待发布</option><option>测试中</option></select></div><div class="right"><button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button><button class="btn">重置</button></div></div>
      <table class="prototype-table">
        <colgroup><col style="width:120px;" /><col style="width:170px;" /><col style="width:90px;" /><col style="width:170px;" /><col style="width:90px;" /><col /><col style="width:90px;" /><col style="width:150px;" /><col style="width:160px;" /></colgroup>
        <thead><tr><th>版本ID</th><th class="left">算法名称</th><th>版本号</th><th class="left">版本名称</th><th>状态</th><th class="left">版本文件</th><th>创建人</th><th>创建时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ row.id }}</td><td class="left">{{ row.algorithm }}</td><td><span class="mini-tag">{{ row.version }}</span></td><td class="left">{{ row.name }}</td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td><td class="left ellipsis">{{ row.file }}</td><td>{{ row.creator }}</td><td>{{ row.created }}</td>
            <td><button class="link-blue" @click="openVersionDetail(row)">详情</button><button class="link-blue" @click="openVersionPreview(row)">预览</button><button class="link-blue" @click="showToast('版本已发布，状态已模拟更新')">发布</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";

// Template calls these injected members bare; declare them so vue-tsc accepts
// that (runtime inject declarations below stay as in the prototype).
declare module "vue" {
  interface ComponentCustomProperties {
    openVersionDetail: (row: any) => void;
    openVersionPreview: (row: any) => void;
  }
}

export default defineComponent({
  name: "VersionManagerPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { SummaryCards },
  inject: {
    openModal: { from: "openModal", default: (key: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    openVersionDetail: { from: "openVersionDetail", default: (row: any) => {} },
    openVersionPreview: { from: "openVersionPreview", default: (row: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  computed: {
    rows(): any[] {
      if (!(this as any).selectedAlgorithm) return (this as any).store.versionRows;
      return (this as any).store.versionRows.filter((row: any) => row.algorithm === (this as any).selectedAlgorithm.name);
    },
    titleText(): string {
      return (this as any).selectedAlgorithm ? `${(this as any).selectedAlgorithm.name} 版本号管理` : "版本号管理";
    },
    cards(): any[] {
      const rows = this.rows;
      return [
        { label: "版本总数", value: rows.length },
        { label: "已发布", value: rows.filter(row => row.status === "已发布").length },
        { label: "待发布", value: rows.filter(row => row.status === "待发布").length },
        { label: "测试中", value: rows.filter(row => row.status === "测试中").length }
      ];
    }
  }
});
</script>
