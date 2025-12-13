<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <p class="eyebrow">SpaceNose · Ground Lab</p>
        <h1>星际嗅探者 · 地面验证实验台</h1>
        <p class="subtitle">模拟探测 + 实时数据接入 + 阈值告警 + 报告导出（Year 1 展示用）</p>
      </div>
      <div class="top-actions">
        <el-button text @click="router.push('/')">实验台</el-button>
        <el-button type="primary" @click="router.push('/visualization')">实时监控</el-button>
      </div>
    </header>

    <el-menu
      mode="horizontal"
      :default-active="activePath"
      router
      class="nav-menu"
      background-color="transparent"
      active-text-color="#4f46e5"
      text-color="#4b5563"
    >
      <el-menu-item index="/">实验台</el-menu-item>
      <el-menu-item index="/visualization">实时监控</el-menu-item>
    </el-menu>

    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const activePath = computed(() => route.path)
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: radial-gradient(circle at 20% 20%, #eef2ff 0, #f8fafc 35%, #ffffff 70%);
  color: #111827;
}

.topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 28px 40px 10px;
  gap: 24px;
}

.brand {
  max-width: 880px;
}

.eyebrow {
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #6b7280;
  font-size: 12px;
  margin: 0 0 6px;
}

.brand h1 {
  margin: 0;
  font-size: 28px;
  color: #0f172a;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.subtitle {
  margin: 8px 0 0;
  color: #4b5563;
  line-height: 1.6;
  max-width: 760px;
}

.top-actions {
  display: flex;
  gap: 10px;
  padding-top: 6px;
}

.nav-menu {
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.06);
  padding-left: 32px;
}

.content {
  padding: 18px 28px 40px;
}

@media (max-width: 960px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .nav-menu {
    padding-left: 14px;
  }
}
</style>
