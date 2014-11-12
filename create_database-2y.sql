# to run
# $ time cat create_database-2y.sql | mysql -uroot --table

# Select database
use kestrel2y; # Jan 2012- Feb 2014 as of 11/07/2014, from ebd_relFeb-2014 data dump

# ###################
# # Create raw table
drop table if exists raw;
create table raw (

# Data schema
global_unique_identifier varchar(255),
taxonomic_order double,
category varchar(32), # spuh, slash, species, ISSF, hybrid, intergrade, domestic, or form
common_name varchar(255),
scientific_name varchar(255),
subspecies_common_name varchar(255),
subspecies_scientific_name varchar(255),
observation_count varchar(8), # varchar because can include 'x'
breeding_bird_atlas_code varchar(100),  # will not use
age_sex varchar(255), # will not use
country varchar(255),
country_code varchar(2),
state varchar(255),
state_code varchar(5),
county varchar(255),
county_code varchar(8),
iba_code varchar(255),  # will not use
locality varchar(255), # hotspot!!
locality_id varchar(100),
locality_type varchar(2),
latitude double,
longitude double,
observation_date date default 0,
time_observation_started timestamp default 0,
trip_comments varchar(255),
species_comments varchar(255),
observer_id varchar(255),
first_name varchar(255),
last_name varchar(255),
sampling_event_identifier varchar(255),
protocol_type varchar(255),
project_code varchar(255),
duration_minutes int,
effort_distance_km double,
effort_area_ha double,
number_observers int,
all_species_reported bit(1),
group_identifier varchar(255),
approved bit(1),
reviewed bit(1),
reason varchar(255)

);
# describe raw;
select('Created raw');
# load data local
infile '/Users/Alexandra/PycharmProjects/trip_bird/data/raw-2y.tsv'
into table raw
fields terminated by '\t'
ignore 1 lines;
show warnings;

select count(*) as n_raw from raw;


create index idx_id_sei on raw (locality_id, sampling_event_identifier); # 51 minutes
create index idx_sei on raw (sampling_event_identifier);

select('Created indices on raw');
# ###################
# # Create observers table

drop table if exists observers;
create table observers (
  pk int not null auto_increment,
  id varchar(255) not null,
  first_name varchar(255),
  last_name varchar(255),
  primary key (pk)
);

insert into observers (id, first_name, last_name)
select observer_id, first_name, last_name
from raw
group by observer_id, first_name, last_name;

select count(*) as n_observers from observers;
# select count(*) as n from observers group by id having n>1;

create index idx_id on observers(id);

select('Created observers indices');


# ###################
# # Create species table

drop table if exists species;
create table species (
  pk int not null auto_increment,
  common_name varchar(255),
  scientific_name varchar(255),
  primary key (pk)
);

#Other relevant fields:
#subspecies_common_name varchar(255),
#subspecies_scientific_name varchar(255),
#taxonomic_order double,
#category varchar(32), # spuh, slash, species, ISSF, hybrid, intergrade, domestic, or form

insert into species (
    common_name,
    scientific_name)
select
    common_name,
    scientific_name
from raw
group by
    common_name
;

# Other useful fields:
#    taxonomic_order,
#    category
#    subspecies_common_name,
#    subspecies_scientific_name)

# Test: count scientific_name repeats. If sci name is unique
# for each common name (expected) this should return an empty set
# select count(*) as n from species group by scientific_name having n > 1 order by n;

select count(*) as n_species from species;

create index idx_common_name on species(common_name);
create index idx_scientific_name on species(scientific_name);

select('Created species indices');



# ###################
# # Create locations table

drop table if exists locations;
create table locations (
  pk int not null auto_increment,
  locality_type varchar(2),
  latitude double not null,
  longitude double not null,
  id varchar(100) not null,
  locality varchar(255) not null, # hotspot!!
  county varchar(255),
  county_code varchar(8),
  state varchar(255),
  state_code varchar(5),
  country varchar(255),
  country_code varchar(2),
  primary key (pk)
);

