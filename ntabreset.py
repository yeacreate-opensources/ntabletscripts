#!/usr/bin/env python3
# Copyright 2020 Commonwealth Scientific and Research Organisation
# (CSIRO)
# Author: Peter Chubb
# SPDX-License-Identifier:	GPL-2.0+
#
# Parts taken from example code in https://github.com/aaugustin/websockets/
#

import sys
import asyncio
import websockets
import time
from getopt import gnu_getopt

def Usage() -> None:
    print("Usage: ntabreset -h host -u user -p password")
    sys.exit(1)


async def reset(uri: str):
    async with websockets.connect(uri) as websocket:
        stop = '{"command":"dev_status","action":"set","sw":%d}'
        await websocket.send(stop % 1)
        time.sleep(1)
        await websocket.send(stop % 0)
        time.sleep(1)


if __name__ == "__main__":
    optlist, args = gnu_getopt(sys.argv[1:], "h:u:p:")
    user = 'admin'
    password = 'admin'
    host = None
    for o,v in optlist:
        if o == '-h':
            host = v
        elif o == '-u':
            user = v
        elif o == '-p':
            password = v
        else:
            Usage()

    if args != [] or host is None:
        Usage()
    uri = f'ws://{user}:{password}@{host}/api'
    asyncio.get_event_loop().run_until_complete(reset(uri))
