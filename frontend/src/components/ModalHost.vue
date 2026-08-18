<script lang="ts">
import { statusClass } from "../utils/prototype-helpers";

export default {
  name: "ModalHost",
  props: ["modal", "store", "state"],
  emits: ["close", "submit"],
  // Aliased injection + same-named method wrapper for `showToast` (used in the
  // template, which is type-checked); runtime behavior matches the prototype's
  // `inject: ["showToast", "setRoute"]`. `setRoute` is only used in script.
  inject: {
    toastImpl: { from: "showToast" },
    setRoute: { from: "setRoute" }
  },
  data() {
    return {
      deployEffectiveDate: "",
      deployEffectiveEndDate: "",
      deployCycleStartTime: "00:00",
      deployCycleEndTime: "23:59",
      deploySimilarity: 50,
      deployTargetUrl: "",
      deployTargetName: "",
      deployAlgorithm: "",
      modelTimeout: 30,
      modelConcurrency: 5,
      modelTemperature: 0.7,
      modelMaxTokens: 2048,
      modelFps: 1,
      smartPrompt: "",
      smartMessages: [{ role: "assistant", text: "你好，我是设备管理智能助手。你可以告诉我需要搜索、添加或更新哪些设备。" }]
    };
  },
  computed: {
    deployTargetSource() {
      return this.deployTargetUrl || (this.state && this.state.prefill) || "";
    },
    deployAlgorithmOptions() {
      if (this.deployTargetSource) return ["人员布控", "车辆布控"];
      return this.store.algorithmManageRows
        .map((row: any) => row.name)
        .filter((name: string) => name !== "人员布控" && name !== "车辆布控");
    },
    imageCropStyle() {
      const crop = this.state && this.state.imageCrop ? this.state.imageCrop : { x: 0, y: 0, width: 0, height: 0 };
      return {
        left: `${crop.x}%`,
        top: `${crop.y}%`,
        width: `${crop.width}%`,
        height: `${crop.height}%`
      };
    },
    submitLabel() {
      const labels: any = {
        reviewTask: "确定",
        mediaExport: "导出",
        mediaMove: "确认移动",
        mediaCapability: "批量保存",
        mediaDelete: "确认删除",
        customLayout: "保存布局",
        patrolPlan: "确定",
        segmentPlayback: "开始分段回放",
        recordDownload: "下载",
        keyboardAccess: "保存并接入",
        wallPreview: "保存配置",
        linkageRule: "保存规则"
      };
      return labels[this.modal.type] || "保存";
    }
  },
  watch: {
    deployTargetSource() {
      this.deployAlgorithm = "";
    },
    "modal.open"(open: boolean) {
      if (!open) {
        this.resetDeployTargetUpload();
        this.deployAlgorithm = "";
      } else if (this.modal.type === "mediaSmartDiscover") {
        this.smartPrompt = "";
        this.smartMessages = [{ role: "assistant", text: "你好，我是设备管理智能助手。你可以告诉我需要搜索、添加或更新哪些设备。" }];
      }
    }
  },
  methods: {
    statusClass,
    showToast(message: string) {
      (this as any).toastImpl(message);
    },
    resetDeployTargetUpload() {
      if (this.deployTargetUrl) URL.revokeObjectURL(this.deployTargetUrl);
      this.deployTargetUrl = "";
      this.deployTargetName = "";
      const input: any = this.$refs.deployTargetInput;
      if (input) input.value = "";
    },
    triggerDeployTargetUpload() {
      const input: any = this.$refs.deployTargetInput;
      if (input) input.click();
    },
    handleDeployTargetUpload(event: any) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        this.showToast("请选择图片文件");
        event.target.value = "";
        return;
      }
      if (this.deployTargetUrl) URL.revokeObjectURL(this.deployTargetUrl);
      this.deployTargetUrl = URL.createObjectURL(file);
      this.deployTargetName = file.name;
      this.showToast("布控目标已添加");
    },
    clearDeployTarget() {
      this.resetDeployTargetUpload();
      if (this.state) {
        this.state.prefill = "";
        this.state.imageCrop = null;
      }
      this.showToast("布控目标已清空");
    },
    goPlayback() {
      this.$emit("close");
      this.setRoute("mediaPlayback");
    },
    submitSmartPrompt(prompt = this.smartPrompt) {
      const text = String(prompt || "").trim();
      if (!text) return;
      this.smartMessages.push({ role: "user", text });
      this.smartPrompt = "";
      const lower = text.toLowerCase();
      let response = "已理解你的请求。请补充设备名称、IP 地址或所在区域，我会继续处理。";
      if (text.includes("添加") || text.includes("新增")) {
        response = "已识别为添加设备请求，正在生成接入配置：设备名称、协议、IP、端口和所属区域均可继续补充，确认后将加入设备管理列表。";
      } else if (text.includes("更新") || text.includes("修改")) {
        response = "已识别为更新设备请求，已定位相关设备并准备更新其连接信息。确认后会保留原有通道和告警联动关系。";
      } else if (text.includes("搜索") || text.includes("查找") || text.includes("发现") || lower.includes("scan")) {
        response = "已开始搜索设备，发现 3 台可接入设备：北门卡口 IPC-07、A3 栋电梯 IPC-06、停车场 NVR-01。你可以继续说“添加它们”或指定设备更新。";
      }
      this.smartMessages.push({ role: "assistant", text: response });
    },
    useSmartPrompt(prompt: string) {
      this.smartPrompt = prompt;
      this.submitSmartPrompt(prompt);
    }
  },
  beforeUnmount() {
    this.resetDeployTargetUpload();
  }
};
</script>

