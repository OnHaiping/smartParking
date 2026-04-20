<template>
  <div class="home-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h1>车位监控</h1>
        <p class="header-sub">实时同步停车场传感器数据</p>
      </div>
      <div class="time-badge">{{ currentTime }}</div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon icon-total">📊</div>
        <div class="stat-body">
          <div class="stat-num">{{ status.totalSpots }}</div>
          <div class="stat-label">总车位数</div>
        </div>
        <div class="stat-bar"></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon icon-free">✅</div>
        <div class="stat-body">
          <div class="stat-num available">{{ status.availableSpots }}</div>
          <div class="stat-label">空闲车位</div>
        </div>
        <div class="stat-bar bar-green" :style="{ width: freePercent + '%' }"></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon icon-used">🚗</div>
        <div class="stat-body">
          <div class="stat-num occupied">{{ status.occupiedSpots }}</div>
          <div class="stat-label">已停车位</div>
        </div>
        <div class="stat-bar bar-red" :style="{ width: usedPercent + '%' }"></div>
      </div>
    </div>

    <!-- 占用率条 -->
    <div class="occupancy-card">
      <div class="occ-head">
        <span>当前占用率</span>
        <span class="occ-pct" :class="usedPercent > 80 ? 'high' : usedPercent > 50 ? 'mid' : 'low'">
          {{ usedPercent.toFixed(0) }}%
        </span>
      </div>
      <div class="occ-track">
        <div class="occ-fill" :style="{ width: usedPercent + '%' }" :class="usedPercent > 80 ? 'high' : usedPercent > 50 ? 'mid' : 'low'"></div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="section-title">快捷操作</div>
    <div class="actions-grid">
      <button class="action-card accent" @click="$router.push('/parking')">
        <div class="ac-icon">🏢</div>
        <div class="ac-body">
          <strong>3D 数字孪生监控</strong>
          <span>实时场景，全方位观察</span> 
        </div>
        <div class="ac-arrow">→</div>
      </button>

      <button class="action-card" @click="$router.push('/billing')">
        <div class="ac-icon">💰</div>
        <div class="ac-body">
          <strong>智能计费系统</strong>
          <span>无感支付，账单查询</span>
        </div>
        <div class="ac-arrow">→</div>
      </button>

      <button class="action-card" @click="$router.push('/profile')">
        <div class="ac-icon">🧑</div>
        <div class="ac-body">
          <strong>个人中心</strong>
          <span>车辆绑定，账号信息</span>
        </div>
        <div class="ac-arrow">→</div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../utils/api'

const status = ref({ totalSpots: 2, availableSpots: 2, occupiedSpots: 0 })
const currentTime = ref('')
let timer = null

const freePercent = computed(() =>
  status.value.totalSpots > 0 ? (status.value.availableSpots / status.value.totalSpots) * 100 : 0
)
const usedPercent = computed(() =>
  status.value.totalSpots > 0 ? (status.value.occupiedSpots / status.value.totalSpots) * 100 : 0
)

const fetchStatus = async () => {
  try {
    const res = await api.get('/parking/status')
    if (res.data.code === 200) status.value = res.data.data
  } catch (err) {
    console.error('获取状态失败', err)
  }
}

const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

onMounted(() => {
  fetchStatus()
  updateTime()
  timer = setInterval(() => { updateTime(); fetchStatus() }, 5000)
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.home-page {
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border);
}

.page-header h1 {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--navy-dark);
  margin-bottom: 0.25rem;
}

.header-sub { color: var(--muted); font-size: 0.9rem; }

.time-badge {
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 0.5rem 1rem;
  border-radius: 50px;
  color: var(--muted);
  font-size: 0.85rem;
  white-space: nowrap;
}

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-bottom: 1.25rem;
}

.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.25rem;
  position: relative;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

.stat-icon {
  font-size: 2rem;
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-total { background: #ebf4ff; }
.icon-free  { background: #f0fff4; }
.icon-used  { background: #fff5f5; }

.stat-body { flex: 1; }

.stat-num {
  font-size: 2.5rem;
  font-weight: 900;
  line-height: 1;
  color: var(--navy-dark);
  margin-bottom: 0.2rem;
}

.stat-num.available { color: var(--success); }
.stat-num.occupied  { color: var(--danger); }
.stat-label { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }

.stat-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: var(--border);
  width: 100%;
}

.bar-green { background: var(--success); }
.bar-red   { background: var(--danger); }

/* 占用率卡片 */
.occupancy-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.occ-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: var(--muted);
  font-weight: 600;
}

.occ-pct { font-size: 1.2rem; font-weight: 800; }
.occ-pct.low  { color: var(--success); }
.occ-pct.mid  { color: #f6ad55; }
.occ-pct.high { color: var(--danger); }

.occ-track {
  height: 8px;
  background: #edf2f7;
  border-radius: 50px;
  overflow: hidden;
}

.occ-fill {
  height: 100%;
  border-radius: 50px;
  transition: width 0.5s ease;
}

.occ-fill.low  { background: var(--success); }
.occ-fill.mid  { background: #f6ad55; }
.occ-fill.high { background: var(--danger); }

/* 快捷操作 */
.section-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--muted);
  margin-bottom: 1rem;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
}

.action-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 1rem;
  text-align: left;
  transition: all 0.2s;
}

.action-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
  border-color: var(--brand);
}

.action-card.accent {
  background: var(--navy-dark);
  border-color: transparent;
  color: #fff;
}

.action-card.accent:hover {
  box-shadow: 0 8px 25px rgba(26,32,44,0.4);
  border-color: var(--brand);
}

.ac-icon { font-size: 1.8rem; flex-shrink: 0; }

.ac-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.ac-body strong { font-size: 1rem; display: block; }
.ac-body span { font-size: 0.82rem; opacity: 0.6; }

.ac-arrow {
  color: var(--brand);
  font-size: 1.2rem;
  opacity: 0.5;
  transition: opacity 0.2s, transform 0.2s;
}

.action-card:hover .ac-arrow { opacity: 1; transform: translateX(3px); }

/* 响应式 */
@media (max-width: 900px) {
  .stats-row, .actions-grid { grid-template-columns: 1fr; }
}

@media (max-width: 600px) {
  .page-header { flex-direction: column; gap: 1rem; }
  .page-header h1 { font-size: 1.5rem; }
}
</style>

