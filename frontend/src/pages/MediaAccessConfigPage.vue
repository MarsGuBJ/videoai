<template>
  <section class="content review-wide access-config-page">
    <div class="review-titlebar"><div><h1>接入配置</h1></div></div>

    <div class="access-protocol-tabs" role="tablist" aria-label="接入协议">
      <button
        v-for="protocol in protocols"
        :id="'access-tab-' + protocol.key"
        :key="protocol.key"
        class="access-protocol-tab"
        :class="{ active: activeProtocol === protocol.key }"
        type="button"
        role="tab"
        :aria-selected="activeProtocol === protocol.key"
        :aria-controls="'access-panel-' + protocol.key"
        :tabindex="activeProtocol === protocol.key ? 0 : -1"
        @click="selectProtocol(protocol.key)"
        @keydown="handleProtocolKeydown"
      >{{ protocol.label }}</button>
    </div>

    <div class="panel access-config-surface">
      <section v-show="activeProtocol === 'gb28181'" id="access-panel-gb28181" class="access-config-form-shell" role="tabpanel" aria-labelledby="access-tab-gb28181">
        <div class="access-config-heading">
          <h2>国标GB28181配置</h2>
          <span class="access-enabled-status" :class="{ off: !gb28181.enabled }">{{ gb28181.enabled ? "已启用" : "已关闭" }}</span>
        </div>
        <form class="access-config-form" @submit.prevent="saveProtocol('gb28181')">
          <div class="access-field">
            <span class="access-field-label">是否启用</span>
            <span class="access-choice-group" role="group" aria-label="是否启用GB28181">
              <button class="access-choice" :class="{ active: gb28181.enabled, enabled: gb28181.enabled }" type="button" :aria-pressed="gb28181.enabled" @click="gb28181.enabled = true">开启</button>
              <button class="access-choice" :class="{ active: !gb28181.enabled }" type="button" :aria-pressed="!gb28181.enabled" @click="gb28181.enabled = false">关闭</button>
            </span>
          </div>
          <label class="access-field">
            <span class="access-field-label required">SIP ID</span>
            <input v-model.trim="gb28181.sipId" class="input" maxlength="20" aria-label="SIP ID" :aria-invalid="!!protocolErrors.gb28181.sipId" :aria-describedby="protocolErrors.gb28181.sipId ? 'gb28181-sip-id-error' : null" @input="clearProtocolError('gb28181', 'sipId')" />
            <span v-if="protocolErrors.gb28181.sipId" id="gb28181-sip-id-error" class="access-field-error" role="alert">{{ protocolErrors.gb28181.sipId }}</span>
          </label>
          <label class="access-field">
            <span class="access-field-label required">SIP 域</span>
            <input v-model.trim="gb28181.sipDomain" class="input" maxlength="10" aria-label="SIP 域" :aria-invalid="!!protocolErrors.gb28181.sipDomain" :aria-describedby="protocolErrors.gb28181.sipDomain ? 'gb28181-domain-error' : null" @input="clearProtocolError('gb28181', 'sipDomain')" />
            <span v-if="protocolErrors.gb28181.sipDomain" id="gb28181-domain-error" class="access-field-error" role="alert">{{ protocolErrors.gb28181.sipDomain }}</span>
          </label>
          <div class="access-field">
            <span class="access-field-label required">SIP IP</span>
            <span class="access-input-action">
              <input v-model="gb28181.sipIp" class="input" disabled aria-label="SIP IP" />
              <button class="access-field-button" type="button" @click="setNetworkIp('gb28181')">设置</button>
            </span>
          </div>
          <div class="access-field">
            <span class="access-field-label required">SIP 端口(TCP/UDP)</span>
            <span class="access-input-action">
              <input v-model.trim="gb28181.sipPort" class="input" inputmode="numeric" aria-label="SIP 端口" :aria-invalid="!!protocolErrors.gb28181.sipPort" :aria-describedby="protocolErrors.gb28181.sipPort ? 'gb28181-port-error' : null" @input="clearProtocolError('gb28181', 'sipPort')" />
              <button class="access-field-button" type="button" @click="detectPort('gb28181')">检测</button>
            </span>
            <span v-if="protocolErrors.gb28181.sipPort" id="gb28181-port-error" class="access-field-error" role="alert">{{ protocolErrors.gb28181.sipPort }}</span>
          </div>
          <label class="access-field">
            <span class="access-field-label">设备统一接入密码</span>
            <input v-model="gb28181.password" class="input" type="password" autocomplete="new-password" aria-label="设备统一接入密码" />
          </label>
          <label class="access-field">
            <span class="access-field-label">上级联请求端口</span>
            <input v-model="gb28181.parentPort" class="input" disabled aria-label="上级联请求端口" />
          </label>
          <div class="access-field">
            <span class="access-field-label">收流端口范围</span>
            <span class="access-port-range">
              <input v-model.trim="gb28181.receivePortStart" class="input" inputmode="numeric" aria-label="收流起始端口" :aria-invalid="!!protocolErrors.gb28181.receivePorts" :aria-describedby="protocolErrors.gb28181.receivePorts ? 'gb28181-receive-port-error' : null" @input="clearProtocolError('gb28181', 'receivePorts')" />
              <span>~</span>
              <input v-model.trim="gb28181.receivePortEnd" class="input" inputmode="numeric" aria-label="收流结束端口" :aria-invalid="!!protocolErrors.gb28181.receivePorts" :aria-describedby="protocolErrors.gb28181.receivePorts ? 'gb28181-receive-port-error' : null" @input="clearProtocolError('gb28181', 'receivePorts')" />
            </span>
            <span v-if="protocolErrors.gb28181.receivePorts" id="gb28181-receive-port-error" class="access-field-error" role="alert">{{ protocolErrors.gb28181.receivePorts }}</span>
          </div>
          <div class="access-config-actions">
            <button class="btn primary" type="submit">保存</button>
            <button class="btn" type="button" @click="checkGb28181">检查配置</button>
            <button class="btn" type="button" @click="copyConfig('gb28181')">一键复制</button>
          </div>
        </form>
      </section>

      <section v-show="activeProtocol === 'gb35114'" id="access-panel-gb35114" role="tabpanel" aria-labelledby="access-tab-gb35114">
        <div class="access-config-heading"><h2>国标GB35114</h2></div>
        <div class="access-certificate-toolbar">
          <button ref="certificateOpenButton" class="btn primary" type="button" @click="openCertificateDialog">＋ 添加设备证书</button>
          <button class="btn ghost" type="button" @click="signCertificate">✎ 签发设备证书</button>
          <button class="btn ghost" type="button" @click="downloadCertificate">⇩ 下载国密证书</button>
        </div>
        <div class="access-certificate-table-wrap">
          <table class="prototype-table access-certificate-table">
            <thead><tr><th>ID</th><th>设备编码</th><th>认证方式</th><th>更新时间</th><th>创建时间</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="(row, index) in certificates" :key="row.id">
                <td>{{ row.id }}</td><td>{{ row.deviceCode }}</td><td>{{ row.authMode }}</td><td>{{ row.updatedAt }}</td><td>{{ row.createdAt }}</td>
                <td><span class="access-cert-actions"><button class="link-blue" type="button" @click="showToast('设备证书状态正常')">查看</button><button class="link-red" type="button" @click="removeCertificate(index)">删除</button></span></td>
              </tr>
              <tr v-if="!certificates.length" class="access-certificate-empty">
                <td colspan="6"><div class="access-empty-state"><span class="access-empty-icon" aria-hidden="true">&#xf01c;</span><span>暂无数据</span></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-show="activeProtocol === 'ga1400'" id="access-panel-ga1400" class="access-config-form-shell" role="tabpanel" aria-labelledby="access-tab-ga1400">
        <div class="access-config-heading">
          <h2>公安GA1400配置</h2>
          <span class="access-enabled-status" :class="{ off: !ga1400.enabled }">{{ ga1400.enabled ? "已启用" : "已关闭" }}</span>
        </div>
        <form class="access-config-form" @submit.prevent="saveProtocol('ga1400')">
          <div class="access-field">
            <span class="access-field-label">是否启用</span>
            <span class="access-choice-group" role="group" aria-label="是否启用GA1400">
              <button class="access-choice" :class="{ active: ga1400.enabled, enabled: ga1400.enabled }" type="button" :aria-pressed="ga1400.enabled" @click="ga1400.enabled = true">开启</button>
              <button class="access-choice" :class="{ active: !ga1400.enabled }" type="button" :aria-pressed="!ga1400.enabled" @click="ga1400.enabled = false">关闭</button>
            </span>
          </div>
          <label class="access-field">
            <span class="access-field-label required">平台 ID</span>
            <input v-model.trim="ga1400.platformId" class="input" maxlength="20" aria-label="平台 ID" :aria-invalid="!!protocolErrors.ga1400.platformId" :aria-describedby="protocolErrors.ga1400.platformId ? 'ga1400-platform-id-error' : null" @input="clearProtocolError('ga1400', 'platformId')" />
            <span v-if="protocolErrors.ga1400.platformId" id="ga1400-platform-id-error" class="access-field-error" role="alert">{{ protocolErrors.ga1400.platformId }}</span>
          </label>
          <div class="access-field">
            <span class="access-field-label required">平台 IP</span>
            <span class="access-input-action">
              <input v-model="ga1400.platformIp" class="input" disabled aria-label="平台 IP" />
              <button class="access-field-button" type="button" @click="setNetworkIp('ga1400')">设置</button>
            </span>
          </div>
          <div class="access-field">
            <span class="access-field-label required">端口</span>
            <span class="access-input-action">
              <input v-model.trim="ga1400.port" class="input" inputmode="numeric" aria-label="GA1400端口" :aria-invalid="!!protocolErrors.ga1400.port" :aria-describedby="protocolErrors.ga1400.port ? 'ga1400-port-error' : null" @input="clearProtocolError('ga1400', 'port')" />
              <button class="access-field-button" type="button" @click="detectPort('ga1400')">检测</button>
            </span>
            <span v-if="protocolErrors.ga1400.port" id="ga1400-port-error" class="access-field-error" role="alert">{{ protocolErrors.ga1400.port }}</span>
          </div>
          <label class="access-field">
            <span class="access-field-label">设备统一接入密码</span>
            <input v-model="ga1400.password" class="input" type="text" autocomplete="off" aria-label="设备统一接入密码" />
          </label>
          <label class="access-field">
            <span class="access-field-label">资源存储路径</span>
            <input v-model.trim="ga1400.resourcePath" class="input" aria-label="资源存储路径" />
          </label>
          <div class="access-field">
            <span class="access-field-label">自动接收采集设备的注册</span>
            <span class="access-choice-group" role="group" aria-label="自动接收采集设备的注册">
              <button class="access-choice" :class="{ active: ga1400.autoRegister, enabled: ga1400.autoRegister }" type="button" :aria-pressed="ga1400.autoRegister" @click="ga1400.autoRegister = true">开启</button>
              <button class="access-choice" :class="{ active: !ga1400.autoRegister }" type="button" :aria-pressed="!ga1400.autoRegister" @click="ga1400.autoRegister = false">关闭</button>
            </span>
          </div>
          <div class="access-config-actions">
            <button class="btn primary" type="submit">保存</button>
            <button class="btn" type="button" @click="copyConfig('ga1400')">一键复制</button>
          </div>
        </form>
      </section>
    </div>

    <div v-if="certificateDialogOpen" class="access-modal-mask" role="presentation" @click.self="closeCertificateDialog" @keydown.esc="closeCertificateDialog" @keydown="trapCertificateFocus">
      <section ref="certificateDialog" class="access-modal" role="dialog" aria-modal="true" aria-labelledby="certificate-dialog-title">
        <header class="access-modal-head">
          <h3 id="certificate-dialog-title">添加</h3>
          <button class="access-modal-close" type="button" aria-label="关闭" @click="closeCertificateDialog">×</button>
        </header>
        <form @submit.prevent="addCertificate">
        <div class="access-modal-body">
          <label class="access-field">
            <span class="access-field-label required">设备编码</span>
            <input ref="certificateCode" v-model.trim="certificateForm.deviceCode" class="input" maxlength="20" placeholder="请输入设备编码..." aria-label="设备编码" :aria-invalid="!!certificateErrors.deviceCode" :aria-describedby="certificateErrors.deviceCode ? 'certificate-code-error' : null" @input="certificateErrors.deviceCode = ''" />
            <span v-if="certificateErrors.deviceCode" id="certificate-code-error" class="access-field-error" role="alert">{{ certificateErrors.deviceCode }}</span>
          </label>
          <label class="access-field">
            <span class="access-field-label required">设备证书</span>
            <textarea ref="certificateText" v-model="certificateForm.certificate" placeholder="请输入设备证书或上传证书..." aria-label="设备证书" :aria-invalid="!!certificateErrors.certificate" :aria-describedby="certificateErrors.certificate ? 'certificate-text-error' : null" @input="certificateErrors.certificate = ''"></textarea>
            <span v-if="certificateErrors.certificate" id="certificate-text-error" class="access-field-error" role="alert">{{ certificateErrors.certificate }}</span>
          </label>
          <div class="access-upload-actions">
            <input ref="certificateFile" class="access-upload-input" type="file" accept=".cer,.crt,.pem,.txt" @change="selectCertificateFile" />
            <button class="btn" type="button" @click="($refs.certificateFile as HTMLInputElement).click()">⇧ 上传设备证书</button>
            <span v-if="certificateForm.fileName" class="access-upload-name">{{ certificateForm.fileName }}</span>
          </div>
          <div class="access-field">
            <span class="access-field-label">认证方式</span>
            <span class="access-choice-group" role="group" aria-label="认证方式">
              <button class="access-choice" :class="{ active: certificateForm.authMode === '双向', enabled: certificateForm.authMode === '双向' }" type="button" :aria-pressed="certificateForm.authMode === '双向'" @click="certificateForm.authMode = '双向'">双向</button>
              <button class="access-choice" :class="{ active: certificateForm.authMode === '单向' }" type="button" :aria-pressed="certificateForm.authMode === '单向'" @click="certificateForm.authMode = '单向'">单向</button>
            </span>
          </div>
        </div>
        <footer class="access-modal-footer">
          <button class="btn" type="button" @click="closeCertificateDialog">取消</button>
          <button class="btn primary" type="submit">确定</button>
        </footer>
        </form>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "MediaAccessConfigPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  data() {
    const persisted = (this as any).store.accessConfig;
    return {
      activeProtocol: "gb28181",
      protocols: [
        { key: "gb28181", label: "国标GB28181" },
        { key: "gb35114", label: "国标GB35114" },
        { key: "ga1400", label: "公安GA1400" }
      ],
      gb28181: { ...persisted.gb28181 },
      ga1400: { ...persisted.ga1400 },
      certificates: persisted.certificates.map((row: any) => ({ ...row })),
      protocolErrors: { gb28181: {} as any, ga1400: {} as any },
      certificateDialogOpen: false,
      certificateForm: {
        deviceCode: "",
        certificate: "",
        authMode: "双向",
        fileName: ""
      },
      certificateErrors: {} as any
    };
  },
  methods: {
    selectProtocol(protocol: any) {
      this.activeProtocol = protocol;
    },
    handleProtocolKeydown(event: any) {
      const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
      if (!keys.includes(event.key)) return;
      event.preventDefault();
      const currentIndex = this.protocols.findIndex(protocol => protocol.key === this.activeProtocol);
      let nextIndex = currentIndex;
      if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + this.protocols.length) % this.protocols.length;
      if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % this.protocols.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = this.protocols.length - 1;
      const nextProtocol = this.protocols[nextIndex].key;
      this.selectProtocol(nextProtocol);
      this.$nextTick(() => {
        const tab = document.getElementById(`access-tab-${nextProtocol}`);
        if (tab) tab.focus();
      });
    },
    isValidPort(value: any) {
      const text = String(value == null ? "" : value).trim();
      const port = Number(text);
      return /^\d+$/.test(text) && Number.isInteger(port) && port >= 1 && port <= 65535;
    },
    clearProtocolError(protocol: any, field: any) {
      if (!(this.protocolErrors as any)[protocol][field]) return;
      const next = { ...(this.protocolErrors as any)[protocol] };
      delete next[field];
      (this.protocolErrors as any)[protocol] = next;
    },
    validateProtocol(protocol: any) {
      const errors: any = {};
      if (protocol === "gb28181") {
        if (!/^\d{20}$/.test(this.gb28181.sipId.trim())) errors.sipId = "SIP ID 需为20位数字";
        if (!/^\d{10}$/.test(this.gb28181.sipDomain.trim())) errors.sipDomain = "SIP 域需为10位数字";
        if (!this.isValidPort(this.gb28181.sipPort)) errors.sipPort = "SIP 端口需为1-65535之间的整数";
        const start = Number(this.gb28181.receivePortStart);
        const end = Number(this.gb28181.receivePortEnd);
        if (!this.isValidPort(this.gb28181.receivePortStart) || !this.isValidPort(this.gb28181.receivePortEnd) || start > end) {
          errors.receivePorts = "请输入有效的收流端口范围（1-65535）";
        }
      } else {
        if (!/^\d{20}$/.test(this.ga1400.platformId.trim())) errors.platformId = "平台 ID 需为20位数字";
        if (!this.isValidPort(this.ga1400.port)) errors.port = "端口需为1-65535之间的整数";
      }
      (this.protocolErrors as any)[protocol] = errors;
      return Object.keys(errors).length === 0;
    },
    setNetworkIp(protocol: any) {
      const field = protocol === "gb28181" ? "sipIp" : "platformIp";
      const target: any = protocol === "gb28181" ? this.gb28181 : this.ga1400;
      target[field] = "192.168.11.195";
      this.showToast("已选择本机网卡地址 192.168.11.195");
    },
    detectPort(protocol: any) {
      const errorKey = protocol === "gb28181" ? "sipPort" : "port";
      const port = protocol === "gb28181" ? this.gb28181.sipPort : this.ga1400.port;
      if (!this.isValidPort(port)) {
        (this.protocolErrors as any)[protocol] = { ...(this.protocolErrors as any)[protocol], [errorKey]: "端口需为1-65535之间的整数" };
        this.showToast("端口格式不正确，请输入1-65535之间的整数");
        return;
      }
      this.clearProtocolError(protocol, errorKey);
      this.showToast(`端口 ${port} 检测通过，可以正常监听`);
    },
    saveProtocol(protocol: any) {
      if (!this.validateProtocol(protocol)) {
        this.showToast("配置存在错误，请检查标记字段");
        return;
      }
      const label = protocol === "gb28181" ? "国标GB28181" : "公安GA1400";
      Object.assign((this as any).store.accessConfig[protocol], protocol === "gb28181" ? this.gb28181 : this.ga1400);
      this.showToast(`${label} 配置已保存`);
    },
    checkGb28181() {
      this.showToast(this.validateProtocol("gb28181") ? "GB28181 配置检查通过" : "GB28181 配置存在错误，请检查标记字段");
    },
    configText(protocol: any) {
      if (protocol === "gb28181") {
        return [
          `是否启用：${this.gb28181.enabled ? "开启" : "关闭"}`,
          `SIP ID：${this.gb28181.sipId}`,
          `SIP 域：${this.gb28181.sipDomain}`,
          `SIP IP：${this.gb28181.sipIp}`,
          `SIP 端口：${this.gb28181.sipPort}`,
          `上级联请求端口：${this.gb28181.parentPort}`,
          `收流端口范围：${this.gb28181.receivePortStart} ~ ${this.gb28181.receivePortEnd}`
        ].join("\n");
      }
      return [
        `是否启用：${this.ga1400.enabled ? "开启" : "关闭"}`,
        `平台 ID：${this.ga1400.platformId}`,
        `平台 IP：${this.ga1400.platformIp}`,
        `端口：${this.ga1400.port}`,
        `资源存储路径：${this.ga1400.resourcePath}`,
        `自动接收采集设备的注册：${this.ga1400.autoRegister ? "开启" : "关闭"}`
      ].join("\n");
    },
    async copyConfig(protocol: any) {
      const text = this.configText(protocol);
      let copied = false;
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
          copied = true;
        }
      } catch (error) {
        copied = false;
      }
      if (!copied) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        try {
          copied = document.execCommand("copy");
        } catch (error) {
          copied = false;
        }
        document.body.removeChild(textarea);
      }
      this.showToast(copied ? "配置已复制到剪贴板" : "当前浏览器不支持自动复制");
    },
    openCertificateDialog() {
      this.certificateForm = { deviceCode: "", certificate: "", authMode: "双向", fileName: "" };
      this.certificateErrors = {};
      this.certificateDialogOpen = true;
      this.$nextTick(() => (this.$refs.certificateCode as any) && (this.$refs.certificateCode as any).focus());
    },
    closeCertificateDialog() {
      this.certificateDialogOpen = false;
      this.certificateErrors = {};
      this.$nextTick(() => (this.$refs.certificateOpenButton as any) && (this.$refs.certificateOpenButton as any).focus());
    },
    trapCertificateFocus(event: any) {
      if (event.key !== "Tab" || !this.$refs.certificateDialog) return;
      const focusable = Array.from((this.$refs.certificateDialog as any).querySelectorAll("button:not(:disabled), input:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex='-1'])"))
        .filter((element: any) => element.offsetParent !== null);
      if (!focusable.length) return;
      const first: any = focusable[0];
      const last: any = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    },
    async selectCertificateFile(event: any) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      this.certificateForm.fileName = file.name;
      try {
        this.certificateForm.certificate = await file.text();
        this.certificateErrors.certificate = "";
      } catch (error) {
        this.showToast("证书文件读取失败，请重新选择");
      }
      event.target.value = "";
    },
    addCertificate() {
      const errors: any = {};
      if (!/^\d{20}$/.test(this.certificateForm.deviceCode.trim())) errors.deviceCode = "请输入20位设备编码";
      if (!this.certificateForm.certificate.trim()) errors.certificate = "请输入或上传设备证书";
      this.certificateErrors = errors;
      if (Object.keys(errors).length) {
        this.$nextTick(() => {
          const target: any = errors.deviceCode ? this.$refs.certificateCode : this.$refs.certificateText;
          if (target) target.focus();
        });
        return;
      }

      const now = new Date();
      const pad = (value: any) => String(value).padStart(2, "0");
      const stamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
      const row = {
        id: String(Date.now()).slice(-8),
        deviceCode: this.certificateForm.deviceCode.trim(),
        authMode: this.certificateForm.authMode,
        updatedAt: stamp,
        createdAt: stamp
      };
      this.certificates.unshift(row);
      (this as any).store.accessConfig.certificates = this.certificates.map(item => ({ ...item }));
      const code = this.certificateForm.deviceCode.trim();
      this.closeCertificateDialog();
      this.showToast(`设备证书已添加：${code}`);
    },
    removeCertificate(index: any) {
      const row = this.certificates[index];
      this.certificates.splice(index, 1);
      (this as any).store.accessConfig.certificates = this.certificates.map(item => ({ ...item }));
      this.showToast(`设备证书已删除：${row.deviceCode}`);
    },
    signCertificate() {
      this.showToast(this.certificates.length ? "已提交设备证书签发任务" : "请先添加设备证书");
    },
    downloadCertificate() {
      this.showToast("国密根证书下载任务已创建");
    }
  }
});
</script>
