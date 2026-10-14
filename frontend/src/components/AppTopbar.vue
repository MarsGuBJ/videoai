<script lang="ts">
import { defineComponent } from "vue";
import { withAppBase } from "../utils/appBase.ts";

export default defineComponent({
  props: ["route", "names"],
  computed: {
    portraitUrl(): string {
      return withAppBase("prototype/portrait.jpg");
    }
  }
});
</script>

<template>
  <header class="topbar">
    <div class="top-left">
      <span class="breadcrumb">首页 / <b>{{ names[route] || "万物搜主页" }}</b></span>
    </div>
    <div class="top-user">
      <span class="notice">铃</span>
      <img class="avatar" alt="管理员头像" :src="portraitUrl" />
      <span>管理员⌄</span>
    </div>
  </header>
</template>
