# kestrel

Traveling birder? Kestrel helps naturalists traveling to new places find birds that they cannot find at home. It helps you identify target locations to increase the chances of seeing birds that are not found in your stomping grounds. It also highlights regionally important or otherwise notable birds to help the you pick the best hot spot and brush up on field mark details.

Data from the [eBird basic dataset](http://ebird.org/ebird/data/download) (Version: EBD_relNov-2013) and [eBird API](https://confluence.cornell.edu/display/CLOISAPI/eBird+API+1.1).

## Getting started
This version requires building a local MySQL database from the eBird basic dataset available at http://ebird.org/ebird/data/download. The download is about 6GB and uncompresses to about 60GB. 

I first selected the last 3 years of data to put into the database, reducing it to ~27GB. The data schema is in `create_database-2y.sql` and results in a ~12GB database.

### Look at some plots
To look for birds that can be found in San Francisco but not Philadelphia in November:
```python
from kestrel import * 
find_good_hotspots('Philadelphia', 'SF, CA', 10, 11) 
```
 `'Philadelphia'` is my "home" and `'San Francisco'` is my destination. These can be any googlable location names. `10` is the radius around each region that will be searched for new birds and locations. `11` is the month in which to look for birds.

I first get a list of all the new birds that can be found in within 10km of my destination + the only venn diagram I have ever made :P :

![sample venn](https://cloud.githubusercontent.com/assets/2320606/5071996/575f998a-6e44-11e4-8d9c-3e50a819ef5e.png)

Next we get the core result, a heatmap of the probability of observing each new bird at each hotspot in the region (click to see full-size):

![sample heatmap](https://cloud.githubusercontent.com/assets/2320606/5071985/452ebe6c-6e44-11e4-9ccb-dd5b5f7d85cc.png)

Red indicates a high probability of observing a bird (column) at a hotspot (row), blue indicates low probability. 
- Birds on the x-axis include only those that have not been reported in your home location in the requested month. These are sorted by the average probability of observing each bird across all hotspots so you're most likely to see birds on the left of this graph.
- Note how some birds (columns), like the Western gull and Anna's hummingbird, are common everywhere. You probably won't need to go to a special place to find them.
- Hotspots are also sorted by the expected number of new birds at each location. The top-most hotspots will have the largest expected number of new birds. 
- 
And just for fun, we get a static google map with the top hotpots:

![sample map](https://cloud.githubusercontent.com/assets/2320606/5072006/738d2438-6e44-11e4-9157-512cfa7c9603.png)

Their names and values of the expected bird count is printed to the terminal.

