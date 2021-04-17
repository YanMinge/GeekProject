#!/usr/bin/env python3
import sys
import time

sys.path.append(r"../")

from communication.bluetooth import bluetooth

def main():
    bluetooth.setup()
    while True:
        array_data = bluetooth.recv()
        if array_data is not None:
            item_type = type(array_data)
            print(array_data)
            if (item_type is int):
                item_type = bytes((array_data,))
            if (item_type is str):
                send_data = "rsp:" + array_data
                send(send_data)

try:  
    main()
except Exception as e:
    print("bluetooth_exit")
    bluetooth.bluetooth_exit()
    print(e)
    pass