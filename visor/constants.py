# numerical bounding values, in nm, for named wavelength ranges used in the
# search interface. note that we elsewhere assume that there are no large
# gaps in wavelength coverage within a given lab spectrum; i.e., that if a
# spectrum has both UVA and NIR, it also has VIS. if this becomes a bad
# assumption, we will need to modify it.
WAVELENGTH_RANGES = {
    "UVB": [0, 314],
    "UVA": [315, 399],
    "VIS": [400, 749],
    "NIR": [750, 2500],
    "MIR": [2501, 10000000],
}