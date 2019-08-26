#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 29 14:24:45 2018

@author: leandro
"""

import os
import sys
from difflib import SequenceMatcher

sys.path.insert(0, '../chaParser/')
import ChaFile
from log import Log

CRITERIA_THRESHOLD = "t"
CRITERIA_MOR = "m"

THRESHOLD = 0.55 #solo para criteria_threshold

CATEGORIAS_VERBOS = ["v","ger","part","aux","imp","inf"] #saco el "cop" y "co"
CATEGORIAS_SUSTANTIVO_ADJETIVO = ["adj", "n"]
CATEGORIAS_TOTALES = CATEGORIAS_VERBOS + CATEGORIAS_SUSTANTIVO_ADJETIVO 

usingDAD = True
useSmartVerbs = True

MAX_INTERVENCION_SPEAKER = 1 # cuantas "intervenciones" del mismo hablante
MAX_INTERVENCION_CHILD = 999 # cuantas intervenciones del CHI
MAX_INTERVENCION_TO_CHILD = 1 # cuantas intervenciones al CHI
MAX_INTERVENCION_OTHER = 3 # cuantas intervenciones del other
MAX_TIEMPO = 4000 #en ms (4000 default)

log = Log()

def getVariationSetsFromFile( chaFilePath, criteria, 
                              resultPath, useDAD = True, 
                              smartVerbs = True ):
    global usingDAD, useSmartVerbs
    
    useSmartVerbs = smartVerbs
    
    usingDAD = useDAD
    tiers = [ ChaFile.TIER_MOR, ChaFile.TIER_ACTIVITY ]
    
    if not usingDAD:
        tiers = [ ChaFile.TIER_MOR ]
    
    ChaFile.log = log
    
    chaFile = ChaFile.ChaFile( chaFilePath, 
                               SPEAKER_IGNORE=[ ChaFile.SPEAKER_SILENCE, ChaFile.SPEAKER_TARGET_CHILD ],
                               USE_TIERS=tiers)
    
    if usingDAD:
        chaFile.fixDAD()
    if useSmartVerbs:
        chaFile.getVerbs()
    
    # Preparo el dir donde voy a arrojar mis resultados
    resultPath = os.path.join( resultPath , chaFile.filename ) + "/"
    
    if os.path.isdir( resultPath ):
        log.log("Aviso: El directorio %s ya existe \n" % resultPath)
    else:
        os.makedirs( resultPath )        
    #####

#    lines = chaParser.getLines(chaFile)
    allVariationSets = getVariationSetsFromLines(chaFile.getLines(), criteria)
    
#    return inspectVS(allVariationSets)
    inspectVSAsUnit(allVariationSets, chaFile)
    saveResults(allVariationSets, resultPath)
    return allVariationSets

def getVariationSetsFromLines(lines, criteria):
    
    variationSets = []

    linesInVS = []
    skippedToChildLineIndex = None
    lineCurrentIndex = 0
    currentVariationSet = []
    
    qtyIntervencionSpeaker = 0
    qtyIntervencionChild = 0
    qtyIntervencionOther = 0
    qtyIntervencionToChild = 0

    def endVariationSet():
        nonlocal lineCurrentIndex, currentVariationSet, variationSets, skippedToChildLineIndex
        
        if len(currentVariationSet) >= 2:
            objVariationSet = {
                "id" : constructId(currentVariationSet),
                "lines" : currentVariationSet
            }
            variationSets.append(objVariationSet)
            
        
        currentVariationSet = []
        
        if skippedToChildLineIndex != None:
            lineCurrentIndex = skippedToChildLineIndex - 1 #-1 por el +1 que hay al final
            skippedToChildLineIndex = None
    
    while lineCurrentIndex < len(lines):
        lineCurrent = lines[ lineCurrentIndex ]
        
        if len(currentVariationSet) == 0:
            if lineCurrent[ChaFile.LINE_ADDRESSEE] == ChaFile.SPEAKER_TARGET_CHILD:
                if not lineCurrent in linesInVS:
                    currentVariationSet = [ lineCurrent ]
                    linesInVS.append(lineCurrent)
                    
                    qtyIntervencionSpeaker = 0
                    qtyIntervencionChild = 0
                    qtyIntervencionOther = 0
                    qtyIntervencionToChild = 0
            
            lineCurrentIndex += 1
            continue
        
        lineToCompare = currentVariationSet[-1]
        sameSpeaker = ( lineCurrent[ChaFile.LINE_SPEAKER] == lineToCompare[ChaFile.LINE_SPEAKER] )
        
#        debugLineCurrent = lineCurrent[ChaFile.LINE_UTTERANCE]
#        debugToCompare = lineToCompare[ChaFile.LINE_UTTERANCE]
#        debugLineCurrentNumber = lineCurrent[ChaFile.LINE_NUMBER]
#        debugToCompareNumber = lineToCompare[ChaFile.LINE_NUMBER]
        
        if not sameSpeaker:
            #es el niño?
            if lineCurrent[ChaFile.LINE_SPEAKER] == ChaFile.SPEAKER_TARGET_CHILD:
                qtyIntervencionChild += 1
                if qtyIntervencionChild > MAX_INTERVENCION_CHILD:
                    endVariationSet()
            else:
                #esta dirigida al niño?
                if lineCurrent[ChaFile.LINE_ADDRESSEE] == ChaFile.SPEAKER_TARGET_CHILD:
                    qtyIntervencionToChild += 1
                    if skippedToChildLineIndex is None:
                        skippedToChildLineIndex = lineCurrentIndex
                    if qtyIntervencionToChild > MAX_INTERVENCION_TO_CHILD:
                        endVariationSet()
                    
                else:
                    qtyIntervencionOther += 1
                    if qtyIntervencionOther > MAX_INTERVENCION_OTHER:
                        endVariationSet()
        else:
            if lineCurrent[ChaFile.LINE_ADDRESSEE] == ChaFile.SPEAKER_TARGET_CHILD:
                palabrasCompartidas = getPalabrasCompartidas(lineCurrent, lineToCompare)
                
                timeStartCurrent = timeEndCompare = None
                
                if ChaFile.LINE_BULLET in lineCurrent:
                    timeStartCurrent = lineCurrent[ChaFile.LINE_BULLET][0]
                    timeEndCompare = lineToCompare[ChaFile.LINE_BULLET][1]                    
                
                if len( palabrasCompartidas ) > 0 and (timeStartCurrent is None or timeStartCurrent - timeEndCompare <= MAX_TIEMPO):
                    
                    currentVariationSet += [ lineCurrent ]
                    linesInVS.append(lineCurrent)
                    
                    # se resetean porque las intervining son entre dos emisiones
                    qtyIntervencionSpeaker = 0
                    qtyIntervencionChild = 0
                    qtyIntervencionOther = 0
                    qtyIntervencionToChild = 0
                else:
                    if skippedToChildLineIndex is None:
                        skippedToChildLineIndex = lineCurrentIndex
                    
                    qtyIntervencionSpeaker += 1
                    if qtyIntervencionSpeaker > MAX_INTERVENCION_SPEAKER:
                        endVariationSet()
                    
            else:
                endVariationSet()
        
        if lineCurrentIndex == len(lines) - 1:
            endVariationSet()
            
        lineCurrentIndex += 1
        
        
    
    return variationSets

def constructId(variationSet):
    newId = str(variationSet[0][ChaFile.LINE_NUMBER]) + "-" + str(variationSet[-1][ChaFile.LINE_NUMBER])
    return newId

def getSimilitud(lineFrom, lineTo):
    matcher = SequenceMatcher(None, lineFrom[ChaFile.LINE_UTTERANCE], lineTo[ChaFile.LINE_UTTERANCE])
    diffRatio = matcher.ratio()
    return diffRatio

def getPalabrasCompartidas(lineFrom, lineTo):
#    if not ChaFile.TIER_MOR in lineFrom or not ChaFile.TIER_MOR in lineTo:
    if lineFrom[ChaFile.TIER_MOR] == ChaFile.MISSING_VALUE or lineTo[ChaFile.TIER_MOR] == ChaFile.MISSING_VALUE :
        return []

    palabrasCompartidas = []

    if not useSmartVerbs:
        for morDataFrom in lineFrom[ChaFile.TIER_MOR]:
            if not morDataFrom[ChaFile.MOR_UNIT_CATEGORIA] in CATEGORIAS_TOTALES:
                continue
    
            for morDataTo in lineTo[ChaFile.TIER_MOR]:
                if not morDataTo[ChaFile.MOR_UNIT_CATEGORIA] in CATEGORIAS_TOTALES:
                    continue
    
                if morDataFrom[ChaFile.MOR_UNIT_LEXEMA] == morDataTo[ChaFile.MOR_UNIT_LEXEMA]:
                    if morDataFrom[ChaFile.MOR_UNIT_CATEGORIA] == morDataTo[ChaFile.MOR_UNIT_CATEGORIA]:
                        #hacemos que "co" con "co" no valga
                        # if morDataFrom["categoria"] != "co":
                        palabrasCompartidas.append(morDataFrom)
                    else:
                        if morDataFrom[ChaFile.MOR_UNIT_CATEGORIA] in CATEGORIAS_VERBOS and morDataTo[ChaFile.MOR_UNIT_CATEGORIA] in CATEGORIAS_VERBOS:
                            palabrasCompartidas.append(morDataFrom)
    else:
        for morDataFromIndex, morDataFrom in enumerate(lineFrom[ChaFile.TIER_MOR]):
            if not morDataFrom[ChaFile.MOR_UNIT_CATEGORIA] in CATEGORIAS_SUSTANTIVO_ADJETIVO:
                continue
    
            for morDataTo in lineTo[ChaFile.TIER_MOR]:
                if not morDataTo[ChaFile.MOR_UNIT_CATEGORIA] in CATEGORIAS_SUSTANTIVO_ADJETIVO:
                    continue
    
                if morDataFrom[ChaFile.MOR_UNIT_LEXEMA] == morDataTo[ChaFile.MOR_UNIT_LEXEMA]:
                    if morDataFrom[ChaFile.MOR_UNIT_CATEGORIA] == morDataTo[ChaFile.MOR_UNIT_CATEGORIA]:
                        palabrasCompartidas.append(morDataFromIndex)
                    
        for verbFrom in lineFrom[ChaFile.LINE_VERBS]:
            for verbTo in lineTo[ChaFile.LINE_VERBS]:
                lexemaFrom = lineFrom[ChaFile.TIER_MOR][verbFrom][ChaFile.MOR_UNIT_LEXEMA]
                lexemaTo = lineTo[ChaFile.TIER_MOR][verbTo][ChaFile.MOR_UNIT_LEXEMA]
                if lexemaFrom == lexemaTo:
                    palabrasCompartidas.append(verbFrom)

    return palabrasCompartidas
    
def saveResults(variationSets, resultPath):
    
    newFileName = "variationsets.txt"
    newFilePath = os.path.join( resultPath, newFileName )
    with open(newFilePath, "w") as newFile:
        newFile.write("Found: " + str(len(variationSets)) + "\n\n")
        for vs in variationSets:
            newFile.write("***********\n")
            newFile.write("Id: %s\n" % vs["id"])
            newFile.write("Hablante: %s\n" % vs["lines"][0][ChaFile.LINE_SPEAKER])
            newFile.write("Largo: %d\n\n" % len(vs["lines"]))
            
            for line in vs["lines"]:
                if usingDAD:
                    newFile.write("[%s] - %s %s [%s]\n" % (line[ ChaFile.LINE_NUMBER ],
                                                              line[ ChaFile.LINE_UTTERANCE ],
                                                              " (+ %s)" % line[ ChaFile.LINE_ADDRESSEE ] if line[ ChaFile.LINE_ADDRESSEE ] != ChaFile.SPEAKER_ADULT else "", 
                                                              line[ChaFile.TIER_ACTIVITY] ))
                                                              
                else:
                    newFile.write("[%s] - %s %s\n" % (line[ ChaFile.LINE_NUMBER ], 
                                                      line[ ChaFile.LINE_UTTERANCE ], 
                                                      " (+ %s)" % line[ ChaFile.LINE_ADDRESSEE ] if line[ ChaFile.LINE_ADDRESSEE ] != ChaFile.SPEAKER_ADULT else ""))
            
            newFile.write("\n")
            
            for i in range( 0, len(vs["lines"])-1 ):
                palabrasCompartidas = getPalabrasCompartidas( vs["lines"][i], vs["lines"][i+1] )
                
                # esto es porque devuelve int o obj dependiendo si smartVerbs o no
                if type(palabrasCompartidas[0]) == int:
                    strPalabras = str( [ vs["lines"][i][ChaFile.TIER_MOR][x] for x in palabrasCompartidas ] )
                else:
                    strPalabras = str( palabrasCompartidas )
                    
                newFile.write("[%s]-[%s] %s\n" % 
                              (vs["lines"][i][ChaFile.LINE_NUMBER],
                               vs["lines"][i+1][ChaFile.LINE_NUMBER], 
                               strPalabras ))
                
                
            newFile.write("\n\n")

def inspectVSAsUnit(vss, chaFile):
    distintosDAD = []
    
    for vs in vss:
        vs["speaker"] = vs["lines"][0][ChaFile.LINE_SPEAKER]
        vs["addressee"] = vs["lines"][0][ChaFile.LINE_ADDRESSEE]
        vs["long"] = len(vs["lines"])
        
        wordCount = 0
        for l in vs["lines"]:
            wordCount += chaFile.countWordsInLine(l)
        vs["wordCount"] = wordCount                    
        
        if usingDAD:
            vs["dad"] = vs["lines"][0][ChaFile.TIER_ACTIVITY]
            
            for l in vs["lines"]:
                if l[ChaFile.TIER_ACTIVITY] != vs["dad"]:
                    distintosDAD.append(vs["id"])
                    break
    
    if len(distintosDAD):
        log.log("Warning: %d distintos DAD a lo largo del variation set. Ids: %s" % (len(distintosDAD), str(distintosDAD)) )