insert into locations (
  locality_type,
  latitude,
  longitude,
  id,
  locality,
  county,
  county_code,
  state,
  state_code,
  country,
  country_code)
select
  locality_type,
  latitude,
  longitude,
  locality_id,
  locality,
  county,
  county_code,
  state,
  state_code,
  country,
  country_code
from raw
group by
  locality_id
;

# # TODO make case SENSITIVE:
alter table locations change locality locality varchar(255) not null collate utf8_bin;

# change it back!
# alter table locations change locality locality varchar(255) not null collate utf8_general_ci;


select count(*) as n_locations from locations;

# Test: the below should have the same number of rows as locations:
# select count(*) from (select locality_id from raw group by locality_id) A;

# drop index idx_locality on locations;

create index idx_id on locations (id);
create index idx_locality_type on locations (locality_type);
create index idx_locality on locations (locality); # 4 s
create index idx_state on locations (state);
create index idx_country on locations (country);
create index idx_country_code on locations (country_code);

create index idx_lat_lng on locations (latitude, longitude);

select('Created location indices');


# # ###################
# # Create checklists table

# NOt included:
# protocol_type
# number_observers
# reason - "in this dataset always "introduced-exotic" for not accepted


drop table if exists checklists2;
create table checklists2 (
  pk int not null auto_increment,
  observation_date date default 0 not null,
  time_observation_started timestamp default 0,
  locality_id varchar(100),
  locations_pk int,
  sampling_event_identifier varchar(255),
  n_sightings_per_checklist int,
  duration_minutes int,
  all_species_reported bit(1),
  group_identifier varchar(255),
  approved bit(1),
  reviewed bit(1),
  primary key (pk)
);

insert into checklists2 (
  observation_date,
  time_observation_started,
  locality_id,
  locations_pk,
  sampling_event_identifier,
  n_sightings_per_checklist,
  duration_minutes,
  all_species_reported,
  group_identifier,
  approved,
  reviewed
   )
select
    observation_date,
    time_observation_started,
    locality_id,
    null, # locality_pk, will add later
    sampling_event_identifier,
    count(*), # number of species per checklist
    duration_minutes,
    all_species_reported,
    group_identifier,
    approved,
    reviewed
from raw
group by sampling_event_identifier
; # 4 hours, 4.8 million rows

create index idx_locality_id on checklists2 (locality_id);


# TODO NEXT: join checklists 2 to locations to get locations_pk; rename table
# update statement
update checklists2, locations
set checklists2.locations_pk = locations.pk
where locations.id = checklists2.locality_id
; # 10 minutes
rename table checklists2 to checklists;

create index idx_sei on checklists (sampling_event_identifier);
create index idx_locations_pk on checklists (locations_pk);


# locations.id,
# join locations on locations.id = raw.locality_id
# where locations.locality_type = 'H'



# drop table if exists checklists;
# create table checklists (
#   pk int not null auto_increment,
#   observation_date date default 0 not null,
#   time_observation_started timestamp default 0,
#   raw_locality_id varchar(100),
#   locality_pk int,
#   sampling_event_identifier varchar(255),
#   n_sightings_per_checklist int,
#   duration_minutes int,
#   all_species_reported bit(1),
#   group_identifier varchar(255),
#   approved bit(1),
#   reviewed bit(1),
#   reason varchar(255),
#   primary key (pk)
# );
#
# insert into checklists (
#   observation_date,
#   time_observation_started,
#   raw_locality_id,
#   locality_pk,
#   sampling_event_identifier,
#   n_sightings_per_checklist,
#   duration_minutes,
#   all_species_reported,
#   group_identifier,
#   approved,
#   reviewed
#    )
# select
#     observation_date,
#     time_observation_started,
#     raw.locality_id,
#     locations.pk,
#     sampling_event_identifier,
#     count(*),
#     duration_minutes,
#     all_species_reported,
#     group_identifier,
#     approved,
#     reviewed
# from raw
# join locations on locations.id = raw.locality_id
# group by locations.id, sampling_event_identifier
# ;
#
#
# where locations.locality_type = 'H'


