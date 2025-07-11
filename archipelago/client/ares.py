import socket
import logging
import os
from time import sleep
from Utils import open_filename

logger = logging.getLogger(__name__)

# https://sourceware.org/gdb/current/onlinedocs/gdb.html/Overview.html#Overview

# Per discussion at https://github.com/NationalSecurityAgency/ghidra/discussions/6787 ares >=142 required

class AresClient:
    lead = '$'

    def __init__(self):
        """Initialize a new instance of the class."""
        self.address = "127.0.0.1"
        self.port = 9124
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
        os.popen(f'/home/jason/projects/ares/build/rundir/bin/ares "{rom}"')
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
        logger.info(f'Sent {payload}')
        return status

    def sockRecv(self, length):
        ret = self.sock.recv(length)
        logger.info(f'Received {ret}')
        return ret

    def _sendack(self):
        payload = bytearray('+'.encode())
        self.sockSend(payload)

    def _recack(self):
        try:
            rec = self.sockRecv(1)
        except Exception as e:
            print(e)
        #if rec != '+':
        #    raise Exception("Nope!!!!!")

    def _cmdstart(self):
        status = self.sockSend(bytearray('$'.encode()))

    def _getchecksum(self, buf: bytearray):
        checksum = 0
        for byte in buf:
            checksum += int(byte)
        
        return checksum % 2**8

    def _readWord(self, addr: int):
        self._cmdstart()
        cmd = f'm{addr:08x},4'
        payload = bytearray(cmd, 'utf-8')
        checksum = self._getchecksum(payload)

        self.sockSend(payload)
        payload = bytearray(f'#{checksum:02x}', 'utf-8')
        self.sockSend(payload)
        self._recack()

        rec = self.sockRecv(12)
        self._sendack()

        return rec[1:-3]

    def _read(self, addr: int, size: int):
        """
            Read length addressable memory units starting at address addr
            https://sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html#index-m-packet
        """

        # Memory reads MUST be word aligned
        if size not in (1, 2, 4, 8):
            rec_buf = bytearray()

            offset = 0
            while offset < size:
                rec = self._readWord(addr + offset)
                bytearr = bytearray(rec)

                # Toss unneeded bytes
                if offset + 4 > size:
                    unused = size - (offset + 4)
                    if unused > 0:
                        bytearr = bytearr[:-unused]

                rec_buf += bytearr
                offset += 4

            ret = rec_buf
            print(f'Final receive: {ret}')
                
        # Bulk read
        else:
            self._cmdstart()       

            cmd = f'm{addr:08x},{size}'
            payload = bytearray(cmd.encode())
            checksum = self._getchecksum(payload)

            status = self.sockSend(payload)

            payload = bytearray(f'#{checksum:02x}', 'utf-8')
            status = self.sockSend(payload)
            self._recack()

            rec = self.sockRecv(1 + size*2 + 3)
            self._sendack()

            ret = rec[1:-3]

        return ret


    def _write(self, addr: int, size: int, data: bytearray):
        """
            Write length addressable memory units starting at address addr
            https://sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html#index-M-packet

            Args:
                addr (int): DDR address to write to
                size (int): # of bytes to write
        """

        logger.info(f'Attempting to write {bytes(data)} to {addr:016x}')
        self._cmdstart()

        cmd = f'M{addr:08x},{size}'
        payload = bytearray(cmd, 'utf-8')
        self.sockSend(payload)
        
        checksum = 0
        for byte in payload:
            checksum += int(byte)
        
        payload = bytearray(f'#{checksum % 2**8:02x}', 'utf-8')
        self.sockSend(payload)

        self._recack

        checksum = 0
        for byte in data:
            checksum += int(byte)

        payload = data
        self.sockSend(payload)

        payload = bytearray(f'#{checksum % 2**8:02x}', 'utf-8')
        self.sockSend(payload)
        self._recack()

        #TODO I think the ares gdb server goes crazy when you write
        # $OK#9a
        ok = self.sockRecv(6)
        self._sendack()

        # $#00
        self._recack()
        idk = self.sockRecv(4)
        self._sendack()
        self._sendack()
        self._sendack()

        return True

    def read_u8(self, address):
        """Read an 8-bit unsigned integer from memory."""
        return int(self._read(addr=address, size=1), 16)

    def read_u16(self, address):
        """Read a 16-bit unsigned integer from memory."""
        return int(self._read(addr=address, size=2), 16)

    def read_u32(self, address):
        """Read a 32-bit unsigned integer from memory."""
        return int(self._read(addr=address, size=4), 16)

    def read_dict(self, dict):
        print("AAAAAAAHHHHHHHHHHHH")
        logger.warn("READ_DICT NOT IMPLEMENTED")

    def read_bytestring(self, address, size):
        """Read a bytestring from memory."""
        bytearr = bytes(self._read(addr=address, size=size))

        # Disgusting!
        bytestr = bytes.fromhex(bytearr.decode('utf-8')).decode('latin1')
        return bytestr

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
        
