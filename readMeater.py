#!/usr/bin/python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# Find the meater address with hcitool lescan (label MEATER).
# run readMeater.py <address>
# python ./readMeater.py D0:D9:4F:83:E8:EB

import sys
import time
from meater import MeaterProbe


def connect_devices(addresses: list) -> list:
    device_list = []
    for addr in addresses:
        try:
            meater: MeaterProbe = MeaterProbe(addr)
            meater.connect()
            device_list.append(meater)
            print(f"Connected to {addr}")
        except Exception as ex:
            print(f"Failed to connect to {addr}. Reason: {ex}")
    return device_list


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <address1> [<address2> ... <addressN>]")
        return

    print("Connecting...")
    meater_probes: list = connect_devices(sys.argv[1:])
    print("Connected to all devices")

    while True:
        for device in meater_probes:
            try:
                device.read_temperatures()
                device.read_battery_percentage()
                print(device)
            except Exception as ex:
                print(f"Failed to read from device {device}. Reason: {ex}")
            time.sleep(1)


if __name__ == "__main__":
    main()