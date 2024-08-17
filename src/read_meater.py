#!/usr/bin/python
"""
This script connects to Meater probes via Bluetooth Low Energy (BLE)
 and reads data such as temperature and battery percentage.

Usage:
    run read_meater.py [<address_1>] [<address_2>] [<address_3>] [...] [<address_n>]
    e.g. python ./readMeater.py D0:D9:4F:83:E8:EB

Arguments:
    <address_n> (optional): The BLE addresses of the Meater probes to connect to.
                             If no addresses are provided, the script will attempt to autodiscover
                             available Meater probes within range.

Example:
    To auto-discover and connect to Meater probes, simply run:
        python read_meater.py

    To connect to specific Meater probes using their addresses, run:
        python read_meater.py D0:D9:4F:83:E8:EB D0:D9:4F:83:E8:EC
"""

import asyncio
import logging
import sys
import time
from datetime import datetime

from auto_discovery import AutoDiscovery
from meater import MeaterProbe


async def connect_devices(addresses: list[str]) -> list[MeaterProbe]:
    device_list: list[MeaterProbe] = []
    for addr in addresses:
        try:
            meater: MeaterProbe = MeaterProbe(addr)
            await meater.connect()
            device_list.append(meater)
            print(f"Connected to {addr}")
        except Exception as e:
            print(f"Failed to connect to {addr}. Error: {e}")
    return device_list


async def find_devices() -> list[str]:
    device_list: list[str] = await AutoDiscovery.discover(MeaterProbe.BLTE_UUID_SERVICE_MEATER)
    return device_list


async def main() -> None:
    log_filename: str = f"meater_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(message)s", encoding='utf-8')
    logger = logging.getLogger(__name__)

    addresses_to_connect: list[str]
    if len(sys.argv) < 2:
        print("Auto discover meaters in range")
        addresses_to_connect = await find_devices()
        if len(addresses_to_connect) == 0:
            print(f"No devices in range offering service {MeaterProbe.BLTE_UUID_SERVICE_MEATER}")
            return
    else:
        addresses_to_connect: list[str] = sys.argv[1:]

    print(f"Devices to connect: {addresses_to_connect}")
    meater_probes: list[MeaterProbe] = await connect_devices(addresses_to_connect)
    if len(meater_probes) == 0:
        print(f"Could not connect to device(s) {meater_probes}")
        return

    logger.info("date;time;model;address;battery %;unknown;tip °C;ambient °C")
    while True:
        for device in meater_probes:
            try:
                if not device.get_is_connected():
                    print(f"Ignoring disconnected device {device.get_address()} ({device.get_device_name()})")
                    time.sleep(1)
                    continue
                await device.read_temperatures()
                await device.read_battery_percentage()
                system_time: str = datetime.now().strftime("%Y-%m-%d;%H:%M:%S")
                logger.info(f"{system_time};{device.get_device_name()};{device.get_address()};"
                            f"{device.get_battery_percentage()};{device.get_unknown()};"
                            f"{device.get_tip_celsius()};{device.get_ambient_celsius()}")

                print(device)
            except Exception as e:
                print(f"Failed to read from device {device}. Error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())