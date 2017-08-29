# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse
from django.shortcuts import render

import importlib
import os
import subprocess as sp
import argparse
import re

from django.template import loader

data_loc = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "\\DataFolder"

#Have to think about how im setting this up... models etc

# Create your views here.
def index(request):
    return HttpResponse("This is where the app might spawn?")

def runapp(request, func):
    #need to check if there are no inputs
    function_name = str(func).strip("/")
    function_manifest = "manifest_of_" + function_name + ".py.txt"
    folder = data_loc + "\\" + function_name
    filename = folder + "\\" + function_manifest
    #data_contents = {"testd1": {"Field Name": "field1", "Help Text": "help1"}, "testd2": {"Field Name": "field2", "Help Text": "help2"}}#str(UnFold(filename))#str(os.listdir(data_loc))
    #template = loader.get_template('VaribleApplication/pagestructure.html')

    #imports the function
    imp_loc = "DataFolder." + function_name + "." + function_name
    mod = importlib.import_module(imp_loc)

    #load manifest
    try:
        data_contents = UnFold(filename)
    except:
        data_contents = {"failed:": filename}

    #return HttpResponse("Running Application: " + function_name + " Pulling from: " + folder + " Computing file: " + filename + " Manifest contains: " + data_contents)
    requestInputs = dict(request.GET.lists())
    #calculate inputs
    form = {}
    for imp in requestInputs.keys():
        field = imp
        value = requestInputs[imp][0]
        form.update({field: value})

    run_from = "unknown"
    output = "Run Me!"
    print("running: " + str(mod) + "with inputs: "+str(form))
    try:
        output = mod.main(form)
        #output = str(mod.add(1, 2))
    except:
        output = "ERROR"
    try:
        try_dict = UnFold(filename)
        data_contents = try_dict
    except:
        try_dict = {"failed:": filename}
    return render(request, 'VaribleApplication/pagestructure.html', {"form": form, "data_contents": data_contents, "inputs": requestInputs, "runpoint": run_from, "output": output, "function_name": function_name})

# input: Filename
# output: Dictionary from file
# Does the inverse of Fold
#this is in the correct location
def UnFold(filename):
#    print("Begining Unfolding. \n")
    #open the text file and read it
    text_file = open(filename, 'r')
    phrase = text_file.read()
    arr = phrase.split("\n")
    fieldSplitter = re.compile("(?s)\s+(.+)\s:\s?(.+)?") #splits a string-form-dict into the keyname and the entry
    #temps
    compiled = {}
    savedfield = ""
    last = ""
    # this parses line by line and determines the meaning from the amount of tabs used on that line
    # no tab: field
    # tab: inner dictionary
    for e in arr:
        try: #here for safty
            if (e[0] != "\t" and e[0] != " "): #if it is a field
                #save the name and create a dict with that name for its inputs later
                savedfield = str(e)
                compiled.update({savedfield:{}})
            else: #if it is part of an inner dictionary
                a = fieldSplitter.findall(e)
                # if it fits the format of KEYNAME : ENTRY
                if a != []:
                    #this entire part basically makes the dict from the inputs
                    a = a[0]
                    last = a[0]
                    if a[1] != "":
                        #if the entry is a tuple, make a tuple out of it
                        if a[1][0] == "(":
                            compiled[savedfield].update({last : maketuple(a[1])})
                        else:
                            compiled[savedfield].update({last: a[1]})
                #this happens when it takes more than one line to display the help entry for a field,
                ## in which case it is just appended onto the last part of said key
                else:
                    compiled[savedfield].update({last: compiled[savedfield][last]+e.strip()})
        except:
            a = a
#            print("MAJOR ERROR WHILE UNFOLDING")
#    print("Unfolding Complete. \n")
    return compiled
