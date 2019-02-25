#!/usr/bin/python3
# This program is used to re-annotate KiCad projects based on hierarchical
# circuit blocks which have already been annotated by KiCad itself, but to
# so in such a way that the components within the hierarchical blocks end
# up having the reference designators used in the original Project Apollo
# design rather than reference designator arbitrarily chosen by KiCad.
# Only 2-level schematics are supported ... i.e., a top-level parent drawing, 
# which has a single layer of child hierarchical-block drawings.  The child
# drawings cannot themselves have child drawings. 

# The reference designators in the original Apollo design take the form of
# the reference designators visibly displayed in the schematic, but prefixed
# by something that uniquely references which instance of the circuit block
# is.  I believe the prefixes are always in the form of simple decimal numbers,
# "1", "2", "3", etc., so that the
# reference designators for the first instance for the circuit block might be
# 1R1, 1R2, 1C1, 1CR1, 1CR2, etc., while for the second instance might be
# 2R1, 2R2, 2C1, 2CR1, 2CR2, etc., an so on.  The exact form of the prefix
# needs to be determined on a case by case basis from the notes on the schematic
# or from the "insulator" drawings associated with the schematic drawing.
# Some modules, such as Block I AGC interface module A19/A39 (drawing 1006534)
# do not seem to have some of these associated materials, but it is not really
# appropriate to run this script in those cases anyway.  (I.e., since the 
# purpose of the script is to match how the components were originally physically
# identified, there's no point in running it when we don't know how the components
# were originally identified.)

# To use this script, the schematics need to be prepared in the following way:
#
#   1.	The reference designators specified in the child drawing are not used.
#	Instead, each component must have a field called "baseRefd" used to
#	visibly display the reference designator.
#   2.  The prefixes for the child reference designators are taken from 
#	"Sheet name" of the hierarchical block in the parent drawing, 
#	stripped of any trailing non-numerical characters.  For example,
#	if the sheet name is 15XT, then the prefix is 15.  Thus the parent
#	drawing must be prepared with the appropriate "Sheet name" fields.

# The script overwrites in-place all of the child schematics it processes.  
# Therefore, it should only be run in folders that have been backed up or 
# committed.  The usage is simply
#
#	blockAnnotater.py <TOPLEVEL.sch

import sys
import re
import os

# First step:  Read the entire parent drawing, and determine (for each hierarchical
# circuit block) the timestamp (which uniquely identifies the child), the sheet name
# which will determine the prefix used), and the filename of the child.  These are
# the only things we actually need the parent for, and we can ignore it thereafter.
# This info will be stored in the "blocks" dictionary, which has a structure like
#	blocks = {
#		 	filename1: {
#					timestamp1: prefix1,
#					timestamp2: prefix2,
#					...
#				   },
#			filename2: ...
#		 }
inSheet = False
timestamp = ""
sheetname = ""
filename = ""
blocks = {}
for line in sys.stdin:
	fields = line.strip().split(" ")
	numFields = len(fields)
	
	if numFields == 1 and fields[0] == "$Sheet":
		inSheet = True
		timestamp = ""
		sheetname = ""
		filename = ""
		continue
	if numFields == 1 and fields[0] == "$EndSheet":
		inSheet = False
		if timestamp != "" and sheetname != "" and filename != "":
			if filename not in blocks:
				blocks[filename] = {}
			blocks[filename][timestamp] = sheetname
		continue
	if not inSheet:
		continue
	
	if numFields == 2 and fields[0] == "U":
		timestamp = fields[1]
		continue
	if numFields == 3 and fields[0] == "F0":
		sheetname = re.sub("\D.*", "", fields[1].strip('"'))
		continue
	if numFields == 3 and fields[0] == "F1":
		filename = fields[1].strip('"')
		continue
#print(blocks)

# Now that we have the blocks dictionary in place, we can process each child
# sheet in turn.
inComponent = False
baseRefd = ""
for filename in blocks:
	# First, read the child schematic in its entirety.
	f = open(filename, "r")
	lines = f.readlines();
	f.close();
	
	# Now, process it, to replace all of the reference designators that
	# were previously annotated.
	for i in range(0, len(lines)):
		fields = lines[i].strip().split()
		numFields = len(fields)
		if numFields == 1 and fields[0] == "$EndComp":
			inComponent = False
			continue
		if numFields == 1 and fields[0] == "$Comp":
			inComponent = True
			baseRefd = ""
			for j in range(i + 1, len(lines)):
				fields2 = lines[j].strip().split()
				numFields2 = len(fields2)
				if numFields2 == 1 and fields2[0] == "$EndComp":
					inComponent = False
					break
				if numFields2 == 11 and fields2[10] == '"baseRefd"':
					baseRefd = fields2[2].strip('"')
					#print(baseRefd)
					break
		if not inComponent:
			continue
		
		if len(fields) != 4 or fields[0] != "AR" or fields[1][:7] != 'Path="/':
			continue
		timestamp = re.sub("/.*", "", fields[1][7:])
		#print(timestamp)
		if timestamp in blocks[filename]:
			refd = blocks[filename][timestamp] + baseRefd
			lines[i] = fields[0] + " " + fields[1] + " " + 'Ref="' + refd + '"  ' + fields[3] + "\n"
			#print("Replacing " + fields[2] + " by " + blocks[filename][timestamp] + baseRefd)
	
	if True:
		# Finally, write out the newly-annotated file.
		os.replace(filename, filename+".block.bak")
		f = open(filename, "w")
		f.writelines(lines);
		f.close();
	