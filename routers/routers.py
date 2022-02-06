import visor.models


def visor_splitter(model):
    if model == visor.models.FilterSet:
        return "filtersets"
    if model in [
        visor.models.Library,
        visor.models.SampleType,
        visor.models.Database,
        visor.models.Sample,
    ]:
        return "spectra"

    return None


class VisorRouter:
    """
    splits databases / filtersets, data, and auth into separate databases.
    """

    @staticmethod
    def db_for_read(model, **hints):
        """
        Attempts to read auth and contenttypes models go to auth_db.
        """
        return visor_splitter(model)

    @staticmethod
    def db_for_write(model, **hints):
        return visor_splitter(model)

    @staticmethod
    def allow_relation(_, __, **hints):
        return True
