import os
from pathlib import Path

import numpy as np
from django.core.exceptions import ValidationError
from rich import print as rprint

from uwinn_ingest.ingest_uwinn import (
    read_uwinn_split,
    logger,
    format_headers,
    translate_headers,
)

from uwinn_ingest.cases import check_split_goodness

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wwu_spec.settings")
import django

django.setup()
from django.core.management import call_command


# debug function
def restrict_to_things(things):
    def thing_in_things(thing):
        return thing in things

    return thing_in_things


# ing = pd.read_csv('uwinn_split_ingest (copy).csv', header=None)
# ing = ing.drop(columns=1)
# ing.columns = ['time', 'level', 'file', 'msg_type', 'field_1', 'field_2']
# errs = ing.loc[ing['level'] == 'ERROR']['file'].values


def ingest_splits(splits, db):
    for ix, split in enumerate(splits):
        # debug statement
        # if ix < 959:
        #     continue
        # check_split_goodness = lambda thing: "5_CRB_OX_ASD_and_or_Vertex 70ED_01.csv" == thing
        # if "Synthetic_organics" not in split.name:
        #     continue
        if check_split_goodness(split.name) is False:
            rprint(
                f"[pale_violet_red1]skipping {split.name}[/pale_violet_red1]"
            )
            continue
        rprint(f"[bold]{ix}: {split.name}[/bold]")
        try:
            headers, ref_block, wavelengths = read_and_parse_split(split)
        except KeyboardInterrupt:
            raise
        except Exception as ex:
            logger.error(f'{split.name},{type(ex)},{ex}')
            rprint(f"[red]{type(ex)},{ex}")
            continue
        sample_errors = []
        successes = 0
        for row_ix in range(len(headers)):
            try:
                ingest_sample_row(
                    headers, ref_block, row_ix, split, db, wavelengths
                )
                successes += 1
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                header = headers.iloc[row_ix]
                sample_errors.append(
                    f'{header["filename"]},{header["sample_id"]},{ex}'
                )
        for error in sample_errors:
            logger.error(error)
            rprint(f"[red]{error}")
        rprint(
            f"[green bold]successfully ingested {successes}/"
            f"{len(headers)} samples"
        )


def ingest_sample_row(headers, ref_block, row_ix, split, db, wavelengths):
    metadata = headers.iloc[row_ix].to_dict() | {
        "origin": db,
        "released": True,
    }
    logger.info(
        f'{metadata["filename"]},{metadata["sample_id"]},'
        f'{metadata["sample_name"]}'
    )
    ref = ref_block[row_ix]
    if len(np.nonzero(ref)[0]) == 0:
        logger.warning(
            f"{split.name},dropped row {row_ix} bc identically 0 ref"
        )
        return
    data = {"reflectance": np.vstack([wavelengths, ref]).T}
    sample = Sample(**(data | metadata))
    sample.clean()
    sample.save()


def read_and_parse_split(split):
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
    if "sample_name" not in headers:
        rprint(f"[dark_orange bold]sample name missing[/dark_orange bold]")
        logger.warning(f"{split.name},interp,sample name missing,")
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
    return headers, reflectance_block, wavelengths


if __name__ == "__main__":
    Path("uwinn_split_ingest.csv").unlink(missing_ok=True)
    Path("data/spectra.sqlite3").unlink(missing_ok=True)
    call_command("migrate", database="spectra", verbosity=0)
    from visor.models import Database, Sample

    UWINN = Database.objects.filter(short_name="uwinn")
    if len(UWINN) == 0:
        UWINN = Database(name="uwinn", short_name="uwinn", released=True)
        INSERT = (UWINN.clean(), UWINN.save())
    else:
        UWINN = UWINN[0]
    SPLIT_PATH = Path("uwinn_ingest/post_split_edits")
    SPLITS = list(SPLIT_PATH.iterdir())
    ingest_splits(SPLITS, UWINN)
