"""Skeleton, forward and inverse kinematics, and the five animation clips of an Undercity NPC.

It owns the motion: where every joint of the shared 18-bone layout sits for a character's
proportions, and the pose of every bone at any time of the idle, walk, talk, guard and sit
loops. It uses mathutils only (no bpy), so the maths reads on its own; build_characters.py turns
these poses into Blender keys. Tuning (amplitudes, lengths, the walk speed) comes from the
animations block of characters.json; the shapes of the motions live here.

Conventions: armature space is Blender's, with X = the character's left, -Y = its front and
Z = up, feet at Z = 0. A pose stores for each bone a rotation R expressed in armature axes as
carried by the parent's pose, so a bone's world rotation is D = D_parent @ R, and the pelvis
offset in armature space. Positive X rotation swings a hanging limb backward; positive Z turns
the character to its left. Angles in code are radians unless a name ends in _deg.
"""
import math

from mathutils import Matrix, Quaternion, Vector

BONES = (
    ("root", None), ("pelvis", "root"), ("spine", "pelvis"), ("chest", "spine"), ("neck", "chest"),
    ("head", "neck"),
    ("upperarm_l", "chest"), ("forearm_l", "upperarm_l"), ("hand_l", "forearm_l"),
    ("upperarm_r", "chest"), ("forearm_r", "upperarm_r"), ("hand_r", "forearm_r"),
    ("thigh_l", "pelvis"), ("shin_l", "thigh_l"), ("foot_l", "shin_l"),
    ("thigh_r", "pelvis"), ("shin_r", "thigh_r"), ("foot_r", "shin_r"),
)
PARENT = dict(BONES)
SIGN = {"l": 1.0, "r": -1.0}
CLIPS = ("idle", "walk", "talk", "guard", "sit")
SOLE_MARGIN = 0.004   # the sole overhangs the shoe upper by this fraction of height, heel and toe

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def euler_deg(x=0.0, y=0.0, z=0.0):
    """Rotation of x degrees about X, then y about Y, then z about Z (armature axes)."""
    return (Quaternion(Z, math.radians(z)) @ Quaternion(Y, math.radians(y)) @ Quaternion(X, math.radians(x)))


def smooth(u):
    """Smoothstep on [0, 1], clamped."""
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def frame(u, n):
    """Orthonormal basis matrix with columns u, n and u x n."""
    return Matrix((u, n, u.cross(n))).transposed()


def ortho(v, axis):
    """v with its component along the unit vector axis removed, normalised."""
    w = v - axis * v.dot(axis)
    return w.normalized()


