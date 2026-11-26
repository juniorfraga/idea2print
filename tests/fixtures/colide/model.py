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
    # content_bloco overlaps the box walls on purpose
    return {"caixa": _box(p), "content_bloco": cq.Workplane("XY").box(38, 28, 10, centered=(True, True, False))}
