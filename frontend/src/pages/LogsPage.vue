<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>日志管理</h1><p>统一查看平台操作、规则执行与推送任务日志</p></div><button class="btn primary" @click="showToast('日志已模拟导出')">导出日志</button></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="log-tabs"><button class="log-tab" :class="{ active: activeLogTab === 'operation' }" @click="activeLogTab = 'operation'">操作日志</button><button class="log-tab" :class="{ active: activeLogTab === 'rule' }" @click="activeLogTab = 'rule'">规则日志</button><button class="log-tab" :class="{ active: activeLogTab === 'push' }" @click="activeLogTab = 'push'">推送日志</button></div>

      <template v-if="activeLogTab === 'operation'">
        <div class="page-actions"><div class="left"><input class="input" style="width:230px;" placeholder="搜索用户、模块、对象" /><select class="select" style="width:140px;"><option>全部结果</option><option>成功</option><option>失败</option></select><input class="input" style="width:150px;" value="2026-07-17" /></div><div class="right"><button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button><button class="btn">重置</button></div></div>
        <table class="prototype-table">
          <colgroup><col style="width:158px;" /><col style="width:92px;" /><col style="width:118px;" /><col style="width:112px;" /><col /><col style="width:76px;" /><col style="width:120px;" /><col style="width:100px;" /></colgroup>
          <thead><tr><th>时间</th><th>用户</th><th>模块</th><th>操作</th><th class="left">对象</th><th>结果</th><th>IP</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="row in store.logRows" :key="row.time + row.action">
              <td>{{ row.time }}</td><td>{{ row.user }}</td><td>{{ row.module }}</td><td>{{ row.action }}</td><td class="left ellipsis">{{ row.target }}</td><td><span class="status-pill" :class="statusClass(row.result)">{{ row.result }}</span></td><td>{{ row.ip }}</td><td><button class="link-blue" @click="showToast('日志详情已模拟打开')">详情</button></td>
            </tr>
          </tbody>
        </table>
        <div class="table-footer"><span>显示 1-{{ store.logRows.length }} 共 {{ store.logRows.length }} 条记录</span><div class="pagination"><button class="page-btn">上一页</button><button class="page-btn active">1</button><button class="page-btn">下一页</button></div></div>
      </template>

      <template v-if="activeLogTab === 'rule'">
        <div class="log-filter-grid">
          <select class="select"><option>事件类型</option><option>车辆违停</option><option>抽烟</option></select>
          <input class="input" placeholder="规则名称" />
          <select class="select"><option>设备名称</option><option>室外-B1北侧道路2</option><option>A1-1郡-室外#01</option></select>
          <select class="select"><option>规则类型</option><option>实时重复图像去重</option><option>时间维度去重</option></select>
          <select class="select"><option>执行状态</option><option>执行成功</option><option>执行失败</option></select>
          <button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button><button class="btn">重置</button>
        </div>
        <table class="prototype-table">
          <colgroup><col style="width:170px;" /><col style="width:160px;" /><col style="width:160px;" /><col style="width:170px;" /><col style="width:100px;" /><col style="width:92px;" /><col style="width:150px;" /><col style="width:90px;" /></colgroup>
          <thead><tr><th class="left">设备名称</th><th class="left">规则名称</th><th>算法类型</th><th>规则类型</th><th>执行状态</th><th>过滤数量</th><th>执行时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="row in store.ruleLogRows" :key="row.time + row.device">
              <td class="left">{{ row.device }}</td><td class="left">{{ row.rule }}</td><td>{{ row.algorithm }}</td><td>{{ row.type }}</td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td><td>{{ row.count }}</td><td>{{ row.time }}</td><td><button class="link-blue" @click="showToast('规则执行详情已模拟打开')">详情</button></td>
            </tr>
          </tbody>
        </table>
        <div class="table-footer"><span>显示 1-{{ store.ruleLogRows.length }} 共 {{ store.ruleLogRows.length }} 条记录</span><div class="pagination"><button class="page-btn">上一页</button><button class="page-btn active">1</button><button class="page-btn">2</button><button class="page-btn">下一页</button></div></div>
      </template>

      <template v-if="activeLogTab === 'push'">
        <div class="log-tabs"><button class="log-tab" :class="{ active: activePushView === 'latest' }" @click="activePushView = 'latest'">最新推送</button><button class="log-tab" :class="{ active: activePushView === 'history' }" @click="activePushView = 'history'">历史推送</button></div>
        <template v-if="activePushView === 'latest'">
          <dl class="push-latest">
            <dt>推送任务名称：</dt><dd>公交车数据推送任务</dd>
            <dt>最新推送时间：</dt><dd>--</dd>
            <dt>推送结果：</dt><dd>--</dd>
            <dt>推送内容：</dt><dd><button class="link-blue" style="float:right;" @click="showToast('示例已模拟复制')">复制示例</button><pre class="json-preview">{{ store.pushPayload }}</pre></dd>
          </dl>
        </template>
        <template v-else>
          <div class="page-actions"><div class="left"><select class="select" style="width:180px;"><option>推送结果</option><option>成功</option><option>失败</option></select><input class="input" style="width:180px;" placeholder="开始日期" /><input class="input" style="width:180px;" placeholder="结束日期" /></div><div class="right"><button class="btn primary" @click="showToast('已根据当前条件刷新演示结果')">查询</button></div></div>
          <table class="prototype-table">
            <colgroup><col style="width:70px;" /><col style="width:190px;" /><col style="width:100px;" /><col style="width:180px;" /><col /><col style="width:150px;" /></colgroup>
            <thead><tr><th>序号</th><th class="left">推送任务名称</th><th>推送结果</th><th class="left">失败信息</th><th class="left">推送内容</th><th>推送时间</th></tr></thead>
            <tbody>
              <tr v-for="row in store.pushLogRows" :key="row.id">
                <td>{{ row.id }}</td><td class="left">{{ row.task }}</td><td><span class="status-pill" :class="statusClass(row.result)">{{ row.result }}</span></td><td class="left">{{ row.error }}</td><td class="left ellipsis">{{ row.content }}</td><td>{{ row.time }}</td>
              </tr>
            </tbody>
          </table>
          <div class="table-footer"><span>显示 1-{{ store.pushLogRows.length }} 共 {{ store.pushLogRows.length }} 条记录</span><div class="pagination"><button class="page-btn">上一页</button><button class="page-btn active">1</button><button class="page-btn">下一页</button></div></div>
        </template>
      </template>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";

// Template calls injected members bare; declare them so vue-tsc accepts that.
declare module "vue" {
  interface ComponentCustomProperties {
    showToast: (message: string) => void;
  }
}

export default defineComponent({
  name: "LogsPage",
  components: { SummaryCards },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  data() {
    return { activeLogTab: "operation", activePushView: "latest" };
  },
  computed: {
    cards(): any[] {
      const allCount = this.store.logRows.length + this.store.ruleLogRows.length + this.store.pushLogRows.length;
      const successCount = this.store.logRows.filter((row: any) => row.result === "成功").length + this.store.ruleLogRows.filter((row: any) => row.status === "执行成功").length + this.store.pushLogRows.filter((row: any) => row.result === "成功").length;
      const failCount = this.store.logRows.filter((row: any) => row.result === "失败").length + this.store.ruleLogRows.filter((row: any) => row.status === "执行失败").length + this.store.pushLogRows.filter((row: any) => row.result === "失败").length;
      return [
        { label: "日志总数", value: allCount },
        { label: "执行成功", value: successCount },
        { label: "执行失败", value: failCount },
        { label: "日志类型", value: 3 }
      ];
    }
  }
});
</script>
