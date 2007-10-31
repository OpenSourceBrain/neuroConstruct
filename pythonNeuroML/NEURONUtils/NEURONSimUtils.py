#
#
#   A class with a number of utilities for use in Python based NEURON
#   simulations run in neuroConstruct
#
#   Author: Padraig Gleeson
#
#   This file has been developed as part of the neuroConstruct project
#   This work has been funded by the Medical Research Council
#
#

import sys
import os
import logging

import hoc


if sys.path.count(os.getcwd())==0:
    sys.path.append(os.getcwd())
    
sys.path.append("../NeuroMLUtils")

from NetworkHandler import NetworkHandler

    
h = hoc.HocObject()


def createSimpleGraph(variable, dur, maxy = 50.0, miny = -90):
    h = hoc.HocObject()
    h("objref SampleGraph")
    h("SampleGraph = new Graph(0)")
    h.SampleGraph.size(0,dur,-90.0, maxy)
    h("graphList[0].append(SampleGraph)")
    
    h.SampleGraph.view(0, miny, dur, maxy-miny, 80, 330, 330, 250)
    h.SampleGraph.addexpr(variable, variable, 1, 1, 0.8, 0.9, 2)
    
    
def forp():
  h('forall psection()')
    
def psection():
  h('psection()')

   
#
#
#   NEURON version of the NetworkHandler for handling network events,
#   e.g. cell locations, connections, etc. These events can come from
#   a SAX parsed NetworkML file, or a parsed HDF5 file, etc.
#
#

class NetManagerNEURON(NetworkHandler):
    
    log = logging.getLogger("NetManagerNEURON")
  
    h = hoc.HocObject()
        
    globalPreSynId = 100000
    
        
        
    #
    #  Overridden from NetworkHandler
    #    
    def handlePopulation(self, cellGroup, cellType, size):
      
        if (size>=0):
            sizeInfo = ", size "+ str(size)+ " cells"
            
            self.log.info("Population: "+cellGroup+", cell type: "+cellType+sizeInfo)
            
            self.executeHoc("n_"+cellGroup+" = "+ str(size))
            self.executeHoc("objectvar a_"+cellGroup+"[n_"+cellGroup+"]")

        else:
                
            self.log.error("Population: "+cellGroup+", cell type: "+cellType+" specifies no size. Will lead to errors!")
        
  
    #
    #  Overridden from NetworkHandler
    #    
    def handleLocation(self, id, cellGroup, cellType, x, y, z):
        self.printLocationInformation(id, cellGroup, cellType, x, y, z)
                
        
        newCellName = cellGroup+"_"+id
        
        
        createCall = "new "+cellType+"(\""+newCellName+"\", \"" +cellType+"\", \"New Cell: "+newCellName+" of type: "+cellType+"\")"
        
        cellInArray = "a_"+cellGroup+"["+id+"]"
        
        setupCreate = "obfunc newCell() { {"+cellInArray+" = "+createCall+"} return "+cellInArray+" }"
        
        self.executeHoc(setupCreate)
        
        
        
        newCell = self.h.newCell()
        
        newCell.position(float(x), float(y), float(z))
        
        
        self.h.allCells.append(newCell)
        
        self.log.info("Have just created cell: "+ newCell.reference)
        
        if self.isParallel == 1:
            self.executeHoc("pnm.register_cell(getCellGlobalId(\""+cellGroup+"\", "+id+"), "+cellInArray+")")
        
        
    #
    #  Overridden from NetworkHandler
    #    
    def handleConnection(self, projName, id, source, target, synapseType, \
                                                    preCellId, \
                                                    postCellId, \
                                                    preSegId = 0, \
                                                    preFract = 0.5, \
                                                    postSegId = 0, \
                                                    postFract = 0.5, \
                                                    localInternalDelay = 0, \
                                                    localPreDelay = 0, \
                                                    localPostDelay = 0, \
                                                    localPropDelay = 0, \
                                                    localWeight = 1, \
                                                    localThreshold = 0):
        
        self.printConnectionInformation(projName, id, source, target, synapseType, preCellId, postCellId, localWeight)
          
        
        self.log.info("Going to create a connection of type " +projName+", id: "+id+", synapse type: "+synapseType)
        self.log.info("From: "+source+", id: "+str(preCellId)+", segment: "+str(preSegId)+", fraction: "+str(preFract))
        self.log.info("To  : "+target+", id: "+str(postCellId)+", segment: "+str(postSegId)+", fraction: "+str(postFract))
        
        
        targetCell = "a_"+target+"["+str(postCellId)+"]"
        sourceCell = "a_"+source+"["+str(preCellId)+"]"
        
        
        if self.isParallel == 1:
            self.executeHoc("localSynapseId = -2")
            self.executeHoc("globalPreSynId = "+str(self.globalPreSynId))
            
        if self.h.isCellOnNode(str(target), int(postCellId)) == 1:
            self.log.info("++++++++++++ PostCell: "+targetCell+" is on this host...")
        
            synObjName = projName+"_"+synapseType+"_"+id
            
            self.executeHoc("objref "+synObjName)
                
            self.executeHoc(targetCell+".accessSectionForSegId("+postSegId+")")
                
            self.executeHoc("fractSecPost = "+targetCell+".getFractAlongSection(" \
                        +str(postFract)+", "+str(postSegId)+")")
            
            self.log.info("Synapse object at: "+str(h.fractSecPost) +" on sec: "+h.secname()+", or: "+str(postFract)+" on seg id: "+ str(postSegId))
            
            self.executeHoc(synObjName+" = new "+synapseType+"(fractSecPost)")
            
            self.executeHoc(targetCell+".synlist.append("+synObjName+")")
            
            
            self.executeHoc("localSynapseId = "+targetCell+".synlist.count()-1")
            
        else:
            self.log.info("------------ PostCell: "+targetCell+" is not on this host...")
            
            
        delayTotal = float(localInternalDelay) + float(localPreDelay) + float(localPostDelay) + float(localPropDelay)
        
        
        if self.isParallel == 0:
        
            self.executeHoc(sourceCell+".accessSectionForSegId("+preSegId+")")
        
            self.executeHoc("fractSecPre = "+sourceCell+".getFractAlongSection("+str(preFract)+", "+str(preSegId)+")")
        
            self.log.info("NetCon object at: "+str(h.fractSecPre) +" on sec: "+h.secname()+", or: "+str(preFract)+" on seg id: "+ str(preSegId))
        
        
            self.executeHoc(sourceCell+".synlist.append(new NetCon(&v(fractSecPre), " \
                      +synObjName+", "+localThreshold+", "+str(delayTotal)+", "+localWeight+"))")
        
       
        else:
            if self.h.isCellOnNode(str(source), int(preCellId)) == 1: 
                self.log.info("++++++++++++ PreCell: "+sourceCell+" with globalPreSynId: "+str(self.globalPreSynId)+" is here!!")
                self.executeHoc("pnm.register_cell(globalPreSynId, "+sourceCell+")")
            else: 
                self.log.info("------------ PreCell: "+sourceCell+" not on this host...")
                
            
            self.executeHoc("pnm.nc_append(globalPreSynId, getCellGlobalId(\""+target+"\", "+postCellId+"), "\
                        +"localSynapseId, "+localWeight+", "+str(delayTotal)+")")
            
        self.globalPreSynId+=1
        
        
#
#   Helper function for printing hoc before executing it
#
    def executeHoc(self, command):
    
        cmdPrefix = ">>>>>>: "
        
        self.log.info(cmdPrefix+command)
        
        self.h(command)
        
        
        
        
        