<template>
  <div class="app-shell">
    <!-- 星空背景层 -->
    <div class="starfield">
      <div class="planet"></div>
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
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
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
  background: radial-gradient(circle at 50% 0%, #0f172a 0%, #020617 80%, #000 100%);
  color: var(--color-text-main);
  overflow-x: hidden;
}

/* 星空背景 - Optimization: Use cleaner gradients */
.starfield {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
}

.planet {
  position: absolute;
  top: -100px;
  right: -100px;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle at 30% 30%, rgba(34, 211, 238, 0.15) 0%, rgba(34, 211, 238, 0.05) 40%, transparent 70%);
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.6;
  animation: planet-pulse 10s ease-in-out infinite;
}

@keyframes planet-pulse {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
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
    radial-gradient(1.5px 1.5px at 90px 40px, var(--color-primary), transparent),
    radial-gradient(1px 1px at 130px 80px, #fff, transparent),
    radial-gradient(1.5px 1.5px at 160px 120px, var(--color-secondary), transparent);
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
    radial-gradient(2px 2px at 170px 20px, var(--color-primary), transparent);
  background-size: 300px 300px;
  animation: twinkle 6s ease-in-out infinite 2s;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.5; }
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
  filter: drop-shadow(0 0 12px var(--color-primary-glow));
  animation: float 6s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.eyebrow {
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--color-primary);
  font-size: 11px;
  font-family: var(--font-mono);
  margin: 0 0 4px;
  text-shadow: 0 0 20px var(--color-primary-glow);
}

.brand h1 {
  margin: 0;
  font-size: 36px;
  font-weight: 800;
  letter-spacing: 1px;
  background: linear-gradient(135deg, #fff 0%, #e2e8f0 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 0 30px rgba(255, 255, 255, 0.1);
}

.subtitle {
  margin: 12px 0 0;
  color: var(--color-text-muted);
  line-height: 1.6;
  max-width: 760px;
  font-size: 14px;
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
  border-bottom: 1px solid var(--color-border);
  background: rgba(15, 23, 42, 0.3);
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
  padding: 16px 24px;
  color: var(--color-text-dim);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.nav-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
}

.nav-item.active {
  color: var(--color-primary);
}

.nav-item.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--color-primary);
  box-shadow: 0 0 10px var(--color-primary);
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
  color: var(--el-color-success);
  font-size: 12px;
  font-family: var(--font-mono);
  padding: 6px 14px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 4px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-success);
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

/* 内容区 Transition */
.content {
  position: relative;
  z-index: 10;
  padding: 24px 40px 48px;
}

/* 页脚 */
.app-footer {
  position: relative;
  z-index: 10;
  padding: 24px 40px;
  border-top: 1px solid var(--color-border);
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(10px);
}

.footer-inner {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  color: var(--color-text-dim);
  font-size: 12px;
}

.footer-sep {
  color: var(--color-border);
}

@media (max-width: 960px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
    padding: 20px 20px 12px;
  }

  .nav-bar {
    padding: 0 20px;
    overflow-x: auto;
  }

  .content {
    padding: 16px 16px 30px;
  }

  .brand h1 {
    font-size: 28px;
  }
}
</style>
