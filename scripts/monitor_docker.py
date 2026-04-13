#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker 内存监控脚本
功能：监控 Docker 容器内存，如果总内存或单个容器内存超出阈值，触发报警。
使用方法：
  请通过 crontab 来定时执行该脚本，比如每 5 分钟执行一次：
  */5 * * * * python3 /path/to/scripts/monitor_docker.py >> /tmp/docker_monitor.log 2>&1
"""
import subprocess
import json
import urllib.request
import datetime

# ================= 配置区 =================
# 单个容器报警阈值 (GB)
SINGLE_LIMIT_GB = 5.0
# 总体容器报警阈值 (GB)
TOTAL_LIMIT_GB = 5.0

# 你的 Webhook 地址 (支持飞书、钉钉、企业微信机器人)
# 例如: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxx"
WEBHOOK_URL = ""
# =========================================

def parse_to_gb(mem_str):
    """将 Docker 的内存字符串转化为 GB 数值"""
    mem_str = mem_str.strip()
    try:
        if 'GiB' in mem_str:
            return float(mem_str.replace('GiB', ''))
        elif 'MiB' in mem_str:
            return float(mem_str.replace('MiB', '')) / 1024
        elif 'KiB' in mem_str:
            return float(mem_str.replace('KiB', '')) / (1024 * 1024)
        elif 'B' in mem_str:
            return float(mem_str.replace('B', '')) / (1024 * 1024 * 1024)
    except ValueError:
        pass
    return 0.0

def send_alert(message):
    """触发报警，如果配置了 webhook，则推送到群里，否则打印到终端日志"""
    print(f"[{datetime.datetime.now()}] 🚨 告警: {message}")
    if not WEBHOOK_URL:
        # 如果没有配置 Webhook，仅仅在日志中输入（你也可以在这里增加发邮件的逻辑）
        return
    
    # 默认使用 【飞书机器人/钉钉】 的通用文本报文格式
    # （如果是企业微信，请将 msg_type 改为 "text"，然后将字段包进去）
    payload = {
        "msg_type": "text",
        "content": {
            "text": message
        }
    }
    
    try:
        req = urllib.request.Request(
            url=WEBHOOK_URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        response = urllib.request.urlopen(req, timeout=10)
        print(f"[{datetime.datetime.now()}] Webhook 发送成功，状态码: {response.status}")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Webhook 发送失败: {e}")

def main():
    try:
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', '{{.Names}}|{{.MemUsage}}'],
            capture_output=True, text=True, check=True
        )
    except Exception as e:
        print(f"[{datetime.datetime.now()}] 运行 'docker stats' 发生错误: {e}")
        return

    lines = result.stdout.strip().split('\n')
    total_mem_gb = 0.0
    alerts = []
    
    for line in lines:
        if not line:
            continue
        parts = line.split('|')
        if len(parts) != 2:
            continue
            
        name = parts[0]
        # mem_str 返回的是 "1.2MiB / 15.6GiB" 或者 "1.2GiB / 15.6GiB" 这样的格式
        # 我们只提取斜杠前边的部分（当前用量）
        mem_str = parts[1].split(' / ')[0] 
        
        mem_gb = parse_to_gb(mem_str)
        total_mem_gb += mem_gb
        
        # 1. 检查单一容器是否超出阈值
        if mem_gb >= SINGLE_LIMIT_GB:
            alerts.append(f"- 容器 [{name}] 已使用 {mem_gb:.2f}GB (超限额 {SINGLE_LIMIT_GB}GB)")
            
    # 2. 检查全部容器物理内存占用是否偏大 (如果你需要的话)
    if total_mem_gb >= TOTAL_LIMIT_GB:
        alerts.insert(0, f"⚠️ Docker 总体负载过高: 当前所有容器被分配了 {total_mem_gb:.2f}GB (整体限额 {TOTAL_LIMIT_GB}GB)")

    # 3. 发送告警
    if alerts:
        msg = "【Docker 内存资源告警】\n" + "\n".join(alerts)
        send_alert(msg)
    else:
        print(f"[{datetime.datetime.now()}] 成功检查。总共使用: {total_mem_gb:.2f}GB。暂无容器超过内存限制。")

if __name__ == '__main__':
    main()
