"""Loading + validation of inputs/scenario files (Test Contract C and D)."""
import json
import math

BUTTONS = ("jump", "interact", "pulse", "dash")


class ContractError(ValueError):
    """Malformed inputs/scenario file -> headless exits with code 2."""


def _num(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ContractError("%s must be a finite number" % what)
    return float(v)


def _vec3(v, what):
    if not isinstance(v, list) or len(v) != 3:
        raise ContractError("%s must be [x, y, z]" % what)
    return [_num(x, what) for x in v]


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
                if not isinstance(fr[b], bool):
                    raise ContractError("inputs: frame %d %s must be boolean" % (i, b))
                ch[b] = fr[b]
        out[t] = ch
    return out


def parse_scenario(data):
    """Validate Contract D; returns a normalised dict accepted by Simulation."""
    if not isinstance(data, dict):
        raise ContractError("scenario: top level must be an object")
    sc = {}
    if "player" in data:
        p = data["player"]
        if not isinstance(p, dict):
            raise ContractError("scenario: player must be an object")
        sp = {}
        if "pos" in p:
            sp["pos"] = _vec3(p["pos"], "player.pos")
        for k in ("carried", "flames"):
            if k in p:
                v = p[k]
                if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                    raise ContractError("scenario: player.%s must be a non-negative integer" % k)
                sp[k] = v
        sc["player"] = sp
    for k in ("random_motes", "random_shades"):
        if k in data:
            if not isinstance(data[k], bool):
                raise ContractError("scenario: %s must be boolean" % k)
            sc[k] = data[k]
    if "motes" in data:
        if not isinstance(data["motes"], list):
            raise ContractError("scenario: motes must be an array")
        sc["motes"] = [_vec3(m, "motes[]") for m in data["motes"]]
    if "shades" in data:
        if not isinstance(data["shades"], list):
            raise ContractError("scenario: shades must be an array")
        shades, ids = [], set()
        for s in data["shades"]:
            if not isinstance(s, dict) or "pos" not in s:
                raise ContractError("scenario: each shade needs a pos")
            sh = {"pos": _vec3(s["pos"], "shades[].pos")}
            if "id" in s:
                if not isinstance(s["id"], str) or not s["id"] or s["id"] in ids:
                    raise ContractError("scenario: shade id must be a unique non-empty string")
                ids.add(s["id"])
                sh["id"] = s["id"]
            shades.append(sh)
        sc["shades"] = shades
    if "lanterns" in data:
        if not isinstance(data["lanterns"], list):
            raise ContractError("scenario: lanterns must be an array")
        lans = []
        for l in data["lanterns"]:
            if not isinstance(l, dict) or not isinstance(l.get("id"), str):
                raise ContractError("scenario: each lantern needs a string id")
            ln = {"id": l["id"]}
            if "pos" in l:
                ln["pos"] = _vec3(l["pos"], "lanterns[].pos")
            if "deposited" in l:
                d = l["deposited"]
                if isinstance(d, bool) or not isinstance(d, int) or d < 0:
                    raise ContractError("scenario: lanterns[].deposited must be a non-negative integer")
                ln["deposited"] = d
            if "lit" in l:
                if not isinstance(l["lit"], bool):
                    raise ContractError("scenario: lanterns[].lit must be boolean")
                ln["lit"] = l["lit"]
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
