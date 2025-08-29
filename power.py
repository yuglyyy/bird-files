import time
import subprocess
import re

def get_jetson_power():
    """
    tegrastats を使って Jetson の電力を取得する関数。
    出力例: RAM 377/7858MB CPU [32%@1533,22%@345] GPU 4%@76 EMC 5%@0 GR3D 0%@0 PMIC@712/0A
    ここでは PMIC の mW を取得します
    """
    result = subprocess.run(['sudo', 'tegrastats'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout
    # PMIC を正規表現で抽出 (例: PMIC@712/0A)
    match = re.search(r'VDD_IN (\d+)', output)
    print(match)
    if match:
        power_mw = int(match.group(1))
        print(power_mw)
        return power_mw / 1000  # W に変換
    return None

def average_power(duration_sec=50, interval_sec=1):
    """
    duration_sec 秒間、interval_sec ごとに電力を取得して平均を計算
    """
    readings = []
    start_time = time.time()
    while time.time() - start_time < duration_sec:
        power = get_jetson_power()
        if power is not None:
            readings.append(power)
            print(f"Current power: {power:.2f} W")
        time.sleep(interval_sec)
    
    if readings:
        avg_power = sum(readings) / len(readings)
        print(f"\nAverage power over {duration_sec} sec: {avg_power:.2f} W")
        return avg_power
    else:
        print("No power readings were obtained.")
        return None

if __name__ == "__main__":
    average_power(5, 1)  # 50秒間、1秒ごとに取得
