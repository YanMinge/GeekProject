#!/usr/bin/env python3
import sys
import time

sys.path.append(r"../")

from communication.bluetooth import bluetooth

def main():
   bluetooth.setup()
   while True:
       print("hello GeekPlay")
       time.sleep(1)

main()