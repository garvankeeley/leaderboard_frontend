import json
import pg8000
import sys
import geopy, math
from geopy.distance import vincenty
from math import radians, cos, sin, asin, sqrt

mercator_id = 3857 # http://en.wikipedia.org/wiki/Web_Mercator 3785 # 900913 or 3857
wgs84_id = 4326


# Code from here, http://wiki.openstreetmap.org/wiki/Mercator
def merc_x(lon):
    r_major = 6378137.000
    return r_major * math.radians(lon)


def merc_y(lat):
    if lat > 89.5:
        lat = 89.5
    if lat < -89.5:
        lat = -89.5
    r_major = 6378137.000
    r_minor = r_major  # orig code is r_minor=6356752.3142, which is not SRID 3857
    temp = r_minor / r_major
    eccent = math.sqrt(1 - temp ** 2)
    phi = math.radians(lat)
    sinphi = math.sin(phi)
    con = eccent * sinphi
    com = eccent / 2
    con = ((1.0 - con) / (1.0 + con)) ** com
    ts = math.tan((math.pi / 2 - phi) / 2) / con
    y = 0 - r_major * math.log(ts)
    return y


def get_easting_northing(lon, lat):
    conn = pg8000.connect()
    curs = conn.cursor()
    q = "SELECT ST_AsText(ST_Transform(ST_SetSRID(ST_POINT(%f, %f), %d), %d))" % \
                 (lon, lat, wgs84_id, mercator_id)
    curs.execute(q)
    easting, northing = curs.fetchone()[0].replace('POINT(', '').replace(')', '').split()
    print northing, merc_y(lat), easting, merc_x(lon)
    return easting, northing


def create_cell_geo(lon, lat):
    easting, northing = get_easting_northing(lon, lat)

    # point to mercator, find nearest grid cell lower left

    e_ll = math.floor(float(easting) * 2) / 2
    n_ll = math.floor(float(northing) * 2) / 2

    dist_km = 0.5
    result = [(e_ll, n_ll), (e_ll, n_ll + dist_km), (e_ll + dist_km, n_ll + dist_km),
              (e_ll + dist_km, n_ll), (e_ll, n_ll)]
    return result

#if __name__ == '__main__':

def get_country(geo_string):
    geo = "ST_GeomFromText('%s', %d)" % (geo_string, mercator_id)
    transform = "ST_Transform(%s, %d)" % (geo, wgs84_id)
    select = "SELECT ogc_fid FROM country_bounds where ST_Contains(wkb_geometry, ST_Centroid(%s))" % transform
    conn = pg8000.connect()
    curs = conn.cursor()
    curs.execute(select)
    result = curs.fetchone()
    if result and len(result) == 1:
        return result[0]

    curs = conn.cursor()
    intersect = "SELECT ogc_fid FROM country_bounds where ST_Intersects(wkb_geometry, %s)" % transform
    curs.execute(intersect)
    result = curs.fetchone()
    if result:
      return result[0]

    curs = conn.cursor()
    nearby = "SELECT ogc_fid FROM country_bounds ORDER BY wkb_geometry <-> ST_Centroid(%s) LIMIT 1" % transform
    curs.execute(nearby)
    result = curs.fetchone()
    return result[0]

_cell_was_created = False

def get_or_create_cell(coord):
    #print 'coord', coord
    conn = pg8000.connect()
    curs = conn.cursor()
    pk = None
    try:
        curs.execute("SELECT gridcell_pk FROM gridcell where " +
                     "ST_Contains(wkb_geometry, ST_Transform("
                     "ST_GeomFromText('POINT(%.8f %.8f)', %d), %d))" %
                     (coord[0], coord[1], wgs84_id, mercator_id))
        pk = curs.fetchone()[0]
    except:
        pass

    global _cell_was_created
    if pk:
        _cell_was_created = False
        return pk

    lat = coord[1]
    lon = coord[0]
    if not isinstance(lat, float) or not isinstance(lon, float):
        print "bad lat lon: ", lat, lon
        return None

    geo = create_cell_geo(lon, lat)
    geo_string = 'POLYGON((' + ','.join([' '.join([str(a) for a in x]) for x in geo]) + '))'

    try:
        country_pk = get_country(geo_string)
    except:
        print "no country: " + geo_string
        get_country(geo_string)
        return None

    conn = pg8000.connect()
    curs = conn.cursor()
    q = "insert into gridcell(wkb_geometry, country_fk) values(ST_GeomFromText('%s', %d), %d) returning gridcell_pk" \
        % (geo_string, mercator_id, country_pk)
    #print q
    curs.execute(q)
    conn.commit()
    _cell_was_created = True
    pk = curs.fetchone()[0]
    #print geo_string
    return pk

def create_random_users():
    conn = pg8000.connect()
    curs = conn.cursor()
    for i in range(0, 2000):
        try:
            curs.execute("INSERT INTO userinfo(name) VALUES ('%s')" % ('name' + str(i)))
            conn.commit()
        except:
            print sys.exc_info()[0]
            conn.rollback()
            conn = pg8000.connect()
            curs = conn.cursor()

def get_user_pk(username):
    conn = pg8000.connect()
    curs = conn.cursor()
    pk = None
    try:
        curs.execute("select userinfo_pk from userinfo where name='%s'" % username)
        pk = curs.fetchone()[0]
    except:
        pass
    return pk

def insert_week(week, year, obs, userpk, cellpk):
    conn = pg8000.connect()
    curs = conn.cursor()
    try:
        curs.execute("""
            insert into weekly_report(week_of_year, year, observations, userinfo_fk, gridcell_fk)
             values(%d, %d, %d, %d, %d)
        """ % (week, year, obs, userpk, cellpk))
        conn.commit()
    except pg8000.Error as ex:
        print ex

from random import randint
def func(coords):
    for coord in coords:
        lat = coord[1]
        lon = coord[0]
        if not isinstance(lat, float) or not isinstance(lon, float):
            print "bad lat lon: ", lat, lon
            return None

    geo = get_easting_northing(lon, lat)

        # cell = get_or_create_cell(coord)
        # if not cell:
        #    continue
        # for i in range(0, 5):
        #     user = get_user_pk('name' + str(randint(0, 1000)))
        #     #print cell, user
        #     try:
        #       insert_week(10, 2015, randint(10,100), user, cell)
        #     except pg8000.core.ProgrammingError as ex:
        #         print ex

def doit():
    with open('../geojson/world.geo.json') as data_file:
        data = json.load(data_file)
        for item in data['features']:
            print item['id']
            for c in item['geometry']['coordinates']:
                func(c)

#create_random_users()
#doit()

p = (-9.4, 51.5)
c = get_or_create_cell(p)

