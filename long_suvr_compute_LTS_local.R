#!/usr/bin/env Rscript
## Least-Trimmed Squares (LTS) regression
## based on FAST-LTS algorith propsed in:
## Rousseeuw, P. J., & Van Driessen, K. (2006). Computing LTS regression for large data sets. Data mining and knowledge discovery, 12(1), 29-45.
## Will Coath 15-Mar-2023
## perform twice flipping axes and take values identified in both, avoiding bias

# SETUP ####
##SET ARGS
args <- commandArgs(trailingOnly = TRUE)
## test if there are two argument: if not, return an error
if (length(args) < 2) {
  stop("Two arguments must be supplied (input csv path; reference region", call. = FALSE)
}
filename <- args[1]
ref_roi <- args[2]

## set args where whilst testing
#root_dir <- "/Users/willcoath/Documents/R-analysis/long_voxel_mapping/long_csv/"
#filename <- paste0(root_dir,"sub-10024822_ses-midpoint_long_gm-cereb-clean_pet_uptake.csv")
#wide.df <- read.csv(filename)
#ref_roi <- 'gm-cereb-clean'

#import libraries
library(tidyverse)
library(ggthemes)
library(robustbase)

#read in datafile
wide.df <- read.csv(file=filename)

cbbPalette <- c("#56B4E9", "#999999", "#E69F00", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7")

# NON-ZERO FILE ####
#remove voxels not in midpoint PET region and save file
wide.df <- wide.df %>%
  filter(voxel_number!=0)
nonzerofile <- str_replace(filename, '\\.csv','_nonzero.csv')
write.csv(wide.df,file = nonzerofile, row.names = FALSE)

# N VOX ####
#get n voxels in midpoint region
nvox <- as.integer(length(wide.df$voxel_number))

# FORWARD LTS ####
#run standard lm
lm.mod <- lm(followup_uptake ~ baseline_uptake , data = wide.df)
lm.rsq <- summary(lm.mod)$r.squared
#run lts
#run both ways, first followup ~ baseline
alpha <- 0.99
lts.mod <- ltsReg(followup_uptake ~ baseline_uptake , data = wide.df,alpha=alpha,qr.out=T)
rsq <- lts.mod$rsquared

#check if lts with 0.99 R2 is higher than lm with all points
if (rsq>=lm.rsq){
  lts.method.forward=TRUE
  #convergence
  print("LTS with 1% left out beats standard OTS regression, running convergence")
  repeat
  {
    new.alpha <- alpha-0.01
    new.lts.mod <- ltsReg(followup_uptake ~ baseline_uptake, data = wide.df,alpha=new.alpha,qr.out=T)
    new.rsq <- new.lts.mod$rsquared
    print(paste0("alpha = ",alpha))
    print(paste0("new alpha = ",new.alpha))
    print(paste0("current r2 = ", rsq))
    print(paste0("new r2 = ", new.rsq))
    if (as.character(new.alpha)==as.character(0.51) | rsq>=new.rsq){
      break
    }
    rsq <- new.rsq
    alpha <- new.alpha
    lts.mod <- new.lts.mod
  }
  rsq1 <- rsq
  alpha1 <- alpha
  lts.mod1 <- lts.mod
  best_lts.df1 <- as.data.frame(lts.mod1['best'])
  lts_subset.df1 <- wide.df[best_lts.df1$best,]
  wide.df$outlier1 <- ifelse(seq_len(nrow(wide.df)) %in% best_lts.df1$best, "in", "out")
  wide.df$outlier1 <- factor(wide.df$outlier1)
  int1 <- coef(lts.mod1)[1]
  slope1 <- coef(lts.mod1)[2]
  out1 <- nvox-as.integer(lts.mod1[5])
  in1 <- as.integer(lts.mod1[5])
} else {
  lts.method.forward=FALSE
  print("Standard LM beats LTS forwards")
  #all in
  wide.df <- wide.df %>%
    mutate(outlier1 = "in")
  wide.df$outlier1 <- factor(wide.df$outlier1)
  lm.mod1 <- lm.mod
  rsq1 <- lm.rsq
  alpha1 <- 1
  int1 <- coef(lm.mod1)[1]
  slope1 <- coef(lm.mod1)[2]
  out1 <- 0
  in1 <- as.integer(nvox)
}

# BACKWARDS LTS ####
#run standard lm
lm.mod <- lm(baseline_uptake ~ followup_uptake, data = wide.df)
lm.rsq <- summary(lm.mod)$r.squared
#run lts
alpha <- 0.99
lts.mod <- ltsReg(baseline_uptake ~ followup_uptake, data = wide.df,alpha=alpha,qr.out=T)
rsq <- lts.mod$rsquared

#check if lts with 0.99 R2 is higher than lm with all points
if (rsq>=lm.rsq){
  lts.method.backward=TRUE
  #convergence
  print("LTS with 1% left out beats standard OTS regression, running convergence")
  repeat
  {
    new.alpha <- alpha-0.01
    new.lts.mod <- ltsReg(baseline_uptake ~ followup_uptake, data = wide.df,alpha=new.alpha,qr.out=T)
    new.rsq <- new.lts.mod$rsquared
    print(paste0("alpha = ",alpha))
    print(paste0("new alpha = ",new.alpha))
    print(paste0("current r2 = ", rsq))
    print(paste0("new r2 = ", new.rsq))
    if (as.character(new.alpha)==as.character(0.51) | rsq>=new.rsq){
      break
    }
    rsq <- new.rsq
    alpha <- new.alpha
    lts.mod <- new.lts.mod
  }
  rsq2 <- rsq
  alpha2 <- alpha
  lts.mod2 <- lts.mod
  best_lts.df2 <- as.data.frame(lts.mod2['best'])
  lts_subset.df2 <- wide.df[best_lts.df2$best,]
  wide.df$outlier2 <- ifelse(seq_len(nrow(wide.df)) %in% best_lts.df2$best, "in", "out")
  wide.df$outlier2 <- factor(wide.df$outlier2)
  int2 <- coef(lts.mod2)[1]
  slope2 <- coef(lts.mod2)[2]
  out2 <- nvox-as.integer(lts.mod2[5])
  in2 <- as.integer(lts.mod2[5])
} else {
  lts.method.backward=FALSE
  print("Standard LM beats LTS backwards")
  #all in
  wide.df <- wide.df %>%
    mutate(outlier2 = "in")
  wide.df$outlier2 <- factor(wide.df$outlier2)
  lm.mod2 <- lm.mod
  rsq2 <- lm.rsq
  alpha2 <- 1
  int2 <- coef(lm.mod2)[1]
  slope2 <- coef(lm.mod2)[2]
  out2 <- 0
  in2 <- as.integer(nvox)
}

# COMBINE LTS OUTLIERS ####
#exclude voxels that are both backwards and forwards outliers
wide.df$outlier_both <- ifelse(wide.df$outlier1=="in" & wide.df$outlier2=="in", "in", "out")
wide.df$outlier_both <- factor(wide.df$outlier_both)
out.both <- as.integer(sum(wide.df$outlier_both == "out"))
in.both <- as.integer(sum(wide.df$outlier_both == "in"))

# SCATTER PLOTS ####

plotfile <- str_replace(filename, '\\.csv','_LTS_plot1.pdf')
pdf(plotfile, width=6.5, height=5)
p <- ggplot(wide.df, aes(x = baseline_uptake, y = followup_uptake)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dotted", col = "black") +
  geom_point(alpha=0.5, aes(col=outlier1)) +
  scale_colour_manual(values=cbbPalette,name="Outlier") +
  geom_smooth(method = "lm",col = "grey",se = T)+
  geom_abline(slope = slope1, intercept = int1, color="black", size =1,linetype = 'dashed')+
  labs(x = 'Baseline Activity (Bq/ml)', y = 'Follow-up Activity (Bq/ml)', title = 'Outliers 1', subtitle = paste0('Ref=',ref_roi, '; N=',nvox,'; Out=', out1,'; In=', in1,'; alpha=', alpha1)) +
  theme_few() +
  coord_fixed() +
  theme(plot.title = element_text(hjust = 0.5), 
        plot.subtitle = element_text(hjust = 0.5))

p
dev.off()

plotfile <- str_replace(filename, '\\.csv','_LTS_plot2.pdf')
pdf(plotfile, width=6.5, height=5)
p <- ggplot(wide.df, aes(x = followup_uptake, y = baseline_uptake)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dotted", col = "black") +
  geom_point(alpha=0.5, aes(col=outlier2)) +
  scale_colour_manual(values=cbbPalette,name="Outlier") +
  geom_smooth(method = "lm",col = "grey",se = T)+
  geom_abline(slope = slope2, intercept = int2, color="black", size = 1,linetype = 'dashed')+
  labs(y = 'Baseline Activity (Bq/ml)', x = 'Follow-up Activity (Bq/ml)', title = 'Outliers 2', subtitle = paste0('Ref=',ref_roi, '; N=',nvox,'; Out=', out2,'; In=', in2,'; alpha=', alpha2)) +
  theme_few() +
  coord_fixed() +
  theme(plot.title = element_text(hjust = 0.5), 
        plot.subtitle = element_text(hjust = 0.5))

p
dev.off()

# LONG DF #### 
#make long df for hists
long.df <- wide.df %>%
  pivot_longer(.,cols = baseline_uptake:followup_uptake,names_to = 'timepoint',values_to = 'uptake')

long.df$timepoint <- gsub("_uptake","",long.df$timepoint)

long.df$timepoint <- factor(long.df$timepoint)
long.df$outlier1 <- factor(long.df$outlier1)
long.df$outlier2 <- factor(long.df$outlier2)
long.df$outlier_both <- factor(long.df$outlier_both)


# HIST PLOTS ####
#all points
plotfile <- str_replace(filename, '\\.csv','_allvox_hist.pdf')
pdf(plotfile, width=6.5, height=5)
p <- ggplot(long.df, aes(x=uptake)) +
  geom_histogram(aes(fill=timepoint),alpha=0.5,binwidth = 200) +
  scale_fill_manual(values=cbbPalette,name="Timepoint") +
  labs(x = 'Activity (Bq/ml)', y = 'Count', title = 'All Voxels', subtitle = paste0('Ref=',ref_roi, '; N vox=',nvox)) +
  theme_few() +
  theme(plot.title = element_text(hjust = 0.5), 
        plot.subtitle = element_text(hjust = 0.5))

p
dev.off()

plotfile <- str_replace(filename, '\\.csv','_LTS_hist.pdf')
pdf(plotfile, width=6.5, height=5)
p <- ggplot(long.df, aes(x=uptake)) +
  geom_histogram(aes(fill=timepoint),alpha=0.5,binwidth = 200) +
  labs(x = 'Activity (Bq/ml)', y = 'Count', title = 'LTS Histograms', subtitle = paste0('Ref=',ref_roi, '; N=',nvox,'; Out=', out.both,'; In=', in.both,'; alpha1=', alpha1,'; alpha2=', alpha2)) +
  theme_few() +
  #geom_vline(data = means.df, aes(xintercept=mean, col = timepoint), linetype="dashed", size=1) +
  scale_fill_manual(values=cbbPalette,name="Timepoint") +
  scale_colour_manual(values=cbbPalette,name="Timepoint") +
  theme(plot.title = element_text(hjust = 0.5), 
        plot.subtitle = element_text(hjust = 0.5)) +
  facet_wrap(~outlier_both)

p
dev.off()


# TABLES ####

outlier.both.tbl <- long.df %>% 
  group_by(timepoint,outlier_both) %>% 
  summarise(mean_uptake = mean(uptake),
            sd_uptake = sd(uptake),
            median_uptake = median(uptake), 
            min_uptake = min(uptake), max_uptake = max(uptake)
  )

ltsfile <- str_replace(filename, '\\.csv','_LTS_outlier_both_stats.csv')
write.csv(outlier.both.tbl,file = ltsfile, row.names = FALSE)

outlier.tbl <- long.df %>% 
  group_by(timepoint,outlier1,outlier2) %>% 
  summarise(mean_uptake = mean(uptake),
            sd_uptake = sd(uptake),
            median_uptake = median(uptake), 
            min_uptake = min(uptake), max_uptake = max(uptake)
  )

ltsfile <- str_replace(filename, '\\.csv','_LTS_outlier_stats.csv')
write.csv(outlier.tbl,file = ltsfile, row.names = FALSE)

#all.tbl <- long.df %>% 
#  group_by(timepoint) %>% 
#  summarise(mean_uptake = mean(uptake),
#            sd_uptake = sd(uptake),
#            median_uptake = median(uptake), 
#            min_uptake = min(uptake), max_uptake = max(uptake)
#  )

#ltsfile <- str_replace(filename, '\\.csv','_LTS_all_stats.csv')
#write.csv(all.tbl,file = ltsfile, row.names = FALSE)

# OUTPUT FILES ####
ltsfile <- str_replace(filename, '\\.csv','_LTS.csv')
write.csv(wide.df,file = ltsfile, row.names = FALSE)

outlierfile <- str_replace(filename, '\\.csv','_outlier_vox_list.csv')

wide.df %>%
  filter(outlier_both == "out") %>%
  select(voxel_number) %>%
  write.csv(.,file = outlierfile, row.names = FALSE)