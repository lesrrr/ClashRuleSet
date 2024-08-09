import os
import signal
import time
import sys
import subprocess
import logging
import datetime
import random
import string

# 根据自己的设备设置worker数量
workers = 16
# 检测时间间隔，单位：秒
check_interval = 600
# 粘贴code
code = ""
# 设置触发重启所有（kuzco/ollama）进程的最低阈值，释放内存和显存。比如你机器600秒平均推理数量为600，建议设置为200，设置为平均推数量的1/3
threshold = 200

worker_ids = {}
log_directory = 'log'
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

logging.basicConfig(
    filename='kuzco_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def count_finish(file_path):
    try:
        subprocess.run('sync', shell=True, check=True)
        with open(file_path, 'r') as file:
            content = file.read()
            return content.count('finished')
    except FileNotFoundError:
        return 0

def generate_worker_id(length=22):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def start_worker(worker_id, code, worker_ids):
    worker_id_str = generate_worker_id()
    log_file_path = os.path.join(log_directory, f'log{worker_id}.txt')
    command = f"kuzco worker start --worker {worker_id_str} --code {code}"
    with open(log_file_path, 'w') as log_file:
        process = subprocess.Popen(command, shell=True, stdout=log_file, stderr=subprocess.STDOUT)
        log_file.flush()
        worker_ids[worker_id] = worker_id_str
    logging.info(f"启动{worker_id}号进程, Worker ID: {worker_id_str}")
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d|%H:%M:%S')} 🪄 启动{GREEN}{worker_id}{RESET}号进程, Worker ID: {GREEN}{worker_id_str}{RESET}")
    time.sleep(6)

def start_kuzco(workers, code, worker_ids):
    for i in range(1, workers + 1):
        start_worker(i, code, worker_ids)

def kill_worker(worker_id, worker_ids):
    worker_id_str = worker_ids[worker_id]
    log_file_path = os.path.join(log_directory, f'log{worker_id}.txt')
    try:
        pids = subprocess.check_output(f"ps aux | grep 'kuzco worker start --worker {worker_id_str}' | grep -v 'grep' | awk '{{print $2}}'", shell=True).decode().strip().split('\n')
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGKILL)
        logging.info(f"成功终止{worker_id}号进程, Worker ID: {worker_id_str}")
        print(f" 🔧 成功终止{YELLOW}{worker_id}{RESET}号进程, Worker ID: {YELLOW}{worker_id_str}{RESET}")
        if os.path.exists(log_file_path):
            os.remove(log_file_path)
            #print(f" 🔧 删除{YELLOW}{worker_id}{RESET}号日志文件: {YELLOW}{log_file_path}{RESET}")
        del worker_ids[worker_id]  
    except (subprocess.CalledProcessError, ProcessLookupError, FileNotFoundError):
        logging.warning(f"Worker ID: {worker_id_str} 不存在或已经终止")
        print(f"🧯 {RED}Worker ID: {worker_id_str} 不存在或已经终止{RED}")


def find_and_kill_processes():
    command = "ps aux | grep kuzco | grep -v grep"
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if stderr:
            print("错误:", stderr.decode())
            return

        pids = set()
        for line in stdout.decode().splitlines():
            parts = line.split()
            if len(parts) > 1:
                pid = parts[1]
                try:
                    subprocess.run(['kill', '-0', pid], check=True)
                    subprocess.run(['kill', pid], check=True)
                    #print(f"进程 {pid} 已被杀死。")
                except subprocess.CalledProcessError as e:
                    print(f"无法杀死进程/不存在或已经终止 {pid}: {e}")

        for filename in os.listdir(log_directory):
            file_path = os.path.join(log_directory, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")

def clear_all_logs():
    for i in range(1, workers + 1):
        log_file_path = f'{log_directory}/log{i}.txt'
        if os.path.exists(log_file_path):
            with open(log_file_path, 'w') as file:
                file.truncate(0)

def exit_handler(signal, frame):
    print("\n检测脚本已关闭，清除所有kuzco进程...")
    find_and_kill_processes()
    sys.exit(0)

def main():
    global worker_ids

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    start_kuzco(workers, code, worker_ids)

    while True:
        initial_finish_counts = {i: count_finish(os.path.join(log_directory, f'log{i}.txt')) for i in range(1, workers + 1)}
        time.sleep(check_interval)
        final_finish_counts = {i: count_finish(os.path.join(log_directory, f'log{i}.txt')) for i in range(1, workers + 1)}
        total_finish = sum(final_finish_counts.values())
        #logging.info(f"{check_interval // 60}内分钟完成 {total_finish} 条推理")
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d|%H:%M:%S')} 💻 {check_interval // 60}分钟内完成 {GREEN}{total_finish}{RESET} 条推理")

        if total_finish < threshold:
            print(f"{RED} ⚠️ 检测到推理量低于设定值，30秒后重新启动所有进程{RESET}")
            find_and_kill_processes()
            clear_all_logs()
            time.sleep(30)
            start_kuzco(workers, code, worker_ids)
            continue
        else:
            for i in range(1, workers + 1):
                if final_finish_counts[i] <= initial_finish_counts[i]:
                    #logging.warning(f"检测到{i}号异常，重启中...")
                    print(f"{datetime.datetime.now().strftime('%Y-%m-%d|%H:%M:%S')} ⚠️ 检测到{YELLOW}{i}{RESET}号异常，终止异常进程并重启...")
                    time.sleep(2)
                    kill_worker(i, worker_ids)
                    time.sleep(6)
                    start_worker(i, code, worker_ids)

        clear_all_logs()

if __name__ == "__main__":
    main()
