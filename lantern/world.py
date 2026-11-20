"""Standard map geometry (Ticket-02 Part 2): ground height and obstacles per night."""
import math

from . import config as C


def ground_height(night, x, z):
    """Top surface height at (x, z), or None over the cloud sea."""
    r = math.hypot(x, z)
    if night == 1:
        return 0.0 if r <= C.N1_RADIUS else None
    if night == 2:
        for cx, cz in C.N2_ISLANDS:
            if math.hypot(x - cx, z - cz) <= C.N2_RADIUS:
                return 0.0
        x0, x1, z0, z1 = C.N2_BRIDGE
        if x0 <= x <= x1 and z0 <= z <= z1:
            return 0.0
        return None
    # night 3
    if r > C.N3_RADIUS:
        return None
    if r <= C.N3_TIER2[0]:
        return C.N3_TIER2[1]
    t_in, t_out, t_h = C.N3_TIER1
    if z > 0 and t_in <= r <= t_out:
        return t_h
    top, foot, width = C.N3_RAMP
    for deg in C.N3_RAMPS:
        a = math.radians(deg)
        ux, uz = math.cos(a), math.sin(a)
        along = x * ux + z * uz
        perp = abs(-x * uz + z * ux)
        if perp <= width / 2 and top <= along <= foot:
            return t_h * (foot - along) / (foot - top)
    return 0.0


def blocked_xz(night, x, z):
    """Solid obstacles nothing can enter (night 3 bell tower)."""
    return night == 3 and math.hypot(x, z) < C.N3_TOWER_R


def push_out_of_tower(night, pos):
    if night != 3:
        return
    d = math.hypot(pos[0], pos[2])
    if d < C.N3_TOWER_R:
        if d < 1e-9:
            pos[0], pos[2] = C.N3_TOWER_R, 0.0
        else:
            pos[0] *= C.N3_TOWER_R / d
            pos[2] *= C.N3_TOWER_R / d
