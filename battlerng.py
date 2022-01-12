from typing import List
from lcg import *

BATTLE_RNG_TABLE = [99, 6, 240, 35, 248, 229, 168, 1, 193, 174, 127, 72, 123, 177, 220, 9, 34, 109, 125, 238, 157, 88,
                    213, 85, 36, 57, 122, 223, 142, 84, 108, 27, 192, 11, 208, 67, 216, 154, 71, 93, 33, 2, 23, 75, 219,
                    17, 175, 112, 205, 77, 52, 73, 114, 145, 45, 98, 151, 89, 69, 247, 110, 70, 170, 10, 163, 200, 49,
                    146, 56, 250, 212, 230, 203, 243, 222, 107, 187, 241, 28, 60, 214, 173, 178, 169, 221, 87, 66, 149,
                    12, 121, 37, 31, 188, 231, 172, 91, 131, 40, 118, 242, 24, 218, 135, 161, 97, 111, 190, 90, 94, 81,
                    239, 176, 201, 21, 116, 137, 189, 209, 162, 117, 215, 153, 133, 76, 79, 210, 191, 74, 32, 8, 86,
                    160, 80, 58, 103, 38, 65, 51, 183, 186, 251, 48, 207, 124, 132, 44, 50, 233, 29, 22, 130, 120, 164,
                    128, 101, 95, 14, 39, 185, 25, 195, 167, 182, 0, 59, 252, 136, 225, 198, 147, 254, 139, 217, 184,
                    19, 105, 47, 100, 18, 55, 253, 119, 226, 181, 4, 224, 26, 140, 143, 180, 204, 249, 96, 235, 41, 227,
                    144, 165, 104, 61, 129, 115, 63, 171, 126, 179, 15, 206, 196, 53, 148, 150, 134, 113, 211, 42, 228,
                    159, 156, 236, 78, 20, 245, 234, 64, 166, 246, 3, 152, 197, 7, 244, 43, 194, 62, 232, 155, 54, 83,
                    46, 141, 13, 82, 16, 102, 30, 237, 138, 68, 158, 5, 255, 92, 199, 106, 202]


class BattleRNG:

    def _seed_rng(self, seed: int):
        i = 0
        while i < 8:
            self.arr[i] = seed & 0xFF
            seed >>= 1
            i += 1
        self.idx = 0

    def __init__(self, seed: int, joker: int):
        self.arr = [0 for _ in range(8)]
        self.idx = 0
        self.joker = joker
        self._seed_rng(seed)

    def __repr__(self):
        return f"{self.idx} {self.joker} | {self.arr}"

    def incr_rng_idx(self):
        self.idx = (self.idx + 1) & 7

    def rand8(self):
        x = BATTLE_RNG_TABLE[self.arr[self.idx]]
        self.arr[self.idx] = (self.arr[self.idx] + 1) % 256
        return x

    def rand8_multiply(self, param):
        return (self.rand8() * param) >> 8

    def rand8_levelup(self, param1):
        r = param1 + 1 + (self.rand8() & 7)
        if r < 0:
            r = 0
        elif 0xb < r:
            r = 0xb
        return r

    def rand16(self):
        rand1 = self.rand8()
        j = self.joker & 7
        self.joker += 1
        if j != 0:
            self.incr_rng_idx()
        rand2 = self.rand8()
        return rand2 << 8 | rand1

    def rand16_percent(self):
        return ((self.rand16() * 99) // 0xFFFF) + 1


def init_ATB(brng: BattleRNG, slot_filled_flags: List[int]):
    out = []
    for slot in slot_filled_flags:
        if slot:
            out.append(brng.rand16() >> 1)
        else:
            out.append(None)
    max_atb = max([x for x in out if x is not None])
    for i in range(len(out)):
        if out[i] is not None:
            out[i] += (0xE000 - max_atb)
    return out


class Fail(Exception):
    pass


class Success(Exception):
    pass
