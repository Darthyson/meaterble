import asyncio

from bleak import BleakScanner, BLEDevice

from meater import MeaterProbe


class AutoDiscovery:
    @staticmethod
    async def discover(uuid_to_search: str) -> list[str]:
        devices: list[BLEDevice] = await BleakScanner.discover(timeout=5.0,
                                                               return_adv=False,
                                                               service_uuids=[uuid_to_search])
        device_list: list[str] = []
        for device in devices:
            device_list.append(device.address)
        return device_list


if __name__ == "__main__":
    result = asyncio.run(AutoDiscovery.discover(MeaterProbe.BLTE_UUID_SERVICE_MEATER))
    print("Discovery result:", result)