class Skeleton:
    """Rest joints of one character in armature space, from the anatomy fractions and its row."""

    def __init__(self, anatomy, row, splay_deg):
        A, H, b = anatomy, row["height_m"], row["build"]
        self.H = H
        self.head, self.tail = {}, {}
        self.head["root"], self.tail["root"] = Vector((0, 0, 0)), Vector((0, -0.15, 0))
        chain = (("pelvis", A["hip_z"], A["waist_z"]), ("spine", A["waist_z"], A["chest_z"]),
                 ("chest", A["chest_z"], A["neck_z"]), ("neck", A["neck_z"], A["skull_z"]), ("head", A["skull_z"], 1.0))
        for name, z0, z1 in chain:
            self.head[name], self.tail[name] = Vector((0, 0, z0 * H)), Vector((0, 0, z1 * H))
        self.splay = {}
        for s, sg in SIGN.items():
            a = math.radians(splay_deg[s])
            self.splay[s] = splay_deg[s]
            d = Vector((sg * math.sin(a), 0, -math.cos(a)))
            sh = Vector((sg * A["shoulder_x"] * H * b["shoulders"], 0, A["shoulder_z"] * H))
            el = sh + d * A["upperarm_len"] * H
            wr = el + d * A["forearm_len"] * H
            for name, h, t in ((f"upperarm_{s}", sh, el), (f"forearm_{s}", el, wr),
                               (f"hand_{s}", wr, wr + d * A["hand_len"] * H)):
                self.head[name], self.tail[name] = h, t
            hx = sg * A["hip_x"] * H * b["hips"]
            hip, knee, ankle = Vector((hx, 0, A["hip_z"] * H)), Vector((hx, 0, A["knee_z"] * H)), Vector((hx, 0, A["ankle_z"] * H))
            ball = Vector((hx, -A["ball_y"] * H, A["ball_z"] * H))
            for name, h, t in ((f"thigh_{s}", hip, knee), (f"shin_{s}", knee, ankle), (f"foot_{s}", ankle, ball)):
                self.head[name], self.tail[name] = h, t
            # ground pivots of the rigid shoe: the back and front of the sole (build_characters
            # makes the sole SOLE_MARGIN longer than the upper at each end)
            self.heel = {**getattr(self, "heel", {}), s: Vector((hx, (A["heel_y"] + SOLE_MARGIN) * H, 0.0))}
            self.toe = {**getattr(self, "toe", {}), s: Vector((hx, -(A["toe_y"] + SOLE_MARGIN) * H, 0.0))}
        self.rest_q = {name: Quaternion() for name, _ in BONES}   # replaced by Blender's matrix_local

    def length(self, name):
        return (self.tail[name] - self.head[name]).length

    def dir(self, name):
        return (self.tail[name] - self.head[name]).normalized()

    def hinge(self, name):
        """Rest hinge axis of a limb bone: the part of X perpendicular to the bone."""
        return ortho(X, self.dir(name))


class Pose:
    """Bone rotations (parent-carried armature axes) plus the pelvis offset (armature space)."""

    def __init__(self):
        self.rot = {name: Quaternion() for name, _ in BONES}
        self.offset = Vector((0, 0, 0))

    def add(self, name, x=0.0, y=0.0, z=0.0):
        """Compose a rotation (degrees about armature X, Y, Z) onto a bone."""
        self.rot[name] = euler_deg(x, y, z) @ self.rot[name]

    def copy(self):
        p = Pose()
        p.rot = {k: q.copy() for k, q in self.rot.items()}
        p.offset = self.offset.copy()
        return p


def fk(sk, pose):
    """World rotation and head position of every bone."""
    D, P = {}, {}
    for name, parent in BONES:
        R = pose.rot[name]
        if parent is None:
            D[name], P[name] = R.copy(), sk.head[name].copy()
            continue
        D[name] = D[parent] @ R
        P[name] = P[parent] + D[parent] @ (sk.head[name] - sk.head[parent])
        if name == "pelvis":
            P[name] = P[name] + pose.offset
    return D, P


def two_bone(root, target, L1, L2, pole, u0, n0, bend):
    """Analytic two-bone IK. Returns world rotations of both bones and the middle joint.

    u0 and n0 are the rest direction and hinge axis of the (straight) limb; the middle joint
    bends toward pole; bend is +1 for a knee (hinge = pole x reach) and -1 for an elbow."""
    w = target - root
    d = min(max(w.length, abs(L1 - L2) + 1e-4), (L1 + L2) * 0.99999)
    wn = w.normalized()
    s = pole - wn * pole.dot(wn)
    if s.length < 1e-6:
        s = n0.cross(wn)
    s.normalize()
    cb = (L1 * L1 + d * d - L2 * L2) / (2.0 * L1 * d)
    beta = math.acos(min(max(cb, -1.0), 1.0))
    joint = root + (wn * math.cos(beta) + s * math.sin(beta)) * L1
    end = root + wn * d
    n = s.cross(wn).normalized() * bend
    F0t = frame(u0, n0).transposed()
    Du = (frame((joint - root).normalized(), n) @ F0t).to_quaternion()
    Dl = (frame((end - joint).normalized(), n) @ F0t).to_quaternion()
    return Du, Dl, joint


