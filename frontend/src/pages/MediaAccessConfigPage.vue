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
      <section v-show="activeProtocol === 'gb28181'" id="access-panel-gb28181" role="tabpanel" aria-labelledby="access-tab-gb28181">
        <div class="access-config-heading"><h2>国标GB28181配置</h2></div>
        <div class="access-certificate-toolbar">
          <button ref="gb28181OpenButton" class="btn primary" type="button" @click="openGb28181Dialog('add')">＋ 新增配置</button>
        </div>
        <div class="access-certificate-table-wrap">
          <table class="prototype-table access-certificate-table">
            <thead><tr><th>SIP ID</th><th>SIP 域</th><th>SIP IP</th><th>SIP 端口</th><th>收流端口范围</th><th>是否启用</th><th>更新时间</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="row in gb28181Entries" :key="row.id">
                <td>{{ row.sipId }}</td><td>{{ row.sipDomain }}</td><td>{{ row.sipIp }}</td><td>{{ row.sipPort }}</td><td>{{ row.receivePortStart }} ~ {{ row.receivePortEnd }}</td><td>{{ row.enabled ? "开启" : "关闭" }}</td><td>{{ formatDateTime(row.updatedAt) }}</td>
                <td><span class="access-cert-actions"><button class="link-blue" type="button" @click="openGb28181Dialog('edit', row)">编辑</button><button class="link-red" type="button" @click="removeGb28181Entry(row)">删除</button></span></td>
              </tr>
              <tr v-if="!gb28181Entries.length" class="access-certificate-empty">
                <td colspan="8"><div class="access-empty-state"><span class="access-empty-icon" aria-hidden="true">&#xf01c;</span><span>暂无数据</span></div></td>
              </tr>
            </tbody>
          </table>
        </div>
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
              <tr v-for="row in certificates" :key="row.id">
                <td>{{ row.id.slice(0, 8) }}</td><td>{{ row.deviceCode }}</td><td>{{ row.authMode }}</td><td>{{ formatDateTime(row.updatedAt) }}</td><td>{{ formatDateTime(row.createdAt) }}</td>
                <td><span class="access-cert-actions"><button class="link-blue" type="button" @click="viewCertificate(row)">查看</button><button class="link-red" type="button" @click="removeCertificate(row)">删除</button></span></td>
              </tr>
              <tr v-if="!certificates.length" class="access-certificate-empty">
                <td colspan="6"><div class="access-empty-state"><span class="access-empty-icon" aria-hidden="true">&#xf01c;</span><span>暂无数据</span></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-show="activeProtocol === 'ga1400'" id="access-panel-ga1400" role="tabpanel" aria-labelledby="access-tab-ga1400">
        <div class="access-config-heading"><h2>公安GA1400配置</h2></div>
        <div class="access-certificate-toolbar">
          <button ref="ga1400OpenButton" class="btn primary" type="button" @click="openGa1400Dialog('add')">＋ 新增配置</button>
        </div>
        <div class="access-certificate-table-wrap">
          <table class="prototype-table access-certificate-table">
            <thead><tr><th>平台 ID</th><th>平台 IP</th><th>端口</th><th>资源存储路径</th><th>自动接收注册</th><th>是否启用</th><th>更新时间</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="row in ga1400Entries" :key="row.id">
                <td>{{ row.platformId }}</td><td>{{ row.platformIp }}</td><td>{{ row.port }}</td><td>{{ row.resourcePath }}</td><td>{{ row.autoRegister ? "开启" : "关闭" }}</td><td>{{ row.enabled ? "开启" : "关闭" }}</td><td>{{ formatDateTime(row.updatedAt) }}</td>
                <td><span class="access-cert-actions"><button class="link-blue" type="button" @click="openGa1400Dialog('edit', row)">编辑</button><button class="link-red" type="button" @click="removeGa1400Entry(row)">删除</button></span></td>
              </tr>
              <tr v-if="!ga1400Entries.length" class="access-certificate-empty">
                <td colspan="8"><div class="access-empty-state"><span class="access-empty-icon" aria-hidden="true">&#xf01c;</span><span>暂无数据</span></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <section v-show="activeProtocol === 'cloud'" id="access-panel-cloud" role="tabpanel" aria-labelledby="access-tab-cloud">
        <div class="access-config-heading"><h2>云平台配置</h2></div>
        <cloud-platform-panel />
      </section>
    </div>

    <div v-if="certificateDialogOpen" class="access-modal-mask" role="presentation" @click.self="closeCertificateDialog" @keydown.esc="closeCertificateDialog" @keydown="trapCertificateFocus">
      <section ref="certificateDialog" class="access-modal" role="dialog" aria-modal="true" aria-labelledby="certificate-dialog-title">
        <header class="access-modal-head">
          <h3 id="certificate-dialog-title">{{ certificateDialogMode === 'view' ? '查看' : '添加' }}</h3>
          <button class="access-modal-close" type="button" aria-label="关闭" @click="closeCertificateDialog">×</button>
        </header>
        <form @submit.prevent="addCertificate">
        <div class="access-modal-body">
          <label class="access-field">
            <span class="access-field-label required">设备编码</span>
            <input ref="certificateCode" v-model.trim="certificateForm.deviceCode" class="input" maxlength="20" placeholder="请输入设备编码..." aria-label="设备编码" :disabled="certificateDialogMode === 'view'" :aria-invalid="!!certificateErrors.deviceCode" :aria-describedby="certificateErrors.deviceCode ? 'certificate-code-error' : null" @input="certificateErrors.deviceCode = ''" />
            <span v-if="certificateErrors.deviceCode" id="certificate-code-error" class="access-field-error" role="alert">{{ certificateErrors.deviceCode }}</span>
          </label>
          <label class="access-field">
            <span class="access-field-label required">设备证书</span>
            <textarea ref="certificateText" v-model="certificateForm.certificate" placeholder="请输入设备证书或上传证书..." aria-label="设备证书" :disabled="certificateDialogMode === 'view'" :aria-invalid="!!certificateErrors.certificate" :aria-describedby="certificateErrors.certificate ? 'certificate-text-error' : null" @input="certificateErrors.certificate = ''"></textarea>
            <span v-if="certificateErrors.certificate" id="certificate-text-error" class="access-field-error" role="alert">{{ certificateErrors.certificate }}</span>
          </label>
          <div v-if="certificateDialogMode !== 'view'" class="access-upload-actions">
            <input ref="certificateFile" class="access-upload-input" type="file" accept=".cer,.crt,.pem,.txt" @change="selectCertificateFile" />
            <button class="btn" type="button" @click="($refs.certificateFile as HTMLInputElement).click()">⇧ 上传设备证书</button>
            <span v-if="certificateForm.fileName" class="access-upload-name">{{ certificateForm.fileName }}</span>
          </div>
          <div class="access-field">
            <span class="access-field-label">认证方式</span>
            <span class="access-choice-group" role="group" aria-label="认证方式">
              <button class="access-choice" :class="{ active: certificateForm.authMode === '双向', enabled: certificateForm.authMode === '双向' }" type="button" :disabled="certificateDialogMode === 'view'" :aria-pressed="certificateForm.authMode === '双向'" @click="certificateForm.authMode = '双向'">双向</button>
              <button class="access-choice" :class="{ active: certificateForm.authMode === '单向' }" type="button" :disabled="certificateDialogMode === 'view'" :aria-pressed="certificateForm.authMode === '单向'" @click="certificateForm.authMode = '单向'">单向</button>
            </span>
          </div>
        </div>
        <footer class="access-modal-footer">
          <template v-if="certificateDialogMode === 'view'">
            <button class="btn" type="button" @click="closeCertificateDialog">关闭</button>
          </template>
          <template v-else>
            <button class="btn" type="button" @click="closeCertificateDialog">取消</button>
            <button class="btn primary" type="submit">确定</button>
          </template>
        </footer>
        </form>
      </section>
    </div>

    <div v-if="gb28181DialogOpen" class="access-modal-mask" role="presentation" @click.self="closeGb28181Dialog" @keydown.esc="closeGb28181Dialog" @keydown="trapGb28181Focus">
      <section ref="gb28181Dialog" class="access-modal" role="dialog" aria-modal="true" aria-labelledby="gb28181-dialog-title">
        <header class="access-modal-head">
          <h3 id="gb28181-dialog-title">{{ gb28181DialogMode === 'edit' ? '修改配置' : '新增配置' }}</h3>
          <button class="access-modal-close" type="button" aria-label="关闭" @click="closeGb28181Dialog">×</button>
        </header>
        <form @submit.prevent="saveGb28181Entry">
        <div class="access-modal-body">
          <div class="access-field">
            <span class="access-field-label">是否启用</span>
            <span class="access-choice-group" role="group" aria-label="是否启用GB28181">
              <button class="access-choice" :class="{ active: gb28181Form.enabled, enabled: gb28181Form.enabled }" type="button" :aria-pressed="gb28181Form.enabled" @click="gb28181Form.enabled = true">开启</button>
              <button class="access-choice" :class="{ active: !gb28181Form.enabled }" type="button" :aria-pressed="!gb28181Form.enabled" @click="gb28181Form.enabled = false">关闭</button>
            </span>
          </div>
          <label class="access-field">
            <span class="access-field-label required">SIP ID</span>
            <input ref="gb28181SipId" v-model.trim="gb28181Form.sipId" class="input" maxlength="20" aria-label="SIP ID" :aria-invalid="!!gb28181Errors.sipId" :aria-describedby="gb28181Errors.sipId ? 'gb28181-sip-id-error' : null" @input="gb28181Errors.sipId = ''" />
            <span v-if="gb28181Errors.sipId" id="gb28181-sip-id-error" class="access-field-error" role="alert">{{ gb28181Errors.sipId }}</span>
          </label>
          <label class="access-field">
            <span class="access-field-label required">SIP 域</span>
            <input v-model.trim="gb28181Form.sipDomain" class="input" maxlength="10" aria-label="SIP 域" :aria-invalid="!!gb28181Errors.sipDomain" :aria-describedby="gb28181Errors.sipDomain ? 'gb28181-domain-error' : null" @input="gb28181Errors.sipDomain = ''" />
            <span v-if="gb28181Errors.sipDomain" id="gb28181-domain-error" class="access-field-error" role="alert">{{ gb28181Errors.sipDomain }}</span>
          </label>
          <div class="access-field">
            <span class="access-field-label required">SIP IP</span>
            <span class="access-input-action">
              <input v-model="gb28181Form.sipIp" class="input" disabled aria-label="SIP IP" />
              <button class="access-field-button" type="button" @click="setNetworkIp('gb28181')">设置</button>
            </span>
          </div>
          <div class="access-field">
            <span class="access-field-label required">SIP 端口(TCP/UDP)</span>
            <span class="access-input-action">
              <input v-model.trim="gb28181Form.sipPort" class="input" inputmode="numeric" aria-label="SIP 端口" :aria-invalid="!!gb28181Errors.sipPort" :aria-describedby="gb28181Errors.sipPort ? 'gb28181-port-error' : null" @input="gb28181Errors.sipPort = ''" />
              <button class="access-field-button" type="button" @click="detectPort('gb28181')">检测</button>
            </span>
            <span v-if="gb28181Errors.sipPort" id="gb28181-port-error" class="access-field-error" role="alert">{{ gb28181Errors.sipPort }}</span>
          </div>
          <label class="access-field">
            <span class="access-field-label">设备统一接入密码</span>
            <input v-model="gb28181Form.password" class="input" type="password" autocomplete="new-password" aria-label="设备统一接入密码" />
          </label>
          <label class="access-field">
            <span class="access-field-label">上级联请求端口</span>
            <input v-model="gb28181Form.parentPort" class="input" disabled aria-label="上级联请求端口" />
          </label>
          <div class="access-field">
            <span class="access-field-label">收流端口范围</span>
            <span class="access-port-range">
              <input v-model.trim="gb28181Form.receivePortStart" class="input" inputmode="numeric" aria-label="收流起始端口" :aria-invalid="!!gb28181Errors.receivePorts" :aria-describedby="gb28181Errors.receivePorts ? 'gb28181-receive-port-error' : null" @input="gb28181Errors.receivePorts = ''" />
              <span>~</span>
              <input v-model.trim="gb28181Form.receivePortEnd" class="input" inputmode="numeric" aria-label="收流结束端口" :aria-invalid="!!gb28181Errors.receivePorts" :aria-describedby="gb28181Errors.receivePorts ? 'gb28181-receive-port-error' : null" @input="gb28181Errors.receivePorts = ''" />
            </span>
            <span v-if="gb28181Errors.receivePorts" id="gb28181-receive-port-error" class="access-field-error" role="alert">{{ gb28181Errors.receivePorts }}</span>
          </div>
        </div>
        <footer class="access-modal-footer">
          <button class="btn" type="button" @click="closeGb28181Dialog">取消</button>
          <button class="btn primary" type="submit">确定</button>
        </footer>
        </form>
      </section>
    </div>

    <div v-if="ga1400DialogOpen" class="access-modal-mask" role="presentation" @click.self="closeGa1400Dialog" @keydown.esc="closeGa1400Dialog" @keydown="trapGa1400Focus">
      <section ref="ga1400Dialog" class="access-modal" role="dialog" aria-modal="true" aria-labelledby="ga1400-dialog-title">
        <header class="access-modal-head">
          <h3 id="ga1400-dialog-title">{{ ga1400DialogMode === 'edit' ? '修改配置' : '新增配置' }}</h3>
          <button class="access-modal-close" type="button" aria-label="关闭" @click="closeGa1400Dialog">×</button>
        </header>
        <form @submit.prevent="saveGa1400Entry">
        <div class="access-modal-body">
          <div class="access-field">
            <span class="access-field-label">是否启用</span>
            <span class="access-choice-group" role="group" aria-label="是否启用GA1400">
              <button class="access-choice" :class="{ active: ga1400Form.enabled, enabled: ga1400Form.enabled }" type="button" :aria-pressed="ga1400Form.enabled" @click="ga1400Form.enabled = true">开启</button>
              <button class="access-choice" :class="{ active: !ga1400Form.enabled }" type="button" :aria-pressed="!ga1400Form.enabled" @click="ga1400Form.enabled = false">关闭</button>
            </span>
          </div>
          <label class="access-field">
            <span class="access-field-label required">平台 ID</span>
            <input ref="ga1400PlatformId" v-model.trim="ga1400Form.platformId" class="input" maxlength="20" aria-label="平台 ID" :aria-invalid="!!ga1400Errors.platformId" :aria-describedby="ga1400Errors.platformId ? 'ga1400-platform-id-error' : null" @input="ga1400Errors.platformId = ''" />
            <span v-if="ga1400Errors.platformId" id="ga1400-platform-id-error" class="access-field-error" role="alert">{{ ga1400Errors.platformId }}</span>
          </label>
          <div class="access-field">
            <span class="access-field-label required">平台 IP</span>
            <span class="access-input-action">
              <input v-model="ga1400Form.platformIp" class="input" disabled aria-label="平台 IP" />
              <button class="access-field-button" type="button" @click="setNetworkIp('ga1400')">设置</button>
            </span>
          </div>
          <div class="access-field">
            <span class="access-field-label required">端口</span>
            <span class="access-input-action">
              <input v-model.trim="ga1400Form.port" class="input" inputmode="numeric" aria-label="GA1400端口" :aria-invalid="!!ga1400Errors.port" :aria-describedby="ga1400Errors.port ? 'ga1400-port-error' : null" @input="ga1400Errors.port = ''" />
              <button class="access-field-button" type="button" @click="detectPort('ga1400')">检测</button>
            </span>
            <span v-if="ga1400Errors.port" id="ga1400-port-error" class="access-field-error" role="alert">{{ ga1400Errors.port }}</span>
          </div>
          <label class="access-field">
            <span class="access-field-label">设备统一接入密码</span>
            <input v-model="ga1400Form.password" class="input" type="text" autocomplete="off" aria-label="设备统一接入密码" />
          </label>
          <label class="access-field">
            <span class="access-field-label">资源存储路径</span>
            <input v-model.trim="ga1400Form.resourcePath" class="input" aria-label="资源存储路径" />
          </label>
          <div class="access-field">
            <span class="access-field-label">自动接收采集设备的注册</span>
            <span class="access-choice-group" role="group" aria-label="自动接收采集设备的注册">
              <button class="access-choice" :class="{ active: ga1400Form.autoRegister, enabled: ga1400Form.autoRegister }" type="button" :aria-pressed="ga1400Form.autoRegister" @click="ga1400Form.autoRegister = true">开启</button>
              <button class="access-choice" :class="{ active: !ga1400Form.autoRegister }" type="button" :aria-pressed="!ga1400Form.autoRegister" @click="ga1400Form.autoRegister = false">关闭</button>
            </span>
          </div>
        </div>
        <footer class="access-modal-footer">
          <button class="btn" type="button" @click="closeGa1400Dialog">取消</button>
          <button class="btn primary" type="submit">确定</button>
        </footer>
        </form>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import CloudPlatformPanel from "../components/CloudPlatformPanel.vue";

