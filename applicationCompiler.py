import utilityCompiler as uc
import shutil as sh
import re as re
import subprocess as sp
import os

DataFolderLoc = "D:/Someting memey/DataFolder" #this should be a setable thing

def main(progLoc):
    fileParse = re.compile('\/([^\/]+)\.py')
    filename = fileParse.findall(progLoc)[0]
    NewLocationPy = DataFolderLoc + filename + ".py"
    manifestLocation = os.curdir + "manifest_of_" + filename + ".py.txt"#hmm thinking
    NewLocationMani = DataFolderLoc + "manifest_of_" + filename + ".py.txt"

    popen = sp.Popen('python %s --help' % progLoc, stdout=sp.PIPE, shell=True)
    stri = popen.stdout.read()
    help = uc.Parse(stri)

    print(uc.Fold(help, filename))
    sh.copyfile(progLoc, NewLocationPy)
    sh.copyfile(manifestLocation, NewLocationMani)