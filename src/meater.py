from typing import Optional
from bleak import BleakClient
from uuid import UUID
import time

__all__ = ["MeaterProbe"]


class MeaterProbe:
    BLTE_UUID_SERVICE_MEATER: str = "a75cc7fc-c956-488f-ac2a-2dbc08b63a04"
    _BLTE_UUID_DEVICE_NAME: UUID = "00002a00-0000-1000-8000-00805f9b34fb"
    _BLTE_UUID_FIRMWARE: UUID = "00002a26-0000-1000-8000-00805f9b34fb"
    _BLTE_UUID_TEMPERATURES: UUID = "7edda774-045e-4bbf-909b-45d1991a2876"
    _BLTE_UUID_BATTERY: UUID = "2adb4877-68d8-4884-bd3c-d83853bf27b8"

    def __init__(self, address: str):
        self.__device: Optional[BleakClient] = None
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

    def __get_unknown(self) -> int:
        return self.__unknown

    def get_device(self):
        return self.__device

    async def connect(self) -> None:
        self.__device = BleakClient(self.get_address())
        try:
            await self.__device.connect()
            await self.read_device_name()
            try:
                await self.read_firmware_revision()
                if not self.__device.is_connected:
                    print(f"{self.get_address()} got disconnected")
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

    async def read_temperatures(self) -> None:
        temperature_bytes: bytes = await self.__get_characteristic_bytes(MeaterProbe._BLTE_UUID_TEMPERATURES)
        self.__parse_temperatures(temperature_bytes)
        self.set_last_update_time()

    async def read_battery_percentage(self) -> None:
        battery_bytes: bytes = await self.__get_characteristic_bytes(MeaterProbe._BLTE_UUID_BATTERY)
        self.__battery_percentage = MeaterProbe.__bytes_to_short(battery_bytes[0], battery_bytes[1]) * 10
        self.set_last_update_time()

    async def __get_characteristic_bytes(self, uuid: UUID) -> Optional[bytes]:
        return await self.__device.read_gatt_char(uuid)

    async def __get_characteristic_str(self, uuid: UUID) -> str:
        value: bytes = await self.__get_characteristic_bytes(uuid)
        if value is None:
            return ""
        return value.decode("utf-8")

    async def read_device_name(self) -> None:
        self.__device_name = await self.__get_characteristic_str(MeaterProbe._BLTE_UUID_DEVICE_NAME)

    async def read_firmware_revision(self) -> None:
        self.__firmware_revision = await self.__get_characteristic_str(MeaterProbe._BLTE_UUID_FIRMWARE)

    def __str__(self) -> str:
        return "%s %s rev: %s tip: %9.04f°F/%9.04f°C ambient: %9.04f°F/%9.04f°C battery: %d%% age: %ds unknown: %d (0x%x)" % (
            self.get_address(), self.get_device_name(), self.get_firmware(), self.get_tip_fahrenheit(),
            self.get_tip_celsius(), self.get_ambient_fahrenheit(), self.get_ambient_celsius(),
            self.get_battery_percentage(), self.get_data_age(), self.__get_unknown(), self.__get_unknown())

