import requests
from pylab import * # "core parts of numpy, scipy, and matplotlib" (http://wiki.scipy.org/PyLab)
from cStringIO import StringIO
from PIL import Image
import urllib
import geopy
from geopy.distance import vincenty
import mysql.connector
from matplotlib_venn import venn2

# import kestrel as ks; reload(ks); from kestrel import *

# loc = 'Jackson, WY'
# geo_bounds([google_geo(loc)['lat'], google_geo(loc)['lng']], 20)

plot_on = 1


def find_good_hotspots(here, there, distance, month):
    ''' wrapper to identify the top hotspots in a destination based on the probability of
        observing "new" birds

    usage: good_hotspots, bad_hotspots, prob_array, bird_list = find_good_hotspots(here, there, distance, month)

    :param here: google-able location name, e.g. "Philadelphia"
    :param there: google-able location name, e.g. "SF, CA"
    :param distance: in km
    :param month: in 2-digit int
    :return: good_hotspots, bad_hotspots, prob_array, bird_list
    '''

    # Get hotspots with frequent sightings
    good_hotspots, bad_hotspots = get_hotspots(there, distance, month)
    if not good_hotspots:
        print 'No good hotspots found in %s, try increasing your search radius' % there
        return

    # Get birds that cannot be found at home
    new_birds, sightings, _, _ = get_birds(here, there, distance, month, good_hotspots)

    # Compute the probability seen of each bird-location
    prob_seen, good_hotspots = get_probability(new_birds, sightings, good_hotspots)

    # Display good hotspots on static google map
    google_map(good_hotspots)

    return good_hotspots, prob_seen, new_birds


def get_hotspots(there, distance, month):
    # hotspots with 10 or more checklists reported in the last 3 years during requested month
    #
    # good_hotspots, bad_hotspots = get_hotspots(there, distance, month)

    # TODO: don't require month as input, use now.month if don't have it

    # Get name,lat,lng and bounding box
    there_geo = google_geo(there)
    if not there_geo:
        print ' Please try a different "there" location'
        return
    there_box = geo_bounds([there_geo['lat'], there_geo['lng']], distance)

    now = datetime.datetime.now()

    # Query MySQL for number of checklists per hotspot
    cnx = mysql.connector.connect(user='root', password='', database='kestrel2y')

    print 'Counting checklists'
    # Count number of checklists per hotspot
    cursor = cnx.cursor()
    cursor.execute('''
    create view checklists as
    select locations.id, locality, latitude, longitude, sampling_event_identifier, count(*)
    from sightings
    join locations on locations.pk = sightings.locations_pk
    where latitude between %s and %s and longitude between %s and %s
    and observation_date > '%s-01-01' and month(observation_date) = %s
    and locality_type = 'H'
    group by locations.id, sampling_event_identifier
    ''', (there_box[0], there_box[1], there_box[2], there_box[3],
          now.year-2,
          month))

    cursor.execute('''
    select id as locality_id, latitude, longitude, locality, count(*)
    from checklists
    group by locality_id
    order by locality
    ''')

    print 'Finished counting checklists'
    # sort hotspots into "good" and "bad" based on total number of checklists (20)
    good_hotspots = []
    bad_hotspots = []
    for hs in cursor:
        if hs[4] >= 10:
            good_hotspots.append({
                'locality_id': hs[0],
                'lat': hs[1],
                'lng': hs[2],
                'locality': hs[3],
                'n_checklists': hs[4]
            })
        else:
            bad_hotspots.append({
                'locality_id': hs[0],
                'lat': hs[1],
                'lng': hs[2],
                'locality': hs[3],
                'n_checklists': hs[4]
            })

    cursor.execute('''drop view checklists''')
    cursor.close()

    cnx.close()
    return good_hotspots, bad_hotspots


