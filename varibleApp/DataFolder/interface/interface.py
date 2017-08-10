import numpy as np #this does math
import pandas as pd #this helps with the sorting and the math associated
import argparse #this helps parse the arguments to the call
import sys #this is needed to deal with inputs
import os #for the sql input
from sqlalchemy.engine import create_engine #for sql input


def main(arguments):
    print "Starting up..."
    sys.stdout.flush()
    args = null_check(arguments)
    print "Extracting table from database..."
    sys.stdout.flush()
    simularites = sqlCall(args)  # the table of simularity mesurements
    print "Sorting table..."
    sys.stdout.flush()
    sortedSims = sort(simularites)  # the sorted table of simularity mesurements (top = highest)
    print "Outputing Requisition... \n"
    sys.stdout.flush()
    return output(sortedSims, args)

# inputs: arguments
# output: arguments in a better format
# checks to see if the arguement inputs are correct, if not, program ends
def null_check(arguments):
    parser = argparse.ArgumentParser()
    parser.add_argument("--howmany", help="How many closest simularites to display.", type=float, default=5)
    parser.add_argument("--thresh" , help="threshold for what simularites to display.", type=float, default=2)
    parser.add_argument("--threshHigh", help="Array in which to display simularites from. (unclear) (DONT USE THIS UNLESS YOU KNOW WHAT YOU ARE DOING)", type=float)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ZooID", help="ZooID of the image you want to compare.")
    group.add_argument("--UniqueID", help="UniqueID of the image you want to compare.")
    parser.add_argument("-dict", type=bool, default=False)
    args = parser.parse_args(args=arguments)
    #this return statment is not completely flesh out yet
    return 0;

#temporary for testing
def check():
    return {'count': 3, 'thresh': 2, 'threshHigh': 5, 'ID': "dank memes", 'ID-type': "ZooID"}

# inputs: arguments
# output: a pandas list of the simularity mesurements of inputed ID
def sqlCall(args):
    #Temporaryly commented out for non-linked testing
    #return pd.read_sql('COLUMN', engine)
    s = {'one' : pd.Series([3, 2, 1, 5, 7, 9], index=['a', 'b', 'c', 'd', 'e', 'f']), 'two' : pd.Series([1, 2, 3, 4, 5, 6 ,7], index=['a', 'b', 'c', 'd', 'e', 'f', 'g'])}
    return pd.DataFrame(s)

# inputs: a simularity mesurements array
# outputs: a sorted simularity mesurements array
def sort(simularities):
    return simularities.sort_values(by="two")

# inputs: a sorted simularity mesurements array and the arguments list
# outputs: nil
# prints out all the simular images information, calls the image downloading if active
def output(simularities, args):
    #case where user choses how many to print off of top
    count = 0
    outdict = []
    for index, row in simularities.iterrows():
        if row[1] >= args['thresh'] and row[1] <= args['threshHigh'] and count < args['count']:
            if args['dict']:
                print row[0], row[1]
            else:
                outdict.append({row[0]: row[1]})
            count += 1
    if args['dict']:
        return outdict

def add(a, b):
    return a + b

if __name__ == '__main__':
    try:
        import sys
        main(sys.argv[1:])
    except:
        print("ERROR")
