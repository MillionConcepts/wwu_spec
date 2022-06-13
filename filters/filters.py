import os

import pandas as pd

def decompose_mastcam_bayer(dataframe):
    red = dataframe.reindex(
        columns=['wavelength', 'red_responsivity']
    ).rename(
        columns={'red_responsivity': 'responsivity'}
    )
    green = dataframe.reindex(
        columns=['wavelength', 'green_responsivity']
    ).rename(
        columns={'green_responsivity': 'responsivity'}
    )
    blue = dataframe.reindex(
        columns=['wavelength', 'blue_responsivity']
    ).rename(
        columns={'blue_responsivity': 'responsivity'}
    )
    return {'bayer_red': red, 'bayer_green': green, 'bayer_blue': blue}


def import_mastcam_filters(path):
    filter_files = [file for file in os.listdir(path + 'mastcam') if
                    file[-3:] == 'txt']
    filters = {}
    for filter_file in filter_files:
        columns = ["wavelength", "red_responsivity", "green_responsivity",
                   "blue_responsivity"] \
            if 'bayer' in filter_file else ["wavelength", "responsivity"]
        filters[filter_file[:-4]] = \
            pd.read_csv(
                path + 'mastcam/' + filter_file,
                encoding='utf-8',
                sep="\t",
                names=columns
            )
    return filters
