import time, framebuf

FRAMERATE_1 = (0x39, 0x02) # (best quality) 0x39-LPM 0x02-HPM_16Hz_LPM_1Hz
FRAMERATE_8 = (0x39, 0x05) # (best quality) 0x39-LPM 0x05-HPM_16Hz_LPM_8Hz
FRAMERATE_16 = (0x38, 0x05) # (best quality) 0x38-HPM 0x05-HPM_16Hz_LPM_8Hz
FRAMERATE_32 = (0x38, 0x15) # (lower quality) 0x38-HPM 0x05-HPM_32Hz_LPM_8Hz

class TFT29(framebuf.FrameBuffer):
    """ 2.9inch, 384x168 framebuf """
    def __init__(self, spi, cs_pin, dc_pin, res_pin, te_pin = None, framerate = FRAMERATE_8):
        self.spi = spi
        self.cs = cs_pin
        self.dc = dc_pin
        self.rs = res_pin
        # 384 * 21 bytes (each byte maps to 8 vertical pixels)
        self.bs = bytearray(384 * 21)
        super().__init__(self.bs, 384, 21 * 8, framebuf.MONO_VLSB)
        # 192 * 14 blocks (each block maps to 2 * 12 pixels)
        self.bt = bytearray(192 * 14 * 3)
        # cache
        self.cmd = bytearray(1)
        self.caset = bytearray([0x17, 0x17 + 14 - 1])
        self.raset = bytearray([0x00, 0x00 + 192 - 1])
        # start
        self._init(framerate)
    
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
    
    def _init(self, framerate):
        # reset
        time.sleep_ms(50)
        self.rs.value(0)
        time.sleep_ms(100)
        self.rs.value(1)
        
        # (command, data...)
        commands = [
            (0xD6, [0x13, 0x02]), # NVM Load Control (0x17 0xXX Enable VS/ID, 0x13 0xXX Enable ID)
            (0xD1, [0x01]), # Booster Enable 
            (0xC0, [0x08, 0x06]), # Gate Voltage Setting VGH 00:8V  04:10V  08:12V   0E:15V ; VGL 00:-5V   04:-7V   0A:-10V 
            (0XC1, [0x3C, 0x3E, 0x3C, 0x3C]), # VSHP Setting (4.8V)
            (0xC2, [0x23, 0x21, 0x23, 0x23]), # VSLP Setting (0.98V)
            (0xC4, [0x5A, 0x5C, 0x5A, 0x5A]), # VSHN Setting (-3.6V)
            (0xC5, [0X37, 0X35, 0X37, 0X37]), # VSLN Setting (0.22V)
            (0xB2, [framerate[1]]), # Frame Rate Control
            (0xB3, [0xE5, 0xF6, 0x17, 0x77, 0x77, 0x77, 0x77, 0x77, 0x77, 0x71]), # Update Period Gate EQ Control in HPM
            (0xB4, [0x05, 0x46, 0x77, 0x77, 0x77, 0x77, 0x76, 0x45]), # Update Period Gate EQ Control in LPM
            (0x62, [0x32, 0x03, 0x1F]), # Gate Timing Control
            (0xB7, [0x13]), # Source EQ Enable
            (0xB0, [0x60]), # Gate Line Setting: 384 line
            
            (0x11, []), # Sleep out
            100, # delay 100ms
            (0xC9, [0x00]), # Source Voltage Select: VSHP1; VSLP1 ; VSHN1 ; VSLN1
            (0x36, [0x00]), # Memory Data Access Control: MX=0 ; DO=0 
            (0x3A, [0x11]), # Data Format Select: 10:4write for 24bit ; 11: 3write for 24bit
            (0xB9, [0x20]), # Gamma Mode Setting: 20: Mono; 00:4GS
            (0xB8, [0x29]), # Panel Setting: 0x29: 1-Dot inversion, Frame inversion, One Line Interlace
            (0x2A, [0x17, 0x24]), # Column Address Setting
            (0x2B, [0x00, 0xBF]), # Row Address Setting
            (0x35, [0x00]), # TE
            (0xD0, [0xFF]), # Auto power down
            (framerate[0], []), # 0x38 HPM; 0x39 LPM
            (0x29, []), # Display on
            100, # delay 100ms
        ]
        
        for command in commands:
            if isinstance(command, tuple):
                self._send(command[0], command[1])
            else:
                time.sleep_ms(command)
    
    @micropython.viper
    def _convert(self):
        s = ptr8(self.bs)
        t = ptr8(self.bt)
        k = 0
        for i in range(0, 384, 2):
            # convert 2 columns
            for j in range(0, 21, 3):
                for y in range(0, 3):
                    b1 = s[(j + y) * 384 + i + 0]
                    b2 = s[(j + y) * 384 + i + 1]
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
