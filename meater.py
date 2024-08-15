from bluepy import btle
from uuid import UUID
import time

__all__ = ["MeaterProbe"]


class MeaterProbe:
    _BLTE_UUID_DEVICE_NAME: UUID = "00002a00-0000-1000-8000-00805f9b34fb"
    _BLTE_UUID_FIRMWARE: UUID = "00002a26-0000-1000-8000-00805f9b34fb"
    _BLTE_UUID_TEMPERATURES: UUID = "7edda774-045e-4bbf-909b-45d1991a2876"
    _BLTE_UUID_BATTERY: UUID = "2adb4877-68d8-4884-bd3c-d83853bf27b8"

    def __init__(self, address: str):
        self.__device: btle.Peripheral = None
        self.__address: str = address
        self.__device_name: str = ""
        self.__firmware_revision: str = ""
        self.__tip_temp_celsius: int = 0
        self.__ambient_temp_celsius: int = 0
        self.__unknown: int = 0
        self.__battery_percentage: int = 0
        self.__last_update_time: float = 0.0

        self.__btle_handle_device_name = -1
        self.__btle_handle_firmware_revision = -1
        self.__btle_handle_temperatures = -1
        self.__btle_handle_battery = -1

    @staticmethod
    def __bytes_to_short(low_byte: int, high_byte: int) -> int:
        low_byte &= 0xff
        high_byte &= 0xff
        result: int = (high_byte << 8) | low_byte
        if result >= 2048:
            result |= -(1 << 12)
        return result

    @staticmethod
    def __raw_to_celsius(value: int) -> float:
        return (float(value) + 8.0) / 16.0

    @staticmethod
    def __celsius_to_fahrenheit(value: float) -> float:
        return ((value * 9.0) / 5.0) + 32.0

    def get_tip_celsius(self) -> float:
        return self.__tip_temp_celsius

    def get_ambient_celsius(self) -> float:
        return self.__ambient_temp_celsius

    def get_tip_fahrenheit(self) -> float:
        return MeaterProbe.__celsius_to_fahrenheit(self.__tip_temp_celsius)

    def get_ambient_fahrenheit(self) -> float:
        return MeaterProbe.__celsius_to_fahrenheit(self.__ambient_temp_celsius)

    def get_battery_percentage(self) -> int:
        return self.__battery_percentage

    def get_address(self) -> str:
        return self.__address

    def get_device_name(self) -> str:
        return self.__device_name

    def get_firmware(self) -> str:
        return self.__firmware_revision

    def get_last_update_time(self) -> float:
        return self.__last_update_time

    def set_last_update_time(self) -> None:
        self.__last_update_time = time.time()

    def get_data_age(self) -> float:
        return time.time() - self.__last_update_time

    def __get_device(self) -> btle.Peripheral:
        return self.__device

    def __get_unknown(self) -> int:
        return self.__unknown

    def connect(self) -> btle.Peripheral:
        self.__device = btle.Peripheral(self.get_address())
        try:
            # just for debugging print list of all services and characteristics
            #self.print_services_and_characteristics()
            self.__btle_handle_device_name = self.get_ble_handle_from_uuid(MeaterProbe._BLTE_UUID_DEVICE_NAME)
            self.__btle_handle_firmware_revision = self.get_ble_handle_from_uuid(MeaterProbe._BLTE_UUID_FIRMWARE)
            self.__btle_handle_temperatures = self.get_ble_handle_from_uuid(MeaterProbe._BLTE_UUID_TEMPERATURES)
            self.__btle_handle_battery = self.get_ble_handle_from_uuid(MeaterProbe._BLTE_UUID_BATTERY)
            self.read_device_name()
            try:
                self.read_firmware_revision()
            except Exception as e:
                print(f"Failed to read firmware revision from  {self.get_address()}. Error: {e}")
        except Exception as e:
            print(f"Failed to read device name from {self.get_address()}. Error: {e}")

    def __parse_temperatures(self, array: bytes) -> None:
        # some examples
        # 0x63 0x01 0x2b 0x00 0x25 0x00 0x20 0x00
        # 0x30 0x00 0x32 0x00 0x25 0x00 0x1f 0x00
        # 0xfc 0x0f 0x35 0x00 0x25 0x00 0x1f 0x00
        # 0xe3 0x0f 0x35 0x00 0x25 0x00 0x1f 0x00
        tip_raw_data: int = MeaterProbe.__bytes_to_short(array[0], array[1])
        ambient_raw_data: int = MeaterProbe.__bytes_to_short(array[2], array[3])
        ambient_offset: int = MeaterProbe.__bytes_to_short(array[4], array[5])
        self.__unknown = MeaterProbe.__bytes_to_short(array[6], array[7])  # seen 0x20 0x00 and 0x1f 0x00

        offset: int = min(48, ambient_offset)
        ambient_raw_data = (ambient_raw_data - offset) * 9424  # 9424 = 16 * 589
        ambient_raw_data = int(ambient_raw_data / 1487)
        ambient_raw_data = max(0, ambient_raw_data)
        ambient_raw_data += tip_raw_data
        self.__tip_temp_celsius = MeaterProbe.__raw_to_celsius(tip_raw_data)
        self.__ambient_temp_celsius = MeaterProbe.__raw_to_celsius(ambient_raw_data)

    def read_temperatures(self) -> None:
        temperature_bytes: bytes = self.__get_characteristic_bytes(self.__btle_handle_temperatures)
        self.__parse_temperatures(temperature_bytes)
        self.set_last_update_time()

    def read_battery_percentage(self) -> None:
        battery_bytes: bytes = self.__get_characteristic_bytes(self.__btle_handle_battery)
        self.__battery_percentage = MeaterProbe.__bytes_to_short(battery_bytes[0], battery_bytes[1]) * 10
        self.set_last_update_time()

    def get_ble_handle_from_uuid(self, uuid: UUID) -> int:
        characteristics: list = self.__get_device().getCharacteristics()
        for characteristic in characteristics:
            if characteristic.uuid == uuid:
                return characteristic.getHandle()
        return -1

    def __get_characteristic_bytes(self, handle: int) -> bytes | None:
        return self.__get_device().readCharacteristic(handle)

    def __get_characteristic_str(self, handle: int) -> str:
        value: bytes = self.__get_characteristic_bytes(handle)
        if value is None:
            return ""
        return value.decode("utf-8")

    def read_device_name(self) -> None:
        self.__device_name = self.__get_characteristic_str(self.__btle_handle_device_name)

    def read_firmware_revision(self) -> None:
        self.__firmware_revision = self.__get_characteristic_str(self.__btle_handle_firmware_revision)

    def __str__(self) -> str:
        return "%s %s rev: %s tip: %4.04f°F/%4.04f°C ambient: %4.04f°F/%4.04f°C battery: %d%% age: %ds unknown: %d (0x%x)" % (
            self.get_address(), self.get_device_name(), self.get_firmware(), self.get_tip_fahrenheit(),
            self.get_tip_celsius(), self.get_ambient_fahrenheit(), self.get_ambient_celsius(),
            self.get_battery_percentage(), self.get_data_age(), self.__get_unknown(), self.__get_unknown())

    def print_services_and_characteristics(self):
        if not self.__get_device():
            print("Device not connected")
            return

        services: list = self.__device.getServices()
        if not services:
            print(f"No services found for device {self.get_address()}")
            return

        for service in services:
            print(f"Service UUID: {service.uuid}")
            characteristics: list = service.getCharacteristics()
            if not characteristics:
                print("\tNo characteristics found")
                continue

            for characteristic in characteristics:
                try:
                    print(f"\t{characteristic}")
                    value = characteristic.read()
                    print(f"\tCharacteristic UUID: {characteristic.uuid}, value: {value}")
                except Exception as e:
                    print(f"\tCharacteristic UUID: {characteristic.uuid}, value: Not readable ({e})")
