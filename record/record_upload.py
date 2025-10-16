import subprocess
from datetime import datetime
import time  # Add this to control the loop timing
from multiprocessing import Process
import os

arecord_device = os.getenv("ARECORD_DEVICE", "plughw:2,0")

minutes = 30
while True:
    for i in range(minutes):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"/opt/bird-files/record/data_temp/Audios/{timestamp}.wav"

        command = [
            "arecord",
            "--device", arecord_device,
            "--rate", "44100", # sampling rate
            "--format", "S16_LE",
            "--channels", "2",
            "--duration", "60",
            filename
        ]
        
        # command = [
        #     "arecord",
        #     "--device", "hw:Loopback,1,0",
        #     "--rate", "32000",
        #     "--format", "S16_LE",
        #     "--channels", "1",
        #     "--duration", "60",
        #     filename
        # ]

        # command = [
        #     "arecord",
        #     "--device", "hw:Loopback,1,0",
        #     "--rate", "44100", # sampling rate
        #     "--format", "S16_LE",
        #     "--channels", "2",
        #     "--duration", "60",
        #     filename
        # ]

        # command = [
        #    "arecord",
        #    "--device", "hw:0,0",
        #    "--rate", "44100",
        #    "--format", "S16_LE",
        #    "--channels", "2",
        #    "--duration", "60",
        #    filename
        # ]

        subprocess.run(command)
        # p = Process(target=move_file, args=(filename,))
        # p.start()
        
    # p = Process(target=upload, args=())
    # p.start()


    
