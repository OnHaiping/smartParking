#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
树莓派红外传感器监控端
负责监控两个停车位（A和B）的红外避障传感器，并实时向后端发送状态
"""

import time
import requests
from gpiozero import DigitalInputDevice
from signal import pause

# ================== 配置区域 ==================
# 后端服务器地址
BACKEND_HOST = "192.168.10.106"  # 修改为运行 FastAPI 的电脑 IP
BACKEND_PORT = 8080
API_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/sensor/update"

# 传感器 GPIO 引脚配置 (BCM编码)
PIN_SPOT_A = 17
PIN_SPOT_B = 27

# ============================================

def send_update(spot_id, is_occupied):
    """向后端发送车位状态更新"""
    try:
        data = {
            "spot": spot_id,
            "occupied": is_occupied,
            "timestamp": int(time.time() * 1000)
        }
        response = requests.post(API_URL, json=data, timeout=3)
        if response.status_code == 200:
            print(f"[{time.strftime('%H:%M:%S')}] {spot_id} 车位状态同步成功 -> {'已占用' if is_occupied else '空闲'}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 同步失败: {response.text}")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 网络请求异常: {e}")

def spot_a_detected():
    print(">>> 车位 A 检测到车辆驶入")
    send_update("A", True)

def spot_a_cleared():
    print("<<< 车位 A 车辆离开")
    send_update("A", False)

def spot_b_detected():
    print(">>> 车位 B 检测到车辆驶入")
    send_update("B", True)

def spot_b_cleared():
    print("<<< 车位 B 车辆离开")
    send_update("B", False)

if __name__ == "__main__":
    print(f"初始化传感器，连接后端: {API_URL}")
    
    # 初始化传感器
    sensor_a = DigitalInputDevice(PIN_SPOT_A, pull_up=True, bounce_time=0.1)
    sensor_b = DigitalInputDevice(PIN_SPOT_B, pull_up=True, bounce_time=0.1)

    # 绑定事件
    sensor_a.when_activated = spot_a_detected
    sensor_a.when_deactivated = spot_a_cleared
    
    sensor_b.when_activated = spot_b_detected
    sensor_b.when_deactivated = spot_b_cleared

    print("传感器监控已启动... 按 Ctrl+C 退出")
    
    # 启动时先同步一次初始状态（假设初始为空闲，或者根据当前引脚真实状态）
    # is_active 为 True 时表示引脚是高电平还是低电平取决于配置，这里直接读取状态
    # 初始状态大家可以根据自己传感器的特性（常开/常闭）调整
    try:
        # 延迟1秒让网络稳定
        time.sleep(1)
        print("发送初始状态兜底同步...")
        # send_update("A", sensor_a.is_active)  # 取决于传感器实际的高低电平
        # send_update("B", sensor_b.is_active)
        pause()
    except KeyboardInterrupt:
        print("\n正在停止监控...")
