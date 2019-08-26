#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: leandro

"""

import sys
sys.path.insert(0, '../chaParser/')
import ChaFile
from log import Log

import VariationSets as vss
from glob import glob
import csv
import os

chaPaths = ["../corpusESPON/longi_audio1/codificados/"]
skipChas = []
resultPath = "./test/"

log = Log( os.path.join(resultPath,"log.txt"), settings = {
    "chaPaths" : chaPaths,
    "usingDAD" : vss.usingDAD,
    "MAX_INTERVENCION_SPEAKER" : vss.MAX_INTERVENCION_SPEAKER,
    "MAX_INTERVENCION_CHILD" : vss.MAX_INTERVENCION_CHILD,
    "MAX_INTERVENCION_TO_CHILD" : vss.MAX_INTERVENCION_TO_CHILD,
    "MAX_INTERVENCION_OTHER" : vss.MAX_INTERVENCION_OTHER,
    "MAX_TIEMPO" : vss.MAX_TIEMPO
} )
vss.log = log


chaFilesFound = []
for chaPath in chaPaths:
    chaFilesFoundTmp = glob( chaPath + "/*.cha" )
    chaFilesFound += chaFilesFoundTmp
    
if len(chaFilesFound) == 0:
    log.log("No cha files found at %s" % chaPath + "/*.cha" )
    exit(1)

csvResult = [
    [ 
        "id",
        "kid",
        "ses",
        "chaFile",
        "speaker",
        "addressee",
        "long",
        "wordCount",
        "dad",
    ]
]
csvCountResult = [
    [ 
        "kid",
        "uttToChild",
        "wordsToChild",
    ]
]

for chaFile in chaFilesFound:
    log.log("\n\nProcessing %s..." % chaFile)
    
    if chaFile in skipChas:
        log.log("skip")
        continue
    
    result = vss.getVariationSetsFromFile( chaFile, vss.CRITERIA_MOR, resultPath, 
                                           useDAD=True, smartVerbs=True )
    
    ses = "nsb"
    if chaFile.find("-nsm-") > 0:
        ses = "nsm"

    kid = chaFile.split("-")[1]
    
    for vs in result:
        newRow = [
            vs["id"],
            kid,
            ses,
            chaFile,
            vs["speaker"],
            vs["addressee"],
            vs["long"],
            vs["wordCount"],
            vs["dad"],
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

    
    