def get_birds(here, there, distance, month, good_hotspots):
    ''' get list of birds that have been observed 'there' but not 'here'

    new_birds, sightings, here_birds, there_birds = get_birds(here, there, distance, month)

    :param here: google-able location name of home
    :param distance: search radius in km
    :return: here_birds a list of all birds that have been reported in this location
            in the last 3 years. new birds that can be found at destination
    #         in the requested month. None of these birds has been reported in
    #         "here" location in the last 3 years.
    '''

    # Get name,lat,lng
    here_geo = google_geo(here)
    there_geo = google_geo(there)
    if not here_geo:
        print ' Please try a different "here" location'
        return
    if not there_geo:
        print ' Please try a different "there" location'
        return

    # Get bounding box within radius = distance
    here_box = geo_bounds([here_geo['lat'], here_geo['lng']], distance)
    there_box = geo_bounds([there_geo['lat'], there_geo['lng']], distance)

    print 'Finding birds that can be found within %.2f' % distance + ' km of ' + there_geo['formatted_address']
    print 'that cannot be found within %.2f' % distance + ' km of ' + here_geo['formatted_address']

    now = datetime.datetime.now()

    # Query MySQL for species list in each region
    cnx = mysql.connector.connect(user='root', password='', database='kestrel2y')

    # Get  "here" sightings (all year):
    cursor = cnx.cursor()
    cursor.execute('''
    select common_name
    from sightings
    join locations on locations.pk = sightings.locations_pk
    join species on species.pk = sightings.species_pk
    where latitude between %s and %s and longitude between %s and %s
    and observation_date > '%s-01-01'
    group by common_name''',
        (here_box[0], here_box[1], here_box[2], here_box[3],now.year-2))

    here_birds = [common_name[0] for common_name in cursor]
    cursor.close()

    print 'Queried "here" birds'

    # Get "there" sightings in requested month (= one per bird-location)
    #   The count here returns the number of sighting events NOT number of
    #   individuals (which is not even in the current data schema)

    ids = [x['locality_id'] for x in good_hotspots]
    id_str = "and (locations.id = '%s'" % ids[0]
    for x in ids[1:]:
        id_str += " or locations.id = '%s'" % x
    id_str += ') '

    query = '''
    select locations.id, locality, common_name, count(*)
    from sightings
    join locations on locations.pk = sightings.locations_pk
    join species on species.pk = sightings.species_pk
    where latitude between %s and %s and longitude between %s and %s
    and observation_date > '%s-01-01' and month(observation_date) = %s ''' \
            + id_str + 'group by locations.id, common_name'

    cursor = cnx.cursor()
    cursor.execute(query, (there_box[0], there_box[1], there_box[2], there_box[3],
          now.year-2,
          month)
    )


    print 'Queried "there" birds'

    sightings = []
    for st in cursor:
        sightings.append({
            'locality_id': st[0],
            'locality': st[1],
            'common_name': st[2],
            'n_sightings': st[3]  # i.e. number of checklists in which bird was sighted
        })

    cursor.close()

    there_birds = list(set([st['common_name'] for st in sightings]))

    # Find new! birds
    new_birds = list(set(there_birds) - set(here_birds))

    # TODO: if date is near this month, add notables to new_birds list.

    cnx.close()

    if plot_on:
        fig, h_plot = plt.subplots(3, 3, figsize=(10,7))
        v = venn2([set(here_birds), set(there_birds)],
                  (here_geo['formatted_address'], there_geo['formatted_address']),
                  ax=h_plot[0][1])
        v.get_patch_by_id('100').set_alpha(1.0)
        v.get_patch_by_id('100').set_color('gray')
        h_plot[0][1].set_title('Number of Bird Species')

        # Hide all other axes - ick
        h_plot[0][0].axis('off')
        h_plot[0][2].axis('off')
        h_plot[1][0].axis('off')
        h_plot[1][1].axis('off')
        h_plot[1][2].axis('off')
        h_plot[2][0].axis('off')
        h_plot[2][1].axis('off')
        h_plot[2][2].axis('off')

        figtext(0.1, 0.6, 'New Birds in ' + there_geo['formatted_address'],
                size=14, color='green')
        text_to_fig(sorted(new_birds),
                    top_loc=0.56,
                    left_loc=0.1,
                    text_col='green',
                    step_size=0.9/50,
                    lines_per_column = 30)
        show()

    return new_birds, sightings, here_birds, there_birds


def get_probability(new_birds, sightings, good_hotspots):
    ''' Probability map of observing each "new" bird at each good hotspot.
        Probability is the proportion of checklists that report the bird in each location

    prob_seen, good_hotspots = get_probability(new_birds, sightings, good_hotspots)

    :param new_birds: list of new bird common names
    :param sightings: dictionary of all sightings in the destination
    :param good_hotspots:
    :return: prob_seen, good_hotspots
    '''

    print 'getting probability'
    # sort out sighting counts into array of size len(good_hotspots) x len(new_birds)
    # yuck
    prob_seen = zeros((len(good_hotspots), len(new_birds)))
    for st in sightings:
        # print 'sighting: %i %s in %s(%s)' % (st['n_sightings'], st['common_name'], st['locality'], st['locality_id'])
        for i_hs, hs in enumerate(good_hotspots):
            if st['locality_id'] == hs['locality_id']: # found hotspot id
                # print 'sighting in %s is in %s' %(st['locality'], hs['locality'])
                for i_bd, bd in enumerate(new_birds):
                    if bd == st['common_name']: # this bird is one we have been looking for
                        prob_seen[i_hs, i_bd] = st['n_sightings'] / double(hs['n_checklists'])
                        # print 'found %i %s in %s. %i checklists. result = %f' % \
                        #       (st['n_sightings'],
                        #        st['common_name'],
                        #        hs['locality'],
                        #        hs['n_checklists'],
                        #        st['n_sightings'] / double(hs['n_checklists']))

    print 'done computing probability'

    # Add expected number of birds to good_hotspot records
    for i_hs, hs in enumerate(good_hotspots):
        good_hotspots[i_hs]['expected_n'] = sum(prob_seen[i_hs])

    if plot_on:
        titles = {'birds': new_birds,
                  'hotspots': [hs['locality'] for hs in good_hotspots],
                  'title': 'Probability of observing new birds in destination'
        }
        plot_hotspots(good_hotspots, prob_seen, titles)

    return prob_seen, good_hotspots


