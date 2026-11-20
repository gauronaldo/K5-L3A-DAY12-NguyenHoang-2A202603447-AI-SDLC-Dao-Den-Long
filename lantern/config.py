"""Standard numbers (Ticket-02, contract v1.1) and the three standard maps.

game.contract.json is checked against TUNING / SCORE by tests/test_headless.py.
"""
import math

CONTRACT_VERSION = "1.1"
TICK_RATE = 60
DT = 1.0 / TICK_RATE

TUNING = {
    "player_speed": 6.0,
    "carry_capacity": 10,
    "lantern_cost": 10,
    "lantern_count_night1": 5,
    "pickup_radius": 1.0,
    "interact_radius": 2.0,
    "pulse_cost": 3,
    "pulse_radius": 5.0,
    "night1_duration_s": 300.0,
    "flames": 3,
    "invuln_s": 1.5,
    "hit_drop_ratio": 0.5,
    "pulse_stun_s": 2.0,
    "pulse_push_m": 4.0,
    "pulse_cooldown_s": 3.0,
    "safe_radius": 6.0,
    "shade_speed": 4.0,
    "shade_hit_radius": 1.0,
    "dash_speed": 14.0,
    "dash_duration_s": 0.2,
    "dash_cooldown_s": 1.5,
    "night2_duration_s": 330.0,
    "night3_duration_s": 360.0,
}
FALL_ENABLED = True

SCORE = {
    "per_mote": 10,           # per firefly deposited into a lantern
    "per_lantern": 100,
    "per_stun": 5,
    "per_second_left": 2,     # floor(time_left_s), only when won
    "per_flame_left": 50,     # only when won
}

# ---- derived tick constants (Part 1) ----
def ticks(seconds):
    return int(round(seconds * TICK_RATE))


JUMP_SPEED = 7.0
GRAVITY = 20.0
DASH_TICKS = ticks(TUNING["dash_duration_s"])        # 12
DASH_CD_TICKS = ticks(TUNING["dash_cooldown_s"])     # 90
PULSE_CD_TICKS = ticks(TUNING["pulse_cooldown_s"])   # 180
STUN_TICKS = ticks(TUNING["pulse_stun_s"])           # 120
PUSH_TICKS = 15
PULSE_CENTER_Y = 0.8
INVULN_TICKS = ticks(TUNING["invuln_s"])             # 90
PICKUP_DY = 1.5
MOTE_START = 20
MOTE_CAP = 30
MOTE_SPAWN_EVERY = 240
DROP_RING = (1.5, 2.5)
DROP_TTL = 480
SHADE_DETECT = 12.0
SHADE_GIVEUP = 18.0
SHADE_HIT_DY = 1.5
SHADE_FIRST_SPAWN = 300
SHADE_SPAWNING_TICKS = 60
SHADE_WANDER_SPEED = 2.0
SHADE_HOVER = 1.0
RECOIL_TICKS = 60
RECOIL_DIST = 2.0
EVICT_TICKS = 30
SHADE_SPAWN_MIN_DIST = 15.0
FALL_Y = -10.0
FALL_WAIT = 60
STEP_UP = 0.35
SAFE_EPS = 1e-3
CHARM_TICKS = 600
CHARM_SPEED = 7.2
CHARM_RESPAWN = 2700
DRIFTER_SPEED = 7.0
DRIFTER_IDLE_SPEED = 2.0
DRIFTER_MAX = 2
DRIFTER_EVERY = 1200
DRIFTER_CHASE_MIN_CARRY = 5
DRIFTER_CHASE_DIST = 15.0
DRIFTER_TOUCH = 1.2
DRIFTER_STEAL = 3
DRIFTER_FLEE_TICKS = 240
DRIFTER_DROP_VANISH = 120
DRIFTER_HOVER = 1.5
WIND_EVERY = 1800
WIND_TICKS = 300
WIND_WARN = 120
WIND_SPEED = 2.0


def polar(r, deg, y=0.0):
    """Angle from +X, counter-clockwise seen from above, on the XZ plane: (r cos, y, r sin)."""
    a = math.radians(deg)
    return [round(r * math.cos(a), 6), y, round(r * math.sin(a), 6)]


def _ring(r, start, step, n, y=0.0, center=(0.0, 0.0)):
    out = []
    for i in range(n):
        p = polar(r, start + step * i, y)
        out.append([round(p[0] + center[0], 6), y, round(p[2] + center[1], 6)])
    return out


