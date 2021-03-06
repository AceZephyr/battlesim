from battlerng import *

MENU_FRAMES = 4
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
        self.temp_queue = []
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
        self.char_for_next_turn = None
        self.current_animation_frames = 0

        self.guard_scorpion_phase = 0

        self.data["cloud_hits"] = 0
        self.data["gs_attacks"] = []
        self.data["gs_scope_1"] = False  # used to prevent barret from cuing an attack before scorp's first attack
        self.data["rolls_cloud"] = []
        self.data["rolls_barret"] = []
        self.data["rolls_gs"] = []

        self.scorp_adjusts = []
        for x in [1, 3, 5]:
            self.scorp_adjusts.append(1 if self.initial_attack_order[x] == 1 else 0)

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
        self.temp_queue.append(char)

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
        self.data["rolls_cloud"].append(damage)

        self.current_animation_frames = 73

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
        self.data["rolls_barret"].append(rand5)

        self.current_animation_frames = 43

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

        if self.hp > 0:
            raise Fail

        self.current_animation_frames = 43

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
            self.data["gs_scope_1"] = True
            if not self.data.get("gs_scope", False):
                self.current_animation_frames = 138
            else:
                self.current_animation_frames = 135 + self.scorp_adjusts.pop(0) * 1
        else:
            # attack
            rand1 = self.brng.rand16()
            # 0 = rifle, 1 = scorpion tail
            if (rand1 % 3) == 0 or self.hp < 400:
                attack = 1
            else:
                attack = 0

            is_first_attack = len(self.data["gs_attacks"]) == 0

            self.data["gs_attacks"].append(attack)

            self.brng.incr_rng_idx()
            self.brng.rand8()

            if attack == 0:
                # rifle
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

                self.current_animation_frames = 113 + self.scorp_adjusts.pop(0) * 2
            else:
                # scorpion tail
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

                if is_first_attack:
                    self.current_animation_frames = 111 + self.scorp_adjusts.pop(0) * 2
                else:
                    self.current_animation_frames = 101 + self.scorp_adjusts.pop(0) * 2
        self.guard_scorpion_phase += 1

    def after_guard_scorpion_search_scope_battle_handler(self):
        self.brng.incr_rng_idx()
        self.data["gs_scope"] = True
        self.current_animation_frames = 0
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
                self.victory_fanfare = True
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
                elif len(self.attack_order_queue) > 0:
                    for i in range(len(self.player_queue)):
                        if self.player_queue[i] == self.attack_order_queue[0] % 2:
                            player = self.player_queue[i]
                            if not (player == 1 and not self.data["gs_scope_1"]):
                                # awkward conditional to prevent cueing an attack with barret on the first turn
                                self.player_queue.pop(i)
                                self.add_to_battle_queue(self.attack_order_queue.pop(0))
                            break
            for i in range(4):
                self.tick()
            while len(self.temp_queue) > 0:
                self.queue.append(self.temp_queue.pop(0))

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


ATTACK_ORDERS = [
    (0, 0, 1, 0, 1, 0, 1, 0, 1, 2),  # 0
    (0, 0, 1, 0, 1, 1, 0, 0, 1, 2),  # 1
    (0, 0, 1, 1, 0, 0, 1, 0, 1, 2),  # 2
    (0, 0, 1, 1, 0, 1, 0, 0, 1, 2),  # 3
    (0, 1, 0, 0, 1, 0, 1, 0, 1, 2),  # 4
    (0, 1, 0, 0, 1, 1, 0, 0, 1, 2),  # 5
    (0, 1, 0, 1, 0, 0, 1, 0, 1, 2),  # 6
    (0, 1, 0, 1, 0, 1, 0, 0, 1, 2),  # 7
]

if __name__ == '__main__':
    count = 0
    for seed in range(32768):
        for joker in range(8):
            for attack_order_index in range(len(ATTACK_ORDERS)):
                attack_order = ATTACK_ORDERS[attack_order_index]
                sim = Simulator(seed, joker, DEX_7, list(attack_order))
                ret = sim.run()
                if ret:
                    count += 1
                    print(
                        f"{hex(seed)[2:].zfill(4)} {sim.brng.joker} {joker} {attack_order_index} {hex(prev_state(seed << 0x10))[2:].zfill(8)} {sim.data['gs_attacks']}")

    print(f"count: {count}")
