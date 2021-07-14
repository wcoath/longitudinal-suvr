#!/SAN/medic/insight46/envs/suvr_2019_01_11/bin/python
'''
NIPYPE LONGITUDINAL SUVR PIPELINE 

Author: Will Coath
Date: Nov 2020

Calculate longitudinal SUVR (2 timepoints) from midpoint GIF parcellation
PVC (with PETPVC nipype) by resampling PET to midpoint

PREREQUISITES:
1. midpoint  GIF parcellation to clean
2. baseline static PET recon (will use nifyPET pCT for now)
3. followup static PET recon
4. 6 DOF TX from baseline T1 -> baseline PET (specific to each recon, to be converted to def field)
5. 6 DOF TX from followup T1 -> followup PET (specific to each recon, to be converted to def field)
6. deformation field from baseline T1 -> midpoint T1
7. deformation field from followup T1 -> midpoint T1
8. deformation field from  midpoint T1 -> baseline T1 (has been inverted using reg_transform invNrr, then composed with rigid)
9. deformation field from  midpoint T1 -> followup T1 (has been inverted using reg_transform invNrr, then composed with rigid)
10. baseline drc brain mask for cleaning parcellation, could do this a) at midpoint with followup mask too b) after resampling to baseline or c) both
11. followup drc brain mask for cleaning parcellation, could do this a) at midpoint with baseline  mask too b) after resampling to baseline or c) both
12. midpoint T1 bias_corrected from gif

WORKFLOW:
STEP 1. resample each drc_brain mask to midpoint using spm deformation fields (reg_resample)
STEP 2. clean midpoint GIF parcellation with both masks (fslmaths)
STEP 3. convert each 6DOF TX to deformation fields (reg_transform) 
STEP 4. compose 6DOF deformation and inverted spm deformation to get def from midpoint to each PET (reg_transform)
STEP 5. resample midpoint par to each PET (reg_resample)
STEP 6 (OPTIONAL). resample midpoint GIF GM segmentation to each TP and only include cortical regions if >0.9 -NOT IMPLEMENTED YET
STEP 7. create ref region (and save ref ROIs), threshold based on labels? Erode WM (fslmaths) - ref region depend on argument input? 
STEP 8. divide PET by ref region mean (or median so not skewed by outliers?)

OPT ARGS:
1. reference region (whole cerebellum, cerebellar gm, eroded white matter, pons, composite reference?)
2. PVC
3. recon (if using reconstruction specific MRI->PET TX from cross-sectional pipeline)
4. --switch_ref if regions already exist
5. --graph for wf graph
'''

### PIPELINE CODE ###
#IMPORT MODULES

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import os
import nipype.interfaces.utility as niu
import nipype.interfaces.io as nio
import nipype.pipeline.engine as pe
import nipype.interfaces.niftyreg as niftyreg
import nipype.interfaces.fsl as fsl
from niftypipe.workflows.misc import (create_regional_normalisation_pipeline,
                    create_regional_average_pipeline)
import nipype.interfaces.petpvc as petpvc
from niftypipe.interfaces.base import (generate_graph, run_workflow,
                                       default_parser_argument, get_qsub_args)
"""
create the help message
"""

__description__ = '''
Compute longitudinal SUVR.
The SUVR of baseline and follow-up PET images (--bl_pet, --fu_pet) are computed using a midpoint GIF parcelation (--mid_par)
and its associated structural image (--mid_t1). The parcellation is first cleaned using masks from both timepoints (--bl_brain_mask, --fu_brain_mask).
The midpoint parcelation is resampled to PET space at each timepoint using a deformation field combining the midpoint->timepoint-T1 warp and T1->PET TX
from each cross-sectional timepoint.

'''

parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                        description=__description__)

"""
Input images
"""
parser.add_argument('--bl_pet',
                    dest='input_bl_pet',
                    metavar='image',
                    nargs='+',
                    help='baseline PET image',
                    required=True)
parser.add_argument('--fu_pet',
                    dest='input_fu_pet',
                    metavar='image',
                    nargs='+',
                    help='follow-up PET image',
                    required=True)

_help = 'Midpoint parcelation (NeuroMorphometrics from GIF) image'
parser.add_argument('--mid_par',
                    dest='input_mid_par',
                    metavar='image',
                    nargs='+',
                    help=_help
                   )
