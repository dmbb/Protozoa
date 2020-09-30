import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os, sys
import csv
import numpy as np
import random
from random import shuffle
import math
import time
import warnings


import sklearn
from sklearn import preprocessing
from sklearn.model_selection import ParameterGrid
#Classifiers
from xgboost import XGBClassifier
import xgboost as xgb

#Eval Metrics
from sklearn.model_selection import train_test_split, cross_val_score, KFold, StratifiedKFold
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve, auc
from scipy import interp

from termcolor import colored 
from itertools import combinations

sklearn.set_config(assume_finite=True)

def PrintColored(string, color):
    print(colored(string, color))


def gatherAllData(cfg, dataset_fraction):
    #Load Datasets
    f = open(cfg[0] + "/" + os.path.basename(cfg[0]) + ".csv", 'r')
    reader = csv.reader(f, delimiter=',')
    reg = list(reader)
    reg = reg[:int(dataset_fraction*len(reg))]

    f = open(cfg[1] + "/" + os.path.basename(cfg[1]) + ".csv", 'r')
    reader = csv.reader(f, delimiter=',')
    fac = list(reader)
    fac = fac[:int(dataset_fraction*len(fac))]

    #Convert data to floats (and labels to integers)
    features_id = reg[0]
    reg_data = []
    for i in reg[1:]:
        int_array = []
        for pl in i[:-1]:
            int_array.append(float(pl))
        int_array.append(0)
        reg_data.append(int_array)

    fac_data = []
    for i in fac[1:]:
        int_array = []
        for pl in i[:-1]:
            int_array.append(float(pl))
        int_array.append(1)
        fac_data.append(int_array)


    #Shuffle both datasets
    shuffled_reg_data = random.sample(reg_data, len(reg_data))
    shuffled_fac_data = random.sample(fac_data, len(fac_data))

    #Build label tensors
    reg_labels = []
    for i in shuffled_reg_data:
        reg_labels.append(int(i[len(reg_data[0])-1]))

    fac_labels = []
    for i in shuffled_fac_data:
        fac_labels.append(int(i[len(reg_data[0])-1]))

    #Take label out of data tensors
    for i in range(0, len(shuffled_reg_data)):
        shuffled_reg_data[i].pop()

    for i in range(0, len(shuffled_fac_data)):
        shuffled_fac_data[i].pop()

    #Create training sets by combining the randomly selected samples from each class
    train_x = shuffled_reg_data + shuffled_fac_data
    train_y = reg_labels + fac_labels

    #Shuffle positive/negative samples for CV purposes
    x_shuf = []
    y_shuf = []
    index_shuf = range(len(train_x))
    shuffle(index_shuf)
    for i in index_shuf:
        x_shuf.append(train_x[i])
        y_shuf.append(train_y[i])

    return x_shuf, y_shuf, features_id

