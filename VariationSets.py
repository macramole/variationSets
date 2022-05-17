#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 29 14:24:45 2018

@author: leandro
"""

import os
import sys
from difflib import SequenceMatcher

sys.path.insert(0, '../../CHAFile/')
import ChaFile
from log import Log

CRITERIA_THRESHOLD = "t"
CRITERIA_MOR = "m"

THRESHOLD = 0.55 #solo para criteria_threshold

CATEGORIAS_VERBOS = ["v","ger","part","aux","imp","inf"] #saco el "cop" y "co"
CATEGORIAS_SUSTANTIVO = ["n", "n:gerund"]
CATEGORIAS_ADJETIVO = ["adj"]
CATEGORIAS_SUSTANTIVO_ADJETIVO = CATEGORIAS_SUSTANTIVO + CATEGORIAS_ADJETIVO
CATEGORIAS_TOTALES = CATEGORIAS_VERBOS + CATEGORIAS_SUSTANTIVO_ADJETIVO

usingDAD = True
useSmartVerbs = True

MAX_INTERVENCION_SPEAKER = 1 # cuantas "intervenciones" del mismo hablante al CHI (si != a CHI se rompe)
MAX_INTERVENCION_CHILD = 1 # cuantas intervenciones del CHI
MAX_INTERVENCION_TO_CHILD = 1 # cuantas intervenciones al CHI de otro hablante
MAX_INTERVENCION_OTHER = 3 # cuantas intervenciones de otros hablantes no dirigidas al niño
MAX_TIEMPO = 5000 #en ms (4000 default)

MAX_INTERVENCION_SPEAKER_ADS = 1 # cuantas "intervenciones" del mismo hablante a un adulto que no tiene palabras en común
MAX_INTERVENCION_TO_CHILD_ADS = 0 # cuantas intervenciones del mismo hablante al CHI
MAX_INTERVENCION_TO_OCH_ADS = 0 # cuantas intervenciones del mismo hablante a OCH
# MAX_INTERVENCION_CHILD_ADS = 2 # cuantas intervenciones del CHI
MAX_INTERVENCION_OTHER_ADS = 3 # cuantas intervenciones de otros hablantes CHI OCH o Adult
MAX_TIEMPO_ADS = 5000 #en ms (4000 default)

MAX_INTERVENCION_SPEAKER_OCH = 1 # cuántas "intervenciones" del mismo hablante al OCH (si le habla a un adulto, se rompe el VS)
MAX_INTERVENCION_TO_CHILD_OCH = 0 # cuántas intervenciones del mismo hablante al CHI
MAX_INTERVENCION_TO_OCH_OCH = 1 # cuantas intervenciones de otros hablantes al OCH
MAX_INTERVENCION_OTHER_OCH = 3 # cuantas intervenciones del CHI o ADULT (no son al OCH)
MAX_TIEMPO_OCH = 5000 #en ms (4000 default)

VS_TYPE_CDS = "cds"
VS_TYPE_ADS = "ads"
VS_TYPE_OCH = "och"

log = Log()

def getVariationSetsFromFile( chaFilePath, criteria,
							  resultPath, useDAD = True,
							  smartVerbs = True, useLineNumbers = None,
							  verbose = False, language = None, vsType = VS_TYPE_CDS ):
	"""Search for VariationSets in CHA file

	Args:
		chaFilePath (string): Path to cha file
		criteria (string): Deprecated
		resultPath (string): Path where results will be saved
		useDAD (bool, optional): Use activity type tier. Defaults to True.
		smartVerbs (bool, optional): Use ChaFile's populateVerbs feature. Defaults to True.
		useLineNumbers (list, optional): Only use provided line numbers (not the whole file). Defaults to None.
		verbose (bool, optional): Defaults to False.
		language (string, optional): Use ChaFile's LANGUAGE_ constants. Defaults to None.
		ADS (bool, optional): Search for VS in ADS. Defaults to False.
	"""

	assert language != None, "language not found"

	global usingDAD, useSmartVerbs

	useSmartVerbs = smartVerbs

	usingDAD = useDAD

	ChaFile.log = log

	chaFile = ChaFile.ChaFile( chaFilePath,
							   verbose = verbose, language = language)

	if usingDAD:
		chaFile.fixDAD()
	if useSmartVerbs:
		chaFile.populateVerbs()

	# Preparo el dir donde voy a arrojar mis resultados
	resultPath = f"{resultPath}/variation_sets/{vsType.upper()}/{chaFile.getLanguage()}/{chaFile.filename}/"

	if not os.path.isdir( resultPath ):
		os.makedirs( resultPath )
	#####

	tmpLines = chaFile.getLines()
	lines = []
	if useLineNumbers != None:
		for l in tmpLines:
			if l[ChaFile.LINE_NUMBER] in useLineNumbers:
				lines.append(l)
	else:
		lines = tmpLines

	log.log(f"Procesando VS de {len(lines)} lineas...")
	if vsType == VS_TYPE_CDS:
		allVariationSets = getVariationSetsFromLines(lines, criteria)
	elif vsType == VS_TYPE_ADS:
		allVariationSets = getVariationSetsFromLinesADS(lines, criteria)
	elif vsType == VS_TYPE_OCH:
		allVariationSets = getVariationSetsFromLinesOCH(lines, criteria)

#    return inspectVS(allVariationSets)
	inspectVSAsUnit(allVariationSets, chaFile)
	saveResults(allVariationSets, resultPath)
	return allVariationSets

def getVariationSetsFromLines(lines, criteria):
	"""Main function for looking for VS

	Args:
		lines (list): Lines from ChaFile
		criteria (string): Deprecated

	Returns:
		list: VariationSets for provided lines
	"""
	variationSets = []

	linesInVS = []
	# volvé a la última línea dirigida al niño que no era VS
	skippedToChildLineIndex = None
	lineCurrentIndex = 0
	currentVariationSet = []
	currentVariationSetIntervining = []

	qtyIntervencionSpeaker = 0
	qtyIntervencionChild = 0
	qtyIntervencionOther = 0
	qtyIntervencionToChild = 0

	def endVariationSet():
		nonlocal lineCurrentIndex, currentVariationSet, variationSets, skippedToChildLineIndex
		nonlocal currentVariationSetIntervining

		if len(currentVariationSet) >= 2:
			objVariationSet = {
				"id" : constructId(currentVariationSet),
				"lines" : currentVariationSet,
				"intervining" : currentVariationSetIntervining
			}
			variationSets.append(objVariationSet)

		currentVariationSet = []
		currentVariationSetIntervining = []

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

		if not sameSpeaker:
			#es el niño?
			if lineCurrent[ChaFile.LINE_SPEAKER] == ChaFile.SPEAKER_TARGET_CHILD:
				qtyIntervencionChild += 1
				currentVariationSetIntervining += [ lineCurrent ]

				if qtyIntervencionChild > MAX_INTERVENCION_CHILD:
					endVariationSet()
			else:
				#esta dirigida al niño?
				if lineCurrent[ChaFile.LINE_ADDRESSEE] == ChaFile.SPEAKER_TARGET_CHILD:
					qtyIntervencionToChild += 1
					currentVariationSetIntervining += [ lineCurrent ]

					if skippedToChildLineIndex is None:
						skippedToChildLineIndex = lineCurrentIndex
					if qtyIntervencionToChild > MAX_INTERVENCION_TO_CHILD:
						endVariationSet()

				else:
					qtyIntervencionOther += 1
					currentVariationSetIntervining += [ lineCurrent ]

					if qtyIntervencionOther > MAX_INTERVENCION_OTHER:
						endVariationSet()
		else:
			if lineCurrent[ChaFile.LINE_ADDRESSEE] == ChaFile.SPEAKER_TARGET_CHILD:
				palabrasCompartidas = getPalabrasCompartidas(lineCurrent, lineToCompare)

				timeStartCurrent = timeEndCompare = None

				if ChaFile.LINE_BULLET in lineCurrent:
					timeStartCurrent = lineCurrent[ChaFile.LINE_BULLET][0]
					timeEndCompare = lineToCompare[ChaFile.LINE_BULLET][1]

				timeOk = (timeStartCurrent is None or timeStartCurrent - timeEndCompare <= MAX_TIEMPO)

				if len( palabrasCompartidas ) > 0 and timeOk :
					currentVariationSet += [ lineCurrent ]
					linesInVS.append(lineCurrent)

					# se resetean porque las intervining son entre dos emisiones
					qtyIntervencionSpeaker = 0
					qtyIntervencionChild = 0
					qtyIntervencionOther = 0
					qtyIntervencionToChild = 0
				else:
					if not timeOk:
						endVariationSet()
					else :
						if skippedToChildLineIndex is None:
							skippedToChildLineIndex = lineCurrentIndex

						qtyIntervencionSpeaker += 1
						currentVariationSetIntervining += [ lineCurrent ]
						if qtyIntervencionSpeaker > MAX_INTERVENCION_SPEAKER:
							endVariationSet()

			else:
				endVariationSet()

		if lineCurrentIndex == len(lines) - 1:
			endVariationSet()

		lineCurrentIndex += 1



	return variationSets

def getVariationSetsFromLinesADS(lines, criteria):
	"""Main function for looking for VS, this is for ADS

	Args:
		lines (list): Lines from ChaFile
		criteria (string): Deprecated

	Returns:
		list: VariationSets for provided lines
	"""

	variationSets = []

	linesInVS = []
	
	#volvé a la última línea que no era VS
	skippedToAdultsLineIndex = None
	lineCurrentIndex = 0
	currentVariationSet = []
	currentVariationSetIntervining = []

	#Intervenciones del mismo hablante (no dirigidas al niñe)
	qtyIntervencionSpeaker = 0
	#Intervenciones del mismo hablante (dirigidas al niñe)
	qtyIntervencionToChild = 0
	#Intervenciones del mismo hablante (dirigidas a otro niñe)
	qtyIntervencionToOtherChild = 0

	#Intervenciones del CHI (no se está usando, todo va a other)
	qtyIntervencionChild = 0
	#Intervenciones de otro hablante
	qtyIntervencionOther = 0

	def endVariationSet():
		nonlocal lineCurrentIndex, currentVariationSet, variationSets, skippedToAdultsLineIndex
		nonlocal currentVariationSetIntervining

		if len(currentVariationSet) >= 2:
			objVariationSet = {
				"id" : constructId(currentVariationSet),
				"lines" : currentVariationSet,
				"intervining" : currentVariationSetIntervining
			}
			variationSets.append(objVariationSet)

		currentVariationSet = []
		currentVariationSetIntervining = []

		if skippedToAdultsLineIndex != None:
			lineCurrentIndex = skippedToAdultsLineIndex - 1 #-1 por el +1 que hay al final
			skippedToAdultsLineIndex = None

	while lineCurrentIndex < len(lines):
		lineCurrent = lines[ lineCurrentIndex ]

		if len(currentVariationSet) == 0:
			if lineCurrent[ChaFile.LINE_ADDRESSEE] != ChaFile.SPEAKER_TARGET_CHILD:
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

		if not sameSpeaker:
			qtyIntervencionOther += 1
			currentVariationSetIntervining += [ lineCurrent ]

			if qtyIntervencionOther > MAX_INTERVENCION_OTHER_ADS:
				endVariationSet()
		else:
			if lineCurrent[ChaFile.LINE_ADDRESSEE] not in [ChaFile.SPEAKER_TARGET_CHILD, ChaFile.SPEAKER_OTHER_CHILD]:
				palabrasCompartidas = getPalabrasCompartidas(lineCurrent, lineToCompare)

				timeStartCurrent = timeEndCompare = None

				if ChaFile.LINE_BULLET in lineCurrent:
					timeStartCurrent = lineCurrent[ChaFile.LINE_BULLET][0]
					timeEndCompare = lineToCompare[ChaFile.LINE_BULLET][1]

				timeOk = (timeStartCurrent is None or timeStartCurrent - timeEndCompare <= MAX_TIEMPO_ADS)

				if len( palabrasCompartidas ) > 0 and timeOk :
					currentVariationSet += [ lineCurrent ]
					linesInVS.append(lineCurrent)

					# se resetean porque las intervining son entre dos emisiones
					qtyIntervencionSpeaker = 0
					qtyIntervencionChild = 0
					qtyIntervencionOther = 0
					qtyIntervencionToChild = 0
				else:
					if not timeOk:
						endVariationSet()
					else :
						if skippedToAdultsLineIndex is None:
							skippedToAdultsLineIndex = lineCurrentIndex

						qtyIntervencionSpeaker += 1
						currentVariationSetIntervining += [ lineCurrent ]
						if qtyIntervencionSpeaker > MAX_INTERVENCION_SPEAKER_ADS:
							endVariationSet()

			else:
				if lineCurrent[ChaFile.LINE_ADDRESSEE] == ChaFile.SPEAKER_TARGET_CHILD:
					qtyIntervencionToChild += 1
					currentVariationSetIntervining += [ lineCurrent ]

					if qtyIntervencionToChild > MAX_INTERVENCION_TO_CHILD_ADS:
						endVariationSet()
				else:
					qtyIntervencionToOtherChild += 1
					currentVariationSetIntervining += [ lineCurrent ]
					
					if qtyIntervencionToOtherChild > MAX_INTERVENCION_TO_OCH_ADS:
						endVariationSet()

		if lineCurrentIndex == len(lines) - 1:
			endVariationSet()

		lineCurrentIndex += 1

	return variationSets

def getVariationSetsFromLinesOCH(lines, criteria):
	"""Main function for looking for VS, this is for OCH

	Args:
		lines (list): Lines from ChaFile
		criteria (string): Deprecated

	Returns:
		list: VariationSets for provided lines
	"""

	variationSets = []

	linesInVS = []
	
	#volvé a la última línea que no era VS
	skippedToOCHLineIndex = None
	lineCurrentIndex = 0
	currentVariationSet = []
	currentVariationSetIntervining = []

	#Intervenciones del mismo hablante (dirigidas al OCH)
	qtyIntervencionSpeaker = 0
	#Intervenciones de otro hablante (dirigidas al OCH)
	qtyIntervencionToOCH = 0
	#Intervenciones de otro hablante
	qtyIntervencionOther = 0

	def endVariationSet():
		nonlocal lineCurrentIndex, currentVariationSet, variationSets, skippedToOCHLineIndex
		nonlocal currentVariationSetIntervining

		if len(currentVariationSet) >= 2:
			objVariationSet = {
				"id" : constructId(currentVariationSet),
				"lines" : currentVariationSet,
				"intervining" : currentVariationSetIntervining
			}
			variationSets.append(objVariationSet)

		currentVariationSet = []
		currentVariationSetIntervining = []

		if skippedToOCHLineIndex != None:
			lineCurrentIndex = skippedToOCHLineIndex - 1 #-1 por el +1 que hay al final
			skippedToAdultsLineIndex = None

	while lineCurrentIndex < len(lines):
		lineCurrent = lines[ lineCurrentIndex ]

		if len(currentVariationSet) == 0:
			if lineCurrent[ChaFile.LINE_ADDRESSEE] != ChaFile.SPEAKER_TARGET_CHILD:
				if not lineCurrent in linesInVS:
					currentVariationSet = [ lineCurrent ]
					linesInVS.append(lineCurrent)

					qtyIntervencionSpeaker = 0
					qtyIntervencionOther = 0
					qtyIntervencionToOCH = 0

			lineCurrentIndex += 1
			continue

		lineToCompare = currentVariationSet[-1]
		sameSpeaker = ( lineCurrent[ChaFile.LINE_SPEAKER] == lineToCompare[ChaFile.LINE_SPEAKER] )

		if not sameSpeaker:
			if lineCurrent[ChaFile.LINE_ADDRESSEE] == ChaFile.SPEAKER_OTHER_CHILD:
				qtyIntervencionToOCH += 1
				currentVariationSetIntervining += [ lineCurrent ]
				
				if qtyIntervencionToOCH > MAX_INTERVENCION_TO_OCH_OCH:
					endVariationSet()
			else :
				qtyIntervencionOther += 1
				currentVariationSetIntervining += [ lineCurrent ]

				if qtyIntervencionOther > MAX_INTERVENCION_OTHER_OCH:
					endVariationSet()
		else:
			if lineCurrent[ChaFile.LINE_ADDRESSEE] == ChaFile.SPEAKER_OTHER_CHILD:
				palabrasCompartidas = getPalabrasCompartidas(lineCurrent, lineToCompare)

				timeStartCurrent = timeEndCompare = None

				if ChaFile.LINE_BULLET in lineCurrent:
					timeStartCurrent = lineCurrent[ChaFile.LINE_BULLET][0]
					timeEndCompare = lineToCompare[ChaFile.LINE_BULLET][1]

				timeOk = (timeStartCurrent is None or timeStartCurrent - timeEndCompare <= MAX_TIEMPO_OCH)

				if len( palabrasCompartidas ) > 0 and timeOk :
					currentVariationSet += [ lineCurrent ]
					linesInVS.append(lineCurrent)

					# se resetean porque las intervining son entre dos emisiones
					qtyIntervencionSpeaker = 0
					qtyIntervencionOther = 0
					qtyIntervencionToOCH = 0
				else:
					if not timeOk:
						endVariationSet()
					else :
						if skippedToOCHLineIndex is None:
							skippedToOCHLineIndex = lineCurrentIndex

						qtyIntervencionSpeaker += 1
						currentVariationSetIntervining += [ lineCurrent ]
						if qtyIntervencionSpeaker > MAX_INTERVENCION_SPEAKER_OCH:
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

			lines = vs["lines"] + vs["intervining"]
			lines.sort( key=lambda x : x[ChaFile.LINE_NUMBER] )

			for line in lines:
				lineNum = line[ ChaFile.LINE_NUMBER ]
				speaker = line[ ChaFile.LINE_SPEAKER ]
				utt = line[ ChaFile.LINE_UTTERANCE ]
				addressee = line[ ChaFile.LINE_ADDRESSEE ]
				toChild = f"(+ {addressee})" if addressee != ChaFile.SPEAKER_ADULT else ""
				dad = f"[{line[ChaFile.TIER_ACTIVITY]}]" if usingDAD else ""
				intervining = "[INTER]" if line in vs["intervining"] else ""

				strToWrite = f"[{lineNum}] *{speaker}	{utt} {toChild} {dad} {intervining}"
				newFile.write(strToWrite + "\n")

			newFile.write("\n")

			for i in range( 0, len(vs["lines"])-1 ):
				strPalabras = str(vs["palabrasCompartidas"][i])

				newFile.write("[%s]-[%s] %s\n" %
							  (vs["lines"][i][ChaFile.LINE_NUMBER],
							   vs["lines"][i+1][ChaFile.LINE_NUMBER],
							   strPalabras ))

			newFile.write("\n")

			newFile.write(
				f"Repite noun: {vs['repiteNoun']}\n"
				f"Repite verb: {vs['repiteVerb']}\n"
				f"Repite adjective: {vs['repiteAdj']}\n"
			)


			newFile.write("\n\n")

def inspectVSAsUnit(vss, chaFile):
	distintosDAD = []

	for vs in vss:
		vs["speaker"] = vs["lines"][0][ChaFile.LINE_SPEAKER]
		vs["addressee"] = vs["lines"][0][ChaFile.LINE_ADDRESSEE]
		vs["long"] = len(vs["lines"])

		wordCount = 0
		nounCount = 0
		verbCount = 0
		adjCount = 0
		for l in vs["lines"]:
			wordCount += chaFile.countWordsInLine(l)
			nounCount += len(chaFile.getNounsInLine(l))
			verbCount += len(chaFile.getVerbsInLine(l))
			adjCount += len(chaFile.getAdjectivesInLine(l))
		vs["wordCount"] = wordCount
		vs["nounCount"] = nounCount
		vs["verbCount"] = verbCount
		vs["adjCount"] = adjCount

		vs["palabrasCompartidas"] = []

		vs["repeticiones"] = {
			"verbo" : [],
			"adjetivo" : [],
			"sustantivo" : [],
		}

		#repetidos
		for i in range( len(vs["lines"])-1 ):
			palabrasCompartidas = getPalabrasCompartidas( vs["lines"][i], vs["lines"][i+1] )

			# esto es porque devuelve int o obj dependiendo si smartVerbs o no
			if type(palabrasCompartidas[0]) == int:
				palabrasCompartidas = [ vs["lines"][i][ChaFile.TIER_MOR][x] for x in palabrasCompartidas ]

			vs["palabrasCompartidas"].append(palabrasCompartidas)

			for p in palabrasCompartidas:
				if p[ChaFile.MOR_UNIT_CATEGORIA] in CATEGORIAS_VERBOS:
					if not p[ChaFile.MOR_UNIT_LEXEMA] in vs["repeticiones"]["verbo"]:
						vs["repeticiones"]["verbo"].append( p[ChaFile.MOR_UNIT_LEXEMA] )
				
				if p[ChaFile.MOR_UNIT_CATEGORIA] in CATEGORIAS_SUSTANTIVO:
					if not p[ChaFile.MOR_UNIT_LEXEMA] in vs["repeticiones"]["sustantivo"]:
						vs["repeticiones"]["sustantivo"].append( p[ChaFile.MOR_UNIT_LEXEMA] )
				
				if p[ChaFile.MOR_UNIT_CATEGORIA] in CATEGORIAS_ADJETIVO:
					if not p[ChaFile.MOR_UNIT_LEXEMA] in vs["repeticiones"]["adjetivo"]:
						vs["repeticiones"]["adjetivo"].append( p[ChaFile.MOR_UNIT_LEXEMA] )
		
		vs["repiteNoun"] = len( vs["repeticiones"]["sustantivo"] )
		vs["repiteAdj"] = len( vs["repeticiones"]["adjetivo"] )
		vs["repiteVerb"] = len( vs["repeticiones"]["verbo"] )

		del vs["repeticiones"]

		if usingDAD:
			vs["dad"] = vs["lines"][0][ChaFile.TIER_ACTIVITY]

			for l in vs["lines"]:
				if l[ChaFile.TIER_ACTIVITY] != vs["dad"]:
					distintosDAD.append(vs["id"])
					break

	if len(distintosDAD):
		log.log("Warning: %d distintos DAD a lo largo del variation set. Ids: %s" % (len(distintosDAD), str(distintosDAD)) )


#getVariationSetsFromFile( "/media/leandro/stuff/Code/ciipme/aclew/bajada-06032019/eng/todos/9801.elan.cha", CRITERIA_MOR, "./results.test", False )
#getVariationSetsFromFile( "/media/leandro/stuff/Code/ciipme/aclew/bajada-06032019/spa/todos/9909.elan.cha", CRITERIA_MOR, "./results.test", False )