parser.add_argument('--bl_t1_to_pet',
                    dest='input_bl_t1_to_pet',
                    metavar='image',
                    nargs='+',
                    help='baseline T1 to PET transform'
                   )
parser.add_argument('--fu_t1_to_pet',
                    dest='input_fu_t1_to_pet',
                    metavar='image',
                    nargs='+',
                    help='follow-up T1 to PET transform'
                   )
parser.add_argument('--bl_t1_to_mid',
                    dest='input_bl_t1_to_mid',
                    metavar='image',
                    nargs='+',
                    help='baseline T1 to mid deformation field'
                   )
parser.add_argument('--fu_t1_to_mid',
                    dest='input_fu_t1_to_mid',
                    metavar='image',
                    nargs='+',
                    help='follow-up T1 to mid deformation field'
                   )
parser.add_argument('--mid_to_bl_t1',
                    dest='input_mid_to_bl_t1',
                    metavar='image',
                    nargs='+',
                    help='midpoint to baseline T1 deformation field'
                   )
parser.add_argument('--mid_to_fu_t1',
                    dest='input_mid_to_fu_t1',
                    metavar='image',
                    nargs='+',
                    help='midpoint to followup T1 deformation field'
                   )
parser.add_argument('--bl_brain_mask',
                    dest='input_bl_brain_mask',
                    metavar='image',
                    nargs='+',
                    help='baseline brain mask'
                   )
parser.add_argument('--fu_brain_mask',
                    dest='input_fu_brain_mask',
                    metavar='image',
                    nargs='+',
                    help='follow-up brain mask'
                   )
parser.add_argument('--bl_par',
                    dest='input_bl_par',
                    metavar='image',
                    nargs='+',
                    help='baseline parcellation, needed if --switch_ref'
                   )
parser.add_argument('--fu_par',
                    dest='input_fu_par',
                    metavar='image',
                    nargs='+',
                    help='follow-up parcellation, needed if --switch_ref'
                   )

"""
Output argument
"""
_help = 'Result directory where the output data is to be stored'
parser.add_argument('-o', '--output',
                    dest='output_dir',
                    metavar='output',
                    help=_help,
                    required=False,
                    default='results')
_help = 'working directory for output for now'
parser.add_argument('-w','--working',
                    dest='working_dir',
                    metavar='working',
                    help=_help,
                    required=False,
                    default='results')


"""
PETPVC argument
For time being: assume upsample, provide X, Y, Z, and iterations
"""
_help = 'Run the partial volume correction. Rather than downsampling MRI to \
PET to compute the SUVR, this will upsample PET to MR space. For now, this \
only uses Iterative Yang method.'
parser.add_argument('--pvc',
                    action='store_true',
                    help=_help)
_help = 'Set the X Y and Z FWHM kernel for partial volume correction'
parser.add_argument('--pvc_kernel',
                    dest='pvc_kernel',
                    metavar=['X', 'Y', 'Z'],
                    default=[6.8, 6.8, 6.8],
                    nargs=3,
                    type=float,
                    help=_help)
parser.add_argument('--pvc_iter',
                    dest='pvc_iter',
                    type=int,
                    default=10,
                    help='Number of iterations to run the PVC correction for')

"""
Others argument
"""
_help = '''ROI to use to perform the function image intensities normalisation.
Choices are: %s without quotes.
The default value is %s'''
roi_choices = ['cereb', 'gm_cereb', 'pons', 'wm_subcort','wm_subcort_gif3']
parser.add_argument('--roi',
                    metavar='roi',
                    nargs=1,
                    choices=roi_choices,
                    default=roi_choices[0],
                    help=_help % (str(roi_choices), str(roi_choices[0])))

_help = 'Perform one erosion on reference region before doing SUVR calculation'
parser.add_argument('--erode_ref', action='store_true', help=_help)

_help = 'Run the SUVR in switch mode, simply using a new reference region. \
This will only do the normalisation and average and assumes you have run the \
SUVR previously and the outputs from the pipeline are the inputs to this one.'
parser.add_argument('--switch_ref',
                    action='store_true',
                    help=_help)

'''
_help = 'Output workflow graph'
parser.add_argument('--graph',
                    action='store_true',
                    help=_help)
'''

"""
Add default arguments in the parser
"""
default_parser_argument(parser)

