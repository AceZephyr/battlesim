from battlerng import *

MENU_FRAMES = 3
STAT_ROLL_ARR = [0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3]
HP_ROLL_ARR = [40, 50, 50, 60, 70, 80, 90, 100, 110, 120, 130, 150]
MP_ROLL_ARR = [20, 30, 30, 50, 70, 80, 90, 100, 110, 120, 140, 160]


class Simulator:
    def __init__(self, seed, joker):
        self.initial_seed = seed
        self.data = {}
        self.brng = BattleRNG(seed=seed, joker=joker)
        self.char_states = []
        self.queue = []
        self.player_queue = []
        self.frame_count = 0
        self.opening_frames_remain = 62
        self.battle_escape_random = None
        self.victory = False
        self.victory_fanfare = False

        self.atbs = [0 for _ in range(10)]
        self.initial_atbs = None
        self.atb_speeds = [
            0x0222,
            0x01E7,
            0x01E7,
            0x01E7,
            0x01E7,
            0x01E7,
            0x0000,
            0x0000,
            0x0000
        ]

        self.menu_frames = 0

        self.current_animation_frames = 0

        self.battle_handlers = {
            0: self.cloud_battle_handler,
            4: self.mp_battle_handler,
            5: self.mp_battle_handler
        }

    def post_battle_victory(self):
        dropChance4 = self.brng.rand8()
        dropChance5 = self.brng.rand8()

        levelupStr = self.brng.rand8_levelup(1)
        levelupVit = self.brng.rand8_levelup(1)
        levelupMag = self.brng.rand8_levelup(2)
        levelupSpr = self.brng.rand8_levelup(1)
        levelupDex = self.brng.rand8_levelup(5)
        levelupLck = self.brng.rand8_levelup(2)
        levelupHP = self.brng.rand8_levelup(0x13A)
        levelupMP = self.brng.rand8_levelup(0x36)

        if STAT_ROLL_ARR[levelupMag] < 3:
            raise Fail

        if STAT_ROLL_ARR[levelupStr] < 2:
            raise Fail

        self.data["dex_increase"] = STAT_ROLL_ARR[levelupDex]

        raise Success

    def add_to_battle_queue(self, char: int):
        self.queue.append(char)

    def pop_from_battle_queue(self):
        return self.queue.pop(0)

    def clean_queue(self):
        for i in range(10):
            if not self.char_states[i] and i in self.queue:
                self.queue.remove(i)

    def remove_from_battle(self, char: int):
        self.char_states[char] = 0
        if not any(self.char_states[4:]):
            self.victory = True

    def cloud_battle_handler(self):
        self.brng.incr_rng_idx()
        rand1 = self.brng.rand8()  # 5c80d7
        hitPercent = 0x62
        rand2 = self.brng.rand8_multiply(100)  # 5ddda8 (Hit Check)
        if rand2 < 3:
            hitPercent = 0xFF

        rand3 = self.brng.rand16_percent()  # 5dde29 (Hit Random %)
        if not (rand3 < hitPercent):
            # miss
            # print(
            #     f"Miss: {self.initial_seed} state: {hex(prev_state(self.initial_seed << 0x10))} joker: {self.brng.joker}")
            raise Fail

        rand4 = self.brng.rand16()  # 5de05c (Crit Check)
        rand5 = self.brng.rand8()  # 5de80e (Damage Roll)

        self.remove_from_battle(self.data["cloud_targets"].pop(0))

        self.current_animation_frames = 36

    def mp_battle_handler(self):
        rand1 = self.brng.rand16()  # 5d874e (AI: Choose Attack)
        chosen_attack = rand1 & 1
        rand2 = self.brng.rand8()  # 5d19a4 (AI: Choose Target)
        self.brng.incr_rng_idx()
        rand3 = self.brng.rand8()  # 5c80d7
        rand4 = self.brng.rand8_multiply(100)  # 5ddda8 (Hit Check)
        rand5 = self.brng.rand16_percent()  # 5dde29 (Hit Random %)
        rand6 = self.brng.rand16()  # 5de05c (Crit Check)
        rand7 = self.brng.rand8()  # 5de80e (Damage Roll)

        if chosen_attack == 0:
            # gun
            hitPercent = 0x6F
            self.data["MP attack"] = "gun"
            self.current_animation_frames = 37
            self.data["sysrng_calls"] = self.data.get("sysrng_calls", 0) + 50
        else:
            # hit
            hitPercent = 0x60
            self.data["MP attack"] = "hit"
            self.current_animation_frames = 34
            self.clean_queue()

    def add_player_to_player_queue(self, charSlot):
        if len(self.player_queue) == 0:
            self.menu_frames = MENU_FRAMES
        self.player_queue.append(charSlot)

    def tick(self):
        for charSlot in range(10):
            if self.atbs[charSlot] is None:
                continue
            if self.atbs[charSlot] != 0xFFFF:
                increaseATB = self.atb_speeds[charSlot]
                targetATB = min(self.atbs[charSlot] + increaseATB, 0xFFFF)
                self.atbs[charSlot] = targetATB
                if targetATB == 0xFFFF:
                    if charSlot < 3:  # player
                        self.add_player_to_player_queue(charSlot)
                    else:
                        self.add_to_battle_queue(charSlot)

    def frame(self):
        self.frame_count += 1

        self.battle_escape_random = self.brng.rand16()

        if self.opening_frames_remain > 0:
            self.opening_frames_remain -= 1
        else:
            if self.current_animation_frames > 0:
                self.current_animation_frames -= 1
            elif self.victory_fanfare:
                self.post_battle_victory()
            elif self.victory:
                self.data["jokers"].append(self.brng.joker)
                self.victory_fanfare = True
                self.current_animation_frames = 67
            elif len(self.queue) > 0:
                char = self.pop_from_battle_queue()
                self.atbs[char] = 0
                if self.char_states[char]:
                    self.data["jokers"].append(self.brng.joker)
                    self.battle_handlers[char]()
            if len(self.player_queue) > 0:
                if self.menu_frames > 0:
                    self.menu_frames -= 1
                else:
                    player = self.player_queue.pop(0)
                    self.add_to_battle_queue(player)
            for i in range(4):
                self.tick()

    def run(self):
        try:
            self.char_states = [1, 0, 0, 0, 1, 1, 0, 0, 0, 0]
            self.atbs = init_ATB(self.brng, self.char_states)
            self.initial_atbs = self.atbs[:]
            self.data["cloud_targets"] = [4, 5]
            self.data["jokers"] = []
            if self.atbs[0] != 0xE000:
                raise Fail()
            if self.atbs[4] >= 0xCABB or self.atbs[5] >= 0xCABB:
                raise Fail()
            while True:
                self.frame()
        except Fail:
            return False
        except Success:
            return True


seed = 0x0
count = 0
while seed < 32768:
    sim = Simulator(seed, 0)
    ret = sim.run()
    if ret:
        count += 1
        print(
            f"{hex(seed)[2:].zfill(4)} {sim.data['MP attack'][0]} {sim.data['dex_increase']} {sim.brng.joker} {hex(prev_state(seed << 0x10))[2:].zfill(8)}")
        # print(hex(seed), sim.data['MP attack'], sim.brng, hex(sim.initial_atbs[4]), hex(sim.initial_atbs[5]), "|",
        #       hex(prev_state(seed << 0x10))[2:])
    seed += 1

print(f"count: {count}")