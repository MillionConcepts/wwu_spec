import numpy as np
import pandas as pd
import os

color2type = {
    "light purple": "drill tailings",
    "dark purple": "dump piles",
    "light blue": "dusty rock",
    "teal": "dusty rock",
    "dark blue": "dusty rock",
    "light green": "DRT target",
    "dark green": "broken rock face",
    "bright red": "undisturbed soil",
    "dark red": "disturbed soil",
    "red": "undisturbed soil",
    "light cyan": "nodule-rich rock",
    "goldenrod": "veins",
    "sienna": None,
    "pink": None,
    "yellow": None,
}

wavelength_to_filter = {
    "MCAM": {
        "L": {
            482: "L0B",  #
            493: "L0B",  # Value has changed over time
            495: "L0B",  #
            554: "L0G",
            640: "L0R",
            527: "L1",
            445: "L2",
            751: "L3",
            676: "L4",
            867: "L5",
            1012: "L6",
        },
        "R": {
            482: "R0B",  #
            493: "R0B",  # Value has changed over time
            495: "R0B",  #
            551: "R0G",
            638: "R0R",
            527: "R1",
            447: "R2", #
            805: "R3",
            908: "R4",
            937: "R5",
            1013: "R6", #
        },
    },
    "ZCAM": {
        "L": {
            630: "L0R",
            544: "L0G",
            480: "L0B",
            800: "L1",
            754: "L2",
            677: "L3",
            605: "L4",
            528: "L5",
            442: "L6",
        },
        "R": {
            631: "R0R",
            544: "R0G1",
            480: "R0B",
            800: "R1",
            866: "R2",
            910: "R3",
            939: "R4",
            978: "R5",
            1022: "R6",
        },
    },
}


def parse_merspect_fn(fn):
    # Parse the MERSpect produced filename for obs information
    sol = int(fn.split("/")[-1].split("_")[0][3:])
    instrument = str.upper(fn.split("/")[-1].split("_")[1][:4])
    seq_id = fn.split("/")[-1].split("_")[1]
    return {"SOL": sol, "INSTRUMENT": instrument, "SEQ_ID": seq_id}


def get_unique_colors(csv):
    # Figure out the unique color names contained in the MERSpect output file
    colors = []
    for k in csv.keys():
        keycolor = " ".join(k.strip().split(" ")[:-2])
        for c in color2type.keys():
            if keycolor == c:
                colors += [c]
    return np.unique(colors)


