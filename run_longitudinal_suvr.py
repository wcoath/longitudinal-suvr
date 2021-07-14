import argparse
import tempfile
import os
import sys
from glob import glob
from shutil import copy
from utils import *

def launch_suvr(scratch_dir,bl_pet,fu_pet,mid_par,bl_t1_to_mid,fu_t1_to_mid,bl_t1_to_pet,
                fu_t1_to_pet,mid_to_bl_t1,mid_to_fu_t1,
                bl_brain_mask,fu_brain_mask,roi,midpoint_type,
                console=False,nipet_pct=False,nipet_ute=False,
                erode=False,switch_ref=None,graph=False,
                pvc=False):
    #Set up output direcctory and check if exists and complete
    suvr_tag='suvr-long-'
    acq_type='pct'
    if midpoint_type=='spm':
        suvr_tag += 'spm-'
    elif midpoint_type=='ants':
        suvr_tag += 'ants-'
    elif midpoint_type=='nireg':
        suvr_tag += 'nireg-'
    else:
        #spm default
        suvr_tag += 'spm-'

    if pvc:
        suvr_tag += 'pvc-'

    if console:
        suvr_tag += 'console-'
        acq_type='console'
    elif nipet_pct:
        suvr_tag += 'nipet-pct-'
        acq_type='nipet_pct'
    elif nipet_ute:
        suvr_tag += 'nipet-ute-'
        acq_type='nipet_ute'
    else:
        suvr_tag += 'pct-'

    suvr_tag += 'gif-'
    roi_dash=roi.replace('_','-')
    bl_out_dir = os.path.join(data_root, 'analysis',
                            suvr_tag + roi_dash,
                            subject_label,
                              'ses-baseline')
    fu_out_dir = os.path.join(data_root, 'analysis',
                            suvr_tag + roi_dash,
                            subject_label,
                              'ses-followup')
    if not os.path.exists(bl_out_dir):
        os.makedirs(bl_out_dir)
    if not os.path.exists(fu_out_dir):
        os.makedirs(fu_out_dir)
    if glob(bl_out_dir+'/pet/*.csv') or glob(bl_out_dir+'/pet/*.txt'):
        print('Either missing or baseline already done')
    else:
        pvc_wd=''
        if pvc:
            pvc_wd='_pvc'
        working_dir=os.path.join(scratch_dir,roi+pvc_wd)
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)

        #at the moment just give out dir as baseline, need to sort outputs into bl and fun
        '''
        cmd=['/SAN/medic/insight46/scripts/perform_compute_longitudinal_suvr.py',
             '--roi',roi,'-o', bl_out_dir,'--no_qsub','-n','1']
        '''
        cmd=['/SAN/medic/insight46/scripts/perform_compute_longitudinal_suvr.py',
             '--roi',roi,'-o', bl_out_dir,'--no_qsub','-n','1']
        cmd.append('--working')
        cmd.append(working_dir)
        #if not debug:
        # cmd.append('--remove_tmp')
        
        if switch_ref:
            switch_dash=switch_ref.replace('_','-')
            bl_orig_suvr=os.path.join(data_root, 'analysis',
                                   suvr_tag + switch_dash,
                                   subject_label,
                                      'ses-baseline')
            bl_orig_suvr=os.path.join(data_root, 'analysis',
                                   suvr_tag + switch_dash,
                                   subject_label,
                                      'ses-followup')
            if pvc:
                #switch ref with pvc, need baseline and followup PET in mid and mid labels
                bl_pet_switch=os.path.join(bl_orig_suvr,
                                        'pet',
                                        subject_label+'_ses-baseline_pet_space-midpoint-T1w_desc-pvc-suvr-long-'+
                                        switch_dash+'.nii.gz')
                fu_pet_switch=os.path.join(fu_orig_suvr,
                                        'pet',
                                        subject_label+'_ses-followup_pet_space-midpoint-T1w_desc-pvc-suvr-long-'+
                                        switch_dash+'.nii.gz')
                par_switch=mid_par
                cmd.append('--bl_pet')
                cmd.append(bl_pet_switch)
                cmd.append('--fu_pet')
                cmd.append(fu_pet_switch)
                cmd.append('--mid_par')
                cmd.append(par_switch)
                
            else:
                bl_par_switch=os.path.join(bl_orig_suvr,
                                        'anat',
                                        subject_label+'_ses-baseline_T1w_space-pet_desc_resampled-midpoint-labels.nii.gz')
                fu_par_switch=os.path.join(fu_orig_suvr,
                                        'anat',
                                        subject_label+'_ses-followup_T1w_space-pet_desc_resampled-midpoint-labels.nii.gz')
                bl_pet_switch=os.path.join(orig_suvr,
                                        'pet',
                                        subject_label+'_ses-baseline_pet_space-orig_desc-suvr-long-'+
                                        switch_dash+'.nii.gz')
                fu_pet_switch=os.path.join(orig_suvr,
                                        'pet',
                                        subject_label+'_ses-followup_pet_space-orig_desc-suvr-long-'+
                                        switch_dash+'.nii.gz')
                cmd.append('--bl_pet')
                cmd.append(bl_pet_switch)
                cmd.append('--fu_pet')
                cmd.append(fu_pet_switch)
                cmd.append('--bl_par')
                cmd.append(bl_par_switch)
                cmd.append('--fu_par')
                cmd.append(fu_par_switch)
            cmd.append('--switch_ref')
        else:
            cmd.append('--bl_pet')
            cmd.append(bl_pet)
            cmd.append('--fu_pet')
            cmd.append(fu_pet)
            cmd.append('--mid_par')
            cmd.append(mid_par)
            cmd.append('--bl_t1_to_mid')
            cmd.append(bl_t1_to_mid)
            cmd.append('--fu_t1_to_mid')
            cmd.append(fu_t1_to_mid)
            cmd.append('--mid_to_bl_t1')
            cmd.append(mid_to_bl_t1)
            cmd.append('--mid_to_fu_t1')
            cmd.append(mid_to_fu_t1)
            cmd.append('--bl_t1_to_pet')
            cmd.append(bl_t1_to_pet)
            cmd.append('--fu_t1_to_pet')
            cmd.append(fu_t1_to_pet)
            cmd.append('--bl_brain_mask')
            cmd.append(bl_brain_mask)
            cmd.append('--fu_brain_mask')
            cmd.append(fu_brain_mask)
        if pvc:
            cmd.append('--pvc')
            cmd.append('--pvc_kernel')
            cmd.append('6.8')
            cmd.append('6.8')
            cmd.append('6.8')
            cmd.append('--pvc_iter')
            cmd.append('10')
        if erode:
            cmd.append('--erode_ref')
        print(cmd)
        subprocess.call(cmd)
        sys.stdout.flush()



