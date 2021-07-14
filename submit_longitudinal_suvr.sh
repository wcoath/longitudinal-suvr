#!/usr/bin/env bash
#$ -S /bin/bash
#$ -l h_rt=02:00:00
#$ -l tmem=7.9G
#$ -l h_vmem=7.9G
#$ -j y
#$ -b y
#$ -cwd
#$ -o /SAN/medic/insight46/midpoint_test/logs
#$ -l tscratch=3G
function finish {
    date
    rm -rf /scratch0/${USER}/${JOB_ID}.${SGE_TASK_ID}
    #If scratch0 acting up on server, replace above line with line below
    #rm -rf /SAN/medic/insight46/scratch/${JOB_ID}.${SGE_TASK_ID}
}

trap finish EXIT ERR

# Now longer needed with new cluster -l scratch0free=3G

echo ${HOSTNAME}
date

#try without having to source this
#source ${ROOT_DIR}/scripts/setup_suvr_ref_mask.sh

source /SAN/medic/insight46/scripts/setup_suvr_newcluster.sh

SCRIPTFILE=/SAN/medic/insight46/scripts/run_longitudinal_suvr.py
SCRATCHDIR=/scratch0/${USER}/${JOB_ID}.${SGE_TASK_ID}
#If scratch0 acting up on server, replace above line with line below
SCRATCHDIR=/SAN/medic/insight46/midpoint_test/scratch/${USER}/${JOB_ID}.${SGE_TASK_ID}
mkdir -p ${SCRATCHDIR}
INFILE=(`cat ${1}`)
if [ "${SGE_TASK_ID}" -ge "${#INFILE[*]}" ]
    then
    echo "This job is out of bounds of the worklist provided"
    exit 1
fi
DEUBG=""
if [ ! -z ${2} ]
then
    DEBUG="--debug"
fi
PROC=${INFILE[${SGE_TASK_ID}]}
echo ${PROC}
echo "Setting up script"
#subject_label,bl_pet_recon,fu_pet_recon,gif_midpoint,bl_t1_to_pet_tx,fu_t1_to_pet_tx,bl_t1_to_mid_def,fu_t1_to_mid_def,bl_brain_mask,fu_brain_mask
SUBJECT=`echo ${PROC} | cut -d, -f1`
BL_PET=`echo ${PROC} | cut -d, -f2`
FU_PET=`echo ${PROC} | cut -d, -f3`
MID_PAR=`echo ${PROC} | cut -d, -f4`
BL_T1_TO_PET=`echo ${PROC} | cut -d, -f5`
FU_T1_TO_PET=`echo ${PROC} | cut -d, -f6`
BL_T1_TO_MID=`echo ${PROC} | cut -d, -f7`
FU_T1_TO_MID=`echo ${PROC} | cut -d, -f8`
BL_BRAIN_MASK=`echo ${PROC} | cut -d, -f9`
FU_BRAIN_MASK=`echo ${PROC} | cut -d, -f10`


MIDPOINT_TYPE='spm'

#first invert deformations for bl and fu
MID_TO_BL_T1=${SCRATCHDIR}/${SUBJECT}_midpoint-${MIDPOINT_TYPE}_to_baseline-T1_def.nii.gz
reg_transform -invNrr $BL_T1_TO_MID $MID_PAR $MID_TO_BL_T1

MID_TO_FU_T1=${SCRATCHDIR}/${SUBJECT}_midpoint-${MIDPOINT_TYPE}_to_followup-T1_def.nii.gz
reg_transform -invNrr $FU_T1_TO_MID $MID_PAR $MID_TO_FU_T1

echo python ${SCRIPTFILE} --mode submit --subject ${SUBJECT} \
    --bl_pet ${BL_PET} --fu_pet ${FU_PET} --mid_par ${MID_PAR} \
    --bl_t1_to_pet ${BL_T1_TO_PET} --fu_t1_to_pet ${FU_T1_TO_PET} \
    --bl_t1_to_mid ${BL_T1_TO_MID} --fu_t1_to_mid ${FU_T1_TO_MID} \
    --mid_to_bl_t1 ${MID_TO_BL_T1} --mid_to_fu_t1 ${MID_TO_FU_T1} \
    --bl_brain_mask ${BL_BRAIN_MASK} --fu_brain_mask ${FU_BRAIN_MASK} \
    --nipet_pct_recon --midpoint_type ${MIDPOINT_TYPE} \
    --scratch_dir ${SCRATCHDIR} ${DEBUG} 

python ${SCRIPTFILE} --mode submit --subject ${SUBJECT} \
    --bl_pet ${BL_PET} --fu_pet ${FU_PET} --mid_par ${MID_PAR} \
    --bl_t1_to_pet ${BL_T1_TO_PET} --fu_t1_to_pet ${FU_T1_TO_PET} \
    --bl_t1_to_mid ${BL_T1_TO_MID} --fu_t1_to_mid ${FU_T1_TO_MID} \
    --mid_to_bl_t1 ${MID_TO_BL_T1} --mid_to_fu_t1 ${MID_TO_FU_T1} \
    --bl_brain_mask ${BL_BRAIN_MASK} --fu_brain_mask ${FU_BRAIN_MASK} \
    --nipet_pct_recon --midpoint_type ${MIDPOINT_TYPE} \
    --scratch_dir ${SCRATCHDIR} ${DEBUG} 

