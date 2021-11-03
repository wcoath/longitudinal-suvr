#!/usr/bin/env bash
#$ -S /bin/bash
#$ -l h_rt=48:00:00
#$ -l tmem=10G
#$ -l h_vmem=10G
#$ -j y
#$ -b y
#$ -cwd
#$ -V
#$ -R y
#$ -o /SAN/medic/insight46/logs
#$ -l tscratch=5G

function finish {
    date
    rm -rf /scratch0/${USER}/${JOB_ID}.${SGE_TASK_ID}
    #If scratch0 acting up on server, replace above line with line below
    #rm -rf /SAN/medic/insight46/scratch/${JOB_ID}.${SGE_TASK_ID}
}

trap finish EXIT ERR

source /SAN/medic/insight46/scripts/setup_long_suvr_voxel_mapping.sh

SCRIPTFILE=/SAN/medic/insight46/scripts/run_long_suvr_voxel_mapping.py

INFILE=(`cat ${1}`)
echo ${HOSTNAME}
if [ "${SGE_TASK_ID}" -ge "${#INFILE[*]}" ] 
    then
    echo "This job is out of bounds of the worklist provided"
    exit 1
fi
PROC=${INFILE[${SGE_TASK_ID}]}
echo ${PROC}

#Call Python code
echo "Setting up script"
SUBJECT=`echo ${PROC} | cut -d, -f1`
RECON=`echo ${PROC} | cut -d, -f2`
BL_AFF=`echo ${PROC} | cut -d, -f3`
FU_AFF=`echo ${PROC} | cut -d, -f4`
BL_DEF=`echo ${PROC} | cut -d, -f5`
FU_DEF=`echo ${PROC} | cut -d, -f6`
MID_PAR=`echo ${PROC} | cut -d, -f7`
BL_PET=`echo ${PROC} | cut -d, -f8`
FU_PET=`echo ${PROC} | cut -d, -f9`


OUT_DIR=/SAN/medic/insight46/analysis/longitudinal_pet_voxel_mapping_${RECON}
SCRATCH_DIR=/scratch0/${USER}/${JOB_ID}.${SGE_TASK_ID}
#SCRATCH_DIR=/SAN/medic/insight46/voxel_mapping_test/scratch/${USER}/${JOB_ID}.${SGE_TASK_ID}
mkdir -p ${SCRATCH_DIR}


mkdir -p ${OUT_DIR}/sub-${SUBJECT}/ses-baseline/anat
mkdir -p ${OUT_DIR}/sub-${SUBJECT}/ses-followup/anat
mkdir -p ${OUT_DIR}/sub-${SUBJECT}/ses-midpoint/anat

mkdir -p ${OUT_DIR}/sub-${SUBJECT}/ses-baseline/xfm
mkdir -p ${OUT_DIR}/sub-${SUBJECT}/ses-followup/xfm

mkdir -p ${OUT_DIR}/sub-${SUBJECT}/ses-midpoint/pet

#source /SAN/medic/insight46/scripts/setup_suvr_ref_mask.sh

BL_INV_AFF=${OUT_DIR}/sub-${SUBJECT}/ses-baseline/xfm/sub-${SUBJECT}_ses-baseline_PET-to-T1.txt
MID_TO_BL=${OUT_DIR}/sub-${SUBJECT}/ses-baseline/xfm/sub-${SUBJECT}_ses-baseline_MID-to-PET_mapping_def.nii.gz

reg_transform -invAff $BL_AFF $BL_INV_AFF
reg_transform -comp $BL_DEF $BL_INV_AFF $MID_TO_BL

FU_INV_AFF=${OUT_DIR}/sub-${SUBJECT}/ses-followup/xfm/sub-${SUBJECT}_ses-followup_PET-to-T1.txt
MID_TO_FU=${OUT_DIR}/sub-${SUBJECT}/ses-followup/xfm/sub-${SUBJECT}_ses-followup_MID-to-PET_mapping_def.nii.gz

reg_transform -invAff $FU_AFF $FU_INV_AFF
reg_transform -comp $FU_DEF $FU_INV_AFF $MID_TO_FU

echo 'creating gm cereb mask in T1 space'

T1_REF_MASK=${OUT_DIR}/sub-${SUBJECT}/ses-midpoint/anat/sub-${SUBJECT}_ses-midpoint_T1w_run-1_desc-gm-cereb-clean.nii.gz

if [ ! -f $T1_REF_MASK ]; then
    T1_SEG=/SAN/medic/insight46/analysis/gif/sub-${SUBJECT}/ses-midpoint/anat/sub-${SUBJECT}_ses-midpoint_T1w_run-1_desc-gradwarp_spm-midpoint_seg.nii.gz
    workingmask=${SCRATCH_DIR}/sub-${SUBJECT}_ses-midpoint_T1w_run-1_desc-refmask.nii.gz
    workingmask1=${SCRATCH_DIR}/sub-${SUBJECT}_ses-midpoint_T1w_run-1_desc-refmask1.nii.gz
    #remake gm cereb clean mask as it wasn't saved before resampling to PET
    #code used from scripts/submit_suvr_gm_cereb_refmask.sh
    fslmaths ${MID_PAR} -thr 38.5 -uthr 40.5 -bin ${workingmask}
    fslmaths ${MID_PAR} -thr 71.5 -uthr 74.5 -bin -add ${workingmask} -bin ${workingmask1}
    #Clean it up a bit with the GM tissue - the labels themselves have
    #already been cleaned with the DRC brainmask
    seg_maths ${T1_SEG} -tp 2 -thr 0.9 -mul ${workingmask1} -bin -odt int ${T1_REF_MASK}
    
    rm -fv ${workingmask}
    rm -fv ${workingmask1}
else 
    echo 'gm-cereb-clean mask already exists'
fi

#source deactivate
#source activate /SAN/medic/insight46/envs/long_suvr_voxel_mapping_2021_10_25

for REF_ROI in cereb gm-cereb-clean ; do
    
    echo "python ${SCRIPTFILE} --subject ${SUBJECT} --mid_to_bl ${MID_TO_BL} --mid_to_fu ${MID_TO_FU} --mid_par ${MID_PAR} --bl_pet ${BL_PET} --fu_pet ${FU_PET} --ref_roi ${REF_ROI} --ref_roi_mask ${T1_REF_MASK} --root_dir ${OUT_DIR} --alpha 0.75"
    python ${SCRIPTFILE} --subject ${SUBJECT} --mid_to_bl ${MID_TO_BL} --mid_to_fu ${MID_TO_FU} --mid_par ${MID_PAR} --bl_pet ${BL_PET} --fu_pet ${FU_PET} --ref_roi ${REF_ROI} --ref_roi_mask ${T1_REF_MASK} --root_dir ${OUT_DIR} --alpha 0.75

done
