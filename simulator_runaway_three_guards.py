from battlerng import *

DEX_7 = [0x22B, 0x218, 0x1E7, 0, 0x235, 0x235, 0x235, 0, 0, 0]
DEX_8 = [0x22B, 0x218, 0x1E7, 0, 0x22B, 0x22B, 0x22B, 0, 0, 0]
DEX_9 = [0x235, 0x20E, 0x1DE, 0, 0x22B, 0x22B, 0x22B, 0, 0, 0]


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