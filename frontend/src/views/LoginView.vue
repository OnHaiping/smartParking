<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-logo">
        <div class="logo-mark">🅿</div>
        <span>智能停车管理平台</span>
      </div>
      <h2 class="auth-title">欢迎回来</h2>
      <p class="auth-subtitle">登录以进入数字孪生监控平台</p>

      <form @submit.prevent="handleLogin" class="auth-form">
        <div class="field">
          <label>用户名</label>
          <input type="text" v-model="form.username" required placeholder="请输入用户名" autocomplete="username" />
        </div>
        <div class="field">
          <label>密码</label>
          <input type="password" v-model="form.password" required placeholder="请输入密码" autocomplete="current-password" />
        </div>
        <div v-if="errorMsg" class="alert alert-error">{{ errorMsg }}</div>
        <button type="submit" class="btn-submit" :disabled="loading">
          <span v-if="loading" class="btn-spinner"></span>
          {{ loading ? '登录中...' : '立即登录' }}
        </button>
      </form>

      <p class="auth-footer">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </p>
    </div>

    <!-- 右侧装饰 -->
    <div class="auth-deco">
      <div class="deco-title">数字孪生智能停车</div>
      <div class="deco-sub">基于 PaddleOCR 的实时识别与 3D 可视化</div>
      <div class="deco-stats">
        <div class="deco-stat"><div class="ds-num">2</div><div class="ds-label">智能车位</div></div>
        <div class="deco-stat"><div class="ds-num">3D</div><div class="ds-label">孪生场景</div></div>
        <div class="deco-stat"><div class="ds-num">AI</div><div class="ds-label">车牌识别</div></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import api from '../utils/api'

const router = useRouter()
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')

const handleLogin = async () => {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await api.post('/web/login', form)
    if (res.data.code === 200) {
      localStorage.setItem('token', res.data.data.token)
      localStorage.setItem('userId', res.data.data.userId)
      localStorage.setItem('userInfo', JSON.stringify(res.data.data))
      router.push('/home')
    } else {
      errorMsg.value = res.data.message || '用户名或密码错误'
    }
  } catch {
    errorMsg.value = '请求异常，请检查网络连接'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  width: 100%;
  display: flex;
  background: var(--bg);
}

/* 左侧表单 */
.auth-card {
  width: 480px;
  min-height: 100vh;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 3rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex-shrink: 0;
}

.auth-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 3rem;
}

.logo-mark {
  width: 36px;
  height: 36px;
  background: var(--brand);
  color: #fff;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-weight: 800;
}

.auth-logo span { font-size: 0.95rem; font-weight: 700; color: var(--text); }

.auth-title { font-size: 2rem; font-weight: 800; color: var(--navy-dark); margin-bottom: 0.4rem; }
.auth-subtitle { color: var(--muted); font-size: 0.9rem; margin-bottom: 2.5rem; }

.auth-form { display: flex; flex-direction: column; gap: 1.25rem; }

.field { display: flex; flex-direction: column; gap: 0.4rem; }

.field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
}

.field input {
  background: var(--bg);
  border: 1.5px solid var(--border);
  border-radius: 10px;
  padding: 0.85rem 1.1rem;
  color: var(--text);
  font-size: 0.95rem;
  outline: none;
  transition: all 0.2s;
}

.field input:focus {
  border-color: var(--brand);
  background: var(--surface);
  box-shadow: 0 0 0 3px rgba(43,125,233,0.12);
}

.alert {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 500;
}

.alert-error {
  background: var(--danger-light);
  border: 1px solid #fecaca;
  color: var(--danger);
}

.btn-submit {
  background: var(--brand);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 0.95rem;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-submit:hover:not(:disabled) {
  background: var(--brand-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(43,125,233,0.25);
}

.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.auth-footer { margin-top: 2rem; color: var(--muted); font-size: 0.9rem; }
.auth-footer a { font-weight: 600; }

/* 右侧装饰区 */
.auth-deco {
  flex: 1;
  background: linear-gradient(135deg, var(--brand) 0%, #1a63c5 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #fff;
}

.deco-title { font-size: 2rem; font-weight: 800; margin-bottom: 1rem; text-align: center; }
.deco-sub { font-size: 1rem; opacity: 0.8; text-align: center; margin-bottom: 3rem; line-height: 1.6; }

.deco-stats { display: flex; gap: 3rem; }
.deco-stat { text-align: center; }
.ds-num { font-size: 2.5rem; font-weight: 900; }
.ds-label { font-size: 0.85rem; opacity: 0.7; margin-top: 0.25rem; }

/* 响应式：移动端隐藏装饰区 */
@media (max-width: 768px) {
  .auth-deco { display: none; }
  .auth-card { width: 100%; border-right: none; padding: 2rem 1.5rem; }
}
</style>
