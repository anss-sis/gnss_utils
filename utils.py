'''
utils.py 
v1.0 
2021-02-09

Contains util functions. 
    Convert lat, lon, elev in WGS84 to ECEF X,Y,Z and back. 
    Parse date in text file to a python datetime object.

Author: Prabha Acharya, ANSS SIS Development Team, SCSN
Email: sis-help@gps.caltech.edu
'''

import math
from datetime import datetime, timezone

# WGS84 reference ellipsoid
EQUATORIAL_RADIUS = 6378137.0   # equatorial radius in m aka semimajor axis in m
FLATTENING = 1/298.257223563 # reciprocal  flattening
# polar semi minor axis = EQUATORIAL_RADIUS*(1-FLATTENING) = 6356752.3142 m
POLAR_RADIUS = 6356752.3142

E2 = 2.0 * FLATTENING - FLATTENING**2 #first eccentricity squared
EP2 = FLATTENING * (2.0 - FLATTENING)/((1.0 - FLATTENING)**2) #second eccentricity squared
E2c = EQUATORIAL_RADIUS**2 - POLAR_RADIUS**2

def xyz2lle(x, y, z):
    ''' Based on Fortran code from Mark Murray.
    Reference: J. Zhu, "Conversion of Earth-centered Earth-fixed coordinates to geodetic coordinates," 
    Aerospace and Electronic Systems, IEEE Transactions on, vol. 30, pp. 957-961, 1994. '''
    
    r = math.hypot(x, y)
    r2 = r**2
    Fc = 54.0 * POLAR_RADIUS**2 * z**2
    G = r2 + (1.0-E2) * z**2 - E2*E2c
    c = (E2**2 * Fc * r2)/(G**3)
    s = ( 1.0 + c + math.sqrt(c**2 + 2.0*c) )**(1/3.0)
    P = Fc / (3.0 * (s + 1.0/s + 1.0)**2 * G * G)
    Q = math.sqrt(1.0 + 2.0 * E2 * E2 * P)
    ro = -(E2*P*r)/(1.0+Q) + math.sqrt((EQUATORIAL_RADIUS**2/2.0)*(1.0+1.0/Q) - ((1.0-E2)*P*z**2)/(Q*(1.0+Q)) - P*r2/2.0)
    tmp = (r - E2*ro)**2
    U = math.sqrt( tmp + z**2 )
    V = math.sqrt( tmp + (1.0-E2)*z**2 )
    zo = (POLAR_RADIUS**2*z)/(EQUATORIAL_RADIUS * V)

    elev = U*( 1.0 - POLAR_RADIUS**2/(EQUATORIAL_RADIUS*V))
    phi = math.atan( (z + EP2 * zo)/r )
    lam = math.atan2(y, x)
    lat = math.degrees(phi)
    lon = math.degrees(lam)
    # 2359 use 8 decimal places for lat, lon. use 4 for elevation
    lat1 = round(lat, 8)
    lon1 = round(lon, 8)
    elev1 = round(elev, 4)
    return (lat1, lon1, elev1)

def lle2xyz(lat, lon, elev):
    # lat and lon given in decimal degrees, elevation in meters
    if lat is None or abs(lat) > 90:
        raise ValueError(f'Invalid Latitude: {lat}' )
    if lon is None or abs(lon) > 180:
        raise ValueError(f'Invalid Longitude: {lon}' )
    if elev is None:
        raise ValueError(f'Invalid Elevation: {elev}' )

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    chi = math.sqrt(1 - E2 * math.sin(lat_rad)**2)

    x = (EQUATORIAL_RADIUS/chi + float(elev)) * math.cos(lat_rad) * math.cos(lon_rad)
    y = (EQUATORIAL_RADIUS/chi + float(elev)) * math.cos(lat_rad) * math.sin(lon_rad)
    z = (EQUATORIAL_RADIUS*(1-E2)/chi + float(elev)) * math.sin(lat_rad)
    # use 4 decimal places for x, y, z
    x1 = round(x, 4)
    y1 = round(y, 4)
    z1 = round(z, 4)
    return (x1, y1, z1)

def dec2dms(coord):
    # convert coordinate in decimal deg to deg min ss
    deg = math.trunc(coord)     # get the integer part as degrees
    fl_mm = abs(coord-deg) * 60 # minutes in float
    mm = math.trunc(fl_mm)      # get the integer part of mins
    ss = (fl_mm - mm ) * 60     # seconds, expected to be a float
    return (deg, mm, ss)

def dms2dec(coord):
    # convert from DDMMSS.SS/DDDMMSS.SS to decimal degrees
    ll = coord.split('.')
    sec = ll[0][-2:] + '.' + ll[1] # not sure if fractional seconds are padded and hence this long about way to get the SS.SS
    minute = ll[0][-4:-2]
    deg = float(ll[0][:-4]) # string might have 2 or 3 digits based on lat/lon and +/- sign. So strip off the MMSS part out. 

    # combine the whole and fractional part; account for the sign
    frac = float(minute)/60 + float(sec)/3600
    if frac >=1: 
        raise ValueError(' Unexpected value in MMSS. Unable to convert minute-seconds to decimal values')
    if deg < 0:
        frac = -frac
    decdeg = deg + frac
    decdeg = round(decdeg, 8)
    return decdeg

def fmt_ll_dms_str(lat, lon):
    # return list of lat, lon formatted like this: (+/-DDMMSS.SS), (+/-DDDMMSS.SS)
    ll_dms = []
    for idx, coord in enumerate([lat, lon]):
        deg, mm, ss = dec2dms(coord)
        ss_padding='0' if ss < 10 else ''
        # the format str is slightly different for lat and lon
        if idx == 0:
            val = f'{deg:+03d}{mm:02d}{ss_padding}{ss:.2f}' 
        else :
            val = f'{deg:+04d}{mm:02d}{ss_padding}{ss:.2f}' 
        ll_dms.append(val)
    return ll_dms


def parse_date(val):
    fmt_z = ('%Y-%m-%dT%H:%MZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ') # date string ending with Z indicating UTC
    fmt_no_tm = ('%Y-%m-%d',) # no time or timezone given in string, assume UTC
    dt = None

    if 'CCYY-MM-DD' in val:  # section 6.1 - many users put in this value to indicate active end date. clear it and return
        return dt

    for fmt in fmt_z + fmt_no_tm:
        try:
            dt = datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
            break
        except ValueError:
            # cant raise error till all dt fmts have been tried. 
            pass

    if val and not dt:
        raise ValueError(f'Unable to parse date: {val}')
    return dt

