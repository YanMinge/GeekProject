#!/usr/bin/env python3

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

import array
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject

import sys
import os
from random import randint
import threading
import time
from utils import log
from communication.frame_data import frame_data_class

mainloop = None


ad_manager_interface = None
ble_advertisement = None
advertisement_status = False
bus = None
ble_server_start = False
ble_register = False
monitor_thread = None

ble_frame_data = frame_data_class(16, 16)

BLUEZ_SERVICE_NAME = 'org.bluez'
BLUEZ_DEVICE_IFACE = 'org.bluez.Device1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'

LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'

class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'

class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'

class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'

class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'

class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.duration = None
        self.timeout = None
        self.discoverable = None
        self.discoverable_timeout = None
        self.include_tx_power = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids,
                                                    signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids,
                                                    signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data,
                                                        signature='sv')
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.duration is not None:
            properties['Duration'] = dbus.Uint16(self.duration)
        if self.timeout is not None:
            properties['Timeout'] = dbus.Uint16(self.timeout)
        if self.discoverable is not None:
            properties['Discoverable'] = self.discoverable
        if self.discoverable_timeout is not None:
            properties['DiscoverableTimeout'] = dbus.Uint16(self.discoverable_timeout)
        if self.include_tx_power is not None:
            properties['IncludesTxpower'] = dbus.Boolean(self.include_tx_power)
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature='sv')
        self.service_data[uuid] = dbus.Array(data, signature='y')

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        self.local_name = dbus.String(name)

    def add_duration(self, time):
        if not self.duration:
            self.duration = dbus.UInt16(2)
        self.duration = dbus.UInt16(time)

    def add_timeout(self, time):
        if not self.timeout:
            self.timeout = dbus.UInt16(1)
        self.timeout = dbus.UInt16(time)

    def add_discoverable(self, val):
        if not self.discoverable:
            self.discoverable = True
        self.discoverable = val

    def add_discoverable_timeout(self, time):
        if not self.discoverable_timeout:
            self.discoverable_timeout = dbus.UInt16(0)
        self.discoverable_timeout = dbus.UInt16(time)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        log.info_print('GetAll')
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        log.info_print('returning props')
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        log.info_print('%s: Released!' % self.path)

class BLEAdvertisement(Advertisement):

    def __init__(self, bus, index):
        #peripheral broadcast
        Advertisement.__init__(self, bus, index, 'peripheral')
        #self.add_service_uuid('180D')
        #self.add_service_uuid('180F')
        self.add_manufacturer_data(0x424D, [0x30, 0x31, 0x6C, 0x00, 0xFA,0x10,0x1B,0x00])
        #self.add_service_data('9999', [0x00, 0x01, 0x02, 0x03, 0x04])
        local_name = 'GeekPlay_' + get_ble_mac(bus)
        self.add_local_name(local_name)
        self.add_discoverable(True)
        self.include_tx_power = True

