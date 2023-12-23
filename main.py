import os
import subprocess
import time
import atexit
import RPi.GPIO as GPIO
import argparse
import logging

# 设置日志的格式和级别
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)

# 使用argparse模块来处理命令行参数
parser = argparse.ArgumentParser(description="A program to play wav files using fm transmitter")
parser.add_argument("-m", "--music", type=str, default="wav_files", help="The folder path of wav files")
parser.add_argument("-c", "--count", type=str, default="count.dat", help="The count file path")
parser.add_argument("-f", "--folder", type=str, default=os.getcwd(), help="The work folder")
parser.add_argument("-t", "--transmitter", type=str, default="fmt", help="The fm transmitter path")
parser.add_argument("-q", "--frequency", type=float, default=88.7, help="The frequency of fm transmission")
args = parser.parse_args()

# 使用变量来存储参数的值
folder_path = f"{args.folder}/{args.music}"
count_file = f"{args.folder}/{args.count}"
fm_tra = f"{args.folder}/{args.transmitter}"
freq = f"{args.folder}/{args.frequency}"

count = 0
subp = None

GPIO.cleanup()
# 获取指定目录里的所有文件(包括子目录)
def scan_files(directory, extension=None):
    # 初始化一个空列表，用于存储文件路径
    file_list = []

    # 遍历指定文件夹中的所有文件和子文件夹
    for root, directory, files in os.walk(directory):
        for filename in files:
            # 如果指定了扩展名，只返回该扩展名的文件
            if extension:
                if filename.endswith(extension):
                    # 使用os.path.join来拼接文件路径
                    file_path = os.path.join(root, filename)
                    file_list.append(file_path)
            else:
                # 如果没有指定扩展名，返回所有文件
                file_path = os.path.join(root, filename)
                file_list.append(file_path)

    return file_list

def bef_exit():
    global subp
    subp.send_signal(15)
    GPIO.cleanup()

def check_c():
    global wav_file_list, count
    if count >= len(wav_file_list):
            count = 0
    if count < 0:
        count = len(wav_file_list) - 1

atexit.register(bef_exit)

class gpio_ctrl():
    bcm_list = [16, 20, 21, 19]
    def init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        for i in self.bcm_list:
            GPIO.setup(i, GPIO.OUT) 
    
    def get_gpio(self):
        bcm_sta = {}
        for i in self.bcm_list:
            bcm_sta[str(i)] = GPIO.input(i)
        return bcm_sta
    
    def gpio_func(self):
        global count, subp, wav_file_list
        gs = self.get_gpio()
        
        if gs["21"] == 1:
            count = 0
        if gs["16"] == 1:
            count -= 2
        if gs["20"] == 1:
            count = count
        if gs["19"] == 1:
            # 获取出现指定字符串的第一个元素的下标
            keyword = "草东没有派对"
            first_index = None
            # 使用enumerate函数来遍历列表
            for index, item in enumerate(wav_file_list):
                if keyword in item:
                    first_index = index
                    break  # 找到后立即退出循循
            count = first_index

        check_c()

        if 1 in gs.values():
            subprocess.run(["sudo", "killall", "-s", "SIGTERM", "fmt"])
            logging.info("Terminated the subprocess")
            logging.info(f"{gs}, {count}, {1 in gs.values()}")
            time.sleep(2)

wav_file_list = scan_files(folder_path, "wav")
wav_file_list = sorted(wav_file_list)
logging.info(wav_file_list)

# 使用with语句来管理文件的打开和关闭
if os.path.exists(count_file):
    with open(count_file, "r") as f:
        count = int(f.read())
# 读取数据后判断是否在范围内
check_c()
GPIO_CTR = gpio_ctrl()
# INIT GPIO
GPIO_CTR.init_gpio()
if GPIO_CTR.get_gpio()["21"] == 1:
    count = 0

with open(count_file, "w") as f:
    f.write(str(count))

def play():
    global count, subp, wav_file_list
    logging.info(f"Now count: {count} File: {wav_file_list[count]}")

    # 使用f-string来格式化字符串
    subp = subprocess.Popen(["sudo", fm_tra, f"-f {freq}", wav_file_list[count]])

    # 假若到达数组长度则重置
    # 不重置将会超出数组长度引发报错
    count += 1
    check_c()

    with open(count_file, "w") as f:
        f.write(str(count))

    while True:
        subp_p = subp.poll()
        if subp_p != None:
            break
        time.sleep(0.5)
        GPIO_CTR.gpio_func()


# 使用if __name__ == "__main__"来判断是否是主程序
if __name__ == "__main__":
    # 使用try-except语句来处理可能出现的异常
    try:
        while True:
            play()
    except Exception as e:
        logging.error(e)
        bef_exit()
