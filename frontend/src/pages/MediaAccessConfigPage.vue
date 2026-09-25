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
          <button ref="gb28181OpenButton" class="btn primary" type="button" @click="openGb28181Dialog('add')">＋ 新增级联服务器</button>
          <button ref="gbBaseOpenButton" class="btn ghost" type="button" @click="openGbBaseDialog">✎ 编辑基础服务器配置</button>
        </div>
        <div class="access-gb-section">
          <h3 class="access-gb-section-title">基础服务器配置</h3>
          <div class="access-gb-base-card">
            <div class="access-gb-base-icon" aria-hidden="true">▤</div>
            <dl class="access-gb-base-fields">
              <div v-for="item in gb28181BaseFields" :key="item.label" class="access-gb-base-field">
                <dt>{{ item.label }}</dt>
                <dd>{{ item.value || "-" }}</dd>
                <button v-if="item.value" class="access-gb-copy" type="button" :aria-label="'复制' + item.label" @click="copyText(item.value)">⧉</button>
              </div>
            </dl>
          </div>
        </div>
        <div class="access-gb-section">
          <h3 class="access-gb-section-title">级联服务器配置</h3>
          <div v-if="gb28181Entries.length" class="access-gb-cascade-list">
            <div v-for="row in gb28181Entries" :key="row.id" class="access-gb-cascade-card">
              <div class="access-gb-cascade-avatar" aria-hidden="true">▦</div>
              <div class="access-gb-cascade-info">
                <h4>{{ row.name || "-" }}</h4>
                <p>SIP 服务器地址：{{ row.sipIp }}</p>
                <p>SIP 服务器端口：{{ row.sipPort }}</p>
                <p>级联服务器SIP ID：{{ row.sipId || "-" }}</p>
                <p>用户名：{{ row.username }}</p>
                <p>密码：********</p>
                <p>状态：{{ onlineStatusLabel(row.onlineStatus) }}</p>
              </div>
              <div class="access-gb-cascade-actions">
                <button class="link-blue" type="button" @click="openGb28181Dialog('edit', row)">编辑</button>
                <button class="link-red" type="button" @click="removeGb28181Entry(row)">删除</button>
              </div>
            </div>
          </div>
          <div v-else class="access-empty-state access-gb-empty"><span class="access-empty-icon" aria-hidden="true">&#xf01c;</span><span>暂无级联服务器</span></div>
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
            <thead><tr><th>平台名称</th><th>平台 ID</th><th>平台 IP</th><th>端口</th><th>资源存储路径</th><th>自动接收注册</th><th>是否启用</th><th>更新时间</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="row in ga1400Entries" :key="row.id">
                <td>{{ row.name || "-" }}</td><td>{{ row.platformId }}</td><td>{{ row.platformIp }}</td><td>{{ row.port }}</td><td>{{ row.resourcePath }}</td><td>{{ row.autoRegister ? "开启" : "关闭" }}</td><td>{{ row.enabled ? "开启" : "关闭" }}</td><td>{{ formatDateTime(row.updatedAt) }}</td><td>{{ onlineStatusLabel(row.onlineStatus) }}</td>
                <td><span class="access-cert-actions"><button class="link-blue" type="button" @click="openGa1400Dialog('edit', row)">编辑</button><button class="link-red" type="button" @click="removeGa1400Entry(row)">删除</button></span></td>
              </tr>
              <tr v-if="!ga1400Entries.length" class="access-certificate-empty">
                <td colspan="10"><div class="access-empty-state"><span class="access-empty-icon" aria-hidden="true">&#xf01c;</span><span>暂无数据</span></div></td>
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
          <h3 id="gb28181-dialog-title">{{ gb28181DialogMode === 'edit' ? '编辑级联服务器' : '新增级联服务器' }}</h3>
          <button class="access-modal-close" type="button" aria-label="关闭" @click="closeGb28181Dialog">×</button>
        </header>
        <form @submit.prevent="saveGb28181Entry">
        <div class="access-modal-body">
          <label class="access-field">
            <span class="access-field-label required">级联服务器名称</span>
            <input ref="gb28181Name" v-model.trim="gb28181Form.name" class="input" maxlength="64" placeholder="请输入级联服务器名称" aria-label="级联服务器名称" :aria-invalid="!!gb28181Errors.name" :aria-describedby="gb28181Errors.name ? 'gb28181-name-error' : null" @input="gb28181Errors.name = ''" />
            <span v-if="gb28181Errors.name" id="gb28181-name-error" class="access-field-error" role="alert">{{ gb28181Errors.name }}</span>
          </label>
          <label class="access-field">
            <span class="access-field-label required">级联服务器IP</span>
            <input v-model.trim="gb28181Form.sipIp" class="input" maxlength="64" placeholder="请输入级联服务器IP" aria-label="级联服务器IP" :aria-invalid="!!gb28181Errors.sipIp" :aria-describedby="gb28181Errors.sipIp ? 'gb28181-ip-error' : null" @input="gb28181Errors.sipIp = ''" />
            <span v-if="gb28181Errors.sipIp" id="gb28181-ip-error" class="access-field-error" role="alert">{{ gb28181Errors.sipIp }}</span>
          </label>
          <label class="access-field">
            <span class="access-field-label required">级联服务器端口</span>
            <input v-model.trim="gb28181Form.sipPort" class="input" inputmode="numeric" maxlength="5" placeholder="请输入级联服务器端口" aria-label="级联服务器端口" :aria-invalid="!!gb28181Errors.sipPort" :aria-describedby="gb28181Errors.sipPort ? 'gb28181-port-error' : null" @input="gb28181Errors.sipPort = ''" />
            <span v-if="gb28181Errors.sipPort" id="gb28181-port-error" class="access-field-error" role="alert">{{ gb28181Errors.sipPort }}</span>
          </label>
          <label class="access-field">
            <span class="access-field-label">级联服务器SIP ID</span>
            <input v-model.trim="gb28181Form.sipId" class="input" maxlength="64" placeholder="请输入级联服务器SIP ID（选填）" aria-label="级联服务器SIP ID" />
          </label>
          <label class="access-field">
            <span class="access-field-label required">用户名</span>
            <input v-model.trim="gb28181Form.username" class="input" maxlength="64" placeholder="请输入用户名" aria-label="用户名" :aria-invalid="!!gb28181Errors.username" :aria-describedby="gb28181Errors.username ? 'gb28181-username-error' : null" @input="gb28181Errors.username = ''" />
            <span v-if="gb28181Errors.username" id="gb28181-username-error" class="access-field-error" role="alert">{{ gb28181Errors.username }}</span>
          </label>
          <div class="access-field">
            <span class="access-field-label required">密码</span>
            <span class="access-input-action">
              <input v-model="gb28181Form.password" class="input" :type="gb28181ShowPassword ? 'text' : 'password'" autocomplete="new-password" maxlength="128" placeholder="请输入密码" aria-label="密码" :aria-invalid="!!gb28181Errors.password" :aria-describedby="gb28181Errors.password ? 'gb28181-password-error' : null" @input="gb28181Errors.password = ''" />
              <button class="access-field-button" type="button" :aria-label="gb28181ShowPassword ? '隐藏密码' : '显示密码'" :aria-pressed="gb28181ShowPassword" @click="gb28181ShowPassword = !gb28181ShowPassword">{{ gb28181ShowPassword ? '隐藏' : '显示' }}</button>
            </span>
            <span v-if="gb28181Errors.password" id="gb28181-password-error" class="access-field-error" role="alert">{{ gb28181Errors.password }}</span>
          </div>
        </div>
        <footer class="access-modal-footer">
          <button class="btn" type="button" @click="closeGb28181Dialog">取消</button>
          <button class="btn primary" type="submit">确定</button>
        </footer>
        </form>
      </section>
    </div>

    <div v-if="gbBaseDialogOpen" class="access-modal-mask" role="presentation" @click.self="closeGbBaseDialog" @keydown.esc="closeGbBaseDialog" @keydown="trapGbBaseFocus">
      <section ref="gbBaseDialog" class="access-modal" role="dialog" aria-modal="true" aria-labelledby="gb-base-dialog-title">
        <header class="access-modal-head">
          <h3 id="gb-base-dialog-title">编辑基础服务器配置</h3>
          <button class="access-modal-close" type="button" aria-label="关闭" @click="closeGbBaseDialog">×</button>
        </header>
        <form @submit.prevent="saveGbBaseConfig">
        <div class="access-modal-body">
          <div class="access-field">
            <span class="access-field-label">是否启用</span>
            <span class="access-choice-group" role="group" aria-label="是否启用GB28181">
              <button class="access-choice" :class="{ active: gbBaseForm.enabled, enabled: gbBaseForm.enabled }" type="button" :aria-pressed="gbBaseForm.enabled" @click="gbBaseForm.enabled = true">开启</button>
              <button class="access-choice" :class="{ active: !gbBaseForm.enabled }" type="button" :aria-pressed="!gbBaseForm.enabled" @click="gbBaseForm.enabled = false">关闭</button>
            </span>
          </div>
          <label class="access-field">
            <span class="access-field-label required">SIP ID</span>
            <input ref="gbBaseSipId" v-model.trim="gbBaseForm.sipId" class="input" maxlength="20" aria-label="SIP ID" :aria-invalid="!!gbBaseErrors.sipId" :aria-describedby="gbBaseErrors.sipId ? 'gb-base-sip-id-error' : null" @input="gbBaseErrors.sipId = ''" />
            <span v-if="gbBaseErrors.sipId" id="gb-base-sip-id-error" class="access-field-error" role="alert">{{ gbBaseErrors.sipId }}</span>
          </label>
          <label class="access-field">
            <span class="access-field-label required">SIP 域</span>
            <input v-model.trim="gbBaseForm.sipDomain" class="input" maxlength="10" aria-label="SIP 域" :aria-invalid="!!gbBaseErrors.sipDomain" :aria-describedby="gbBaseErrors.sipDomain ? 'gb-base-domain-error' : null" @input="gbBaseErrors.sipDomain = ''" />
            <span v-if="gbBaseErrors.sipDomain" id="gb-base-domain-error" class="access-field-error" role="alert">{{ gbBaseErrors.sipDomain }}</span>
          </label>
          <div class="access-field">
            <span class="access-field-label required">SIP IP</span>
            <span class="access-input-action">
              <input v-model="gbBaseForm.sipIp" class="input" disabled aria-label="SIP IP" />
              <button class="access-field-button" type="button" @click="setNetworkIp('gb28181')">设置</button>
            </span>
          </div>
          <div class="access-field">
            <span class="access-field-label required">SIP 端口(TCP/UDP)</span>
            <span class="access-input-action">
              <input v-model.trim="gbBaseForm.sipPort" class="input" inputmode="numeric" aria-label="SIP 端口" :aria-invalid="!!gbBaseErrors.sipPort" :aria-describedby="gbBaseErrors.sipPort ? 'gb-base-port-error' : null" @input="gbBaseErrors.sipPort = ''" />
              <button class="access-field-button" type="button" @click="detectPort('gb28181')">检测</button>
            </span>
            <span v-if="gbBaseErrors.sipPort" id="gb-base-port-error" class="access-field-error" role="alert">{{ gbBaseErrors.sipPort }}</span>
          </div>
          <label class="access-field">
            <span class="access-field-label">设备统一接入密码</span>
            <input v-model="gbBaseForm.password" class="input" type="password" autocomplete="new-password" aria-label="设备统一接入密码" />
          </label>
          <label class="access-field">
            <span class="access-field-label">上级联请求端口</span>
            <input v-model="gbBaseForm.parentPort" class="input" disabled aria-label="上级联请求端口" />
          </label>
          <div class="access-field">
            <span class="access-field-label required">收流端口范围</span>
            <span class="access-port-range">
              <input v-model.trim="gbBaseForm.receivePortStart" class="input" inputmode="numeric" aria-label="收流起始端口" :aria-invalid="!!gbBaseErrors.receivePorts" :aria-describedby="gbBaseErrors.receivePorts ? 'gb-base-receive-port-error' : null" @input="gbBaseErrors.receivePorts = ''" />
              <span>~</span>
              <input v-model.trim="gbBaseForm.receivePortEnd" class="input" inputmode="numeric" aria-label="收流结束端口" :aria-invalid="!!gbBaseErrors.receivePorts" :aria-describedby="gbBaseErrors.receivePorts ? 'gb-base-receive-port-error' : null" @input="gbBaseErrors.receivePorts = ''" />
            </span>
            <span v-if="gbBaseErrors.receivePorts" id="gb-base-receive-port-error" class="access-field-error" role="alert">{{ gbBaseErrors.receivePorts }}</span>
          </div>
        </div>
        <footer class="access-modal-footer">
          <button class="btn" type="button" @click="closeGbBaseDialog">取消</button>
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
            <span class="access-field-label">平台名称</span>
            <input v-model.trim="ga1400Form.name" class="input" maxlength="64" placeholder="请输入平台名称" aria-label="平台名称" />
          </label>
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
        name: "",
        sipIp: "",
        sipPort: "",
        sipId: "",
        username: "",
        password: ""
      },
      gb28181Errors: {} as any,
      gb28181ShowPassword: false,
      editingGb28181Id: null as string | null,
      gb28181Base: { ...(persisted.gb28181 || {}) } as any,
      gbBaseDialogOpen: false,
      gbBaseForm: {
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
      gbBaseErrors: {} as any,
      ga1400DialogOpen: false,
      ga1400DialogMode: "add" as "add" | "edit",
      ga1400Form: {
        enabled: true,
        name: "",
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
    const [accessConfigResult, gb28181Result, certificatesResult, ga1400Result] = await Promise.allSettled([api.accessConfig(), api.gb28181Entries(), api.accessCertificates(), api.ga1400Entries()]);
    if (accessConfigResult.status === "fulfilled" && accessConfigResult.value && accessConfigResult.value.gb28181) {
      this.gb28181Base = { ...accessConfigResult.value.gb28181 };
      this.syncGb28181BaseToStore();
    } else if (accessConfigResult.status === "rejected") {
      this.showToast("GB28181 基础服务器配置加载失败");
    }
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
  computed: {
    gb28181BaseFields(): any[] {
      return [
        { label: "SIP 服务器ID", value: this.gb28181Base.sipId },
        { label: "SIP 服务域", value: this.gb28181Base.sipDomain },
        { label: "SIP 服务器地址", value: this.gb28181Base.sipIp },
        { label: "SIP 服务器端口", value: this.gb28181Base.sipPort }
      ];
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
    onlineStatusLabel(status: any) {
      if (status === "ONLINE") return "在线";
      if (status === "OFFLINE") return "离线";
      return "未知";
    },
    syncGb28181EntriesToStore() {
      (this as any).store.accessConfig.gb28181Entries = this.gb28181Entries.map(item => ({ ...item }));
    },
    syncGb28181BaseToStore() {
      (this as any).store.accessConfig.gb28181 = { ...this.gb28181Base };
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
      const target: any = isGb28181 ? this.gbBaseForm : this.ga1400Form;
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
      const port = isGb28181 ? this.gbBaseForm.sipPort : this.ga1400Form.port;
      if (!this.isValidPort(port)) {
        if (isGb28181) {
          this.gbBaseErrors = { ...this.gbBaseErrors, sipPort: "端口需为1-65535之间的整数" };
        } else {
          this.ga1400Errors = { ...this.ga1400Errors, port: "端口需为1-65535之间的整数" };
        }
        this.showToast("端口格式不正确，请输入1-65535之间的整数");
        return;
      }
      if (isGb28181) {
        this.gbBaseErrors.sipPort = "";
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
        name: row.name || "",
        sipIp: row.sipIp || "",
        sipPort: row.sipPort || "",
        sipId: row.sipId || "",
        username: row.username || "",
        password: row.password || ""
      } : {
        name: "",
        sipIp: "",
        sipPort: "",
        sipId: "",
        username: "",
        password: ""
      };
      this.gb28181Errors = {};
      this.gb28181ShowPassword = false;
      this.gb28181DialogOpen = true;
      this.$nextTick(() => (this.$refs.gb28181Name as any) && (this.$refs.gb28181Name as any).focus());
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
      if (!this.gb28181Form.name.trim()) errors.name = "请输入级联服务器名称";
      if (!this.gb28181Form.sipIp.trim()) errors.sipIp = "请输入级联服务器IP";
      if (!this.isValidPort(this.gb28181Form.sipPort)) errors.sipPort = "端口需为1-65535之间的整数";
      if (!this.gb28181Form.username.trim()) errors.username = "请输入用户名";
      if (!this.gb28181Form.password.trim()) errors.password = "请输入密码";
      this.gb28181Errors = errors;
      if (Object.keys(errors).length) {
        this.$nextTick(() => {
          const target: any = this.$refs.gb28181Name;
          if (errors.name && target) target.focus();
        });
        return;
      }
      const payload = {
        name: this.gb28181Form.name.trim(),
        sipIp: this.gb28181Form.sipIp.trim(),
        sipPort: this.gb28181Form.sipPort.trim(),
        sipId: this.gb28181Form.sipId.trim(),
        username: this.gb28181Form.username.trim(),
        password: this.gb28181Form.password
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
        this.showToast("级联服务器配置已保存");
      } catch (error: any) {
        this.showToast(`级联服务器配置保存失败：${error && error.message ? error.message : "未知错误"}`);
      }
    },
    async removeGb28181Entry(row: any) {
      if (!window.confirm(`确定删除级联服务器 ${row.name || row.sipIp} 吗？`)) return;
      try {
        await api.deleteGb28181Entry(row.id);
        this.gb28181Entries = this.gb28181Entries.filter(item => item.id !== row.id);
        this.syncGb28181EntriesToStore();
        this.showToast(`级联服务器已删除：${row.name || row.sipIp}`);
      } catch (error: any) {
        this.showToast(`级联服务器删除失败：${error && error.message ? error.message : "未知错误"}`);
      }
    },
    async copyText(value: any) {
      const text = String(value == null ? "" : value);
      if (!text) return;
      try {
        await navigator.clipboard.writeText(text);
        this.showToast("已复制到剪贴板");
      } catch (error) {
        this.showToast("复制失败，请手动复制");
      }
    },
    openGbBaseDialog() {
      this.gbBaseForm = {
        enabled: !!this.gb28181Base.enabled,
        sipId: this.gb28181Base.sipId || "",
        sipDomain: this.gb28181Base.sipDomain || "",
        sipIp: this.gb28181Base.sipIp || "",
        sipPort: this.gb28181Base.sipPort || "",
        password: this.gb28181Base.password || "",
        parentPort: this.gb28181Base.parentPort || "",
        receivePortStart: this.gb28181Base.receivePortStart || "",
        receivePortEnd: this.gb28181Base.receivePortEnd || ""
      };
      this.gbBaseErrors = {};
      this.gbBaseDialogOpen = true;
      this.$nextTick(() => (this.$refs.gbBaseSipId as any) && (this.$refs.gbBaseSipId as any).focus());
    },
    closeGbBaseDialog() {
      this.gbBaseDialogOpen = false;
      this.gbBaseErrors = {};
      this.$nextTick(() => (this.$refs.gbBaseOpenButton as any) && (this.$refs.gbBaseOpenButton as any).focus());
    },
    trapGbBaseFocus(event: any) {
      if (event.key !== "Tab" || !this.$refs.gbBaseDialog) return;
      const focusable = Array.from((this.$refs.gbBaseDialog as any).querySelectorAll("button:not(:disabled), input:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex='-1'])"))
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
    async saveGbBaseConfig() {
      const errors: any = {};
      if (!/^\d{20}$/.test(this.gbBaseForm.sipId.trim())) errors.sipId = "SIP ID 需为20位数字";
      if (!/^\d{10}$/.test(this.gbBaseForm.sipDomain.trim())) errors.sipDomain = "SIP 域需为10位数字";
      if (!this.isValidPort(this.gbBaseForm.sipPort)) errors.sipPort = "SIP 端口需为1-65535之间的整数";
      const start = Number(this.gbBaseForm.receivePortStart);
      const end = Number(this.gbBaseForm.receivePortEnd);
      if (!this.isValidPort(this.gbBaseForm.receivePortStart) || !this.isValidPort(this.gbBaseForm.receivePortEnd) || start > end) {
        errors.receivePorts = "请输入有效的收流端口范围（1-65535）";
      }
      this.gbBaseErrors = errors;
      if (Object.keys(errors).length) {
        this.$nextTick(() => {
          const target: any = this.$refs.gbBaseSipId;
          if (errors.sipId && target) target.focus();
        });
        return;
      }
      const payload = {
        enabled: this.gbBaseForm.enabled,
        sipId: this.gbBaseForm.sipId.trim(),
        sipDomain: this.gbBaseForm.sipDomain.trim(),
        sipIp: this.gbBaseForm.sipIp,
        sipPort: this.gbBaseForm.sipPort.trim(),
        password: this.gbBaseForm.password,
        parentPort: this.gbBaseForm.parentPort,
        receivePortStart: this.gbBaseForm.receivePortStart.trim(),
        receivePortEnd: this.gbBaseForm.receivePortEnd.trim()
      };
      try {
        const saved: any = await api.saveGb28181Config(payload);
        this.gb28181Base = { ...saved };
        this.syncGb28181BaseToStore();
        this.closeGbBaseDialog();
        this.showToast("基础服务器配置已保存");
      } catch (error: any) {
        this.showToast(`基础服务器配置保存失败：${error && error.message ? error.message : "未知错误"}`);
      }
    },
    openGa1400Dialog(mode: any, row?: any) {
      this.ga1400DialogMode = mode === "edit" ? "edit" : "add";
      this.editingGa1400Id = mode === "edit" && row ? row.id : null;
      this.ga1400Form = mode === "edit" && row ? {
        enabled: !!row.enabled,
        name: row.name || "",
        platformId: row.platformId || "",
        platformIp: row.platformIp || "",
        port: row.port || "",
        password: row.password || "",
        resourcePath: row.resourcePath || "",
        autoRegister: !!row.autoRegister
      } : {
        enabled: true,
        name: "",
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
        name: this.ga1400Form.name.trim(),
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
