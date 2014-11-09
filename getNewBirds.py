import sys
from pprint import pprint
import requests
import math
import numpy as np
# import matplotlib.pyplot as plt
from pylab import * # "core parts of numpy, scipy, and matplotlib" (http://wiki.scipy.org/PyLab)
from cStringIO import StringIO
from PIL import Image
import urllib
import geopy
from geopy.distance import VincentyDistance
import mysql.connector
from matplotlib_venn import venn2

plot_on = 1

# import getNewBirds as nb; reload(nb); from getNewBirds import *


def ebird(service, **reqParams):
    # eBird API query

    base_url = 'http://ebird.org/ws1.1/'

    reqParams['fmt'] = 'json'
    resp = requests.get(base_url+service, params=reqParams)
    if resp.status_code != 200:
        raise Exception(resp.status_code, resp.url, resp.text)
    else:
        return resp.json()


def google_geo(location):
    # Google location lookup by name
    info = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json?address='+location+'&sensor=false').json()

    geo = {'formatted_address': info['results'][0]['formatted_address'],
        'lat': info['results'][0]['geometry']['location']['lat'],
        'lng': info['results'][0]['geometry']['location']['lng']}

    return geo

def google_map(good_hs, bad_hs):
    # show a Google map!

    colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'black']

    # if isinstance(location, str):
    #     geo = google_geo(location)
    #     lat = geo['lat']
    #     lng = geo['lng']
    # else:
    #     lat = location[0]
    #     lng = location[1]

    # sort hotspots by number of birds! TODO: do this in find_good_hotspots, also sort p array
    good_hs = sorted(good_hs, key=lambda n: n['expected_n'])

    if len(good_hs) > 6:
        use_hs = good_hs[0:6]
    else:
        use_hs = good_hs

    print(len(use_hs))


    # Generate URL with markers
    base_url = 'http://maps.googleapis.com/maps/api/staticmap?&size=1000x1000&sensor=false]'

    url_param = ''
    # markers for good hotspots
    url_param = '&markers=size:mid%%7Ccolor:%s' %colors[0]
    ind = 0
    for x in use_hs:
        url_param += '&markers=size:mid%%7Ccolor:%s%%7Clabel:%i' %(colors[ind], ind+1)
        url_param += '%%7C%f,%f' %(x['lat'],x['lng'])
        ind += 1

    url_param += '&markers=size:tiny%%7Ccolor:%s' % colors[-1]
    for x in bad_hs[1:20]: #FIXME: make reasonable estimate of size
        url_param+='%%7C%f,%f' %(x['lat'],x['lng'])


    image_bytes = urllib.urlopen(base_url+url_param).read()
    image = Image.open(StringIO(image_bytes)) #StringIO makes file object out of image data


    # TODO
    # - take in lat,lng of hotspots
    # - plot hotspot markers, sorted by # expected new birds.


    Image._show(image)

    return image


# def get_new_birds(here, there, distance):
#     # get list of birds that have been observed 'there' but not 'here'
#     # 'here' and 'there' should be google-able location names
#     # distance in km
#     # usage: new_birds = get_new_birds(here, there, distance)
#
#     here_geo = google_geo(here)
#     there_geo = google_geo(there)
#
#     print 'Finding birds within %.2f' % distance + ' km of ' + there_geo['formatted_address']
#     print 'that are not found within %.2f' % distance + ' km of ' + here_geo['formatted_address']
#
#     # there_geo['results'][0]['geometry']['location']['lat']
#
#     here_sightings = ebird('data/obs/geo/recent',
#                           lat=here_geo['lat'],
#                           lng=here_geo['lng'],
#                           dist=distance)
#     there_sightings = ebird('data/obs/geo/recent',
#                            lat=there_geo['lat'],
#                            lng=there_geo['lng'],
#                            dist=distance)
#
#     # Allow for missing common name, returns 'None', missing names bug fixed by eBird on 9/8
#     here_birds = [x.get('comName') for x in here_sightings]
#     there_birds = [x.get('comName') for x in there_sightings]
#
#     new_birds = list(set(there_birds) - set(here_birds))
#
#     # print 'New birds:'
#     # pprint(new_birds)
#
#     return new_birds

