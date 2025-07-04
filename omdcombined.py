#!@Python3_EXECUTABLE@
"""OMDCombined

Opens two omd files, one with a solute structure and one with a
solvent structure. Viable with solvents containing both rigid and
non-rigid atoms, with the stipulation that no atoms overlap.
Produces a new combined omd file.  The output omd file must be 
edited to run properly in OpenMD.  Note that the two boxes must 
have identical box geometries (specified on the Hmat line).

Usage: omdCombined

Options:
  -h,  --help              show this help
  -u,  --solute=...        use specified OpenMD (.omd) file as the solute
  -v,  --solvent=...       use specified OpenMD (.omd) file as the solvent
  -o,  --output-file=...   use specified output (.omd) file


Example:
   omdCombined -u solute.omd -v solvent.omd -o combined.omd

"""

__author__ = "Sydney Shavalier (sshavali@nd.edu)"
__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2020 by the University of Notre Dame"
__license__ = "OpenMD"

import sys
import getopt
import string
import math
import random

_haveMDFileName1 = 0
_haveMDFileName2 = 0
_haveOutputFileName = 0

metaData1 = []
frameData1 = []
positions1 = []
velocities1 = []
quaternions1 = []
angVels1 = []
indices1 = []
Hmat1 = []
BoxInv1 = []
pvqj1 = []

metaData2 = []
frameData2 = []
positions2 = []
velocities2 = []
quaternions2 = []
angVels2 = []
indices2 = []
Hmat2 = []
BoxInv2 = []
pvqj2 = []
componentLines = []
ensembleLines = []

def usage():
    print(__doc__)

def readFile1(mdFileName):
    mdFile = open(mdFileName, 'r')        
    # Find OpenMD version info first
    line = mdFile.readline()
    while True:
        if '<OpenMD version=' in line or '<OOPSE version=' in line:
            OpenMDversion = line
            break
        line = mdFile.readline()

    mdFile.seek(0)
    

    line = mdFile.readline()

    print("reading solute MetaData")
    while True:
        if '<MetaData>' in line:
            while 2:
                line = mdFile.readline()
                if 'molecule' in line:
                    while not 'component' in line:
                        componentLines.append(line)
                        line = mdFile.readline()
                    componentLines.append("\n")
                if 'component' in line:
                    while not '}' in line:
                        componentLines.append(line)
                        line = mdFile.readline()
                    componentLines.append("}\n\n")
                if 'ensemble' in line:
                    while not '</MetaData>' in line:
                        ensembleLines.append(line)
                        line = mdFile.readline()
                metaData1.append(line)

                if '</MetaData>' in line:
                    metaData1.append(line)
                    break
            break
        line = mdFile.readline()

    mdFile.seek(0)
    
    print("reading solute Snapshot")
    line = mdFile.readline()
    while True:
        if '<Snapshot>' in line:
            line = mdFile.readline()
            while True:
                print("reading solute FrameData")
                if '<FrameData>' in line:
                    while 2:
                        frameData1.append(line)
                        if 'Hmat:' in line:
                            L = line.split()
                            Hxx = float(L[2].strip(','))
                            Hxy = float(L[3].strip(','))
                            Hxz = float(L[4].strip(','))
                            Hyx = float(L[7].strip(','))
                            Hyy = float(L[8].strip(','))
                            Hyz = float(L[9].strip(','))
                            Hzx = float(L[12].strip(','))
                            Hzy = float(L[13].strip(','))
                            Hzz = float(L[14].strip(','))
                            Hmat1.append([Hxx, Hxy, Hxz])
                            Hmat1.append([Hyx, Hyy, Hyz])
                            Hmat1.append([Hzx, Hzy, Hzz])
                            BoxInv1.append(1.0/Hxx)
                            BoxInv1.append(1.0/Hyy)
                            BoxInv1.append(1.0/Hzz)
                        line = mdFile.readline()
                        if '</FrameData>' in line:
                            frameData1.append(line)
                            break
                    break

            line = mdFile.readline()
            while True:
                if '<StuntDoubles>' in line:
                    line = mdFile.readline()
                    while 2:
                        L = line.split()
                        myIndex = int(L[0])
                        indices1.append(myIndex)
                        pvqj1.append(L[1])
                        x = float(L[2])
                        y = float(L[3])
                        z = float(L[4])
                        positions1.append(wrapVector([x, y, z])) #wraps positions back into periodic box
                        vx = float(L[5])
                        vy = float(L[6])
                        vz = float(L[7])
                        velocities1.append([vx, vy, vz])
                        if 'pvqj' in L[1]:
                            qw = float(L[8])
                            qx = float(L[9])
                            qy = float(L[10])
                            qz = float(L[11])
                            quaternions1.append([qw, qx, qy, qz])
                            jx = float(L[12])
                            jy = float(L[13])
                            jz = float(L[14])
                            angVels1.append([jx, jy, jz])
                        else:
                            quaternions1.append([0.0, 0.0, 0.0, 0.0])
                            angVels1.append([0.0, 0.0, 0.0])

                        line = mdFile.readline()
                        if '</StuntDoubles>' in line:
                            break
                    break
        line = mdFile.readline()
        if not line: break
    
    mdFile.close()

