<template>
  <div class="parking-wrapper">
    <!-- HUD 顶部悬浮控制条 -->
    <div class="hud-bar">
      <div class="hud-title">
        <span class="live-dot"></span>
        3D 数字孪生监控
      </div>
      <div class="hud-actions">
        <button @click="resetCamera" class="hud-btn">↺ 重置视角</button>
      </div>
    </div>

    <!-- 实时通知 -->
    <Transition name="toast">
      <div v-if="notification.show" :class="['toast', notification.type]">
        <span>{{ notification.icon }}</span>
        <span>{{ notification.message }}</span>
      </div>
    </Transition>

    <!-- 3D 渲染容器 -->
    <div ref="canvasContainer" class="canvas-host"></div>

    <!-- 加载/错误遮罩 -->
    <Transition name="fade">
      <div v-if="loading || sceneError" class="overlay">
        <template v-if="!sceneError">
          <div class="spinner"></div>
          <p class="overlay-text">正在同步 3D 孪生场景...</p>
        </template>
        <template v-else>
          <div class="overlay-icon">⚠️</div>
          <p class="overlay-text error">场景加载失败<br>请确认后端服务已启动</p>
          <button @click="reloadPage" class="hud-btn">重新加载</button>
        </template>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import api from '../utils/api'

// ===== Refs =====
const canvasContainer = ref(null)
const loading = ref(true)
const sceneError = ref(false)

// ===== Three.js 对象 =====
let scene, camera, renderer, controls, animFrameId
let parkScene = null
let ws = null
let fetchTimer = null

// 模型缓存
const carModelTemplate = ref(null)
const parkingSpots = {} // spot_id -> mesh

// ===== 通知 =====
const notification = reactive({ show: false, type: '', icon: '', message: '' })

const showNotification = (type, message) => {
  const icons = { entrance: '🚗', exit: '🚙', bill: '📄', payment: '💳' }
  notification.show = true
  notification.type = type
  notification.icon = icons[type] || '📢'
  notification.message = message
  setTimeout(() => { notification.show = false }, 3500)
}

// ===== 生命周期 =====
onMounted(() => {
  // 等待两帧，确保 DOM 和 CSS 布局都已完成渲染
  requestAnimationFrame(() => requestAnimationFrame(() => {
    initThree()
    loadModels()
    connectWebSocket()
  }))
})

onUnmounted(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId)
  if (ws) ws.close()
  if (fetchTimer) clearInterval(fetchTimer)
  if (renderer) {
    renderer.dispose()
    renderer.forceContextLoss()
  }
  window.removeEventListener('resize', onResize)
})

// ===== 初始化 Three.js =====
const initThree = () => {
  const el = canvasContainer.value
  if (!el) return

  // 获取容器实际尺寸（多重回退方案）
  let W = el.clientWidth || el.getBoundingClientRect().width || window.innerWidth
  let H = el.clientHeight || el.getBoundingClientRect().height || (window.innerHeight - 64)

  // 确保有效
  if (W < 1) W = window.innerWidth
  if (H < 1) H = window.innerHeight - 64

  // ---- 场景 ----
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x1a202c)
  scene.fog = new THREE.FogExp2(0x1a202c, 0.005)

  // ---- 相机 ----
  camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 5000)
  camera.position.set(0, 120, 100)
  camera.lookAt(0, 0, 20)

  // ---- 渲染器 ----
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
  renderer.setSize(W, H)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  el.appendChild(renderer.domElement)

  // ---- 灯光 ----
  scene.add(new THREE.AmbientLight(0xffffff, 0.7))
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.0)
  dirLight.position.set(30, 80, 40)
  dirLight.castShadow = true
  dirLight.shadow.mapSize.set(2048, 2048)
  scene.add(dirLight)

  // 补光
  const fillLight = new THREE.DirectionalLight(0x4fc3f7, 0.3)
  fillLight.position.set(-30, 20, -20)
  scene.add(fillLight)

  // ---- 控制器 ----
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.06
  controls.target.set(0, 0, 20)
  controls.minDistance = 20
  controls.maxDistance = 500
  controls.maxPolarAngle = Math.PI / 2.1

  // ---- 动画循环 ----
  const animate = () => {
    animFrameId = requestAnimationFrame(animate)
    controls.update()
    renderer.render(scene, camera)
  }
  animate()

  // ---- 响应窗口尺寸变化 ----
  window.addEventListener('resize', onResize)
}