def get_new_birds(here, there, distance, month):
    # get list of birds that have been observed 'there' but not 'here'
    # 'here' and 'there' should be google-able location names
    # distance in km
    # month in 2-digit month format
    # usage: new_birds = get_new_birds(here, there, distance, month)

    # Get location name, lat,lng
    here_geo = google_geo(here)
    there_geo = google_geo(there)

    # Get bounding box within radius = distance
    here_box = geo_bounds([here_geo['lat'], here_geo['lng']], distance)
    there_box = geo_bounds([there_geo['lat'], there_geo['lng']], distance)

    print 'Finding birds within %.2f' % distance + ' km of ' + there_geo['formatted_address']
    print 'that are not found within %.2f' % distance + ' km of ' + here_geo['formatted_address']

    # Query MySQL for species list in each region
    cnx = mysql.connector.connect(user='root', password='',
                                  database='kestrel1m')


    now = datetime.datetime.now()

    # there birds:
    # cursor = cnx.cursor()
    # cursor.execute('''
    # select common_name
    # from checklists
    # # join locations on locations.pk = checklists.location_pk
    # join sightings on sightings.checklist_pk = checklists.pk
    # join species on species.pk = sightings.species_pk
    # where latitude between %s and %s and longitude between %s and %s
    # and (observation_date between '%s-%s-01' and '%s-%s-31'
    # or observation_date between '2003-11-01' and '2003-11-31'
    # or observation_date between '%s-%s-01' and '%s-%s-31'
    # or observation_date between '%s-%s-01' and '%s-%s-31')
    # group by common_name
    # ''', (there_box[0], there_box[1], there_box[2], there_box[3],
    #       now.year-2, month,
    #       now.year-2, month,
    #       now.year-1, month,
    #       now.year-1, month,
    #       now.year, month,
    #       now.year, month))

    #TODO: remove 2003 line!!
    cursor = cnx.cursor()
    cursor.execute('''
    select common_name
    from sightings
    join locations on locations.pk = sightings.locations_pk
    join species on species.pk = sightings.species_pk
    where latitude between %s and %s and longitude between %s and %s
    and (observation_date between '%s-%s-01' and '%s-%s-31'
    or observation_date between '2003-11-01' and '2003-11-31'
    or observation_date between '%s-%s-01' and '%s-%s-31'
    or observation_date between '%s-%s-01' and '%s-%s-31')
    group by common_name
    ''', (there_box[0], there_box[1], there_box[2], there_box[3],
          now.year-2, month,
          now.year-2, month,
          now.year-1, month,
          now.year-1, month,
          now.year, month,
          now.year, month))


    there_birds = [common_name for common_name in cursor]

    # here birds:
    # TODO: do we want to restrict bird list here to this month??
    # TODO: remove 2003!
    # cursor.execute('''
    # select common_name
    # from checklists
    # join locations on locations.pk = checklists.location_pk
    # join sightings on sightings.checklist_pk = checklists.pk
    # join species on species.pk = sightings.species_pk
    # where latitude between %s and %s and longitude between %s and %s
    # and (observation_date between '%s-%s-01' and '%s-%s-31'
    # or observation_date between '2003-11-01' and '2003-11-31'
    # or observation_date between '%s-%s-01' and '%s-%s-31'
    # or observation_date between '%s-%s-01' and '%s-%s-31')
    # group by common_name
    # ''', (here_box[0], here_box[1], here_box[2], here_box[3],
    #       now.year-2, month,
    #       now.year-2, month,
    #       now.year-1, month,
    #       now.year-1, month,
    #       now.year, month,
    #       now.year, month))

    cursor.execute('''
    select common_name
    from sightings
    join locations on locations.pk = sightings.locations_pk
    join species on species.pk = sightings.species_pk
    where latitude between %s and %s and longitude between %s and %s
    and (observation_date between '%s-%s-01' and '%s-%s-31'
    or observation_date between '2003-11-01' and '2003-11-31'
    or observation_date between '%s-%s-01' and '%s-%s-31'
    or observation_date between '%s-%s-01' and '%s-%s-31')
    group by common_name
    ''', (here_box[0], here_box[1], here_box[2], here_box[3],
          now.year-2, month,
          now.year-2, month,
          now.year-1, month,
          now.year-1, month,
          now.year, month,
          now.year, month))

    here_birds = [common_name for common_name in cursor]

    cursor.close()
    cnx.close()

    new_birds = list(set(there_birds) - set(here_birds))

    # print 'New birds:'
    pprint(new_birds)

    if plot_on:
        plt.figure(figsize=(10,8))
        v = venn2([set(here_birds), set(there_birds)], (here_geo['formatted_address'], there_geo['formatted_address']))
        v.get_patch_by_id('100').set_alpha(1.0)
        v.get_patch_by_id('100').set_color('gray')
        plt.title('Number of Bird Species')
        top = 0.70


        # here birds
        if len(here_birds) < 40:
            step_size = 0.05
            font_size = 10
        elif len(here_birds) < 80:
            step_size = 0.025
            font_size = 8
        else:
            step_size = 0.01
            font_size = 6

        n = len(here_birds)
        bottom = top - (n * step_size)
        y_loc = sort(np.arange(bottom, top+0.01, step_size))

        count = 0
        plt.text(-1, 0.7, 'Here Birds', size=font_size, weight='bold')
        # y_loc = sort(np.arange(-0.7, 0.61, 1.3/len(here_birds)))
        for bird in here_birds:
            plt.text(-1, y_loc[count], bird[0], size=font_size)
            count += 1
        # TODO: add overlapping birds!

        # new birds
        plt.text(0.8, top, 'New Birds', size=font_size, weight='bold', color = 'green')

        if len(new_birds) < 40:
            step_size = 0.05
            font_size = 10
        elif len(new_birds) < 80:
            step_size = 0.025
            font_size = 8
        else:
            step_size = 0.01
            font_size = 6

        n = len(new_birds)
        bottom = top - (n * step_size)
        y_loc = sort(np.arange(bottom, top+0.01, step_size))
        count = 0
        for bird in new_birds:
            plt.text(0.7, y_loc[count], bird[0], size=font_size)
            count += 1
        plt.show()


    return new_birds

