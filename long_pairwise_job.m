function long_pairwise_job(bl_t1, fu_t1, yrs_dif, spm_dir)
addpath(spm_dir);
% check arguments are specified
if nargin < 4
    error('T1 raw image must be specified');
end

spm_jobman('initcfg');

%-----------------------------------------------------------------------
% Job saved on 20-Jul-2020 10:59:26 by cfg_util (rev $Rev: 6460 $)
% spm SPM - SPM12 (12.1)
% cfg_basicio BasicIO - Unknown
%-----------------------------------------------------------------------
matlabbatch{1}.spm.tools.longit{1}.pairwise.vols1 = {[bl_t1, ',1']};
matlabbatch{1}.spm.tools.longit{1}.pairwise.vols2 = {[fu_t1, ',1']};
matlabbatch{1}.spm.tools.longit{1}.pairwise.tdif = yrs_dif;
matlabbatch{1}.spm.tools.longit{1}.pairwise.noise = NaN;
matlabbatch{1}.spm.tools.longit{1}.pairwise.wparam = [0 0 100 25 100];
matlabbatch{1}.spm.tools.longit{1}.pairwise.bparam = 1000000;
matlabbatch{1}.spm.tools.longit{1}.pairwise.write_avg = 1;
matlabbatch{1}.spm.tools.longit{1}.pairwise.write_jac = 1;
matlabbatch{1}.spm.tools.longit{1}.pairwise.write_div = 1;
matlabbatch{1}.spm.tools.longit{1}.pairwise.write_def = 1;

spm('defaults', 'PET');
spm_jobman('run', matlabbatch);

exit;
