<template>
  <div class="profile-page">
    <!-- 用户卡片 -->
    <div class="user-card panel">
      <div class="avatar-container" @click="triggerAvatarUpload">
        <img v-if="userInfo.avatar_url" :src="fullAvatarUrl" class="avatar-img" />
        <div v-else class="avatar">{{ avatarChar }}</div>
        <div class="avatar-overlay">
          <span>📷 修改</span>
        </div>
      </div>
      <input type="file" ref="avatarInput" accept="image/*" style="display: none" @change="handleAvatarUpload" />
      
      <div class="user-info">
        <h2>{{ userInfo.nickname || userInfo.username }}</h2>
        <p class="username">@{{ userInfo.username }}</p>
      </div>
      
      <div class="profile-actions">
        <button class="btn btn-outline" @click="showEditNickname = true">修改昵称</button>
        <button class="btn btn-outline" @click="showEditPassword = true">修改密码</button>
        <button class="btn btn-danger-outline" @click="confirmDeleteAccount">注销账号</button>
      </div>
    </div>

    <!-- 车辆管理 -->
    <div class="panel vehicle-panel">
      <div class="panel-head">
        <div>
          <h3>我的车辆</h3>
          <p>管理您名下绑定的车牌号</p>
        </div>
        <span class="count-badge">{{ vehicles.length }} 辆</span>
      </div>

      <!-- 添加车辆 -->
      <div class="add-row">
        <input
          type="text"
          v-model="newPlate"
          placeholder="输入车牌号（如：粤B12345）"
          @keyup.enter="bindVehicle"
          class="plate-input"
        />
        <button @click="bindVehicle" class="btn btn-add" :disabled="binding">
          {{ binding ? '绑定中...' : '+ 添加' }}
        </button>
      </div>

      <!-- 车辆列表 -->
      <div v-if="vehicles.length === 0" class="empty-state">
        <span>🚗</span>
        <p>暂未绑定任何车辆，请在上方添加</p>
      </div>

      <div v-else class="vehicle-list">
        <div v-for="(v, i) in vehicles" :key="i" class="vehicle-item">
          <div class="plate-box">{{ v.plateNumber }}</div>
          <div class="meta">
            <span v-if="v.isDefault" class="default-tag">默认</span>
            <span class="bind-time">{{ v.createdAt }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 修改昵称弹窗 -->
    <div class="modal-overlay" v-if="showEditNickname" @click="showEditNickname = false">
      <div class="modal-content" @click.stop>
        <h3>修改昵称</h3>
        <input type="text" v-model="tempNickname" placeholder="输入新昵称" class="plate-input modal-input" />
        <div class="modal-actions">
          <button class="btn btn-cancel" @click="showEditNickname = false">取消</button>
          <button class="btn btn-primary" @click="updateNickname" :disabled="!tempNickname.trim() || savingProfile">
            {{ savingProfile ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <div class="modal-overlay" v-if="showEditPassword" @click="showEditPassword = false">
      <div class="modal-content" @click.stop>
        <h3>修改登录密码</h3>
        <input type="password" v-model="pwdForm.old" placeholder="当前密码" class="plate-input modal-input" />
        <input type="password" v-model="pwdForm.new" placeholder="新密码" class="plate-input modal-input" style="margin-top: 10px;" />
        <input type="password" v-model="pwdForm.confirm" placeholder="确认新密码" class="plate-input modal-input" style="margin-top: 10px;" />
        <div class="modal-actions">
          <button class="btn btn-cancel" @click="showEditPassword = false">取消</button>
          <button class="btn btn-primary" @click="updatePassword" :disabled="!pwdForm.old || !pwdForm.new || pwdForm.new !== pwdForm.confirm || savingPwd">
            {{ savingPwd ? '提交中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../utils/api'

const router = useRouter()

const userInfo = ref({})
const vehicles = ref([])
const newPlate = ref('')
const binding = ref(false)

// Profile Edit States
const avatarInput = ref(null)
const showEditNickname = ref(false)
const tempNickname = ref('')
const savingProfile = ref(false)

const showEditPassword = ref(false)
const pwdForm = ref({ old: '', new: '', confirm: '' })
const savingPwd = ref(false)

const avatarChar = computed(() => {
  const n = userInfo.value.nickname || userInfo.value.username || 'U'
  return n.charAt(0).toUpperCase()
})

const fullAvatarUrl = computed(() => {
  if (!userInfo.value.avatar_url) return ''
  // 后端运行在 192.168.137.1:8080
  const baseUrl = 'http://192.168.137.1:8080'
  return userInfo.value.avatar_url.startsWith('http') ? userInfo.value.avatar_url : baseUrl + userInfo.value.avatar_url
})

onMounted(() => {
  const stored = localStorage.getItem('userInfo')
  if (stored) {
    userInfo.value = JSON.parse(stored)
    loadVehicles()
  }
})

const loadVehicles = async () => {
  const userId = localStorage.getItem('userId')
  if (!userId) return
  try {
    const res = await api.get(`/user/vehicle/list?user_id=${userId}`)
    if (res.data.code === 200) vehicles.value = res.data.data
  } catch (err) {
    console.error('获取车辆列表失败', err)
  }
}

const bindVehicle = async () => {
  const plate = newPlate.value.trim().toUpperCase()
  if (!plate) return alert('请输入车牌号')

  const userId = localStorage.getItem('userId')
  binding.value = true
  try {
    const res = await api.post('/user/vehicle/bind', {
      user_id: parseInt(userId, 10),
      plate_number: plate,
      is_default: vehicles.value.length === 0
    })
    if (res.data.code === 200) {
      newPlate.value = ''
      await loadVehicles()
    } else {
      alert(res.data.message || '绑定失败')
    }
  } catch {
    alert('绑定请求错误，请检查网络')
  } finally {
    binding.value = false
  }
}

// ---- 用户资料管理逻辑 ----

const triggerAvatarUpload = () => {
  avatarInput.value?.click()
}

const handleAvatarUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    const res = await api.post('/upload/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    if (res.data.code === 200) {
      const newUrl = res.data.data.url
      // 更新后端 User 记录
      const userId = localStorage.getItem('userId')
      await api.post('/user/profile/update', {
        user_id: parseInt(userId, 10),
        avatar_url: newUrl
      })
      
      // 更新本地状态
      userInfo.value.avatar_url = newUrl
      localStorage.setItem('userInfo', JSON.stringify(userInfo.value))
      alert('头像上传成功')
    } else {
      alert(res.data.message || '上传失败')
    }
  } catch (err) {
    console.error(err)
    alert('上传请求错误')
  } finally {
    event.target.value = '' // reset input
  }
}

const updateNickname = async () => {
  const val = tempNickname.value.trim()
  if (!val) return
  
  savingProfile.value = true
  try {
    const userId = localStorage.getItem('userId')
    const res = await api.post('/user/profile/update', {
      user_id: parseInt(userId, 10),
      nickname: val
    })
    
    if (res.data.code === 200) {
      userInfo.value.nickname = val
      localStorage.setItem('userInfo', JSON.stringify(userInfo.value))
      showEditNickname.value = false
      alert('昵称修改成功')
    } else {
      alert(res.data.message || '修改失败')
    }
  } catch {
    alert('请求错误')
  } finally {
    savingProfile.value = false
    tempNickname.value = ''
  }
}

const updatePassword = async () => {
  if (pwdForm.value.new !== pwdForm.value.confirm) {
    return alert('两次输入的新密码不一致')
  }
  
  savingPwd.value = true
  try {
    const userId = localStorage.getItem('userId')
    const res = await api.post('/user/password/update', {
      user_id: parseInt(userId, 10),
      old_password: pwdForm.value.old,
      new_password: pwdForm.value.new
    })
    
    if (res.data.code === 200) {
      alert('密码修改成功，请重新登录')
      localStorage.removeItem('token')
      localStorage.removeItem('userId')
      localStorage.removeItem('userInfo')
      router.push('/login')
    } else {
      alert(res.data.message || '修改失败')
    }
  } catch {
    alert('请求错误')
  } finally {
    savingPwd.value = false
    pwdForm.value = { old: '', new: '', confirm: '' }
  }
}

const confirmDeleteAccount = async () => {
  const num = vehicles.value.length
  const msg = num > 0 
    ? `您当前绑定了 ${num} 辆车。注销账号将永久删除您的个人信息与车辆绑定记录（停车记录保留归属系统）。\n\n您确定要注销吗？输入您的登录用户名确认：`
    : '注销账号将永久删除您的个人信息。\n\n您确定要注销吗？输入您的登录用户名确认：'
  
  const confirmUser = prompt(msg)
  if (confirmUser !== userInfo.value.username) {
    if (confirmUser !== null) alert('用户名输入不匹配，取消注销操作。')
    return
  }
  
  try {
    const userId = localStorage.getItem('userId')
    const res = await api.post('/user/delete', {
      user_id: parseInt(userId, 10)
    })
    
    if (res.data.code === 200) {
      alert('账号已注销')
      localStorage.removeItem('token')
      localStorage.removeItem('userId')
      localStorage.removeItem('userInfo')
      router.push('/login')
    } else {
      alert(res.data.message || '注销失败')
    }
  } catch {
    alert('请求失败')
  }
}
</script>

<style scoped>
.profile-page {
  max-width: 760px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
}

/* 用户卡片 */
.user-card {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap; /* 适配窄屏幕 */
}

/* 头像容器及遮罩 */
.avatar-container {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  flex-shrink: 0;
}

.avatar, .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  font-size: 2rem;
  font-weight: 800;
}

.avatar-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-container:hover .avatar-overlay {
  opacity: 1;
}

.user-info {
  flex: 1;
  min-width: 150px;
}

.user-info h2 {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--navy-dark);
  margin-bottom: 0.25rem;
}

.username { color: var(--muted); font-size: 1rem; }

/* 个人操作按钮区 */
.profile-actions {
  display: flex;
  gap: 0.75rem;
  margin-left: auto; /* 靠右对齐 */
  flex-wrap: wrap;
}

.btn-outline, .btn-danger-outline, .btn-cancel, .btn-primary {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline {
  background: transparent;
  color: var(--brand);
  border: 1.5px solid var(--brand);
}

.btn-outline:hover {
  background: rgba(66,185,131,0.1);
}

.btn-danger-outline {
  background: transparent;
  color: #e53e3e;
  border: 1.5px solid #fc8181;
}

.btn-danger-outline:hover {
  background: #fff5f5;
  border-color: #e53e3e;
}

/* 车辆面板 */
.vehicle-panel {
  display: flex;
  flex-direction: column;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border);
}

.panel-head h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--navy-dark);
  margin-bottom: 0.2rem;
}