def get_hotspots(location, distance):
    # returns all hotspot names and IDs within 'distance' of 'location'
    # location can be googlable name
    # distance in km
    # usage: hotspots = get_hotspots(location, distance)

    print 'Finding hotspots in %s' %location

    geo = requests.get('https://maps.googleapis.com/maps/api/geocode/json?address='+location+'&sensor=false').json()
    origin = [geo['results'][0]['geometry']['location']['lat'], geo['results'][0]['geometry']['location']['lng']]
    geo_box = geo_bounds(origin, distance)

    # Query MySQL for hotspots within distance of location
    cnx = mysql.connector.connect(user='root', password='',
                                  database='kestrel1m')
    cursor = cnx.cursor()
    cursor.execute('''
    select locality, id, latitude, longitude
    from locations
    where latitude between %s and %s
    and longitude between %s and %s
    and locality_type = 'H'
    group by id
    ''', (geo_box[0], geo_box[1], geo_box[2], geo_box[3]))

    hotspots = [hs for hs in cursor]

    cursor.close()
    cnx.close()

    # Get all hotspots in the state (finest resolution provided by eBird API)
    # geo = requests.get(
    #     'https://maps.googleapis.com/maps/api/geocode/json?address='+location+'&sensor=false').json()
    # origin = [geo['results'][0]['geometry']['location']['lat'], geo['results'][0]['geometry']['location']['lng']]
    # country_name = geo['results'][0]['address_components'][3]['short_name']
    # state_name = geo['results'][0]['address_components'][2]['short_name']
    #
    # # get all state hotspots
    # state_hs = ebird('ref/hotspot/region',
    #                  rtype='subnational1',
    #                  r=country_name + '-' + state_name,
    #                  back=15, # look back only 15 days
    #                  fmt='csv')
    #
    # # find state hotspots within distance (km)
    # hotspots = [[x['locName'], x['locID'], x['lat'], x['lng']] for x in state_hs if get_distance(origin, [x['lat'], x['lng']]) < distance]

    return hotspots


def get_distance(origin, destination):
    # compute great-circle distance using haversine formula
    # 'origin' and 'destination' should be [lat, lng] lists
    # Author: Wayne Dyck
    # usage: d = get_distance(origin [lat,lng], destination [lat, lng])

    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371 # km (or 3963 mi, but eBird refs in km so beware)

    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c

    return d

def geo_bounds(origin, distance):
    # get bounding box of 'distance' km around a geo point in (lat, lng)
    # origin should be [lat,lng] list
    # distance is radius in km
    # usage: box = geo_bounds(origin, distance)
    # box = (lat S (min), lat N (max), lng W (min), lng E (max))

    north = VincentyDistance(kilometers=distance).destination(geopy.Point(origin), 0)
    east = VincentyDistance(kilometers=distance).destination(geopy.Point(origin), 90)
    south = VincentyDistance(kilometers=distance).destination(geopy.Point(origin), 180)
    west = VincentyDistance(kilometers=distance).destination(geopy.Point(origin), 270)

    # get bounding box: (min lat, max lat, min lng, max lng)
    box = (south.latitude, north.latitude, west.longitude, east.longitude)

    return box

def get_counts(birds_wanted, hotspot_id):
    # *approximate* bird frequency: the number of checklists in which it was reported. Turns out eBird API does not
    # return all sightings and provides no access to total number of checklists! So we're upper bounding here.
    # 'birds_wanted' should be a list of common bird name strings
    # hotspot_id should be the eBird locID
    # num_seen = get_counts(birds_wanted, hotspot_id)

    # get all recent checklists from a hotspot
    sightings = ebird('product/obs/hotspot/recent',
          back=30,
          r=hotspot_id,
          detail='full',
          includeProvisional='true',
          fmt='json')

    if len(sightings) > 0:
        print '  Counting sightings in ' + sightings[0]['locName']

    num_checklists = [x['numChecklists'] for x in sightings]

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

