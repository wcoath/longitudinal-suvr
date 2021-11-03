#!/usr/bin/env bash
#$ -S /bin/bash
#$ -l h_rt=24:00:00
#$ -l tmem=11G
#$ -l h_vmem=11G
#$ -j y
#$ -b y
#$ -cwd
#$ -V
#$ -R y
#$ -o /SAN/medic/insight46/logs
#$ -l tscratch=1G

##HOW SCRIPT WILL CLEAN UP SCRATCH WHEN QSUB
## I put SCRATCHDIR as a variable in this function, hard coded before, might not work
SCRATCH_DIR=/scratch0/${USER}/${JOB_ID}.${SGE_TASK_ID}
#SCRATCH_DIR=/SAN/medic/insight46/midpoint_test/tmp/${USER}/${JOB_ID}.${SGE_TASK_ID}

## DONT CLEAN UP WHILST TESTING
function finish {
    date
    rm -rf ${SCRATCH_DIR}
}

trap finish EXIT ERR

mkdir -p ${SCRATCH_DIR}


ROOT_DIR=/SAN/medic/insight46


#SETUP
#NIFTYPIPE_DIR=/share/apps/cmic/NiftyPipe
source /SAN/medic/insight46/scripts/setup_midpoint.sh
SCRIPTFILE=/SAN/medic/insight46/scripts/run_midpoint.py
SPM_DIR='/home/wcoath/spm12_r6470/'
INFILE=(`cat ${1}`)

#ONLY RELEVANT WHEN QSUB
echo ${HOSTNAME}
if [ "${SGE_TASK_ID}" -ge "${#INFILE[*]}" ] 
    then
    echo "This job is out of bounds of the worklist provided"
    exit 1
fi
PROC=${INFILE[${SGE_TASK_ID}]}
echo ${PROC}

#JOB_NO=$2
#PROC=${INFILE[${JOB_NO}]}

#Call Python code
echo "Setting up script"
SUBJECT=`echo ${PROC} | cut -d, -f1`
BL_SESSION=`echo ${PROC} | cut -d, -f2`
FU_SESSION=`echo ${PROC} | cut -d, -f3`
BL_T1=`echo ${PROC} | cut -d, -f4`
FU_T1=`echo ${PROC} | cut -d, -f5`

echo "python ${SCRIPTFILE} --subject ${SUBJECT} --bl_session ${BL_SESSION} --fu_session ${FU_SESSION} --bl_t1 ${BL_T1} --fu_t1 ${FU_T1} --root_dir ${ROOT_DIR} --scratch_dir ${SCRATCH_DIR} --spm_dir ${SPM_DIR}"
python ${SCRIPTFILE} --subject ${SUBJECT} --bl_session ${BL_SESSION} --fu_session ${FU_SESSION} --bl_t1 ${BL_T1} --fu_t1 ${FU_T1} --root_dir ${ROOT_DIR} --scratch_dir ${SCRATCH_DIR} --spm_dir ${SPM_DIR}