parser = argparse.ArgumentParser(description='Compute SUVR')
parser.add_argument('--mode', type=str, required=True,
                    help='Validate input file or submit jobs',
                    choices=['validate','submit'])
parser.add_argument('--infile', type=str,
                    help='Input CSV to validate')
parser.add_argument('--subject',type=str,
                    help='Subject ID')
parser.add_argument('--bl_pet',type=str,
                    help='baseline PET')
parser.add_argument('--fu_pet',type=str,
                    help='followup  PET')
parser.add_argument('--bl_t1_to_mid',type=str,
                    help='def field to mid from bl T1')
parser.add_argument('--fu_t1_to_mid',type=str,
                    help='def field to mid from fu T1')
parser.add_argument('--mid_to_bl_t1',type=str,
                    help='def field to baseline T1 from mid')
parser.add_argument('--mid_to_fu_t1',type=str,
                    help='def field to followup T1 from mid')
parser.add_argument('--bl_t1_to_pet',type=str,
                    help='TX from baseline T1 to PET')
parser.add_argument('--fu_t1_to_pet',type=str,
                    help='TX from followup T1 to PET')
parser.add_argument('--mid_par',type=str,
                    help='midpoint GIF parcellation to use')
parser.add_argument('--bl_brain_mask',type=str,
                    help='baseline brain mask')
