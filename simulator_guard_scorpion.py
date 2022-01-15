from battlerng import *

MENU_FRAMES = 5
STAT_ROLL_ARR = [0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3]
HP_ROLL_ARR = [40, 50, 50, 60, 70, 80, 90, 100, 110, 120, 130, 150]
MP_ROLL_ARR = [20, 30, 30, 50, 70, 80, 90, 100, 110, 120, 140, 160]
DEX_7 = [0x22B, 0x218, 0, 0, 0x249]
DEX_8 = [0x22B, 0x20E, 0, 0, 0x23E]
DEX_9 = [0x235, 0x20E, 0, 0, 0x23E]


class Simulator:
    def __init__(self, seed, joker, atb_speeds, attack_order_queue):
        self.initial_seed = seed
        self.initial_attack_order = attack_order_queue[:]
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

        self.next_func = None

        self.atbs = [0 for _ in range(10)]
        self.initial_atbs = None
        self.atb_speeds = atb_speeds

        self.hp = 800
        self.attack_order_queue = attack_order_queue

        self.menu_frames = 0

        self.current_attacker = None
        self.current_animation_frames = 0

        self.guard_scorpion_phase = 0

        self.data["cloud_hits"] = 0
        self.data["gs_attacks"] = []

        self.battle_handlers = {
            0: self.cloud_battle_handler,
            1: self.barret_battle_handler,
            2: self.cloud_braver_battle_handler,
            4: self.guard_scorpion_battle_handler,
        }

    def post_battle_victory(self):
        dropChance4 = self.brng.rand8()

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

    def damage(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.remove_from_battle(4)
            raise Success

    def cloud_battle_handler(self):
        self.current_attacker = 0
        self.brng.incr_rng_idx()
        rand1 = self.brng.rand8()
        rand2 = self.brng.rand8()
        rand3 = self.brng.rand8_damage_roll(0x31)  # 5DEA4F (Damage Roll)

        damage = rand3 * 2

        self.damage(damage)

        self.current_animation_frames = 74

    def barret_battle_handler(self):
        self.current_attacker = 1
        self.brng.incr_rng_idx()
        rand1 = self.brng.rand8()  # 5c80d7
        hitPercent = 0x63
        rand2 = self.brng.rand8_multiply(100)  # 5ddda8 (Hit Check)
        if rand2 < 3:
            hitPercent = 0xFF

        rand3 = self.brng.rand16_percent()  # 5dde29 (Hit Random %)
        if not (rand3 < hitPercent):
            # miss
            raise Fail

        rand4 = self.brng.rand16()  # 5de05c (Crit Check)
        rand5 = self.brng.rand8_damage_roll(0x1A)  # 5de80e (Damage Roll)
        self.damage(rand5)

        self.current_animation_frames = 44

    def cloud_braver_battle_handler(self):
        self.current_attacker = 0
        self.brng.incr_rng_idx()
        rand1 = self.brng.rand8()  # 5c80d7
        hitPercent = 0x103
        rand2 = self.brng.rand8_multiply(100)  # 5ddda8 (Hit Check)
        if rand2 < 3:
            hitPercent = 0xFF

        rand3 = self.brng.rand16_percent()  # 5dde29 (Hit Random %)
        if not (rand3 < hitPercent):
            # miss
            raise Fail

        rand4 = self.brng.rand16_percent()  # 5de05c (Crit Check)
        if not (rand4 <= 2):
            # not crit
            # print(f"rand4: {rand4}")
            raise Fail
        rand5 = self.brng.rand8_damage_roll(0x7C * 2)  # 5de80e (Damage Roll)
        self.damage(rand5)

        self.current_animation_frames = 44

    def guard_scorpion_battle_handler(self):
        self.current_attacker = 4
        if self.guard_scorpion_phase in {0, 2}:
            # search scope
            rand2 = self.brng.rand8()  # 5d19a4 (AI: Choose Target)
            chosen_target = rand2 & 1

            if chosen_target == 1:
                raise Fail

            self.brng.incr_rng_idx()
            rand3 = self.brng.rand8()  # 5c80d7
            self.brng.rand8_multiply(0)  # maybe determine value here (though it shouldn't matter)

            self.next_func = self.after_guard_scorpion_search_scope_battle_handler
            if not self.data.get("gs_scope", False):
                self.current_animation_frames = 138
            else:
                self.current_animation_frames = 135
        else:
            # attack
            self.brng.rand8()
            self.brng.incr_rng_idx()
            rand1 = self.brng.rand16()
            # 0 = rifle, 1 = scorpion tail
            if (rand1 % 3) == 0 or self.hp < 400:
                attack = 1
            else:
                attack = 0

            self.data["gs_attacks"].append(attack)

            if attack == 0:
                hitPercent = 0x71
                rand2 = self.brng.rand8_multiply(100)  # 5ddda8 (Hit Check)
                if rand2 < 4:
                    hitPercent = 0x00

                rand3 = self.brng.rand16_percent()  # 5dde29 (Hit Random %)
                if not (rand3 < hitPercent):
                    # miss
                    raise Fail

                rand4 = self.brng.rand16()  # 5de05c (Crit Check)
                rand5 = self.brng.rand8_damage_roll(0x44)  # 5de80e (Damage Roll)

                self.current_animation_frames = 114
            else:
                hitPercent = 0x6C
                rand2 = self.brng.rand8_multiply(100)  # 5ddda8 (Hit Check)
                if rand2 < 4:
                    hitPercent = 0x00

                rand3 = self.brng.rand16_percent()  # 5dde29 (Hit Random %)
                if not (rand3 < hitPercent):
                    # miss
                    raise Fail

                rand4 = self.brng.rand16()  # 5de05c (Crit Check)
                rand5 = self.brng.rand8_damage_roll(0x44)  # 5de80e (Damage Roll)

                self.current_animation_frames = 102
        self.guard_scorpion_phase += 1

    def after_guard_scorpion_search_scope_battle_handler(self):
        self.brng.incr_rng_idx()
        self.data["gs_scope"] = True
        self.current_animation_frames = 1
        self.next_func = None

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
                # self.data["jokers"].append(self.brng.joker)
                self.victory_fanfare = True
                self.current_animation_frames = 67
            elif self.next_func is not None:
                self.next_func()
            elif len(self.queue) > 0:
                if self.current_attacker is not None:
                    self.atbs[self.current_attacker] = 0
                    # if self.current_attacker == 4:
                    #     self.data["cloud_hits"] += 1
                if 2 in self.queue:
                    char = 2
                    self.queue.remove(2)
                else:
                    char = self.pop_from_battle_queue()
                self.current_attacker = 0 if char == 2 else char
                if self.char_states[self.current_attacker]:
                    self.battle_handlers[char]()
            if len(self.player_queue) > 0:
                if self.menu_frames > 0:
                    self.menu_frames -= 1
                elif len(self.attack_order_queue) > 0:
                    for i in range(len(self.player_queue)):
                        if self.player_queue[i] == self.attack_order_queue[0] % 2:
                            player = self.player_queue.pop(i)
                            self.add_to_battle_queue(self.attack_order_queue.pop(0))
                            break
            for i in range(4):
                self.tick()

    def run(self):
        try:
            self.char_states = [1, 1, 0, 0, 1, 0, 0, 0, 0, 0]
            self.atbs = init_ATB(self.brng, self.char_states)
            self.initial_atbs = self.atbs[:]
            if self.atbs[0] != 0xE000:
                raise Fail
            if self.atbs[4] >= 0xAF47:
                raise Fail
            while True:
                self.frame()
        except Fail:
            return False
        except Success:
            return True


# sim = Simulator(Simulator1, 0, DEX_7, [0, 1, 0, 1, 0, 1, 0, 1, 0, 2])
# ret = sim.run()
# breakpoint()

ATTACK_ORDERS = [
    (0, 0, 1, 0, 1, 0, 1, 0, 1, 2),
    # [0, 0, 1, 0, 1, 1, 0, 0, 1, 2],
    # [0, 0, 1, 1, 0, 0, 1, 0, 1, 2],
    # [0, 0, 1, 1, 0, 1, 0, 0, 1, 2],
    # [0, 1, 0, 0, 1, 0, 1, 0, 1, 2],
    # [0, 1, 0, 0, 1, 1, 0, 0, 1, 2],
    # [0, 1, 0, 1, 0, 0, 1, 0, 1, 2],
    # [0, 1, 0, 1, 0, 1, 0, 0, 1, 2],
]

seed = 0x0
joker = 0
count = 0
while joker < 8:
    while seed < 32768:
        # print(f"seed: {seed} | joker: {joker}")
        for attack_order in ATTACK_ORDERS:
            sim = Simulator(seed, 0, DEX_7, list(attack_order))
            ret = sim.run()
            if ret:
                count += 1
                print(f"{hex(seed)[2:].zfill(4)} {sim.brng.joker} {hex(prev_state(seed << 0x10))[2:].zfill(8)} {sim.data['gs_attacks']}")
            seed += 1
    joker += 1

print(f"count: {count}")
