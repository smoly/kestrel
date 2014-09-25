# Kestrel

Traveling birder? Kestrel helps naturalists traveling to new places find birds that they cannot find at home. It helps you identify target locations to increase the chances of seeing birds that are not found in your stomping grounds. It also highlights regionally important or otherwise notable birds to help the you pick the best hot spot and brush up on field mark details.


Powered by the awesome [eBird API](https://confluence.cornell.edu/display/CLOISAPI/eBird+API+1.1).

## Quick Start

Don’t care about the details, just want to look at a heatmap?
```python
from getNewBirds import * 
find_good_hotspots('Philadelphia', 'San Francisco', 20) 
```
 `'Philadelphia'` is my "home" and `'San Francisco'` is my destination. These can be any googlable location names. `20` is the radius for each region in km. 

plots this heatmap (click to see full-size):
![sample output](https://cloud.githubusercontent.com/assets/2320606/4396693/9614cc18-4437-11e4-8935-adff1a649b19.png)

Red indicates high probability of observing a bird (x-axis) at a hotspot (y-axis), blue indicates low probability. 
- Birds on the x-axis include only those that have not been reported in your "home" location in the last 30 days.
- Note how some birds (columns), like Anna's hummingbird, are common everywhere. You probably won't need to go to a special place to find them.
- "notable" species names are colored in red, these might be worth a detour. Acorn woodpecker at Buena Vista Park? Yes, please!

## Playing with bird lists and hotspot details
If you assign outputs, 
```python
[good_hotspots, prob_array, bird_list] = find_good_hotspots(here, there, distance)
```
you get:
- `good_hotspots`: dictionary with information about each hotspot with >10 observations in 
```python
In[36]: good_hotspots[5]
Out[36]: 
{'birds': [(u"Anna's Hummingbird", 1.0), # bird name and probability of seeing it at this hotspot
  (u'Pygmy Nuthatch', 0.90909090909090906),
  (u'Western Tanager', 0.90909090909090906),
  (u"Steller's Jay", 0.90909090909090906),
  (u'California Towhee', 0.72727272727272729),
  (u'Pacific-slope Flycatcher', 0.72727272727272729),
  (u'Chestnut-backed Chickadee', 0.63636363636363635),
  (u"Townsend's Warbler", 0.63636363636363635),
  (u'Black Phoebe', 0.36363636363636365),
  (u"Hutton's Vireo", 0.27272727272727271),
  (u'Dark-eyed Junco', 0.27272727272727271),
  (u'oriole sp.', 0.18181818181818182),
  (u'American Coot', 0.18181818181818182),
  (u'White-crowned Sparrow', 0.18181818181818182),
  (u'Brown Creeper', 0.18181818181818182),
  (u'Black-headed Grosbeak', 0.18181818181818182),
  (u'Orange-crowned Warbler', 0.18181818181818182),
  (u'Western Scrub-Jay', 0.18181818181818182),
  (u'Western Gull', 0.090909090909090912),
  (u'Fox Sparrow', 0.090909090909090912),
  (u'Pacific Wren', 0.090909090909090912),
  (u"Nuttall's Woodpecker", 0.090909090909090912),
  (u'Bushtit', 0.090909090909090912)],
 'expected_n': 9.0909090909090917,
 'locID': u'L743012',
 'locName': u'Golden Gate Park--Middle Lake', # hotspot name
 'notable': {u'American Redstart'}}  #  notable birds found here and not at home
```
- `prob_array`: an array of probabilities of observing each bird in each hotspot. It is sized `len(good_hotspots)` by `len(bird_list)`
```python
In[37]: prob_array
Out[37]: 
array([[ 0.42857143,  0.        ,  0.82142857, ...,  1.        ,
         0.        ,  0.        ],
       [ 0.32      ,  0.        ,  0.92      , ...,  1.        ,
         0.        ,  0.        ],
       ...
       ])
         
```
- `bird_list`: the list of all birds seen in the destination that cannot be found at home
```python
In[42]: bird_list
Out[42]: 
[u"Hutton's Vireo",
 u'Zonotrichia sp.',
 u'Pygmy Nuthatch',
 u'Great-tailed Grackle',
 u'Golden-crowned Sparrow,
 ...
 ]
```

## Module components
If you'd like to dig deeper, read on!

start with 
```python
from getNewBirds import * 
```
1) Get list of birds found at the destination but not at home:
```python
In[11]: new_birds = get_new_birds('Philadelphia', 'San Francisco', 20)
Finding birds within 20.00 km of San Francisco, CA, USA
that are not found within 20.00 km of Philadelphia, PA, USA
In[12]: new_birds
Out[12]: 
[u"Hutton's Vireo",
 u'Zonotrichia sp.',
 u'Pygmy Nuthatch',
 u'Great-tailed Grackle',
 u'Golden-crowned Sparrow',
 u'Violet-green Swallow',
  ...
]
```

2) Get list of hotspots within 20 km of destination:
```python
In[13]: hotspots = get_hotspots('San Francisco', 20)
Finding hotspots in San Francisco
In[14]: hotspots
Out[14]: 
[[u'Agua Vista Park', u'L486458'],
 [u'Albany Mudflats', u'L484238'],
 [u'Alcatraz Island', u'L253857'],
 [u'Alemany Farm', u'L2415053'],
 [u'Balboa Park (SF Co.)', u'L2769960'],
 [u'Ballena Bay', u'L594831'],
 [u'Bayview Park (SF Co.)', u'L1292481'],
 [u'Bernal Hill', u'L668844'],
 ...
 ]
```

3) Count observations of a bird at a hotspot:
  These values are the number checklists in which each bird was reported in the last 30 days.
```python
In[18]: num_seen = get_counts(new_birds, hotspots[0][1])
  Counting sightings in Agua Vista Park
In[19]: zip(new_birds, num_seen)
Out[19]: 
[(u"Hutton's Vireo", 0),
 (u'Zonotrichia sp.', 0),
 (u'Pygmy Nuthatch', 0),
 (u'Great-tailed Grackle', 0),
 (u'Golden-crowned Sparrow', 0),
 (u'Violet-green Swallow', 0),
 (u'California Quail', 0),
 (u'Black-throated Gray Warbler', 0),
 ...
 ]
```

4) Get notable observations from a hotspot
```python
In[25]: notable = get_notable(hotspots[15][1])
In[26]: notable
Out[26]: {u'Acorn Woodpecker', u'Blackpoll Warbler', u"Lewis's Woodpecker"}

```


