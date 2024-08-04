import time, framebuf

class TFT213(framebuf.FrameBuffer):
    """ 2.13inch, 250x120(actually 250x122, 2 bottom lines are unused)"""
    def __init__(self, spi, cs_pin, dc_pin, res_pin):
        self.spi = spi
        self.cs = cs_pin
        self.dc = dc_pin
        self.rs = res_pin
        # 250 * 15 bytes (each byte maps to 8 vertical pixels)
        self.bs = bytearray(250 * 15)
        super().__init__(self.bs, 250, 15 * 8, framebuf.MONO_VLSB)
        # 125 * 10 blocks (each block maps to 2 * 12 pixels)
        self.bt = bytearray(125 * 10 * 3)
        # cache
        self.cmd = bytearray(1)
        self.caset = bytearray([0x19, 0x19 + 10 - 1])
        self.raset = bytearray([0x00, 0x00 + 125 - 1])
        # start
        self._init()
    
    def _send(self, command, data = None):
        self.cmd[0] = command
        self.dc.value(0)  # Command mode
        self.cs.value(0)
        self.spi.write(self.cmd)
        self.cs.value(1)
        self.dc.value(1) # Data mode
        if data:
            self.cs.value(0)
            if isinstance(data, bytearray) or isinstance(data, memoryview):
                self.spi.write(data)
            else:
                self.spi.write(bytearray(data))
            self.cs.value(1)
    
    def _init(self):
        # reset
        time.sleep_ms(50)
        self.rs.value(0)
        time.sleep_ms(100)
        self.rs.value(1)
        
        # (command, data...)
        commands = [
            (0xeb, [0x02]), # Enable OTP
            (0xd7, [0x68]), # OTP Load Control
            #(0xD1, [0x01]), # Auto Power Control
            (0xC0, [0x80]), # Gate Voltage Setting VGH=12V ; VGL=-5V
            (0XC1, [0x28, 0x28, 0x28, 0x28, 0x14, 0x00]), # VSH Setting
            (0xC2, [0x00, 0x00, 0x00, 0x00]), # VSL Setting VSL=0
            (0xCB, [0x14]), # VCOMH Setting 14  0C   7
            #(0xB4, [0xE5, 0x77, 0xF1, 0xFF, 0xFF, 0x4F, 0xF1, 0xFF, 0xFF, 0x4F]), # Gate EQ Setting HPM EQ LPM EQ
            (0xb4, [0xa5, 0x66, 0x01, 0x00, 0x00, 0x40, 0x01, 0x00, 0x00, 0x40]), # Gate EQ Setting HPM EQ LPM EQ
            (0x11, []), # Sleep out
            100, # delay 100ms 
            #(0xC7, [0xA6, 0xE9]), # OSC Setting
            (0x36, [0x00]), # Memory Data Access Control
            (0x3a, [0x11]), # Data Format Select 4 write for 24 bit
            (0xb0, [0x64]), # Duty Setting: 250duty/4=63
            #(0xB9, [0x23]), # Source Setting
            (0xb8, [0x09]), # Panel Setting Frame inversion
            (0xB2, [0x01, 0x05]), # Frame Rate Control 32Hz(HPM)/8Hz(LPM)
            (0x39, []), # LPM
            (0x29, []), # Display on
            100, # delay 100ms
        ]
        
        for command in commands:
            if isinstance(command, tuple):
                self._send(command[0], command[1])
            else:
                time.sleep_ms(command)

        # clear 2 bottom lines
        self.fill(0)
        self._send(0x2A, [0x19 + 10, 0x19 + 10])
        self._send(0x2B, [0x00, 0x00 + 125 - 1])
        self._send(0x2C, memoryview(self.bs)[0:125 * 3])
    
    @micropython.viper
    def _convert(self):
        s = ptr8(self.bs)
        t = ptr8(self.bt)
        k = 0
        for i in range(0, 250, 2):
            # convert 2 columns
            for j in range(0, 15, 3):
                for y in range(0, 3):
                    b1 = s[(j + y) * 250 + i + 0]
                    b2 = s[(j + y) * 250 + i + 1]
                    mix = 0x00
                    mix=mix|((b1&0x01)<<7)
                    mix=mix|((b2&0x01)<<6)
                    mix=mix|((b1&0x02)<<4)
                    mix=mix|((b2&0x02)<<3)
                    mix=mix|((b1&0x04)<<1)
                    mix=mix|((b2&0x04)<<0)
                    mix=mix|((b1&0x08)>>2)
                    mix=mix|((b2&0x08)>>3)
                    t[k] = mix
                    k += 1
                    
                    b1 = b1 >> 4
                    b2 = b2 >> 4
                    mix = 0x00
                    mix=mix|((b1&0x01)<<7)
                    mix=mix|((b2&0x01)<<6)
                    mix=mix|((b1&0x02)<<4)
                    mix=mix|((b2&0x02)<<3)
                    mix=mix|((b1&0x04)<<1)
                    mix=mix|((b2&0x04)<<0)
                    mix=mix|((b1&0x08)>>2)
                    mix=mix|((b2&0x08)>>3)
                    t[k] = mix
                    k += 1
    
    def refresh(self):
        self._convert()
        self._send(0x2A, self.caset)
        self._send(0x2B, self.raset)
        self._send(0x2C, self.bt)