const onResize = () => {
  const el = canvasContainer.value
  if (!el || !camera || !renderer) return
  const W = el.clientWidth
  const H = el.clientHeight
  if (W < 1 || H < 1) return
  camera.aspect = W / H
  camera.updateProjectionMatrix()
  renderer.setSize(W, H)
}

// ===== 加载模型 =====
const loadModels = () => {
  const loader = new GLTFLoader()

  loader.load(
    'http://192.168.137.1:8080/static/scene.glb',
    (gltf) => {
      parkScene = gltf.scene

      // 阴影
      parkScene.traverse(child => {
        if (child.isMesh) { child.receiveShadow = true; child.castShadow = true }
      })

      // 自动适配模型尺寸
      const box0 = new THREE.Box3().setFromObject(parkScene)
      const size0 = box0.getSize(new THREE.Vector3())
      const maxDim = Math.max(size0.x, size0.y, size0.z)
      if (maxDim > 500) parkScene.scale.setScalar(0.01)
      else if (maxDim > 50) parkScene.scale.setScalar(0.1)
      // maxDim <= 50: 保持原始比例

      // 更新矩阵后居中
      parkScene.updateMatrixWorld(true)
      const box1 = new THREE.Box3().setFromObject(parkScene)
      const center = box1.getCenter(new THREE.Vector3())
      parkScene.position.x -= center.x
      parkScene.position.z -= center.z
      parkScene.position.y -= box1.min.y // 地面对齐 Y=0

      scene.add(parkScene)

      // 调试信息
      const final = new THREE.Box3().setFromObject(parkScene)
      console.log('[场景] 包围盒', final)
      console.log('[场景] 尺寸', final.getSize(new THREE.Vector3()))

      // 加载车辆模型
      loader.load(
        'http://192.168.137.1:8080/static/车子.glb',
        (carGltf) => {
          const car = carGltf.scene
          car.traverse(c => { if (c.isMesh) { c.castShadow = true } })
          car.scale.setScalar(0.012)
          carModelTemplate.value = car
          loading.value = false
          fetchParkingStatus()
        },
        undefined,
        (err) => {
          console.error('车辆模型加载失败', err)
          sceneError.value = true
          loading.value = false
        }
      )
    },
    undefined,
    (err) => {
      console.error('场景模型加载失败', err)
      sceneError.value = true
      loading.value = false
    }
  )
}

// ===== 相机重置 =====
const resetCamera = () => {
  if (!camera || !controls) return
  camera.position.set(0, 120, 100)
  controls.target.set(0, 0, 20)
  controls.update()
}

const reloadPage = () => window.location.reload()

// ===== 车位坐标 =====
const spotPositions = {
  'A': new THREE.Vector3(13, 1, 105),
  'B': new THREE.Vector3(21, 1, 105)
}

// ===== 更新车辆模型 =====
const updateCarModel = (spotId, occupied) => {
  if (occupied && !parkingSpots[spotId]) {
    if (carModelTemplate.value && spotPositions[spotId]) {
      const clone = carModelTemplate.value.clone()
      clone.position.copy(spotPositions[spotId])
      scene.add(clone)
      parkingSpots[spotId] = clone
    }
  } else if (!occupied && parkingSpots[spotId]) {
    scene.remove(parkingSpots[spotId])
    parkingSpots[spotId] = null
  }
}

// ===== 主动拉取状态 =====
const fetchParkingStatus = async () => {
  try {
    const res = await api.get('/parking/status')
    if (res.data.code === 200) {
      const spots = res.data.data.spots
      if (Array.isArray(spots)) spots.forEach(s => updateCarModel(s.id, s.occupied))
    }
  } catch (err) {
    console.error('拉取停车场状态失败', err)
  }
}

