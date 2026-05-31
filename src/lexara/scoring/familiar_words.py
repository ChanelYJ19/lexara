"""Familiar-word list for the Dale-Chall difficulty heuristic.

APPROXIMATION
-------------
The official New Dale-Chall formula uses a curated list of ~3,000 words known
to ~80% of 4th graders. Shipping and licensing that exact list is out of scope
for v1, so we approximate "familiar" using a high-frequency English word set
(the few hundred most common function and content words, plus common
inflections). This makes our ``difficult_word_count`` a *reasonable estimate*
rather than an exact Dale-Chall reproduction.

To upgrade later: drop the full 3,000-word list into ``DALE_CHALL_FAMILIAR``
(load from a data file) and no other code changes are required.
"""

from __future__ import annotations

# High-frequency English words. Intentionally compact; expand for accuracy.
_BASE_FAMILIAR = """
a about above across act add after again against age ago air all almost alone
along already also always am among amount an and animal another answer any
anyone anything appear apple are area arm around as ask at ate away baby back
bad bag ball bank base be bear beautiful became because become bed been before
began begin behind being believe below beside best better between big bird bit
black blue boat body book born both box boy bread break bring brother brought
brown build built busy but buy by call came can cannot car care carry case cat
catch cause center certain chair chance change child children church city clean
clear close cloth cold color come common company complete cook cool corner could
country course cover cried cross cry cup cut dark day dead deal dear death decide
deep did die different dinner do does dog done don't door down draw dream dress
drink drive drop dry during each ear early earth east easy eat egg eight either
else end enough enter even evening ever every everyone everything example eye
face fact fall family far farm fast father fear feed feel feet fell felt few field
fight figure fill find fine finger finish fire first fish five floor flower fly
follow food foot for force found four free fresh friend from front full fun funny
gave get girl give glad go God gold gone good got grass great green grew ground
group grow guess had hair half hand happen happy hard has hat have he head hear
heard heart heavy held hello help her here high hill him himself his hold hole
home hope horse hot hour house how however hundred hurt I ice idea if ill important
in inch into is it its itself job jump just keep kept key kind king knew know
known lady land large last late laugh lay lead learn least leave led left leg less
let letter life light like line list listen little live long look lost lot loud
love low made make man many mark market may maybe me mean meant meet men might mile
milk mind mine minute miss money month moon more morning most mother mountain mouth
move much music must my myself name near need never new next nice night no none nor
north nose not note nothing now number of off office often oh oil old on once one
only open or order other our out outside over own page paint paper part party pass
past pay people perhaps person pick picture piece place plain plan plant play please
point poor possible power present pretty problem pull put question quick quiet quite
rain ran reach read ready real reason red remember rest return rich ride right ring
river road rock room round rule run sad safe said same sat save saw say school sea
season seat second see seem seen self sell send sense sent serve set seven several
shall shape she ship shoe short should show side sight sign simple since sing sister
sit six size sleep slow small smell smile snow so some someone something sometimes
son song soon sound south space speak special spell spend spoke spot spring stand
star start state stay step still stone stood stop store story street strong such
sudden summer sun sure table take talk tall teach teacher tell ten than thank that
the their them themselves then there these they thing think third this those though
thought three through throw time to today together told too took top touch toward
town trade train tree trip trouble true try turn two under understand until up upon
us use usual very visit voice wait walk wall want war warm was wash watch water way
we wear week well went were west what wheel when where whether which while white who
whole whose why wide wife wild will win wind window winter wish with within without
woman women word work world would write wrong wrote yard year yellow yes yet you
young your yourself
""".split()

# Add a few common inflected forms generically so plurals/3rd-person don't all
# read as "difficult". This is heuristic, not exhaustive.
_INFLECTIONS: set[str] = set()
for _w in _BASE_FAMILIAR:
    _INFLECTIONS.add(_w + "s")
    _INFLECTIONS.add(_w + "ed")
    _INFLECTIONS.add(_w + "ing")

DALE_CHALL_FAMILIAR: frozenset[str] = frozenset(_BASE_FAMILIAR) | frozenset(
    _INFLECTIONS
)