def get_notable(hotspot_id):
    # get notable sightings in a hotspot from the last 30 days (via API)
    # usage: notable = get_notable(hotspot_id)

    sightings = ebird('data/notable/hotspot/recent',
          back=30,
          r=hotspot_id,
          detail='full',
          includeProvisional='true',
          fmt='json')

    notable = set([x['comName'] for x in sightings])

    return notable


def geo_bounds(origin, distance):
    ''' get lat,lng bounding box of 'distance' km around a geo point

        geo_box = geo_bounds(origin, distance)

    :param origin: [lat,lng] list
    :param distance: radius in km
    :return: geo_box: (min lat, max lat, min lng, max lng)
    '''

    north = vincenty(kilometers=distance).destination(geopy.Point(origin), 0)
    east = vincenty(kilometers=distance).destination(geopy.Point(origin), 90)
    south = vincenty(kilometers=distance).destination(geopy.Point(origin), 180)
    west = vincenty(kilometers=distance).destination(geopy.Point(origin), 270)

    # get bounding box: (min lat, max lat, min lng, max lng)
    geo_box = (south.latitude, north.latitude, west.longitude, east.longitude)

    return geo_box


def plot_hotspots(good_hotspots, prob_seen, titles):
    '''

    plot_hotspots(good_hotspots, prob_seen, titles)

    :param good_hotspots: dictionary of hotspot info, including lat, lng, and expected_n
    :param prob_seen: len(good_hotspots) x len(new_birds) array of probabilities
    :param titles:
    :return:
    '''
    # plot heat map of bird probabilities
    # usage: plot_hotspots(good_hotspots, prob_seen, titles)

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

    # plot heat map
    axes.imshow(prob_seen, interpolation = 'none')

    # TODO: add notable if exits!
    # # highlight notable birds by coloring names in red
    # all_notable = set()
    # [all_notable.update(z['notable']) for z in good_hotspots]
    # # pprint(all_notable)
    #
    # [i.set_color("red") for i in plt.gca().get_xticklabels() if i.get_text() in all_notable]

    plt.title(titles['title'])
    show()


def google_map(good_hotspots):
    # show a Google map of hotspots ranked by goodness!

    marker_colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'black']
    max_hotspots = 20

    # sort hotspots by number of birds!
    hs_sort = sorted(good_hotspots, key=lambda x: x['expected_n'], reverse=True)
    
    if len(good_hotspots) >= 5:
        ind_cutoff = int(len(good_hotspots)*0.2)
        cutoff = 'Top 20%'
    else:
        ind_cutoff = len(good_hotspots)
        cutoff = 'All good'
        
    print '\n%s of hotspots:' % cutoff
    for idx, hs in enumerate(hs_sort):
        if idx == ind_cutoff:
            print '\nOthers'
        print '%i: %s , expected number of new birds = %.2f' % (idx+1, hs['locality'], hs['expected_n'])

    use_good = hs_sort[:ind_cutoff]
    use_bad = hs_sort[ind_cutoff:]

    # Generate URL with markers
    base_url = 'http://maps.googleapis.com/maps/api/staticmap?&size=1000x1000&sensor=false]'

    url_param = ''
    # markers for good hotspots
    url_param = '&markers=size:mid%%7Ccolor:%s' %marker_colors[0]
    ind = 0
    for x in use_good:
        url_param += '&markers=size:mid%%7Ccolor:%s%%7Clabel:%i' %(marker_colors[ind], ind+1)
        url_param += '%%7C%f,%f' %(x['lat'], x['lng'])
        ind += 1

    url_param += '&markers=size:tiny%%7Ccolor:%s' % marker_colors[-1]
    for x in use_bad:
        url_param += '%%7C%f,%f' %(x['lat'], x['lng'])

    image_bytes = urllib.urlopen(base_url+url_param).read()
    image = Image.open(StringIO(image_bytes))  # StringIO makes file object out of image data

    Image._show(image)

    return


def text_to_fig(lines, top_loc, left_loc, text_col, step_size, lines_per_column):
    # display text in figure in columns

    font_size = 10

    for i_line, this_line in enumerate(lines):
        if mod(i_line, lines_per_column) == 0 and i_line != 0:
            left_loc += 0.2
        figtext(left_loc, top_loc - step_size*mod(i_line,lines_per_column),
                this_line[:25],
                size=font_size, color=text_col)


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

    geo = {}
    if info['status'] != 'ZERO_RESULTS':
        geo = {'formatted_address': info['results'][0]['formatted_address'],
            'lat': info['results'][0]['geometry']['location']['lat'],
            'lng': info['results'][0]['geometry']['location']['lng']}
    else:
        print 'Could not find ' + location

    return geo
