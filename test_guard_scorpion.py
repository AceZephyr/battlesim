from simulator_guard_scorpion import *

assert Simulator(rand(0x5429f641), 0, DEX_7, list(ATTACK_ORDERS[0])).run()
assert Simulator(rand(0xcc41f641), 0, DEX_7, list(ATTACK_ORDERS[0])).run()
assert not Simulator(rand(0xf16cf641), 0, DEX_7, list(ATTACK_ORDERS[3])).run()
assert Simulator(rand(0x66c4f641), 5, DEX_7, list(ATTACK_ORDERS[6])).run()
assert Simulator(rand(0x2c18f641), 3, DEX_7, list(ATTACK_ORDERS[6])).run()

print("done!")
