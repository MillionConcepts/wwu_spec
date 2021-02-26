# utilities for interpreting and manipulating filter data

import json
from ast import literal_eval

from scipy import interpolate
from scipy import integrate
import pandas as pd
import numpy as np

import vnirsd.models


def interpolate_spectrum(
    ref_wavelengths: np.ndarray,
    input_wavelengths: np.ndarray,
    input_spectrum: np.ndarray,
) -> np.ndarray:
    interpolator = interpolate.interp1d(
        input_wavelengths,
        input_spectrum,
        kind="linear",
        bounds_error=False,
        fill_value=0,
    )
    output_spectrum = interpolator(ref_wavelengths)
    return output_spectrum


# noinspection PyTypeChecker
def normalize_power(
    spectrum: pd.Series,
    bins: np.ndarray
) -> pd.Series:
    return spectrum / integrate.trapz(spectrum.values, bins)


def convolve(
    radiance: np.ndarray,
    responsivity: np.ndarray,
    bins: np.ndarray,
    irradiance: bool = None,
) -> float:
    output = integrate.trapz(radiance * responsivity, bins)
    if irradiance is None:
        scale = 1
    else:
        scale = integrate.trapz(responsivity * irradiance, bins)
    return output / scale


def simulate_spectrum(
    sample: 'vnirsd.models.Sample',
    filterset: 'vnirsd.models.FilterSet',
    illuminated: bool = True,
) -> pd.DataFrame:
    # turn sample and illumination values into nice arrays

    filter_wavelengths = np.array(literal_eval(filterset.wavelengths))

    sample = np.array(literal_eval(sample.reflectance))
    sample_wavelengths = sample[:, 0]
    reflectance = sample[:, 1]

    # then use them to get sample radiance

    radiance = reflectance

    if filterset.illumination:
        if illuminated:
            illumination = np.array(literal_eval(filterset.illumination))
            illumination_wavelengths = illumination[:, 0]
            illumination_intensity = illumination[:, 1]

            # trim and interpolate solar (or whatever) spectrum to sample
            # spectrum
            irradiance = interpolate_spectrum(
                sample_wavelengths,
                illumination_wavelengths,
                illumination_intensity,
            )
            radiance = irradiance * reflectance

    # trim and interpolate radiance and irradiance to the bins of the filterset

    radiance = interpolate_spectrum(
        filter_wavelengths, sample_wavelengths, radiance
    )
    if illuminated:
        irradiance = interpolate_spectrum(
            filter_wavelengths,
            illumination_wavelengths,
            illumination_intensity,
        )
    else:
        irradiance = None

    # load filter bank

    filters = json.loads(filterset.filters)
    for filt in filters:
        filters[filt] = np.array(filters[filt])

    # if we hadn't already power-normalized the filters, we would normalize
    # them here but our filtersets should all be power-normalized at upload

    # create blank spectral response dataframe

    simulated_spectrum = (
        pd.DataFrame(
            np.vstack(literal_eval(filterset.filter_wavelengths)),
            columns=["filter", "wavelength"],
        )
        .astype({"wavelength": "float"})
        .sort_values(["wavelength"])
    )
    simulated_spectrum["response"] = 0

    # convolve reflectance with each of the filters (dividing illumination
    # back out) and stick it in the spectral response dataframe and toss out
    # irradiance if we don't want it

    for filt in filters:
        simulated_spectrum.loc[
            simulated_spectrum["filter"] == filt, "response"
        ] = convolve(radiance, filters[filt], filter_wavelengths, irradiance)
    return simulated_spectrum


# noinspection PyUnresolvedReferences
def make_filterset(
    name: str,
    filters: dict,
    bins: np.ndarray,
    waves: dict[str, float],
    illumination_path: str,
):
    """
    make_filterset below is a convenience function for generating filtersets.
    'filters' is a dict formatted like: {'filter_name':pandas dataframe of
    wavelength&response, 'filter_name_2'...} this might be generated by,
    for instance, using pd.read_csv on a directory of csv files,
    or by generating curves from a list of mathematical specifications,
    like: (for a dict DIST of {name:distribution} with distributions given as
    band center / FWHM)

    from scipy.stats import norm
    filters = {
        filt:pd.DataFrame(
               ([n,norm(DISTS[filt][0], DISTS[filt][1]/2.355).pdf(n)]
            for n in bins),
            columns=['wavelength','responsivity']
        )
        for filt in DISTS
    }

    'bins' is a reference array of wavelength bins; should span range of all
    filters in set. 'waves' gives the nominal center wavelength of each filter (
    used only for graphing convolved spectra); this is a dict formatted like
    {'filter_name':center_wavelength,'filter_name_2'...}
    """
    # 'filter' is a python builtin so not a good variable name
    for filt in filters:
        filters[filt] = pd.DataFrame(
            {
                "wavelength": bins,
                "responsivity": interpolate_spectrum(
                    bins,
                    filters[filt]["wavelength"],
                    filters[filt]["responsivity"],
                ),
            }
        )
    for filt in filters:
        filters[filt] = normalize_power(filters[filt]["responsivity"], bins)
    for filt in filters:
        filters[filt] = np.array(filters[filt]).tolist()
    illumination = str(
        pd.read_csv(
            illumination_path, names=["wavelength", "irradiance"]
        ).values.tolist()
    )
    filterset = {
        "name": name,
        "filters": json.dumps(filters),
        "wavelengths": str(bins.tolist()),
        "filter_wavelengths": str(waves.values.tolist()),
    }
    if illumination_path:
        filterset |= {"illumination": illumination}
    return vnirsd.models.FilterSet(**filterset)
