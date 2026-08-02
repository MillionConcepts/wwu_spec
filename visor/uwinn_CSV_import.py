from pathlib import Path
import pandas as pd
import django
import os

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'wwu_spec.settings')
django.setup()

from visor.models import Sample, Database

print("number of samples in DB", Sample.objects.count())

# matching excels decimal point, but in diplay only the full precision remains intact
pd.set_option("display.float_format", "{:.6f}".format)

CSV_path = r"C:\Users\12048\PycharmProjects\Parser\output\1_Master_synthetic_elemental_fo_CTAPE_site_mar_2_2021\1_ASD_and_Vertex70edit__AA-BB.csv"
df = pd.read_csv(CSV_path)
first_col = df.columns[0]

axis_rows = df[df[first_col].astype(str).str.contains("wavelength (nm)", case=False, na=False, regex=False)]
print("First Column: ", first_col)
print("Spectrum: ", list(df.columns[1:]))
print("Axis rows: ")
print(axis_rows[[first_col]])

axis_index = axis_rows.index[0]

metadata = df.iloc[:axis_index]
data = df.iloc[axis_index + 1:]
data = data.apply(pd.to_numeric, errors="coerce")

print("metadata rows: ", len(metadata))
print("Data rows: ", len(data))
print("first couple metdata data labels: ")
print(metadata[first_col].head(20).to_list())
print("first few wavelengths: ")
print(data.head())

print("\nAvailable DB:)")

for database in Database.objects.all():
    print(database.id,database.name, database.short_name)

for spectrum_type in df.columns[1:]:
    metadata_dictionary = dict(
        zip(
            metadata[first_col],
            metadata[spectrum_type]python manage.py
        )
    )
    # testing to make sure my dictionary is being made correctly and that i can retrieve a value from it can remove later
    # print(metadata_dictionary)
    # print("Directory:", metadata_dictionary.get("directory"))
    # print("Sample #:", metadata_dictionary.get("sample #"))
    spectrum_data = data[[first_col, spectrum_type]]
    reflectance = spectrum_data.values.tolist()


# making sure that it maps correctly into Django by creating a test object
    sample = Sample(
        sample_id=spectrum_type,
        original_sample_id=spectrum_type,
        reflectance=reflectance,
        sample_number=metadata_dictionary.get("sample #"),
        directory=metadata_dictionary.get("directory"),
        sample_desc=metadata_dictionary.get("sample description"),
        grain_size=metadata_dictionary.get("grain size"),
        view_geom=metadata_dictionary.get("viewing geometry"),
        integration_time=metadata_dictionary.get("integration time"),
        number_of_spectrum_avg=metadata_dictionary.get("# of spectrum avg"),
        atmosphere=metadata_dictionary.get("atmosphere"),
        sample_temperature=metadata_dictionary.get("sample temperature"),
        sample_cup=metadata_dictionary.get("sample cup"),
        light_source=metadata_dictionary.get("light source"),
        depolarizer=metadata_dictionary.get("depolarizer"),
        sample_spun=metadata_dictionary.get("sample spun"),
        pickup_fiber=metadata_dictionary.get("pickup fiber"),
        approx_measured_area=metadata_dictionary.get("approximate measured area"),
        sample_prep=metadata_dictionary.get("sample prep"),
        spectralon_correction_file=metadata_dictionary.get("spectralon correction file"),


        )
    print(
        spectrum_type,
        "| sample #:",
        sample.sample_number,
        "| Directory:",
        sample.directory,
        "| Data rows:",
        len(spectrum_data)
)
# checking all of it is being read without printing it
print("\ntotal spectra processed: ", len(df.columns[1:]))