parser.add_argument('--fu_brain_mask',type=str,
                    help='followup brain mask')
parser.add_argument('--console_recon',action='store_true',
                    help='use console UTE recon')
parser.add_argument('--pct_recon',action='store_true',
                    help='use pCT recon')
parser.add_argument('--nipet_pct_recon',action='store_true',
                    help='use NiftyPET pCT recon')
parser.add_argument('--nipet_ute_recon',action='store_true',
                    help='use NiftyPET UTE recon')
parser.add_argument('--midpoint_type', type=str,
                    default='spm',
                    help='type of midpoint T1 reg, spm, ants or nireg')
parser.add_argument('--root_dir', type=str,
                    default='/SAN/medic/insight46/midpoint_test',
                    help='Root directory')
parser.add_argument('--scratch_dir', type=str,
                    default='/SAN/medic/insight46/midpoint_test',
                    help='Scratch directory')
parser.add_argument('--debug',action='store_true',
                    help='Turn on debugging for NiftyPET')
args=parser.parse_args()


if args.mode=='validate':
    if not args.infile:
        parser.error('Validate mode needs --infile option set')
    else:
        pd.read_csv(args.infile)


#removed or not ac_pet from this
elif args.mode=='submit':
    if not os.path.exists(args.bl_pet) or not os.path.exists(args.fu_pet) \
    or not os.path.exists(args.bl_t1_to_mid) or not os.path.exists(args.fu_t1_to_mid) \
    or not os.path.exists(args.mid_to_bl_t1) or not  os.path.exists(args.mid_to_fu_t1) \
    or not os.path.exists(args.bl_t1_to_pet) or not os.path.exists(args.fu_t1_to_pet) \
    or not os.path.exists(args.mid_par) or not os.path.exists(args.bl_brain_mask) or not os.path.exists(args.fu_brain_mask):
        parser.error('Submit needs all of the data: ' +
                     '--subject, --bl_pet, -fu_pet, --bl_t1_to_mid, \
                     --fu_t1_to_mid, --mid_to_bl_t1, --mid_to_fu_t1, --bl_t1_to_pet, --fu_t1_to_pet, \
                     --mid_par, --bl_brain_mask, --fu_brain_mask')
    
    if not args.scratch_dir:
        scratch_dir=os.path.join('/scratch0',
                                 os.genenv('USER'),
                                 os.genenv('JOB_ID')+'.'+os.genenv('SGE_TASK_ID'))
    else:
        scratch_dir=args.scratch_dir
    if args.root_dir:
        data_root=args.root_dir
    else:
        data_root='/SAN/medic/insight46/midpoint_test'

    subject_label='sub-' + args.subject

    #ONLY RUN ON NIPET_PCT FOR NOW
    #order of arguments:
    #bl_pet,fu_pet,mid_par,bl_t1_to_mid,fu_t1_to_mid,bl_t1_to_pet,
    #            fu_t1_to_pet,mid_to_bl_t1,mid_to_fu_t1,
    #            bl_brain_mask,fu_brain_mask,roi,midpoint_type,
    #            console=False,nipet_pct=False,nipet_ute=False,
    #            erode=False,switch_ref=None,graph=False,
    #            pvc=False
            
    if args.nipet_pct_recon:
         if os.path.exists(args.bl_pet) and os.path.exists(args.fu_pet):
             launch_suvr(scratch_dir,
                         args.bl_pet,
                         args.fu_pet,
                         args.mid_par,
                         args.bl_t1_to_mid,
                         args.fu_t1_to_mid,
                         args.bl_t1_to_pet,
                         args.fu_t1_to_pet,
                         args.mid_to_bl_t1,
                         args.mid_to_fu_t1,
                         args.bl_brain_mask,
                         args.fu_brain_mask,
                         'cereb','spm',
                         nipet_pct=True)
    
         else:
             print('No nipet_pct reconstruction available. Skipping')


