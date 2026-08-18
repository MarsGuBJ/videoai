<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>复核类型管理</h1><p>维护用于人工复核和大模型判断的算法类型</p></div></div>
    <div class="review-board">
      <div class="algorithm-toolbar"><button class="btn primary" @click="openModal('reviewType')">新建</button></div>
      <table class="prototype-table">
        <colgroup><col style="width:48px;" /><col style="width:170px;" /><col style="width:210px;" /><col /><col style="width:110px;" /><col style="width:125px;" /><col style="width:150px;" /><col style="width:100px;" /></colgroup>
        <thead><tr><th>ID</th><th class="left">算法名称</th><th class="left">算法编码</th><th class="left">提示词</th><th class="left">备注</th><th>注入事件字段</th><th>更新时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in store.algorithmRows" :key="row.id">
            <td>{{ row.id }}</td><td class="left">{{ row.name }}</td><td class="left">{{ row.code }}</td><td class="left ellipsis">{{ row.prompt }}</td><td class="left ellipsis">{{ row.remark }}</td><td><span v-if="row.fields !== '-'" class="mini-tag">{{ row.fields }}</span><span v-else>-</span></td><td>{{ row.updated }}</td>
            <td><button class="link-blue" @click="openModal('reviewType')">编辑</button><button class="link-red" @click="showToast('已模拟删除该算法')">删除</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "ReviewTypesPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    injectedOpenModal: { from: "openModal", default: (key: string) => {} },
    injectedShowToast: { from: "showToast", default: (m: string) => {} },
  },
  methods: {
    openModal(key: string) {
      (this as any).injectedOpenModal(key);
    },
    showToast(m: string) {
      (this as any).injectedShowToast(m);
    },
  },
});
</script>
