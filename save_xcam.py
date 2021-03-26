import os

from clize import run
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wwu_spec.settings")
django.setup()

from visor.convert import ingest_xcam_roi_file



def ingest_xcam(path_to_file: str) -> None:
    """
    command-line wrapper for ingest_xcam_roi_file. ingests all spectra from a
    csv file containing ROI spectra from an xcam instrument into VISOR.
    assumes the file is _either_ a marslab format file (as produced by
    merspect_to_marslab) or a merspect-type file that merspect_to_marslab can
    ingest, with conventional naming format.

    :param path_to_file: path to .csv file
    """
    ingest_xcam_roi_file(path_to_file)


if __name__ == '__main__':
    run(ingest_xcam)
