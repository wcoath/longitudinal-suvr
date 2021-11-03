import argparse
import numpy as np
#import matplotlib.pyplot as plt
import pandas as pd
np.set_printoptions(precision=4, suppress=True)
import numpy.linalg as npl
import nibabel as nib
import os
from glob import glob
import subprocess

parser = argparse.ArgumentParser(description='Voxel Mapping')
parser.add_argument('--subject',type=str,
                    help='Subject ID')
parser.add_argument('--mid_to_bl',type=str,
                    help='deformation field from mid T1 -> baseline PET')
parser.add_argument('--mid_to_fu',type=str,
                    help='deformation field from mid T1 -> followup PET')
parser.add_argument('--mid_par',type=str,
                    help='cleaned midpoint GIF parcelltion')
parser.add_argument('--bl_pet',type=str,
                    help='baseline PET')
parser.add_argument('--fu_pet',type=str,
                    help='followup PET')
parser.add_argument('--ref_roi',type=str,
                    help='reference region')
parser.add_argument('--ref_roi_mask',type=str,
                    help='reference region mask')
parser.add_argument('--alpha',type=float,
                    help='alpha value for LTS regression, needs to be between 0.5 and 1. Relates to proportion of voxels included')
parser.add_argument('--root_dir', type=str,
                    default='/SAN/medic/insight46',
                    help='Root directory')

args=parser.parse_args()

if not  args.mid_to_bl or not args.mid_to_fu or not args.mid_par \
   or not args.bl_pet or not args.fu_pet or not args.ref_roi:
    parser.error('argument missing')
