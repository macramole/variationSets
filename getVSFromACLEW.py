#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 11 16:07:34 2018

@author: leandro


Este es muy parecido a getVSFromDir pero agarra de varias fuentes.


Hacer un csv por variation set con:
. id -> esto tiene que estar tambien en el .txt
. hablante
. addressee [CHI OCH NADA]
. largo
. dad
. pra en el output de texto
. ses
. kid
. numLinea
"""

import sys
sys.path.insert(0, '../chaParser/')
import ChaFile
import VariationSets as vss
from log import Log
from glob import glob
import os
import csv
import pandas as pd

aclewPaths = [
    "../aclew/bajada-06032019/spa/todos/",
    "../aclew/bajada-06032019/eng/todos/"
]

resultPath = "./result.aclew.newest"

USE_DAD = False
USE_SMARTVERBS = False

aclewCorporaDescriptionPath = "../aclew/ACLEW_list_of_corpora.csv"
dfACLEW = pd.read_csv(aclewCorporaDescriptionPath)

log = Log( os.path.join(resultPath,"log.txt"), settings = {
    "chaPaths" : aclewPaths,
    "usingDAD" : USE_DAD,
    "smartVerbs" : USE_SMARTVERBS,
    "MAX_INTERVENCION_SPEAKER" : vss.MAX_INTERVENCION_SPEAKER,
    "MAX_INTERVENCION_CHILD" : vss.MAX_INTERVENCION_CHILD,
    "MAX_INTERVENCION_TO_CHILD" : vss.MAX_INTERVENCION_TO_CHILD,
    "MAX_INTERVENCION_OTHER" : vss.MAX_INTERVENCION_OTHER,
    "MAX_TIEMPO" : vss.MAX_TIEMPO
} )
vss.log = log


chaFilesFound = []

for path in aclewPaths:
    g = "%s/*.cha" % path
    print(g)
    for f in glob(g):
        chaFilesFound.append(f)

csvResult = [
    [ 
        "id",
        "kid",
        "std_mat_ed",
        "ses",
        "chaFile",
        "speaker",
        "addressee",
        "long",
        "wordCount"
    ]
]

csvCountResult = [
    [ 
        "kid",
        "uttToChild",
        "wordsToChild",
    ]
]

print("%d files found" % len(chaFilesFound))

for chaFile in chaFilesFound:
    print("Processing %s..." % chaFile)
    
    vss.ChaFile.USE_ALT_TARGET_CHILD = ("spa" in chaFile)
    
    result = vss.getVariationSetsFromFile( chaFile, 
                                           vss.CRITERIA_MOR, 
                                           resultPath,
                                           useDAD = USE_DAD,
                                           smartVerbs=USE_SMARTVERBS)
    
    filename = os.path.basename(chaFile)
    kid = filename[:filename.find(".")]
    ses = "?"
    
    std_mat_ed_list = dfACLEW[dfACLEW.aclew_id == int(kid)]["std_mat_ed"].tolist()
    std_mat_ed = std_mat_ed_list[0]
    if len(std_mat_ed_list) > 1:
        print("Warning: ID %s is not unique in list corpora" % kid)
    
    for vs in result:
        newRow = [
            vs["id"],
            kid,
            std_mat_ed,
            ses,
            chaFile,
            vs["speaker"],
            vs["addressee"],
            vs["long"],
            vs["wordCount"]
        ]
    
        csvResult.append(newRow)
    
    chaForCount = ChaFile.ChaFile( chaFile )
    uttToChild = chaForCount.countUtterancesByAddressee()[ChaFile.SPEAKER_TARGET_CHILD]
    wordsToChild = chaForCount.countWordsByAddressee()[ChaFile.SPEAKER_TARGET_CHILD]
    csvCountResult.append([
        kid,
        uttToChild,
        wordsToChild
    ])


with open(resultPath + "/variation_sets.csv", "w") as f :
    csvWriter = csv.writer(f)
    csvWriter.writerows(csvResult)
with open(resultPath + "/counts.csv", "w") as f :
    csvWriter = csv.writer(f)
    csvWriter.writerows(csvCountResult)