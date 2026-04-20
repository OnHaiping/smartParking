<template>
  <div id="app-root">
    <header v-if="isLoggedIn && !isAuthPage" class="global-nav">
      <div class="nav-inner">
        <div class="nav-brand">
          <span class="brand-dot"></span>
          <span class="brand-text">智能停车系统</span>
        </div>
        <nav class="nav-links">
          <router-link to="/home">监控大盘</router-link>
          <router-link to="/parking">3D 可视化</router-link>
          <router-link to="/billing">计费支付</router-link>
          <router-link to="/profile">个人中心</router-link>
        </nav>
        <button @click="logout" class="logout-btn">退出</button>
      </div>
    </header>

    <main class="main-content" :class="{ 'is-parking': isParkingPage, 'is-auth': isAuthPage }">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const isLoggedIn = ref(!!localStorage.getItem('token'))
const isAuthPage = computed(() => ['/login', '/register'].includes(route.path))
const isParkingPage = computed(() => route.path === '/parking')

watchEffect(() => {
  isLoggedIn.value = !!localStorage.getItem('token')
  route.path
})

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('userId')
  localStorage.removeItem('userInfo')
  router.push('/login')
}
</script>

<style>
/* ===== 导航栏 - 浅色主题 ===== */
.global-nav {
  position: sticky;
  top: 0;
  z-index: 200;
  width: 100%;
  height: var(--nav-h);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 1px 8px rgba(0,0,0,0.06);
  flex-shrink: 0;
}

.nav-inner {
  max-width: 1400px;
  margin: 0 auto;
  height: 100%;
  padding: 0 2rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text);
  white-space: nowrap;
}

.brand-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--brand);
}

.nav-links {
  display: flex;
  gap: 0.2rem;
  flex: 1;
}

.nav-links a {
  color: var(--muted);
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
  text-decoration: none;
}

.nav-links a:hover { color: var(--text); background: var(--bg); }
.nav-links a.router-link-active { color: var(--brand); background: var(--brand-light); font-weight: 600; }

.logout-btn {
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
  padding: 0.4rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  transition: all 0.2s;
  white-space: nowrap;
}

.logout-btn:hover { border-color: var(--danger); color: var(--danger); background: var(--danger-light); }

/* ===== 主内容区 ===== */
.main-content {
  flex: 1;
  width: 100%;
  padding: 2rem;
  overflow-x: hidden;
  overflow-y: auto;
  box-sizing: border-box;
}

.main-content.is-auth { padding: 0; display: flex; }
.main-content.is-parking { padding: 0; overflow: hidden; position: relative; }

@media (max-width: 768px) {
  .nav-inner { padding: 0 0.6rem; gap: 0.4rem; }
  .nav-links a { padding: 0.35rem 0.5rem; font-size: 0.78rem; }
  .main-content { padding: 1rem; }
}

@media (max-width: 520px) {
  /* 超小屏：隐藏品牌文字，只保留圆点 */
  .brand-text { display: none; }
  .brand-dot { width: 8px; height: 8px; flex-shrink: 0; }
  /* 让品牌区宽度收缩，把空间留给导航链接 */
  .nav-brand { min-width: 0; gap: 0; }
  .nav-inner { gap: 0.3rem; flex-wrap: nowrap; }
  .nav-links { gap: 0; flex-wrap: nowrap; overflow-x: auto; }
  .nav-links a { padding: 0.3rem 0.4rem; font-size: 0.75rem; white-space: nowrap; }
  .logout-btn { padding: 0.3rem 0.5rem; font-size: 0.75rem; flex-shrink: 0; }
}
</style>