// ===== WebSocket =====
const connectWebSocket = () => {
  ws = new WebSocket('ws://192.168.137.1:8080/ws')

  ws.onopen = () => {
    const token = localStorage.getItem('token')
    if (token) ws.send(JSON.stringify({ type: 'login', token }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'sensorUpdate' || data.type === 'spotUpdate') {
        updateCarModel(data.spot, data.occupied)
      } else if (data.type === 'parkingStatus' && Array.isArray(data.spots)) {
        data.spots.forEach(s => updateCarModel(s.id, s.occupied))
      } else if (data.type === 'entranceEvent') {
        showNotification('entrance', data.message)
      } else if (data.type === 'exitEvent') {
        showNotification('exit', data.message)
      } else if (data.type === 'billGenerated') {
        showNotification('bill', data.message)
      } else if (data.type === 'paymentSuccess' || data.type === 'paymentRequired') {
        showNotification('payment', data.message)
      }
    } catch (err) {
      console.error('WebSocket 消息解析失败', err)
    }
  }

  ws.onclose = () => {
    if (!fetchTimer) fetchTimer = setInterval(fetchParkingStatus, 10000)
  }

  ws.onerror = (err) => console.error('WebSocket 错误', err)
}
</script>

<style scoped>
/*
  parking-wrapper 使用 position:fixed，直接锚定到视口，
  完全不依赖父级布局传递高度。这是解决 Three.js 容器高度
  为 0 问题最可靠的方案。
  top: var(--nav-h) 使它从导航栏下方开始。
*/
.parking-wrapper {
  position: fixed;
  top: var(--nav-h);
  left: 0;
  right: 0;
  bottom: 0;
  background: #1a202c;
  overflow: hidden;
  z-index: 10;
}

/* 3D 画布宿主，完整填充父容器 */
.canvas-host {
  width: 100%;
  height: 100%;
  display: block;
}

/* HUD 悬浮条 */
.hud-bar {
  position: absolute;
  top: 1.2rem;
  left: 1.2rem;
  right: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 50;
  pointer-events: none;
}

.hud-title {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(26, 32, 44, 0.75);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.1);
  color: #fff;
  padding: 0.65rem 1.4rem;
  border-radius: 50px;
  font-weight: 600;
  font-size: 0.95rem;
  pointer-events: auto;
}

.live-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #42b983;
  box-shadow: 0 0 0 0 rgba(66,185,131,0.6);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 rgba(66,185,131,0.6); }
  70%  { box-shadow: 0 0 0 8px rgba(66,185,131,0); }
  100% { box-shadow: 0 0 0 0 rgba(66,185,131,0); }
}

.hud-actions { pointer-events: auto; }

.hud-btn {
  background: rgba(66, 185, 131, 0.15);
  border: 1px solid rgba(66, 185, 131, 0.5);
  color: #42b983;
  padding: 0.6rem 1.4rem;
  border-radius: 50px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
}

.hud-btn:hover {
  background: #42b983;
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(66,185,131,0.3);
}

/* 加载/错误遮罩 */
.overlay {
  position: absolute;
  inset: 0;
  background: rgba(26, 32, 44, 0.92);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  z-index: 30;
}

.overlay-text {
  color: #a0aec0;
  font-size: 1rem;
  text-align: center;
  line-height: 1.6;
}

.overlay-text.error { color: #fc8181; }
.overlay-icon { font-size: 3rem; }

.spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: #42b983;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* 通知 Toast */
.toast {
  position: absolute;
  top: 5rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.8rem 1.6rem;
  border-radius: 50px;
  color: #fff;
  font-weight: 600;
  font-size: 0.95rem;
  z-index: 60;
  white-space: nowrap;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}

.toast.entrance { background: linear-gradient(135deg, #27ae60, #2ecc71); }
.toast.exit      { background: linear-gradient(135deg, #2980b9, #3498db); }
.toast.bill      { background: linear-gradient(135deg, #8e44ad, #9b59b6); }
.toast.payment   { background: linear-gradient(135deg, #e67e22, #f39c12); }

/* 动画 */
.toast-enter-active, .toast-leave-active    { transition: all 0.35s ease; }
.toast-enter-from,   .toast-leave-to        { opacity: 0; transform: translateX(-50%) translateY(-16px); }
.fade-enter-active,  .fade-leave-active     { transition: opacity 0.3s; }
.fade-enter-from,    .fade-leave-to         { opacity: 0; }
</style>