NIGHTS = {
    1: {
        "name": "Đảo Bến",
        "duration_s": TUNING["night1_duration_s"],
        "start": [0.0, 0.0, 0.0],
        "lanterns": [[0, 0, 25], [23.8, 0, 7.7], [14.7, 0, -20.2], [-14.7, 0, -20.2], [-23.8, 0, 7.7]],
        "mote_points": _ring(12, 0, 45, 8) + _ring(33, 0, 22.5, 16),
        "shade_points": _ring(37, 15, 30, 12, y=SHADE_HOVER),
        "shade_every_s": 8, "shade_max": 6, "shade_speed": 4.0,
        "charms": [], "drifters": False, "wind": False,
        "pads": [],
    },
    2: {
        "name": "Đảo Cau",
        "duration_s": TUNING["night2_duration_s"],
        "start": [0.0, 0.0, 0.0],
        "lanterns": [[0, 0, 20], [17, 0, -10], [-17, 0, -10], [70, 0, 20], [87, 0, -10], [53, 0, -10]],
        "mote_points": (_ring(10, 0, 90, 4) + _ring(22, 0, 45, 8)
                        + _ring(10, 0, 90, 4, center=(70, 0)) + _ring(22, 0, 45, 8, center=(70, 0))),
        "shade_points": _ring(26, 22.5, 45, 8, y=SHADE_HOVER) + _ring(26, 22.5, 45, 8, y=SHADE_HOVER, center=(70, 0)),
        "shade_every_s": 7, "shade_max": 8, "shade_speed": 4.0,
        "charms": [[35, 0, 0]], "drifters": True, "wind": False,
        # pad centre, launch vy, horizontal speed, target point for direction
        "pads": [{"pos": [20, 0, 18], "vy": 14.0, "h": 24.0, "toward": [70, 0, 0]},
                 {"pos": [50, 0, -18], "vy": 14.0, "h": 24.0, "toward": [0, 0, 0]}],
    },
    3: {
        "name": "Đảo Chuông",
        "duration_s": TUNING["night3_duration_s"],
        "start": [0.0, 0.0, -25.0],
        "lanterns": [[0, 6, 6], [18, 3, 10], [-18, 3, 10], [35, 0, -10], [-35, 0, -10], [20, 0, -35], [-20, 0, -35]],
        "mote_points": _ring(34, 0, 20, 18) + _ring(18, 20, 20, 8, y=3.0) + _ring(5, 45, 90, 4, y=6.0),
        "shade_points": _ring(43, 0, 22.5, 16, y=SHADE_HOVER),
        "shade_every_s": 6, "shade_max": 10, "shade_speed": 4.5,
        "charms": [[30, 0, 25], [-30, 0, 25]], "drifters": True, "wind": True,
        "pads": [{"pos": [0, 3, 13], "vy": 12.0, "h": 8.0, "dir": [0.0, -1.0]}],
    },
}

# Night 3 geometry
N3_RADIUS = 45.0
N3_TIER1 = (12.0, 24.0, 3.0)      # inner r, outer r, height (only z > 0)
N3_TIER2 = (8.0, 6.0)             # radius, height
N3_TOWER_R = 2.0
N3_TOWER_H = 8.0
N3_RAMPS = (30.0, 150.0)          # angles (deg)
N3_RAMP = (24.0, 30.0, 3.0)       # top r, foot r, width
N2_ISLANDS = ((0.0, 0.0), (70.0, 0.0))
N2_RADIUS = 28.0
N2_BRIDGE = (26.0, 44.0, -2.0, 2.0)
N1_RADIUS = 40.0

# Palette (Ticket-02 Part 3)
PALETTE = {
    "sky": "#0E1430", "fog": "#1B2350", "grass": "#2F5D50", "sand": "#C9B48A", "wood": "#6B4A2F",
    "cloud_sea": "#12384A", "lantern_lit": "#FFB347", "lantern_core": "#FFE9B0", "lantern_off": "#5B5F6E",
    "mote_core": "#FFF6C2", "mote_glow": "#FFE58A", "shade_body": "#120A1A", "shade_rim": "#7A3CFF",
    "shade_stunned": "#3A3450", "may_cloak": "#E8E2D0", "may_scarf": "#C8102E", "charm": "#C8102E",
    "gold": "#F2C14E", "drifter": "#8FA3B8", "ui_danger": "#FF5A5F", "ui_text": "#F5F1E6",
}


def hex_rgb(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


def ambient_intensity(lit, total):
    return 0.15 + 0.55 * (lit / float(total)) if total else 0.15
