import os
import subprocess
import time
import atexit
import RPi.GPIO as GPIO
import argparse
import logging

# 设置日志的格式和级别
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)

# 使用argparse模块来处理命令行参数
parser = argparse.ArgumentParser(
    description="A program to play wav files using fm transmitter")
parser.add_argument("-m", "--music", type=str,
                    default="wav_files", help="The folder path of wav files")
parser.add_argument("-c", "--count", type=str,
                    default="count.dat", help="The count file path")
parser.add_argument("-f", "--folder", type=str,
                    default=os.getcwd(), help="The work folder")
parser.add_argument("-s", "--slow_music", type=str,
                    default="slow_wav", help="The slow music work folder")
parser.add_argument("-t", "--transmitter", type=str,
                    default="fmt", help="The fm transmitter path")
parser.add_argument("-q", "--frequency", type=float,
                    default=88.7, help="The frequency of fm transmission")
args = parser.parse_args()

# 使用变量来存储参数的值
folder_path = f"{args.folder}/{args.music}"
count_file = f"{args.folder}/{args.count}"
fm_tra = f"{args.folder}/{args.transmitter}"
slow_folder = f"{args.folder}/slow_wav"
caodong_list = f"{args.folder}/caodong.json"
freq = args.frequency

current_index = 0

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


def check_c():
    global wav_file_list, current_index
    if current_index >= len(wav_file_list):
        current_index = 0
    if current_index < 0:
        current_index = len(wav_file_list) - 1


def bef_exit():
    subprocess.run(["sudo", "killall", "-s", "SIGTERM", "fmt"])
    GPIO.cleanup()


atexit.register(bef_exit)


def break_play():
    subprocess.run(["sudo", "killall", "-s", "SIGTERM", "fmt"])
    logging.info("Terminated the subprocess")
    time.sleep(2)


class gpio_ctrl:
    bcm_list = [16, 20, 21, 19, 26, 13, 6, 5, 12]

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
        global current_index, wav_file_list
        gs = self.get_gpio()
        if gs["5"] == 1:
            wav_file_list = scan_files(slow_folder, "wav")
            wav_file_list = sorted(wav_file_list, key=lambda x: x.lower())
            logging.info(wav_file_list)
        if gs["6"] == 1:
            # 获取出现指定字符串的第一个元素的下标
            keyword = "万能青年旅店"
            keyword_index = 0
            for index, item in enumerate(wav_file_list):
                if keyword in item:
                    keyword_index = index
                    break  # 找到后立即退出循循
            current_index = keyword_index
        if gs["21"] == 1:
            current_index = 0
            logging.info("播放第一首")
        if gs["16"] == 1:
            current_index -= 2
            logging.info("播放上一首")
        if gs["20"] == 1:
            logging.info("播放下一首")
        if gs["26"] == 1:
            current_index = 11
            logging.info("但 in Caodong")
        if gs["13"] == 1:
            wav_file_list = scan_files(folder_path, "wav")
            wav_file_list = sorted(wav_file_list)
            logging.info(wav_file_list)
        if gs["19"] == 1:
            # Hardcode
            import json
            with open(caodong_list, "r") as caodong_f:
                data = json.load(caodong_f)
                caodong = data["songs"]
            wav_file_list = [os.path.join(folder_path, x) for x in caodong]
            current_index = 0
            logging.info(wav_file_list)
            logging.info("草东模式")

        check_c()
        gs["12"] = 0
        if 1 in gs.values():
            logging.info(f"{gs}, {current_index}, {1 in gs.values()}")
            break_play()


wav_file_list = scan_files(folder_path, "wav")
wav_file_list = sorted(wav_file_list)
logging.info(wav_file_list)


def play():
    global current_index
    gs = GPIO_CTR.get_gpio()
    if gs["12"] == 1:
        current_index -= 1
    logging.info(f"Now count: {current_index} File: {wav_file_list[current_index]}")
    logging.info(["sudo", fm_tra, f"-f {freq}", wav_file_list[current_index]])
    # 使用f-string来格式化字符串
    sub_play_process = subprocess.Popen(
        ["sudo", fm_tra, f"-f {freq}", wav_file_list[current_index]])

    # 假若到达数组长度则重置
    # 不重置将会超出数组长度引发报错
    current_index += 1
    check_c()

    with open(count_file, "w") as count_f:
        count_f.write(str(current_index))

    while True:
        subp_p = sub_play_process.poll()
        if subp_p is not None:
            break
        time.sleep(0.5)
        GPIO_CTR.gpio_func()


# 使用if __name__ == "__main__"来判断是否是主程序
if __name__ == "__main__":
    # 使用try-except语句来处理可能出现的异常
    try:
        if os.path.exists(count_file):
            with open(count_file, "r") as f:
                current_index = int(f.read())
        # 读取数据后判断是否在范围内
        check_c()
        GPIO_CTR = gpio_ctrl()
        # INIT GPIO
        GPIO_CTR.init_gpio()
        if GPIO_CTR.get_gpio()["21"] == 1:
            current_index = 0

        with open(count_file, "w") as f:
            f.write(str(current_index))
        while True:
            play()
    except Exception as e:
        logging.error(e)
        bef_exit()
