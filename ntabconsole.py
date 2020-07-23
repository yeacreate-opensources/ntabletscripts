#!/usr/bin/env python3
# Copyright 2020 Commonwealth Scientific and Research Organisation
# (CSIRO)
# Author: Peter Chubb
# SPDX-License-Identifier:	GPL-2.0+
#
# Parts taken from example code in https://github.com/aaugustin/websockets/
#
import asyncio
import os
import io
import signal
import sys
import tty, termios
import threading
import asyncio
import re
from time import sleep
from getopt import gnu_getopt
from websockets import connect, ConnectionClosed


from typing import Any, Set


def toascii(msg: str):
    
    msg = re.sub(r'[ \n\r]', '', msg)
    if re.fullmatch(r'([a-fA-F0-9][a-fA-F0-9])*', msg) is None:
        return ''
    out = ''
    while msg != '':
        c = msg[:2]
        msg = msg[2:]
        out += chr(int(c, 16))
    return out

def exit_from_event_loop_thread(
    loop: asyncio.AbstractEventLoop, stop: "asyncio.Future[None]"
) -> None:
    loop.stop()
    if not stop.done():
        # When exiting the thread that runs the event loop, raise
        # KeyboardInterrupt in the main thread to exit the program.
        os.kill(os.getpid(), signal.SIGINT)

def print_during_input(string: str) -> None:
    sys.stdout.write(string)
    #     # Save cursor position
    #     "\N{ESC}7"
    #     # Add a new line
    #     "\N{LINE FEED}"
    #     # Move cursor up
    #     "\N{ESC}[A"
    #     # Insert blank line, scroll last line down
    #     "\N{ESC}[L"
    #     # Print string in the inserted blank line
    #     f"{string}"
    #     # Restore cursor position
    #     "\N{ESC}8"
    #     # Move cursor down
    #     "\N{ESC}[B"
    # )
    sys.stdout.flush()


def print_over_input(string: str) -> None:
    sys.stdout.write(
        # Move cursor to beginning of line
        "\N{CARRIAGE RETURN}"
        # Delete current line
        "\N{ESC}[K"
        # Print string
        f"{string}\N{LINE FEED}"
    )
    sys.stdout.flush()

async def reset(uri):
    async with connect(uri) as websocket:
        stop = '{"command":"dev_status","action":"set","sw":%d}'
        await websocket.send(stop % 1)
        sleep(1)
        await websocket.send(stop % 0)
        sleep(1)

async def run_client(
    uri: str,
    loop: asyncio.AbstractEventLoop,
    inputs: "asyncio.Queue[str]",
    stop: "asyncio.Future[None]",
    rst: "asyncio.Future[None]",
) -> None:
    try:
        websocket = await connect(uri)
    except Exception as exc:
        print_over_input(f"Failed to connect to {uri}: {exc}.")
        exit_from_event_loop_thread(loop, stop)
        return
    else:
        print_during_input(f"Connected to {uri}.\n\r")

    try:
        while True:
            incoming: asyncio.Future[Any] = asyncio.ensure_future(websocket.recv())
            outgoing: asyncio.Future[Any] = asyncio.ensure_future(inputs.get())
            done: Set[asyncio.Future[Any]]
            pending: Set[asyncio.Future[Any]]
            done, pending = await asyncio.wait(
                [incoming, outgoing, stop, rst], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks to avoid leaking them.
            if incoming in pending:
                incoming.cancel()
            if outgoing in pending:
                outgoing.cancel()

            if incoming in done:
                try:
                    message = incoming.result()
                except ConnectionClosed:
                    break
                else:
                    if isinstance(message, str):
                        if message.startswith('{"command"'):
                            continue
                        print_during_input(toascii(message))
                    else:
                        print_during_input("< (binary) " + message.hex())

            if outgoing in done:
                message = outgoing.result()
                await websocket.send(message)

            if stop in done:
                break
            if rst in done:
                await reset(uri)

    finally:
        await websocket.close()

        print_over_input(f"Connection closed.")

        exit_from_event_loop_thread(loop, stop)

def start(uri: str) -> None:

    # Create an event loop that will run in a background thread.
    loop = asyncio.new_event_loop()

    # Create a queue of user inputs. There's no need to limit its size.
    inputs: asyncio.Queue[str] = asyncio.Queue(loop=loop)

    # Create a stop condition when receiving SIGINT or SIGTERM.
    stop: asyncio.Future[None] = loop.create_future()

    # Create a stop condition when receiving SIGINT or SIGTERM.
    rst: asyncio.Future[None] = loop.create_future()

    # Schedule the task that will manage the connection.
    asyncio.ensure_future(run_client(uri, loop, inputs, stop, rst), loop=loop)

    # Start the event loop in a background thread.
    thread = threading.Thread(target=loop.run_forever)
    thread.start()
    #    sys.stdin = io.open(sys.stdin.fileno())
    old = termios.tcgetattr(0)
    tty.setraw(sys.stdin)
    # Read from stdin in the main thread in order to receive signals.
    state = 0
    try:
        while True:
            # Since there's no size limit, put_nowait is identical to put.
            message = sys.stdin.read(1).replace('"', '\\"')
            if state == 2:
                if message == '.':
                    raise EOFError
                if message == 'r': 
                    print("Resetting NTablet")
                    loop.call_soon_threadsafe(rst.set_result, None)
                else:
                    message = '~' + message
                state = 0
            elif state == 1:
                if message == '~':
                    state = 2
                    continue
                state = 0
            elif message == '\n':
                state = 1
            elif message == '\r':
                state = 1
                message = '\n'
            jsmsg = """
{ "command" : "instruct_p", "action" : "set", "msg_p" : "%s" }
""" % message
            loop.call_soon_threadsafe(inputs.put_nowait, jsmsg)
    except (KeyboardInterrupt, EOFError):  # ^C, ^D
        loop.call_soon_threadsafe(stop.set_result, None)

    # Wait for the event loop to terminate.
    thread.join()
    termios.tcsetattr(0, termios.TCSADRAIN, old)



def Usage() -> None:
    print("Usage: ntabconsole -h host -u user -p password")
    sys.exit(1)

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
    start(uri)
