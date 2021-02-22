"""
precooked versions of functions in the VNIRSD programming manual
"""

# define partially-evaluated convenience function
from functools import partial

from mars.dj_utils import djget, eta
from mars.models import Sample

get_contains = partial(
    djget,
    model=Sample,
    value = "",
    # the field value is model-specific! you can omit it if you don't want to
    # use the shortened call types in the next cell.
    field = "sample_name",
    querytype='icontains'
)
# reorder arguments to prevent collisions
samples = eta(get_contains, "value", "field")