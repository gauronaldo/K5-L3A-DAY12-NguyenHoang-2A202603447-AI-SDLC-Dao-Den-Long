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
