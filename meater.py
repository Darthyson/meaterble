from bluepy import btle
import time

__all__ = ['MeaterProbe']


class MeaterProbe:
    _BLTE_HANDLE_FIRMWARE: int = 22
    _BLTE_HANDLE_TEMPERATURES: int = 31
    _BLTE_HANDLE_BATTERY: int = 35

    def __init__(self, address: str):
        self.__device: btle.Peripheral = None
        self.__address: str = address
        self.__id: str = ""
        self.__firmware: str = ""
        self.__tip_temp_celsius: int = 0
        self.__ambient_temp_celsius: int = 0
        self.__unknown: int = 0
        self.__battery_percentage: int = 0
        self.__last_update_time: float = 0.0

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

    def get_id(self) -> str:
        return self.__id

    def get_firmware(self) -> str:
        return self.__firmware

    def get_last_update_time(self) -> float:
        return self.__last_update_time

    def set_last_update_time(self) -> None:
        self.__last_update_time = time.time()

    def get_data_age(self) -> float:
        return time.time() - self.__last_update_time

    def __get_unknown(self) -> int:
        return self.__unknown

    def connect(self) -> btle.Peripheral:
        self.__device = btle.Peripheral(self.__address)
        try:
            self.read_firmware_id()
        except Exception as e:
            print(f"Failed to read firmware id of device {self.__address}. Reason: {e}")

    def __parse_temperatures(self, array: bytes) -> None:
        #0x63 0x01 0x2b 0x00 0x25 0x00 0x20 0x00
        #0x30 0x00 0x32 0x00 0x25 0x00 0x1f 0x00
        #0xfc 0x0f 0x35 0x00 0x25 0x00 0x1f 0x00
        #0xe3 0x0f 0x35 0x00 0x25 0x00 0x1f 0x00
        tip_raw_data: int = MeaterProbe.__bytes_to_short(array[0], array[1])
        ambient_raw_data: int = MeaterProbe.__bytes_to_short(array[2], array[3])
        ambient_offset: int = MeaterProbe.__bytes_to_short(array[4], array[5])
        self.__unknown = MeaterProbe.__bytes_to_short(array[6], array[7]) # seen 0x20 0x00 and 0x1f 0x00

        offset: int = min(48, ambient_offset)
        ambient_raw_data = (ambient_raw_data - offset) * 9424  # 9424 = 16 * 589
        ambient_raw_data = int(ambient_raw_data / 1487)
        ambient_raw_data = max(0, ambient_raw_data)
        ambient_raw_data += tip_raw_data
        self.__tip_temp_celsius = MeaterProbe.__raw_to_celsius(tip_raw_data)
        self.__ambient_temp_celsius = MeaterProbe.__raw_to_celsius(ambient_raw_data)


    def read_temperatures(self) -> None:
        temperature_bytes: bytes = self.__device.readCharacteristic(MeaterProbe._BLTE_HANDLE_TEMPERATURES)
        self.__parse_temperatures(temperature_bytes)
        self.set_last_update_time()

    def read_battery_percentage(self) -> None:
        battery_bytes: bytes = self.__device.readCharacteristic(MeaterProbe._BLTE_HANDLE_BATTERY)
        self.__battery_percentage = MeaterProbe.__bytes_to_short(battery_bytes[0], battery_bytes[1]) * 10
        self.set_last_update_time()

    def read_firmware_id(self) -> None:
        firmware_bytes: bytes = self.__device.readCharacteristic(MeaterProbe._BLTE_HANDLE_FIRMWARE)
        (self.__firmware, self.__id) = str(firmware_bytes).split("_")

    def __str__(self) -> str:
        return "%s %s probe: %s tip: %.04f°F/%.04f°C ambient: %.04f°F/%.04f°C battery: %d%% age: %ds unknown: %d" % (
            self.get_address(), self.get_firmware(), self.get_id(), self.get_tip_fahrenheit(), self.get_tip_celsius(),
            self.get_ambient_fahrenheit(), self.get_ambient_celsius(), self.get_battery_percentage(),
            self.get_data_age(), self.__get_unknown())