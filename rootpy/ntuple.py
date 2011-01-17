import ROOT
from basictypes import *
import numpy as np
from classfactory import *

class Ntuple(ROOT.TTree):

    def __init__(self, name, buffer = None, variables = None):

        ROOT.TTree.__init__(self, name, name)
        if buffer != None:
            if variables == None:
                variables = buffer.keys()
            for variable in variables:
                value = buffer[variable]
                if isinstance(value, Variable):
                    self.Branch(variable, value, "%s/%s"% (name, value.type()))
                elif isinstance(value, ROOT.vector):
                    self.Branch(variable, value)
                else:
                    raise TypeError("type %s for branch %s is not valid"% (type(value), variable))

class NtupleChain:
    
    def __init__(self, treeName, files, buffer=None):
        
        self.treeName = treeName
        if type(files) is not list:
            files = [files]
        self.files = files
        self.buffer = buffer
        if self.buffer:
            for name, value in self.buffer.items():
                if name not in dir(self):
                    setattr(self, name, value)
                else:
                    raise ValueError("Illegal or duplicate branch name: %s"%name)
        self.weight = 1.
        self.tree = None
        self.file = None
        self.entry = 0
        self.entries = 0
        
    def _initialize(self):

        if self.tree != None:
            self.tree = None
        if self.file != None:
            self.file.Close()
            self.file = None
        if len(self.files) > 0:
            fileName = self.files.pop()
            self.file = ROOT.TFile.Open(fileName)
            if not self.file:
                print "WARNING: Skipping file. Could not open file %s"%(fileName)
                return self._initialize()
            self.tree = self.file.Get(self.treeName)
            if not self.tree:
                print "WARNING: Skipping file. Tree %s does not exist in file %s"%(self.treeName, fileName)
                return self._initialize()
            # Buggy D3PD:
            if len(self.tree.GetListOfBranches()) == 0:
                # Try the next file:
                print "WARNING: skipping tree with no branches in file %s"%fileName
                return self._initialize()
            self.entry = 0
            self.entries = self.tree.GetEntries()
            if self.buffer:
                self.tree.SetBranchStatus("*", False)
                for branch, address in self.buffer.items():
                    if not self.tree.GetBranch(branch):
                        print "WARNING: Skipping file. Branch %s was not found in tree %s in file %s"%(branch, self.treeName, fileName)
                        return self._initialize()
                    self.tree.SetBranchStatus(branch, True)
                    self.tree.SetBranchAddress(branch, address)
            return True
        return False

    def show(self):

        if self.tree:
            self.tree.Show()
    
    def read(self):
        
        if not self.entry < self.entries:
            if not self._initialize():
                return False
        self.tree.GetEntry(self.entry)
        self.weight = self.tree.GetWeight()
        self.entry += 1
        return True

class NtupleBuffer(dict):

    try:
        ROOT.gInterpreter.GenerateDictionary("vector<vector<float> >", "vector")
        ROOT.gInterpreter.GenerateDictionary("vector<vector<int> >", "vector")
    except:
        make_class("vector<vector<float> >", "<vector>")
        make_class("vector<vector<int> >", "<vector>")

    demote = {"Float_T":"F",
              "Int_T":"I",
              "Int":"I",
              "Float":"F",
              "F":"F",
              "I":"I",
              "UI":"UI",
              "vector<float>":"F",
              "vector<int>":"I",
              "vector<int, allocator<int> >":"I",
              "vector<float, allocator<float> >":"F",
              "VF":"F",
              "VI":"I",
              "vector<vector<float> >":"VF",
              "vector<vector<float> >":"VI",
              "vector<vector<int>, allocator<vector<int> > >":"VI",
              "vector<vector<float>, allocator<vector<float> > >":"VF",
              "VVF":"VF",
              "VVI":"VI"} 

    def __init__(self, variables, default=-1111, flatten=False):
        
        data = {}
        methods = dir(self)
        processed = []
        for name, type in variables:
            if flatten:
                type = NtupleBuffer.demote[type]
            if name in processed:
                raise ValueError("Duplicate variable name %s"%name)
            else:
                processed.append(name)
            if type.upper() in ("I", "INT_T"):
                data[name] = Int(default)
            elif type.upper() in ("UI", "UINT_T"):
                data[name] = UInt(default)
            elif type.upper() in ("F", "FLOAT_T"):
                data[name] = Float(default)
            elif type.upper() in ("VI", "VECTOR<INT>"):
                data[name] = ROOT.vector("int")()
            elif type.upper() in ("VF", "VECTOR<FLOAT>"):
                data[name] = ROOT.vector("float")()
            elif type.upper() in ("VVI", "VECTOR<VECTOR<INT> >"):
                data[name] = ROOT.vector("vector<int>")()
            elif type.upper() in ("VVF", "VECTOR<VECTOR<FLOAT> >"):
                data[name] = ROOT.vector("vector<float>")()
            else:
                raise TypeError("Unsupported variable type: %s"%(type.upper()))
            if name not in methods and not name.startswith("_"):
                setattr(self, name, data[name])
            else:
                raise ValueError("Illegal variable name: %s"%name)
        dict.__init__(self, data)

    def reset(self):
        
        for value in self.values():
            value.clear()

    def __str__(self):

        return self.__repr__()

    def __repr__(self):

        rep = ""
        for var, value in self.items():
            rep += "%s ==> %s\n"%(var, value)
        return rep

