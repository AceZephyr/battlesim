# a = 0x343FD
# b = 0x269EC3
# a_inv = 3115528533


def next_state(x):
    a = 0x343FD
    b = 0x269EC3
    return (a * x + b) & 0xffffffff


def rand(x):
    return (next_state(x) >> 0x10) & 0x7fff


def prev_state(x):
    a_inv = 3115528533
    b = 0x269EC3
    return (a_inv * (x - b)) & 0xffffffff


def state_from_index(x):
    a = 0x343FD
    b = 0x269EC3
    q = 2 ** 32
    # inverse of (a-1)/4
    inv = 3831377663
    return (b * int((pow(a, x, 4 * q) - 1) // 4) * inv) % q


def index_from_state(state):
    out = 0
    for i in range(32):
        out ^= (state_from_index(out) ^ state) & (1 << i)
    return out