def aim(u0, p0, u1, p1):
    """World rotation taking rest direction u0 and side axis p0 onto u1 and p1."""
    u1 = u1.normalized()
    return (frame(u1, ortho(p1, u1)) @ frame(u0, ortho(p0, u0)).transposed()).to_quaternion()


def leg_ik(sk, pose, side, ankle, pitch_deg=0.0):
    """Put the ankle at a point (armature space) with the foot pitched about X; knee forward."""
    D, P = fk(sk, pose)
    th, sh, ft = f"thigh_{side}", f"shin_{side}", f"foot_{side}"
    pole = D["pelvis"] @ Vector((0, -1, 0))
    Du, Dl, _ = two_bone(P[th], ankle, sk.length(th), sk.length(sh), pole, sk.dir(th), sk.hinge(th), 1.0)
    pose.rot[th] = D["pelvis"].inverted() @ Du
    pose.rot[sh] = Du.inverted() @ Dl
    pose.rot[ft] = Dl.inverted() @ euler_deg(pitch_deg)


def arm_ik(sk, pose, side, wrist, pole, hand_dir=None, palm=None):
    """Put the wrist at a point with the elbow toward pole; optionally aim the hand."""
    D, P = fk(sk, pose)
    ua, fa, hd = f"upperarm_{side}", f"forearm_{side}", f"hand_{side}"
    Du, Dl, _ = two_bone(P[ua], wrist, sk.length(ua), sk.length(fa), pole.normalized(), sk.dir(ua), sk.hinge(ua), -1.0)
    pose.rot[ua] = D["chest"].inverted() @ Du
    pose.rot[fa] = Du.inverted() @ Dl
    if hand_dir is not None:
        palm0 = sk.hinge(hd) * -SIGN[side]
        pose.rot[hd] = Dl.inverted() @ aim(sk.dir(hd), palm0, hand_dir, palm)


def plant_feet(sk, pose, widen=0.0):
    """Keep both feet flat at their rest spots (optionally wider) while the pelvis moves."""
    for s, sg in SIGN.items():
        a = sk.head[f"foot_{s}"].copy()
        a.x += sg * widen
        leg_ik(sk, pose, s, a)


def stoop(pose, deg):
    """A character's standing stoop: the back rounds forward, the head comes back up."""
    if deg:
        pose.add("spine", x=0.45 * deg)
        pose.add("chest", x=0.55 * deg)
        pose.add("neck", x=-0.45 * deg)
        pose.add("head", x=-0.4 * deg)


def apply_hold(pose, hold):
    """Override the arm that holds a prop (degrees about X, Y, Z per bone). An arm is holding
    when any of its three bones is posed; then all three take the hold, zeros included."""
    if hold:
        for s in SIGN:
            names = (f"upperarm_{s}", f"forearm_{s}", f"hand_{s}")
            if any(any(hold[n]) for n in names):
                for n in names:
                    pose.rot[n] = euler_deg(*hold[n])


