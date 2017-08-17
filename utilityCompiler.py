#more commenting to come
import subprocess as sp
import argparse
import re

# input: string of help result to do an initial pass on
# output: dict of valuable display parts
# Parses the Help text of function
def Parse(inputString):
    # Shape of output:
    # a dict of param fields ex: i, verbose, v
    # that each hold a dict containing: "Field Name" (a string), "Help Text" (a string),
    # "Type" (a string), "Requirement Status" (a tupple with a number and a list), "Base Value" (a "Type")
    resultant = {}
    #these need to be restructured likely
    divOne = re.compile("(?s)usage:\s\w+(?:.py )?(.+)optional arguments:")  # this is the section with the logic
    # might be able to combine the following two
    divTwo = re.compile(
        "(?s)optional arguments:\s(.+)")  # this is the section with the optional or mutually exclusive arguments
    divThree = re.compile("(?s)required named arguments:\s(.+)")  # this is the section with the not optional arguements
    #parse the logic
    resultant = ParseLogic(resultant, divOne.findall(inputString)[0])
    docLong = divTwo.findall(inputString)[0]
    if (divThree.findall(inputString) != []):
        docLong = docLong + divThree.findall(inputString)[0]
    #parse the documentation
    resultant = ParseDoc(resultant, docLong)
    return resultant


# inputs: the resultant dict and the logicals input
# outputs: the resultant dict with logical data added in so the entire dict should be defined and the inner dicts should have Mutually Exclusive Links set
def ParseLogic(resultant, input):
    print("Starting Logic Parsing. \n")
    divOneParse = re.compile(
        "(?s)(?:\| | |\[|\()-+(.+?(?:(?=(?:\s(?:-|\[-|\(-))|$)))")  # this parses out the logic, group 1 tells you something about the type, group 2 tells you what field is
    divOneField = re.compile(
        "([^\s\]\)]+)(?:\s(([[(])?(?(3)[^])]+?[])]{1}|[^])]+)))?(\])?( \|)?(\))?( )?")  # group 1 is field name group 2 is input name
    # i belive that the next chunk of code here works... but a second pass should be taken before this is finalized
    mutualArr = []
    for a in divOneParse.findall(input):
        e = divOneField.findall(a)[0]
        resultant.update({e[0]: {}})
        # something isn't right here
        if (e[3] != ''):
            val = 0
        elif (e[5] != ''):
            val = 1
        elif (e[4] != ''):
            val = 2
        else:
            val = 3
        if (val == 0 or val == 1 or val == 3):
            mutualArr = [e[1]]
        elif (val == 2):
            mutualArr.append(e[1])
        resultant[e[0]].update({"Requirement Status": (val, mutualArr)})
        # make sure e is what i think it is before proceeding
    print("Ending Logic Parsing. \n")
    return resultant


# inputs: the resultant dict and the help text input
# outputs: the resultant dict with the Help Text and Field Name added
# parses the documentation of help text associated with the program
def ParseDoc(resultant, input):
    print("Starting up Documentation Parsing. \n")
    sectionCapture = re.compile(
        "(?s)(?:\s+-+(.+?))(?:(?=[\n\r]\s+-+)|$)")#parses out each individual inputs documentation
    sectionParse = re.compile(
        "(?s)([^\s,]+)(?:\s([^\s,]+))?(?:,\s+-+([^\s]+)(?:\s([^\s]+))?)?\s+(.+)")#parses out the text of each input
    for e in sectionCapture.findall(input):
        a = sectionParse.findall(e)
        if (a != []): #if it actually matches something
            #add the help text information to the input's dict
            a = a[0]
            resultant[a[0]].update({"Field Name": a[1], "Help Text": a[4].strip()})
    print("Ending Documentation Parsing. \n")
    return resultant

# input: Dictionary to fold
# output: Filename
# Places a dictionary into a .txt file in a reasonable manner
# The file produced by this can be edited by the user, adding links or removing them where wanted
# additional functionality will be added in the UnFold part to support initial values where possible, since this program cannot pick up if there are initial values
def Fold(dict, pyfile):
    #format: dict of fields that each are dicts with {Field Name, Reqiurement Status, Help Text}
    print("Starting Fold. \n")
    text_file = open("manifest_of_%s.txt" % pyfile, 'w')
    for e in dict.keys():
        #write the field
        text_file.write(e + "\n")
        for a in dict[e].keys():
            #write one of the dicts as an output every line
            text_file.write("\t" + a + " : " + str(dict[e][a]) + "\n")
    text_file.close()
    print("Finished Folding. \n")
    return "manifest_of_%s.txt" % pyfile

# input: Filename
# output: Dictionary from file
# Does the inverse of Fold
# wont ever be used here but here for documentation purposes
def UnFold(filename):
    print("Begining Unfolding. \n")
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
            print("MAJOR ERROR WHILE UNFOLDING")
    print("Unfolding Complete. \n")
    return compiled

# input: string that can be made into a tuple
# output: a tuple from the form of the string
# pretty simple and naive... if it is causing the problems rebuild it from scratch
def maketuple(string):
    formSplitter = re.compile("(?s)\((\d),\s\[(.+)\]\)")#splits into didget and inner part of the requirements
    listExtractor = re.compile("(?s)'([^']+)'")#identifys all the parts of a list
    temp = formSplitter.findall(string)[0]
    int_imp = int(temp[0])
    temp = listExtractor.findall(temp[1])
    tup = (int_imp, temp)
    return tup

# parses the parameters of the function
def params():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pyfile", "-f", help=""" The python program you would like to make a manifest of """,
                        required=True)
    # these next three should be mutually exclusive
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--manifest", "-m", help=""" Use if you want to make a manifest of the program. """)
    group.add_argument("--extract", "-e", help=""" Use if you want to extract the manifest of the program. """)
    group.add_argument("--print", "-p", help=""" Use if you only want to print the produced output. """)
    args = parser.parse_args()
    return args

# main loop of the function
def main():
    # this part simply calls the function and sees what its output for help is and then pases the information on to parser
    args = params()
    print("Beginning Processing. \n")
    storagefilename = "manifest_of_%s.txt" % args.pyfile
    if (not args.extract):
        popen = sp.Popen('python %s --help' % args.pyfile, stdout=sp.PIPE, shell=True)
        stri = popen.stdout.read()
        help = Parse(stri)
    if (args.manifest):
        # folds the dict up into a text document
        print(Fold(help, args.pyfile))
    elif (args.extract):
        # this part here (the UnFold) would not be in the final program, it would be moved into the webapp so that the webapp could parse out the dict.
        recomped = UnFold(storagefilename)
    else: #args.print
        print(help)
    print("Process Complete. \n")

main()