else:
    if args.root_dir:
        data_root=args.root_dir
    else:
        data_root='/SAN/medic/insight46'

    if args.alpha>=0.5 and args.alpha<=1.0:
        alpha=str(args.alpha)
    else:
        print('no alpha set or value not between 0.5 and 1, setting default alpha = 0.75')
        alpha=str(0.75)
        
    subject_label='sub-' + args.subject
        
    bl_out_anat_dir=os.path.join(data_root,subject_label,'ses-baseline','anat')
    fu_out_anat_dir=os.path.join(data_root,subject_label,'ses-followup','anat')
    mid_out_anat_dir=os.path.join(data_root,subject_label,'ses-midpoint','anat')
    mid_out_pet_dir=os.path.join(data_root,subject_label,'ses-midpoint','pet')

    
    csv_out_path=os.path.join(mid_out_pet_dir,subject_label+'_ses-midpoint_long_'+args.ref_roi+'_pet_uptake.csv')
    #if glob(csv_out_path):
    #    print('outfile already exists, exit, skip to')
    #    exit(0)


    #load def fields
    mid_to_bl_img = nib.load(args.mid_to_bl)
    mid_to_bl_data = mid_to_bl_img.get_fdata()
    

    mid_to_fu_img = nib.load(args.mid_to_fu)
    mid_to_fu_data = mid_to_fu_img.get_fdata()
   

    mid_to_bl_data = np.squeeze(mid_to_bl_data)
    mid_to_fu_data = np.squeeze(mid_to_fu_data)
    
    
    mid_par_img = nib.load(args.mid_par)
    mid_par_data = mid_par_img.get_fdata()

    #whole cereb indicies
    if args.ref_roi=='cereb':
        ref_roi=args.ref_roi
        ref_roi_ind = [39,40,41,42,72,73,74]
        ref_roi_mask = ((mid_par_data == 39) |
                        (mid_par_data == 40) |
                        (mid_par_data == 41) |
                        (mid_par_data == 42) |
                        (mid_par_data == 72) |
                        (mid_par_data == 73) |
                        (mid_par_data == 74))
        ref_roi_mask_int = np.array(ref_roi_mask,dtype = int)
    elif args.ref_roi=='gm-cereb-clean':
        if args.ref_roi_mask:
            ref_roi=args.ref_roi
            ref_roi_mask_img = nib.load(args.ref_roi_mask)
            ref_roi_mask_data = ref_roi_mask_img.get_fdata()
            ref_roi_mask_int = np.array(ref_roi_mask_data,dtype = int)
        else:
            print('cerebellar gm mask needed')
            exit(1)
    else:
        print('only cereb or gm cereb supported')
        exit(1)

    
    print('creating midpoint t1 int mask')
    n=1
    with np.nditer(ref_roi_mask_int, op_flags=['readwrite']) as it:
        for vox in it:
            if vox==1:
                vox[...] = int(n)
                n+=1

    print('mask created')
    bl_pet_img = nib.load(args.bl_pet)
    bl_pet_data = bl_pet_img.get_fdata()

    fu_pet_img = nib.load(args.fu_pet)
    fu_pet_data = fu_pet_img.get_fdata()
    
    def get_mm_def(def_data,i,j,k):
        x_mm = def_data[i,j,k,0]
        y_mm = def_data[i,j,k,1]
        z_mm = def_data[i,j,k,2]
        return [x_mm,y_mm,z_mm]

    def vox2mm(img,i,j,k):
        M = img.affine[:3, :3]
        abc = img.affine[:3, 3]
        return M.dot([i,j,k]) + abc

    def mm2vox(img,x,y,z):
        M = npl.inv(img.affine)[:3, :3]
        abc = npl.inv(img.affine)[:3, 3]
        vox_array = M.dot([x,y,z]) + abc
        return np.round(vox_array)

    bl_mask = np.zeros(shape=bl_pet_data.shape, dtype = int)
    fu_mask = np.zeros(shape=fu_pet_data.shape, dtype = int)

    nvox = np.count_nonzero(ref_roi_mask_int)
    print('number of voxels in region: ' + str(nvox))
    
    
    roi_dict = {}
    bl_dict = {}
    fu_dict = {}
    vox_values = np.zeros((nvox, 3))
    


    n=0
    while n < nvox:
        #print(n)
        coord = np.nonzero(ref_roi_mask_int == int(n+1))
        i,j,k = coord
        x_mm,y_mm,z_mm = get_mm_def(mid_to_bl_data, int(i), int(j), int(k))
        bl_i,bl_j,bl_k = mm2vox(bl_pet_img,x_mm,y_mm,z_mm)
        x_mm,y_mm,z_mm = get_mm_def(mid_to_fu_data, int(i), int(j), int(k))
        fu_i,fu_j,fu_k = mm2vox(fu_pet_img,x_mm,y_mm,z_mm)

        vox_tup = ([int(bl_i),int(bl_j),int(bl_k)],[int(fu_i),int(fu_j),int(fu_k)])
        if vox_tup not in roi_dict.values():
            bl_tup = ([int(bl_i),int(bl_j),int(bl_k)])
            fu_tup = ([int(fu_i),int(fu_j),int(fu_k)])
            if bl_tup not in bl_dict.values() and fu_tup not in fu_dict.values():
                roi_dict.update({str(n) : vox_tup})
                bl_dict.update({str(n) : bl_tup})
                fu_dict.update({str(n) : fu_tup})
                bl_mask[int(bl_i),int(bl_j),int(bl_k)] = n
                fu_mask[int(fu_i),int(fu_j),int(fu_k)] = n
                #extract PET values at these voxels
                bl_value = bl_pet_data[int(bl_i),int(bl_j),int(bl_k)]
                fu_value = fu_pet_data[int(fu_i),int(fu_j),int(fu_k)]
                print('vox: '+str(int(n+1))+', bl: '+str(bl_value)+', fu: '+str(fu_value))
                vox_values[n, 0] = int(n+1)
                vox_values[n, 1] = bl_value
                vox_values[n, 2] = fu_value
                

        n+=1

    
    bl_mask_img = nib.Nifti1Image(bl_mask.astype(int), affine=bl_pet_img.affine, header=bl_pet_img.header)
    fu_mask_img = nib.Nifti1Image(fu_mask.astype(int), affine=fu_pet_img.affine, header=fu_pet_img.header)
    nib.save(bl_mask_img, os.path.join(bl_out_anat_dir,subject_label+'_ses-baseline_PET_'+ref_roi+'_mask.nii.gz'))
    nib.save(fu_mask_img, os.path.join(fu_out_anat_dir,subject_label+'_ses-followup_PET_'+ref_roi+'_mask.nii.gz'))
    mid_mask_img = nib.Nifti1Image(ref_roi_mask_int.astype(int), affine=mid_par_img.affine, header=mid_par_img.header)
    nib.save(mid_mask_img, os.path.join(mid_out_anat_dir,subject_label+'_ses-midpoint_T1w_'+ref_roi+'_mask.nii.gz'))
    #set header row
    
    df = pd.DataFrame(vox_values,columns=['voxel_number','baseline_uptake','followup_uptake'])
    df.to_csv(csv_out_path,index=False)
    
    #run LTS R script, requires tidyverse,ggthemes,robustbase packages
    rscript='/SAN/medic/insight46/scripts/long_suvr_compute_LTS.R'
    r_cmd=['Rscript',rscript,csv_out_path,ref_roi,alpha]
    print(r_cmd)
    subprocess.call(r_cmd)
    
    print('get descriptives from non-zero')
    nonzero_file=csv_out_path.replace('.csv','_nonzero.csv')
    df = pd.read_csv(nonzero_file)
    ##mean,sd and median,range for baseline and followup
    ##don't include voxel_number column
    cols=set(df.columns) - {"voxel_number"}
    df1=df[list(cols)]
    descriptives=df1.describe()
    print(descriptives)
    print('saving to file')
    descriptives_file=csv_out_path.replace('.csv','_descriptive_stats.csv')
    descriptives.to_csv(descriptives_file,index_label='statistic')
    
    outlier_file=csv_out_path.replace('.csv','_outlier_vox_list.csv')
    outlier_df = pd.read_csv(outlier_file)
    outlier_arr = outlier_df["voxel_number"].to_numpy()

    print('creating baseline and followup PET outlier masks')
    bl_outlier=bl_mask
    with np.nditer(bl_outlier, op_flags=['readwrite']) as it:
        for vox in it:
            if vox in outlier_arr:
                print('outlier vox: '+str(vox))
                vox[...] = int(1)
            else:
                vox[...] = int(0)

    fu_outlier=fu_mask
    with np.nditer(fu_outlier, op_flags=['readwrite']) as it:
        for vox in it:
            if vox in outlier_arr:
                print('outlier vox: '+str(vox))
                vox[...] = int(1)
            else:
                vox[...] = int(0)

    bl_outlier_img = nib.Nifti1Image(bl_outlier.astype(bool), affine=bl_pet_img.affine, header=bl_pet_img.header)
    fu_outlier_img = nib.Nifti1Image(fu_outlier.astype(bool), affine=fu_pet_img.affine, header=fu_pet_img.header)
    nib.save(bl_outlier_img, os.path.join(bl_out_anat_dir,subject_label+'_ses-baseline_PET_'+ref_roi+'_outlier_mask_alpha-'+alpha+'_.nii.gz'))
    nib.save(fu_outlier_img, os.path.join(fu_out_anat_dir,subject_label+'_ses-followup_PET_'+ref_roi+'_outlier_mask_alpha-'+alpha+'_.nii.gz'))

    
            
                

    
                
    

    

    