.panel-head p { font-size: 0.85rem; color: var(--muted); }

.count-badge {
  background: #edf2f7;
  color: var(--muted);
  padding: 0.3rem 0.8rem;
  border-radius: 50px;
  font-size: 0.85rem;
  font-weight: 700;
  white-space: nowrap;
}

/* 添加行 */
.add-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.plate-input {
  flex: 1;
  padding: 0.85rem 1.2rem;
  border: 1.5px solid var(--border);
  border-radius: 10px;
  font-size: 1rem;
  outline: none;
  transition: all 0.2s;
}

.plate-input:focus {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(66,185,131,0.15);
}

.btn-add {
  background: var(--brand);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 0.85rem 1.5rem;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-add:hover:not(:disabled) {
  background: var(--brand-dark);
  transform: translateY(-1px);
}

.btn-add:disabled { opacity: 0.6; cursor: not-allowed; }

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--muted);
}

.empty-state span { font-size: 3rem; display: block; margin-bottom: 1rem; opacity: 0.3; }

/* 车辆列表 */
.vehicle-list { display: flex; flex-direction: column; gap: 0.75rem; }

.vehicle-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: border-color 0.2s;
}

.vehicle-item:hover { border-color: var(--brand); }

.plate-box {
  background: var(--navy-dark);
  color: #fff;
  padding: 0.4rem 1rem;
  border-radius: 7px;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 2px;
}

.meta { display: flex; align-items: center; gap: 0.75rem; }

.default-tag {
  background: #c6f6d5;
  color: #22543d;
  padding: 0.2rem 0.6rem;
  border-radius: 50px;
  font-size: 0.75rem;
  font-weight: 700;
}

.bind-time { font-size: 0.85rem; color: var(--muted); }

@media (max-width: 600px) {
  .panel { padding: 1.25rem; }
  .user-card { flex-direction: column; text-align: center; }
  .profile-actions { margin-left: 0; justify-content: center; width: 100%; }
  .add-row { flex-direction: column; }
  .vehicle-item { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
}

/* 模态框 (Modal) 样式 */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

.modal-content {
  background: #fff;
  padding: 2rem;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1);
  animation: slideUp 0.3s ease-out;
}

.modal-content h3 {
  margin-bottom: 1.5rem;
  color: var(--navy-dark);
}

.modal-input {
  width: 100%;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
}

.btn-cancel {
  background: #f1f5f9;
  color: var(--muted);
  border: none;
}
.btn-cancel:hover { background: #e2e8f0; }

.btn-primary {
  background: var(--brand);
  color: #fff;
  border: none;
}
.btn-primary:hover:not(:disabled) { background: var(--brand-dark); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
