% make_migratory_list

% copied into text file list of migratory birds from 
% http://www.fws.gov/migratorybirds/RegulationsPolicies/mbta/mbtandx.html

% remove all text before the comma

%% Open file and read the only line
fid = fopen('/Users/Alexandra/PycharmProjects/trip_bird/data/migratory_birds_orig.txt');

tline = fgets(fid); % all one line!

values = textscan(tline, '%s', ...
        'Delimiter',{',','¨'}, ...
        'MultipleDelimsAsOne', 0);
values = values{1};    

fclose(fid);
%% Only keep scientific name, look for funny characters and then remove
keep = {};
for iVal = 1:length(values),
    if strfind(values{iVal}, 'â€')
        while strfind(values{iVal}, 'â€')
            values{iVal} = values{iVal}(1:end-2);
        end
        
        if strfind(values{iVal}, ' ')
            keep{end+1} = values{iVal};
            disp(keep{end})
            
        end
    end      
end

clear values

%% write to new file
txtID = fopen('/Users/Alexandra/PycharmProjects/trip_bird/data/migratory_birds.tsv', 'wt');
for iVal = 1:length(keep),
    fprintf(txtID, '%s\n', keep{iVal});
end
%%

fclose(txtID);