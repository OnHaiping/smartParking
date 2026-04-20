# 智能数字孪生停车管理系统 (Smart Parking System)

基于 PaddleOCR、FastAPI、Vue 3 和 Three.js 的 3D 数字孪生智能停车场管理系统。

## 🌟 系统特性

- **3D 数字孪生监控**: 使用 Three.js 构建 3D 实时监控界面，展示停车场实况。
- **高精度车牌识别**: 集成 PaddleOCR (PP-OCRv4) 实现毫秒级入场/离场识别。
- **全链路计费支付**: 自动计算停车时长、生成账单并支持在线支付状态同步。
- **多端设备互联**: 支持电脑、手机及树莓派监控端通过局域网 (192.168.137.1) 同步数据。
- **WebSocket 实时通信**: 传感器状态、车辆入离场事件秒级推送至前端。

## 🛠️ 技术栈

- **后端**: Python 3.8+, FastAPI, Uvicorn, SQLAlchemy (MySQL), PaddleOCR, OpenCV
- **前端**: Vue 3, Vite, Three.js, Axios, Vue Router
- **硬件端**: Raspberry Pi, Pi Camera, 舵机驱动, 传感器模拟

## 🚀 快速启动

### 1. 后端配置 (Backend)
```bash
cd backend
pip install -r requirements.txt
python server.py
```
- API 地址: `http://192.168.137.1:8080`
- API 文档: `/docs`

### 2. 前端配置 (Frontend)
```bash
cd frontend
npm install
npm run dev
```
- 访问地址: `http://192.168.137.1:5173`

### 3. 树莓派端 (Raspberry Pi)
```bash
cd raspberry_pi
python main.py
```

## 📦 目录结构

```text
├── backend          # Python FastAPI 后端服务及 OCR 模型
├── frontend         # Vue 3 + Three.js 3D 前端监控台
├── raspberry_pi     # 树莓派监控与硬件控制代码
└── README.md        # 项目说明文档
```

## 📝 许可证

[MIT License](LICENSE)
