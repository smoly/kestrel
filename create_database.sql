# to run
# $ cat create_database.sql | mysql -uroot --table

# Select database (= table container)
use kestrel;

####################
## Create raw table
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

load data local
  infile 'raw.tsv'
  into table raw
  fields terminated by '\t'
  ignore 1 lines;
# show warnings;


####################
## Create observer table

drop table if exists observers;
create table observers (
  pk INT NOT NULL AUTO_INCREMENT,
  id varchar(255),
  first_name varchar(255),
  last_name varchar(255),
  primary key (pk)
);

insert into observers (id, first_name, last_name)
select observer_id, first_name, last_name
from raw
group by observer_id, first_name, last_name;

####################
## Create species table

drop table if exists species;
create table species (
  pk int not null auto_increment,
  taxonomic_order double,
  category varchar(32), # spuh, slash, species, ISSF, hybrid, intergrade, domestic, or form
  common_name varchar(255),
  scientific_name varchar(255),
  subspecies_common_name varchar(255),
  subspecies_scientific_name varchar(255),
  primary key (pk)
 );

insert into species (
    taxonomic_order,
    category,
    common_name,
    scientific_name,
    subspecies_common_name,
    subspecies_scientific_name)
select
    taxonomic_order,
    category,
    common_name,
    scientific_name,
    subspecies_common_name,
    subspecies_scientific_name
from raw
group by
    taxonomic_order,
    category,
    common_name,
    scientific_name,
    subspecies_common_name,
    subspecies_scientific_name
;

####################
## Create locations table

drop table if exists locations;
create table locations (
  pk int not null auto_increment,
  locality_type varchar(2),
  latitude double,
  longitude double,
  locality_id varchar(100),
  locality varchar(255), # hotspot!!
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
  locality_id,
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
;

####################
## Create sightings table

drop table if exists sightings;
create table sightings (
  pk int not null auto_increment,
  global_unique_identifier varchar(255),
  species_comments varchar(255),
  species_pk int,
  locality_pk int,
  checklist_pk int,
  primary key (pk)
);


# TODO: fill table!

####################
## Create checklist table

drop table if exists checklists;
create table checklists (
  pk int not null auto_increment,
  observation_date date default 0,
  time_observation_started timestamp default 0,
  comments varchar(255),
  observer_pk int,
  location_pk int,
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
  reason varchar(255),
  primary key (pk)
);

insert into checklists (
  observation_date,
  time_observation_started,
  comments,
  observer_pk,
  location_pk,
  sampling_event_identifier,
  protocol_type,
  project_code,
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
  observation_date,
  time_observation_started,
  trip_comments,
  observers.pk,
  locations.pk,
  sampling_event_identifier,
  protocol_type,
  project_code,
  duration_minutes,
  effort_distance_km,
  effort_area_ha,
  number_observers,
  all_species_reported,
  group_identifier,
  approved,
  reviewed,
  reason
from observers
  join raw on observers.id = raw.observer_id
  join locations on locations.locality = raw.locality
group by sampling_event_identifier
;