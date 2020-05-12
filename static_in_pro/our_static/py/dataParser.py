import csv
import sys
import json
import re
import copy
import itertools

def hasNumbers(inputString):
  result = bool(re.search(r'\d', inputString))
  return result

def process_file(file, mineral_class, mineral_type):
    dataArray = [] # Array of IDs
    sampArray = [] # Sample IDs
    nameArray = [] # Mineral Names
    collArray = [] # Collection localities
    grainArray = [] # Grain sizes
    vGeoArray = [] # Viewing Geometries
    resArray = [] # Resolutions
    formArray = [] # Formulas
    compArray = [] # Compositions

    error_messages = ''

    try:
        paramFile = file.read()
        reader = csv.reader(file)

        # HEADER Section
        header_line = reader.next()
        while header_line[0] != '':

            # Database of origin
            if 'database' in header_line[0].lower():
                origin = header_line[1]

            # Spreadsheet Description
            elif 'description' in header_line[0].lower():
                desc = header_line[1]

            # Date of original database access (YEAR-MONTH-DAY)
            elif 'accessed' in header_line[0].lower():
                access = header_line[1]

            else:
                error_messages += "\"" + header_line[0] + "\" does not contain a known key\n"

            header_line = reader.next()

        # METADATA Section
        dataIDs = reader.next() # Data ID must come first
        start = 1
        while dataIDs[start] == '':
            start += 1

        c = start
        while c < len(dataIDs):
            dataArray.append(dataIDs[c])
            c+=1

        # Rest of the metadata
        meta_line = reader.next()
        while meta_line[0] != '':
            c = start

            # Sample ID
            if 'sample id' in meta_line[0].lower():
                while c < len(meta_line):
                    sampArray.append(meta_line[c])
                    c+=1

            # Mineral name
            elif 'name' in meta_line[0].lower():
                while c < len(meta_line):
                    nameArray.append(meta_line[c])
                    c+=1

            # Collection Locality
            elif 'locality' in meta_line[0].lower():
                while c < len(meta_line):
                    collArray.append(meta_line[c])
                    c+=1

            # Grain size
            elif 'grain size' in meta_line[0].lower():
                while c < len(meta_line):
                    grainArray.append(meta_line[c])
                    c+=1

            # Viewing geometry
            elif 'grain size' in meta_line[0].lower():
                while c < len(meta_line):
                    vGeoArray.append(meta_line[c])
                    c+=1

            # Resolution
            elif 'resolution' in meta_line[0].lower():
                while c < len(meta_line):
                    resArray.append(meta_line[c])
                    c+=1

            # Formula
            elif 'formula' in meta_line[0].lower():
                while c < len(meta_line):
                    formArray.append(meta_line[c])
                    c+=1

            # Composition
            elif 'composition' in meta_line[0].lower():
                while c < len(meta_line):
                    compArray.append(meta_line[c])
                    c+=1

            """
            Add new metadata fields here
            """

            else:
                error_messages += "\"" + meta_line[0] + "\" does not contain a known key\n"

            meta_line = reader.next()

        # REFLECTANCE Section
        line = reader.next()

        # Figure out units
        if "microns" in line[0] or "um" in line[0]:
            factor = 1000
        else:
            factor = 1

        wl = reader.next()

        row_len = len(dataIDs)
        c = start

        dataPoints = [{}] * (row_len - c)
        for row in reader:
            if hasNumbers(row[0]) == True:
                for column in xrange(c,row_len):
                    if float(row[column]) > 1.0:
                        dataPoints[column-c][str(float(row[0]) * factor)] = str(float(row[column]) / 100.)

                    # Check for invalid datapoints #
                    elif float(row[column]) < 0.0:
                        continue

                    else:
                        dataPoints[column-c][str(float(row[0]) * factor)] = row[column]

    except Exception, e:
        print str(e)

    size = len(dataArray)

    for i in range(size):
        dataId = dataArray[i]
        sampId = sampArray[i]
        name = nameArray[i]
        collection = collArray[i]
        gr = grainArray[i]
        vGeo= vGeoArray[i]
        res = resArray[i]

        low = min([float(w) for w in dataPoints[i]])
        high = max([float(w) for w in dataPoints[i]])
        tempRan = [int(round(low, -2)), int(round(high, -2))]

        form = formArray[i]
        comp = compArray[i]

        # Check to see if Data ID already exists #
        # exists = Sample.objects.filter(data_id=dataID)

        sample = Sample.create(dataId, sampId, access, origin, collection, name, desc, mineral_type, mineral_class,'', gr, vGeo, res, tempRan, form, comp, dataPoints[i])
        sample.save()
