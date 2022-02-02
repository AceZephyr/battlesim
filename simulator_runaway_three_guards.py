from battlerng import *

DEX_7 = [0x22B, 0x218, 0x1E7, 0, 0x235, 0x235, 0x235, 0, 0, 0]
DEX_8 = [0x22B, 0x218, 0x1E7, 0, 0x22B, 0x22B, 0x22B, 0, 0, 0]
DEX_9 = [0x235, 0x20E, 0x1DE, 0, 0x22B, 0x22B, 0x22B, 0, 0, 0]


class Simulator:
    def __init__(self, seed, joker, atb_speeds, runaway_increment):
        self.initial_seed = seed
        # self.initial_attack_order = attack_order_queue[:]
        self.data = {}
        self.brng = BattleRNG(seed=seed, joker=joker)
        self.char_states = []
        self.queue = []
        self.temp_queue = []
        self.player_queue = []
        self.frame_count = 0
        self.opening_frames_remain = 61
        self.runaway_random = None
        self.victory = False
        self.victory_fanfare = False

        self.next_func = None

        self.atbs = [0 for _ in range(10)]
        self.initial_atbs = None
        self.atb_speeds = atb_speeds

        self.menu_frames = 0

        self.current_attacker = None
        self.char_for_next_turn = None
        self.current_animation_frames = 0

        self.runaway_mode = 0
        self.runaway_counter = 0
        self.runaway_increment = runaway_increment

        self.battle_handlers = {
            4: self.guard_battle_handler,
            5: self.guard_battle_handler,
            6: self.guard_battle_handler,
        }

        self.disable_runaway = False
        self.disable_runaway_next_frame = False

    def add_to_battle_queue(self, char: int):
        self.temp_queue.append(char)

    def pop_from_battle_queue(self):
        return self.queue.pop(0)

    def guard_battle_handler(self):
        rand1 = self.brng.rand16()  # 5d874e

        if self.current_attacker == 4:
            # front row
            attack = rand1 & 1
        else:
            # back row
            attack = 0 if (rand1 % 12) == 0 else 1

        rand2 = self.brng.rand8()
        target = rand2 & 1

        self.brng.incr_rng_idx()
        self.brng.rand8()

        if attack == 0:
            raise Fail
            # # Beam Gun
            # hitPercent = 0x74
            # rand3 = self.brng.rand8_multiply(100)  # 5ddda8 (Hit Check)
            # if rand3 < 4:
            #     hitPercent = 0x00
            # rand4 = self.brng.rand16_percent()  # 5dde29 (Hit Random %)
            # if not (rand4 < hitPercent):
            #     # miss
            #     raise Fail
            # rand5 = self.brng.rand16()  # 5de05c (Crit Check)
            # rand6 = self.brng.rand8_damage_roll(0x6)  # 5de80e (Damage Roll)
            #
            # self.current_animation_frames = 55 + target * 5
        else:
            # hit
            hitPercent = 0x75
            rand3 = self.brng.rand8_multiply(100)  # 5ddda8 (Hit Check)
            if rand3 < 4:
                hitPercent = 0x00
            rand4 = self.brng.rand16_percent()  # 5dde29 (Hit Random %)
            if not (rand4 < hitPercent):
                # miss
                raise Fail
            rand5 = self.brng.rand16()  # 5de05c (Crit Check)
            rand6 = self.brng.rand8_damage_roll(0x6)  # 5de80e (Damage Roll)

            self.current_animation_frames = 18

    def add_player_to_player_queue(self, charSlot):
        self.player_queue.append(charSlot)

    def tick(self):
        if not self.disable_runaway or True:
            self.runaway_counter += self.runaway_increment
            if 0x2000 < self.runaway_counter:
                self.runaway_counter -= 0x2000
                print(f"runrand: {self.runaway_random}")
                if self.runaway_mode == 0 and self.runaway_random < 0x4000:
                    self.runaway_mode = 1
                self.disable_runaway_next_frame = True
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

        self.runaway_random = self.brng.rand16()  # 4326ef

        if self.opening_frames_remain > 0:
            self.opening_frames_remain -= 1
        else:
            if self.current_animation_frames > 0:
                self.current_animation_frames -= 1
            elif self.runaway_mode == 2:
                raise Success
            elif self.runaway_mode == 1:
                self.runaway_mode = 2
                self.current_animation_frames = 67
            elif self.next_func is not None:
                self.next_func()
            elif self.char_for_next_turn is not None:
                self.current_attacker = 0 if self.char_for_next_turn == 2 else self.char_for_next_turn
                if self.char_states[self.current_attacker]:
                    self.battle_handlers[self.char_for_next_turn]()
                self.char_for_next_turn = None
            elif len(self.queue) > 0:
                if self.current_attacker is not None:
                    self.atbs[self.current_attacker] = 0
                if 2 in self.queue:
                    char = 2
                    self.queue.remove(2)
                else:
                    char = self.pop_from_battle_queue()
                self.char_for_next_turn = char
            if len(self.player_queue) > 0:
                if self.menu_frames > 0:
                    self.menu_frames -= 1
            for i in range(4):
                self.tick()
                # self.disable_runaway = False
                # if self.disable_runaway_next_frame:
                #     self.disable_runaway = True
                self.disable_runaway_next_frame = False
            while len(self.temp_queue) > 0:
                self.queue.append(self.temp_queue.pop(0))

    def run(self):
        try:
            self.char_states = [1, 1, 0, 0, 1, 1, 1, 0, 0, 0]
            self.atbs = init_ATB(self.brng, self.char_states)
            self.initial_atbs = self.atbs[:]
            while True:
                self.frame()
        except Fail:
            return False
        except Success:
            return True


sim = Simulator(1002, 0, DEX_8, 273)
sim.run()

if __name__ == '__main__':
    count = 0
    for seed in range(1000, 32768):
        for joker in range(8):
            sim = Simulator(seed, joker, DEX_8, 273)
            if sim.run():
                print(f"{seed} | {hex(prev_state(seed << 0x10))[2:].zfill(8)} | {joker}")