def runClassificationKFold_CV(data_folder, mode, cfg, classifier, comparison, location, cap_folder):
    #Set fixed randomness
    np.random.seed(1)
    random.seed(1)

    dataset_fraction = 1.0
    train_x, train_y, features_id = gatherAllData(cfg, dataset_fraction)

    model = classifier[0]
    clf_name = classifier[1]

    #Report Cross-Validation Accuracy
    PrintColored(clf_name + " : " + os.path.basename(cfg[0]) + " vs " + os.path.basename(cfg[1]), 'green')

    cv = StratifiedKFold(n_splits=10)
    tprs = []
    aucs = []
    mean_fpr = np.linspace(0, 1, 100)
    train_times = []
    test_times = []
    importances = []

    #Split the data in k-folds, perform classification, and report ROC
    i = 0
    for train, test in cv.split(train_x, train_y):

        start_train = time.time()
        model = model.fit(np.asarray(train_x)[train], np.asarray(train_y)[train])
        end_train = time.time()
        train_times.append(end_train - start_train)

        start_test = time.time()
        probas_ = model.predict_proba(np.asarray(train_x)[test])
        end_test = time.time()
        test_times.append(end_test - start_test)

        # Compute ROC curve and area under the curve
        fpr, tpr, thresholds = roc_curve(np.asarray(train_y)[test], probas_[:, 1], pos_label=1)
        roc_auc = auc(fpr, tpr)


        if(roc_auc < 0.5):
            roc_auc = 1 - roc_auc
            fpr = [1 - e for e in fpr]
            fpr.sort()
            tpr = [1 - e for e in tpr]
            tpr.sort()

        tprs.append(interp(mean_fpr, fpr, tpr))
        tprs[-1][0] = 0.0
        aucs.append(roc_auc)
        i += 1

    plt.plot([0, 1], [0, 1], linestyle='--', lw=2, color='r', label='Random Guess', alpha=.8)


    mean_tpr = np.mean(tprs, axis=0)
    mean_tpr[-1] = 1.0
    mean_auc = auc(mean_fpr, mean_tpr)
    print "Model AUC: " + "{0:.3f}".format(mean_auc)

    if(mean_auc < 0.5):
        mean_auc = 1 - mean_auc
        print "Inverting ROC curve - new auc: " + str(mean_auc)
        fpr = [1 - e for e in fpr]
        fpr.sort()
        tpr = [1 - e for e in tpr]
        tpr.sort()


    print "10-Fold AUC: " + "{0:.3f}".format(mean_auc)


    #Figure properties
    fig = plt.figure()
    ax1 = fig.add_subplot(111)

    std_auc = np.std(aucs)

    plt.plot(mean_fpr, mean_tpr, color='b', label=r'Mean ROC (AUC = %0.2f $\pm$ %0.3f)' % (mean_auc, std_auc), lw=2, alpha=.8)

    #Compute Standard Deviation between folds
    std_tpr = np.std(tprs, axis=0)
    tprs_upper = np.minimum(mean_tpr + std_tpr, 1)
    tprs_lower = np.maximum(mean_tpr - std_tpr, 0)
    plt.fill_between(mean_fpr, tprs_lower, tprs_upper, color='grey', alpha=.3, label=r'$\pm$ ROC Std. Dev.')


    #Save data to file TODO
    if not os.path.exists('classificationData/' + cap_folder + "/" + location + "/" + comparison + "/" + mode):
                os.makedirs('classificationData/' + cap_folder + "/" + location + "/" + comparison + "/" + mode)
                
    np.save('classificationData/' + cap_folder + "/" + location + "/" + comparison + "/" + mode + "/" + "ROC_10CV_" + clf_name + "_Sensitivity", np.array(mean_tpr))
    np.save('classificationData/' + cap_folder + "/" + location + "/" + comparison + "/" + mode + "/" + "ROC_10CV_" + clf_name + "_Specificity", np.array(mean_fpr))

    ax1.plot([0, 1], [0, 1], 'k--', lw=2, color='orange', label = 'Random Guess')
    ax1.grid(color='black', linestyle='dotted')

    plt.title('Receiver Operating Characteristic (ROC)')
    plt.xlabel('False Positive Rate', fontsize='x-large')
    plt.ylabel('True Positive Rate', fontsize='x-large')
    plt.legend(loc='lower right', fontsize='large')

    plt.setp(ax1.get_xticklabels(), fontsize=14)
    plt.setp(ax1.get_yticklabels(), fontsize=14)

    if not os.path.exists('classificationResults/' + cap_folder + "/" + location + "/" + comparison + "/" + mode):
        os.makedirs('classificationResults/' + cap_folder + "/" + location + "/" + comparison + "/" + mode)
    fig.savefig('classificationResults/' + cap_folder + "/" + location + "/" + comparison + "/" + mode + "/" + "ROC_10CV_" + clf_name + "_" + os.path.basename(cfg[1]) + ".pdf")   # save the figure to file
    plt.close(fig)

    return mean_tpr, mean_fpr, mean_auc, os.path.basename(cfg[1])



