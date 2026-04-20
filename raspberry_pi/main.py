#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
树莓派综合控制端 (双摄像头版)
功能：
1. 双摄像头独立推流 (入口 19999, 出口 19998)
2. 自动断线重连
3. 多线程处理视频流与后端指令
4. 红外传感器联动
"""

import cv2
import socket
import pickle
import struct
import time
import select
import requests
import threading
from gpiozero import PWMOutputDevice, DigitalInputDevice

# ================== 配置区域 ==================
# 后端服务器地址配置
BACKEND_HOST = "192.168.137.1"      # 修改为运行 FastAPI 的电脑 IP
API_PORT = 8080                     # HTTP API 端口
API_URL = f"http://{BACKEND_HOST}:{API_PORT}/api/sensor/update"

# 摄像头与端口配置
# 入口
ENTRANCE_CAM_INDEX = 0
ENTRANCE_VIDEO_PORT = 19999
# 出口
EXIT_CAM_INDEX = 2
EXIT_VIDEO_PORT = 19998

FRAME_INTERVAL = 3                  # 每3帧发送一次 (双头建议调小频率防卡顿)

# 硬件配置 (BCM编号)
SERVO_PIN = 18                      # 舵机连接的GPIO引脚
PIN_SPOT_A = 17                     # 车位A红外传感器
PIN_SPOT_B = 27                     # 车位B红外传感器

SERVO_OPEN_DUTY = 0.075             # 抬杆占空比 (约90度)
SERVO_CLOSE_DUTY = 0.025            # 落杆占空比 (约0度)
# ============================================

# 全局变量与线程锁
barrier_lock = threading.Lock()

# ================== 舵机控制模块 ==================
def open_barrier_task(servo):
    """独立线程执行的抬杆动作，避免阻塞视频流"""
    if not barrier_lock.acquire(blocking=False):
        print(">>> [拦截] 挡车杆正在动作中，忽略重复指令")
        return

    try:
        print(">>> [舵机线程] 收到后端开门指令，启动舵机进行抬杆...")
        if servo:
            servo.value = SERVO_OPEN_DUTY
            time.sleep(3)  # 保持抬起状态3秒
            print(">>> [舵机线程] 车辆已通过，落杆...")
            servo.value = SERVO_CLOSE_DUTY
            time.sleep(0.5)
            servo.value = 0 # 释放以避免舵机抖动发热
        else:
            print(">>> [模拟硬件] 抬起停车杆 -> 3秒后落下")
            time.sleep(3)
            print(">>> [模拟硬件] 停车杆已落下")
    finally:
        barrier_lock.release()

# ================== 红外传感器监控模块 ==================
def send_update(spot_id, is_occupied):
    """向后端发送车位状态更新"""
    try:
        data = {
            "spot": spot_id,
            "occupied": is_occupied,
            "timestamp": int(time.time() * 1000)
        }
        requests.post(API_URL, json=data, timeout=2)
        print(f"[{time.strftime('%H:%M:%S')}] {spot_id} 车位同步成功 -> {'已占用' if is_occupied else '空闲'}")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] {spot_id} 同步失败: {e}")

# ================== 工具函数 ==================
def list_available_cameras():
    """检测并打印所有可用的摄像头索引"""
    print("[诊断] 正在扫描可用摄像头设备...")
    available_indexes = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_indexes.append(str(i))
            cap.release()
    if available_indexes:
        print(f"[诊断] 发现可用摄像头索引: {', '.join(available_indexes)}")
    else:
        print("[诊断] 未发现任何可用摄像头！请检查硬件连接")
    return available_indexes

# ================== 视频推送节点类 ==================
class VideoNode(threading.Thread):
    def __init__(self, camera_index, port, name, servo):
        super().__init__()
        self.camera_index = camera_index
        self.port = port
        self.node_name = name
        self.servo = servo
        self.daemon = True
        self.running = True

    def run(self):
        print(f"[{self.node_name}] 节点线程已启动 (目标 Port: {self.port})")
        
        # 尝试初始化摄像头
        cap = None
        retry_count = 0
        while self.running and not cap:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                print(f"[{self.node_name}] 无法打开摄像头 {self.camera_index}，等待5秒后重试 ({retry_count})...")
                cap.release()
                cap = None
                time.sleep(5)
                retry_count += 1
                continue
            
            # 设置分辨率
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            print(f"[{self.node_name}] 摄像头 {self.camera_index} 初始化成功")

        while self.running:
            # 建立或恢复 Socket 连接
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            
            try:
                print(f"[{self.node_name}] 正在连接后端 {BACKEND_HOST}:{self.port}...")
                client_socket.connect((BACKEND_HOST, self.port))
                client_socket.setblocking(False)
                print(f"[{self.node_name}] 连接成功！开始推送视频流...")
            except Exception as e:
                print(f"[{self.node_name}] 连接失败: {e}，5秒后重试...")
                client_socket.close()
                time.sleep(5)
                continue

            frame_count = 0
            sent_count = 0

            try:
                while self.running:
                    # 1. 接收后端指令 (select 监听)
                    try:
                        ready_to_read, _, _ = select.select([client_socket], [], [], 0.01)
                        if ready_to_read:
                            msg = client_socket.recv(1024)
                            if not msg:
                                print(f"[{self.node_name}] 后端关闭了连接")
                                break
                            
                            cmd = msg.decode('utf-8').strip()
                            if "OPEN_DOOR" in cmd:
                                threading.Thread(target=open_barrier_task, args=(self.servo,), daemon=True).start()
                    except Exception as e:
                        print(f"[{self.node_name}] 信令解析异常: {e}")
                        break

                    # 2. 采集与推流
                    ret, frame = cap.read()
                    if not ret:
                        print(f"[{self.node_name}] 读取帧失败，正在尝试重新初始化摄像头...")
                        cap.release()
                        time.sleep(2)
                        cap = cv2.VideoCapture(self.camera_index)
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        continue
                    
                    frame_count += 1
                    if frame_count % FRAME_INTERVAL == 0:
                        try:
                            # 序列化
                            data = pickle.dumps(frame, protocol=pickle.HIGHEST_PROTOCOL)
                            message_size = struct.pack(">Q", len(data))
                            
                            # 发送
                            client_socket.setblocking(True)
                            client_socket.sendall(message_size)
                            client_socket.sendall(data)
                            client_socket.setblocking(False)
                            
                            sent_count += 1
                            if sent_count % 30 == 0:
                                print(f"[{self.node_name}] 推送中... | 累计: {sent_count} 帧")
                        except Exception as e:
                            print(f"[{self.node_name}] 发送数据包失败: {e}")
                            break
                    
                    time.sleep(0.01)

            except Exception as e:
                print(f"[{self.node_name}] 运行过程中捕获到异常: {e}")
            finally:
                client_socket.close()
                print(f"[{self.node_name}] 当前连接已关闭，正在重新初始化...")
                time.sleep(1)

        if cap:
            cap.release()
        print(f"[{self.node_name}] 节点已安全退出。")

# ================== 主程序 ==================
def main():
    servo = None
    
    try:
        print("="*40)
        print(" 树莓派综合控制端 V3.1 (双摄像头 + 自动重连) ")
        print("="*40)
        
        list_available_cameras()
        print("-" * 20)
        
        # 1. 硬件初始化
        try:
            from gpiozero import PWMOutputDevice, DigitalInputDevice
            
            # 舵机
            servo = PWMOutputDevice(SERVO_PIN, frequency=50)
            servo.value = SERVO_CLOSE_DUTY
            time.sleep(0.5)
            servo.value = 0
            print(f"[OK] 舵机初始化成功于引脚 GPIO{SERVO_PIN}")
            
            # 传感器
            sensor_a = DigitalInputDevice(PIN_SPOT_A, pull_up=True, bounce_time=0.1)
            sensor_b = DigitalInputDevice(PIN_SPOT_B, pull_up=True, bounce_time=0.1)
            
            sensor_a.when_activated = lambda: send_update("A", True)
            sensor_a.when_deactivated = lambda: send_update("A", False)
            sensor_b.when_activated = lambda: send_update("B", True)
            sensor_b.when_deactivated = lambda: send_update("B", False)
            print("[OK] 红外传感器监控已启动")
            
        except Exception as e:
            print(f"[警告] 硬件初始化受限: {e}")

        # 2. 启动双摄像头推送线程
        entrance_node = VideoNode(ENTRANCE_CAM_INDEX, ENTRANCE_VIDEO_PORT, "入口Node", servo)
        exit_node = VideoNode(EXIT_CAM_INDEX, EXIT_VIDEO_PORT, "出口Node", servo)
        
        entrance_node.start()
        exit_node.start()
        
        print("\n[系统] 所有服务已启动。双路推流并行监控中...\n(按 Ctrl+C 退出)\n")
        
        # 3. 主线程维持运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[系统] 收到停止信号，正在释放资源...")
    finally:
        if servo:
            servo.close()
        print("[系统] 服务已全面停止。")

if __name__ == "__main__":
    main()
