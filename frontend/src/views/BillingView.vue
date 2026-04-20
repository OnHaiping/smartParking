<template>
  <div class="billing-page">
    <div class="page-header">
      <h1>计费收银台</h1>
      <p class="header-sub">全自动无感计费，实时同步停车账单</p>
    </div>

    <!-- 查询卡片 -->
    <div class="panel">
      <div class="panel-head">
        <span class="panel-icon">🔍</span>
        <div>
          <h2>查询账单</h2>
          <p>系统已自动读取您名下的默认车辆</p>
        </div>
      </div>

      <div class="search-row">
        <input
          type="text"
          v-model="plateNumber"
          placeholder="请输入车牌号（如：粤B12345）"
          @keyup.enter="searchBilling"
          class="plate-input"
        />
        <button @click="searchBilling" class="btn btn-primary" :disabled="querying">
          {{ querying ? '查询中...' : '查询' }}
        </button>
      </div>
    </div>

    <!-- 账单结果 -->
    <Transition name="slide-up">
      <div v-if="hasResult && searched" class="panel result-panel">
        <div class="result-head">
          <div class="plate-badge">{{ billingInfo.plateNumber }}</div>
          <div class="status-tag unpaid">待支付</div>
        </div>

        <div class="bill-rows">
          <div class="bill-row">
            <span>停车位置</span>
            <span>{{ billingInfo.spotId || '—' }}</span>
          </div>
          <div class="bill-row">
            <span>入场时间</span>
            <span>{{ billingInfo.entryTime }}</span>
          </div>
          <div class="bill-row">
            <span>停车时长</span>
            <span class="duration">{{ billingInfo.duration }}</span>
          </div>
          <div class="bill-divider"></div>
          <div class="bill-row total-row">
            <span>应付金额</span>
            <span class="amount">¥ {{ billingInfo.amount }}</span>
          </div>
        </div>

        <button @click="payBill" class="btn btn-pay" :disabled="paying">
          <span v-if="paying" class="btn-spinner"></span>
          {{ paying ? '支付处理中...' : '✓ 确认支付' }}
        </button>
      </div>
    </Transition>

    <!-- 无账单 -->
    <Transition name="slide-up">
      <div v-if="!hasResult && searched" class="panel empty-panel">
        <div class="empty-icon">✓</div>
        <p>未找到待支付账单，您的账户记录良好。</p>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../utils/api'

const plateNumber = ref('')
const hasResult = ref(false)
const searched = ref(false)
const querying = ref(false)
const paying = ref(false)
const billingInfo = ref({})

const loadDefaultVehicle = async () => {
  const userId = localStorage.getItem('userId')
  if (!userId) return
  try {
    const res = await api.get(`/user/vehicle/list?user_id=${userId}`)
    if (res.data.code === 200 && res.data.data.length > 0) {
      const def = res.data.data.find(v => v.isDefault) || res.data.data[0]
      plateNumber.value = def.plateNumber
      searchBilling()
    }
  } catch (err) {
    console.error('获取车辆失败', err)
  }
}

const searchBilling = async () => {
  if (!plateNumber.value.trim()) return
  querying.value = true
  try {
    const res = await api.get(`/billing/query?plate=${plateNumber.value}`)
    searched.value = true
    if (res.data.code === 200) {
      hasResult.value = true
      billingInfo.value = res.data.data
    } else {
      hasResult.value = false
      billingInfo.value = {}
    }
  } catch (err) {
    searched.value = true
    hasResult.value = false
    console.error(err)
  } finally {
    querying.value = false
  }
}

const payBill = async () => {
  if (!confirm(`确认支付 ¥${billingInfo.value.amount} 吗？`)) return
  paying.value = true
  try {
    const res = await api.post('/billing/pay', {
      plate: billingInfo.value.plateNumber,
      amount: billingInfo.value.amount,
      payment_method: 'wechat'
    })
    if (res.data.code === 200) {
      alert('支付成功！')
      hasResult.value = false
      searched.value = false
    } else {
      alert(res.data.message || '支付失败')
    }
  } catch {
    alert('网络异常，请重试')
  } finally {
    paying.value = false
  }
}

onMounted(loadDefaultVehicle)
</script>

<style scoped>
.billing-page {
  max-width: 760px;
  margin: 0 auto;
  width: 100%;
}

.page-header {
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

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  margin-bottom: 1.5rem;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.panel-icon { font-size: 1.5rem; margin-top: 2px; }

.panel-head h2 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--navy-dark);
  margin-bottom: 0.2rem;
}

.panel-head p { font-size: 0.85rem; color: var(--muted); }

.search-row {
  display: flex;
  gap: 1rem;
}

.plate-input {
  flex: 1;
  padding: 0.9rem 1.2rem;
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

.btn {
  padding: 0.9rem 1.8rem;
  border-radius: 10px;
  border: none;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.btn-primary { background: var(--navy-dark); color: #fff; }
.btn-primary:hover:not(:disabled) { background: #000; transform: translateY(-1px); }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }

.result-panel { border-left: 4px solid var(--brand); }

.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.plate-badge {
  background: var(--navy-dark);
  color: #fff;
  padding: 0.4rem 1.2rem;
  border-radius: 8px;
  font-size: 1.3rem;
  font-weight: 800;
  letter-spacing: 2px;
}

.status-tag {
  padding: 0.3rem 0.9rem;
  border-radius: 50px;
  font-size: 0.8rem;
  font-weight: 700;
}

.status-tag.unpaid {
  background: #fff5f5;
  color: var(--danger);
  border: 1px solid #fed7d7;
}

.bill-rows { display: flex; flex-direction: column; gap: 1rem; }

.bill-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1rem;
  color: var(--text);
}

.bill-row span:first-child { color: var(--muted); }
.duration { color: var(--navy); font-weight: 600; }
.bill-divider { height: 1px; background: var(--border); }

.total-row { font-size: 1.1rem; }
.amount {
  font-size: 2.2rem;
  font-weight: 900;
  color: var(--brand);
}

.btn-pay {
  width: 100%;
  justify-content: center;
  margin-top: 2rem;
  padding: 1.1rem;
  background: var(--brand);
  color: #fff;
  font-size: 1.1rem;
  border-radius: 12px;
}

.btn-pay:hover:not(:disabled) {
  background: var(--brand-dark);
  box-shadow: 0 6px 20px rgba(66,185,131,0.3);
  transform: translateY(-2px);
}

.empty-panel {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-icon {
  font-size: 4rem;
  color: var(--brand);
  opacity: 0.3;
  margin-bottom: 1rem;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* 过渡动画 */
.slide-up-enter-active { transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-up-enter-from { opacity: 0; transform: translateY(20px); }

@media (max-width: 600px) {
  .search-row { flex-direction: column; }
  .panel { padding: 1.25rem; }
}
</style>