def runClassification(classifiers, baselines, modes, cap_folder, location):
    
    baselines_combinations = combinations(baselines, 2)

    for baseline_set in baselines_combinations:
        comparison = baseline_set[0] + "-" + baseline_set[1]

        PrintColored("Running classifiers for " + baseline_set[0] + " and " + baseline_set[1], 'red')

        for mode in modes:
            if(".DS_Store" in mode):
                    continue


            PrintColored("Mode: " + mode, 'cyan')
            
            #baseline regular folder
            features_folder = 'extractedFeatures/' + cap_folder + "/" + baseline_set[0] + "/" + location + '/' + mode + '/'
            baseline = baseline_set[0] + "_0"
            baseline_folder = features_folder + baseline

            #challenger folders
            comp_folder = 'extractedFeatures/' + cap_folder + "/" + baseline_set[1] + "/" + location + '/' + mode + '/'
            comp_features_folders = os.listdir(comp_folder)
            comp_features_folders = [comp_folder + s for s in comp_features_folders]

            #regular_folders w/o the regular_0 baseline
            regular_features_folders = os.listdir(features_folder)
            regular_features_folders = [e for e in regular_features_folders if baseline not in e]
            regular_features_folders = [features_folder + s for s in regular_features_folders]

            folders = regular_features_folders + comp_features_folders
            folders.sort()


            for classifier in classifiers:

                for sample_folder in folders:
                    if(".DS_Store" in sample_folder or baseline in sample_folder):
                        continue
                    data_folder = baseline + '-' + os.path.basename(sample_folder) + '/'

                    tpr, fpr, auc, sample_set = runClassificationKFold_CV(data_folder, mode, [baseline_folder, sample_folder], classifier, comparison, location, cap_folder)
                        
                    PrintColored("#####################################",'red')



if __name__ == "__main__":
    warnings.filterwarnings(action='ignore', category=DeprecationWarning)

    if(len(sys.argv) < 2):
        print "Input sample folder location"
        sys.exit(0)

    cap_folder_name = sys.argv[1]


    if not os.path.exists('classificationResults'):
                os.makedirs('classificationResults')

    classifiers = [
    [XGBClassifier(),"XGBoost"]
    ]



    baselines = os.listdir('extractedFeatures/' + cap_folder_name + '/')
    baselines = [e for e in baselines if ".DS_Store" not in e]

    #For kinds of traffic (Protozoa | Regular versions)
    for b in baselines:
        PrintColored("Analyzing " + b + " Baseline", "yellow")
        profiles = os.listdir('extractedFeatures/' + cap_folder_name + "/" + b)
        profiles = [e for e in profiles if ".DS_Store" not in e]
        
        #For video profiles (Chat, LiveCoding, Gaming, Sports)
        for profile in profiles:
            PrintColored("Analyzing " + profile + " Video Profile", "yellow")
            network_conditions = os.listdir('extractedFeatures/' + cap_folder_name + "/" + b + "/" + profile)
            network_conditions = [e for e in network_conditions if ".DS_Store" not in e]

            #For network conditions (regular, bw, drop, latency)
            for network_condition in network_conditions:
                PrintColored("Analyzing " + network_condition + " Network Condition", "yellow")
                samples_folder =  profile + "/" + network_condition

                #Filter MODES is use
                modes = os.listdir('extractedFeatures/' + cap_folder_name + "/" + baselines[0] + "/" + profile + "/" + network_condition + '/')
                
                #Pattern for matching wanted modes
                #modes = [mode for mode in modes if ("_10_" in mode)]
                #modes = [mode for mode in modes if((mode.endswith('_1000') and mode.startswith('Stats')) or (mode.endswith('_1000') and mode.startswith('PL')) )]""" or
                #    (mode.endswith('_1000') and mode.startswith('RTCPTimeStats')) or (mode.endswith('_1000') and mode.startswith('RTPTimeStats')) or
                #    (mode.endswith('_1000') and mode.startswith('RTCPPL')) or (mode.endswith('_1000') and mode.startswith('RTPPL')))]"""
                    
                runClassification(classifiers, baselines, modes, cap_folder_name, samples_folder)
