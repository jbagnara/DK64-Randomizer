import socket
import logging
import os
from time import sleep
from Utils import open_filename

logger = logging.getLogger(__name__)

# https://sourceware.org/gdb/current/onlinedocs/gdb.html/Overview.html#Overview

class AresClient:
    lead = '$'

    def __init__(self):
        """Initialize a new instance of the class."""
        self.address = "127.0.0.1"
        self.port = 9123
        self._check_client()
        self.socket = None
        self.connected_message = False
        self._connect()
        self._sendack()

    def _check_client(self):
        """Ensure the Project 64 executable and the required adapter script are properly set up.

        Raises:
            PJ64Exception: If the Project 64 executable is not found or if the `ap_adapter.js` file is in use.
        """
        logger.info("we HIGHLY Recommend you switch to linux!!!!!")
        rom = open_filename("Select ROM", (("N64 ROM", (".n64", ".z64", ".v64")),))

        # TODO Check if ares is running!!!
        os.popen(f'ares "{rom}"')
        sleep(5)

    def _connect(self):
        """Establish a connection to the specified address and port using a socket.

        If the socket is not already created, it initializes a new socket with
        AF_INET and SOCK_STREAM parameters and sets a timeout of 0.1 seconds.
        Raises:
            OSError: If the socket is already connected.
        """
        if self.connected_message:
            return
        if self.socket is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(("127.0.0.1", 9123))
            self.sock.settimeout(0.1)
        try:
            print(f"{self.address} 9123")
            self.sock.connect((self.address, 9123))
            self.connected_message = True
        except (ConnectionRefusedError, ConnectionResetError, ConnectionAbortedError) as e:
            self.socket = None
            self.connected_message = False
            print(e)
        except OSError:
            # We're already connected, just move on
            pass

    def sockSend(self, payload):
        #for byte in payload:
        #    logger.debug(byte.to_bytes().decode())

        status = self.sock.send(payload)
        print(status)

    def _sendack(self):
        payload = bytearray('+'.encode())
        self.sockSend(payload)

    def _recack(self):
        try:
            rec = self.sock.recv(1)
        except Exception as e:
            print(e)
        #if rec != '+':
        #    raise Exception("Nope!!!!!")

    def _read(self, addr: int, size: int):
        """
            Read length addressable memory units starting at address addr
            https://sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html#index-m-packet
        """

        status = self.sockSend(bytearray('$'.encode()))

        cmd = f'm{addr:08x},{size}'
        buf = bytearray(cmd, 'utf - 8')
        
        checksum = 0
        for byte in buf:
            checksum += int(byte)

        payload = bytearray(cmd.encode())
        status = self.sockSend(payload)

        payload = bytearray(f'#{checksum % 2**8:02x}', 'utf -8')
        status = self.sockSend(payload)
        self._recack()

        rec = self.sock.recv(1 + size*2 + 3)
        self._sendack()
        print(rec)

        #TODO check checksum
        return rec[1:-3]


    def _write(self, addr: int, size: int, data: bytearray):
        """
            Write length addressable memory units starting at address addr
            https://sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html#index-M-packet

            Args:
                addr (int): DDR address to write to
                size (int): # of bytes to write
        """

        cmd = f'M{addr:08x},{size}'
        buf = bytearray(cmd, 'utf - 8')
        
        checksum = 0
        for byte in buf:
            checksum += int(byte)
        
        payload = bytearray(cmd.encode())
        self.sockSend(payload)
        
        payload = bytearray(f'#{checksum % 2**8:02x}', 'utf -8')
        self.sockSend(payload)

        self._recack

        checksum = 0
        for byte in data:
            checksum += int(byte)

        payload = data
        self.sockSend(payload)

        payload = bytearray(f'#{checksum % 2**8:02x}', 'utf -8')
        self.sockSend(payload)

        print()
        self._recack()

        return True

    def read_u8(self, address):
        """Read an 8-bit unsigned integer from memory."""
        return int.from_bytes(self._read(addr=address, size=1))

    def read_u16(self, address):
        """Read a 16-bit unsigned integer from memory."""
        return int.from_bytes(self._read(addr=address, size=2))

    def read_u32(self, address):
        """Read a 32-bit unsigned integer from memory."""
        return int.from_bytes(self._read(addr=address, size=4))

    def read_dict(self, dict):
        logger.warn("READ_DICT NOT IMPLEMENTED")

    def read_bytestring(self, address, size):
        """Read a bytestring from memory."""
        ret = self._read(addr=address, size=size)
        print(type(ret))
        logger.info("Read bytestring: {ret:08x}")
        return ret

    def _write_memory(self, command, address, data):
        """Write data to memory and returns the emulator response."""
        logger.warn("write_memory NOT IMPLEMENTED")

    def write_u8(self, address, data: int):
        """Write an 8-bit unsigned integer to memory."""
        return self._write(addr=address, size=1, data=data.to_bytes(1))

    def write_u16(self, address, data: int):
        """Write a 16-bit unsigned integer to memory."""
        return self._write(addr=address, size=2, data=data.to_bytes(2))

    def write_u32(self, address, data: int):
        """Write a 32-bit unsigned integer to memory."""
        return self._write(addr=address, size=4, data=data.to_bytes(4))

    def write_bytestring(self, address, data):
        """Write a bytestring to memory."""
        return self._write(addr=address, size=size)

    def validate_rom(self, name, memory_location=None):
            # $m807ff1c,4#32
            return memory_location is None or self.read_u32(memory_location) != 0
        
