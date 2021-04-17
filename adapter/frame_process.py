#!/usr/bin/env python3
from config import *
from communication.bluetooth import bluetooth
from communication.serial import usb_serial
from utils import log
from struct import pack, unpack
import time

class frame_process_class():
    def __init__(self, frame_phy, frame_protocol, port_name = "auto"):
        self.frame_phy = frame_phy
        self.port_name = port_name
        self.frame_protocol = frame_protocol
        self.byte_array_data = bytearray()
        self.prev_data = 0
        self.is_head_data_match = False
        self.head_type = None
        self.is_tail_data_match = False
        self.data_length = 0
        self.is_checksum_correct = False
        self.MAX_DATA_SIZE =  4
        if (self.frame_protocol & FRAME_PROTOCOL_COMMON_VERSION_REQ == FRAME_PROTOCOL_COMMON_VERSION_REQ) and \
           (self.frame_protocol & FRAME_PROTOCOL_COMMON_VERSION_RSP == FRAME_PROTOCOL_COMMON_VERSION_RSP):
                log.error_print("error: can't support common version req and rsp same channel!!!")

        if self.frame_phy == FRAME_PHY_BLE_SERVER:
            if bluetooth.get_serial_status() == False:
                bluetooth.setup(self.port_name)

        if self.frame_phy == FRAME_PHY_USB_SERIAL:
            if usb_serial.get_serial_status() == False:
                usb_serial.setup(self.port_name)

    def __big_string_package(self, string):
        string_frame = bytearray()
        #string_length = len(string)
        #length_bytes = string_length.to_bytes(2, "little")

        #add string len, two bytes
        #string_frame += length_bytes
        string_bytes = bytes(string, "utf8")
        string_frame += string_bytes
        return string_frame

    def get_ble_server_frame(self):
        array_data = bluetooth.recv()
        if self.split_frame(array_data):
            return self.byte_array_data
        else:
            return None

    def get_usb_serial_frame(self):
        array_data = usb_serial.recv()
        if self.split_frame(array_data):
            return self.byte_array_data
        else:
            return None

    def split_frame(self, item):
        if (self.frame_protocol != 0):
            if item is not None:
                item_type = type(item)
                if (item_type is int):
                    item = bytes((item,))
                for data in item:
                    if (item_type is str):
                        data = ord(data)
                    if(self.frame_protocol & FRAME_PROTOCOL_F0F7 == FRAME_PROTOCOL_F0F7) and \
                        data == HEAD_DATA_F0 and \
                        self.is_head_data_match == False:
                        #print("head f0 match")
                        self.is_head_data_match = True
                        self.head_type = FRAME_PROTOCOL_F0F7
                        self.byte_array_data = bytearray()
                    elif(self.frame_protocol & FRAME_PROTOCOL_F3F4 == FRAME_PROTOCOL_F3F4) and \
                        data == HEAD_DATA_F3 and \
                        self.is_head_data_match == False:
                        #print("head f3 match")
                        self.is_head_data_match = True
                        self.head_type = FRAME_PROTOCOL_F3F4
                        self.byte_array_data = bytearray()

                    elif((self.frame_protocol & FRAME_PROTOCOL_COMMON_VERSION_REQ == FRAME_PROTOCOL_COMMON_VERSION_REQ) or \
                        (self.frame_protocol & FRAME_PROTOCOL_COMMON_VERSION_RSP == FRAME_PROTOCOL_COMMON_VERSION_RSP) or \
                        (self.frame_protocol & FRAME_PROTOCOL_GAMEPAD == FRAME_PROTOCOL_GAMEPAD)) and \
                        data == HEAD_DATA_2 and self.is_head_data_match == False:
                        #print("head ff55 match")
                        if self.prev_data == HEAD_DATA_1:
                            self.is_head_data_match = True
                            self.head_type = HEAD_FF55
                            self.byte_array_data = bytearray()
                    else:
                        self.prev_data = data
                        if self.is_head_data_match:
                            self.byte_array_data.append(data)
                            if(self.head_type  == FRAME_PROTOCOL_F3F4) and (len(self.byte_array_data) == self.data_length) :
                                data_checksum = 0
                                for num in range(3, self.data_length - 2):
                                    data_checksum += self.byte_array_data[num]
                                data_checksum = data_checksum & 0x00ff
                                if(self.byte_array_data[-1] == TAIL_DATA_F4) and (data_checksum == self.byte_array_data[-2]):
                                    self.is_tail_data_match = True
                                else:
                                    self.is_tail_data_match = False
                                    self.is_head_data_match = False
                                    self.head_type = None
                                    self.data_length = 0
                            elif(self.head_type  == FRAME_PROTOCOL_F0F7) and (data == TAIL_DATA_F7):
                                self.is_tail_data_match = True

                            elif(self.head_type  == FRAME_PROTOCOL_F3F4) and (len(self.byte_array_data) >= 4):
                                head_checksum = (HEAD_DATA_F3 + self.byte_array_data[1] + self.byte_array_data[2]) & 0xff
                                data_length = (self.byte_array_data[2] << 8) & 0xff00 | self.byte_array_data[1] & 0xff
                                self.data_length = data_length + 3 + 2
                                if(head_checksum != self.byte_array_data[0]):
                                    self.is_tail_data_match = False
                                    self.is_head_data_match = False
                                    self.head_type = None
                        
                            elif(len(self.byte_array_data) >= 128):
                                self.is_tail_data_match = False
                                self.is_head_data_match = False
                                self.head_type = None
                                self.data_length = 0

                if(self.head_type  == HEAD_FF55 and \
                   self.is_head_data_match and \
                   len(self.byte_array_data) >= 0x04):
                    if (self.frame_protocol & FRAME_PROTOCOL_COMMON_VERSION_RSP == FRAME_PROTOCOL_COMMON_VERSION_RSP) and \
                       self.byte_array_data[1] == 0x04 and \
                       self.byte_array_data[2] == 0x09:
                       self.head_type =  FRAME_PROTOCOL_COMMON_VERSION_RSP
                       self.MAX_DATA_SIZE =  9 + 3
                    elif(self.frame_protocol & FRAME_PROTOCOL_COMMON_VERSION_REQ == FRAME_PROTOCOL_COMMON_VERSION_REQ) and \
                       self.byte_array_data[0] == 0x03 and \
                       self.byte_array_data[2] == 0x01 and \
                       self.byte_array_data[3] == 0x00:
                       self.head_type =  FRAME_PROTOCOL_COMMON_VERSION_REQ
                       self.MAX_DATA_SIZE =  4
                    elif(self.frame_protocol & FRAME_PROTOCOL_GAMEPAD == FRAME_PROTOCOL_GAMEPAD):
                       self.head_type =  FRAME_PROTOCOL_GAMEPAD
                       self.MAX_DATA_SIZE =  8

                if(self.head_type  == FRAME_PROTOCOL_F3F4) and \
                  (self.is_tail_data_match):
                    self.is_tail_data_match = False
                    self.is_head_data_match = False
                    self.head_type = None
                    self.data_length = 0
                    self.byte_array_data.insert(0, HEAD_DATA_F3)
                    return self.byte_array_data 

                if(self.head_type == FRAME_PROTOCOL_GAMEPAD) and \
                  (self.is_head_data_match) and \
                  (len(self.byte_array_data) == self.MAX_DATA_SIZE):
                    checksum = 0
                    for num in range(0, self.MAX_DATA_SIZE - 1):
                        checksum += self.byte_array_data[num]
                    checksum = checksum & 0x00ff
                    if(checksum == self.byte_array_data[self.MAX_DATA_SIZE - 1]):
                        self.is_head_data_match  = False
                        self.head_type = None
                        #and HEAD
                        self.byte_array_data.insert(0, HEAD_DATA_2)
                        self.byte_array_data.insert(0, HEAD_DATA_1)
                        return self.byte_array_data
                    else:
                        self.is_head_data_match = False
                        self.head_type = None

                elif((self.head_type == FRAME_PROTOCOL_COMMON_VERSION_RSP) or \
                     (self.head_type == FRAME_PROTOCOL_COMMON_VERSION_REQ)) and \
                   (self.is_head_data_match) and \
                   (len(self.byte_array_data) == self.MAX_DATA_SIZE):
                   self.is_head_data_match = False
                   self.head_type = None
                   self.byte_array_data.insert(0, HEAD_DATA_2)
                   self.byte_array_data.insert(0, HEAD_DATA_1)
                   return self.byte_array_data
        return None

    def get_frame(self):
        if self.frame_phy == FRAME_PHY_BLE_SERVER:
            return self.get_ble_server_frame()
        if self.frame_phy == FRAME_PHY_USB_SERIAL:
            return self.get_usb_serial_frame()
        return None

    def write_bytes_directly(self, item):
        if self.frame_phy == FRAME_PHY_BLE_SERVER:
            if bluetooth.get_serial_status() != True:
                while True:
                    if bluetooth.get_serial_status() == True:
                        break
                    time.sleep(0.001)
            bluetooth.send(item)
        if self.frame_phy == FRAME_PHY_USB_SERIAL:
            if usb_serial.get_serial_status() != True:
                while True:
                    if usb_serial.get_serial_status() == True:
                        break
                    time.sleep(0.001)
            usb_serial.send(item)

    def send_f3f4_frame(self, data_item):
        protocol_frame = bytearray()
        protocol_frame.append(HEAD_DATA_F3)
        datalen = len(data_item)
        data_len_byte = datalen.to_bytes(2, "little")
        head_checksum = (data_len_byte[0] + data_len_byte[1] + HEAD_DATA_F3) & 0xFF
        protocol_frame.append(head_checksum)
        protocol_frame += data_len_byte
        for data in data_item:
            protocol_frame.append(data)
        data_checksum = 0
        for i in range(len(data_item)):
            data_checksum += data_item[i]
        data_checksum = data_checksum & 0xff
        protocol_frame.append(data_checksum)
        protocol_frame.append(TAIL_DATA_F4)
        # print("send_frame:")
        # for data in protocol_frame:
        #    print(hex(data), end=" ")
        # print("")
        if self.frame_phy == FRAME_PHY_BLE_SERVER:
            self.write_bytes_directly(protocol_frame)
        if self.frame_phy == FRAME_PHY_USB_SERIAL:
            self.write_bytes_directly(protocol_frame)

    def clear_rx_buffer():
        for i in range(1000):
            frame = self.get_frame()

    def wait_script_result(self, serial_num, type):
        count = 0
        while True:
            frame = self.get_frame()
            if frame is not None:
                #for data in frame:
                #    print(hex(data), end = " ")
                #print("")
                if (frame[0] == HEAD_DATA_F3) and (frame[-1] == TAIL_DATA_F4) and len(frame) > 10:
                    serial_num_read_bytes = bytearray()
                    serial_num_read_bytes.append(frame[6])
                    serial_num_read_bytes.append(frame[7])
                    serial_num_read = unpack('h', serial_num_read_bytes)
                    #print(serial_num_read)
                    if (frame[4] == 0x28) and (frame[5] == 0x01) and(serial_num == serial_num_read[0]):
                        result = frame[8:-3]
                        if(result == bytes("None", encoding='utf-8')):
                            return None
                        if(type == "bool"):
                            if(str(result, 'utf-8') == "True"):
                                return True
                            elif(str(result, 'utf-8') == "False"):
                                return False
                        if(type == "int"):
                                return int(result)
                        if(type == "float"):
                                return float(result)
                        if(type == "str"):
                                return result
                return None
            else: 
                time.sleep(0.001)
                count = count+1
            if(count > 200):
                break
        return "Timeout"   

    def write_script(self, script, response = False, serial_num = 0, type = "str"):
        protocol_frame = bytearray()

        # add protocol id 0x28
        protocol_frame.append(0x28)
        if(response):
             #add service id 0x01
             protocol_frame.append(0x01)
             serial_num_bytes = int(serial_num).to_bytes(2, "little")
             protocol_frame += serial_num_bytes
             string_bytes = self.__big_string_package(script)
             protocol_frame += string_bytes
             retransmissions = 3
             while(retransmissions):
                 self.send_f3f4_frame(protocol_frame)
                 #print(protocol_frame)
                 result = self.wait_script_result(serial_num, type)
                 if (result is not None) and (result != "Timeout"):
                     return result
                 else:
                     log.warn_print("retransmissions(%d)" %(retransmissions))
                     retransmissions = retransmissions - 1
             return None
        else:
             #add service id 0x00
             protocol_frame.append(0x00)
             serial_num_bytes = int(serial_num).to_bytes(2, "little")
             protocol_frame += serial_num_bytes
             string_bytes = self.__big_string_package(script)
             protocol_frame += string_bytes
             self.send_f3f4_frame(protocol_frame)
             return None

        return "Timeout" 

