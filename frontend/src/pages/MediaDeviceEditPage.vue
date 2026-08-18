<template>
  <section class="content review-wide">
    <div class="review-titlebar">
      <div><h1>编辑设备</h1><p>维护设备基础参数、接入协议与所属区域</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('mediaDeviceDetail')">返回设备详情</button></div>
    </div>
    <div class="panel form-panel" style="width:min(960px,100%);">
      <h3 class="form-section-title">基础参数</h3>
      <div class="form-grid-2">
        <div class="wide-field-row"><label>设备名称：</label><input class="input" value="A1栋入口 IPC-01" /></div>
        <div class="wide-field-row"><label>设备编号：</label><input class="input" value="100000000000000001" /></div>
        <div class="wide-field-row"><label>接入协议：</label><select class="select"><option>海康 SDK</option><option>GB28181</option><option>ONVIF</option><option>大华 SDK</option><option>RTSP 拉流</option></select></div>
        <div class="wide-field-row"><label>IP地址：</label><input class="input" value="192.168.96.70" /></div>
        <div class="wide-field-row"><label>端口号：</label><input class="input" value="8000" /></div>
        <div class="wide-field-row"><label>所属区域：</label><select class="select"><option>园区总部 / A区 / A1栋</option><option>园区总部 / B区 / B1栋</option><option>园区总部 / 停车场</option></select></div>
        <div class="wide-field-row"><label>用户名：</label><input class="input" value="admin" /></div>
        <div class="wide-field-row"><label>密码：</label><input class="input" type="password" placeholder="留空则不修改密码" /></div>
        <div class="wide-field-row"><label>设备能力：</label><span style="display:flex;gap:16px;flex-wrap:wrap;align-self:center;"><label class="video-device-include"><input type="checkbox" checked />视频</label><label class="video-device-include"><input type="checkbox" checked />音频</label><label class="video-device-include"><input type="checkbox" checked />云台</label><label class="video-device-include"><input type="checkbox" />对讲</label><label class="video-device-include"><input type="checkbox" />警告输入输出</label></span></div>
      </div>
      <div class="wide-field-row"><label>描述：</label><textarea class="textarea" style="height:80px;">主入口枪机，支持音频、云台和告警联动。</textarea></div>
      <div class="button-row"><button class="btn primary" @click="saveDevice">保存修改</button><button class="btn" @click="setRoute('mediaDeviceDetail')">取消</button></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "MediaDeviceEditPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (r: string, o?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  methods: {
    saveDevice() {
      (this as any).showToast("设备信息已保存");
      (this as any).setRoute("mediaDeviceDetail");
    }
  }
});
</script>
