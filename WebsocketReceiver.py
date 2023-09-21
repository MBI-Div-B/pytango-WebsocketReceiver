#! /usr/bin/env python3

import asyncio
from tango import AttrWriteType, DevState, GreenMode
from tango.server import Device, attribute, command, device_property
import time


class WebsocketReceiver(Device):
    """TCP socket server to receive and store image information from PERCIVAL
    detector."""

    green_mode = GreenMode.Asyncio

    port = device_property(
        dtype=int,
        mandatory=True,
        update_db=True,
        )

    listen_host = device_property(
        dtype=str,
        default_value="0.0.0.0",
        )

    basename = attribute(
        dtype=str,
        access=AttrWriteType.READ,
        )

    nimages = attribute(
        label="images per trigger",
        dtype=int,
        access=AttrWriteType.READ,
        )

    dtime = attribute(
        label="time since last message",
        dtype=float,
        access=AttrWriteType.READ,
        )

    async def init_device(self):
        await super().init_device()
        self._basename = ''
        self._nimages = 0
        self._tlast = time.time()
        self.set_state(DevState.ON)

        self.server = await asyncio.start_server(
            self.message_handler, self.listen_host, self.port
            )
        host, port = self.server.sockets[0].getsockname()
        print(f"Listening on {host}:{port}", file=self.log_info)

    async def message_handler(self, reader, writer):
        client = writer.get_extra_info('peername')
        print(f"Connection from {client}", file=self.log_debug)
        async for line in reader:
            line = line.decode()
            print(f"Processing input: {line}", file=self.log_debug)
            try:
                line = line.split(',')
                assert len(line) == 2, "Invalid message format"
                bn = line[0].strip()
                num = int(line[1].strip())
                self._basename = bn
                self._nimages = num
                self._tlast = time.time()
                ans = "OK"
            except Exception as ex:
                print(ex, file=self.log_error)
                ans = "NOK"
            writer.write(f"{ans}\n".encode())
            await writer.drain()

    def read_basename(self):
        return self._basename

    def read_nimages(self):
        return self._nimages

    def read_dtime(self):
        return time.time() - self._tlast

    async def delete_device(self):
        self.server.close()
        await self.server.wait_closed()

if __name__ == "__main__":
    WebsocketReceiver.run_server()

