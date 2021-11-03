'''
This script's job is to identify all data where MIDPOINT REGISTRATION is needed
1. CHECK IF DONE (QUERY analysis/midpoint/) to see if midpoint T1 images created using: SPM12, ANTS and NIFTY_REG exist.
2. CHECK IF PREREQ IS THERE: T1 baseline and T1 followup
3. ADD TO LIST, remove duplicates and print
'''
import requests
import csv
import datetime as dt
import os
from utils import refresh_cookies,get_credentials

requests.packages.urllib3.disable_warnings()
xnat_host='https://nimg1946.cs.ucl.ac.uk'
username,login,pw=get_credentials(xnat_host,
                                  os.path.expanduser('~/.daxnetrc'))
headers=refresh_cookies(xnat_host,username,pw,None)
data_root='/SAN/medic/insight46'

actual_list=[]

#Get all MR sessions
url_sessions=xnat_host+'/REST/experiments?' + \
    'xsiType=xnat:mrSessionData&project=1946'
r=requests.get(url_sessions,headers=headers)
session_list=r.json()

for session in sorted(session_list['ResultSet']['Result'],
                      key=lambda k: k['subject_label']):
    #print(session)
    sesdict = {
        "subject_label": session['subject_label'],
        "label": session['label']
    }
    actual_list.append(sesdict)

#now add PETMR sessions
url_sessions=xnat_host+'/REST/experiments?' + \
    'xsiType=xnat:petmrSessionData&project=1946'
r=requests.get(url_sessions,headers=headers)
session_list=r.json()

for session in sorted(session_list['ResultSet']['Result'],
                      key=lambda k: k['subject_label']):
    sesdict = {
        "subject_label": session['subject_label'],
        "label": session['label']
    }
    actual_list.append(sesdict)

num_sessions = 0
sessions_to_submit=[]
#methods=['spm12','ants','nifty-reg']
#only running SPM for now
methods=['spm-midpoint']


for session in actual_list:
    
    num_sessions += 1

    #For each subject, does the midpoint T1 already exist?
    subject_id=session['subject_label']
    session_id=session['label']
    mid_tag='midpoint'

    print 'Subject: ' + subject_id + "   Session: " + session_id
    visit_id=session_id.split('_')[1]
    if visit_id=='01':
        visit_tag='baseline'
    elif visit_id=='02':
        visit_tag='followup'
    else:
        print('Incorrect session label: ' + visit_id)

    for method_tag in methods:
        
        mid_t1_file=os.path.join(data_root,'analysis','midpoint',
                                     'sub-'+subject_id,
                                     'ses-'+mid_tag,'anat',
                                     'sub-'+subject_id + '_ses-' + mid_tag +
                                     '_T1w_run-1_desc-gradwarp_' + method_tag + '.nii.gz')
        #print(gif_labels_file)
        # First check if midpoint T1 has already been run
        if os.path.exists(mid_t1_file):
            print(method_tag +' midpoint T1 already completed. No action')
        else:
            print(method_tag +' midpoint T1 does not exist, looking for T1 images')

            #IF bl session is 'Nope' then search sessions to submit for matching ID number and set to that, same for missing followup
            bl_session='Nope'
            fu_session='Nope'

            if visit_id=='01':
                bl_session=session_id
                filt_sess=next(iter(filter(lambda sess: sess['subject_label'] == subject_id and sess['followup_session'] != 'Nope', sessions_to_submit)), None)
                if filt_sess:
                    fu_session=filt_sess['followup_session']

            else:
                fu_session=session_id
                filt_sess=next(iter(filter(lambda sess: sess['subject_label'] == subject_id and sess['baseline_session'] != 'Nope', sessions_to_submit)), None)
                if filt_sess:
                    bl_session=filt_sess['baseline_session']
            
            

            bl_t1_img=os.path.join(data_root,'analysis','gradwarp','sub-'+subject_id,'ses-baseline','anat','sub-'+subject_id+'_ses-baseline_T1w_run-1_desc-gradwarp.nii.gz')
            fu_t1_img=os.path.join(data_root,'analysis','gradwarp','sub-'+subject_id,'ses-followup','anat','sub-'+subject_id+'_ses-followup_T1w_run-1_desc-gradwarp.nii.gz')

            if os.path.exists(bl_t1_img) and os.path.exists(fu_t1_img):
                print('Adding ' + subject_id + ' data to process')
                session_details={'subject_label': subject_id,
                                 'baseline_session': bl_session,
                                 'followup_session': fu_session,
                                 'baseline_t1': bl_t1_img,
                                 'followup_t1': fu_t1_img}
                sessions_to_submit.append(session_details)
            elif os.path.exists(bl_t1_img):
                print(subject_id + ' followup gradwarp T1 missing')
            elif os.path.exists(fu_t1_img):
                print(subject_id + ' baseline gradwarp T1 missing')
            else:
                print(subject_id + ' both timepoint gradwarp T1 missing')


#Remove rows with missing sessions
sessions_to_submit=iter(filter(lambda sess: sess['baseline_session'] != 'Nope' and sess['followup_session'] != 'Nope', sessions_to_submit))
#Remove remaining  duplactes (as both timepoint sessions got selected, for each method)
sessions_to_submit=[dict(tupleized) for tupleized in set(tuple(item.items()) for item in sessions_to_submit)]

sessions_to_submit=sorted(sessions_to_submit,key=lambda k: k['subject_label'])

if sessions_to_submit:
    today=dt.datetime.now()
    out_csv='/SAN/medic/insight46/jobs/midpoint_submit_list_' + \
        today.strftime('%Y%m%d_%H%M%S') + '.csv'
    with open(out_csv, 'wb') as csvfile:
        fieldnames=['subject_label','baseline_session','followup_session','baseline_t1','followup_t1']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames,
                                lineterminator=os.linesep)
        writer.writeheader()
        for i in sessions_to_submit:
            writer.writerow(i)

    print('Job file written to: ' + out_csv)