def readFile2(mdFileName):
    mdFile = open(mdFileName, 'r')        
    # Find OpenMD version info first
    line = mdFile.readline()
    while True:
        if '<OpenMD version=' in line or '<OOPSE version=':
            OpenMDversion = line
            break
        line = mdFile.readline()

    mdFile.seek(0)
    
    line = mdFile.readline()

    print("reading solvent MetaData")
    while True:
        if '<MetaData>' in line:
            while 2:
                line = mdFile.readline()
                if 'molecule' in line:
                    while not 'component' in line:
                        componentLines.append(line)
                        line = mdFile.readline()
                    componentLines.append("\n")
                if 'component' in line:
                    while not '}' in line:
                        componentLines.append(line)
                        line = mdFile.readline()
                    componentLines.append("}\n\n")
                metaData2.append(line)
                if '</MetaData>' in line:
                    metaData2.append(line)
                    break
            break
        line = mdFile.readline()

    mdFile.seek(0)
    
    print("reading solvent Snapshot")
    line = mdFile.readline()
    while True:
        if '<Snapshot>' in line:
            line = mdFile.readline()
            while True:
                print("reading solvent FrameData")
                if '<FrameData>' in line:
                    while 2:
                        frameData2.append(line)
                        if 'Hmat:' in line:
                            L = line.split()
                            Hxx = float(L[2].strip(','))
                            Hxy = float(L[3].strip(','))
                            Hxz = float(L[4].strip(','))
                            Hyx = float(L[7].strip(','))
                            Hyy = float(L[8].strip(','))
                            Hyz = float(L[9].strip(','))
                            Hzx = float(L[12].strip(','))
                            Hzy = float(L[13].strip(','))
                            Hzz = float(L[14].strip(','))
                            Hmat2.append([Hxx, Hxy, Hxz])
                            Hmat2.append([Hyx, Hyy, Hyz])
                            Hmat2.append([Hzx, Hzy, Hzz])
                            BoxInv2.append(1.0/Hxx)
                            BoxInv2.append(1.0/Hyy)
                            BoxInv2.append(1.0/Hzz)
                        line = mdFile.readline()
                        if '</FrameData>' in line:
                            frameData2.append(line)
                            break
                    break

            line = mdFile.readline()
            while True:
                if '<StuntDoubles>' in line:
                    line = mdFile.readline()
                    while 2:
                        L = line.split()
                        myIndex = int(L[0])
                        indices2.append(myIndex)
                        pvqj2.append(L[1])
                        x = float(L[2])
                        y = float(L[3])
                        z = float(L[4])
                        positions2.append(wrapVector([x, y, z])) #wraps positions back into periodic box
                        vx = float(L[5])
                        vy = float(L[6])
                        vz = float(L[7])
                        velocities2.append([vx, vy, vz])
                        if 'pvqj' in L[1]:
                            qw = float(L[8])
                            qx = float(L[9])
                            qy = float(L[10])
                            qz = float(L[11])
                            quaternions2.append([qw, qx, qy, qz])
                            jx = float(L[12])
                            jy = float(L[13])
                            jz = float(L[14])
                            angVels2.append([jx, jy, jz])
                        else:
                            quaternions2.append([0.0, 0.0, 0.0, 0.0])
                            angVels1.append([0.0, 0.0, 0.0])

                        line = mdFile.readline()
                        if '</StuntDoubles>' in line:
                            break
                    break
        line = mdFile.readline()
        if not line: break

    mdFile.close()

