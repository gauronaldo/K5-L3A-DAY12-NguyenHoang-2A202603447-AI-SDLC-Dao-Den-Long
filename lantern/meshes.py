"""Procedural low-poly meshes for the Panda3D client (no external assets). Panda3D is Z-up."""
import math

from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
                          GeomVertexWriter, NodePath)


def _build(name, verts, normals, tris):
    vdata = GeomVertexData(name, GeomVertexFormat.getV3n3(), Geom.UHStatic)
    vw, nw = GeomVertexWriter(vdata, "vertex"), GeomVertexWriter(vdata, "normal")
    for v, n in zip(verts, normals):
        vw.addData3(*v)
        nw.addData3(*n)
    prim = GeomTriangles(Geom.UHStatic)
    for a, b, c in tris:
        prim.addVertices(a, b, c)
    geom = Geom(vdata)
    geom.addPrimitive(prim)
    node = GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)


def cylinder(r, h, seg=24, name="cyl"):
    verts, norms, tris = [], [], []
    for i in range(seg + 1):
        a = 2 * math.pi * i / seg
        c, s = math.cos(a), math.sin(a)
        verts += [(r * c, r * s, 0), (r * c, r * s, h)]
        norms += [(c, s, 0), (c, s, 0)]
    for i in range(seg):
        k = 2 * i
        tris += [(k, k + 2, k + 1), (k + 1, k + 2, k + 3)]
    for z, nz in ((h, 1), (0, -1)):
        base = len(verts)
        verts.append((0, 0, z))
        norms.append((0, 0, nz))
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            verts.append((r * math.cos(a), r * math.sin(a), z))
            norms.append((0, 0, nz))
        for i in range(seg):
            t = (base, base + 1 + i, base + 2 + i)
            tris.append(t if nz > 0 else (t[0], t[2], t[1]))
    return _build(name, verts, norms, tris)


def cone(r, h, seg=24, name="cone"):
    verts, norms, tris = [], [], []
    slope = r / h
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        am = (a0 + a1) / 2
        n = (math.cos(am), math.sin(am), slope)
        base = len(verts)
        verts += [(r * math.cos(a0), r * math.sin(a0), 0), (r * math.cos(a1), r * math.sin(a1), 0), (0, 0, h)]
        norms += [n, n, n]
        tris.append((base, base + 1, base + 2))
    base = len(verts)
    verts.append((0, 0, 0))
    norms.append((0, 0, -1))
    for i in range(seg + 1):
        a = 2 * math.pi * i / seg
        verts.append((r * math.cos(a), r * math.sin(a), 0))
        norms.append((0, 0, -1))
    for i in range(seg):
        tris.append((base, base + 2 + i, base + 1 + i))
    return _build(name, verts, norms, tris)


def sphere(r, seg=16, rings=10, name="sphere"):
    verts, norms, tris = [], [], []
    for j in range(rings + 1):
        phi = math.pi * j / rings
        for i in range(seg + 1):
            th = 2 * math.pi * i / seg
            n = (math.sin(phi) * math.cos(th), math.sin(phi) * math.sin(th), math.cos(phi))
            verts.append((r * n[0], r * n[1], r * n[2]))
            norms.append(n)
    w = seg + 1
    for j in range(rings):
        for i in range(seg):
            a, b = j * w + i, (j + 1) * w + i
            tris += [(a, b, a + 1), (a + 1, b, b + 1)]
    return _build(name, verts, norms, tris)


def ring(r_in, r_out, seg=48, name="ring"):
    verts, norms, tris = [], [], []
    for i in range(seg + 1):
        a = 2 * math.pi * i / seg
        c, s = math.cos(a), math.sin(a)
        verts += [(r_in * c, r_in * s, 0), (r_out * c, r_out * s, 0)]
        norms += [(0, 0, 1), (0, 0, 1)]
    for i in range(seg):
        k = 2 * i
        tris += [(k, k + 1, k + 2), (k + 1, k + 3, k + 2)]
    return _build(name, verts, norms, tris)


