<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-logo">
        <div class="logo-mark">🅿</div>
        <span>智能停车管理平台</span>
      </div>
      <h2 class="auth-title">创建账号</h2>
      <p class="auth-subtitle">加入数字孪生智能停车平台</p>

      <form @submit.prevent="handleRegister" class="auth-form">
        <div class="field">
          <label>用户名</label>
          <input type="text" v-model="form.username" required placeholder="设置唯一用户名" minlength="3" maxlength="20" />
        </div>
        <div class="field">
          <label>昵称 <span class="opt">可选</span></label>
          <input type="text" v-model="form.nickname" placeholder="您的显示昵称" maxlength="20" />
        </div>
        <div class="field">
          <label>密码</label>
          <input type="password" v-model="form.password" required placeholder="至少 6 位密码" minlength="6" />
        </div>
        <div class="field">
          <label>确认密码</label>
          <input type="password" v-model="form.confirmPassword" required placeholder="再次输入密码" />
        </div>

        <div v-if="errorMsg" class="alert alert-error">{{ errorMsg }}</div>
        <div v-if="successMsg" class="alert alert-success">{{ successMsg }}</div>

        <button type="submit" class="btn-submit" :disabled="loading">
          <span v-if="loading" class="btn-spinner"></span>
          {{ loading ? '注册中...' : '立即注册' }}
        </button>
      </form>

      <p class="auth-footer">
        已有账号？<router-link to="/login">立即登录</router-link>
      </p>
    </div>

    <div class="auth-deco">
      <div class="deco-title">数字孪生智能停车</div>
      <div class="deco-sub">基于 PaddleOCR 的实时识别与 3D 可视化</div>
      <div class="deco-steps">
        <div class="step"><span class="step-num">01</span><span>注册账号，绑定车牌</span></div>
        <div class="step"><span class="step-num">02</span><span>AI 自动识别车辆入场</span></div>
        <div class="step"><span class="step-num">03</span><span>3D 孪生实时可视化</span></div>
        <div class="step"><span class="step-num">04</span><span>支付离场，无感体验</span></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import api from '../utils/api'

const router = useRouter()
const form = reactive({ username: '', nickname: '', password: '', confirmPassword: '' })
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const handleRegister = async () => {
  errorMsg.value = ''
  successMsg.value = ''

  if (form.password !== form.confirmPassword) {
    errorMsg.value = '两次输入的密码不一致！'
    return
  }

  loading.value = true
  try {
    const res = await api.post('/web/register', {
      username: form.username,
      password: form.password,
      nickname: form.nickname
    })
    if (res.data.code === 200) {
      successMsg.value = '注册成功！正在跳转到登录页...'
      setTimeout(() => router.push('/login'), 1500)
    } else {
      errorMsg.value = res.data.message || '注册失败'
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
  overflow-y: auto;
}

.auth-logo { display: flex; align-items: center; gap: 10px; margin-bottom: 2.5rem; }

.logo-mark {
  width: 36px; height: 36px;
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
.auth-title { font-size: 1.8rem; font-weight: 800; color: var(--navy-dark); margin-bottom: 0.4rem; }
.auth-subtitle { color: var(--muted); font-size: 0.9rem; margin-bottom: 2rem; }

.auth-form { display: flex; flex-direction: column; gap: 1.1rem; }

.field { display: flex; flex-direction: column; gap: 0.4rem; }

.field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 6px;
}

.opt { color: var(--muted); font-weight: 400; font-size: 0.78rem; }

.field input {
  background: var(--bg);
  border: 1.5px solid var(--border);
  border-radius: 10px;
  padding: 0.8rem 1.1rem;
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

.alert { padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.88rem; font-weight: 500; }
.alert-error { background: var(--danger-light); border: 1px solid #fecaca; color: var(--danger); }
.alert-success { background: var(--success-light); border: 1px solid #86efac; color: var(--success); }

.btn-submit {
  background: var(--brand);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 0.95rem;
  font-size: 0.95rem;
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

.auth-footer { margin-top: 1.5rem; color: var(--muted); font-size: 0.9rem; }
.auth-footer a { font-weight: 600; }

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

.deco-title { font-size: 2rem; font-weight: 800; margin-bottom: 0.75rem; text-align: center; }
.deco-sub { font-size: 0.95rem; opacity: 0.8; text-align: center; margin-bottom: 3rem; line-height: 1.6; }

.deco-steps { display: flex; flex-direction: column; gap: 1.2rem; width: 100%; max-width: 300px; }

.step {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(255,255,255,0.12);
  padding: 1rem 1.25rem;
  border-radius: 12px;
}

.step-num {
  font-weight: 900;
  font-size: 1.2rem;
  color: rgba(255,255,255,0.5);
  width: 30px;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .auth-deco { display: none; }
  .auth-card { width: 100%; border-right: none; padding: 2rem 1.5rem; }
}
</style>