class BLEApplication(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(TestService(bus, 0))
        

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        log.info_print('GetManagedObjects')

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_SERVICE_IFACE: {
                        'UUID': self.uuid,
                        'Primary': self.primary,
                        'Characteristics': dbus.Array(
                                self.get_characteristic_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_CHRC_IFACE: {
                        'Service': self.service.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                        'Descriptors': dbus.Array(
                                self.get_descriptor_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        log.error_print('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        log.error_print('Default WriteValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        log.error_print('Default StartNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        log.error_print('Default StopNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Descriptor(dbus.service.Object):
    """
    org.bluez.GattDescriptor1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_DESC_IFACE: {
                        'Characteristic': self.chrc.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        log.error_print('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        log.error_print('Default WriteValue called, returning error')
        raise NotSupportedException()

class TestService(Service):
    """
    Dummy test service that provides characteristics and descriptors that
    exercise various API functionality.

    """
    TEST_SVC_UUID = '0000ffe1-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.TEST_SVC_UUID, True)
        self.add_characteristic(CharacteristicFFE3(bus, 0, self))
        self.add_characteristic(CharacteristicFFE2(bus, 1, self))

class CharacteristicFFE3(Characteristic):
    """
    Dummy test characteristic. Allows writing arbitrary bytes to its value, and
    contains "extended properties", as well as a test descriptor.

    """
    RX_CHRC_UUID = '0000ffe3-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.RX_CHRC_UUID,
                ['write', 'write-without-response'],
                service)
        self.value = []

    def WriteValue(self, value, options):
        ble_frame_data.enqueue(value)

class CharacteristicFFE2(Characteristic):
    """
    Dummy test characteristic. Allows writing arbitrary bytes to its value, and
    contains "extended properties", as well as a test descriptor.

    """
    TX_CHRC_UUID = '0000ffe2-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.TX_CHRC_UUID,
                ['notify'],
                service)
        self.notifying = False

    def notify_cb(self):
        value = ble_frame_data.dequeue()
        if value is not None:
            valueData = []
            for val in value:	
                valueData.append(dbus.Byte(ord(val)))
            self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': valueData }, [])
        return self.notifying

    def update_notify_data(self):
        if not self.notifying:
            return
        GObject.timeout_add(10, self.notify_cb)

    def StartNotify(self):
        if self.notifying:
            log.info_print('Already notifying, nothing to do')
            return
        self.notifying = True
        self.update_notify_data()

    def StopNotify(self):
        if not self.notifying:
            log.info_print('Not notifying, nothing to do')
            return

        self.notifying = False
        self.update_notify_data()

def register_app_cb():
    log.info_print('GATT application registered')


def register_app_error_cb(error):
    log.error_print('Failed to register application: ' + str(error))
    mainloop.quit()

def register_ad_cb():
    global advertisement_status
    log.info_print('registered Advertisement')
    advertisement_status = True

def register_ad_error_cb(error):
    global ad_manager_interface
    global ble_advertisement
    #log.error_print('Failed to register advertisement: ' + str(error))
    print('Failed to register advertisement: ' + str(error))
    if str(error).find('AlreadyExists'):
        log.info_print('Unregister Advertisement')
        ad_manager_interface.UnregisterAdvertisement(ble_advertisement.get_path())
    advertisement_status = False
    mainloop.quit()

def get_server_manager(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o

    return None

def get_ad_manager(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in props.keys():
            return o

    return None

def get_ble_mac(bus):
    p = os.popen('hciconfig')
    data = p.read()
    len = data.find('Address')
    add = data[len+9:len+9+17]
    dbaddr = add[0:2]+add[3:5]+add[6:8]+add[9:11]+add[12:14]+add[15:17]
    return dbaddr

def set_ble_adv_inetval():
    os.popen('sudo sh -c "echo 48 >/sys/kernel/debug/bluetooth/hci0/adv_min_interval"')
    os.popen('sudo sh -c "echo 80 >/sys/kernel/debug/bluetooth/hci0/adv_max_interval"')

def get_connect_status():
    global ad_manager_interface
    global ble_advertisement
    global advertisement_status
    global ble_register
    global bus
    p = os.popen('hcitool con')
    data = p.read()
    len = data.find('> LE')
    if len > 0:
        if ad_manager_interface and ble_advertisement and advertisement_status == True:
            log.info_print("StartNotify UnregisterAdvertisement")
            ad_manager_interface.UnregisterAdvertisement(ble_advertisement.get_path())
            ble_advertisement.Release()
            advertisement_status = False
            ble_register = False
        return True
    else:
        if ad_manager_interface and ble_advertisement and advertisement_status == False and ble_register == False:
            log.info_print("StartNotify RegisterAdvertisement")
            ble_register = True
            ad_manager_interface.RegisterAdvertisement(ble_advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)
        return False

def monitor():
    while True:
        get_connect_status()
        time.sleep(0.001)

def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
    # """if it returns a number greater than one, you're in trouble,
    # and you should call it again with exc=NULL to revert the effect"""
    ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
    raise SystemError("PyThreadState_SetAsyncExc failed")

def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)

def bluetooth_exit():
    global monitor_thread
    global ad_manager_interface    
    global ble_advertisement
    global advertisement_status
    global ble_register
    if monitor_thread is not None:
        stop_thread(monitor_thread)
    if ad_manager_interface and ble_advertisement and advertisement_status == True:
        log.info_print("StartNotify UnregisterAdvertisement")
        ad_manager_interface.UnregisterAdvertisement(ble_advertisement.get_path())
        ble_advertisement.Release()
        advertisement_status = False
        ble_register = False

def loop():
    global mainloop
    mainloop.run()

def setup():
    global mainloop
    global ad_manager_interface
    global ble_advertisement
    global ble_server_start
    global ble_register
    global monitor_thread
    ad_manager_interface = None
    ble_advertisement = None
    ble_register = False
    set_ble_adv_inetval()
    monitor_thread = threading.Thread(target=monitor, args=())
    monitor_thread.setDaemon(True)
    monitor_thread.start()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    server_manager = get_server_manager(bus)
    if not server_manager:
        log.error_print('server manager interface not found')
        return

    add_manager = get_ad_manager(bus)
    if not add_manager:
        log.error_print('add manager interface not found')
        return

    service_manager_interface = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, server_manager),
            GATT_MANAGER_IFACE)

    ad_manager_interface = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, add_manager),
            LE_ADVERTISING_MANAGER_IFACE)

    ble_app = BLEApplication(bus)
    mainloop = GObject.MainLoop()

    log.info_print('Registering GATT application...')

    service_manager_interface.RegisterApplication(ble_app.get_path(), {},
                                    reply_handler=register_app_cb,
                                    error_handler=register_app_error_cb)
    log.info_print("Start BLEAdvertisement")
    ble_advertisement = BLEAdvertisement(bus, 0)

    mainloop_thread = threading.Thread(target=loop, args=())
    mainloop_thread.setDaemon(True)
    mainloop_thread.start()
    ble_server_start = True

def is_ble_server_start():
    global ble_server_start
    return ble_server_start

def send(item):
    ble_frame_data.send(item)

def recv():
    value = ble_frame_data.recv()
    return value   

