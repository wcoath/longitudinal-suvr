#!/usr/bin/env Rscript
## Least-Trimmed Squares (LTS) regression
## based on FAST-LTS algorith propsed in:
## Rousseeuw, P. J., & Van Driessen, K. (2006). Computing LTS regression for large data sets. Data mining and knowledge discovery, 12(1), 29-45.
## Will Coath 01-Nov-2021

##SET ARGS
args <- commandArgs(trailingOnly = TRUE)
## test if there are two argument: if not, return an error
if (length(args) < 3) {
  stop("Two arguments must be supplied (input csv path; reference region", call. = FALSE)
}
filename <- args[1]
ref_roi <- args[2]
alpha <- as.numeric(args[3])

## set args where whilst testing
#root_dir <- "/Users/willcoath/Documents/Neuroscience/R/voxel_suvr/"
#filename <- paste0(root_dir,"sub-10250925_ses-midpoint_long_gm-cereb-clean_pet_uptake.csv")
#wide.df <- read.csv(filename)
#ref_roi <- 'gm-cereb-clean'

#import libraries
library(tidyverse)
library(ggthemes)
library(robustbase)

#read in datafile
wide.df <- read.csv(file=filename)

cbbPalette <- c("#56B4E9", "#999999", "#E69F00", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7")

#remove voxels not in midpoint PET region and save file
wide.df <- wide.df %>%
  filter(voxel_number!=0)
nonzerofile <- str_replace(filename, '.csv','_nonzero.csv')
write.csv(wide.df,file = nonzerofile, row.names = FALSE)

#get n voxels in midpoint region
nvox <- length(wide.df$voxel_number)

# LTS regression, set alpha anywhere between 0.5 and 1, voxels to include
lts.mod <- ltsReg(followup_uptake ~ baseline_uptake, data = wide.df,alpha=alpha)

#get subset used and subset outliers
best_lts.df <- as.data.frame(lts.mod['best'])
lts_subset.df <- wide.df[best_lts.df$best,]
#lts_outlier_subset.df  <- wide.df[-best_lts.df$best,]

wide.df$outlier <- ifelse(seq_len(nrow(wide.df)) %in% best_lts.df$best, FALSE, TRUE)

int <- coef(lts.mod)[1]
slope <- coef(lts.mod)[2]

#bl_min <- min(wide.df['baseline_uptake'])
#fu_min <- min(wide.df['followup_uptake'])
#bl_max <- max(wide.df['baseline_uptake'])
#fu_max <- max(wide.df['followup_uptake'])

#minmin <- min(bl_min,fu_min)
#maxmax <- max(bl_max,fu_max)
plotfile <- str_replace(filename, '.csv','_LTS_plot.pdf')
pdf(plotfile, width=6.5, height=5)
p <- ggplot(wide.df, aes(x = baseline_uptake, y = followup_uptake)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dotted", col = "black") +
  geom_point(alpha=0.5, aes(col=outlier)) +
  scale_colour_manual(values=cbbPalette,name="Outlier") +
  #geom_smooth(col = "red", method = 'lm',linetype = 'dotted') +
  geom_abline(slope = slope, intercept = int, color="black", size =1,linetype = 'dashed')+
  labs(x = 'Baseline Uptake (Bq)', y = 'Followup Uptake (Bq)', title = 'LTS Outliers', subtitle = paste0('Ref=',ref_roi, '; N=',nvox,'; Out=', nvox-as.integer(lts.mod[5]),'; In=', lts.mod[5],'; alpha=', lts.mod[1])) +
  #scale_x_continuous(limits=c(minmin, maxmax)) +
  #scale_y_continuous(limits=c(minmin, maxmax)) +
  theme_few() +
  coord_fixed() +
  theme(plot.title = element_text(hjust = 0.5), 
        plot.subtitle = element_text(hjust = 0.5))

p
dev.off()

#make long df for hists
long.df <- wide.df %>%
  pivot_longer(.,cols = baseline_uptake:followup_uptake,names_to = 'timepoint',values_to = 'uptake') 

#bl_m <- mean(wide.df$baseline_uptake)
#fu_m <- mean(wide.df$followup_uptake)
#bl_m <- mean(wide.df$baseline_uptake[wide.df$outlier==FALSE])
#fu_m <- mean(wide.df$followup_uptake[wide.df$outlier==FALSE])

#all points
plotfile <- str_replace(filename, '.csv','_allvox_hist.pdf')
pdf(plotfile, width=6.5, height=5)
p <- ggplot(long.df, aes(x=uptake)) +
  geom_histogram(aes(col=timepoint),fill=NA,binwidth = 300) +
  scale_colour_manual(values=cbbPalette,name="Timepoint") +
  labs(x = 'Uptake (Bq)', y = 'Count', title = 'All Voxels', subtitle = paste0('Ref=',ref_roi, '; N vox=',nvox)) +
  theme_few() +
  theme(plot.title = element_text(hjust = 0.5), 
        plot.subtitle = element_text(hjust = 0.5))

p
dev.off()

plotfile <- str_replace(filename, '.csv','_LTS_hist.pdf')
pdf(plotfile, width=6.5, height=5)
p <- ggplot(long.df, aes(x=uptake)) +
  geom_histogram(aes(col=timepoint),alpha=0.25,fill=NA,binwidth = 300) +
  scale_colour_manual(values=cbbPalette,name="Timepoint") +
  labs(x = 'Uptake (Bq)', y = 'Count', title = 'LTS Histograms', subtitle = paste0('Ref=',ref_roi, '; N=',nvox,'; Out=', nvox-as.integer(lts.mod[5]),'; In=', lts.mod[5],'; alpha=', lts.mod[1])) +
  theme_few() +
  theme(plot.title = element_text(hjust = 0.5), 
        plot.subtitle = element_text(hjust = 0.5)) +
  facet_wrap(~outlier)

p
dev.off()

ltsfile <- str_replace(filename, '.csv','_LTS.csv')
write.csv(wide.df,file = ltsfile, row.names = FALSE)

outlierfile <- str_replace(filename, '.csv','_outlier_vox_list.csv')
wide.df %>%
  filter(outlier == TRUE) %>%
  select(voxel_number) %>%
  write.csv(.,file = outlierfile, row.names = FALSE)

