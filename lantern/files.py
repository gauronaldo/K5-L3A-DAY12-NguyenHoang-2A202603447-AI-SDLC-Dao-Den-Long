"""Loading + validation of inputs/scenario files (Test Contract sections C and D, v1.1)."""
import json
import math

BUTTONS = ("jump", "interact", "pulse", "dash", "pause")
SHADE_STATES = ("spawning", "wander", "chase", "recoil", "stunned")
DRIFTER_STATES = ("idle", "chase", "flee", "removed")


class ContractError(ValueError):
    """Malformed inputs/scenario file -> headless exits with code 2."""


def _num(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ContractError("%s must be a finite number" % what)
    return float(v)


def _int(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ContractError("%s must be a non-negative integer" % what)
    return v


def _bool(v, what):
    if not isinstance(v, bool):
        raise ContractError("%s must be boolean" % what)
    return v


def _vec3(v, what):
    if not isinstance(v, list) or len(v) != 3:
        raise ContractError("%s must be [x, y, z]" % what)
    return [_num(x, what) for x in v]


def _list(data, key):
    if not isinstance(data[key], list):
        raise ContractError("scenario: %s must be an array" % key)
    return data[key]


def _obj(v, what):
    if not isinstance(v, dict):
        raise ContractError("%s must be an object" % what)
    return v


def _load_json(path, kind):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise ContractError("cannot read %s file %s: %s" % (kind, path, e))
    except json.JSONDecodeError as e:
        raise ContractError("%s file is not valid JSON: %s" % (kind, e))


def parse_inputs(data):
    """Return {tick: {field: value}} after validating Contract C."""
    if not isinstance(data, dict) or not isinstance(data.get("frames"), list):
        raise ContractError("inputs: top level must be an object with a 'frames' array")
    out, last = {}, -1
    for i, fr in enumerate(data["frames"]):
        if not isinstance(fr, dict):
            raise ContractError("inputs: frame %d is not an object" % i)
        t = fr.get("tick")
        if isinstance(t, bool) or not isinstance(t, int) or t < 0:
            raise ContractError("inputs: frame %d has invalid tick" % i)
        if t <= last:
            raise ContractError("inputs: ticks must strictly increase (frame %d, tick %d)" % (i, t))
        last = t
        ch = {}
        if "move" in fr:
            m = fr["move"]
            if not isinstance(m, list) or len(m) != 2:
                raise ContractError("inputs: frame %d move must be [x, z]" % i)
            mx, mz = _num(m[0], "move"), _num(m[1], "move")
            if not (-1.0 <= mx <= 1.0 and -1.0 <= mz <= 1.0):
                raise ContractError("inputs: frame %d move components must be in [-1, 1]" % i)
            ch["move"] = (mx, mz)
        if "cam_yaw_deg" in fr:
            ch["cam_yaw_deg"] = _num(fr["cam_yaw_deg"], "cam_yaw_deg")
        for b in BUTTONS:
            if b in fr:
                ch[b] = _bool(fr[b], "inputs: frame %d %s" % (i, b))
        out[t] = ch
    return out


def parse_scenario(data):
    """Validate Contract D (v1.1); returns a normalised dict accepted by Simulation."""
    if not isinstance(data, dict):
        raise ContractError("scenario: top level must be an object")
    sc = {}
    if "player" in data:
        p = _obj(data["player"], "scenario: player")
        sp = {}
        if "pos" in p:
            sp["pos"] = _vec3(p["pos"], "player.pos")
        for k in ("carried", "flames", "invuln_ticks", "dash_cd_ticks", "pulse_cd_ticks", "charm_ticks",
                  "successful_lights"):
            if k in p:
                sp[k] = _int(p[k], "scenario: player.%s" % k)
        sc["player"] = sp
    for k in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
        if k in data:
            sc[k] = _bool(data[k], "scenario: %s" % k)
    if "motes" in data:
        motes = []
        for m in _list(data, "motes"):
            if isinstance(m, list):
                motes.append({"pos": _vec3(m, "motes[]"), "kind": "random"})
                continue
            m = _obj(m, "scenario: motes[]")
            mm = {"pos": _vec3(m.get("pos"), "motes[].pos"), "kind": m.get("kind", "random")}
            if mm["kind"] not in ("random", "dropped"):
                raise ContractError("scenario: motes[].kind must be random or dropped")
            if m.get("ttl_s") is not None:
                mm["ttl_ticks"] = max(1, int(round(_num(m["ttl_s"], "motes[].ttl_s") * 60)))
            motes.append(mm)
        sc["motes"] = motes
    if "shades" in data:
        shades, ids = [], set()
        for s in _list(data, "shades"):
            s = _obj(s, "scenario: shades[]")
            sh = {"pos": _vec3(s.get("pos"), "shades[].pos")}
            if "id" in s:
                if not isinstance(s["id"], str) or not s["id"] or s["id"] in ids:
                    raise ContractError("scenario: shade id must be a unique non-empty string")
                ids.add(s["id"])
                sh["id"] = s["id"]
            if "state" in s:
                if s["state"] not in SHADE_STATES + ("drain",):
                    raise ContractError("scenario: unknown shade state %r" % s["state"])
                sh["state"] = s["state"]
            if "state_ticks_left" in s:
                sh["state_ticks_left"] = _int(s["state_ticks_left"], "scenario: shades[].state_ticks_left")
            if "target_lantern_id" in s:
                if not isinstance(s["target_lantern_id"], str):
                    raise ContractError("scenario: shades[].target_lantern_id must be a string")
                sh["target_lantern_id"] = s["target_lantern_id"]
            shades.append(sh)
        sc["shades"] = shades
    if "drifters" in data:
        drs = []
        for d in _list(data, "drifters"):
            d = _obj(d, "scenario: drifters[]")
            dd = {"pos": _vec3(d.get("pos"), "drifters[].pos")}
            if "id" in d:
                dd["id"] = str(d["id"])
            if "state" in d:
                if d["state"] not in DRIFTER_STATES:
                    raise ContractError("scenario: unknown drifter state %r" % d["state"])
                dd["state"] = d["state"]
            if "stolen" in d:
                dd["stolen"] = _int(d["stolen"], "scenario: drifters[].stolen")
            if "state_ticks_left" in d:
                dd["state_ticks_left"] = _int(d["state_ticks_left"], "scenario: drifters[].state_ticks_left")
            drs.append(dd)
        sc["drifters"] = drs
    if "charms" in data:
        chs = []
        for c in _list(data, "charms"):
            c = _obj(c, "scenario: charms[]")
            cc = {}
            if "id" in c:
                cc["id"] = str(c["id"])
            if "pos" in c:
                cc["pos"] = _vec3(c["pos"], "charms[].pos")
            if "available" in c:
                cc["available"] = _bool(c["available"], "scenario: charms[].available")
            if "respawn_ticks" in c:
                cc["respawn_ticks"] = _int(c["respawn_ticks"], "scenario: charms[].respawn_ticks")
            elif "respawn_s" in c:
                cc["respawn_ticks"] = int(round(_num(c["respawn_s"], "charms[].respawn_s") * 60))
            chs.append(cc)
        sc["charms"] = chs
    if "lanterns" in data:
        lans = []
        for l in _list(data, "lanterns"):
            if not isinstance(l, dict) or not isinstance(l.get("id"), str):
                raise ContractError("scenario: each lantern needs a string id")
            ln = {"id": l["id"]}
            if "pos" in l:
                ln["pos"] = _vec3(l["pos"], "lanterns[].pos")
            if "deposited" in l:
                ln["deposited"] = _int(l["deposited"], "scenario: lanterns[].deposited")
            for k in ("lit", "ever_lit"):
                if k in l:
                    ln[k] = _bool(l[k], "scenario: lanterns[].%s" % k)
            if "fuel" in l:
                ln["fuel"] = _num(l["fuel"], "lanterns[].fuel")
            lans.append(ln)
        sc["lanterns"] = lans
    if "time_left_s" in data:
        t = _num(data["time_left_s"], "time_left_s")
        if t < 0:
            raise ContractError("scenario: time_left_s must be >= 0")
        sc["time_left_s"] = t
    return sc


def load_inputs(path):
    return parse_inputs(_load_json(path, "inputs"))


def load_scenario(path):
    return parse_scenario(_load_json(path, "scenario"))
