import argparse
#import pandas as pd
import subprocess
import os
from glob import glob
import requests
import tempfile
from utils import refresh_cookies,get_credentials,get_nifti,get_dicom
from datetime import datetime,timedelta
from shutil import copy2


#TEST RUN SCRIPT FOR MIDPOINT REG

parser = argparse.ArgumentParser(description='Midpoint T1')
parser.add_argument('--subject',type=str,
                    help='Subject ID')
parser.add_argument('--bl_session',type=str,
                    help='Baseline PET-MR session')
parser.add_argument('--fu_session',type=str,
                    help='Followup PET-MR session')
parser.add_argument('--bl_t1',type=str,
                    help='Baseline T1 Scan ID to use')
parser.add_argument('--fu_t1',type=str,
                    help='Followup T1 Scan ID to use')
parser.add_argument('--root_dir', type=str,
                    default='/SAN/medic/insight46',
                    help='Root directory')
parser.add_argument('--spm_dir', type=str,
                    help='SPM directory')
parser.add_argument('--scratch_dir', type=str,
                    help='Temp working directory')
args=parser.parse_args()

if not args.bl_t1:
    parser.error('Submit needs --bl_t1')
elif not args.fu_t1:
    parser.error('Submit needs --fu_t1')
else:
    if args.root_dir:
        data_root=args.root_dir
    else:
        data_root='/SAN/medic/insight46'
    if args.spm_dir:
        spm_dir=args.spm_dir
    else:
        parser.error('Need --spm_dir')
    if args.scratch_dir:
        working_dir=args.scratch_dir
    else:
        parser.error('Need --scratch_dir')

    subject_label='sub-' + args.subject
    print('Subject label: ' + subject_label )
    orig_bl_t1_path=args.bl_t1
    print('Baseline T1 path: ' + orig_bl_t1_path)
    orig_fu_t1_path=args.fu_t1
    print('fu_t1_path: ' + orig_fu_t1_path)
    
    #make new working for baseline and followup 
    tmp_bl_dir=os.path.join(working_dir,subject_label,'ses-baseline','anat')
    tmp_fu_dir=os.path.join(working_dir,subject_label,'ses-followup','anat')
    if not os.path.exists(tmp_bl_dir):
        os.makedirs(tmp_bl_dir)
    if not os.path.exists(tmp_fu_dir):
        os.makedirs(tmp_fu_dir)
    
    #make new out dir
    out_dir=os.path.join(data_root,'analysis','midpoint',
                                 subject_label,'ses-midpoint','anat')
    xfm_dir=os.path.join(data_root,'analysis','midpoint',
                                 subject_label,'ses-midpoint','xfm')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        if not os.path.exists(xfm_dir):
            os.makedirs(xfm_dir)
    ### SPM
    
    #make copy of T1 if it doesn't exist, for SPM
    bl_t1_spm_path=os.path.join(tmp_bl_dir,subject_label+'_ses-baseline_T1w_run-1_desc-gradwarp_spm-midpoint.nii.gz')
    fu_t1_spm_path=os.path.join(tmp_fu_dir,subject_label+'_ses-followup_T1w_run-1_desc-gradwarp_spm-midpoint.nii.gz')
    if not os.path.exists(bl_t1_spm_path):
        copy2(orig_bl_t1_path,bl_t1_spm_path)
    if not os.path.exists(fu_t1_spm_path):
        copy2(orig_fu_t1_path,fu_t1_spm_path)

    #get scan time difference for SPM12 from sessions
    bl_scan_date_str=args.bl_session.split('_')[3]
    bl_scan_date=datetime.strptime(bl_scan_date_str, '%Y%m%d')
    fu_scan_date_str=args.fu_session.split('_')[3]
    fu_scan_date=datetime.strptime(fu_scan_date_str, '%Y%m%d')
    print('Baseline Scan Date: ' + str(bl_scan_date))
    print('Followup Scan Date: ' + str(fu_scan_date))
    delta=fu_scan_date-bl_scan_date
    yrs_dif=float(delta.days)/365.25
    print('Difference in years: ' + str(yrs_dif))
    f = open(os.path.join(xfm_dir,subject_label+"_scan_interval_yrs.txt"), "w") 
    f.write(str(yrs_dif)) 
    f.close() 
    
    #Set up scripts dir for SPM to find 'long_pairwise_job.m' file
    scripts_dir='/SAN/medic/insight46/scripts/'
    
    #unzip files for SPM
    gunzip_cmd=['gunzip',bl_t1_spm_path,fu_t1_spm_path]
    subprocess.call(gunzip_cmd)
    #update file names to unzipped
    bl_t1_spm_path=bl_t1_spm_path.replace(".nii.gz", ".nii")
    fu_t1_spm_path=fu_t1_spm_path.replace(".nii.gz", ".nii")

    #create SPM submit command, then call it
    spm_cmd="matlab -nosplash -nodesktop -r \"addpath([\'"+scripts_dir+"\']) ; long_pairwise_job(\'"+bl_t1_spm_path+"\',\'"+fu_t1_spm_path+"\',"+str(yrs_dif)+",\'"+spm_dir+"\') ; exit\""
    print(spm_cmd)
    subprocess.call(spm_cmd,shell=True)
    
    #re-zip and copy files to output dir
    avg=os.path.join(working_dir,subject_label,'ses-baseline','anat','avg_'+subject_label+'_ses-baseline_T1w_run-1_desc-gradwarp_spm-midpoint.nii')
    if os.path.exists(avg):
        print("zipping "+avg)
        zip_cmd=['gzip',avg]
        subprocess.call(zip_cmd)
        avg_source=avg.replace(".nii", ".nii.gz")
        avg_target=os.path.join(out_dir,subject_label+'_ses-midpoint_T1w_run-1_desc-gradwarp_spm-midpoint.nii.gz')
        print("copying "+avg_source+" to "+avg_target)
        copy2(avg_source,avg_target)

    xfm_list=[os.path.join(working_dir,subject_label,'ses-baseline','anat','dv_'+subject_label+'_ses-baseline_T1w_run-1_desc-gradwarp_spm-midpoint_'+subject_label+'_ses-followup_T1w_run-1_desc-gradwarp_spm-midpoint.nii'),
              os.path.join(working_dir,subject_label,'ses-baseline','anat','y_'+subject_label+'_ses-baseline_T1w_run-1_desc-gradwarp_spm-midpoint.nii'),
              os.path.join(working_dir,subject_label,'ses-followup','anat','y_'+subject_label+'_ses-followup_T1w_run-1_desc-gradwarp_spm-midpoint.nii'),
              os.path.join(working_dir,subject_label,'ses-baseline','anat','jd_'+subject_label+'_ses-baseline_T1w_run-1_desc-gradwarp_spm-midpoint_'+subject_label+'_ses-followup_T1w_run-1_desc-gradwarp_spm-midpoint.nii')]
    
    for spm_file in xfm_list:
        if os.path.exists(spm_file):
            print("zipping "+spm_file)
            zip_cmd=['gzip',spm_file]
            subprocess.call(zip_cmd)
            spm_file=str(spm_file.replace(".nii", ".nii.gz"))
            print("copying "+spm_file+" to "+xfm_dir)
            copy2(spm_file,xfm_dir)
        else:
            print(spm_file+" doesn't exist")

        
    ### ANTs
    #and make copy of T1 for ANTs, don't use SPM copy in case it's been altered
    #bl_t1_ants_path=os.path.join(tmp_bl_dir,subject_label+'_ses-baseline_T1w_run-1_desc-gradwarp_ants.nii.gz')
    #fu_t1_ants_path=os.path.join(tmp_fu_dir,subject_label+'_ses-followup_T1w_run-1_desc-gradwarp_ants.nii.gz')
    #if not os.path.exists(bl_t1_ants_path):
    #    copy2(orig_bl_t1_path,bl_t1_ants_path)
    #if not os.path.exists(fu_t1_ants_path):
    #    copy2(orig_fu_t1_path,fu_t1_ants_path)

    #ants_tmp_dir=os.path.join(working_dir,subject_label,'ants_working')
    #print("creating working directory for ANTs: "+ants_tmp_dir)
    #if not os.path.exists(ants_tmp_dir):
    #    os.makedirs(ants_tmp_dir)

    #create ants command and call it
    #ants_cmd="${ANTSPATH}/antsMultivariateTemplateConstruction.sh \
    #   -d 3 \
    #   -o "+ants_tmp_dir+"/ants_\
    #   -c 1 \
    #   -j 1 \
    #   -i 4 \
    #   -k 1 \
    #   -w 1 \
    #   -n 1 \
    #   -r 1 \
    #   -s CC \
    #   -t S2 \
    #   -g 0.25 \
    #   -b 1 \
    #   "+bl_t1_ants_path+" "+fu_t1_ants_path

    #print(ants_cmd)
    #subprocess.call(ants_cmd,shell=True)
