#!/usr/bin/env python3
import sys
import time
import os
sys.path.append(r"../")

from communication.bluetooth import bluetooth

def main():
    bluetooth.setup()
    while True:
        array_data = bluetooth.recv()
        if array_data is not None:
            item_type = type(array_data)
            print(item_type)
            data_str = ''.join([chr(byte) for byte in array_data])
            print(data_str)
            res = os.system(data_str)
            bluetooth.send("ok")
try:  
    main()
except KeyboardInterrupt as e:
    print("bluetooth_exit")
    bluetooth.bluetooth_exit()
    print(e)
    pass