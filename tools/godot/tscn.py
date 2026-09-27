"""Tiny writer for Godot 4 text scenes (.tscn) and resources (.tres).

Used by gen_scenes.py so that props, weapons and enemies built from primitives are defined
as readable Python data instead of hand-edited transforms.
"""
import os


class Raw(str):
    """A value emitted verbatim (e.g. ExtResource("1"), NodePath("x"))."""


def fmt(v):
    if isinstance(v, Raw):
        return str(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        s = repr(round(v, 6))
        return s
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(fmt(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{\n" + ",\n".join(f"{fmt(k)}: {fmt(x)}" for k, x in v.items()) + "\n}"
    raise TypeError(f"cannot format {v!r}")


def v3(x, y, z):
    return Raw(f"Vector3({fmt(float(x))}, {fmt(float(y))}, {fmt(float(z))})")


def v2(x, y):
    return Raw(f"Vector2({fmt(float(x))}, {fmt(float(y))})")


def color(r, g, b, a=1.0):
    return Raw(f"Color({fmt(float(r))}, {fmt(float(g))}, {fmt(float(b))}, {fmt(float(a))})")


def hexcolor(h, a=1.0):
    h = h.lstrip("#")
    return color(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def path(p):
    return Raw(f'NodePath("{p}")')


class _Doc:
    def __init__(self):
        self.ext = []
        self.sub = []
        self._ext_ids = {}
        self._n = 0

    def ext_res(self, type_, res_path):
        key = (type_, res_path)
        if key not in self._ext_ids:
            self._n += 1
            rid = f"{self._n}_{os.path.basename(res_path).split('.')[0][:12]}"
            self._ext_ids[key] = rid
            self.ext.append((type_, res_path, rid))
        return Raw(f'ExtResource("{self._ext_ids[key]}")')

    def sub_res(self, type_, **props):
        self._n += 1
        rid = f"{type_}_{self._n}"
        self.sub.append((type_, rid, props))
        return Raw(f'SubResource("{rid}")')

    def _header_blocks(self):
        out = []
        for type_, p, rid in self.ext:
            out.append(f'[ext_resource type="{type_}" path="{p}" id="{rid}"]')
        if self.ext:
            out.append("")
        for type_, rid, props in self.sub:
            out.append(f'[sub_resource type="{type_}" id="{rid}"]')
            for k, v in props.items():
                out.append(f"{k} = {fmt(v)}")
            out.append("")
        return out


class Scene(_Doc):
    def __init__(self, root_name, root_type=None, instance=None, **props):
        super().__init__()
        self.nodes = []
        self.root = root_name
        if instance:
            self.nodes.append((root_name, None, None, props, self.ext_res("PackedScene", instance), []))
        else:
            self.nodes.append((root_name, root_type, None, props, None, []))

    def node(self, name, type_, parent=".", groups=None, **props):
        self.nodes.append((name, type_, parent, props, None, groups or []))
        return name if parent == "." else f"{parent}/{name}"

    def instance(self, name, scene_path, parent=".", **props):
        self.nodes.append((name, None, parent, props, self.ext_res("PackedScene", scene_path), []))
        return name if parent == "." else f"{parent}/{name}"

    def set_root_groups(self, groups):
        n = self.nodes[0]
        self.nodes[0] = (n[0], n[1], n[2], n[3], n[4], groups)

    def save(self, file):
        lines = ["[gd_scene format=3]", ""]
        lines += self._header_blocks()
        for name, type_, parent, props, inst, groups in self.nodes:
            head = f'[node name="{name}"'
            if type_:
                head += f' type="{type_}"'
            if parent is not None:
                head += f' parent="{parent}"'
            if inst:
                head += f" instance={inst}"
            if groups:
                head += " groups=[" + ", ".join(f'"{g}"' for g in groups) + "]"
            head += "]"
            lines.append(head)
            for k, v in props.items():
                lines.append(f"{k} = {fmt(v)}")
            lines.append("")
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "w") as f:
            f.write("\n".join(lines))


class Resource(_Doc):
    def __init__(self, type_, **props):
        super().__init__()
        self.type = type_
        self.props = props

    def save(self, file):
        lines = [f'[gd_resource type="{self.type}" format=3]', ""]
        lines += self._header_blocks()
        lines.append("[resource]")
        for k, v in self.props.items():
            lines.append(f"{k} = {fmt(v)}")
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "w") as f:
            f.write("\n".join(lines) + "\n")