class Motion:
    """Everything a clip needs about one character: skeleton, tuning, pose options, body sizes."""

    def __init__(self, sk, tune, row, body):
        self.sk, self.tune, self.row, self.body = sk, tune, row, body
        self.hold = tune["holds"][row["pose"]["hold"]] if row["pose"]["hold"] else None
        self.stoop = row["pose"]["stoop_deg"]
        self.walk_cycle_s = row["walk_cycle_s"] or tune["walk"]["cycle_s"]

    def frames(self, clip):
        """Number of frames in a loop (the last key equals the first, so N + 1 keys)."""
        fps = self.tune["fps"]
        length = self.walk_cycle_s if clip == "walk" else self.tune[clip]["length_s"]
        return max(1, round(length * fps))

    def poses(self, clip):
        """Poses for keys 0..N; key N is an exact copy of key 0, so every loop is seamless."""
        n = self.frames(clip)
        if clip == "walk":
            out = self._walk_all(n)
        else:
            make = getattr(self, "_" + clip)
            out = [make(i / self.tune["fps"], i / n) for i in range(n)]
        out.append(out[0].copy())
        return out

    # --------------------------------------------------------------------- shared pieces

    def _upper(self, pose):
        stoop(pose, self.stoop)

    def _arms_relaxed(self, pose, swing_l=0.0, swing_r=0.0, elbow_l=8.0, elbow_r=8.0):
        pose.add("upperarm_l", x=swing_l)
        pose.add("upperarm_r", x=swing_r)
        pose.add("forearm_l", x=-elbow_l)
        pose.add("forearm_r", x=-elbow_r)
        pose.add("hand_l", x=-4.0)
        pose.add("hand_r", x=-4.0)

    # --------------------------------------------------------------------- clips

    def _idle(self, t, ph):
        c = self.tune["idle"]
        w = 2.0 * math.pi * ph
        p = Pose()
        p.offset = Vector((c["sway_m"] * math.sin(w), 0.0, -c["knee_drop_m"]))
        p.add("pelvis", y=-c["sway_roll_deg"] * math.sin(w))
        p.add("spine", y=0.6 * c["sway_roll_deg"] * math.sin(w))
        p.add("chest", y=0.4 * c["sway_roll_deg"] * math.sin(w))
        breath = 0.5 - 0.5 * math.cos(w)
        p.add("chest", x=-c["breath_deg"] * breath)
        p.add("neck", x=0.6 * c["breath_deg"] * breath)
        a, b, cc, d = c["head_turn_s"]
        turn = c["head_turn_deg"] * (smooth((t - a) / (b - a)) - smooth((t - cc) / (d - cc)))
        p.add("neck", z=0.4 * turn)
        p.add("head", z=0.6 * turn, x=-0.08 * abs(turn))
        self._upper(p)
        plant_feet(self.sk, p)
        e = c["elbow_deg"]
        self._arms_relaxed(p, 1.0 * math.sin(w), -1.0 * math.sin(w), e + breath, e + breath)
        apply_hold(p, self.hold)
        return p

    def _walk_pose(self, ph, dz):
        """The pose at phase ph (0..1) of the walk with the pelvis dropped by dz metres."""
        c, sk = self.tune["walk"], self.sk
        w = 2.0 * math.pi * ph
        yaw, roll = -c["hip_yaw_deg"] * math.cos(w), -c["hip_roll_deg"] * math.sin(w)
        p = Pose()
        p.offset = Vector((c["hip_sway_m"] * math.sin(w), 0.0, dz))
        p.add("pelvis", y=roll, z=yaw)
        p.add("spine", x=c["lean_deg"], y=-0.6 * roll, z=-0.5 * yaw)
        p.add("chest", y=-0.3 * roll, z=-0.7 * yaw)
        p.add("neck", y=-0.05 * roll, z=0.1 * yaw)
        p.add("head", x=-c["lean_deg"], y=-0.05 * roll, z=0.1 * yaw)
        self._upper(p)
        return p

    def _foot_path(self, side, ph):
        """Ankle target (armature space) and foot pitch for one leg at walk phase ph."""
        c, sk, H = self.tune["walk"], self.sk, self.sk.H
        T, v = self.walk_cycle_s, c["speed_m_s"]
        s = c["stance_fraction"]
        D = v * s * T
        p = (ph + (0.0 if side == "l" else 0.5)) % 1.0
        ankle0 = sk.head[f"foot_{side}"].copy()
        x = ankle0.x * c["step_width"]
        heel_rel = sk.heel[side] - ankle0          # sole's back edge (heel strike pivot)
        toe_rel = sk.toe[side] - ankle0            # sole's front edge (the heel peels about it)

        def stance(u):
            yflat = -c["front_fraction"] * D + D * u
            flat = Vector((x, yflat, ankle0.z))
            zone = 0.15
            if u < zone:
                pitch = -c["heel_strike_deg"] * (1.0 - smooth(u / zone))
                pivot = flat + heel_rel
                return pivot + euler_deg(pitch) @ (-heel_rel), pitch
            pf = c["peel_fraction"]
            if u > 1.0 - pf:
                pitch = c["heel_peel_deg"] * smooth((u - (1.0 - pf)) / pf)
                pivot = flat + toe_rel
                return pivot + euler_deg(pitch) @ (-toe_rel), pitch
            return flat, 0.0

        if p < s:
            return stance(p / s)
        q = (p - s) / (1.0 - s)
        a0, pitch0 = stance(1.0)
        a1, pitch1 = stance(0.0)
        m = v * (1.0 - s) * T                     # body-frame foot speed at lift-off and touch-down
        h00, h10, h01, h11 = 2 * q ** 3 - 3 * q ** 2 + 1, q ** 3 - 2 * q ** 2 + q, -2 * q ** 3 + 3 * q ** 2, q ** 3 - q ** 2
        y = h00 * a0.y + h10 * m + h01 * a1.y + h11 * m
        e = smooth(q)
        z = a0.z + (a1.z - a0.z) * e + c["foot_lift_m"] * (H / 1.8) * math.sin(math.pi * q)
        return Vector((x, y, z)), pitch0 + (pitch1 - pitch0) * e

    def _walk_all(self, n):
        c, sk = self.tune["walk"], self.sk
        reach = (sk.length("thigh_l") + sk.length("shin_l")) * 0.99999
        drops, feet = [], []
        for i in range(n):
            ph = i / n
            p = self._walk_pose(ph, 0.0)
            _, P = fk(sk, p)
            f = {s: self._foot_path(s, ph) for s in SIGN}
            allowed = []
            for s in SIGN:
                hip, (ank, _) = P[f"thigh_{s}"], f[s]
                horiz2 = (ank.x - hip.x) ** 2 + (ank.y - hip.y) ** 2
                allowed.append(ank.z + math.sqrt(max(reach * reach - horiz2, 0.0)) - hip.z)
            drops.append(min(allowed) - c["knee_margin_m"])
            feet.append(f)
        for _ in range(2):                         # soften the kinks where the stance leg changes
            drops = [0.25 * drops[i - 1] + 0.5 * drops[i] + 0.25 * drops[(i + 1) % n] for i in range(n)]
        out = []
        for i in range(n):
            ph = i / n
            w = 2.0 * math.pi * ph
            p = self._walk_pose(ph, drops[i])
            for s in SIGN:
                ank, pitch = feet[i][s]
                leg_ik(sk, p, s, ank, pitch)
            e0, e1 = c["elbow_deg"]
            sw = c["arm_swing_deg"]
            self._arms_relaxed(p, sw * math.cos(w), -sw * math.cos(w),
                               e0 + (e1 - e0) * (1 - math.cos(w)) / 2, e0 + (e1 - e0) * (1 + math.cos(w)) / 2)
            apply_hold(p, self.hold)
            out.append(p)
        return out

    def _talk(self, t, ph):
        c, sk = self.tune["talk"], self.sk
        w = 2.0 * math.pi * ph
        p = Pose()
        p.offset = Vector((c["sway_m"] * math.sin(w), 0.0, -self.tune["idle"]["knee_drop_m"]))
        p.add("pelvis", y=-1.0 * math.sin(w))
        p.add("chest", z=c["turn_deg"] * math.sin(w), y=0.6 * math.sin(w))
        nod = c["nod_deg"] * (0.5 - 0.5 * math.cos(2 * w + 0.6))
        p.add("neck", x=0.4 * nod)
        p.add("head", x=0.6 * nod, z=-0.5 * c["turn_deg"] * math.sin(w))
        self._upper(p)
        plant_feet(sk, p)
        g, e, tw = c["gesture_deg"], c["elbow_deg"], c["twist_deg"]
        for s, sg, k, lag in (("r", -1.0, 1.0, 0.0), ("l", 1.0, 0.45, 1.3)):
            beat = math.sin(2 * w + lag)
            p.add(f"upperarm_{s}", x=-k * (0.9 * g + 0.35 * g * math.sin(w + lag)), y=-sg * k * 8.0)
            flex = k * (e + 0.25 * e * beat) + (1 - k) * 10.0
            twist = Quaternion(sk.dir(f"forearm_{s}"), math.radians(-sg * k * tw * (0.5 + 0.5 * beat)))
            p.rot[f"forearm_{s}"] = euler_deg(-flex) @ twist
            p.add(f"hand_{s}", x=-k * 12.0 * math.sin(2 * w + lag + 0.8))
        apply_hold(p, self.hold)
        return p

    def _guard(self, t, ph):
        c, sk, H, body = self.tune["guard"], self.sk, self.sk.H, self.body
        w = 2.0 * math.pi * ph
        p = Pose()
        p.offset = Vector((0.0, 0.0, -c["knee_drop_m"]))
        breath = 0.5 - 0.5 * math.cos(w)
        p.add("chest", x=-c["breath_deg"] * breath)
        scan = c["scan_deg"] * math.sin(w)
        p.add("neck", z=0.4 * scan)
        p.add("head", z=0.6 * scan)
        self._upper(p)
        plant_feet(sk, p, c["stance_widen_m"])
        if self.row["pose"]["guard"] == "clasped":
            # the bouncer's stance: hands folded in front of the belt, left hand over right
            thick = 2.0 * body["hand_half"] + 0.012
            for s, sg in SIGN.items():
                over = s == "l"
                wrist = Vector((sg * 0.045 * H, -(body["belt_front"] + body["forearm_r"] + 0.015 + (thick if over else 0.0)),
                                body["clasp_z"] - c["knee_drop_m"] + (0.0 if over else -0.02 * H)))
                arm_ik(sk, p, s, wrist, Vector((sg * 0.7, 1.0, 0.1)), Vector((-sg * 0.75, -0.15, -0.65)), Vector((0.0, 1.0, 0.0)))
        else:
            for s, sg in SIGN.items():
                wrist = Vector((sg * (body["hip_side"][s] + body["hand_half"] + 0.012), 0.015 * H,
                                body["hand_z"] - c["knee_drop_m"]))
                pole = Vector((sg * 1.0, 0.7, 0.1))
                arm_ik(sk, p, s, wrist, pole, Vector((0, -0.5, -0.87)), Vector((-sg, 0, 0)))
        apply_hold(p, self.hold)
        return p

    def _sit(self, t, ph):
        c, sk, body = self.tune["sit"], self.sk, self.body
        p = Pose()
        hip_z = sk.head["thigh_l"].z
        p.offset = Vector((0.0, 0.02 * sk.H, c["seat_height_m"] + body["seat_to_hip"] - hip_z))
        p.add("spine", x=0.5 * c["slouch_deg"])
        p.add("chest", x=0.3 * c["slouch_deg"])
        p.add("neck", x=-0.4 * c["slouch_deg"])
        p.add("head", x=-0.4 * c["slouch_deg"])
        self._upper(p)
        for s, sg in SIGN.items():
            hip = sk.head[f"thigh_{s}"]
            ankle = Vector((hip.x * 1.1, p.offset.y - 0.97 * sk.length(f"thigh_{s}"), sk.head[f"foot_{s}"].z))
            leg_ik(sk, p, s, ankle)
        D, P = fk(sk, p)
        for s, sg in SIGN.items():
            th = f"thigh_{s}"
            along = D[th] @ (sk.dir(th) * sk.length(th) * 0.55)
            up = D[th] @ ortho(Z, sk.dir(th))
            wrist = P[th] + along + up * (body["thigh_r"] + body["hand_half"] + 0.012) + Vector((sg * 0.01, 0, 0))
            wrist = wrist - D[th] @ sk.dir(th) * (sk.length(f"hand_{s}") * 0.45)
            arm_ik(sk, p, s, wrist, Vector((sg * 0.7, 1.0, 0.0)), D[th] @ sk.dir(th), Vector((0, 0, -1)))
        apply_hold(p, self.hold)
        return p
