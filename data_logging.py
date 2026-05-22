import os
from datetime import date
import csv
import glob
import math

final_columns=[1, 0, math.nan, math.nan]

def find_files(folder, scene, participant):
    # get latest session only
    if os.path.exists(folder):
        # setting up the data logging folder and participant name
        data_folder = os.path.join(folder, participant)
        files = glob.glob(os.path.join(data_folder, '*.csv'))
        sessions = [int(file.split('\\')[-1].split('_')[0].split('S')[1]) for file in files]
        if(len(sessions)>0):
            session = str(max(sessions))
        else:
            session = '0'
        filtered_files = glob.glob(os.path.join(data_folder, '*S'+session+'_'+str(date.today())+'*.csv'))
        
        filename_base = filtered_files[0].rsplit('_', 1)[0]+'_'
    else:
        print('The data-saving folder selected does not exist.')
    return filtered_files, filename_base

def save_file(base, timestamp, data_type, data_values):
    filename=base+data_type+'.csv'
    
    data_line=[timestamp]+[x for x in data_values.strip('()').split(',')]
    # add appropriate values for last column
    if(data_type=='position'):
        data_line.append('1')
    elif(data_type=='rotation'):
        data_line.append('0')
        
    with open(filename, 'a', newline='') as file:
            writer = csv.writer(file) 
            writer.writerow(data_line)

def is_nan(val):
    return isinstance(val, float) and math.isnan(val)

def save_data(arg):
    files, base = find_files(arg['folder'], arg['scene'], arg['participant'])
    data_to_save = {key: arg[key] for key in ['time', 'position', 'rotation', 'wheels', 'motion'] if key in arg} #dict(list(arg.items())[3:])
    
    for i in range(len(data_to_save)-1):
        # only save if data was received
        if((list(data_to_save.values())[i+1]) is not None):
            save_file(base, data_to_save['time'], list(data_to_save.keys())[i+1], list(data_to_save.values())[i+1])
            
if __name__ == "__main__":
    arg = {"folder": r'D:\Maria_school\Documents\S2026\data',
           "scene": "scene",
           "participant": "test",
           "time": '0000000000.000',
           "position": '(0,0,0)',
           "rotation": '(0,0,0)',
           "wheels": math.nan,
           "motion": math.nan}

    save_data(arg)