"""
Parse the input arguments
"""
args = parser.parse_args()

if not args.input_mid_par or not args.input_bl_t1_to_pet or not args.input_fu_t1_to_pet \
or not args.input_bl_t1_to_mid or not args.input_fu_t1_to_mid \
or not args.input_mid_to_bl_t1 or not args.input_mid_to_fu_t1 \
or not args.input_bl_brain_mask or not args.input_fu_brain_mask \
and not args.switch_ref:
    print('You must specify an parcelation,mid_t1,transforms and masks if you are not using option --switch_ref')
    sys.exit(1)

#need pet for both options
bl_pet = os.path.abspath(str(args.input_bl_pet[0]))
fu_pet = os.path.abspath(str(args.input_fu_pet[0]))

if not args.switch_ref:
    mid_par = os.path.abspath(str(args.input_mid_par[0]))
    bl_t1_to_pet = os.path.abspath(str(args.input_bl_t1_to_pet[0]))
    fu_t1_to_pet = os.path.abspath(str(args.input_fu_t1_to_pet[0]))
    bl_t1_to_mid = os.path.abspath(str(args.input_bl_t1_to_mid[0]))
    fu_t1_to_mid = os.path.abspath(str(args.input_fu_t1_to_mid[0]))
    mid_to_bl_t1 = os.path.abspath(str(args.input_mid_to_bl_t1[0]))
    mid_to_fu_t1 = os.path.abspath(str(args.input_mid_to_fu_t1[0]))
    bl_brain_mask = os.path.abspath(str(args.input_bl_brain_mask[0]))
    fu_brain_mask = os.path.abspath(str(args.input_fu_brain_mask[0]))

else:
    if not os.path.abspath(str(args.input_bl_par[0])) or not os.path.abspath(str(args.input_fu_par[0])):
        print("Need baseline and follow-up parcellation  as inputs if --switch_ref")
    else:
        bl_par = os.path.abspath(str(args.input_bl_par[0]))
        fu_par = os.path.abspath(str(args.input_fu_par[0]))
        sys.exit(1)
"""
Create the output folder if it does not exists
"""
#changed result from output to working
#result_dir = os.path.abspath(str(args.working_dir[0]))
result_dir=os.path.abspath(args.working_dir)
print('result directory: '+result_dir)
if not os.path.exists(result_dir):
    os.mkdir(result_dir)

erode_ref=args.erode_ref
norm_region=args.roi[0]
'''
I am combining and modifying elements of 'perform_compute_suvr.py'
and underlying functions from 'petmr_suvr.py'
'''


if args.switch_ref:
    print('switch ref... not ready')
    ##not ready yet
    ## Create the workflow
    #wf = pe.Workflow(name='compute_suvr')
    #wf.base_output_dir = result_dir
    #
    ## Create all the required nodes
    #inputnode = pe.Node(interface=niu.IdentityInterface(fields=['in_pets',
    #                                                            'in_pars']),
    #                    name='inputspec')
    
    ## Create an output node
    #outputnode = pe.Node(interface=niu.IdentityInterface(fields=['norm_files',
    #                                                             'suvr_files']),
    #                     name='outputspec')
    #
    #normalisation = create_regional_normalisation_pipeline(erode_ref=erode_ref)
    #if norm_region == 'pons':
    #    roi_indices = [35]
    #elif norm_region == 'gm_cereb':
    #    roi_indices = [39, 40, 72, 73, 74]
    #elif norm_region == 'wm_subcort':
    #    roi_indices = [45, 46]
    #elif norm_region == 'wm_subcort_gif3':
    #    roi_indices = [81, 82, 83, 84, 85, 86, 87, 89, 90, 91, 92, 93, 94]
    #else:  # full cerebellum
    #    roi_indices = [39, 40, 41, 42, 72, 73, 74]
    #normalisation.inputs.inputspec.label_indices = roi_indices
    #wf.connect([
    #    (inputnode, normalisation, [('in_pets', 'inputspec.in_files')]),
    #    (inputnode, normalisation, [('in_pars', 'inputspec.in_rois')])
    #])
    ## The regional uptake are computed
    #regional_avg = create_regional_average_pipeline(neuromorphometrics=True)
    #wf.connect([
    #    (normalisation, regional_avg, [('outputspec.out_files',
    #                                    'inputspec.in_files')]),
    #    (inputnode, regional_avg, [('in_pars', 'inputspec.in_rois')]),
    #    # Output node
    #    (normalisation, outputnode, [('outputspec.out_files', 'norm_files')]),
    #    (regional_avg, outputnode, [('outputspec.out_files', 'suvr_files')])
    #])
    #
    #wf.inputs.inputspec.in_pars = [bl_par,fu_par]

