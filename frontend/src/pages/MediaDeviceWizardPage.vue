<template>
  <section class="content review-wide">
    <div class="review-titlebar">
      <div><h1>新增设备</h1><p>按设备类型、接入协议和通道信息完成编码设备接入</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('media')">返回设备管理</button></div>
    </div>
    <div class="media-resource-tabs" style="max-width:860px;">
      <button :class="{ active: wizardStep === 1 }" @click="wizardStep = 1"><span class="step-badge">1</span> 选择设备类型</button>
      <button :class="{ active: wizardStep === 2 }" @click="wizardStep = 2"><span class="step-badge">2</span> 配置基本信息</button>
      <button :class="{ active: wizardStep === 3 }" @click="wizardStep = 3"><span class="step-badge">3</span> 配置通道信息</button>
    </div>
    <div v-if="wizardStep === 1" class="panel form-panel">
      <h3 class="form-section-title">设备类型</h3>
      <div class="wide-field-row"><label>设备类别：</label><select class="select"><option>编码设备</option><option>解码设备</option></select></div>
      <div class="wide-field-row"><label>设备类型：</label><select class="select"><option>IPC</option><option>NVR</option><option>DVR</option><option>平台级联网设备</option></select></div>
      <div class="wide-field-row"><label>厂商类型：</label><select class="select"><option>海康威视</option><option>大华</option><option>宇视</option><option>华为</option><option>其他厂商</option></select></div>
      <div class="button-row"><button class="btn primary" @click="wizardStep = 2">下一步</button><button class="btn" @click="setRoute('media')">取消</button></div>
    </div>
    <div v-else-if="wizardStep === 2" class="panel form-panel" style="width:min(960px,100%);">
      <div class="modal-summary-strip"><span>设备类别：编码设备</span><span>设备类型：IPC</span><span>厂商类型：海康威视</span></div>
      <h3 class="form-section-title">基本信息</h3>
      <div class="form-grid-2">
        <div class="wide-field-row"><label>接入方式：</label><select class="select"><option>海康 SDK</option><option>GB28181</option><option>ONVIF</option><option>Ehome / ISUP 5.0</option><option>大华 SDK</option><option>RTSP 拉流</option><option>RTMP 推流</option><option>HTTP 拉流</option><option>GA/T 1400</option></select></div>
        <div class="wide-field-row"><label>协议版本：</label><select class="select"><option>标准协议</option><option>海康 ISUP 5.0</option><option>GB/T 28181-2022</option><option>ONVIF Profile S</option></select></div>
        <div class="wide-field-row"><label>设备名称：</label><input class="input" value="A1栋入口 IPC-01" /></div>
        <div class="wide-field-row"><label>设备编号：</label><input class="input" value="100000000000000001" /></div>
        <div class="wide-field-row"><label>IP地址：</label><input class="input" value="192.168.96.70" /></div>
        <div class="wide-field-row"><label>端口号：</label><input class="input" value="8000" /></div>
        <div class="wide-field-row"><label>用户名：</label><input class="input" value="admin" /></div>
        <div class="wide-field-row"><label>密码：</label><input class="input" type="password" value="12345678" /></div>
        <div class="wide-field-row"><label>所属区域：</label><select class="select"><option>园区总部 / A区 / A1栋</option><option>园区总部 / A区 / A2栋</option><option>园区总部 / B区 / B1栋</option><option>园区总部 / 停车场</option></select></div>
        <div class="wide-field-row"><label>设备能力：</label><span style="display:flex;gap:16px;flex-wrap:wrap;align-self:center;"><label class="video-device-include"><input type="checkbox" checked />视频</label><label class="video-device-include"><input type="checkbox" checked />音频</label><label class="video-device-include"><input type="checkbox" checked />云台</label><label class="video-device-include"><input type="checkbox" />对讲</label><label class="video-device-include"><input type="checkbox" />警告输入输出</label></span></div>
      </div>
      <div class="wide-field-row"><label>描述：</label><textarea class="textarea" style="height:80px;">主入口枪机，纳入园区安防实时预览与告警联动。</textarea></div>
      <h3 class="form-section-title">高级配置</h3>
      <div class="form-grid-2">
        <div class="wide-field-row"><label>拉流地址：</label><input class="input" placeholder="rtsp://user:pass@ip:port/stream" /></div>
        <div class="wide-field-row"><label>注册有效期：</label><input class="input" value="3600" /></div>
        <div class="wide-field-row"><label>心跳周期：</label><input class="input" value="60" /></div>
        <div class="wide-field-row"><label>国标域编码：</label><input class="input" placeholder="请输入 20 位国标编码" /></div>
      </div>
      <div class="button-row"><button class="btn" @click="wizardStep = 1">上一步</button><button class="btn primary" @click="wizardStep = 3">下一步</button><button class="btn" @click="setRoute('media')">取消</button></div>
    </div>
    <div v-else class="panel" style="padding:18px 22px;">
      <div class="video-device-filter" style="margin-bottom:12px;">
        <label>设备名称<input class="input" value="A1栋入口 IPC-01" /></label>
        <label class="video-device-include" style="align-self:end;padding-bottom:6px;"><input type="checkbox" checked />自动获取通道</label>
        <button class="btn" @click="showToast('已模拟自动探测设备通道')">自动探测通道</button>
        <button class="btn primary" @click="showToast('全部通道已模拟启用')">全部启用</button>
      </div>
      <div class="modal-table-wrap">
        <table class="prototype-table" style="min-width:1080px;">
          <thead><tr><th>通道号</th><th>通道名称</th><th>编码类型</th><th>通道编码</th><th>码流</th><th>水平视角</th><th>云台方向</th><th>通道能力</th><th>智能分析</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            <tr><td>1</td><td><input class="input" value="A1栋入口通道" /></td><td><select class="select"><option>主码流</option><option>子码流</option></select></td><td><input class="input" value="CH-0001" /></td><td><select class="select"><option>H.265</option><option>H.264</option></select></td><td><input class="input" value="90" /></td><td><select class="select"><option>固定</option><option>云台</option></select></td><td><select class="select"><option>视频/音频</option><option>视频</option></select></td><td><span class="status-pill enabled">启用</span></td><td><span class="status-pill pass">在线</span></td><td><button class="link-red" @click="showToast('通道已模拟删除')">删除</button></td></tr>
            <tr><td>2</td><td><input class="input" value="A1栋门禁联动" /></td><td><select class="select"><option>子码流</option><option>主码流</option></select></td><td><input class="input" value="CH-0002" /></td><td><select class="select"><option>H.264</option><option>H.265</option></select></td><td><input class="input" value="120" /></td><td><select class="select"><option>云台</option><option>固定</option></select></td><td><select class="select"><option>视频/云台</option><option>视频</option></select></td><td><span class="status-pill">停用</span></td><td><span class="status-pill reject">离线</span></td><td><button class="link-red" @click="showToast('通道已模拟删除')">删除</button></td></tr>
          </tbody>
        </table>
      </div>
      <div class="button-row" style="margin-top:14px;"><button class="btn" @click="wizardStep = 2">上一步</button><button class="btn primary" @click="finishWizard">保存</button><button class="btn" @click="setRoute('media')">取消</button></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "MediaDeviceWizardPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  // Aliased injection + same-named method wrappers so the template type-checks;
  // runtime behavior matches the prototype's `inject: ["setRoute", "showToast"]`.
  inject: {
    setRouteImpl: { from: "setRoute" },
    showToastImpl: { from: "showToast" }
  },
  data() {
    return { wizardStep: 1 };
  },
  methods: {
    setRoute(route: string, options?: any) {
      (this as any).setRouteImpl(route, options);
    },
    showToast(msg: string) {
      (this as any).showToastImpl(msg);
    },
    finishWizard() {
      this.showToast("新设备已保存，已加入设备管理列表");
      this.setRoute("media");
    }
  }
});
</script>