# 
# drop table if exists checklists;
# create table checklists (
#   pk int not null auto_increment,
#   observation_date date default 0 not null,
#   time_observation_started timestamp default 0,
#   comments varchar(255),
#   observer_pk int not null,
#   location_pk int not null,
#   sampling_event_identifier varchar(255),
#   protocol_type varchar(255),
#   project_code varchar(255),
#   duration_minutes int,
#   effort_distance_km double,
#   effort_area_ha double,
#   number_observers int,
#   all_species_reported bit(1),
#   group_identifier varchar(255),
#   approved bit(1),
#   reviewed bit(1),
#   reason varchar(255),
#   primary key (pk)
# );
# 
# insert into checklists (
#   observation_date,
#   time_observation_started,
#   comments,
#   observer_pk,
#   location_pk,
#   sampling_event_identifier,
#   protocol_type,
#   project_code,
#   duration_minutes,
#   effort_distance_km,
#   effort_area_ha,
#   number_observers,
#   all_species_reported,
#   group_identifier,
#   approved,
#   reviewed,
#   reason
# )
# select
#   observation_date,
#   time_observation_started,
#   trip_comments,
#   observers.pk,
#   locations.pk,
#   sampling_event_identifier,
#   protocol_type,
#   project_code,
#   duration_minutes,
#   effort_distance_km,
#   effort_area_ha,
#   number_observers,
#   all_species_reported,
#   group_identifier,
#   approved,
#   reviewed,
#   reason
# from observers
#   join raw on observers.id = raw.observer_id
#   join locations on locations.locality = raw.locality
# group by sampling_event_identifier
# ;
# 
# create index idx_observation_date on checklists(observation_date);
# create index idx_sampling_event_identifier on checklists(sampling_event_identifier);
# 
# select count(*) as n_checklists from checklists;

# ###################
# # Create sightings table

# TODO: add observation_count??

drop table if exists sightings;
create table sightings (
  pk int not null auto_increment,
  global_unique_identifier varchar(255),
  observation_date date default 0 not null,
  time_observation_started timestamp default 0,
  species_comments varchar(255),
  species_pk int not null,
  observers_pk int not null,
  locations_pk int not null,
  sampling_event_identifier varchar(255),
  protocol_type varchar(255),
  duration_minutes int,
  effort_distance_km double,
  effort_area_ha double,
  number_observers int,
  all_species_reported bit(1),
  group_identifier varchar(255),
  approved bit(1),
  reviewed bit(1),
  reason varchar(255),
  primary key (pk)
);

insert into sightings (
  global_unique_identifier,
  observation_date,
  time_observation_started,
  species_comments,
  species_pk,
  observers_pk,
  locations_pk,
  sampling_event_identifier,
  protocol_type,
  duration_minutes,
  effort_distance_km,
  effort_area_ha,
  number_observers,
  all_species_reported,
  group_identifier,
  approved,
  reviewed,
  reason
)
select
  global_unique_identifier,
  observation_date,
  time_observation_started,
  species_comments,
  species.pk,
  observers.pk,
  locations.pk,
  sampling_event_identifier,
  protocol_type,
  duration_minutes,
  effort_distance_km,
  effort_area_ha,
  number_observers,
  all_species_reported,
  group_identifier,
  approved,
  reviewed,
  reason
from raw
join species on species.common_name = raw.common_name
join observers on observers.id = raw.observer_id
join locations on locations.id = raw.locality_id
;

select count(*) as n_sightings from sightings;

create index idx_species_pk on sightings(species_pk);
create index idx_locations_pk on sightings(locations_pk); # 37 minutes
create index idx_observation_date on sightings(observation_date); # 14 minutes
create index idx_observers_pk on sightings(observers_pk); # TODO: build!!
create index idx_sei on sightings(sampling_event_identifier); # 30 minutes


# Nov 8: total time: ~181 m
# observers: 24m
# species: ?
# locations + sightings = 133m
