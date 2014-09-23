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
    # pprint(here_geo['results']) for a somewhat clearer print

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

    # Allow for missing common name, returns 'None'
    here_birds = [x.get('comName') for x in here_sightings]
    there_birds = [x.get('comName') for x in there_sightings]

    new_birds = list(set(there_birds) - set(here_birds))

    # print 'New birds:'
    # pprint(new_birds)

    return new_birds

def get_hotspots(location, max_distance):
    # location can be googlable name and distance must be in km

    # Get all hotspots in the state (finest resolution provided by ebird API)
    geo = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json?address='+location+'&sensor=false').json()
    origin = [geo['results'][0]['geometry']['location']['lat'], geo['results'][0]['geometry']['location']['lng']]
    country_name = geo['results'][0]['address_components'][3]['short_name']
    state_name = geo['results'][0]['address_components'][2]['short_name']

    # get all state hotspots
    state_hs = ebird('ref/hotspot/region',
        rtype='subnational1',
        r=country_name+'-'+state_name,
        back=15, # look back only 15 days
        fmt='csv')

    # find state hotspots within distance km
    # TODO add distance
    hotspots = [[x['locName'], x['locID']] for x in state_hs if get_distance(origin, [x['lat'], x['lng']]) < max_distance]

    return hotspots


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

def report_counts(birds_wanted, hotspot_id):
    # *approximate* probability of observing a bird, estimated from the number of checklists
    # in which it was reported. Turns out eBird API does not return all sightings and
    # provides no access to total number of checklists! So we're upper bounding here.

    # get all recent checklists from a hotspot
    sightings = ebird('product/obs/hotspot/recent',
                          back=30,
                          r=hotspot_id,
                          detail='full',
                          includeProvisional='true',
                          fmt='json')

    # if len(sightings) > 0:
    #     print sightings[0]['locName']

    num_checklists = np.array([x['numChecklists'] for x in sightings])

    # Find "wanted" birds and store number of times reported
    ind_wanted = 0
    num_seen = [0 for x in range(len(birds_wanted))]
    for bird in birds_wanted:
        ind_sightings = 0
        for sighting in sightings:
            if bird in sighting['comName']:
                # print '    ' + sighting['comName'] + ', seen %s' %num_checklists[ind_sightings] +' times'
                num_seen[ind_wanted] = num_checklists[ind_sightings]
            ind_sightings += 1
        ind_wanted += 1

    num_seen = np.array(num_seen)

    return num_seen


##
bird_list = get_new_birds('Philadelphia', 'San Francisco', 20)
hotspots = get_hotspots('San Francisco', 20)

good_hotspots = []
for x in hotspots:
    num_seen = report_counts(bird_list, x[1])

    ind_max = num_seen.argmax()
    most_common = [bird_list[ind_max], num_seen[ind_max]]

    # only store hotspots with >20 sightings of most common bird
    if most_common[1] > 10:
        prob_seen = [y/float(most_common[1]) for y in num_seen]
        keep_birds = [z for z in sorted(zip(bird_list, prob_seen), key=lambda x: x[1], reverse=True) if z[1] > 0.5]

        good_hotspots.append({'locName': x[0], 'locID': x[1], 'birds': keep_birds})

        print good_hotspots[-1]['locName']
        print '  Most common bird: ' + most_common[0] + ', reported %s' %most_common[1] + ' times in the last 30 days'
        for i in good_hotspots[-1]['birds']:
            print '     ' + i[0] + ' prob = %.2f' % i[1]
