/*
 * Copyright (c) 2004-present, The University of Notre Dame. All rights
 * reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived from
 *    this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 *
 * SUPPORT OPEN SCIENCE!  If you use OpenMD or its source code in your
 * research, please cite the appropriate papers when you publish your
 * work.  Good starting points are:
 *
 * [1] Meineke, et al., J. Comp. Chem. 26, 252-271 (2005).
 * [2] Fennell & Gezelter, J. Chem. Phys. 124, 234104 (2006).
 * [3] Sun, Lin & Gezelter, J. Chem. Phys. 128, 234107 (2008).
 * [4] Vardeman, Stocker & Gezelter, J. Chem. Theory Comput. 7, 834 (2011).
 * [5] Kuang & Gezelter, Mol. Phys., 110, 691-701 (2012).
 * [6] Lamichhane, Gezelter & Newman, J. Chem. Phys. 141, 134109 (2014).
 * [7] Lamichhane, Newman & Gezelter, J. Chem. Phys. 141, 134110 (2014).
 * [8] Bhattarai, Newman & Gezelter, Phys. Rev. B 99, 094106 (2019).
 */

#include "HBondRvol.hpp"
#include <vector>
#include <algorithm>
#include <fstream>

#include "io/DumpReader.hpp"
#include "primitives/Molecule.hpp"
#include "utils/Constants.hpp"
#include "utils/simError.h"

namespace OpenMD {

  HBondRvol::HBondRvol(SimInfo* info, const std::string& filename,
                 const std::string& sele1, const std::string& sele2,
                 const std::string& sele3, double rCut, RealType len,
                 double thetaCut, int nrbins) :
      StaticAnalyser(info, filename, nrbins),
      selectionScript1_(sele1), seleMan1_(info), evaluator1_(info),
      selectionScript2_(sele2), seleMan2_(info), evaluator2_(info),
      selectionScript3_(sele3), seleMan3_(info), evaluator3_(info),
      len_(len), nBins_(nrbins) {


    ff_ = info_->getForceField();


    evaluator1_.loadScriptString(sele1);
    if (!evaluator1_.isDynamic()) {
      seleMan1_.setSelectionSet(evaluator1_.evaluate());
    }
    evaluator2_.loadScriptString(sele2);
    if (!evaluator2_.isDynamic()) {
      seleMan2_.setSelectionSet(evaluator2_.evaluate());
    }
    evaluator3_.loadScriptString(sele3);
    if (!evaluator3_.isDynamic()) {
      seleMan3_.setSelectionSet(evaluator3_.evaluate());
    }


    // Set up cutoff values:

    rCut_     = rCut;
    thetaCut_ = thetaCut;
    deltaR_   = len_ / nBins_;
    nBins_    = nrbins;
    
    // fixed number of bins

    nHBonds_.resize(nBins_);
    nDonor_.resize(nBins_);
    nAcceptor_.resize(nBins_);
    sliceQ_.resize(nBins_);
    binvol_.resize(nBins_);
    sliceCount_.resize(nBins_);
    std::fill(sliceQ_.begin(), sliceQ_.end(), 0.0);
    std::fill(sliceCount_.begin(), sliceCount_.end(), 0);

    setOutputName(getPrefix(filename) + ".hbondrvol");
  }