# inTree is an existing tree containing data (entries>0).
# outTree is a new tree, not necessarily containing any branches, and should not contain any data (entries==0).
class NtupleProcessor(object):

    def __init__(self, inTree, outTree, inVars=None, outVars=None, flatten=False):

        self.inTree = inTree
        self.outTree = outTree
        self.inVars = inVars
        if not self.inVars:
            self.inVars = [(branch.GetName(), branch.GetListOfLeaves()[0].GetTypeName().upper()) for branch in inTree.GetListOfBranches()]
        self.outVars = outVars
        if not self.outVars:
            self.outVars = self.inVars
        self.inBuffer = NtupleBuffer(self.inVars)
        self.outBuffer = self.inBuffer
        self.inBuffer.fuse(self.inTree, createMissing=False)
        self.outBuffer.fuse(self.outTree, createMissing=True)
        self.entries = self.inTree.GetEntries()
        self.entry = 0
        self.flatten = flatten

    def read(self):

        if self.entry < self.entries:
            self.inTree.GetEntry(self.entry)
            return True
        return False

    def write(self):

        self.outTree.Fill()

    def copy(self):

        if self.flatten:
            while self.next():
                self.write()
        else:
            while self.next():
                self.write()

class NtupleReader:
    
    def __init__(self, treeList, branchMap, branchList=None, subs=None):
        
        if type(treeList) is not list:
            treeList = [treeList]
        assert(len(treeList)>0)
        self.treeList = [tree for tree in treeList]
        self.branchMap = branchMap
        self.subs = subs
        
        if not branchList:
            self.branchList = self.branchMap.keys()
        else:
            self.branchList = branchList
            
        self.weight = 1.
        self.tree = None
        self.entry = 0
        self.entries = 0
        
    def initialize(self):

        if self.tree != None:
            self.tree.ResetBranchAddresses()
        if len(self.treeList) > 0:
            self.tree = self.treeList.pop()
            self.entry = 0
            self.entries = self.tree.GetEntries()
            for branch in self.branchList:
                subBranch = branch
                if self.subs:
                    if branch in self.subs.keys():
                        subBranch = self.subs[branch]
                if not self.tree.GetBranch(subBranch):
                    raise RuntimeError("Branch %s was not found in tree %s"%(subBranch, self.tree.GetName()))
                self.tree.SetBranchAddress(subBranch, self.branchMap[branch])
            return True
        return False
    
    def isReady(self):
        
        return self.entry < self.entries
    
    def read(self):
        
        if not self.isReady():
            if not self.initialize():
                return False
        self.tree.GetEntry(self.entry)
        self.weight = self.tree.GetWeight()
        self.entry += 1
        return True

class FastTuple:
    
    def __init__(self, trees, branchNames=None):
        
        if branchNames != None:
            if type(branchNames) is not list:
                branchNames = [branchNames]
        self.specialBranchNames = ["__weight"]
        self.branchNames = branchNames
        
        if self.branchNames == None: 
            self.branchNames = [branch.GetName() for branch in trees[0].GetListOfBranches()]
        branches = dict([(name, []) for name in self.branchNames + self.specialBranchNames])
        buffer = dict([(name, Float()) for name in self.branchNames])
        
        #read in trees as lists
        reader = NtupleReader(trees, buffer)
        while reader.read():
            for name in self.branchNames:
                branches["__weight"].append(reader.weight)
                branches[name].append(buffer[name].value())
        
        #convert to numpy array
        self.arrays = dict([(name, np.array(branches[name])) for name in self.branchNames])
    
    def sort(self, branch):

        if self.arrays.has_key(branch):
            inx = np.argsort(self.arrays[branch])
            for key in self.arrays.keys():
                self.arrays[key] = np.array([self.arrays[key][i] for i in inx])
    
    def getListOfBranches(self):
        
        return self.arrays.keys()
    
    def getBranch(self, name):
        
        if self.arrays.has_key(name):
            return self.arrays[name]
        return None
    
    """
    def apply_cut(self, name, low=None, high=None):
        
        if name not in self.branchToIndex.keys():
            return
        index = self.branchToIndex[name]
        if low != None and high != None:
            condition = (self.crop[index] >= low) & (self.crop[index] < high)
        elif low != None:
            condition = self.crop[index] >= low
        elif high != None:
            condition = self.crop[index] < high
        else:
            return
        self.crop = self.crop.compress(condition, axis=1)
    
    def apply_cuts(self, cuts):
        
        self.reset()
        for cut in cuts:
            self.apply_cut(cut["variable"], low=cut["low"], high=cut["high"])
    """