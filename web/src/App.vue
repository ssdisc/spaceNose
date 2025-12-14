<template>
  <div class="app-shell">
    <!-- 星空背景层 -->
    <div class="starfield">
      <div class="stars stars-1"></div>
      <div class="stars stars-2"></div>
      <div class="stars stars-3"></div>
    </div>

    <header class="topbar">
      <div class="brand">
        <div class="logo-row">
          <div class="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="18" stroke="url(#logoGradient)" stroke-width="2" fill="none"/>
              <ellipse cx="20" cy="20" rx="18" ry="7" stroke="url(#logoGradient)" stroke-width="1.5" fill="none" opacity="0.6"/>
              <circle cx="20" cy="20" r="6" fill="url(#coreGradient)"/>
              <circle cx="12" cy="14" r="2" fill="#22d3ee"/>
              <circle cx="28" cy="26" r="1.5" fill="#a855f7"/>
              <defs>
                <linearGradient id="logoGradient" x1="0" y1="0" x2="40" y2="40">
                  <stop offset="0%" stop-color="#22d3ee"/>
                  <stop offset="100%" stop-color="#a855f7"/>
                </linearGradient>
                <radialGradient id="coreGradient" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stop-color="#67e8f9"/>
                  <stop offset="100%" stop-color="#0891b2"/>
                </radialGradient>
              </defs>
            </svg>
          </div>
          <div>
            <p class="eyebrow">SpaceNose · Interstellar Sniffer</p>
            <h1>星际嗅探者</h1>
          </div>
        </div>
        <p class="subtitle">基于智能嗅觉的多星体气体探测任务 · 地面验证实验台</p>
      </div>
      <div class="top-actions">
        <el-button
          :class="['nav-btn', { active: activePath === '/' }]"
          @click="router.push('/')"
        >
          <span class="btn-icon">🔬</span>
          实验台
        </el-button>
        <el-button
          :class="['nav-btn', { active: activePath === '/visualization' }]"
          @click="router.push('/visualization')"
        >
          <span class="btn-icon">📡</span>
          实时监控
        </el-button>
      </div>
    </header>

    <nav class="nav-bar">
      <div class="nav-inner">
        <div
          :class="['nav-item', { active: activePath === '/' }]"
          @click="router.push('/')"
        >
          <span class="nav-dot"></span>
          地面验证实验台
        </div>
        <div
          :class="['nav-item', { active: activePath === '/visualization' }]"
          @click="router.push('/visualization')"
        >
          <span class="nav-dot"></span>
          实时数据监控
        </div>
      </div>
      <div class="nav-status">
        <span class="status-dot pulse"></span>
        <span>系统运行中</span>
      </div>
    </nav>

    <main class="content">
      <router-view />
    </main>

    <footer class="app-footer">
      <div class="footer-inner">
        <span>© 2025 星际嗅探者项目组</span>
        <span class="footer-sep">|</span>
        <span>北京邮电大学 · 大学生创新创业训练计划</span>
      </div>
    </footer>
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
  position: relative;
  background: linear-gradient(135deg, #0a0a1a 0%, #0f172a 25%, #1e1b4b 50%, #0f172a 75%, #0a0a1a 100%);
  color: #e2e8f0;
  overflow-x: hidden;
}

/* 星空背景 */
.starfield {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
}

.stars {
  position: absolute;
  width: 100%;
  height: 100%;
  background-repeat: repeat;
}

.stars-1 {
  background-image:
    radial-gradient(1px 1px at 20px 30px, #fff, transparent),
    radial-gradient(1px 1px at 40px 70px, rgba(255,255,255,0.8), transparent),
    radial-gradient(1px 1px at 50px 160px, rgba(255,255,255,0.6), transparent),
    radial-gradient(1.5px 1.5px at 90px 40px, #22d3ee, transparent),
    radial-gradient(1px 1px at 130px 80px, #fff, transparent),
    radial-gradient(1.5px 1.5px at 160px 120px, #a855f7, transparent);
  background-size: 200px 200px;
  animation: twinkle 4s ease-in-out infinite;
}

.stars-2 {
  background-image:
    radial-gradient(1px 1px at 75px 45px, #fff, transparent),
    radial-gradient(1px 1px at 100px 130px, rgba(255,255,255,0.7), transparent),
    radial-gradient(1.5px 1.5px at 150px 70px, #67e8f9, transparent),
    radial-gradient(1px 1px at 180px 180px, #fff, transparent);
  background-size: 250px 250px;
  animation: twinkle 5s ease-in-out infinite 1s;
}

.stars-3 {
  background-image:
    radial-gradient(1.5px 1.5px at 30px 100px, #c084fc, transparent),
    radial-gradient(1px 1px at 80px 50px, rgba(255,255,255,0.5), transparent),
    radial-gradient(1px 1px at 120px 170px, #fff, transparent),
    radial-gradient(2px 2px at 170px 20px, #22d3ee, transparent);
  background-size: 300px 300px;
  animation: twinkle 6s ease-in-out infinite 2s;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

/* 顶部栏 */
.topbar {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 28px 40px 16px;
  gap: 24px;
}

.brand {
  max-width: 880px;
}

.logo-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo-icon {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  filter: drop-shadow(0 0 12px rgba(34, 211, 238, 0.4));
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.eyebrow {
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: #22d3ee;
  font-size: 11px;
  margin: 0 0 4px;
  text-shadow: 0 0 20px rgba(34, 211, 238, 0.5);
}

.brand h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 800;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #22d3ee 0%, #a855f7 50%, #f472b6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: none;
  filter: drop-shadow(0 0 30px rgba(168, 85, 247, 0.3));
}

.subtitle {
  margin: 12px 0 0;
  color: #94a3b8;
  line-height: 1.6;
  max-width: 760px;
  font-size: 14px;
}

.top-actions {
  display: flex;
  gap: 12px;
  padding-top: 6px;
}

.nav-btn {
  background: rgba(30, 41, 59, 0.8) !important;
  border: 1px solid rgba(71, 85, 105, 0.5) !important;
  color: #94a3b8 !important;
  padding: 10px 20px !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
  transition: all 0.3s ease !important;
  backdrop-filter: blur(10px);
  display: flex !important;
  align-items: center;
  gap: 8px;
}

.nav-btn:hover {
  background: rgba(51, 65, 85, 0.9) !important;
  border-color: rgba(34, 211, 238, 0.5) !important;
  color: #e2e8f0 !important;
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.2);
}

.nav-btn.active {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.2), rgba(168, 85, 247, 0.2)) !important;
  border-color: rgba(34, 211, 238, 0.6) !important;
  color: #22d3ee !important;
  box-shadow: 0 0 25px rgba(34, 211, 238, 0.3), inset 0 0 20px rgba(34, 211, 238, 0.1);
}

.btn-icon {
  font-size: 16px;
}

/* 导航栏 */
.nav-bar {
  position: relative;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(71, 85, 105, 0.3);
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(10px);
}

.nav-inner {
  display: flex;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.nav-item:hover {
  color: #94a3b8;
}

.nav-item.active {
  color: #22d3ee;
  border-bottom-color: #22d3ee;
  text-shadow: 0 0 20px rgba(34, 211, 238, 0.5);
}

.nav-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.5;
  transition: all 0.3s ease;
}

.nav-item.active .nav-dot {
  opacity: 1;
  box-shadow: 0 0 10px currentColor;
}

.nav-status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #22c55e;
  font-size: 12px;
  padding: 6px 14px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 20px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
}

.status-dot.pulse {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
  }
  50% {
    opacity: 0.7;
    box-shadow: 0 0 0 6px rgba(34, 197, 94, 0);
  }
}

/* 内容区 */
.content {
  position: relative;
  z-index: 10;
  padding: 20px 28px 40px;
}

/* 页脚 */
.app-footer {
  position: relative;
  z-index: 10;
  padding: 20px 40px;
  border-top: 1px solid rgba(71, 85, 105, 0.3);
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(10px);
}

.footer-inner {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
}

.footer-sep {
  color: #475569;
}

@media (max-width: 960px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
    padding: 20px 20px 12px;
  }

  .nav-bar {
    padding: 0 20px;
    flex-wrap: wrap;
    gap: 10px;
  }

  .content {
    padding: 16px 16px 30px;
  }

  .brand h1 {
    font-size: 24px;
  }

  .top-actions {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
