#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
树莓派USB摄像头推流与舵机控制端
整合视频流推送与后端指令接收的功能
"""

import cv2
import socket
import pickle
import struct
import time
import select
from gpiozero import PWMOutputDevice  # 用于控制舵机

# ================== 配置区域 ==================
# 后端服务器地址和端口
BACKEND_IP = "192.168.10.106"    # 修改为运行 FastAPI 的电脑 IP
VIDEO_PORT = 19999               # 避免常用端口冲突，从 9999 改为 19999

# 摄像头配置
CAMERA_INDEX = 0                 # USB摄像头索引
FRAME_INTERVAL = 5               # 每5帧发送一次

# 硬件配置 (舵机)
SERVO_PIN = 18                   # 舵机连接的GPIO引脚 (BCM编号)
SERVO_OPEN_DUTY = 0.075          # (这里使用软PWM控制占空比，具体数值需按实体舵机测试调整：约对应 90 度)
SERVO_CLOSE_DUTY = 0.025         # (约对应 0 度)
# ============================================

def open_barrier(servo):
    """模拟抬杆动作"""
    print(">>> 收到后端开门指令，启动舵机进行抬杆...")
    
    if servo:
        # 转动到放行角度
        servo.value = SERVO_OPEN_DUTY
        time.sleep(3)  # 保持抬起状态3秒
        
        # 落杆
        print(">>> 车辆已通过，落杆...")
        servo.value = SERVO_CLOSE_DUTY
        time.sleep(0.5)
        # 释放以避免舵机抖动发热
        servo.value = 0
    else:
        # 开发测试用：没有硬件环境时的纯打印
        print(">>> [模拟硬件] 抬起停车杆 -> 3秒后落下")
        time.sleep(3)
        print(">>> [模拟硬件] 停车杆已落下")

def main():
    print("正在初始化硬件模块...")
    # 初始化舵机
    try:
        servo = PWMOutputDevice(SERVO_PIN, frequency=50)
        # 保证初始状态是关闭的
        servo.value = SERVO_CLOSE_DUTY
        time.sleep(0.5)
        servo.value = 0
        print(f"舵机初始化成功于引脚 GPIO{SERVO_PIN}")
    except Exception as e:
        print(f"[警告] 舵机初始化失败(也许不在真实的树莓派环境中): {e}")
        servo = None
    
    print("正在初始化USB摄像头...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print("错误: 无法打开USB摄像头")
        return
    
    # 设置分辨率减轻网络压力
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print(f"摄像头初始化成功 ({int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))})")
    
    # 创建socket连接，由于需要双向通信，必须长连接
    print(f"正在连接到后端 AI 推流核心 {BACKEND_IP}:{VIDEO_PORT}...")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client_socket.connect((BACKEND_IP, VIDEO_PORT))
        # 设置 socket 为非阻塞，方便同时进行发和收
        client_socket.setblocking(False)
        print("连接成功！开始双向通信...")
    except Exception as e:
        print(f"连接失败: {e}")
        cap.release()
        return
    
    frame_count = 0
    sent_count = 0
    
    try:
        while True:
            # ======= 1. 非阻塞接收后端下发的指令 =======
            ready_to_read, _, _ = select.select([client_socket], [], [], 0.01)
            if ready_to_read:
                try:
                    msg = client_socket.recv(1024)
                    if not msg:
                        print("后端连接断开...")
                        break
                    
                    cmd = msg.decode('utf-8').strip()
                    if cmd == "OPEN_DOOR":
                        open_barrier(servo)
                except Exception as e:
                    print(f"接收信令时发生错误: {e}")
                    pass
            
            # ======= 2. 视频帧采集与推送 =======
            ret, frame = cap.read()
            
            if not ret:
                print("错误: 无法读取摄像头帧，跳过本轮")
                time.sleep(1)
                continue
            
            frame_count += 1
            
            if frame_count % FRAME_INTERVAL == 0:
                try:
                    data = pickle.dumps(frame, protocol=pickle.HIGHEST_PROTOCOL)
                    message_size = struct.pack(">Q", len(data))
                    
                    # 为了安全发送，临时把 socket 设为阻塞
                    client_socket.setblocking(True)
                    client_socket.sendall(message_size)
                    client_socket.sendall(data)
                    client_socket.setblocking(False)
                    
                    sent_count += 1
                    
                    if sent_count % 30 == 0:
                        print(f"[{time.strftime('%H:%M:%S')}] 网络推流正常 | 累计已发送 {sent_count} 帧")
                        
                except Exception as e:
                    print(f"推流断开或序列化错误: {e}")
                    break
            
            # 控制帧率，防止CPU 100%
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\n正在停止双向通信服务...")
    
    finally:
        cap.release()
        client_socket.close()
        if servo:
            servo.close()
        print(f"服务结束。总共成功推送 {sent_count} 帧视频流")

if __name__ == "__main__":
    main()