def poly_mesh(faces, center, name="poly"):
    """Convex polygon faces (lists of Panda3D points); winding/normals are oriented away from `center`."""
    verts, norms, tris = [], [], []
    for f in faces:
        a, b, c = f[0], f[1], f[2]
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        fc = [sum(p[i] for p in f) / len(f) for i in range(3)]
        if sum((fc[i] - center[i]) * n[i] for i in range(3)) < 0:
            f = list(reversed(f))
            n = (-n[0], -n[1], -n[2])
        base = len(verts)
        for p in f:
            verts.append(tuple(p))
            norms.append(n)
        for i in range(1, len(f) - 1):
            tris.append((base, base + i, base + i + 1))
    return _build(name, verts, norms, tris)


def box(x0, x1, y0, y1, z0, z1, name="box"):
    p = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    faces = [[p[0], p[1], p[3], p[2]], [p[4], p[5], p[7], p[6]], [p[0], p[1], p[5], p[4]],
             [p[2], p[3], p[7], p[6]], [p[0], p[2], p[6], p[4]], [p[1], p[3], p[7], p[5]]]
    return poly_mesh(faces, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), name)


def annulus_sector(r0, r1, a0, a1, h, seg=24, name="sector"):
    """Solid ring sector in Panda3D XY (angles in degrees), from z=0 to z=h. Built per segment (each convex)."""
    faces = []
    for i in range(seg):
        t0 = math.radians(a0 + (a1 - a0) * i / seg)
        t1 = math.radians(a0 + (a1 - a0) * (i + 1) / seg)
        q = [(r * math.cos(t), r * math.sin(t)) for r, t in ((r0, t0), (r1, t0), (r1, t1), (r0, t1))]
        faces.append([(x, y, h) for x, y in q])
        faces.append([(x, y, 0) for x, y in q])
        faces.append([(q[1][0], q[1][1], 0), (q[2][0], q[2][1], 0), (q[2][0], q[2][1], h), (q[1][0], q[1][1], h)])
        faces.append([(q[0][0], q[0][1], 0), (q[3][0], q[3][1], 0), (q[3][0], q[3][1], h), (q[0][0], q[0][1], h)])
    # centre is the middle of the sector, so walls get outward normals segment by segment
    np_ = NodePath(name)
    for i, f in enumerate(faces):
        seg_i = i // 4
        tm = math.radians(a0 + (a1 - a0) * (seg_i + 0.5) / seg)
        rm = (r0 + r1) / 2
        poly_mesh([f], (rm * math.cos(tm), rm * math.sin(tm), h / 2)).reparentTo(np_)
    for a, inward in ((a0, 1), (a1, -1)):   # radial end caps
        t = math.radians(a)
        tc = math.radians(a + inward * 1.0)
        cap = [(r * math.cos(t), r * math.sin(t), z) for r, z in ((r0, 0), (r1, 0), (r1, h), (r0, h))]
        rm = (r0 + r1) / 2
        poly_mesh([cap], (rm * math.cos(tc), rm * math.sin(tc), h / 2)).reparentTo(np_)
    np_.flattenStrong()
    return np_


def wedge(p_foot_l, p_foot_r, p_top_l, p_top_r, h, name="ramp"):
    """Ramp from ground (foot edge, z=0) up to height h (top edge). Points are Panda3D (x, y)."""
    fl, fr = (p_foot_l[0], p_foot_l[1], 0), (p_foot_r[0], p_foot_r[1], 0)
    tl, tr = (p_top_l[0], p_top_l[1], h), (p_top_r[0], p_top_r[1], h)
    bl, br = (p_top_l[0], p_top_l[1], 0), (p_top_r[0], p_top_r[1], 0)
    faces = [[fl, fr, tr, tl], [fl, fr, br, bl], [bl, br, tr, tl], [fl, bl, tl], [fr, br, tr]]
    c = tuple(sum(p[i] for p in (fl, fr, tl, tr, bl, br)) / 6 for i in range(3))
    return poly_mesh(faces, c, name)