else:
    
    #define functions to use as nodes to separate bl/fu output from MapNodes
    #def get_baseline(in_list):
    #    return in_list[0]
    # def get_followup(in_list):
    #    return in_list[1]
    
    #funtions to take list of bl and fu, split then create tuples for invnrr input with floating file
    #def bl_create_tuple(file1,file2):
    #    bl_tuple=(file1,file2)
    #    return bl_tuple

    #def fu_create_tuple(file1,file2):
    #    fu_tuple=(file1.encode("utf-8"),file2.encode("utf-8"))
    #    return fu_tuple
    
        #not sure why this...
    #def create_defs_list(def1,def2):
    #    def_list=[def1,def2]
    #    return defs_list
    '''
    
    #def run_invert_def_bl(defs):
        
    '''
    use_pvc=args.pvc
    pvc_kernel=args.pvc_kernel
    pvc_iter=args.pvc_iter

    wf = pe.Workflow(name='compute_suvr')
    wf.base_output_dir = result_dir

    # Create all the required nodes
    inputnode = pe.Node(interface=niu.IdentityInterface(
        fields=['bl_pet',
                'fu_pet',
                'mid_par',
                'bl_t1_to_pet',
                'fu_t1_to_pet',
                'bl_t1_to_mid',
                'fu_t1_to_mid',
                'mid_to_bl_t1',
                'mid_to_fu_t1',
                'bl_brain_mask' ,
                'fu_brain_mask' #,
                #'inv_nrr_tuples'
		]),name='inputspec')
    #Create an output node
    outputnode = pe.Node(interface=niu.IdentityInterface(
        fields=['bl_norm_file',
                'fu_norm_file',
                'bl_suvr_file',
                'fu_suvr_file',
                'bl_def_file',
                'fu_def_file',
                'mid_clean_par_file',
                'bl_out_par_file',
                'fu_out_par_file']),name='outputspec')

   
    
    #DEFINE NODES
    #resample masks and clean, ref_file is always mid_t1
    #alternative without mapnodes, keep it simple
    bl_res_mask=pe.Node(interface=niftyreg.RegResample(
        verbosity_off_flag=True), name='bl_res_mask')
    bl_res_mask.inputs.inter_val='NN'

    fu_res_mask=pe.Node(interface=niftyreg.RegResample(
        verbosity_off_flag=True), name='fu_res_mask')
    fu_res_mask.inputs.inter_val='NN'

    #make resampled masks binary int for summing
    bl_binint = pe.Node(interface=fsl.UnaryMaths(operation='bin',output_type='NIFTI_GZ',output_datatype='int'),name='bl_binint')
    fu_binint = pe.Node(interface=fsl.UnaryMaths(operation='bin',output_type='NIFTI_GZ',output_datatype='int'),name='fu_binint')
    #sum and thres at 2 to get intersection
    sum_masks = pe.Node(interface=fsl.BinaryMaths(operation='add',output_type='NIFTI_GZ'),name='sum_masks')
    thresh_mask = pe.Node(interface=fsl.Threshold(thresh=2,args='-bin',
                           output_type='NIFTI_GZ'), name="thresh_mask")
    #clean midpoint par file
    apply_mask = pe.Node(interface=fsl.ApplyMask(output_type='NIFTI_GZ'), name="apply_mask")

    bl_def_file=os.path.join(result_dir,'baseline-t1_to_PET_def.nii.gz')
    print(bl_def_file)
    bl_tx_to_def = pe.Node(interface=niftyreg.RegTransform(out_file=bl_def_file), name='bl_tx_to_def')
    fu_def_file=os.path.join(result_dir,'followup-t1_to_PET_def.nii.gz')
    print(fu_def_file)
    fu_tx_to_def = pe.Node(interface=niftyreg.RegTransform(out_file=fu_def_file), name='fu_tx_to_def')

    bl_compose_def = pe.Node(interface=niftyreg.RegTransform(), name='bl_compose_def')
    fu_compose_def = pe.Node(interface=niftyreg.RegTransform(), name='fu_compose_def')

    bl_res_par = pe.Node(interface=niftyreg.RegResample(
        verbosity_off_flag=True), name='bl_res_par')
    bl_res_par.inputs.inter_val='NN'

    fu_res_par = pe.Node(interface=niftyreg.RegResample(
        verbosity_off_flag=True), name='fu_res_par')
    fu_res_par.inputs.inter_val='NN'

    #CONNECT NODES
    wf.connect([
        #resample masks to midpoint
        (inputnode, bl_res_mask, [('bl_brain_mask', 'flo_file')]),
        (inputnode, bl_res_mask, [('mid_par', 'ref_file')]),
        (inputnode, bl_res_mask, [('bl_t1_to_mid', 'trans_file')]),
        (inputnode, fu_res_mask, [('fu_brain_mask', 'flo_file')]),
        (inputnode, fu_res_mask, [('mid_par', 'ref_file')]),
        (inputnode, fu_res_mask, [('fu_t1_to_mid', 'trans_file')]),
        #bin int masks
        (bl_res_mask, bl_binint, [('out_file', 'in_file')]),
        (fu_res_mask, fu_binint, [('out_file', 'in_file')]),
        #sum masks
        (bl_binint, sum_masks, [('out_file', 'in_file')]),
        (fu_binint, sum_masks, [('out_file', 'operand_file')]),
        #threshold summed mask at 2 to get intersection
        (sum_masks, thresh_mask, [('out_file', 'in_file')]),
        #apply mask to midpoint labels
        (inputnode, apply_mask , [('mid_par', 'in_file')]),
        (thresh_mask, apply_mask , [('out_file', 'mask_file')]),
        ##invert deformation fields to get mid->t1 def
        #(inputnode, bl_create_tuple , [('bl_t1_to_mid', 'file1')]),
        #(inputnode, bl_create_tuple , [('mid_par', 'file2')]),
        #(inputnode, fu_create_tuple , [('fu_t1_to_mid', 'file1')]),
        #(inputnode, fu_create_tuple , [('mid_par', 'file2')]),
        #(bl_create_tuple, bl_invert_def , [('bl_tuple', 'inv_nrr_input')]),
        #(fu_create_tuple, fu_invert_def , [('fu_tuple', 'inv_nrr_input')]),
        #change affines to def
        (inputnode, bl_tx_to_def , [('bl_t1_to_pet', 'def_input')]),
        (inputnode, bl_tx_to_def , [('bl_pet', 'ref1_file')]),
        (inputnode, fu_tx_to_def , [('fu_t1_to_pet', 'def_input')]),
        (inputnode, fu_tx_to_def , [('fu_pet', 'ref1_file')]),
        #compose mid-->t1 def and t1-->PET defs
        (inputnode, bl_compose_def , [('mid_to_bl_t1', 'comp_input')]),
        (bl_tx_to_def, bl_compose_def , [('out_file', 'comp_input2')]),
        (inputnode, fu_compose_def , [('mid_to_fu_t1', 'comp_input')]),
        (fu_tx_to_def, fu_compose_def , [('out_file', 'comp_input2')]),
     ])
    

    bl_normalisation = create_regional_normalisation_pipeline(erode_ref=erode_ref,name='bl_normalisation')
    fu_normalisation = create_regional_normalisation_pipeline(erode_ref=erode_ref,name='fu_normalisation')

    if norm_region == 'pons':
        roi_indices = [35]
    elif norm_region == 'gm_cereb':
        roi_indices = [39, 40, 72, 73, 74]
    elif norm_region == 'wm_subcort':
        roi_indices = [45, 46]
    elif norm_region == 'wm_subcort_gif3':
        roi_indices = [81, 82, 83, 84, 85, 86, 87, 89, 90, 91, 92, 93, 94]
    else:  # full cerebellum
        roi_indices = [39, 40, 41, 42, 72, 73, 74]
    
    bl_normalisation.inputs.inputspec.label_indices = roi_indices
    fu_normalisation.inputs.inputspec.label_indices = roi_indices
    
    bl_out = pe.Node(interface=niu.IdentityInterface(fields=['in_rois']),name='bl_out')
    fu_out = pe.Node(interface=niu.IdentityInterface(fields=['in_rois']),name='fu_out')
    # If PVC, this works in a different way than before
    
    if use_pvc:
        '''
        For now:
        Resample PET to midpoint space for PVC...Not sure if best way but simplest.
        '''
        #bl_res_pet = pe.MapNode(interface=niftyreg.RegResample(
        #verbosity_off_flag=True), name='bl_res_pet')
        #bl_res_pet.inputs.inter_val='CUB'
        #fu_res_pet = pe.MapNode(interface=niftyreg.RegResample(
        #verbosity_off_flag=True), name='fu_res_pet')
        #fu_res_pet.inputs.inter_val='CUB'
        
        ## Then run the PVC
        #bl_pvc_pet = pe.Node(interface=petpvc.PETPVCDiscreteIterativeYang(
        #    x_fwhm=pvc_kernel[0], y_fwhm=pvc_kernel[1], z_fwhm=pvc_kernel[2],
        #    iteration=pvc_iter),name='bl_pvc_pet')

        #fu_pvc_pet = pe.Node(interface=petpvc.PETPVCDiscreteIterativeYang(
        #    x_fwhm=pvc_kernel[0], y_fwhm=pvc_kernel[1], z_fwhm=pvc_kernel[2],
        #    iteration=pvc_iter),name='fu_pvc_pet')

        #wf.connect([
        #    #invert mid->PET def field WILL NEED TO MAKE TUPLE OF (def_field, PET)
        #    (inputnode, bl_create_tuple_pvc , [('bl_t1_to_mid', 'file1')]),
        #    (inputnode, bl_create_tuple_pvc , [('bl_pet', 'file2')]),
        #    (inputnode, fu_create_tuple_pvc , [('fu_t1_to_mid', 'file1')]),
        #    (inputnode, fu_create_tuple_pvc , [('fu_pet', 'file2')]),
        #    (bl_create_tuple, bl_invert_def, [('bl_tuple', 'inv_nrr_input')]),
        #    (bl_compose_def, bl_invert_def, [('out_file', 'inv_nrr_input')]),
        #    #resample PET to mid
        #    (bl_invert_def, res_pet, [('out_file', 'trans_file')]),
        #    (inputnode, res_pet, [('in_pets', 'flo_file')]),
        #    (inputnode, res_pet, [('in_pars', 'ref_file')]),
        #    (apply_mask, bl_pvc_pet, [('out_file', 'label_file')]),
        #    (apply_mask, fu_pvc_pet, [('out_file', 'label_file')]),
        #    # Upsampled PET goes into PVC
        #    (res_pet, pvc_pet, [('out_file', 'pet_file')]),
        #    (bl_pvc_pet, bl_normalisation, [('out_file', 'inputspec.in_files')]),
        #    (fu_pvc_pet, fu_normalisation, [('out_file', 'inputspec.in_files')]),
        #    (apply_mask, bl_normalisation, [('out_file', 'inputspec.in_rois')]),
        #    (apply_mask, fu_normalisation, [('out_file', 'inputspec.in_rois')]),
        #    (apply_mask, bl_out, [('out_file', 'in_rois')]), #cleaned midpoint labs in mid-space
        #    (apply_mask, fu_out, [('out_file', 'in_rois')]), #cleaned midpoint labs in mid-space
        #])
    else:
        #resample mid_par to both PETs
        # If no PVC, downsample MRI
        wf.connect([
            (apply_mask, bl_res_par, [('out_file', 'flo_file')]), #cleaned midpoint labs
            (inputnode, bl_res_par, [('bl_pet', 'ref_file')]), 
            (bl_compose_def, bl_res_par, [('out_file', 'trans_file')]),
            (apply_mask, fu_res_par, [('out_file', 'flo_file')]),
            (inputnode, fu_res_par, [('fu_pet', 'ref_file')]),
            (fu_compose_def, fu_res_par, [('out_file', 'trans_file')]),
            (inputnode, bl_normalisation, [('bl_pet', 'inputspec.in_files')]),
            (bl_res_par, bl_normalisation, [('out_file', 'inputspec.in_rois')]),
            (inputnode, fu_normalisation, [('fu_pet', 'inputspec.in_files')]),
            (fu_res_par, fu_normalisation, [('out_file', 'inputspec.in_rois')]),
            (bl_res_par, bl_out, [('out_file', 'in_rois')]),
            (fu_res_par, fu_out, [('out_file', 'in_rois')]),
        ])

    # The regional uptake are computed
    bl_regional_avg = create_regional_average_pipeline(neuromorphometrics=True,name='bl_regional_avg')
    fu_regional_avg = create_regional_average_pipeline(neuromorphometrics=True,name='fu_regional_avg')    

    wf.connect([
        (bl_normalisation, bl_regional_avg, [('outputspec.out_files',
                                        'inputspec.in_files')]),
        (bl_out, bl_regional_avg, [('in_rois', 'inputspec.in_rois')]),
        (fu_normalisation, fu_regional_avg, [('outputspec.out_files',
                                        'inputspec.in_files')]),
        (fu_out, fu_regional_avg, [('in_rois', 'inputspec.in_rois')]),
        # Output node
        (bl_normalisation, outputnode, [('outputspec.out_files', 'bl_norm_file')]),
        (fu_normalisation, outputnode, [('outputspec.out_files', 'fu_norm_file')]),
        (bl_regional_avg, outputnode, [('outputspec.out_files', 'bl_suvr_file')]),
        (fu_regional_avg, outputnode, [('outputspec.out_files', 'fu_suvr_file')]),
        (bl_compose_def,outputnode, [('out_file', 'bl_def_file')]),
        (fu_compose_def,outputnode, [('out_file', 'fu_def_file')]),
    ])

    if not use_pvc:
        wf.connect(bl_res_par, 'out_file', outputnode, 'bl_out_par_file')
        wf.connect(fu_res_par, 'out_file', outputnode, 'fu_out_par_file')
        wf.connect(apply_mask, 'out_file', outputnode, 'mid_clean_par_file')
    #define inputs
    wf.inputs.inputspec.mid_par = mid_par
    wf.inputs.inputspec.bl_t1_to_pet = bl_t1_to_pet
    wf.inputs.inputspec.fu_t1_to_pet = fu_t1_to_pet
    wf.inputs.inputspec.bl_t1_to_mid = bl_t1_to_mid
    wf.inputs.inputspec.fu_t1_to_mid = fu_t1_to_mid
    wf.inputs.inputspec.mid_to_bl_t1 = mid_to_bl_t1
    wf.inputs.inputspec.mid_to_fu_t1 = mid_to_fu_t1
    wf.inputs.inputspec.bl_brain_mask = bl_brain_mask
    wf.inputs.inputspec.fu_brain_mask = fu_brain_mask
    