  void HBondRvol::process() {
    Molecule* mol1;
    Molecule* mol2;
    Molecule* mol3;
    Molecule::HBondDonor* hbd1;
    Molecule::HBondDonor* hbd2;
    std::vector<Molecule::HBondDonor*>::iterator hbdi;
    std::vector<Molecule::HBondDonor*>::iterator hbdj;
    std::vector<Atom*>::iterator hbai;
    std::vector<Atom*>::iterator hbaj;

    RealType r;

    Atom* hba1;
    Atom* hba2;
    Vector3d dPos;
    Vector3d aPos;
    Vector3d hPos;
    Vector3d DH;
    Vector3d DA;
    RealType DAdist, DHdist, theta, ctheta;
    int ii, jj;
    int nHB, nA, nD;

    DumpReader reader(info_, dumpFilename_);
    int nFrames   = reader.getNFrames();
    frameCounter_ = 0;

    for (int istep = 0; istep < nFrames; istep += step_) {
      reader.readFrame(istep);
      currentSnapshot_ = info_->getSnapshotManager()->getCurrentSnapshot();

      if (evaluator1_.isDynamic()) {
        seleMan1_.setSelectionSet(evaluator1_.evaluate());
      }

      if (evaluator2_.isDynamic()) {
        seleMan2_.setSelectionSet(evaluator2_.evaluate());
      }

      if (evaluator3_.isDynamic()) {
        seleMan3_.setSelectionSet(evaluator3_.evaluate());
      }

      for (mol1 = seleMan1_.beginSelectedMolecule(ii); mol1 != NULL;
           mol1 = seleMan1_.nextSelectedMolecule(ii)) {
        // We're collecting statistics on the molecules in selection 1:
        nHB           = 0;
        nA            = 0;
        nD            = 0;
        Vector3d mPos = mol1->getCom();

        for (mol2 = seleMan2_.beginSelectedMolecule(jj); mol2 != NULL;
             mol2 = seleMan2_.nextSelectedMolecule(jj)) {
          // loop over the possible donors in molecule 1:
          for (hbd1 = mol1->beginHBondDonor(hbdi); hbd1 != NULL;
               hbd1 = mol1->nextHBondDonor(hbdi)) {
            dPos = hbd1->donorAtom->getPos();
            hPos = hbd1->donatedHydrogen->getPos();
            DH   = hPos - dPos;
            currentSnapshot_->wrapVector(DH);
            DHdist = DH.length();

            // loop over the possible acceptors in molecule 2:
            for (hba2 = mol2->beginHBondAcceptor(hbaj); hba2 != NULL;
                 hba2 = mol2->nextHBondAcceptor(hbaj)) {
              aPos = hba2->getPos();
              DA   = aPos - dPos;
              currentSnapshot_->wrapVector(DA);
              DAdist = DA.length();

              // Distance criteria: are the donor and acceptor atoms
              // close enough?
              if (DAdist < rCut_) {
                ctheta = dot(DH, DA) / (DHdist * DAdist);
                theta  = acos(ctheta) * 180.0 / Constants::PI;

                // Angle criteria: are the D-H and D-A and vectors close?
                if (theta < thetaCut_) {
                  // molecule 1 is a Hbond donor:
                  nHB++;
                  nD++;
		  r = hPos.length();
		  int binNo = int(r / deltaR_);
		  sliceQ_[binNo] += 1;
		  sliceCount_[binNo] += 1;		  
                }
              }
            }
          }

          // now loop over the possible acceptors in molecule 1:
          for (hba1 = mol1->beginHBondAcceptor(hbai); hba1 != NULL;
               hba1 = mol1->nextHBondAcceptor(hbai)) {
            aPos = hba1->getPos();

            // loop over the possible donors in molecule 2:
            for (hbd2 = mol2->beginHBondDonor(hbdj); hbd2 != NULL;
                 hbd2 = mol2->nextHBondDonor(hbdj)) {
              dPos = hbd2->donorAtom->getPos();

              DA = aPos - dPos;
              currentSnapshot_->wrapVector(DA);
              DAdist = DA.length();

              // Distance criteria: are the donor and acceptor atoms
              // close enough?
              if (DAdist < rCut_) {
                hPos = hbd2->donatedHydrogen->getPos();
                DH   = hPos - dPos;
                currentSnapshot_->wrapVector(DH);
                DHdist = DH.length();
                ctheta = dot(DH, DA) / (DHdist * DAdist);
                theta  = acos(ctheta) * 180.0 / Constants::PI;
                // Angle criteria: are the D-H and D-A and vectors close?
                if (theta < thetaCut_) {
                  // molecule 1 is a Hbond acceptor:
                  nHB++;
                  nA++;
		  r = hPos.length();
		  int binNo = int(r / deltaR_);
		  sliceQ_[binNo] += 1;
		  sliceCount_[binNo] += 1;		  		  
                }
              }
            }
          }
        }
      }
      writeDensityR();
    }
  }

    void HBondRvol::writeDensityR() {
      // compute average box length:

      double pi = acos(-1.0);
      DumpReader reader(info_, dumpFilename_);
      int nFrames   = reader.getNFrames();
      std::ofstream qRstream(outputFilename_.c_str());
      if (qRstream.is_open()) {
        
        qRstream << "# " << getAnalysisType() << "\n";
        qRstream << "#selection 1: (" << selectionScript1_ << ")\n";
        qRstream << "#selection 2: (" << selectionScript2_ << ")\n";
        qRstream << "#selection 3: (" << selectionScript3_ << ")\n";
        if (!paramString_.empty())
          qRstream << "# parameters: " << paramString_ << "\n";

        qRstream << "#distance"
                 << "\tH Bonds\n";
        for (unsigned int i = 0; i < sliceQ_.size(); ++i) {
          RealType Rval = (i + 0.5) * deltaR_;
	  binvol_[i] = (4*pi*(Rval*Rval)*deltaR_);
          if (sliceCount_[i] != 0 && binvol_[i] !=0) {
            qRstream << Rval << "\t" << sliceQ_[i] / (binvol_[i]) / nFrames
                     << "\n";
          } else {
              qRstream << Rval << "\t" << 0 << "\n";          
          }
        }

      } else {
        snprintf(painCave.errMsg, MAX_SIM_ERROR_MSG_LENGTH,
                 "HBondRvol: unable to open %s\n", outputFilename_.c_str());
        painCave.isFatal = 1;
        simError();
      }
      qRstream.close();
    }
  }  // namespace OpenMD