export default defineComponent({
  name: "MediaAccessConfigPage",
  components: { CloudPlatformPanel },
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
        { key: "ga1400", label: "公安GA1400" },
        { key: "cloud", label: "云平台" }
      ],
      gb28181Entries: (persisted.gb28181Entries || []).map((row: any) => ({ ...row })),
      certificates: persisted.certificates.map((row: any) => ({ ...row })),
      ga1400Entries: (persisted.ga1400Entries || []).map((row: any) => ({ ...row })),
      certificateDialogOpen: false,
      certificateDialogMode: "add" as "add" | "view",
      certificateForm: {
        deviceCode: "",
        certificate: "",
        authMode: "双向",
        fileName: ""
      },
      certificateErrors: {} as any,
      gb28181DialogOpen: false,
      gb28181DialogMode: "add" as "add" | "edit",
      gb28181Form: {
        enabled: true,
        sipId: "",
        sipDomain: "",
        sipIp: "",
        sipPort: "",
        password: "",
        parentPort: "",
        receivePortStart: "",
        receivePortEnd: ""
      },
      gb28181Errors: {} as any,
      editingGb28181Id: null as string | null,
      ga1400DialogOpen: false,
      ga1400DialogMode: "add" as "add" | "edit",
      ga1400Form: {
        enabled: true,
        platformId: "",
        platformIp: "",
        port: "",
        password: "",
        resourcePath: "",
        autoRegister: false
      },
      ga1400Errors: {} as any,
      editingGa1400Id: null as string | null
    };
  },
  async mounted() {
    const [gb28181Result, certificatesResult, ga1400Result] = await Promise.allSettled([api.gb28181Entries(), api.accessCertificates(), api.ga1400Entries()]);
    if (gb28181Result.status === "fulfilled") {
      this.gb28181Entries = (gb28181Result.value || []).map((row: any) => ({ ...row }));
      this.syncGb28181EntriesToStore();
    } else {
      this.showToast("GB28181 配置列表加载失败");
    }
    if (certificatesResult.status === "fulfilled") {
      this.certificates = (certificatesResult.value || []).map((row: any) => ({ ...row }));
      this.syncCertificatesToStore();
    } else {
      this.showToast("设备证书列表加载失败");
    }
    if (ga1400Result.status === "fulfilled") {
      this.ga1400Entries = (ga1400Result.value || []).map((row: any) => ({ ...row }));
      this.syncGa1400EntriesToStore();
    } else {
      this.showToast("GA1400 配置列表加载失败");
    }
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
    syncGb28181EntriesToStore() {
      (this as any).store.accessConfig.gb28181Entries = this.gb28181Entries.map(item => ({ ...item }));
    },
    syncCertificatesToStore() {
      (this as any).store.accessConfig.certificates = this.certificates.map(item => ({ ...item }));
    },
    syncGa1400EntriesToStore() {
      (this as any).store.accessConfig.ga1400Entries = this.ga1400Entries.map(item => ({ ...item }));
    },
    formatDateTime(value: any) {
      const date = new Date(value);
      if (isNaN(date.getTime())) return value == null ? "" : String(value);
      const pad = (v: number) => String(v).padStart(2, "0");
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    },
    async setNetworkIp(protocol: any) {
      const isGb28181 = protocol === "gb28181";
      const field = isGb28181 ? "sipIp" : "platformIp";
      const target: any = isGb28181 ? this.gb28181Form : this.ga1400Form;
      try {
        const result = await api.accessHostIps();
        const ip = result && result.ips && result.ips.length ? result.ips[0] : "";
        if (!ip) {
          this.showToast("未获取到本机网卡地址");
          return;
        }
        target[field] = ip;
        this.showToast(`已选择本机网卡地址 ${ip}`);
      } catch (error: any) {
        this.showToast(`获取本机网卡地址失败：${error && error.message ? error.message : "未知错误"}`);
      }
    },
    async detectPort(protocol: any) {
      const isGb28181 = protocol === "gb28181";
      const port = isGb28181 ? this.gb28181Form.sipPort : this.ga1400Form.port;
      if (!this.isValidPort(port)) {
        if (isGb28181) {
          this.gb28181Errors = { ...this.gb28181Errors, sipPort: "端口需为1-65535之间的整数" };
        } else {
          this.ga1400Errors = { ...this.ga1400Errors, port: "端口需为1-65535之间的整数" };
        }
        this.showToast("端口格式不正确，请输入1-65535之间的整数");
        return;
      }
      if (isGb28181) {
        this.gb28181Errors.sipPort = "";
      } else {
        this.ga1400Errors.port = "";
      }
      try {
        const result = await api.checkAccessPort(Number(port));
        this.showToast(result && result.available ? `端口 ${port} 检测通过，可以正常监听` : `端口 ${port} 已被占用，请更换端口`);
      } catch (error: any) {
        this.showToast(`端口检测失败：${error && error.message ? error.message : "未知错误"}`);
      }
    },
    openCertificateDialog() {
      this.certificateForm = { deviceCode: "", certificate: "", authMode: "双向", fileName: "" };
      this.certificateErrors = {};
      this.certificateDialogMode = "add";
      this.certificateDialogOpen = true;
      this.$nextTick(() => (this.$refs.certificateCode as any) && (this.$refs.certificateCode as any).focus());
    },
    viewCertificate(row: any) {
      this.certificateForm = {
        deviceCode: row.deviceCode || "",
        certificate: row.certificate || "",
        authMode: row.authMode || "双向",
        fileName: ""
      };
      this.certificateErrors = {};
      this.certificateDialogMode = "view";
      this.certificateDialogOpen = true;
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
    openGb28181Dialog(mode: any, row?: any) {
      this.gb28181DialogMode = mode === "edit" ? "edit" : "add";
      this.editingGb28181Id = mode === "edit" && row ? row.id : null;
      this.gb28181Form = mode === "edit" && row ? {
        enabled: !!row.enabled,
        sipId: row.sipId || "",
        sipDomain: row.sipDomain || "",
        sipIp: row.sipIp || "",
        sipPort: row.sipPort || "",
        password: row.password || "",
        parentPort: row.parentPort || "",
        receivePortStart: row.receivePortStart || "",
        receivePortEnd: row.receivePortEnd || ""
      } : {
        enabled: true,
        sipId: "",
        sipDomain: "",
        sipIp: "",
        sipPort: "",
        password: "",
        parentPort: "",
        receivePortStart: "",
        receivePortEnd: ""
      };
      this.gb28181Errors = {};
      this.gb28181DialogOpen = true;
      this.$nextTick(() => (this.$refs.gb28181SipId as any) && (this.$refs.gb28181SipId as any).focus());
    },
    closeGb28181Dialog() {
      this.gb28181DialogOpen = false;
      this.gb28181Errors = {};
      this.$nextTick(() => (this.$refs.gb28181OpenButton as any) && (this.$refs.gb28181OpenButton as any).focus());
    },
    trapGb28181Focus(event: any) {
      if (event.key !== "Tab" || !this.$refs.gb28181Dialog) return;
      const focusable = Array.from((this.$refs.gb28181Dialog as any).querySelectorAll("button:not(:disabled), input:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex='-1'])"))
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
    async saveGb28181Entry() {
      const errors: any = {};
      if (!/^\d{20}$/.test(this.gb28181Form.sipId.trim())) errors.sipId = "SIP ID 需为20位数字";
      if (!/^\d{10}$/.test(this.gb28181Form.sipDomain.trim())) errors.sipDomain = "SIP 域需为10位数字";
      if (!this.isValidPort(this.gb28181Form.sipPort)) errors.sipPort = "SIP 端口需为1-65535之间的整数";
      const start = Number(this.gb28181Form.receivePortStart);
      const end = Number(this.gb28181Form.receivePortEnd);
      if (!this.isValidPort(this.gb28181Form.receivePortStart) || !this.isValidPort(this.gb28181Form.receivePortEnd) || start > end) {
        errors.receivePorts = "请输入有效的收流端口范围（1-65535）";
      }
      this.gb28181Errors = errors;
      if (Object.keys(errors).length) {
        this.$nextTick(() => {
          const target: any = this.$refs.gb28181SipId;
          if (errors.sipId && target) target.focus();
        });
        return;
      }
      const payload = {
        enabled: this.gb28181Form.enabled,
        sipId: this.gb28181Form.sipId.trim(),
        sipDomain: this.gb28181Form.sipDomain.trim(),
        sipIp: this.gb28181Form.sipIp,
        sipPort: this.gb28181Form.sipPort.trim(),
        password: this.gb28181Form.password,
        parentPort: this.gb28181Form.parentPort,
        receivePortStart: this.gb28181Form.receivePortStart.trim(),
        receivePortEnd: this.gb28181Form.receivePortEnd.trim()
      };
      try {
        if (this.gb28181DialogMode === "edit" && this.editingGb28181Id) {
          const updated: any = await api.updateGb28181Entry(this.editingGb28181Id, payload);
          this.gb28181Entries = this.gb28181Entries.map(item => (item.id === updated.id ? { ...updated } : item));
        } else {
          const created: any = await api.createGb28181Entry(payload);
          this.gb28181Entries.unshift({ ...created });
        }
        this.syncGb28181EntriesToStore();
        this.closeGb28181Dialog();
        this.showToast("GB28181 配置已保存");
      } catch (error: any) {
        this.showToast(`GB28181 配置保存失败：${error && error.message ? error.message : "未知错误"}`);
      }
    },
    async removeGb28181Entry(row: any) {
      if (!window.confirm(`确定删除 GB28181 配置 ${row.sipId} 吗？`)) return;
      try {
        await api.deleteGb28181Entry(row.id);
        this.gb28181Entries = this.gb28181Entries.filter(item => item.id !== row.id);
        this.syncGb28181EntriesToStore();
        this.showToast(`GB28181 配置已删除：${row.sipId}`);
      } catch (error: any) {
        this.showToast(`GB28181 配置删除失败：${error && error.message ? error.message : "未知错误"}`);
      }
    },
    openGa1400Dialog(mode: any, row?: any) {
      this.ga1400DialogMode = mode === "edit" ? "edit" : "add";
      this.editingGa1400Id = mode === "edit" && row ? row.id : null;
      this.ga1400Form = mode === "edit" && row ? {
        enabled: !!row.enabled,
        platformId: row.platformId || "",
        platformIp: row.platformIp || "",
        port: row.port || "",
        password: row.password || "",
        resourcePath: row.resourcePath || "",
        autoRegister: !!row.autoRegister
      } : {
        enabled: true,
        platformId: "",
        platformIp: "",
        port: "",
        password: "",
        resourcePath: "",
        autoRegister: false
      };
      this.ga1400Errors = {};
      this.ga1400DialogOpen = true;
      this.$nextTick(() => (this.$refs.ga1400PlatformId as any) && (this.$refs.ga1400PlatformId as any).focus());
    },
    closeGa1400Dialog() {
      this.ga1400DialogOpen = false;
      this.ga1400Errors = {};
      this.$nextTick(() => (this.$refs.ga1400OpenButton as any) && (this.$refs.ga1400OpenButton as any).focus());
    },
    trapGa1400Focus(event: any) {
      if (event.key !== "Tab" || !this.$refs.ga1400Dialog) return;
      const focusable = Array.from((this.$refs.ga1400Dialog as any).querySelectorAll("button:not(:disabled), input:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex='-1'])"))
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
    async saveGa1400Entry() {
      const errors: any = {};
      if (!/^\d{20}$/.test(this.ga1400Form.platformId.trim())) errors.platformId = "平台 ID 需为20位数字";
      if (!this.isValidPort(this.ga1400Form.port)) errors.port = "端口需为1-65535之间的整数";
      this.ga1400Errors = errors;
      if (Object.keys(errors).length) {
        this.$nextTick(() => {
          const target: any = this.$refs.ga1400PlatformId;
          if (errors.platformId && target) target.focus();
        });
        return;
      }
      const payload = {
        enabled: this.ga1400Form.enabled,
        platformId: this.ga1400Form.platformId.trim(),
        platformIp: this.ga1400Form.platformIp,
        port: this.ga1400Form.port.trim(),
        password: this.ga1400Form.password,
        resourcePath: this.ga1400Form.resourcePath,
        autoRegister: this.ga1400Form.autoRegister
      };
      try {
        if (this.ga1400DialogMode === "edit" && this.editingGa1400Id) {
          const updated: any = await api.updateGa1400Entry(this.editingGa1400Id, payload);
          this.ga1400Entries = this.ga1400Entries.map(item => (item.id === updated.id ? { ...updated } : item));
        } else {
          const created: any = await api.createGa1400Entry(payload);
          this.ga1400Entries.unshift({ ...created });
        }
        this.syncGa1400EntriesToStore();
        this.closeGa1400Dialog();
        this.showToast("GA1400 配置已保存");
      } catch (error: any) {
        this.showToast(`GA1400 配置保存失败：${error && error.message ? error.message : "未知错误"}`);
      }
    },
    async removeGa1400Entry(row: any) {
      if (!window.confirm(`确定删除 GA1400 配置 ${row.platformId} 吗？`)) return;
      try {
        await api.deleteGa1400Entry(row.id);
        this.ga1400Entries = this.ga1400Entries.filter(item => item.id !== row.id);
        this.syncGa1400EntriesToStore();
        this.showToast(`GA1400 配置已删除：${row.platformId}`);
      } catch (error: any) {
        this.showToast(`GA1400 配置删除失败：${error && error.message ? error.message : "未知错误"}`);
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
    async addCertificate() {
      if (this.certificateDialogMode === "view") return;
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

      const code = this.certificateForm.deviceCode.trim();
      try {
        const created = await api.createAccessCertificate({
          deviceCode: code,
          certificate: this.certificateForm.certificate,
          authMode: this.certificateForm.authMode
        });
        this.certificates.unshift({ ...created });
        this.syncCertificatesToStore();
        this.closeCertificateDialog();
        this.showToast(`设备证书已添加：${code}`);
      } catch (error: any) {
        this.showToast(`设备证书添加失败：${error && error.message ? error.message : "未知错误"}`);
      }
    },
    async removeCertificate(row: any) {
      try {
        await api.deleteAccessCertificate(row.id);
        this.certificates = this.certificates.filter(item => item.id !== row.id);
        this.syncCertificatesToStore();
        this.showToast(`设备证书已删除：${row.deviceCode}`);
      } catch (error: any) {
        this.showToast(`设备证书删除失败：${error && error.message ? error.message : "未知错误"}`);
      }
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
