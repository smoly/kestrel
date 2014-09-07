import sys
from pprint import pprint
import requests
import math
import numpy as np


def ebird(service, **reqParams):
    base_url = 'http://ebird.org/ws1.1/'

    reqParams['fmt'] = 'json'
    resp = requests.get(base_url+service, params=reqParams)
    if resp.status_code != 200:
        raise Exception(resp.status_code, resp.url, resp.text)
    else:
        return resp.json()


def get_new_birds(here, there, distance):
    # here and there should be google-able location names
    # distance in km

    here_geo = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json?address='+here+'&sensor=false').json()
    # from pprint import pprint. then pprint(here_geo['results']) for a somewhat clearer print

    from pprint import pprint

    there_geo = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json?address='+there+'&sensor=false').json()

    print 'Finding birds in ' + there_geo['results'][0]['formatted_address']
    print 'that are not found in ' + here_geo['results'][0]['formatted_address']

    there_geo['results'][0]['geometry']['location']['lat']

    here_sightings = ebird('data/obs/geo/recent',
                          lat=here_geo['results'][0]['geometry']['location']['lat'],
                          lng=here_geo['results'][0]['geometry']['location']['lng'],
                          dist=distance)
    there_sightings = ebird('data/obs/geo/recent',
                           lat=there_geo['results'][0]['geometry']['location']['lat'],
                           lng=there_geo['results'][0]['geometry']['location']['lng'],
                           dist=distance)

    # Extract common name, or scientific name is the former is not available
    # If neither is available, returns 'None'.
    here_birds = [x.get('comName', x.get('sciName')) for x in here_sightings]
    there_birds = [x.get('comName', x.get('sciName')) for x in there_sightings]

    new_birds = list(set(there_birds) - set(here_birds))

    print 'New birds:'
    pprint(new_birds)

    # return new_birds

def get_hotspots(location, max_distance):
    # location can be googlable name and distance must be in km

    # Get all hotspots in the state (finest resolution provided by ebird API)
    geo = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json?address='+location+'&sensor=false').json()
    origin = [geo['results'][0]['geometry']['location']['lat'], geo['results'][0]['geometry']['location']['lng']]
    country_name = geo['results'][0]['address_components'][3]['short_name']
    state_name = geo['results'][0]['address_components'][2]['short_name']

    state_hs = ebird('ref/hotspot/region',
        rtype='subnational1',
        r=country_name+'-'+state_name,
        back=15, # look back only 15 days
        fmt='csv')

    # find state hotspots within distance km
    hotspots = [[x['locName'], x['locID']] for x in state_hs if get_distance(origin, [x['lat'], x['lng']]) < max_distance]

    return hotspots


def bird_probability(birds, hotspot_id):

    # get all recent checklists from a hotspot

    sightings = ebird('data/obs/hotspot/recent',
                          back=30,
                          r=hotspot_id,
                          detail='full',
                          fmt='json')
    # loop through birds
    # determine in how many checklists bird was observed
    return []


    #
    # if __name__ == '__main__': # prevent from executing when importing (or run when called as a script)
    #     print 42
    #     print 'hi alex'
    #     print bird_probability(sys.argv)

def get_distance(origin, destination):
    # origin and distance should be [lat, long] lists
    # Haversine formula example in Python
    # Author: Wayne Dyck

    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371 # km (or 3963 mi, but ebird refs in km so beware)

    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c

    return d

print get_new_birds('Philadelphia', 'San Francisco', 20)
