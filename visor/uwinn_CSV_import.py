from pathlib import Path
import pandas as pd
import django
import os


os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'wwu_spec.settings')
django.setup()

from visor.models import Sample, Database

#matching excels decimal point, but in diplay only the full precision remains intact
pd.set_option("display.float_format", "{:.6f}".format)

CSV_path= r"C:\Users\12048\PycharmProjects\Parser\output\1_Master_synthetic_elemental_fo_CTAPE_site_mar_2_2021\1_ASD_and_Vertex70edit__AA-BB.csv"
df = pd.read_csv(CSV_path)
first_col = df.columns[0]

axis_rows= df[df[first_col].astype(str).str.contains("wavelength (nm)", case=False, na=False, regex = False)]
print ("First Column: ", first_col)
print ("Spectrum: ", list (df.columns[1:]))
print ("Axis rows: ")
print (axis_rows[[first_col]])

axis_index = axis_rows.index[0]

metadata = df.iloc[:axis_index]
data = df.iloc [axis_index +1:]
data=data.apply(pd.to_numeric, errors= "coerce")

print ("metadata rows: ", len(metadata))
print ("Data rows: ", len(data))
print ("first couple metdata data labels: ")
print (metadata[first_col].head(20).to_list())
print ("first few wavelengths: ")
print (data.head())

spectrum_type= df.columns[1]

print ("Spectrum name: ")
print(spectrum_type)

print ("\nMetadata for this spectrum")
print (metadata[[first_col, spectrum_type]])
print("\nSpectral data for this spectrum: ")
print (data[[first_col, spectrum_type]].head())