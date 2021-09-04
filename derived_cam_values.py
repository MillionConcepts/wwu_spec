"""
a bunch of derived dictionaries relating to filters for quick parsing and easy
interpretation of operations on individual spectra
"""

from math import floor
from statistics import mean
from itertools import chain, combinations

from marslab.compatibility import WAVELENGTH_TO_FILTER


def make_cam_filter_dict(abbreviation):
    """
    form filter: wavelength dictionary for mastcam-family instruments
    """
    wave_dict = WAVELENGTH_TO_FILTER[
            abbreviation
        ]['L'] | WAVELENGTH_TO_FILTER[abbreviation]['R']
    return {
        name.lower(): wavelength
        for wavelength, name in
        sorted(wave_dict.items())
    }


def make_cam_filter_pairs(abbreviation):
    """
    form list of pairs of close filters for mastcam-family instruments
    """
    filter_dict = make_cam_filter_dict(abbreviation)
    return tuple([
        (filter_1, filter_2)
        for filter_1, filter_2 in combinations(filter_dict, 2)
        if abs(filter_dict[filter_1] - filter_dict[filter_2]) <= 5
    ])


# at least for MASTCAM, the set of virtual filters === the set of pairs of
# the virtual mean reflectance in an ROI for a virtual filter is the
# arithmetic mean of the mean reflectance values in that ROI for the two
# real filters in its associated pair. the nominal band center of a virtual
# filter is the arithmetic mean of the nominal band centers of the two real
# filters in its associated pair.

def make_virtual_filters(abbreviation):
    """
    form mapping from close filter names to wavelengths for mastcam-family
    """
    filter_dict = make_cam_filter_dict(abbreviation)
    filter_pairs = make_cam_filter_pairs(abbreviation)
    return {
        pair[0].lower() + "_" + pair[1].lower():
            floor(mean([filter_dict[pair[0]], filter_dict[pair[1]]]))
        for pair in filter_pairs
    }


def make_virtual_filter_mapping(abbreviation):
    """
    form mapping from close filter names to filter pairs for mastcam-family
    """
    return {
        pair[0].lower() + "_" + pair[1].lower(): pair
        for pair in make_cam_filter_pairs(abbreviation)
    }


def make_canonical_averaged_filters(abbreviation):
    filter_dict = make_cam_filter_dict(abbreviation)
    virtual_filters = make_virtual_filters(abbreviation)
    virtual_filter_mapping = make_virtual_filter_mapping(abbreviation)
    retained_filters = {
        filt: filter_dict[filt] for filt in filter_dict
        if filt not in chain.from_iterable(virtual_filter_mapping.values())
    }
    caf = retained_filters | virtual_filters
    return {
        filt: caf[filt]
        for filt in sorted(caf, key=lambda x: caf[x])
    }


DERIVED_CAM_ABBREVIATIONS = ['MCAM', 'ZCAM']
DERIVED_CAM_DICT = {
    abbrev: {
        'filter_dict': make_cam_filter_dict(abbrev),
        'virtual_filters': make_virtual_filters(abbrev),
        'virtual_filter_mapping': make_virtual_filter_mapping(abbrev),
        'canonical_averaged_filters': make_canonical_averaged_filters(abbrev)
    }
    for abbrev in DERIVED_CAM_ABBREVIATIONS
}