#common inputs to both switch_ref and full wf
wf.base_dir = result_dir
wf.inputs.inputspec.bl_pet = bl_pet
wf.inputs.inputspec.fu_pet = fu_pet	

"""
Data sink
"""
ds = pe.Node(nio.DataSink(parameterization=True, base_directory=result_dir),
             name='datasink')
wf.connect([
    (wf.get_node('outputspec'), ds, [('bl_norm_file', '@bl_norm_file'),
                                     ('bl_suvr_file', '@bl_suvr_file'),
                                     ('fu_norm_file', '@fu_norm_file'),
                                     ('fu_suvr_file', '@fu_suvr_file')])
])            

if not args.switch_ref:
    wf.connect([
        (wf.get_node('outputspec'), ds, [('bl_out_par_file', '@bl_out_par_file'),
                                         ('bl_def_file', '@bl_def_file'),
                                         ('fu_out_par_file','@fu_out_par_file'),
                                         ('fu_def_file','@fu_def_file'),
                                         ('mid_clean_par_file','@mid_clean_par_file')])

    ])

"""
graph kept trying to write to /compute_suvr/, won't write to result_dir 
#if args.graph is True:

#generate_graph(workflow=wf)
wf.write_graph(graph2use='colored')
sys.exit(0)
"""

#Edit the qsub arguments based on the input arguments
qsubargs_time = '01:00:00'
qsubargs_mem = '1.9G'

if 'OMP_NUM_THREADS' in os.environ and args.use_qsub is True:
    qsubargs_mem = '%sG' %\
                   str(max(0.95, 1.9 / int(os.environ.get('OMP_NUM_THREADS'))))

qsubargs = get_qsub_args(qsubargs_time, qsubargs_mem)


#Run the workflow

run_workflow(workflow=wf, qsubargs=qsubargs, parser=args)


