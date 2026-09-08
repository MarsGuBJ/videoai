<template>
  <div>
    <div class="event-config-page-board">
      <div class="event-config-filter"><div class="event-config-filter-left"><button class="btn primary" @click="openCreate">＋ 新增平台</button><button class="btn primary" @click="loadPlatforms">查询</button><button class="btn" @click="reset">重置</button><input v-model="keyword" class="input" style="width:260px;" placeholder="请输入平台名称" /></div></div>
      <div class="table-wrap"><table class="prototype-table"><thead><tr><th class="left">平台名称</th><th>平台类型</th><th class="left">Key</th><th>密钥</th><th class="left">IP</th><th>端口</th><th>更新时间</th><th>操作</th></tr></thead><tbody><tr v-for="row in paginatedRows" :key="row.id"><td class="left">{{ row.name }}</td><td>{{ row.type }}</td><td class="left"><code>{{ row.key }}</code></td><td>******</td><td class="left">{{ row.ip }}</td><td>{{ row.port }}</td><td>{{ formatTime(row.updatedAt) }}</td><td><div class="event-config-actions"><button class="link-blue" @click="openEdit(row)">编辑</button><button class="link-blue danger" @click="remove(row)">删除</button></div></td></tr><tr v-if="!loading && !paginatedRows.length"><td colspan="8" class="empty-cell">暂无云平台配置</td></tr><tr v-if="loading"><td colspan="8" class="empty-cell">加载中...</td></tr></tbody></table></div>
      <div class="event-config-pagination"><span style="color:#98a2b3;font-size:11px;margin-right:auto;">共 {{ filteredRows.length }} 条</span><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in pageCount" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><button type="button" aria-label="下一页" :disabled="activePage === pageCount" @click="activePage++">›</button><select class="select" v-model.number="pageSize" aria-label="每页条数" @change="activePage = 1"><option :value="10">10条/页</option><option :value="20">20条/页</option><option :value="50">50条/页</option></select></div>
    </div>
    <div v-if="modalOpen" class="event-config-modal-mask" @click.self="closeForm">
      <section class="event-config-modal wide" role="dialog" aria-modal="true" :aria-label="editing ? '编辑云平台' : '新增云平台'">
        <div class="event-config-modal-head"><h3>{{ editing ? "编辑云平台" : "新增云平台" }}</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeForm">×</button></div>
        <div class="event-config-form-grid cols-3">
          <label class="event-config-field"><span>* 平台名称</span><input v-model="form.name" class="input" placeholder="请输入平台名称" /></label>
          <label class="event-config-field"><span>* 平台类型</span><select v-model="form.type" class="select"><option value="" disabled>请选择平台类型</option><option v-for="option in typeOptions" :key="option">{{ option }}</option></select></label>
          <label class="event-config-field"><span>* Key</span><input v-model="form.key" class="input" placeholder="请输入平台 Key" /></label>
          <label class="event-config-field"><span>* 密钥</span><input v-model="form.secret" type="password" class="input" placeholder="请输入平台密钥" /></label>
          <label class="event-config-field"><span>* IP</span><input v-model="form.ip" class="input" placeholder="请输入平台 IP 地址" /></label>
          <label class="event-config-field"><span>* 端口</span><input v-model="form.port" class="input" placeholder="请输入端口号" /></label>
        </div>
        <div class="event-config-modal-actions"><button class="btn" @click="closeForm">取消</button><button class="btn primary" :disabled="saving" @click="save">保存</button></div>
      </section>
    </div>
  </div>
</template>

<script lang="ts">
// 云平台配置面板：原 MediaCloudConfigPage 内容，作为「接入配置」页的 tab 嵌入。
import { defineComponent } from "vue";
import { api } from "../api";
import type { CloudPlatform } from "../types";

function pad2(n: number) {
  return n.toString().padStart(2, "0");
}

function formatDateTime(value?: string): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

export default defineComponent({
  name: "CloudPlatformPanel",
  inject: {
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      keyword: "",
      activePage: 1,
      pageSize: 10,
      rows: [] as CloudPlatform[],
      loading: false,
      saving: false,
      modalOpen: false,
      editing: null as CloudPlatform | null,
      typeOptions: ["省级视频云平台", "集团云平台", "第三方安防云"],
      form: { name: "", type: "", key: "", secret: "", ip: "", port: "" }
    };
  },
  computed: {
    filteredRows(): CloudPlatform[] {
      const value = this.keyword.trim().toLowerCase();
      return value ? this.rows.filter(row => `${row.name}${row.type}${row.ip}`.toLowerCase().includes(value)) : this.rows;
    },
    pageCount(): number {
      return Math.max(1, Math.ceil(this.filteredRows.length / this.pageSize));
    },
    paginatedRows(): CloudPlatform[] {
      const start = (this.activePage - 1) * this.pageSize;
      return this.filteredRows.slice(start, start + this.pageSize);
    }
  },
  mounted() {
    this.loadPlatforms();
  },
  methods: {
    formatTime: formatDateTime,
    reset() { this.keyword = ""; this.activePage = 1; },
    async loadPlatforms() {
      if (this.loading) return;
      this.loading = true;
      try {
        this.rows = await api.cloudPlatforms();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "云平台配置加载失败");
      } finally {
        this.loading = false;
      }
    },
    blankForm() {
      return { name: "", type: "", key: "", secret: "", ip: "", port: "" };
    },
    openCreate() { this.editing = null; this.form = this.blankForm(); this.modalOpen = true; },
    openEdit(row: CloudPlatform) {
      this.editing = row;
      this.form = { name: row.name, type: row.type, key: row.key, secret: row.secret, ip: row.ip, port: row.port };
      this.modalOpen = true;
    },
    closeForm() { this.modalOpen = false; },
    async save() {
      const form = { name: this.form.name.trim(), type: this.form.type, key: this.form.key.trim(), secret: this.form.secret.trim(), ip: this.form.ip.trim(), port: this.form.port.trim() };
      if (!form.name || !form.type || !form.key || !form.secret || !form.ip || !form.port) {
        this.showToast("请完整填写平台名称、类型、Key、密钥、IP 和端口");
        return;
      }
      if (this.saving) return;
      this.saving = true;
      try {
        if (this.editing) {
          await api.updateCloudPlatform(this.editing.id, form);
          this.showToast(`云平台已更新：${form.name}`);
        } else {
          await api.createCloudPlatform(form);
          this.showToast(`云平台已保存：${form.name}`);
        }
        this.closeForm();
        await this.loadPlatforms();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "云平台保存失败");
      } finally {
        this.saving = false;
      }
    },
    async remove(row: CloudPlatform) {
      try {
        await api.deleteCloudPlatform(row.id);
        this.showToast(`已删除云平台：${row.name}`);
        if (this.activePage > 1 && this.paginatedRows.length === 1) this.activePage--;
        await this.loadPlatforms();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "云平台删除失败");
      }
    }
  }
});
</script>
