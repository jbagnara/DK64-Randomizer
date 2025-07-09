import socket
import logging
logger = logging.getLogger(__name__)

# https://sourceware.org/gdb/current/onlinedocs/gdb.html/Overview.html#Overview

Utils.init_logging("DK64Context", exception_logger="Client")

class ares:
    lead = '$'

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", 9123))

    def sockSend(self, payload):
        for byte in payload:
            logger.debug(byte.to_bytes().decode())

        status = self.sock.send(payload)

    def start(self):
        payload = bytearray('+'.encode())
        self.sockSend(payload)

    def read(self, addr: int, size: int):
        """
            Read length addressable memory units starting at address addr
            https://sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html#index-m-packet
        """

        self.sockSend(bytearray('$'.encode()))

        cmd = f'm{addr:08x},{size}'
        buf = bytearray(cmd, 'utf - 8')
        
        checksum = 0
        for byte in buf:
            checksum += int(byte)

        payload = bytearray(cmd.encode())
        self.sockSend(payload)

        payload = bytearray(f'#{checksum % 2**8:02x}', 'utf -8')
        self.sockSend(payload)

        print()

        rec = self.sock.recv(1 + size*2 + 3)
        print(rec)


    def write(self, addr: int, size: int, data: bytearray):
        """
            Write length addressable memory units starting at address addr
            https://sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html#index-M-packet
        """

        cmd = f'M{addr:08x},{size}'
        buf = bytearray(cmd, 'utf - 8')
        
        checksum = 0
        for byte in buf:
            checksum += int(byte)
        
        payload = bytearray(cmd.encode())
        payload.append(checksum % 2**8)
        self.sockSend(payload)
        
        checksum = 0
        for byte in buf:
            checksum += int(byte)

        payload = bytearray(cmd.encode())
        self.sockSend(payload)

        checksum = 0
        for byte in data:
            checksum += int(byte)

        payload = data
        self.sockSend(payload)

        payload = bytearray(cmd.encode())
        self.sockSend(payload)

        print()

a = ares()
a.start()

a.read(0x800001a0, 4)
