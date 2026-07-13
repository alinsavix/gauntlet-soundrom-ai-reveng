#!/usr/bin/env python3
"""Small NMOS 6502 executor used for branch-qualified ROM cycle traces.

This is intentionally an analysis helper, not a hardware/device emulator.  It
implements the documented NMOS opcodes used by the selected sound-ROM paths,
including indexed-read and taken-branch page penalties.  Unsupported opcodes
fail closed with their PC so a trace cannot silently skip unknown behavior.
"""


class CPU6502:
    C, Z, I, D, B, U, V, N = (1, 2, 4, 8, 16, 32, 64, 128)

    READ = {
        # LDA
        0xA9: ("lda", "imm", 2, 0), 0xA5: ("lda", "zp", 3, 0),
        0xB5: ("lda", "zpx", 4, 0), 0xAD: ("lda", "abs", 4, 0),
        0xBD: ("lda", "absx", 4, 1), 0xB9: ("lda", "absy", 4, 1),
        0xA1: ("lda", "indx", 6, 0), 0xB1: ("lda", "indy", 5, 1),
        # LDX / LDY
        0xA2: ("ldx", "imm", 2, 0), 0xA6: ("ldx", "zp", 3, 0),
        0xB6: ("ldx", "zpy", 4, 0), 0xAE: ("ldx", "abs", 4, 0),
        0xBE: ("ldx", "absy", 4, 1),
        0xA0: ("ldy", "imm", 2, 0), 0xA4: ("ldy", "zp", 3, 0),
        0xB4: ("ldy", "zpx", 4, 0), 0xAC: ("ldy", "abs", 4, 0),
        0xBC: ("ldy", "absx", 4, 1),
        # ALU
        0x69: ("adc", "imm", 2, 0), 0x65: ("adc", "zp", 3, 0),
        0x75: ("adc", "zpx", 4, 0), 0x6D: ("adc", "abs", 4, 0),
        0x7D: ("adc", "absx", 4, 1), 0x79: ("adc", "absy", 4, 1),
        0x61: ("adc", "indx", 6, 0), 0x71: ("adc", "indy", 5, 1),
        0xE9: ("sbc", "imm", 2, 0), 0xE5: ("sbc", "zp", 3, 0),
        0xF5: ("sbc", "zpx", 4, 0), 0xED: ("sbc", "abs", 4, 0),
        0xFD: ("sbc", "absx", 4, 1), 0xF9: ("sbc", "absy", 4, 1),
        0xE1: ("sbc", "indx", 6, 0), 0xF1: ("sbc", "indy", 5, 1),
        0x29: ("and", "imm", 2, 0), 0x25: ("and", "zp", 3, 0),
        0x35: ("and", "zpx", 4, 0), 0x2D: ("and", "abs", 4, 0),
        0x3D: ("and", "absx", 4, 1), 0x39: ("and", "absy", 4, 1),
        0x21: ("and", "indx", 6, 0), 0x31: ("and", "indy", 5, 1),
        0x09: ("ora", "imm", 2, 0), 0x05: ("ora", "zp", 3, 0),
        0x15: ("ora", "zpx", 4, 0), 0x0D: ("ora", "abs", 4, 0),
        0x1D: ("ora", "absx", 4, 1), 0x19: ("ora", "absy", 4, 1),
        0x01: ("ora", "indx", 6, 0), 0x11: ("ora", "indy", 5, 1),
        0x49: ("eor", "imm", 2, 0), 0x45: ("eor", "zp", 3, 0),
        0x55: ("eor", "zpx", 4, 0), 0x4D: ("eor", "abs", 4, 0),
        0x5D: ("eor", "absx", 4, 1), 0x59: ("eor", "absy", 4, 1),
        0x41: ("eor", "indx", 6, 0), 0x51: ("eor", "indy", 5, 1),
        # compares
        0xC9: ("cmp", "imm", 2, 0), 0xC5: ("cmp", "zp", 3, 0),
        0xD5: ("cmp", "zpx", 4, 0), 0xCD: ("cmp", "abs", 4, 0),
        0xDD: ("cmp", "absx", 4, 1), 0xD9: ("cmp", "absy", 4, 1),
        0xC1: ("cmp", "indx", 6, 0), 0xD1: ("cmp", "indy", 5, 1),
        0xE0: ("cpx", "imm", 2, 0), 0xE4: ("cpx", "zp", 3, 0),
        0xEC: ("cpx", "abs", 4, 0),
        0xC0: ("cpy", "imm", 2, 0), 0xC4: ("cpy", "zp", 3, 0),
        0xCC: ("cpy", "abs", 4, 0),
    }

    STORE = {
        0x85: ("a", "zp", 3), 0x95: ("a", "zpx", 4),
        0x8D: ("a", "abs", 4), 0x9D: ("a", "absx", 5),
        0x99: ("a", "absy", 5), 0x81: ("a", "indx", 6),
        0x91: ("a", "indy", 6),
        0x86: ("x", "zp", 3), 0x96: ("x", "zpy", 4),
        0x8E: ("x", "abs", 4),
        0x84: ("y", "zp", 3), 0x94: ("y", "zpx", 4),
        0x8C: ("y", "abs", 4),
    }

    RMW = {
        0x0A: ("asl", "acc", 2), 0x06: ("asl", "zp", 5),
        0x16: ("asl", "zpx", 6), 0x0E: ("asl", "abs", 6),
        0x1E: ("asl", "absx", 7),
        0x4A: ("lsr", "acc", 2), 0x46: ("lsr", "zp", 5),
        0x56: ("lsr", "zpx", 6), 0x4E: ("lsr", "abs", 6),
        0x5E: ("lsr", "absx", 7),
        0x2A: ("rol", "acc", 2), 0x26: ("rol", "zp", 5),
        0x36: ("rol", "zpx", 6), 0x2E: ("rol", "abs", 6),
        0x3E: ("rol", "absx", 7),
        0x6A: ("ror", "acc", 2), 0x66: ("ror", "zp", 5),
        0x76: ("ror", "zpx", 6), 0x6E: ("ror", "abs", 6),
        0x7E: ("ror", "absx", 7),
        0xE6: ("inc", "zp", 5), 0xF6: ("inc", "zpx", 6),
        0xEE: ("inc", "abs", 6), 0xFE: ("inc", "absx", 7),
        0xC6: ("dec", "zp", 5), 0xD6: ("dec", "zpx", 6),
        0xCE: ("dec", "abs", 6), 0xDE: ("dec", "absx", 7),
    }

    BRANCH = {
        0x10: lambda p: not (p & 0x80), 0x30: lambda p: bool(p & 0x80),
        0x50: lambda p: not (p & 0x40), 0x70: lambda p: bool(p & 0x40),
        0x90: lambda p: not (p & 0x01), 0xB0: lambda p: bool(p & 0x01),
        0xD0: lambda p: not (p & 0x02), 0xF0: lambda p: bool(p & 0x02),
    }

    def __init__(self, rom, rom_base=0x4000):
        self.mem = bytearray(0x10000)
        self.mem[rom_base:rom_base + len(rom)] = rom
        self.a = self.x = self.y = 0
        self.sp = 0xFF
        self.p = self.U
        self.pc = rom_base
        self.cycles = 0
        self.instructions = 0
        self.trace = []

    def _set_nz(self, value):
        value &= 0xFF
        self.p = (self.p & ~(self.N | self.Z)) | (self.N if value & 0x80 else 0) | (self.Z if value == 0 else 0)
        return value

    def _flag(self, flag, state):
        self.p = self.p | flag if state else self.p & ~flag

    def _byte(self):
        value = self.mem[self.pc]
        self.pc = (self.pc + 1) & 0xFFFF
        return value

    def _word(self):
        lo = self._byte()
        return lo | (self._byte() << 8)

    def _zp_word(self, address):
        return self.mem[address & 0xFF] | (self.mem[(address + 1) & 0xFF] << 8)

    def _address(self, mode):
        crossed = False
        if mode == "zp":
            return self._byte(), crossed
        if mode == "zpx":
            return (self._byte() + self.x) & 0xFF, crossed
        if mode == "zpy":
            return (self._byte() + self.y) & 0xFF, crossed
        if mode == "abs":
            return self._word(), crossed
        if mode in ("absx", "absy"):
            base = self._word()
            value = self.x if mode == "absx" else self.y
            address = (base + value) & 0xFFFF
            return address, (base & 0xFF00) != (address & 0xFF00)
        if mode == "indx":
            return self._zp_word((self._byte() + self.x) & 0xFF), crossed
        if mode == "indy":
            base = self._zp_word(self._byte())
            address = (base + self.y) & 0xFFFF
            return address, (base & 0xFF00) != (address & 0xFF00)
        raise ValueError(mode)

    def _read(self, mode):
        if mode == "imm":
            return self._byte(), False
        address, crossed = self._address(mode)
        return self.mem[address], crossed

    def _push(self, value):
        self.mem[0x100 | self.sp] = value & 0xFF
        self.sp = (self.sp - 1) & 0xFF

    def _pop(self):
        self.sp = (self.sp + 1) & 0xFF
        return self.mem[0x100 | self.sp]

    def _compare(self, register, value):
        result = (register - value) & 0x1FF
        self._flag(self.C, register >= value)
        self._set_nz(result)

    def _adc(self, value):
        carry = 1 if self.p & self.C else 0
        total = self.a + value + carry
        result = total & 0xFF
        self._flag(self.C, total > 0xFF)
        self._flag(self.V, bool((~(self.a ^ value) & (self.a ^ result) & 0x80)))
        self.a = self._set_nz(result)

    def _rmw(self, operation, value):
        old_carry = 1 if self.p & self.C else 0
        if operation == "asl":
            self._flag(self.C, value & 0x80)
            return self._set_nz(value << 1)
        if operation == "lsr":
            self._flag(self.C, value & 1)
            return self._set_nz(value >> 1)
        if operation == "rol":
            self._flag(self.C, value & 0x80)
            return self._set_nz((value << 1) | old_carry)
        if operation == "ror":
            self._flag(self.C, value & 1)
            return self._set_nz((value >> 1) | (old_carry << 7))
        if operation == "inc":
            return self._set_nz(value + 1)
        if operation == "dec":
            return self._set_nz(value - 1)
        raise ValueError(operation)

    def step(self):
        start = self.pc
        opcode = self._byte()
        cycles = 0
        if opcode in self.READ:
            operation, mode, cycles, page_penalty = self.READ[opcode]
            value, crossed = self._read(mode)
            cycles += page_penalty if crossed else 0
            if operation == "lda": self.a = self._set_nz(value)
            elif operation == "ldx": self.x = self._set_nz(value)
            elif operation == "ldy": self.y = self._set_nz(value)
            elif operation == "adc": self._adc(value)
            elif operation == "sbc": self._adc(value ^ 0xFF)
            elif operation == "and": self.a = self._set_nz(self.a & value)
            elif operation == "ora": self.a = self._set_nz(self.a | value)
            elif operation == "eor": self.a = self._set_nz(self.a ^ value)
            elif operation == "cmp": self._compare(self.a, value)
            elif operation == "cpx": self._compare(self.x, value)
            elif operation == "cpy": self._compare(self.y, value)
        elif opcode in self.STORE:
            register, mode, cycles = self.STORE[opcode]
            address, _ = self._address(mode)
            self.mem[address] = getattr(self, register)
        elif opcode in self.RMW:
            operation, mode, cycles = self.RMW[opcode]
            if mode == "acc":
                self.a = self._rmw(operation, self.a)
            else:
                address, _ = self._address(mode)
                self.mem[address] = self._rmw(operation, self.mem[address])
        elif opcode in self.BRANCH:
            offset = self._byte()
            cycles = 2
            if self.BRANCH[opcode](self.p):
                old = self.pc
                self.pc = (self.pc + (offset - 256 if offset & 0x80 else offset)) & 0xFFFF
                cycles += 1 + ((old & 0xFF00) != (self.pc & 0xFF00))
        elif opcode == 0x20:  # JSR
            target = self._word(); return_address = (self.pc - 1) & 0xFFFF
            self._push(return_address >> 8); self._push(return_address); self.pc = target; cycles = 6
        elif opcode == 0x60:  # RTS
            self.pc = ((self._pop() | (self._pop() << 8)) + 1) & 0xFFFF; cycles = 6
        elif opcode == 0x4C: self.pc = self._word(); cycles = 3
        elif opcode == 0x6C:
            pointer = self._word(); lo = self.mem[pointer]
            hi = self.mem[(pointer & 0xFF00) | ((pointer + 1) & 0xFF)]
            self.pc = lo | (hi << 8); cycles = 5
        elif opcode == 0x24:
            value = self.mem[self._byte()]; self._flag(self.Z, not (self.a & value)); self._flag(self.N, value & 0x80); self._flag(self.V, value & 0x40); cycles = 3
        elif opcode == 0x2C:
            value = self.mem[self._word()]; self._flag(self.Z, not (self.a & value)); self._flag(self.N, value & 0x80); self._flag(self.V, value & 0x40); cycles = 4
        elif opcode == 0x48: self._push(self.a); cycles = 3
        elif opcode == 0x68: self.a = self._set_nz(self._pop()); cycles = 4
        elif opcode == 0x08: self._push(self.p | self.B | self.U); cycles = 3
        elif opcode == 0x28: self.p = (self._pop() | self.U) & ~self.B; cycles = 4
        elif opcode == 0xAA: self.x = self._set_nz(self.a); cycles = 2
        elif opcode == 0x8A: self.a = self._set_nz(self.x); cycles = 2
        elif opcode == 0xA8: self.y = self._set_nz(self.a); cycles = 2
        elif opcode == 0x98: self.a = self._set_nz(self.y); cycles = 2
        elif opcode == 0xBA: self.x = self._set_nz(self.sp); cycles = 2
        elif opcode == 0x9A: self.sp = self.x; cycles = 2
        elif opcode == 0xE8: self.x = self._set_nz(self.x + 1); cycles = 2
        elif opcode == 0xCA: self.x = self._set_nz(self.x - 1); cycles = 2
        elif opcode == 0xC8: self.y = self._set_nz(self.y + 1); cycles = 2
        elif opcode == 0x88: self.y = self._set_nz(self.y - 1); cycles = 2
        elif opcode == 0x18: self.p &= ~self.C; cycles = 2
        elif opcode == 0x38: self.p |= self.C; cycles = 2
        elif opcode == 0x58: self.p &= ~self.I; cycles = 2
        elif opcode == 0x78: self.p |= self.I; cycles = 2
        elif opcode == 0xB8: self.p &= ~self.V; cycles = 2
        elif opcode == 0xD8: self.p &= ~self.D; cycles = 2
        elif opcode == 0xF8: self.p |= self.D; cycles = 2
        elif opcode == 0xEA: cycles = 2
        else:
            raise RuntimeError(f"unsupported opcode ${opcode:02X} at ${start:04X}")
        self.cycles += cycles
        self.instructions += 1
        self.trace.append((start, opcode, cycles))
        return cycles

    def run(self, start, stop_rts=None, max_instructions=10000):
        self.pc = start
        while self.instructions < max_instructions:
            if stop_rts is not None and self.pc == stop_rts and self.mem[self.pc] == 0x60:
                self.cycles += 6
                self.instructions += 1
                self.trace.append((self.pc, 0x60, 6))
                return self.cycles
            self.step()
        raise RuntimeError(f"execution limit at ${self.pc:04X}")
