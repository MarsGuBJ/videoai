<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>权限中心</h1><p>统一管理角色、菜单权限、数据范围与用户授权</p></div><button class="btn primary" @click="openModal('permissionRole')">新建角色</button></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="permission-layout">
      <aside class="role-panel">
        <div class="page-actions" style="margin-bottom:0;"><div class="left"><input class="input" style="width:190px;" placeholder="搜索角色名称" /></div><div class="right"><button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button></div></div>
        <div class="role-list">
          <button class="role-card" v-for="role in store.permissionRoles" :key="role.code" :class="{ active: activeRoleCode === role.code }" @click="activeRoleCode = role.code">
            <h4>{{ role.name }}<span class="status-pill" :class="statusClass(role.status)">{{ role.status }}</span></h4>
            <p>{{ role.desc }}</p>
            <div class="role-meta"><span>{{ role.code }}</span><span>{{ role.users }} 人</span></div>
          </button>
        </div>
      </aside>
      <section class="permission-panel">
        <div class="permission-head">
          <div><h3>{{ selectedRole.name }}</h3><p>{{ selectedRole.desc }}</p><div class="tags"><span class="tag blue">{{ selectedRole.code }}</span><span class="tag">{{ selectedRole.scope }}</span><span class="tag">更新：{{ selectedRole.updated }}</span></div></div>
          <div class="segmented"><button class="btn" @click="openModal('permissionRole')">编辑角色</button><button class="btn primary" @click="showToast('角色权限已模拟保存')">保存权限</button></div>
        </div>
        <div class="permission-section-grid">
          <div class="permission-block">
            <h4>菜单权限</h4>
            <div class="permission-tree">
              <div class="tree-group" v-for="group in store.permissionTree" :key="group.group">
                <label class="tree-parent"><input type="checkbox" checked />{{ group.group }}</label>
                <div class="tree-children"><label v-for="item in group.items" :key="item"><input type="checkbox" checked />{{ item }}</label></div>
              </div>
            </div>
          </div>
          <div class="permission-block">
            <h4>数据范围</h4>
            <div class="scope-list">
              <label><input type="radio" name="dataScope" :checked="selectedRole.scope === '全部数据'" />全部数据</label>
              <label><input type="radio" name="dataScope" :checked="selectedRole.scope === '安防中心'" />安防中心</label>
              <label><input type="radio" name="dataScope" :checked="selectedRole.scope === '算法组'" />算法组</label>
              <label><input type="radio" name="dataScope" :checked="selectedRole.scope === '万物核'" />万物核</label>
              <label><input type="radio" name="dataScope" :checked="selectedRole.scope === '只读演示'" />只读演示</label>
            </div>
            <div class="config-note" style="margin:14px 0 0;"><strong>权限策略</strong><span>菜单权限控制页面入口，数据范围控制事件、任务、资源和日志的可见数据。</span></div>
          </div>
        </div>
        <div class="permission-block">
          <div class="table-head" style="padding:0 0 12px; border-bottom:0;"><h3>授权用户</h3><button class="btn" @click="showToast('授权用户选择框已模拟打开')">添加用户</button></div>
          <div class="member-list">
            <div class="member-item" v-for="user in assignedUsers" :key="user.account">
              <span class="member-avatar">{{ user.name.slice(0, 1) }}</span>
              <div><h5>{{ user.name }}</h5><p>{{ user.account }} · {{ user.dept }}</p></div>
              <span class="status-pill" :class="statusClass(user.status)">{{ user.status }}</span>
            </div>
            <div v-if="!assignedUsers.length" class="hint-text" style="padding:20px; text-align:center;">当前角色暂无授权用户</div>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";

// Template calls injected members bare; declare them so vue-tsc accepts that.
declare module "vue" {
  interface ComponentCustomProperties {
    openModal: (name: string, payload?: any) => void;
    showToast: (message: string) => void;
  }
}

export default defineComponent({
  name: "PermissionsPage",
  components: { SummaryCards },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    openModal: { from: "openModal", default: (name: string) => {} },
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  data() {
    return { activeRoleCode: "SYSTEM_ADMIN" };
  },
  computed: {
    selectedRole(): any {
      return this.store.permissionRoles.find((row: any) => row.code === this.activeRoleCode) || this.store.permissionRoles[0];
    },
    assignedUsers(): any[] {
      return this.store.permissionUsers.filter((row: any) => row.role === this.selectedRole.name);
    },
    cards(): any[] {
      return [
        { label: "角色总数", value: this.store.permissionRoles.length },
        { label: "启用角色", value: this.store.permissionRoles.filter((row: any) => row.status === "启用").length },
        { label: "授权用户", value: this.store.permissionUsers.length },
        { label: "权限分组", value: this.store.permissionTree.length }
      ];
    }
  }
});
</script>