def writeFile(outputFileName):
    outputFile = open(outputFileName, 'w')

    outputFile.write("<OpenMD version=1>\n")
    outputFile.write("   <MetaData>\n")
    for componentLine in componentLines: 
        outputFile.write(componentLine)
    for ensembleLine in ensembleLines:
        outputFile.write(ensembleLine)
    outputFile.write("\n")
    outputFile.write("    </MetaData>\n")
    outputFile.write("  <Snapshot>\n")
    for frameline in frameData1:
        outputFile.write(frameline)
    outputFile.write("    <StuntDoubles>\n")


    newIndex = 0
    for i in range(len(indices1)):
        if (pvqj1[i] == 'pv'):
            outputFile.write("%10d %7s %18.10g %18.10g %18.10g %14e %13e %13e\n" % (newIndex, pvqj1[i], positions1[i][0], positions1[i][1], positions1[i][2], velocities1[i][0], velocities1[i][1], velocities1[i][2]))
        elif(pvqj1[i] == 'pvqj'):
            outputFile.write("%10d %7s %18.10g %18.10g %18.10g %13e %13e %13e %13e %13e %13e %13e %13e %13e %13e\n" % (newIndex, pvqj1[i], positions1[i][0], positions1[i][1], positions1[i][2], velocities1[i][0], velocities1[i][1], velocities1[i][2], quaternions1[i][0], quaternions1[i][1], quaternions1[i][2], quaternions1[i][3], angVels1[i][0], angVels1[i][1], angVels1[i][2]))

        newIndex+=1

    newIndexAlt = newIndex
    for j in range(len(indices2)):
        if (pvqj2[j] == 'pv'):
            outputFile.write("%10d %7s %18.10g %18.10g %18.10g %14e %13e %13e\n" % (newIndexAlt, pvqj2[j], positions2[j][0], positions2[j][1], positions2[j][2], velocities2[j][0], velocities2[j][1], velocities2[j][2]))
        elif(pvqj2[j] == 'pvqj'):
            outputFile.write("%10d %7s %18.10g %18.10g %18.10g %13e %13e %13e %13e %13e %13e %13e %13e %13e %13e\n" % (newIndexAlt, pvqj2[j], positions2[j][0], positions2[j][1], positions2[j][2], velocities2[j][0], velocities2[j][1], velocities2[j][2], quaternions2[j][0], quaternions2[j][1], quaternions2[j][2], quaternions2[j][3], angVels2[j][0], angVels2[j][1], angVels2[j][2]))
        
        newIndexAlt+=1

    outputFile.write("    </StuntDoubles>\n")
    outputFile.write("  </Snapshot>\n")
    outputFile.write("</OpenMD>\n")
    outputFile.close()


def checkBoxes():
    boxTolerance = 1.0e-3
    maxDiff = 0.0
    for i in range(3):
        for j in range(3):
            diff = math.fabs( Hmat1[i][j] - Hmat2[i][j])
            if (diff > maxDiff):
               maxDiff = diff
    if (maxDiff > boxTolerance):
       print("The solute and solvent boxes have different geometries:")
       print("                     Solute           |                   Solvent")
       print(" -------------------------------------|------------------------------------")
       for i in range(3):
           print(( "|  %10.4g %10.4g %10.4g   |  %10.4g %10.4g %10.4g  |" % (Hmat1[i][0], Hmat1[i][1], Hmat1[i][2], Hmat2[i][0], Hmat2[i][1], Hmat2[i][2])))

       print(" -------------------------------------|------------------------------------")
       sys.exit()

def checkOverlap(sd1_index,sd2_index): #checks to see if solute and solvent atoms overlap (within 1 Angstrom of each other)
    overlapTolerance = 1.0
    diff = 0.0
    for i in range(3):
        diff += (math.fabs(positions1[sd1_index][i]-positions2[sd2_index][i]))**2
    diff = math.sqrt(diff)
    if (diff < overlapTolerance):
        print("Warning: Solute and solvent atoms overlap! No output file was created.")
        sys.exit()

    
def roundMe(x):
    if (x >= 0.0):
        return math.floor(x + 0.5)
    else:
        return math.ceil(x - 0.5)

def frange(start,stop,step=1.0):
    while start < stop:
        yield start
        start += step


def wrapVector(myVect):
    scaled = [0.0, 0.0, 0.0]
    for i in range(3):
        scaled[i] = myVect[i] * BoxInv1[i]
        scaled[i] = scaled[i] - roundMe(scaled[i])
        myVect[i] = scaled[i] * Hmat1[i][i]
    return myVect

    
def main(argv):                         
    try:                                
        opts, args = getopt.getopt(argv, "hu:v:o:", ["help", "solute=", "solvent=",  "output-file="]) 
    except getopt.GetoptError:           
        usage()                          
        sys.exit(2)                     
    for opt, arg in opts:                
        if opt in ("-h", "--help"):      
            usage()                     
            sys.exit()                  
        elif opt in ("-u", "--solute"): 
            mdFileName1 = arg
            global _haveMDFileName1
            _haveMDFileName1 = 1
        elif opt in ("-v", "--solvent"): 
            mdFileName2 = arg
            global _haveMDFileName2
            _haveMDFileName2 = 1
        elif opt in ("-o", "--output-file"): 
            outputFileName = arg
            global _haveOutputFileName
            _haveOutputFileName = 1

    if (_haveMDFileName1 != 1):
        usage() 
        print("No OpenMD (omd) file was specified for the solute")
        sys.exit()

    if (_haveMDFileName2 != 1):
        usage() 
        print("No OpenMD (omd) file was specified for the solvent")
        sys.exit()

    if (_haveOutputFileName != 1):
        usage()
        print("No output file was specified")
        sys.exit()

    readFile1(mdFileName1)
    readFile2(mdFileName2)
    checkBoxes()
    for sd1 in range(len(indices1)):
        for sd2 in range(len(indices2)):
            checkOverlap(sd1,sd2)
    writeFile(outputFileName)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        usage()
        sys.exit()
    main(sys.argv[1:])