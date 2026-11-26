import cadquery as cq


def _box(p):
    return (
        cq.Workplane("XY")
        .box(p.v("width"), p.v("depth"), p.v("height"), centered=(True, True, False))
        .faces(">Z").workplane().hole(p.v("hole_diameter"))
    )


def parts(p):
    return {"caixa": _box(p)}


def assembly(p):
    return {"caixa": _box(p)}
