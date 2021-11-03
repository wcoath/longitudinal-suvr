#!/bin/sh

# Python
PATH=/share/apps/cmic/NiftyPipe/anaconda2/bin:${PATH}

# MATLAB
MATLAB_DIR=/share/apps/matlabR2016b
PATH=${MATLAB_DIR}/bin:${PATH}
MATLABPATH=/share/apps/cmic/noddi/niftimatlib-1.2/matlab:${MATLAB_DIR}/toolbox/matlab/optimfun:${MATLAB_DIR}/toolbox/shared/optimlib:$MATLABPATH


# NiftyReg
PATH=/share/apps/cmic/niftyreg_v1.5.43/bin:${PATH}

#ANTs
ANTSPATH=${ANTSPATH:="/share/apps/ants-2.2.0/bin"}



export PATH
export PYTHONPATH
export MATLABPATH
export ANTSPATH
