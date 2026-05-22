import os
from datetime import date
import csv
import glob

# different data types that could be saved
data_types = ['position', 'rotation', 'wheels', 'motion']
# number of columns to write in file (per data_type) [for now, placeholder numbers for wheels and motion]
data_columns = [4, 4, 1, 1]

def make_folder(data_folder, participant):
    folder = os.path.join(data_folder, participant)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder

def get_session(folder):
    # determining which session number we should write to (to not over-write data)
    files = glob.glob(os.path.join(folder, '*.csv'))
    if(len(files))>0:
        sessions = [int(file.split('\\')[-1].split('_')[0].split('S')[1]) for file in files]
        session = str(max(sessions)+1)
    else:
        session = '0'
    return session

def make_header(type_index):
    header=['time']+[data_types[type_index]+'[:,'+str(i)+']' for i in range(data_columns[type_index])]
    return header

def make_filenames(session, scene, data_to_save):
    files=[]
    headers=[]
    for i in range(len(data_types)):
        if data_to_save[i]==True:
            files.append('S'+session+'_'+str(date.today())+'_'+scene+'_'+data_types[i]+'.csv')
            headers.append(make_header(i))
    return files, headers

def make_csv(folder, filename, header):
    with open(os.path.join(folder, filename), 'w', newline='') as file:
                writer = csv.writer(file) 
                writer.writerow(header)

def create_files(arg):
    folder = make_folder(arg['folder'], arg['participant'])
    session = get_session(folder)
    
    data_to_save =[arg['player_position'], arg['player_rotation'], arg['instrumented_wheels'], arg['motion_capture']]
    filenames, headers = make_filenames(session, arg['scene'], data_to_save)
    
    for i in range(len(filenames)):
        make_csv(folder, filenames[i], headers[i])
        print('Created '+filenames[i])

if __name__ == "__main__":
    arg = {"folder": r'D:\Maria_school\Documents\S2026\data',
           "scene": "scene",
           "participant": "test",
           "player_position": True,
           "player_rotation": True,
           "instrumented_wheels": False,
           "motion_capture": False}

    create_files(arg)