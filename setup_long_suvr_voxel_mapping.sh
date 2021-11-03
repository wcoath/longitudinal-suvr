#!/bin/sh

# Python
ANACONDA=/share/apps/anaconda
ENVS=/SAN/medic/insight46/envs

source ${ANACONDA}/bin/activate ${ENVS}/long_suvr_voxel_mapping_2021_10_25

# NiftyReg
PATH=/share/apps/cmic/niftyreg_v1.5.43/bin:${PATH}

# NiftySeg
PATH=/share/apps/cmic/niftyseg_ef3f62d/bin:${PATH}

# FSL
FSLDIR=/share/apps/fsl-5.0.10
PATH=${FSLDIR}/bin:${PATH}
export FSLDIR PATH
. ${FSLDIR}/etc/fslconf/fsl.sh
FSLOUTPUTTYPE=NIFTI_GZ

#R
#export PATH=/share/apps/R-3.5.2/bin:${PATH}
export PATH=/share/apps/R-3.6.1/bin:${PATH}
export FSLDIR

export PATH
export PYTHONPATH
export LD_LIBRARY_PATH
