<template>
  <section class="content wide">
    <div class="title-row"><span class="module-icon">▣</span><div><h1 class="page-title">快速布防</h1><p class="page-subtitle">快速部署智能布防任务</p></div></div>
    <div class="panel deploy-panel">
      <h3 class="form-section-title"><span style="color:var(--blue)">✥</span> 布防目标设定</h3>
      <div class="form-split">
        <button class="upload-card" @click="showToast('静态原型：此处模拟上传入口')"><img v-if="state.prefill" :src="state.prefill" alt="布防目标" /><span v-else><span class="upload-mark">＋</span><br />上传目标图片</span></button>
        <div><label class="field-label" style="padding-top:0; display:block; margin-bottom:8px;">目标描述</label><textarea class="textarea" style="height:60px;">请输入目标特征描述，如：身穿蓝色工服、身高约175cm、戴眼镜的中年男性...</textarea></div>
      </div>
      <div class="hr"></div>
      <h3 class="form-section-title"><span style="color:var(--blue)">⌖</span> 布防范围和时间</h3>
      <div class="deploy-grid">
        <div class="deploy-field"><label>监控点位</label><input class="input" value="全部点位" /></div>
        <div class="deploy-field"><label>区域选择</label><input class="input" value="全部区域" /></div>
        <div class="deploy-field"><label>生效时间</label><div class="effective-row"><button class="btn ghost">立即生效</button><button class="btn">定时生效</button><button class="btn">永久有效</button></div></div>
        <div class="deploy-field"><label>相似度阈值</label><div class="effective-row"><span>相似度</span><input class="input" style="width:60px;" value="85" /><span>%</span></div></div>
      </div>
      <div class="submit-line"><button class="btn" @click="setRoute('home')">取消</button><button class="btn primary" @click="showToast('布防任务已提交，可进入万物核复核')">✓ 提交布防</button></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

// The prototype accesses injected members (setRoute/showToast) directly in the
// template; vue-tsc does not infer inject keys onto the template `this`, so
// merge them into ComponentCustomProperties (type-level only, runtime inject
// declarations below stay exactly as the prototype).
declare module "vue" {
  interface ComponentCustomProperties {
    setRoute: (route: string, options?: any) => void;
    showToast: (m: string) => void;
  }
}

export default defineComponent({
  name: "QuickDeployPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
  },
});
</script>
