#!/usr/bin/env python3
import sys
import time

sys.path.append(r"../")

from hardware.mbuild import power_expand_board

def run_dc_motor():
    power_expand_board.set_power("DC1",50)
    power_expand_board.set_power("DC2", 100)
    time.sleep(3)
    power_expand_board.set_power("DC1",-50)
    power_expand_board.set_power("DC2", -100)
    time.sleep(3)

def run_bldc_motor():
    power_expand_board.set_power("BL1",30)
    power_expand_board.set_power("BL2", 30)
    time.sleep(3)
    power_expand_board.set_power("BL1",0)
    power_expand_board.set_power("BL2", 0)
    time.sleep(3)

if (__name__ == '__main__'):
    while True:
        run_dc_motor()
        run_bldc_motor()