def merspect_to_marslab(fn):
    csv = pd.read_csv(fn)
    # Get the sol, seq_id, instrument from the filename
    obsparams = parse_merspect_fn(fn)
    # Rename "# Wavelength (nm)" to "Wavelength (nm)"
    csv.rename(columns={"# Wavelength (nm)": "Wavelength"}, inplace=True)
    # Clean up column names
    [csv.rename(columns={k: k.strip()}, inplace=True) for k in csv.keys()]

    # We want the columns in order of ascending wavelength, regardless of instrument
    columns = {
        "MCAM": [
            "SOL",
            "SEQ_ID",
            "INSTRUMENT",
            "COLOR",
            "FEATURE",
            "FORMATION",
            "MEMBER",
            "FLOAT",
            "L2",
            "L2_ERR",
            "R2",
            "R2_ERR",
            "L0B",
            "L0B_ERR",
            "R0B",
            "R0B_ERR",
            "L1",
            "L1_ERR",
            "R1",
            "R1_ERR",
            "R0G",
            "R0G_ERR",
            "L0G",
            "L0G_ERR",
            "R0R",
            "R0R_ERR",
            "L0R",
            "L0R_ERR",
            "L4",
            "L4_ERR",
            "L3",
            "L3_ERR",
            "R3",
            "R3_ERR",
            "L5",
            "L5_ERR",
            "R4",
            "R4_ERR",
            "R5",
            "R5_ERR",
            "L6",
            "L6_ERR",
            "R6",
            "R6_ERR",
        ],
        "ZCAM": [
            "SOL",
            "SEQ_ID",
            "INSTRUMENT",
            "COLOR",
            "FEATURE",
            "FORMATION",
            "MEMBER",
            "FLOAT",
            "L6",
            "L6_ERR",
            "L0B",
            "L0B_ERR",
            "R0B",
            "R0B_ERR",
            "L5",
            "L5_ERR",
            "L0G",
            "L0G_ERR",
            "R0G",
            "R0G_ERR",
            "L4",
            "L4_ERR",
            "L0R",
            "L0R_ERR",
            "R0R",
            "R0R_ERR",
            "L3",
            "L3_ERR",
            "L2",
            "L2_ERR",
            "L1",
            "L1_ERR",
            "R1",
            "R1_ERR",
            "R2",
            "R2_ERR",
            "R3",
            "R3_ERR",
            "R4",
            "R4_ERR",
            "R5",
            "R5_ERR",
            "R6",
            "R6_ERR",
        ],
    }[obsparams["INSTRUMENT"]]

    # Init the dataframe
    data = pd.DataFrame(columns=columns)
    # Generate the index column --- 'COLOR'
    colors = get_unique_colors(csv)
    data["COLOR"] = colors
    data = data.set_index("COLOR")

    for color in colors:
        this_color = csv[
            ["Eye", "Wavelength", f"{color} Mean Value", f"{color} Standard Deviation"]
        ]
        for i in range(len(this_color)):
            try:
                eye = this_color.loc[i]["Eye"].strip()[0]
                wavelength = int(this_color.loc[i]["Wavelength"])
                filt = wavelength_to_filter[obsparams["INSTRUMENT"]][eye][wavelength]
                data[f"{filt}"].loc[color] = this_color.loc[i][f"{color} Mean Value"]
                data[f"{filt}_ERR"].loc[color] = this_color.loc[i][
                    f"{color} Standard Deviation"
                ]
            except AttributeError:  # empty entries
                try:
                    if this_color.iloc[i]["Wavelength"].strip() == "Notes":
                        if color2type[color] == None:
                            data["FEATURE"].loc[color] = this_color.iloc[i][
                                f"{color} Mean Value"
                            ]
                        else:
                            data["FEATURE"].loc[color] = color2type[color]
                    elif this_color.iloc[i]["Wavelength"].strip() == "Float":
                        data["FLOAT"].loc[color] = this_color.iloc[i][
                            f"{color} Mean Value"
                        ]
                    elif this_color.iloc[i]["Wavelength"].strip() == "Formation":
                        data["FORMATION"].loc[color] = this_color.iloc[i][
                            f"{color} Mean Value"
                        ]
                    elif this_color.iloc[i]["Wavelength"].strip() == "Member":
                        data["MEMBER"].loc[color] = this_color.iloc[i][
                            f"{color} Mean Value"
                        ]
                except:
                    pass

    # Set values for constant columns
    data["INSTRUMENT"] = obsparams["INSTRUMENT"]
    data["SOL"] = obsparams["SOL"]
    data["SEQ_ID"] = obsparams["SEQ_ID"]
    # Clean up for consistency
    data["FORMATION"].replace('Murray ', 'Murray', inplace=True)
    data["MEMBER"].replace('Knockfarril Hill ', 'Knockfarril Hill', inplace=True)
    # Clean up some entries for human-readability
    data["FORMATION"].replace(np.nan, "-", inplace=True)
    data["MEMBER"].replace(np.nan, "-", inplace=True)
    data["FLOAT"].replace(np.nan, "N", inplace=True)
    data["FLOAT"].replace("x", "Y", inplace=True)
    data["FLOAT"].replace("float", "N", inplace=True)
    data["FEATURE"].replace(np.nan, "-", inplace=True)


    data.reset_index(inplace=True)
    data = data[columns]

    fn = fn.replace("-BEFORE", "")  # for test files
    outfile=fn.replace('.csv','-marslab.csv')
    data.to_csv(outfile, index=False)
    return data
