"""
precooked versions of functions in the VNIRSD programming manual
"""

from functools import partial

from vnirsd.dj_utils import djget, eta
from vnirsd.models import Sample

# define partially-evaluated convenience function
get_contains = partial(
    djget,
    model=Sample,
    value="",
    # the field value is model-specific! you can omit it if you don't want to
    # use the shortened call types in the next cell.
    field="sample_name",
    querytype='icontains'
)
# reorder arguments to prevent collisions
samples = eta(get_contains, "value", "field")


# factory version of this for different models
def make_getter(model):
    # crude heuristic
    model_name_field = [
        field for field in fields(model) if "name" in field
    ][0]
    getter = partial(
        djget,
        model=model,
        value="",
        field=model_name_field,
        querytype='icontains'
    )
    return eta(getter, "value", "field")
