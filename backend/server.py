#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能停车场后端服务器 - 双摄像头版
使用FastAPI + WebSocket + MySQL
架构：视频接收线程 -> 帧队列 -> OCR处理线程 -> 支付通知线程
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import time
import asyncio
from datetime import datetime
import logging
import os
import hashlib
import secrets
import socket
import struct
import pickle
import os
import cv2
import numpy as np
import threading
import re
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor

# 强制将当前工作目录切换到 backend 文件夹所在目录
# 解决 Paddle C++ 底层遇到中文绝对路径导致无法读取模型的问题
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 导入数据库模块
from database import DatabaseManager, init_database, ParkingSpot, ParkingRecord, User, UserVehicle

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="智能停车场API",
    description="基于数字孪生技术的智能停车场管理系统 - 双摄像头版",
    version="2.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件夹用于提供3D模型文件
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# 初始化数据库
init_database()

# ============== 数据模型 ==============

class SensorUpdate(BaseModel):
    """传感器更新模型"""
    spot: str  # 车位编号（A或B）
    occupied: bool  # 是否被占用
    plate: Optional[str] = None  # 车牌号
    timestamp: Optional[int] = None  # 时间戳


class BillingQuery(BaseModel):
    """计费查询模型"""
    plate: str  # 车牌号


class BillingPay(BaseModel):
    """支付模型"""
    plate: str  # 车牌号
    amount: float  # 支付金额
    payment_method: str = "wechat"  # 支付方式


class WebRegister(BaseModel):
    """Web注册模型"""
    username: str
    password: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


class WebLogin(BaseModel):
    """Web登录模型"""
    username: str
    password: str


class VehicleBind(BaseModel):
    """车辆绑定模型"""
    user_id: int
    plate_number: str
    is_default: bool = False

class UserProfileUpdate(BaseModel):
    """用户资料更新模型"""
    user_id: int
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

class UserPasswordUpdate(BaseModel):
    """用户密码更新模型"""
    user_id: int
    old_password: str
    new_password: str

class UserDelete(BaseModel):
    """用户注销模型"""
    user_id: int


# ============== 全局状态 ==============

# WebSocket 连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket 连接建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket 连接断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.warning(f"发送消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# 用户 Token 存储 (生产环境应使用 Redis)
ACTIVE_TOKENS = {}

# ============== 核心数据结构 ==============

# 帧队列：用于视频接收线程传递帧给 OCR 处理线程
frame_queue_entrance = Queue(maxsize=10)  # 入口摄像头帧队列
frame_queue_exit = Queue(maxsize=10)      # 出口摄像头帧队列

# 客户端 socket 字典：用于向树莓派发送开闸指令
# {camera_type: socket}
camera_client_sockets = {
    "entrance": None,
    "exit": None
}
camera_sockets_lock = threading.Lock()

# 出口摄像头 socket 连接字典 {plate_number: socket}
# 用于支付成功后通知出口摄像头开闸
exit_camera_sockets = {}
exit_camera_sockets_lock = threading.Lock()

# 广播消息队列
broadcast_queue = None

# PaddleOCR Pipeline (延迟初始化)
pipeline = None
pipeline_lock = threading.Lock()


# ============== 工具函数 ==============

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def schedule_broadcast(message: dict):
    """将广播消息放入队列，由主事件循环处理"""
    global broadcast_queue
    if broadcast_queue:
        broadcast_queue.put(message)


def init_pipeline():
    """初始化 PaddleOCR Pipeline"""
    global pipeline
    with pipeline_lock:
        if pipeline is None:
            try:
                print("正在初始化 PaddleOCR Pipeline...")
                from paddlex import create_pipeline
                pipeline = create_pipeline(pipeline="./ocr_config.yaml", device="gpu")
                print("PaddleOCR Pipeline 初始化成功")
            except Exception as e:
                print(f"Pipeline 初始化失败: {e}")
    return pipeline


