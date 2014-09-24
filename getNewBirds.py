import sys
from pprint import pprint
import requests
import math
import numpy as np
import matplotlib.pyplot as plt


def ebird(service, **reqParams):
    # eBird API query

    base_url = 'http://ebird.org/ws1.1/'

    reqParams['fmt'] = 'json'
    resp = requests.get(base_url+service, params=reqParams)
    if resp.status_code != 200:
        raise Exception(resp.status_code, resp.url, resp.text)
    else:
        return resp.json()


def get_new_birds(here, there, distance):
    # get list of birds that have been observed 'there' but not 'here'
    # 'here' and 'there' should be google-able location names
    # distance in km
    # usage: new_birds = get_new_birds(here, there, distance)

    here_geo = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json?address='+here+'&sensor=false').json()
    # pprint(here_geo['results']) for a somewhat clearer print

    there_geo = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json?address='+there+'&sensor=false').json()

    print 'Finding birds within %.2f' % distance + ' km of ' + there_geo['results'][0]['formatted_address']
    print 'that are not found within %.2f' % distance + ' km of ' + here_geo['results'][0]['formatted_address']

    there_geo['results'][0]['geometry']['location']['lat']

    here_sightings = ebird('data/obs/geo/recent',
                          lat=here_geo['results'][0]['geometry']['location']['lat'],
                          lng=here_geo['results'][0]['geometry']['location']['lng'],
                          dist=distance)
    there_sightings = ebird('data/obs/geo/recent',
                           lat=there_geo['results'][0]['geometry']['location']['lat'],
                           lng=there_geo['results'][0]['geometry']['location']['lng'],
                           dist=distance)

    # Allow for missing common name, returns 'None', missing names bug fixed by eBird on 9/8
    here_birds = [x.get('comName') for x in here_sightings]
    there_birds = [x.get('comName') for x in there_sightings]

    new_birds = list(set(there_birds) - set(here_birds))

    # print 'New birds:'
    # pprint(new_birds)

    return new_birds

def get_hotspots(location, distance):
    # returns hotspot names and IDs within 'distance' of 'location'
    # location can be googlable name
    # distance in km
    # usage: hotspots = et_hotspots(location, distance)

    print 'Finding hotspots in %s' %location

    # Get all hotspots in the state (finest resolution provided by eBird API)
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
    hotspots = [[x['locName'], x['locID']] for x in state_hs if get_distance(origin, [x['lat'], x['lng']]) < distance]

    return hotspots


def get_distance(origin, destination):
    # compute great-circle distance using haversine formula
    # 'origin' and 'destination' should be [lat, long] lists
    # Author: Wayne Dyck
    # usage: d = get_distance(origin [lat,lng], destination [lat, long])

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
    plt.show()


def find_good_hotspots(here, there, distance):
    # return hotspots with frequent sightings and the probability of observing "wanted" birds
    # also return sightings data array for plotting
    # 'here' and 'there' should be google-able location names, e.g. "Philadelphia"
    # distance in km
    # usage: [good_hotspots, prob_array, bird_list] = find_good_hotspots(here, there, distance)

    bird_list = get_new_birds(here, there, distance)
    hotspots = get_hotspots(there, distance)

    good_hotspots = []
    prob_array = []
    for x in hotspots:
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
                'birds': keep_birds,
                'notable': notable_birds,
                'expected_n': np.sum(prob_seen)})

            # print good_hotspots[-1]['locName']
            # print '  Most common bird: ' + most_common[0] + ', reported %s' %most_common[1] + ' times in the last 30 days'
            # for i in good_hotspots[-1]['birds']:
            #     print '     ' + i[0] + ' prob = %.2f' % i[1]

    # make array and plot!
    prob_array = np.array(prob_array)

    titles = {'birds': bird_list,
        'hotspots': [x['locName'] for x in good_hotspots],
        'title': 'Probability of observing birds not seen in %s' %here + ' in %s hotspots' %there
    }
    plot_hotspots(good_hotspots, prob_array, titles)


    print 'Done!'
    return good_hotspots, prob_array, bird_list