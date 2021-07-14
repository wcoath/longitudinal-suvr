import csv
import datetime as dt
import os
from glob import glob


data_root='/SAN/medic/insight46/midpoint_test'
#data_root==insight_root when testing is finished
insight_root='/SAN/medic/insight46/'

#get all midpoint GIF, won't count any that haven't been run
sessions_to_submit=[]

gif=os.path.join(data_root,'analysis','gif','sub-*','ses-midpoint','anat','*midpoint_labels.nii.gz')

'''
WHAT WE NEED:
1. midpoint  GIF parcellation to clean
2. baseline static PET recon (will use nifyPET pCT for now)
3. followup static PET recon
4. 6 DOF TX from baseline T1 -> baseline PET (specific to each recon, to be converted to def field)
5. 6 DOF TX from followup T1 -> followup PET (specific to each recon, to be converted to def field)
6. deformation field from baseline T1 -> midpoint T1 (will be inveted using reg_transform invNrr, then composed with rigid)
7. deformation field from followup T1 -> midpoint T1 (will be inveted using reg_transform invNrr, then composed with rigid)
8. baseline drc brain mask for cleaning parcellation, could do this a) at midpoint with followup mask too b) after resampling to baseline or c) both
9. followup drc brain mask for cleaning parcellation, could do this a) at midpoint with baseline  mask too b) after resampling to baseline or c) both
'''
#For each session: check input requirments and if already completed
for gif_par_midpoint in glob(gif):
    gif_base=os.path.basename(gif_par_midpoint)
    subject_label=gif_base.split('_')[0]
    subject_id=subject_label.split('-')[1]
    print('Subject: ' + subject_id)
    bl_nipet_pct_recon=os.path.join(insight_root,'analysis','static-pet',subject_label,
                                 'ses-baseline','PET',subject_label + '_ses-baseline_desc-static-50-60-pct-niftypet-itr4.nii.gz')
    fu_nipet_pct_recon=os.path.join(insight_root,'analysis','static-pet',subject_label,
                                 'ses-followup','PET',subject_label + '_ses-followup_desc-static-50-60-pct-niftypet-itr4.nii.gz')
    bl_t1_to_pet_tx=os.path.join(insight_root,'analysis','suvr-nipet-pct-gif-cereb',subject_label,'ses-baseline','xfm',subject_label+'_ses-baseline_from-T1w_to-PET_mode-image_xfm.txt')
    fu_t1_to_pet_tx=os.path.join(insight_root,'analysis','suvr-nipet-pct-gif-cereb',subject_label,'ses-followup','xfm',subject_label+'_ses-followup_from-T1w_to-PET_mode-image_xfm.txt')
    bl_t1_to_mid_def=os.path.join(data_root,'analysis','midpoint',subject_label,'ses-midpoint','xfm','y_'+subject_label+'_ses-baseline_T1w_run-1_desc-gradwarp_spm-midpoint.nii.gz')
    fu_t1_to_mid_def=os.path.join(data_root,'analysis','midpoint',subject_label,'ses-midpoint','xfm','y_'+subject_label+'_ses-followup_T1w_run-1_desc-gradwarp_spm-midpoint.nii.gz')
    bl_brain_mask=os.path.join(insight_root,'analysis','drc_brain',subject_label,'ses-baseline','anat',subject_label+'_ses-baseline_T1w_run-1_space-orig_desc-drc-brain-mask.nii.gz')
    fu_brain_mask=os.path.join(insight_root,'analysis','drc_brain',subject_label,'ses-followup','anat',subject_label+'_ses-followup_T1w_run-1_space-orig_desc-drc-brain-mask.nii.gz')

    data_missing=False
    
    
    if not os.path.exists(bl_nipet_pct_recon):
        data_missing=True
        print('baseline PET RECON missing')

    if not os.path.exists(fu_nipet_pct_recon):
        data_missing=True
        print('followup PET RECON missing')

    if not os.path.exists(bl_t1_to_pet_tx):
        data_missing=True
        print('bl_t1_to_pet_tx missing')

    if not os.path.exists(fu_t1_to_pet_tx):
        data_missing=True
        print('fu_t1_to_pet_tx missing')

    if not os.path.exists(bl_t1_to_mid_def):
        data_missing=True
        print('bl_t1_to_mid_def missing')

    if not os.path.exists(fu_t1_to_mid_def):
        data_missing=True
        print('fu_t1_to_mid_def missing')

    if not os.path.exists(bl_brain_mask):
        data_missing=True
        print('bl_brain_mask missing')

    if not os.path.exists(fu_brain_mask):
        data_missing=True
        print('fu_brain_mask missing')

    if not data_missing:
        session_details={'subject_label': subject_id,
                         'bl_pet_recon': bl_nipet_pct_recon,
                         'fu_pet_recon': fu_nipet_pct_recon,
                         'gif_midpoint': gif_par_midpoint,
                         'bl_t1_to_pet_tx': bl_t1_to_pet_tx,
                         'fu_t1_to_pet_tx': fu_t1_to_pet_tx,
                         'bl_t1_to_mid_def': bl_t1_to_mid_def,
                         'fu_t1_to_mid_def': fu_t1_to_mid_def,
                         'bl_brain_mask': bl_brain_mask,
                         'fu_brain_mask': fu_brain_mask
    }
        sessions_to_submit.append(session_details)
        print('Adding ' + subject_id + ' data to process')
    else:
        print('Unable to submit')
        print('Some data missing')

if sessions_to_submit:
    today=dt.datetime.now()
    out_csv='/SAN/medic/insight46/midpoint_test/jobs/longitudinal_suvr_submit_list_' + \
        today.strftime('%Y%m%d_%H%M%S') + '.csv'
    with open(out_csv, 'wb') as csvfile:
        fieldnames=['subject_label','bl_pet_recon','fu_pet_recon',
                     'gif_midpoint','bl_t1_to_pet_tx','fu_t1_to_pet_tx',
                     'bl_t1_to_mid_def','fu_t1_to_mid_def','bl_brain_mask','fu_brain_mask']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames,
                                lineterminator=os.linesep)
        writer.writeheader()
        for i in sessions_to_submit:
            writer.writerow(i)
