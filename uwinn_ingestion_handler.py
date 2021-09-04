import os
from pathlib import Path

import numpy as np
from rich import print as rprint

from uwinn_ingest.ingest_uwinn import (
    read_uwinn_split,
    logger,
    format_headers,
    translate_headers,
    check_split_goodness,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wwu_spec.settings")
import django

django.setup()
from visor.models import Database, Sample


# debug function
def restrict_to_things(things):
    def thing_in_things(thing):
        return thing in things
    return thing_in_things


# ing = pd.read_csv('uwinn_split_ingest (copy).csv', header=None)
# ing = ing.drop(columns=1)
# ing.columns = ['time', 'level', 'file', 'msg_type', 'field_1', 'field_2']
# errs = ing.loc[ing['level'] == 'ERROR']['file'].values

uwinn = Database.objects.get(name__icontains="winnipeg")
split_path = Path("uwinn_ingest/All_UWinn_splits_070621")
splits = list(split_path.iterdir())
for split in splits:
    # debug statement
    check_split_goodness = restrict_to_things(['22_5_MASTER_NOMAD_runs_3_NOMAD_RUN3_before_and_after_ASD_11.csv'])
    if check_split_goodness(split) is False:
        continue
    try:
        rprint(f"[black]{split.name}")
        (
            fields,
            metadata,
            wavelengths,
            reflectance,
            split_warnings,
        ) = read_uwinn_split(split)
        for warning in split_warnings:
            rprint(f"[red]{warning}")
            logger.warning(f'{split.name},"{warning}"')
        headers = format_headers(metadata, fields)
        headers = translate_headers(headers, wavelengths, split.name)
        reflectance_block = reflectance.dropna(axis=1).values.T
        wavelengths = wavelengths.dropna().values
        if len(headers) > reflectance_block.shape[0]:
            headers = headers.iloc[: reflectance_block.shape[0]]
            logger.info(f"{split.name},trailing columns truncated")
        assert reflectance_block.shape == (
            len(headers),
            len(wavelengths),
        ), f"{reflectance_block.shape} != {len(wavelengths)} {len(headers)}"
        if (reflectance_block.max() > 5) and ("%" in str(metadata)):
            reflectance_block /= 100
            logger.info(f"{split.name},unit change,percent reflectance")
        for row_ix in range(len(headers)):
            ref = reflectance_block[row_ix]
            if len(np.nonzero(ref)[0]) == 0:
                logger.warning(
                    f"{split.name},dropped row {row_ix} bc identically 0 ref"
                )
                continue
            data = {
                "reflectance": np.vstack(
                    [wavelengths, reflectance_block[row_ix]]
                ).T
            }
            metadata = headers.iloc[row_ix].to_dict() | {
                "origin": uwinn,
                "released": True,
            }

            sample = Sample(**(data | metadata))
            sample.clean()
            sample.save()
        rprint("[green bold]successful")
    except KeyboardInterrupt:
        raise
    except Exception as ex:
        logger.error(f'{split.name},{type(ex)},"{ex}"')
        rprint(f"[red]{type(ex)},{ex}")