# ============== API 路由 ==============

@app.get("/")
async def root():
    return {"message": "智能停车场API正在运行", "version": "2.0.0"}


@app.get("/api/parking/status")
async def get_parking_status():
    """获取停车场状态"""
    try:
        db = DatabaseManager()
        with db:
            status = db.get_parking_status()
        return {"code": 200, "data": status}
    except Exception as e:
        print(f"获取停车场状态失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.post("/api/sensor/update")
async def sensor_update(data: SensorUpdate):
    """接收传感器状态更新"""
    try:
        db = DatabaseManager()
        with db:
            db.update_spot_status(data.spot, data.occupied)
        
        # 广播状态变化
        schedule_broadcast({
            "type": "spotUpdate",
            "spot": data.spot,
            "occupied": data.occupied,
            "timestamp": int(time.time() * 1000)
        })
        
        return {"code": 200, "message": f"车位 {data.spot} 状态已更新"}
    except Exception as e:
        print(f"传感器更新失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.get("/api/billing/query")
async def query_billing(plate: str):
    """查询计费信息"""
    try:
        db = DatabaseManager()
        with db:
            record = db.get_unpaid_record(plate)
        
        if record:
            return {"code": 200, "data": record}
        else:
            return {"code": 404, "message": "未找到待支付账单"}
    except Exception as e:
        print(f"查询计费信息失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.post("/api/billing/pay")
async def pay_bill(data: BillingPay):
    """支付停车费"""
    try:
        db = DatabaseManager()
        with db:
            success = db.pay_bill(data.plate, data.amount, data.payment_method)
        
        if success:
            # 支付成功，发送开闸指令
            gate_opened = False
            print(f"[支付] 支付成功，车牌: {data.plate}，发送开闸指令...")
            
            # 调试：打印当前 socket 状态
            with camera_sockets_lock:
                print(f"[支付] 当前 socket 状态: entrance={camera_client_sockets.get('entrance') is not None}, exit={camera_client_sockets.get('exit') is not None}")
            
            # 通过入口或出口摄像头 socket 发送开闸指令
            # 因为入口和出口共用同一个舵机，所以可以通过任意一个发送
            with camera_sockets_lock:
                # 优先尝试入口摄像头 socket
                entrance_socket = camera_client_sockets.get("entrance")
                print(f"[支付] 入口摄像头 socket: {entrance_socket}")
                if entrance_socket:
                    try:
                        entrance_socket.sendall(b"OPEN_DOOR")
                        print(f"[支付] 已通过入口摄像头发送开闸指令，车牌: {data.plate}")
                        gate_opened = True
                    except Exception as e:
                        print(f"[支付] 通过入口摄像头发送失败: {e}")
                
                # 如果入口摄像头发送失败，尝试出口摄像头
                if not gate_opened:
                    exit_socket = camera_client_sockets.get("exit")
                    print(f"[支付] 出口摄像头 socket: {exit_socket}")
                    if exit_socket:
                        try:
                            exit_socket.sendall(b"OPEN_DOOR")
                            print(f"[支付] 已通过出口摄像头发送开闸指令，车牌: {data.plate}")
                            gate_opened = True
                        except Exception as e:
                            print(f"[支付] 通过出口摄像头发送失败: {e}")
                
                if not gate_opened:
                    print(f"[支付] 所有摄像头连接均不可用")
            
            # 广播支付成功事件
            schedule_broadcast({
                "type": "paymentSuccess",
                "plate": data.plate,
                "amount": data.amount,
                "timestamp": int(time.time() * 1000),
                "message": f"车辆 {data.plate} 支付成功，道闸已开启"
            })
            
            return {
                "code": 200,
                "message": "支付成功" + ("，道闸已开启" if gate_opened else ""),
                "data": {
                    "orderId": f"order_{int(time.time())}",
                    "plateNumber": data.plate,
                    "amount": data.amount,
                    "paidTime": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "paid": True,
                    "gateOpened": gate_opened
                }
            }
        else:
            return {
                "code": 404,
                "message": "未找到待支付账单"
            }
    except Exception as e:
        logger.error(f"支付失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.post("/api/web/register")
async def web_register(data: WebRegister):
    """Web端用户注册"""
    try:
        db = DatabaseManager()
        with db as session:
            # 检查用户名是否已存在
            existing = session.query(User).filter(User.username == data.username).first()
            if existing:
                return {"code": 400, "message": "用户名已存在"}
            
            # 创建新用户
            user = User(
                username=data.username,
                password_hash=get_password_hash(data.password),
                nickname=data.nickname or data.username,
                avatar_url=data.avatar_url or ""
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            print(f"新用户注册: {user.id} - {user.username}")
            
            return {
                "code": 200,
                "message": "注册成功",
                "data": {
                    "userId": user.id,
                    "username": user.username,
                    "nickname": user.nickname
                }
            }
    except Exception as e:
        print(f"注册失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.post("/api/web/login")
async def web_login(data: WebLogin):
    """传统账号密码登录接口"""
    try:
        db = DatabaseManager()
        with db as session:
            # 验证用户名与密码
            user = session.query(User).filter(User.username == data.username).first()
            
            if not user or user.password_hash != get_password_hash(data.password):
                return {"code": 401, "message": "用户名或密码错误"}
            
            # 生成随机 Token
            token = secrets.token_hex(16)
            ACTIVE_TOKENS[token] = user.id
            
            print(f"用户网页登录: {user.id} - {user.username}")
            
            return {
                "code": 200,
                "message": "登录成功",
                "data": {
                    "token": token,
                    "userId": user.id,
                    "username": user.username,
                    "nickname": getattr(user, 'nickname', user.username),
                    "avatar": getattr(user, 'avatar_url', '')
                }
            }
    except Exception as e:
        print(f"网页登录失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.post("/api/user/vehicle/bind")
async def bind_vehicle(data: VehicleBind):
    """用户绑定车辆"""
    try:
        db = DatabaseManager()
        with db as session:
            # 检查车牌是否绑定过
            existing = session.query(UserVehicle).filter(
                UserVehicle.user_id == data.user_id,
                UserVehicle.plate_number == data.plate_number
            ).first()
            
            if existing:
                return {"code": 400, "message": "该车牌已在您的名下绑定过"}
            
            # 如果设为默认，先取消其他默认
            if data.is_default:
                session.query(UserVehicle).filter(
                    UserVehicle.user_id == data.user_id,
                    UserVehicle.is_default == True
                ).update({"is_default": False})
            
            # 绑定新车牌
            vehicle = UserVehicle(
                user_id=data.user_id,
                plate_number=data.plate_number,
                is_default=data.is_default
            )
            session.add(vehicle)
            session.commit()
            
            print(f"用户 {data.user_id} 绑定车辆: {data.plate_number}")
            
            return {"code": 200, "message": "绑定成功"}
    except Exception as e:
        print(f"绑定车辆失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.get("/api/user/vehicle/list")
async def get_vehicles(user_id: int):
    """获取用户绑定的车辆列表"""
    try:
        db = DatabaseManager()
        with db as session:
            vehicles = session.query(UserVehicle).filter(
                UserVehicle.user_id == user_id
            ).all()
            
            return {
                "code": 200,
                "data": [
                    {
                        "plateNumber": v.plate_number,
                        "isDefault": v.is_default,
                        "createdAt": v.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    for v in vehicles
                ]
            }
    except Exception as e:
        print(f"获取车辆列表失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.post("/api/upload/avatar")
async def upload_avatar(file: UploadFile = File(...)):
    """上传头像"""
    try:
        # 创建头像目录
        avatar_dir = os.path.join(static_path, "avatars")
        if not os.path.exists(avatar_dir):
            os.makedirs(avatar_dir)
            
        # 生成唯一文件名
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"avatar_{int(time.time())}_{secrets.token_hex(4)}.{ext}"
        file_path = os.path.join(avatar_dir, filename)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # 返回相对URL
        return {
            "code": 200,
            "message": "上传成功",
            "data": {
                "url": f"/static/avatars/{filename}"
            }
        }
    except Exception as e:
        print(f"上传头像失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.post("/api/user/profile/update")
async def update_profile(data: UserProfileUpdate):
    """更新用户资料"""
    try:
        db = DatabaseManager()
        with db:
            success = db.update_user_profile(
                data.user_id, 
                nickname=data.nickname, 
                avatar_url=data.avatar_url
            )
            
            if success:
                return {"code": 200, "message": "资料更新成功"}
            else:
                return {"code": 404, "message": "用户不存在"}
    except Exception as e:
        print(f"更新资料失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.post("/api/user/password/update")
async def update_password(data: UserPasswordUpdate):
    """更新密码"""
    try:
        db = DatabaseManager()
        with db as session:
            user = session.query(User).filter(User.id == data.user_id).first()
            if not user:
                return {"code": 404, "message": "用户不存在"}
                
            # 验证旧密码
            if user.password_hash != get_password_hash(data.old_password):
                return {"code": 400, "message": "原密码错误"}
                
            # 更新新密码
            db.update_user_password(data.user_id, get_password_hash(data.new_password))
            
            # 清除相关 token，要求重新登录
            keys_to_delete = [k for k, v in ACTIVE_TOKENS.items() if v == data.user_id]
            for k in keys_to_delete:
                del ACTIVE_TOKENS[k]
                
            return {"code": 200, "message": "密码修改成功，请重新登录"}
    except Exception as e:
        print(f"更新密码失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.post("/api/user/delete")
async def delete_user(data: UserDelete):
    """注销账号"""
    try:
        db = DatabaseManager()
        with db:
            success = db.delete_user(data.user_id)
            
            if success:
                # 清除相关 token
                keys_to_delete = [k for k, v in ACTIVE_TOKENS.items() if v == data.user_id]
                for k in keys_to_delete:
                    del ACTIVE_TOKENS[k]
                    
                return {"code": 200, "message": "账号已注销"}
            else:
                return {"code": 404, "message": "用户不存在"}
    except Exception as e:
        print(f"注销账号失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.get("/api/records/recent")
async def get_recent_records(limit: int = 10):
    """获取最近的停车记录"""
    try:
        db = DatabaseManager()
        with db:
            records = db.get_recent_records(limit)
        
        return {
            "code": 200,
            "data": records
        }
    except Exception as e:
        print(f"获取停车记录失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.get("/api/exit_records")
async def get_exit_records(page: int = 1, page_size: int = 10):
    """获取出场记录"""
    try:
        db = DatabaseManager()
        with db:
            result = db.get_billing_history(page=page, page_size=page_size)
        
        return {
            "code": 200,
            "data": result
        }
    except Exception as e:
        print(f"获取出场记录失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接处理"""
    await manager.connect(websocket)
    try:
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                print(f"收到WebSocket消息: {message}")
                
                # 处理不同类型的消息
                if message.get("type") == "getStatus":
                    # 获取状态
                    db = DatabaseManager()
                    with db:
                        status = db.get_parking_status()
                    
                    await websocket.send_text(json.dumps({
                        "type": "parkingStatus",
                        **status
                    }, ensure_ascii=False))
                
                elif message.get("type") == "login":
                    # 登录消息
                    print(f"客户端登录: {message.get('code')}")
                    
            except json.JSONDecodeError:
                print("无法解析JSON消息")
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"处理WebSocket消息失败: {e}")
                break
    
    except WebSocketDisconnect:
        print("WebSocket连接关闭")
    finally:
        manager.disconnect(websocket)


# ============== 广播消费者 ==============

async def broadcast_consumer():
    """异步任务：从队列消费消息并广播"""
    global broadcast_queue, manager
    from queue import Empty
    
    print("广播消费者任务已启动")
    while True:
        try:
            try:
                message = broadcast_queue.get_nowait()
                await manager.broadcast(message)
                logger.debug(f"已广播消息: {message.get('type')}")
            except Empty:
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"广播消费者异常: {e}")
            await asyncio.sleep(0.5)


# ============== OCR 处理函数 ==============

def process_frame_for_entrance(frame, client_socket):
    """处理入口摄像头帧 - 车辆入场识别"""
    global pipeline
    
    try:
        if pipeline is None:
            if not init_pipeline():
                return
        
        output = pipeline.predict(
            frame,
            use_doc_unwarping=False,
            use_doc_orientation_classify=False,
            use_textline_orientation=False,
            text_det_box_thresh=0.8
        )
        
        for res in output:
            if hasattr(res, 'json') and res.json:
                res_data = res.json
                if 'res' in res_data:
                    texts = res_data['res'].get('rec_texts', [])
                    for text in texts:
                        text = text.strip().replace(" ", "")
                        if re.search(r'^[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}$', text):
                            print(f">>> [入口] 成功识别到有效车牌: {text} <<<")
                            
                            db = DatabaseManager()
                            with db as session:
                                existing_record = session.query(ParkingRecord).filter(
                                    ParkingRecord.plate_number == text,
                                    ParkingRecord.exit_time == None
                                ).first()
                                
                                if not existing_record:
                                    print(f"[入口] 车牌 {text} 准许入场，生成停车记录并下发开闸指令")
                                    db.create_parking_record(text, "Entrance")
                                    
                                    schedule_broadcast({
                                        "type": "entranceEvent",
                                        "plate": text,
                                        "timestamp": int(time.time() * 1000),
                                        "message": f"车辆 {text} 已入场"
                                    })
                                    
                                    try:
                                        client_socket.sendall(b"OPEN_DOOR")
                                    except Exception as se:
                                        print(f"[入口] 发送开门指令失败: {se}")
                                else:
                                    print(f"[入口] 车牌 {text} 已经在场内，忽略重复入场")
    except Exception as e:
        print(f"[入口] OCR 处理失败: {e}")


def process_frame_for_exit(frame, client_socket):
    """处理出口摄像头帧 - 车辆出场识别"""
    global pipeline
    
    try:
        if pipeline is None:
            if not init_pipeline():
                return
        
        output = pipeline.predict(
            frame,
            use_doc_unwarping=False,
            use_doc_orientation_classify=False,
            use_textline_orientation=False,
            text_det_box_thresh=0.8
        )
        
        for res in output:
            if hasattr(res, 'json') and res.json:
                res_data = res.json
                if 'res' in res_data:
                    texts = res_data['res'].get('rec_texts', [])
                    if texts:
                        logger.debug(f"[出口] OCR 识别到文本: {texts}")
                    for text in texts:
                        text = text.strip().replace(" ", "")
                        if re.search(r'^[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}$', text):
                            print(f">>> [出口] 成功识别到有效车牌: {text} <<<")
                            
                            db = DatabaseManager()
                            with db as session:
                                existing_record = session.query(ParkingRecord).filter(
                                    ParkingRecord.plate_number == text,
                                    ParkingRecord.exit_time == None
                                ).first()
                                
                                if existing_record:
                                    if existing_record.paid:
                                        print(f"[出口] 车牌 {text} 已支付，准许出场，下发开闸指令")
                                        
                                        existing_record.exit_time = datetime.now()
                                        session.commit()
                                        
                                        schedule_broadcast({
                                            "type": "exitEvent",
                                            "plate": text,
                                            "timestamp": int(time.time() * 1000),
                                            "message": f"车辆 {text} 已出场"
                                        })
                                        
                                        try:
                                            client_socket.sendall(b"OPEN_DOOR")
                                        except Exception as se:
                                            print(f"[出口] 发送开门指令失败: {se}")
                                    else:
                                        exit_time = datetime.now()
                                        duration = (exit_time - existing_record.entry_time).total_seconds()
                                        hours = int(duration // 3600)
                                        minutes = int((duration % 3600) // 60)
                                        
                                        if hours > 0:
                                            duration_str = f"{hours}小时{minutes}分钟"
                                        else:
                                            duration_str = f"{minutes}分钟"
                                        
                                        duration_hours = duration / 3600
                                        if duration_hours <= 1:
                                            amount = 5.0
                                        else:
                                            amount = 5.0 + ((duration_hours - 1) * 6.0)
                                        amount = min(round(amount, 2), 50.0)
                                        
                                        existing_record.exit_time = exit_time
                                        existing_record.duration = duration_str
                                        existing_record.amount = amount
                                        session.commit()
                                        
                                        with exit_camera_sockets_lock:
                                            exit_camera_sockets[text] = client_socket
                                            print(f"[出口] 已保存车牌 {text} 的socket连接，当前等待支付车辆: {list(exit_camera_sockets.keys())}")
                                        
                                        print(f"[出口] 车牌 {text} 未支付，已生成账单: {amount}元，等待支付...")
                                        
                                        schedule_broadcast({
                                            "type": "billGenerated",
                                            "plate": text,
                                            "entryTime": existing_record.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                                            "exitTime": exit_time.strftime('%Y-%m-%d %H:%M:%S'),
                                            "duration": duration_str,
                                            "amount": amount,
                                            "timestamp": int(time.time() * 1000),
                                            "message": f"车辆 {text} 需支付 {amount} 元后方可出场"
                                        })
                                else:
                                    print(f"[出口] 车牌 {text} 未在停车场内，可能是识别错误")
    except Exception as e:
        print(f"[出口] OCR 处理失败: {e}")


# ============== 视频接收线程 ==============

def video_receiver_thread(port, camera_type):
    """
    视频流接收线程
    只负责接收视频帧，放入队列，不做 OCR 处理
    """
    camera_name = "入口摄像头" if camera_type == "entrance" else "出口摄像头"
    frame_queue = frame_queue_entrance if camera_type == "entrance" else frame_queue_exit
    
    SERVER_IP = "0.0.0.0"
    SERVER_PORT = port
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((SERVER_IP, SERVER_PORT))
        server_socket.listen(5)
        print(f"[{camera_name}] 视频流接收线程已启动，监听 {SERVER_IP}:{SERVER_PORT}")
    except Exception as e:
        print(f"[{camera_name}] 视频接收服务器启动失败: {e}")
        return

    while True:
        try:
            client_socket, addr = server_socket.accept()
            print(f"[{camera_name}] 树莓派摄像头已连接: {addr}")
            
            # 保存客户端 socket 引用
            with camera_sockets_lock:
                camera_client_sockets[camera_type] = client_socket
            
            # 处理该客户端的视频流
            handle_video_client(client_socket, camera_type, frame_queue)
            
        except Exception as e:
            print(f"[{camera_name}] 接收树莓派连接异常: {e}")


def handle_video_client(client_socket, camera_type, frame_queue):
    """
    处理视频客户端连接
    接收视频帧并放入队列
    """
    payload_size = struct.calcsize(">Q")
    data = b""
    frame_count = 0
    camera_name = "入口摄像头" if camera_type == "entrance" else "出口摄像头"
    
    print(f"[{camera_name}] 开始接收视频流数据...")
    
    try:
        while True:
            # 接收消息大小
            while len(data) < payload_size:
                packet = client_socket.recv(4096)
                if not packet:
                    raise ConnectionAbortedError("客户端断开连接")
                data += packet
            
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">Q", packed_msg_size)[0]
            
            # 接收完整帧数据
            while len(data) < msg_size:
                packet = client_socket.recv(4096)
                if not packet:
                    raise ConnectionAbortedError("客户端断开连接")
                data += packet
            
            frame_data = data[:msg_size]
            data = data[msg_size:]
            
            frame = pickle.loads(frame_data)
            frame_count += 1
            
            # 每30帧打印一次状态
            if frame_count % 30 == 0:
                print(f"[{camera_name}] 已接收 {frame_count} 帧")
            
            # 将帧放入队列，供 OCR 处理线程消费
            # 每隔3帧放入一次，减少 OCR 负载
            if frame_count % 3 == 0:
                try:
                    # 非阻塞放入，如果队列满则跳过
                    frame_queue.put_nowait((frame, client_socket))
                except:
                    pass  # 队列满，跳过此帧
                
    except Exception as e:
        logger.warning(f"[{camera_name}] 树莓派视频流处理结束或异常: {e}")
    finally:
        client_socket.close()
        with camera_sockets_lock:
            if camera_client_sockets.get(camera_type) == client_socket:
                camera_client_sockets[camera_type] = None
        print(f"[{camera_name}] 连接已关闭")


# ============== OCR 处理线程 ==============

def ocr_worker(camera_type):
    """
    OCR 处理线程
    从帧队列中取出帧进行 OCR 识别
    """
    camera_name = "入口摄像头" if camera_type == "entrance" else "出口摄像头"
    frame_queue = frame_queue_entrance if camera_type == "entrance" else frame_queue_exit
    
    print(f"[{camera_name}] OCR 处理线程已启动")
    
    # 延迟初始化 Pipeline
    time.sleep(5)  # 等待服务器启动完成
    init_pipeline()
    
    while True:
        try:
            # 阻塞获取帧
            frame, client_socket = frame_queue.get(timeout=1.0)
            
            # 执行 OCR 处理
            if camera_type == "entrance":
                process_frame_for_entrance(frame, client_socket)
            else:
                process_frame_for_exit(frame, client_socket)
                
        except Empty:
            continue  # 队列为空，继续等待
        except Exception as e:
            print(f"[{camera_name}] OCR 处理异常: {e}")


# ============== FastAPI 启动事件 ==============

@app.on_event("startup")
async def startup_event():
    """FastAPI 启动时初始化"""
    global broadcast_queue
    
    # 初始化广播消息队列
    broadcast_queue = Queue()
    print("广播消息队列已初始化")
    
    # 启动广播消费者任务
    asyncio.create_task(broadcast_consumer())
    print("广播消费者任务已启动")


# ============== 主程序入口 ==============

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("智能停车场后端服务器 (双摄像头版 v2.0)")
    print("=" * 50)
    print(f"HTTP API: http://localhost:8080")
    print(f"WebSocket: ws://localhost:8080/ws")
    print(f"API文档: http://localhost:8080/docs")
    print("-" * 50)
    print("视频流端口:")
    print("  - 入口摄像头: 19999 (入场识别)")
    print("  - 出口摄像头: 19998 (出场识别)")
    print("=" * 50)
    
    # 启动入口摄像头视频接收线程
    threading.Thread(
        target=video_receiver_thread,
        args=(19999, "entrance"),
        daemon=True
    ).start()
    
    # 启动出口摄像头视频接收线程
    threading.Thread(
        target=video_receiver_thread,
        args=(19998, "exit"),
        daemon=True
    ).start()
    
    # 启动入口摄像头 OCR 处理线程
    threading.Thread(
        target=ocr_worker,
        args=("entrance",),
        daemon=True
    ).start()
    
    # 启动出口摄像头 OCR 处理线程
    threading.Thread(
        target=ocr_worker,
        args=("exit",),
        daemon=True
    ).start()
    
    # 启动 FastAPI 服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True
    )