<template>
  <div class="modal-mask" :class="{ open: modal.open }" :aria-hidden="modal.open ? 'false' : 'true'" @click.self="$emit('close')">
    <section class="modal-dialog" :class="[{ narrow: modal.narrow }, { wide: modal.wide }, { 'event-detail-dialog': modal.type === 'eventDetail' }]" aria-label="弹窗表单">
      <div class="modal-head">
        <h3>{{ modal.title }}</h3>
        <button class="modal-close" aria-label="关闭" @click="$emit('close')">×</button>
      </div>
      <div class="modal-body">
        <template v-if="modal.type === 'reviewTask'">
          <div class="modal-form-row">
            <label><span class="required">*</span>事件编码：</label>
            <select class="select"><option>请选择事件编码</option><option>PERSON_INTRUSION</option><option>PARKING</option><option>SMOKE_FIRE_DETECTION</option></select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>图片：</label>
            <div>
              <button class="modal-upload"><span><span class="plus">＋</span>上传</span></button>
            </div>
          </div>
          <div class="modal-form-row">
            <label>视频：</label>
            <div>
              <button class="modal-upload"><span><span class="plus">＋</span>上传</span></button>
            </div>
          </div>
        </template>
        <template v-if="modal.type === 'eventDetail' && modal.item">
          <div class="event-detail-grid">
            <dl class="event-detail-field"><dt>事件有效</dt><dd :class="modal.item.timeValid === '有效' ? 'text-success' : 'text-danger'">{{ modal.item.timeValid === '有效' ? '是' : '否' }}</dd></dl>
            <dl class="event-detail-field"><dt>事件地点</dt><dd>{{ modal.item.location }}</dd></dl>
            <dl class="event-detail-field"><dt>事件时间</dt><dd>{{ modal.item.created }}</dd></dl>
            <dl class="event-detail-field"><dt>任务状态</dt><dd><span class="status-pill" :class="statusClass(modal.item.executionStatus)">{{ modal.item.executionStatus }}</span></dd></dl>
            <dl class="event-detail-field"><dt>任务执行时长</dt><dd>{{ modal.item.duration }}</dd></dl>
          </div>
          <div class="event-detail-section">
            <h4>研判原因</h4>
            <p>{{ modal.item.reason }}</p>
          </div>
          <div class="event-detail-section">
            <h4>证据信息</h4>
            <pre class="event-detail-evidence">{{ modal.item.evidence }}</pre>
          </div>
          <div class="event-detail-section">
            <h4>事件图片</h4>
            <div class="event-detail-image"><img :src="modal.item.image" :alt="modal.item.type + '事件图片'" /><span class="event-detail-image-time">{{ modal.item.created }}</span></div>
          </div>
        </template>
        <template v-if="modal.type === 'reviewType'">
          <div class="modal-form-row">
            <label><span class="required">*</span>算法名称：</label>
            <input class="input" placeholder="请输入算法名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>提示词：</label>
            <textarea class="textarea" style="height:220px;" placeholder="请输入提示词">你是园区安防监控事件复检助手，请根据图片或视频片段判断是否存在目标事件，并输出结构化判断结果。</textarea>
          </div>
          <div class="modal-form-row">
            <label>注入事件：</label>
            <input class="input" placeholder="请输入注入事件字段" />
          </div>
          <div class="modal-form-row">
            <label>备注：</label>
            <textarea class="textarea" style="height:64px;" placeholder="请输入备注"></textarea>
          </div>
        </template>
        <template v-if="modal.type === 'algorithm'">
          <div class="modal-form-row">
            <label><span class="required">*</span>算法名称：</label>
            <input class="input" placeholder="请输入算法名称" value="人员入侵检测" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>算法类型：</label>
            <select class="select">
              <option>请选择算法类型</option>
              <option>图像识别</option>
              <option>视频检测</option>
              <option>目标跟踪</option>
              <option>事件判断</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>初始版本：</label>
            <input class="input" placeholder="请输入初始版本，如 v1.0.0" value="v1.0.0" />
          </div>
          <div class="modal-form-row">
            <label>版本说明：</label>
            <textarea class="textarea" style="height:82px;" placeholder="请输入版本说明">初始版本，支持基础场景识别。</textarea>
          </div>
          <div class="modal-form-row">
            <label>算法描述：</label>
            <textarea class="textarea" style="height:96px;" placeholder="请输入算法描述">用于检测特定人员、车辆或异常行为的算法，可在布控任务中选择使用。</textarea>
          </div>
        </template>
        <template v-if="modal.type === 'deployTask'">
          <div class="modal-form-row">
            <label><span class="required">*</span>任务名称：</label>
            <input class="input" value="人员布控-东门" placeholder="请输入任务名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>布控区域：</label>
            <select class="select">
              <option>请选择布控区域</option>
              <option>园区南门</option>
              <option>A座停车区</option>
              <option>仓储区</option>
              <option>园区周界</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label>布控目标：</label>
            <div class="deploy-target-field">
              <input ref="deployTargetInput" class="hidden-file-input" type="file" accept="image/*" @change="handleDeployTargetUpload" />
              <div v-if="deployTargetSource" class="deploy-target-preview">
                <img :src="deployTargetSource" :alt="deployTargetName || '已框选布控目标'" />
                <span v-if="!deployTargetUrl && state && state.imageCrop" class="transferred-crop-box" :style="imageCropStyle"></span>
              </div>
              <button v-else class="file-upload-tile" style="height:96px;" type="button" @click="triggerDeployTargetUpload"><span><b>＋ 点击上传布控图像</b><br />支持 jpg / png / jpeg</span></button>
              <button v-if="deployTargetSource" class="btn deploy-target-clear" type="button" @click="clearDeployTarget">清空</button>
            </div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>布控算法：</label>
            <select class="select" v-model="deployAlgorithm">
              <option value="">请选择布控算法</option>
              <option v-for="item in deployAlgorithmOptions" :key="item" :value="item">{{ item }}</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>生效时间：</label>
            <div class="effective-range">
              <input class="input" type="date" v-model="deployEffectiveDate" aria-label="生效开始日期" />
              <span class="range-arrow">→</span>
              <input class="input" type="date" v-model="deployEffectiveEndDate" aria-label="生效结束日期" />
            </div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>循环周期：</label>
            <div class="effective-range">
              <input class="input" type="time" v-model="deployCycleStartTime" aria-label="循环开始时间" />
              <span class="range-arrow">→</span>
              <input class="input" type="time" v-model="deployCycleEndTime" aria-label="循环结束时间" />
            </div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>置信度：</label>
            <div class="deploy-similarity-field">
              <input id="deploy-similarity" type="range" min="0" max="100" step="1" v-model.number="deploySimilarity" aria-label="置信度" />
              <output for="deploy-similarity">{{ deploySimilarity }}%</output>
            </div>
          </div>
          <div class="modal-form-row">
            <label>任务描述：</label>
            <textarea class="textarea" style="height:96px;" placeholder="请输入任务描述">请输入任务描述</textarea>
          </div>
        </template>
        <template v-if="modal.type === 'version'">
          <div class="modal-form-row">
            <label><span class="required">*</span>所属算法：</label>
            <select class="select">
              <option v-for="row in store.algorithmManageRows" :key="row.id">{{ row.name }}</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>版本号：</label>
            <input class="input" value="v3.1.0" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>版本名称：</label>
            <input class="input" placeholder="请输入版本名称" />
          </div>
          <div class="modal-form-row">
            <label>版本说明：</label>
            <textarea class="textarea" style="height:72px;" placeholder="请输入本次版本优化内容"></textarea>
          </div>
          <div class="modal-form-row">
            <label>版本文件：</label>
            <div class="version-upload-grid">
              <button class="file-upload-tile"><span><b>＋ 模型文件</b><br />onnx / pt / zip</span></button>
              <button class="file-upload-tile"><span><b>＋ 配置文件</b><br />json / yaml</span></button>
              <button class="file-upload-tile"><span><b>＋ 说明文档</b><br />md / pdf / doc</span></button>
            </div>
          </div>
        </template>
        <template v-if="modal.type === 'eventSource'">
          <div class="modal-form-row">
            <label><span class="required">*</span>数据源名称：</label>
            <input class="input" value="视频事件平台" placeholder="请输入数据源名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>接口地址：</label>
            <input class="input" value="video-event.platform.cn/api" placeholder="请输入接口地址" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>接入方式：</label>
            <select class="select"><option>主动拉取</option><option>被动接收</option><option>Webhook推送</option></select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>事件类型：</label>
            <input class="input" value="跌倒检测、聚集检测" placeholder="请输入事件类型，多个用顿号分隔" />
          </div>
          <div class="modal-form-row">
            <label>拉取频率：</label>
            <select class="select"><option>实时推送</option><option>每5分钟</option><option>每10分钟</option><option>每30分钟</option></select>
          </div>
          <div class="modal-form-row">
            <label>状态：</label>
            <select class="select"><option>运行中</option><option>停止</option><option>停止</option></select>
          </div>
          <div class="modal-form-row">
            <label>说明：</label>
            <textarea class="textarea" style="height:82px;" placeholder="请输入接入说明">聚合后的事件将作为原始事件，为后续去重、复核提供支撑。</textarea>
          </div>
        </template>
        <template v-if="modal.type === 'modelConfig'">
          <div class="model-config-section-title">基础配置</div>
          <div class="modal-form-row">
            <label><span class="required">*</span>模型名称：</label>
            <input class="input" value="通义千问-Max" placeholder="请输入模型名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>接口地址：</label>
            <input class="input" value="dashscope.aliyuncs.com/api/v1" placeholder="请输入接口地址" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>API Key：</label>
            <div class="model-api-field">
              <input class="input" value="sk-***************" placeholder="请输入API Key" />
              <button class="model-api-toggle" type="button" aria-label="显示或隐藏 API Key">&#xf06e;</button>
            </div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>部署方式：</label>
            <div class="model-config-radio-group">
              <label class="model-config-radio"><input type="radio" name="model-deploy-mode" checked />云端部署</label>
              <label class="model-config-radio"><input type="radio" name="model-deploy-mode" />本地部署</label>
            </div>
          </div>
          <div class="model-config-section-title">高级配置</div>
          <div class="modal-form-row">
            <label>超时时间（秒）：</label>
            <input class="input" type="number" min="10" max="120" v-model.number="modelTimeout" />
          </div>
          <p class="model-config-field-note">请求的最大等待时间，建议范围：10 - 120s</p>
          <div class="modal-form-row">
            <label>温度参数（Temperature）：</label>
            <div class="model-config-range">
              <input type="range" min="0" max="1" step="0.1" v-model.number="modelTemperature" />
              <output>{{ modelTemperature }}</output>
            </div>
          </div>
          <p class="model-config-field-note">控制输出的随机性：0 表示最稳定，1 表示最富创造力</p>
          <div class="modal-form-row">
            <label>最大输出长度（Tokens）：</label>
            <input class="input" type="number" min="1" v-model.number="modelMaxTokens" />
          </div>
          <p class="model-config-field-note">模型生成的最大 Token 数量</p>
          <div class="modal-form-row">
            <label>视频帧数（FPS）：</label>
            <input class="input" type="number" min="1" v-model.number="modelFps" />
          </div>
          <p class="model-config-field-note">视频理解任务中的采样帧率</p>
        </template>
        <template v-if="modal.type === 'permissionRole'">
          <div class="modal-form-row">
            <label><span class="required">*</span>角色名称：</label>
            <input class="input" value="安防运营" placeholder="请输入角色名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>角色编码：</label>
            <input class="input" value="SECURITY_OPERATOR" placeholder="请输入角色编码" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>数据范围：</label>
            <select class="select"><option>全部数据</option><option>安防中心</option><option>算法组</option><option>万物核</option><option>只读演示</option></select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>启用状态：</label>
            <select class="select"><option>启用</option><option>停用</option></select>
          </div>
          <div class="modal-form-row">
            <label>角色描述：</label>
            <textarea class="textarea" style="height:90px;" placeholder="请输入角色描述">负责万物搜、布控任务、事件处置和日志查看。</textarea>
          </div>
        </template>
        <template v-if="modal.type === 'mediaImport'">
          <div class="media-resource-tabs"><button class="active">模板导入</button><button @click="showToast('手动录入模式已模拟切换')">手动录入</button></div>
          <div class="modal-drop-zone">
            <strong>拖拽或选择文件上传</strong>
            <span>支持 .xlsx / .csv，字段包含设备名称、协议、IP、端口、区域、账号、密码、设备编号。</span>
          </div>
        </template>
        <template v-if="modal.type === 'mediaSmartDiscover'">
          <div class="exact-dialog-chat" style="margin-top:0;padding-top:0;border-top:0;">
            <div class="exact-dialog-chat-head"><strong>设备管理 AI 助手</strong><span>支持搜索、添加、更新设备</span></div>
            <div class="exact-chat-messages" style="max-height:280px;">
              <div v-for="(message, index) in smartMessages" :key="index" class="exact-chat-message" :class="message.role">{{ message.text }}</div>
            </div>
            <div class="exact-chat-quick">
              <button type="button" @click="useSmartPrompt('搜索园区内可接入的在线设备')">搜索在线设备</button>
              <button type="button" @click="useSmartPrompt('添加北门卡口 IPC-07')">添加北门卡口 IPC-07</button>
              <button type="button" @click="useSmartPrompt('更新所有离线设备的 IP 地址')">更新离线设备</button>
            </div>
            <div class="exact-chat-composer">
              <textarea class="textarea" v-model="smartPrompt" placeholder="请输入提示词，例如：搜索北门附近的摄像机，或更新 IPC-07 的端口"></textarea>
              <button class="btn primary" type="button" @click="submitSmartPrompt()">发送</button>
            </div>
          </div>
        </template>
        <template v-if="modal.type === 'mediaExport'">
          <div class="modal-form-row"><label>导出范围：</label><select class="select"><option>当前筛选结果</option><option>选中设备</option><option>全部设备</option></select></div>
          <div class="modal-form-row"><label>导出字段：</label><select class="select"><option>全部展示字段</option><option>基础信息</option><option>连接信息</option></select></div>
        </template>
        <template v-if="modal.type === 'mediaMove'">
          <p class="modal-hint">将已选择设备移动到其他区域，通道与告警联动关系保持不变。</p>
          <div class="modal-form-row"><label>目标区域：</label><select class="select"><option>园区总部 / A区 / A2栋</option><option>园区总部 / B区 / B1栋</option><option>园区总部 / 停车场</option></select></div>
        </template>
        <template v-if="modal.type === 'mediaCapability'">
          <div class="modal-check-grid">
            <label class="video-device-include"><input type="checkbox" checked />视频预览</label>
            <label class="video-device-include"><input type="checkbox" checked />音频采集</label>
            <label class="video-device-include"><input type="checkbox" />语音对讲</label>
            <label class="video-device-include"><input type="checkbox" checked />云台控制</label>
            <label class="video-device-include"><input type="checkbox" />智能分析</label>
            <label class="video-device-include"><input type="checkbox" />告警输入输出</label>
          </div>
          <div class="modal-form-row"><label>配置策略：</label><select class="select"><option>覆盖原能力配置</option><option>仅追加新增能力</option><option>仅应用到在线设备</option></select></div>
        </template>
        <template v-if="modal.type === 'mediaCloud'">
          <div class="modal-form-grid">
            <div class="modal-form-row"><label>云平台：</label><select class="select"><option>省级视频云平台</option><option>集团云平台</option><option>第三方安防云</option></select></div>
            <div class="modal-form-row"><label>同步范围：</label><select class="select"><option>全部授权设备</option><option>指定区域</option><option>最近新增设备</option></select></div>
            <div class="modal-form-row"><label>冲突处理：</label><select class="select"><option>保留本地配置，仅补充云端字段</option><option>云端覆盖本地</option><option>生成待确认清单</option></select></div>
            <div class="modal-form-row"><label>所属区域：</label><select class="select"><option>园区总部</option><option>园区总部 / A区</option><option>园区总部 / B区</option></select></div>
          </div>
          <div class="modal-summary-strip"><strong>预计同步</strong><span>新增 12 台，更新 8 台，冲突 2 台</span></div>
          <div class="modal-table-wrap">
            <table class="prototype-table">
              <thead><tr><th style="width:36px;"><input type="checkbox" checked aria-label="全选云端设备" /></th><th>设备名称</th><th>云端区域</th><th>接入协议</th><th>IP地址</th><th>同步到区域</th><th>处理方式</th></tr></thead>
              <tbody>
                <tr><td><input type="checkbox" checked /></td><td>云端-办公楼入口 IPC</td><td>办公楼 / 一层</td><td>GB28181</td><td>10.20.8.21</td><td><select class="select"><option>园区总部 / A区 / A1栋</option><option>园区总部 / A区 / A2栋</option><option>园区总部 / B区 / B1栋</option></select></td><td><span class="status-pill pass">新增</span></td></tr>
                <tr><td><input type="checkbox" checked /></td><td>云端-停车场 NVR</td><td>停车区域</td><td>ONVIF</td><td>10.20.9.88</td><td><select class="select"><option>园区总部 / 停车场</option><option>园区总部 / B区 / B2栋</option><option>园区总部</option></select></td><td><span class="status-pill waiting">冲突待确认</span></td></tr>
                <tr><td><input type="checkbox" /></td><td>云端-北门卡口 IPC</td><td>园区入口</td><td>GA/T 1400</td><td>10.20.10.45</td><td><select class="select"><option>园区总部</option><option>园区总部 / A区 / A3栋</option><option>园区总部 / 停车场</option></select></td><td><span class="status-pill waiting">更新</span></td></tr>
              </tbody>
            </table>
          </div>
        </template>
        <template v-if="modal.type === 'mediaDelete'">
          <p class="modal-hint danger">删除后将解除设备、通道、预览分组和告警联动关系。历史录像索引可按策略保留。</p>
          <div class="modal-form-row"><label>删除选项：</label><span style="padding-top:7px;"><label class="video-device-include"><input type="checkbox" />同时删除通道配置</label></span></div>
        </template>
        <template v-if="modal.type === 'videoConfig'">
          <div class="modal-split">
            <aside class="modal-split-side">
              <div class="media-side-menu"><button class="active">基础配置</button><button @click="showToast('视频配置分组已模拟切换')">视频配置</button><button @click="showToast('回放配置分组已模拟切换')">回放配置</button><button @click="showToast('抓图配置分组已模拟切换')">抓图配置</button></div>
            </aside>
            <div class="modal-split-main">
              <h4 class="modal-block-title">基础配置</h4>
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>保存路径：</label><input class="input" value="C:/Users/Public/AVPreview" /></div>
                <div class="modal-form-row"><label>启动窗口：</label><select class="select"><option>2x2</option><option>1x1</option><option>3x3</option><option>4x4</option></select></div>
              </div>
              <div class="modal-check-grid" style="grid-template-columns:repeat(2,minmax(0,1fr));">
                <label class="video-device-include"><input type="checkbox" checked />播放性能不足提示</label>
                <label class="video-device-include"><input type="checkbox" />GPU 硬件解码</label>
                <label class="video-device-include"><input type="checkbox" />录像预警提示</label>
                <label class="video-device-include"><input type="checkbox" />是否组播</label>
              </div>
              <h4 class="modal-block-title">视频配置</h4>
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>重连次数：</label><input class="input" value="10" /></div>
                <div class="modal-form-row"><label>重连间隔：</label><input class="input" value="15 秒" /></div>
                <div class="modal-form-row"><label>码流策略：</label><select class="select"><option>根据窗口数量自动切换</option><option>优先主码流</option><option>优先子码流</option></select></div>
                <div class="modal-form-row"><label>性能阈值：</label><select class="select"><option>CPU 超过 80% 切子码流</option><option>CPU 超过 70% 切子码流</option></select></div>
              </div>
              <h4 class="modal-block-title">回放与抓图</h4>
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>即时回放：</label><select class="select"><option>前15秒</option><option>前30秒</option><option>前60秒</option></select></div>
                <div class="modal-form-row"><label>录像格式：</label><select class="select"><option>MP4</option><option>FLV</option></select></div>
                <div class="modal-form-row"><label>抓图格式：</label><select class="select"><option>JPG</option><option>PNG</option></select></div>
                <div class="modal-form-row"><label>命名规则：</label><input class="input" value="设备名称_通道_时间" /></div>
              </div>
            </div>
          </div>
        </template>
        <template v-if="modal.type === 'customLayout'">
          <div class="modal-split">
            <div class="modal-split-main">
              <div class="modal-wall-canvas cols-3">
                <div class="media-wall-window active">窗口 1</div>
                <div class="media-wall-window">窗口 2</div>
                <div class="media-wall-window">窗口 3</div>
                <div class="media-wall-window">窗口 4</div>
                <div class="media-wall-window">窗口 5</div>
              </div>
            </div>
            <aside class="modal-split-side" style="flex-basis:220px;">
              <div class="modal-form-row" style="grid-template-columns:70px 1fr;"><label>布局名称：</label><input class="input" value="园区重点点位布局" /></div>
              <div class="modal-form-row" style="grid-template-columns:70px 1fr;"><label>窗口数量：</label><select class="select"><option>5</option><option>7</option><option>10</option><option>13</option><option>17</option></select></div>
              <div class="modal-form-row" style="grid-template-columns:70px 1fr;"><label>画面比例：</label><select class="select"><option>原始宽高比</option><option>满屏窗口</option></select></div>
              <p class="modal-hint">拖拽窗口边界可调整大小，拖拽窗口标题可交换两个播放窗口画面。</p>
            </aside>
          </div>
        </template>
        <template v-if="modal.type === 'quickReplay'">
          <p class="modal-hint">无需配置录像存储，直接回看当前预览时间点前 15 秒画面。</p>
          <div class="modal-replay-preview"><span>真实黄区球机_通道_1</span><b>正在回放 00:00:11 / 00:00:15</b></div>
          <div class="modal-form-row"><label>回放时长：</label><select class="select"><option>前15秒</option><option>前30秒</option><option>前60秒</option></select></div>
        </template>
        <template v-if="modal.type === 'patrolPlan'">
          <div class="modal-split">
            <aside class="modal-split-side" style="flex-basis:220px;">
              <input class="input" placeholder="搜索监控点名称/IP" aria-label="搜索监控点" style="margin-bottom:10px;" />
              <ul class="media-resource-list">
                <li class="group">本域(45/64)</li>
                <li><input type="checkbox" />mipc_10.210.33.198_通道_1</li>
                <li><input type="checkbox" />真实黄区球机_通道_1</li>
                <li><input type="checkbox" />A1栋入口 IPC-01</li>
              </ul>
            </aside>
            <div class="modal-split-main">
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>计划名称：</label><input class="input" value="园区巡检计划1" /></div>
                <div class="modal-form-row"><label>窗口布局：</label><select class="select"><option>2x2</option><option>1x1</option><option>3x3</option><option>自定义布局</option></select></div>
                <div class="modal-form-row"><label>轮巡窗口：</label><select class="select"><option>当前选中窗口</option><option>全部窗口</option><option>窗口 1</option></select></div>
                <div class="modal-form-row"><label>停留时间：</label><input class="input" value="20 秒" /></div>
              </div>
              <div class="modal-table-wrap">
                <table class="prototype-table">
                  <thead><tr><th style="width:44px;">序号</th><th>通道名称</th><th>预置点</th><th>通道类型</th><th>操作</th></tr></thead>
                  <tbody>
                    <tr><td>1</td><td>mipc_10.210.33.198_通道_1</td><td><select class="select"><option>无</option><option>主入口</option></select></td><td>固定枪机</td><td><button class="link-blue" @click="showToast('已模拟调整轮巡顺序')">↑ ↓</button><button class="link-red" @click="showToast('已模拟移除轮巡通道')">删除</button></td></tr>
                    <tr><td>2</td><td>真实黄区球机_10.210.2.54_通道_1</td><td><select class="select"><option>主入口</option><option>东侧车道</option></select></td><td>球机</td><td><button class="link-blue" @click="showToast('已模拟调整轮巡顺序')">↑ ↓</button><button class="link-red" @click="showToast('已模拟移除轮巡通道')">删除</button></td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </template>
        <template v-if="modal.type === 'segmentPlayback'">
          <div class="modal-form-row"><label>录像时段：</label><input class="input" value="2026-07-06 00:00:00 - 2026-07-06 23:59:59" /></div>
          <div class="modal-form-row"><label>分段数量：</label><select class="select"><option>4段</option><option>9段</option><option>16段</option></select></div>
          <div class="modal-form-row"><label>分段策略：</label><select class="select"><option>按时间均分</option><option>按有录像片段均分</option><option>按告警片段优先</option></select></div>
          <div class="modal-segment-preview"><span>00:00-06:00</span><span>06:00-12:00</span><span>12:00-18:00</span><span>18:00-24:00</span></div>
        </template>
        <template v-if="modal.type === 'recordDownload'">
          <div class="modal-replay-preview"><span>2K_IPC7240-UEF1P枪机_通道_1</span><b>12:00 — 13:00 时间轴已选中 30 分钟录像</b></div>
          <div class="modal-form-row"><label>录像时段：</label><input class="input" value="2026-07-06 12:44:10 - 2026-07-06 13:14:10" /></div>
          <div class="modal-form-row"><label>下载倍速：</label><select class="select"><option>2倍速</option><option>4倍速</option><option>8倍速</option><option>16倍速</option><option>32倍速</option><option>64倍速</option></select></div>
          <div class="modal-form-row"><label>保存目录：</label><input class="input" value="C:/Users/Public/WebBrowserPlayer/Record" /></div>
          <div class="modal-form-row"><label>文件格式：</label><select class="select"><option>MP4</option><option>原始码流</option></select></div>
          <div class="modal-summary-strip"><span>预计大小：<strong>386 MB</strong></span><span>云检索来源：中心录像</span></div>
        </template>
        <template v-if="modal.type === 'shortcutHelp'">
          <div class="modal-kbd-list">
            <div><kbd>Space</kbd><span>暂停 / 恢复播放</span></div>
            <div><kbd>← / →</kbd><span>切换倍速</span></div>
            <div><kbd>↑</kbd><span>单帧播放</span></div>
            <div><kbd>↓</kbd><span>恢复 1 倍速播放</span></div>
          </div>
        </template>
        <template v-if="modal.type === 'tvWall'">
          <div class="media-resource-tabs"><button class="active">1 电视墙配置</button><button @click="showToast('解码通道绑定步骤已模拟切换')">2 解码通道绑定</button><button @click="showToast('应用步骤已模拟切换')">3 应用</button></div>
          <div class="modal-split">
            <div class="modal-split-main">
              <h4 class="modal-block-title">基础信息</h4>
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>电视墙名称：</label><input class="input" value="指挥中心主墙" /></div>
                <div class="modal-form-row"><label>电视墙编号：</label><input class="input" value="TVW-001" /></div>
                <div class="modal-form-row"><label>M*N 行列：</label><select class="select"><option>4 x 4</option><option>3 x 3</option><option>2 x 2</option><option>自定义</option></select></div>
                <div class="modal-form-row"><label>默认布局：</label><select class="select"><option>16窗口均分</option><option>1大15小</option><option>报警窗口优先</option></select></div>
              </div>
              <h4 class="modal-block-title">解码通道</h4>
              <div class="modal-table-wrap">
                <table class="prototype-table">
                  <thead><tr><th>窗口</th><th>解码设备</th><th>解码通道</th></tr></thead>
                  <tbody>
                    <tr><td>1</td><td><select class="select"><option>DEC-01</option></select></td><td><select class="select"><option>HDMI-1</option></select></td></tr>
                    <tr><td>2</td><td><select class="select"><option>DEC-01</option></select></td><td><select class="select"><option>HDMI-2</option></select></td></tr>
                  </tbody>
                </table>
              </div>
            </div>
            <aside class="modal-split-side" style="flex-basis:230px;">
              <div class="modal-wall-canvas">
                <div class="media-wall-window active">1</div><div class="media-wall-window">2</div><div class="media-wall-window">3</div><div class="media-wall-window">4</div>
                <div class="media-wall-window">5</div><div class="media-wall-window">6</div><div class="media-wall-window">7</div><div class="media-wall-window">8</div>
                <div class="media-wall-window">9</div><div class="media-wall-window">10</div><div class="media-wall-window">11</div><div class="media-wall-window">12</div>
                <div class="media-wall-window">13</div><div class="media-wall-window">14</div><div class="media-wall-window">15</div><div class="media-wall-window">16</div>
              </div>
            </aside>
          </div>
        </template>
        <template v-if="modal.type === 'spliceWall'">
          <div class="modal-split">
            <div class="modal-split-main">
              <h4 class="modal-block-title">拼控设备配置</h4>
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>拼控墙名称：</label><input class="input" value="LCD拼控墙" /></div>
                <div class="modal-form-row"><label>拼控设备：</label><select class="select"><option>LCD拼控控制器-01</option><option>LED拼接处理器-02</option></select></div>
                <div class="modal-form-row"><label>墙面行列：</label><select class="select"><option>3 x 4</option><option>2 x 4</option><option>4 x 4</option></select></div>
                <div class="modal-form-row"><label>开窗模式：</label><select class="select"><option>支持跨屏开窗</option><option>固定单屏窗口</option></select></div>
              </div>
              <h4 class="modal-block-title">输出通道绑定</h4>
              <div class="modal-table-wrap">
                <table class="prototype-table">
                  <thead><tr><th>输出通道</th><th>物理屏</th><th>位置</th></tr></thead>
                  <tbody>
                    <tr><td>OUT-01</td><td>屏幕 1</td><td>1行1列</td></tr>
                    <tr><td>OUT-02</td><td>屏幕 2</td><td>1行2列</td></tr>
                    <tr><td>OUT-03</td><td>屏幕 3</td><td>1行3列</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
            <aside class="modal-split-side" style="flex-basis:230px;">
              <div class="modal-wall-canvas cols-2">
                <div class="media-wall-window active">大屏窗口 A</div>
                <div class="media-wall-window">窗口 B</div>
                <div class="media-wall-window">窗口 C</div>
                <div class="media-wall-window">窗口 D</div>
              </div>
            </aside>
          </div>
        </template>
        <template v-if="modal.type === 'alarmPlan'">
          <div class="modal-split">
            <div class="modal-split-main">
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>预案名称：</label><input class="input" value="周界入侵上墙" /></div>
                <div class="modal-form-row"><label>报警类型：</label><select class="select"><option>周界入侵</option><option>门禁异常</option><option>区域入侵</option><option>设备离线</option></select></div>
                <div class="modal-form-row"><label>开窗电视墙：</label><select class="select"><option>指挥中心主墙</option><option>园区安防副墙</option></select></div>
                <div class="modal-form-row"><label>开窗位置：</label><select class="select"><option>窗口 1</option><option>窗口 4</option><option>报警专用窗口</option></select></div>
                <div class="modal-form-row"><label>绑定信号源：</label><select class="select"><option>周界球机 IPC-03</option><option>A1栋入口 IPC-01</option><option>北门卡口 IPC-07</option></select></div>
                <div class="modal-form-row"><label>停留时间：</label><input class="input" value="30 秒" /></div>
                <div class="modal-form-row"><label>状态：</label><select class="select"><option>开启</option><option>关闭</option></select></div>
                <div class="modal-form-row"><label>优先级：</label><select class="select"><option>高</option><option>中</option><option>低</option></select></div>
              </div>
            </div>
            <aside class="modal-split-side" style="flex-basis:230px;">
              <div class="modal-wall-canvas cols-2">
                <div class="media-wall-window active">报警窗口<br />周界球机</div>
                <div class="media-wall-window">窗口 2</div>
                <div class="media-wall-window">窗口 3</div>
                <div class="media-wall-window">窗口 4</div>
              </div>
            </aside>
          </div>
        </template>
        <template v-if="modal.type === 'keyboardAccess'">
          <div class="modal-form-grid">
            <div class="modal-form-row"><label>键盘名称：</label><input class="input" value="KB-指挥中心-01" /></div>
            <div class="modal-form-row"><label>IP地址：</label><input class="input" value="192.168.88.21" /></div>
            <div class="modal-form-row"><label>接入协议：</label><select class="select"><option>网络键盘 SDK</option><option>ONVIF 控制</option></select></div>
            <div class="modal-form-row"><label>控制电视墙：</label><select class="select"><option>指挥中心主墙</option><option>园区安防副墙</option></select></div>
            <div class="modal-form-row"><label>电视墙编号：</label><input class="input" value="TVW-001" /></div>
            <div class="modal-form-row"><label>视频源编号：</label><input class="input" value="SRC-A1-001" /></div>
            <div class="modal-form-row"><label>轮巡组编号：</label><input class="input" value="TOUR-PATROL-001" /></div>
            <div class="modal-form-row"><label>控制权限：</label><select class="select"><option>指定键盘独占</option><option>按角色授权</option></select></div>
          </div>
          <div class="modal-keyboard-pad"><button @click="showToast('已模拟键盘上墙操作')">上墙</button><button @click="showToast('已模拟键盘下墙操作')">下墙</button><button @click="showToast('已模拟键盘切源操作')">切源</button><button @click="showToast('已模拟键盘轮巡操作')">轮巡</button></div>
        </template>
        <template v-if="modal.type === 'wallPreview'">
          <div class="modal-form-row"><label>默认预览墙：</label><select class="select"><option>指挥中心主墙</option><option>园区安防副墙</option></select></div>
          <div class="modal-form-row"><label>窗口布局：</label><select class="select"><option>4x4</option><option>2x2</option><option>1大多小</option></select></div>
          <div class="modal-form-row"><label>预览码流：</label><select class="select"><option>子码流优先</option><option>主码流优先</option><option>自动</option></select></div>
          <div class="modal-form-row"><label>上墙确认：</label><select class="select"><option>需要确认</option><option>直接上墙</option></select></div>
          <div class="modal-form-row"><label>显示选项：</label><span style="display:flex;gap:16px;padding-top:7px;"><label class="video-device-include"><input type="checkbox" checked />显示窗口编号</label><label class="video-device-include"><input type="checkbox" checked />显示信号源名称</label></span></div>
        </template>
        <template v-if="modal.type === 'detector'">
          <div class="modal-form-grid">
            <div class="modal-form-row"><label>探测器名称：</label><input class="input" value="A区东侧红外对射" /></div>
            <div class="modal-form-row"><label>探测类型：</label><select class="select"><option>非法入侵</option><option>环境数据</option><option>异常人车布控</option><option>设备异常</option></select></div>
            <div class="modal-form-row"><label>所在区域：</label><select class="select"><option>A区 / 东侧围栏</option><option>B区 / B2机房</option><option>北门卡口</option></select></div>
            <div class="modal-form-row"><label>接入协议：</label><select class="select"><option>干接点输入</option><option>Modbus TCP</option><option>HTTP 推送</option><option>设备 SDK</option></select></div>
            <div class="modal-form-row"><label>IP地址：</label><input class="input" value="192.168.88.61" /></div>
            <div class="modal-form-row"><label>报警阈值：</label><input class="input" value="连续触发 2 次" /></div>
            <div class="modal-form-row"><label>联动摄像机：</label><select class="select"><option>周界球机 IPC-03</option><option>A1栋入口 IPC-01</option><option>北门卡口 IPC-07</option></select></div>
            <div class="modal-form-row"><label>启用状态：</label><select class="select"><option>启用</option><option>停用</option></select></div>
          </div>
          <div class="modal-form-row"><label>备注：</label><textarea class="textarea" style="height:80px;">用于 A 区东侧围栏非法入侵检测，触发后联动视频上墙、客户端弹窗和声音提醒。</textarea></div>
        </template>
        <template v-if="modal.type === 'linkageRule'">
          <div class="modal-split">
            <div class="modal-split-main">
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>规则名称：</label><input class="input" value="周界入侵联动" /></div>
                <div class="modal-form-row"><label>触发信号：</label><select class="select"><option>红外对射 / 入侵</option><option>温湿度越限</option><option>布控车辆出现</option></select></div>
                <div class="modal-form-row"><label>联动摄像机：</label><select class="select"><option>周界球机 IPC-03</option><option>北门卡口 IPC-07</option></select></div>
                <div class="modal-form-row"><label>录像联动：</label><select class="select"><option>关联前30秒后60秒</option><option>关联前15秒后30秒</option><option>不关联录像</option></select></div>
                <div class="modal-form-row"><label>上墙位置：</label><select class="select"><option>指挥中心主墙 / 窗口1</option><option>应急联动墙 / 报警窗口</option></select></div>
                <div class="modal-form-row"><label>客户端弹窗：</label><select class="select"><option>值班客户端</option><option>全部在线客户端</option><option>指定角色</option></select></div>
                <div class="modal-form-row"><label>声音文件：</label><select class="select"><option>alarm_intrusion.wav</option><option>alarm_env.wav</option><option>alarm_vehicle.wav</option></select></div>
                <div class="modal-form-row"><label>闪烁时长：</label><input class="input" value="10 秒" /></div>
              </div>
              <div class="modal-form-row"><label>叠加文字：</label><input class="input" value="周界入侵告警：A区东侧围栏" /></div>
            </div>
            <aside class="modal-split-side" style="flex-basis:230px;">
              <div class="modal-replay-preview" style="min-height:160px;align-content:end;"><span>周界入侵告警</span><b>A区东侧围栏</b></div>
            </aside>
          </div>
        </template>
        <template v-if="modal.type === 'alarmEventDetail'">
          <div class="modal-split">
            <div class="modal-split-main">
              <div class="modal-replay-preview" style="min-height:220px;align-content:end;"><span>周界入侵告警</span><b>2026-07-09 12:42:18 告警画面</b></div>
            </div>
            <aside class="modal-split-side" style="flex-basis:330px;">
              <h4 class="modal-block-title">事件信息</h4>
              <div class="event-detail-grid" style="grid-template-columns:1fr;gap:12px;margin-bottom:0;">
                <dl class="event-detail-field"><dt>报警名称</dt><dd>周界入侵</dd></dl>
                <dl class="event-detail-field"><dt>报警类型</dt><dd>非法入侵</dd></dl>
                <dl class="event-detail-field"><dt>所在区域</dt><dd>A区东侧围栏</dd></dl>
                <dl class="event-detail-field"><dt>探测器</dt><dd>A区东侧红外对射</dd></dl>
                <dl class="event-detail-field"><dt>联动摄像机</dt><dd>周界球机 IPC-03</dd></dl>
                <dl class="event-detail-field"><dt>联动结果</dt><dd>客户端弹窗、电视墙上墙、声音提醒、录像关联</dd></dl>
                <dl class="event-detail-field"><dt>处理状态</dt><dd><span class="status-pill waiting">待处理</span></dd></dl>
              </div>
            </aside>
          </div>
        </template>
      </div>
      <div class="modal-footer">
        <template v-if="modal.type === 'eventDetail'">
          <button class="btn" @click="$emit('close')">关闭</button>
          <button class="btn primary" @click="$emit('close')">重试</button>
          <button class="btn danger" @click="$emit('close')">删除</button>
        </template>
        <template v-else-if="modal.type === 'mediaImport'">
          <button class="btn" @click="showToast('导入模板已开始下载')">下载模板</button>
          <button class="btn primary" @click="$emit('submit', modal.type)">开始校验</button>
        </template>
        <template v-else-if="modal.type === 'mediaSmartDiscover'">
          <button class="btn" @click="$emit('close')">关闭</button>
        </template>
        <template v-else-if="modal.type === 'mediaCloud'">
          <button class="btn" @click="showToast('预检查通过：新增 12 台，更新 8 台，冲突 2 台')">预检查</button>
          <button class="btn primary" @click="$emit('submit', modal.type)">开始同步</button>
        </template>
        <template v-else-if="modal.type === 'videoConfig'">
          <button class="btn" @click="showToast('已恢复默认视频参数')">恢复默认配置</button>
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" @click="$emit('submit', modal.type)">确定</button>
        </template>
        <template v-else-if="modal.type === 'quickReplay'">
          <button class="btn" @click="goPlayback">切至历史录像</button>
          <button class="btn primary" @click="$emit('submit', modal.type)">返回实况</button>
        </template>
        <template v-else-if="modal.type === 'shortcutHelp'">
          <button class="btn primary" @click="$emit('close')">知道了</button>
        </template>
        <template v-else-if="modal.type === 'alarmPlan'">
          <button class="btn danger" @click="$emit('close'); showToast('报警上墙预案已模拟删除')">删除预案</button>
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" @click="$emit('submit', modal.type)">保存</button>
        </template>
        <template v-else-if="modal.type === 'alarmEventDetail'">
          <button class="btn" @click="$emit('close'); showToast('该告警已按误报关闭')">误报关闭</button>
          <button class="btn" @click="$emit('close'); showToast('已生成处置工单')">转工单</button>
          <button class="btn primary" @click="$emit('submit', modal.type)">确认处理</button>
        </template>
        <template v-else>
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" :class="{ danger: modal.type === 'mediaDelete' }" @click="$emit('submit', modal.type)">{{ submitLabel }}</button>
        </template>
      </div>
    </section>
  </div>
</template>