def get_notable(hotspot_id):
    # get notable sightings from a hotspot
    # usage: notable = get_notable(hotspot_id)

    sightings = ebird('data/notable/hotspot/recent',
          back=30,
          r=hotspot_id,
          detail='full',
          includeProvisional='true',
          fmt='json')

    notable = set([x['comName'] for x in sightings])

    return notable

def plot_hotspots(good_hotspots, prob_array, titles):
    # plot heatmap of bird probabilities
    # usage: plot_hotspots(good_hotspots, prob_array, titles)

    if len(good_hotspots) < 1:
        print 'No hotspots provided to plot_hotspots'
        return

    # set up axes and labels
    fig, axes = plt.subplots(1, 1, figsize=(20, 8),
         subplot_kw={
             'xticks': range(0,len(titles['birds'])),
             'xticklabels': titles['birds'],
             'yticks': range(0,len(good_hotspots)),
             'yticklabels': titles['hotspots'],
         }
    )
    plt.subplots_adjust(left=0.12, right=0.99, top=0.99, bottom=0.1)

    for label in (axes.get_xticklabels() + axes.get_yticklabels()):
        label.set_fontname('Arial')
        label.set_fontsize(9)
    axes.set_xticklabels(titles['birds'], rotation=90)

    # plot heatmap
    axes.imshow(prob_array, interpolation = 'none')

    # highlight notable birds by coloring names in red
    all_notable = set()
    [all_notable.update(z['notable']) for z in good_hotspots]
    # pprint(all_notable)

    [i.set_color("red") for i in plt.gca().get_xticklabels() if i.get_text() in all_notable]

    plt.title(titles['title'])
    show()


def find_good_hotspots(here, there, distance, month):
    # return hotspots with frequent sightings and the probability of observing "wanted" birds
    # also return sightings data array for plotting
    # 'here' and 'there' should be google-able location names, e.g. "Philadelphia"
    # distance in km
    # usage: [good_hotspots, bad_hotspots, prob_array, bird_list] = find_good_hotspots(here, there, distance)

    bird_list = get_new_birds(here, there, distance, month)
    hotspot_ids = get_hotspots(there, distance)

    good_hotspots = []
    bad_hotspots = []

    prob_array = []
    for x in hotspot_ids:
        num_seen = get_counts(bird_list, x[1])

        ind_max = num_seen.argmax()
        most_common = [bird_list[ind_max], num_seen[ind_max]]

        # only store hotspots with >10 sightings of the most common bird
        if most_common[1] > 10:
            prob_seen = [y/float(most_common[1]) for y in num_seen]
            prob_array.append(prob_seen)
            keep_birds = [z for z in sorted(zip(bird_list, prob_seen), key=lambda x: x[1], reverse=True) if z[1] > 0]

            notable_birds = get_notable(x[1])
            if len(notable_birds):
                print '     Found notable species:'
                for i in notable_birds:
                    print '          ' + i

            good_hotspots.append({
                'locName': x[0],
                'locID': x[1],
                'lat': x[2],
                'lng': x[3],
                'birds': keep_birds,
                'notable': notable_birds,
                'expected_n': np.sum(prob_seen)})

            print good_hotspots[-1]['locName']
            print '  Most common bird: ' + most_common[0] + ', reported %s' %most_common[1] + ' times in the last 30 days'
            for i in good_hotspots[-1]['birds']:
                print '     ' + i[0] + ' prob = %.2f' %i[1]
        else:
            bad_hotspots.append({
                'locName': x[0],
                'locID': x[1],
                'lat': x[2],
                'lng': x[3]})
            print '    X does not have enough sightings of most common bird (%d)' %most_common[1]

    # make probability array and plot!
    prob_array = np.array(prob_array)

    #TODO 1
    # sort hotspots ** and prob array?? **
    # good_hotspots = sorted(good_hotspots, key=lambda n: n['expected_n'])



    # good_hotspots = sorted(good_hotspots, key=good_hotspots.expected_n)

    titles = {'birds': bird_list,
        'hotspots': [x['locName'] for x in good_hotspots],
        'title': 'Probability of observing birds not seen in %s' %here + ' in %s hotspots' %there
    }

    plot_hotspots(good_hotspots, prob_array, titles)
    # google_map(there, good_hotspots, bad_hotspots)

    print 'Done! Found %d good hotspots' %len(good_hotspots)
    return good_hotspots, bad_hotspots, prob_array, bird_list