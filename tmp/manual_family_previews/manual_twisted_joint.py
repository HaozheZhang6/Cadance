from cadquery import Sketch
from cadquery.func import *
from cadquery.vis import show

th = 4
sk1 = Sketch().rect(10, 20).moved(x=5).circle(10).clean().circle(5, "s")
fsk1 = sk1.faces().val().moved(z=-th / 2)
part1 = extrude(fsk1, (0, 0, th))
part2 = part1.mirror("YZ").moved(x=45, rx=-90)

f1 = part1.faces(">X")
f2 = part2.faces("<X")
f2 = Face(f2.wrapped.Reversed())

eps = 1e-3
twist = loft(
    f1.moved(x=-eps),
    f1,
    f2,
    f2.moved(x=eps),
    parametrization="chordal",
    compat=False,
)

result = part1 + twist + part2
show(result, width=500, height=500)