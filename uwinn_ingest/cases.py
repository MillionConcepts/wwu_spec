KNOWN_BAD_SPLITS = (
    "4_BNNP_DandP_Vertex70_03.csv",
    "5_CRB_OX_Vertex70_and _merged_14.csv",
    "2_1_Pyroxenes_FTIR_refl_Bruker_01.csv",
    "2_3_PLG_iRaman_edit_01.csv",
    "11_Bas_ign_ASD_grainsize_phases_12.csv",
    "2_3_PLG_singegrain_EDIT_03.csv",
    "2_3_PLG_USGS_01.csv",
    "2_2_OLV_USGS_01.csv",
    "15_28_MIXES_EDIT_01.csv",
    "18_5_Synthetic_organics_Maya_UV_edit_01.csv",
    "5_CRB_OX_ASD_plus_Maya_EDIT_03.csv",
    "2_2_OLV_iRaman_01.csv",
    "40_Wagner_Hapke_spectra_edit_02.csv",
    "9_2_Magnetites_Wagner_archive_01.csv",
    "9_6_Oth_ox_Wagner_archive_01.csv",
    "9_5_ilm_Wagner_archive_01.csv",
    "16_6_14_METS_Abreu_CRs_edit_03.csv",
    "40_Wagner_Hapke_spectra_edit_01.csv",
    "16_6_METs_carb_chon_edit_Part3_02.csv",
    "11_Bas_ign_ASD_grainsize_phases_02.csv",
    "2_1_Pyroxenes_single_grain_refl_04.csv",
)
SPECTRAL_STOPWORDS = ["mastcam"]


def field_mapping(field):
    """map to VISOR metadata fields as possible"""
    lowered = field.lower().strip()
    translation = None
    if "geometry" in lowered:
        translation = "view_geom"
    elif "descrip" in lowered:
        translation = "sample_desc"
    elif "resolution" in lowered:
        translation = "resolution"
    elif "grain" in lowered:
        if "nm" in lowered:
            raise ValueError("oops check unit!")
        translation = "grain_size"
    # TODO: this one might be dangerous
    elif lowered in [
        "apollo sample id",
        "sample id",
        "sample #",
        "sample number",
    ]:
        translation = "sample_id"
    elif lowered in ["sample name", "sample", "Directory (yy/mm/dd)", "name"]:
        translation = "sample_name"
    elif "notes" in lowered:
        translation = "other"
    elif "comments" in lowered:
        translation = "sample_desc"
    elif "basename" in lowered:
        translation = "references"
    return field, translation
