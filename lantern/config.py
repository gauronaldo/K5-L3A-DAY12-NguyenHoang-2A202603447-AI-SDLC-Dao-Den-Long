"""Tuning values for Night 1. game.contract.json is generated from / checked against this file."""

TICK_RATE = 60
DT = 1.0 / TICK_RATE

TUNING = {
    "player_speed": 6.0,          # m/s on the ground
    "carry_capacity": 10,         # max fireflies carried
    "lantern_cost": 5,            # fireflies needed to light one lantern
    "lantern_count_night1": 5,
    "pickup_radius": 1.0,         # XZ distance player feet -> mote
    "interact_radius": 2.5,       # XZ distance player feet -> lantern base
    "pulse_cost": 1,              # fireflies spent per light pulse
    "pulse_radius": 6.0,
    "night1_duration_s": 300.0,
    "flames": 3,                  # player HP
    "invuln_s": 1.5,              # invulnerability after a hit
    "hit_drop_ratio": 0.5,        # floor(carried * ratio) fireflies lost on hit
    "pulse_stun_s": 3.0,
    "pulse_push_m": 4.0,
    "pulse_cooldown_s": 1.0,
    "safe_radius": 5.0,           # shades never enter this radius around ANY lantern
    "shade_speed": 3.5,
    "shade_hit_radius": 1.0,
}

FALL_ENABLED = False

SCORE = {
    "per_mote": 10,
    "per_lantern": 100,
    "per_stun": 5,
    "per_second_left": 1,     # floor(time_left_s), only when won
    "per_flame_left": 50,     # only when won
}

# Layout / non-contract constants (assumptions, see docs/notes/phase-1.md)
ISLAND_RADIUS = 32.0
LANTERN_RING_RADIUS = 25.0
JUMP_SPEED = 7.0              # m/s initial vertical speed
GRAVITY = 20.0                # m/s^2
SHADE_HEIGHT = 1.0            # shade centre height for generated shades
RANDOM_MOTES = 40
MOTE_RING = (4.0, 30.0)
INITIAL_SHADES = 2
SHADE_SPAWN_EVERY_S = 45.0
MAX_SHADES = 6
SHADE_SPAWN_RING = (14.0, 30.0)
SHADE_SPAWN_MIN_DIST_PLAYER = 12.0
SAFE_EPS = 1e-3               # shades are kept at safe_radius + eps
