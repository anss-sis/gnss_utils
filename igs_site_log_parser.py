'''
igs_site_log_parser.py 
v1.0 
2021-02-09

Parse a IGS Site Log text file Sections 0-12 into an OrderedDict.

Author: Prabha Acharya, ANSS SIS Development Team, SCSN
Email: sis-help@gps.caltech.edu
'''

import re
from collections import OrderedDict
import utils
import custom_exceptions as c_exc

# Report warnings for lines without colon. Except for these which are valid and expected (and ignored)
# labels in the IGS Site log
labels_no_colon = ('Approximate Position (ITRF)', 'Differential Components from GNSS Marker to the tied monument (ITRS)', 
    'Primary Contact', 'Secondary Contact', 'Hardcopy on File', 'Antenna Graphics with Dimensions') 

class IGSSiteLogParser(object):
    ''' Read a IGSSitelog file into a python object '''
    def __init__(self):
        self.filename = None
        self.content = {}

    def loadFromFile(self, filename):
        self.filename = filename
        self.content = self.__parseFile()

    def getContent(self):
        return self.content

    # Internal function.
    def __parseFile(self):
        skipsection = True  # Used to ignore content of sections of type n.x or n.n.x
        sectionnum = None
        subsectionnum = None
        content = OrderedDict()
        subkey = None
        errmsgs = []
        warnings = {'missingcolon':[]}
        prefx = ''
        # File needs to be processed in two steps. 
        # Step 1 - Read the file and make a dict of dict like this:
        #   { sectionkey|subsection : { label: value,  } ,  }
        # The sections ending with .x are discarded, and values are "cleaned" 
        with open(self.filename, 'r') as f_in:
            for line in f_in:
                try:
                    line = line.strip()
                    linedata = None
                    prevval = ''
                    if not line:
                        continue

                    if re.search('^\d+.\s+', line): # look for a main section heading
                        sectionnum, restofline = line.split(maxsplit=1)
                        subsectionnum = None
                        skipsection = False

                    elif re.search('^[\d]+.[\d]+', line):      # look for a subsection heading. 
                        subsectionnum, restofline = line.split(maxsplit=1)
                        skipsection = subsectionnum.endswith('x')
                        if skipsection:
                            continue
                        # Anything designated as subsections are to be saved in list of dicts 
                        # where key is the subsection without the final suffix. 
                        # So for n.1 save as n: [{ section contents in a dict}, ]
                        # So for n.n.1 save as n.n: [{ section contents in a dict}, ]
                        # (subsectionnum, suffix) = subsectionnum.rsplit('.', 1)
                        if restofline:
                            linedata = restofline.split(':', maxsplit=1)                
                    else:
                        if skipsection:
                            continue

                        # Keep track of lines that do not have a preceding colon and report a warning
                        if ':' not in line and line not in labels_no_colon:
                            warnings['missingcolon'].append(line)

                        linedata = line.split(':', maxsplit=1)
                    
                    # Stop processing when section 13, Antenna Graphics with Dimensions is reached. 
                    if sectionnum == '13.' and linedata and linedata[0].startswith('Antenna Graphics with Dimensions'):
                        break

                    # Another exception processing! Section 11 Primary contact and secondary contact 
                    # are listed on lines that are not even read by the code
                    # The keys themselves (contact name, telephone etc are listed twice)
                    # Define a prefix for use only in this section of the file
                    if sectionnum == '11.':
                        if linedata:
                            if linedata[0] == 'Primary Contact':
                                prefx = 'primary_'
                            elif linedata[0] == 'Secondary Contact':
                                prefx = 'secondary_'
                            elif linedata[0].startswith('Additional'):
                                # Clear the prefix 
                                prefx = ''
                    else:
                        prefx = ''

                    if linedata:
                        if len(linedata) == 2:
                            # Set the key and subkey even if no val is set. There are some 
                            # multiline entries where the first line has no value, 
                            # but the second line has.  
                            key = subsectionnum if subsectionnum else sectionnum
                            if linedata[0].strip():
                                subkey = f'{prefx}{linedata[0].strip()}'
                                prevval = ''

                            # Read and clean the val and assign it to the dict
                            val = linedata[1].strip()
                            if val is not None and len(val) > 0:
                                if val.startswith("("):
                                    #default value. Ignore it.
                                    continue

                                # save to subdict. define one if not already present
                                if key not in content:
                                    content[key]={}
                                if subkey in content[key]:
                                    # multiline data. get existing value
                                    prevval = content[key][subkey] + ' '

                                val = prevval + val

                                try: 
                                   cleaned_val = self.__clean_data(subkey, val)
                                   if cleaned_val is not None: 
                                        content[key][subkey] = cleaned_val
                                except Exception as exc:
                                    errmsgs.append(f'Invalid value found in section: {key}, {subkey}: {val}. Error message: {exc}')

                except ValueError as v:
                    errmsgs.append (f'{v} on line {line}')            

        # Step 2. Take the dict of dict generated above and rearrange the subsection entities into a list. 
        # { sectionkey: {}, subsectionkey : [{} {} ]}
        content2 = OrderedDict()
        for k, v in content.items():
            (key, suffix) = k.rsplit('.', 1)
            if suffix:
                # Save in a list of items. Create list if not present
                if key not in content2:
                    content2[key] = []
                content2[key].append(v)
            else:
                content2[key] = v

        if warnings['missingcolon']:
            content2['warning'] = 'Did not find a colon separator on line(s). Ignoring these lines:\n    ' + '\n    '.join(warnings["missingcolon"])
        if errmsgs:
            content2['error'] = errmsgs
            raise c_exc.ParseException('Parsing error: \n'.join(errmsgs))
        return content2

    def __clean_data(self, key, val):
        # Returns cleaned value, or raises ValueError if unable to parse/format the value
        cleaned_val = None
        if key in ('Date Installed', 'Date Removed', 'Date Measured', 'Calibration date', 'Date Prepared'):
            # Date time or date only
            cleaned_val = utils.parse_date(val)

        elif key in ('Effective Dates', 'Date'):
            # Date range
            dates = val.split('/')
            # ensure list has two items. pad if needed.
            dates += [''] * (2 - len(dates))
            cleaned_val = [utils.parse_date(d) for d in dates]

        elif key == 'Antenna Type':
            # split into antenna model and radome model
            cleaned_val = [val[:-4].strip(), val[-4:].strip()]
        elif key in ('Latitude (N is +)', 'Longitude (E is +)',):
            # convert from DDMMSS.SS/DDDMMSS.SS to decimal degrees
            cleaned_val = utils.dms2dec(val)

        elif key in ('Height of the Monument', 'Foundation Depth', 'X coordinate (m)', 'Y coordinate (m)', 'Z coordinate (m)', 
                'Elevation (m,ellips.)', 
                'Height of the Monument', 'Foundation Depth',
                'dx (m)', 'dy (m)', 'dz (m)'):
            # remove any space or m
            # convert to float and return it
            cleaned_val = val.replace('m', '').strip()
            cleaned_val = float(cleaned_val)
        elif key in ('Alignment from True N', 'Elevation Cutoff Setting'):
            cleaned_val = val.replace('deg', '').strip()
        elif key == 'Accuracy (mm)':
            # This pertains only to the entry under section 5 Tied markers. Remove the mm suffix if present 
            # convert to float and return it
            cleaned_val = val.replace('mm', '').strip()
            cleaned_val = float(cleaned_val)
        else:
            cleaned_val = val

        return cleaned_val


def main():
    import argparse
    import pprint

    argparser = argparse.ArgumentParser(description='Parse IGS SiteLog')
    argparser.add_argument('igs_file', help='Path and name of IGS SiteLog file')
    options = argparser.parse_args()

    # Initialize the parser and load the file to be parsed
    slparser = IGSSiteLogParser()
    slparser.loadFromFile(options.igs_file)

    # View the contents of the file parsed into an OrderedDict
    od = slparser.getContent()
    pprint.pprint(od)

if __name__ == "__main__":
    main()
