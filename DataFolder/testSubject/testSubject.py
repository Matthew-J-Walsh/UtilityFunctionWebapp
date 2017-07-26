#!/usr/bin/env python

# -------------------------------------------------------------------------
#      Setup.
# -------------------------------------------------------------------------

# ---- Import standard modules to the python path.
import sys, os, shutil, math, random, copy, getopt, re, string, popen2, time
import ConfigParser, glob, operator, argparse, socket, socket, uuid, pdb
import numpy as np
#from glue import segments
# from glue.segmentsUtils import fromsegwizard, tosegwizard
#from glue import pipeline
#from glue import datafind
from numpy import loadtxt

#from XPypeline import xcondor, xparseoutputtype
#from gwpy.detector import Channel
#from gwpy.segments import DataQualityFlag


def parse_commandline():
    parser = argparse.ArgumentParser(description="Script for setting up \
                                                 X-Pipeline triggered search jobs.")
    # Define groups of flags to make the help output ore useful
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument("-s", "--search-type", help=
    """
    Search Type you would like to perform
    """,
                               required=True)
    requiredNamed.add_argument("-p", "--params-file", help=
    """
    Parameters (.ini) file
    """,
                               required=True)
    requiredNamed.add_argument("-n", "--grb-name", help=
    """
    Name of GRB, e.g., GRB070201
    """,
                               required=True)
    requiredNamed.add_argument("-g", "--grb-time", help=
    """
    GRB trigger time (GPS seconds)
    """,
                               required=True, dest='trigger_time', type=float)
    requiredNamed.add_argument("-r", "--right-ascension", help=
    """
    Right ascension of GRB (degrees, from 0 to 360)
    """,
                               required=True, dest='ra', type=float)
    requiredNamed.add_argument("-d", "--declination", help=
    """
    Declination of GRB (degrees, from -90 to 90)
    """,
                               required=True, dest='decl', type=float)
    requiredNamed.add_argument("-i", "--detector", help=
    """
    Add detector to the network
    """,
                               required=True, nargs='+')
    parser.add_argument("--FAR", help=
    """
    To be used with the --search-type=allsky argument.
    This controls the number of background trials/jobs
    such that the desired FAR is achieved roughly exactly.
    Will warn and error if not enough coincident background
    to achieve desired FAR
    """,
                        type=float)
    parser.add_argument("--FAP", help=
    """
    To be used with the --search-type=sn or grb argument.
    This controls the number of background trials/jobs
    such that the desired FAP is achieved roughly exactly.
    Will warn and error if not enough coincident background
    to achieve desired FAP
    """,
                        type=float)
    parser.add_argument("-e", "--sky-pos-err", help=
    """
    1-sigma uncertainty in sky position of GRB
(degrees) or file name of sky position grid to be used
with -t file option.
    """,
                        type=float)
    parser.add_argument("-t", "--grid-type", help=
    """
    String. Determines what shape of sky position
grid will be generated.  Recognized values are
'circular' (2-d grids constructed from concentric
'healpix' (2-d grids constructed using
the healpix algorithm), 'line' (1-d arc
grid), and 'file' (user generated grid of point, given
with -e option). 'timedelay' (1-D arc that creates
fixed time delay steps between base line of Dets
Default 'circular'.
    """,
                        default='circular')
    parser.add_argument("--right-ascension2", help=
    """
    Right ascension of center of second trigger
          error circle (degrees, from 0 to 360).  Intended
          for ANTARES HEN analysis.
    """,
                        type=float, dest='ra2')
    parser.add_argument("--declination2", help=
    """
    Declination of center of second trigger\
    error circle (degrees, from -90 to 90).  Intended\
    for ANTARES HEN analysis.
    """,
                        type=float, dest='decl2')
    parser.add_argument("--sky-pos-err2", help=
    """
    1-sigma uncertainty in sky position of second\
    trigger error circle (degrees).
    """,
                        type=float)
    parser.add_argument("-f", "--grid-sim-file", help=
    """
    File which contains (R.A.,Dec) coordinates
of simulated source positions.  To be used with
'--grid-type file' option.
    """,
                        default='')
    parser.add_argument("--network-selection", help=
    """
    If this flag is set we select the appropriate
network of IFOs from the set specified using
the --detector option using our data-quality
selection criteria; see <https://www.lsc-group.
phys.uwm.edu/twiki/bin/view/Bursts/
S5VSR1GRBNetworksV2pt5DQ>
    """,
                        action='store_true', default=False)
    parser.add_argument("--injdistrib", help=
    """
    Tilde delimited string of parameters describin\
the injection distribution in the first circle
Formats are:
1 parameter: 1-sigma containment of a fisher distribution
3 parameters: lognormal distribution in degrees
4 parameters: fisher distribution of statistical error and
core + tail fisher distribution of systematic error.
[stat_sigma sys_core_sigma fraction_core sys_tail_sigma]
all sigma are in degrees
    """)
    parser.add_argument("--injdistrib2", help=
    """
    Same as --injdistrib but for second error circle.
    """)
    parser.add_argument("--elognormal", help="Same as --injdistrib")
    parser.add_argument("--elognormal2", help="Same as --injdistrib2")
    parser.add_argument("--priority", help=
    """
    Integer specifying the priority of condor jobs.
Default value is 0, higher priority jobs are
submitted first to the cluster.
    """,
                        default="0", dest='condorPriority')
    parser.add_argument("--end-offset", help=
    """
    Specify that the end offset of the onsource window should be
greater or equal <offset>. The maximum of the end offset in the ini
file and <offset> is used.
    """,
                        type=float, dest='manualEndOffset')
    parser.add_argument("-m", "--mdc-path", help=
    """
    Path to mdc parent dir
    If this option is used then the mdc log files
for each GRB will be copied from
<mdc-path>/GRB_<grb-name>/<waveform>/logs
into the GRBs /input dir and renamed according
to X-Pipeline conventions.
    """)
    parser.add_argument("--disable-fast-injections", help=
    """
    If set disables the fast processing of injections
time frequency map produced only for small window
around injection time
    """,
                        dest='disableFastInjections', action='store_true', default=False)
    parser.add_argument("-c", "--catalogdir", help=
    """
    Specify location of waveform catalog files for
astrophysical injections (e.g., supernovae)
    """,
                        dest='catalog_dir')
    parser.add_argument("--big-mem", help=
    """
    Integer specifying the minimal memory requirement
for condor jobs in MB.
    """,
                        type=int, dest='minimalMem')
    parser.add_argument("--use-merging-cuts", help=
    """
    Specify the location of a post-processing
directory from which coherent cuts
should be read and applied to triggers
at the the trigger collection stage
    """,
                        dest='mergingCutsPath')
    parser.add_argument("--reuse-inj", help=
    """
    If --use-merging-cuts option also set will
reuse the injection from the previous cut-tuning
run. Use with caution no check is performed on
consistency between provided and needed injections.
    """,
                        dest='reUseInj', action='store_true', default=False)
    parser.add_argument("--xtmva", help=
    """
    Perform XTMVA analysis.
    """,
                        dest='xtmvaFlag', action='store_true', default=False)
    parser.add_argument("--off-source-inj", help=
    """
    If set perform injections into the off-source
instead of the on-source region.
    """,
                        dest='offSourceInj', action='store_true', default=False)
    parser.add_argument("--long-inj", help=
    """
    If specified, then when making injection dags a
buffer will be used in comparing injection peak 
time to block interval to determine if an 
injection should be processed by multiple blocks.
Works only for waveform sets with names beginning
with adi-a, adi-b, adi-c, adi-d, adi-e, ebbh-a,  
ebbh-d, ebbh-e, mva. See code for details.
    """,
                        dest='longInjections', action='store_true', default=False)
    parser.add_argument("--smart-cluster", help=
    """
    This will produce an extra set of DAGs that will run
the smart clustering for large production analyses.
    """,
                        dest='smartCluster', action='store_true', default=False)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="store_true")
    group.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    return args


# -------------------------------------------------------------------------
#      Parse the command line options.
# -------------------------------------------------------------------------
args = parse_commandline()

# Set command line arguments to variables to be used later in the code
# Also based on command line arguments set some other defaults
reUseInj = args.reUseInj
mergingCutsPath = args.mergingCutsPath
grid_type = args.grid_type
grb_name = args.grb_name
params_file = args.params_file
trigger_time = args.trigger_time
ra = args.ra
decl = args.decl
sky_pos_err = args.sky_pos_err
injdistrib = args.injdistrib
ra2 = args.ra2
decl2 = args.decl2
sky_pos_err2 = args.sky_pos_err2
injdistrib2 = args.injdistrib2
detector = args.detector
network_selection = args.network_selection
mdc_path = args.mdc_path
condorPriority = args.condorPriority
xtmvaFlag = args.xtmvaFlag
manualEndOffset = args.manualEndOffset
longInjections = args.longInjections
disableFastInjections = args.disableFastInjections
catalog_dir = args.catalog_dir
offSourceInj = args.offSourceInj
grid_sim_file = args.grid_sim_file
smartCluster = args.smartCluster
minimalMem = args.minimalMem
FAR = args.FAR
FAP = args.FAP

#
#    Naming defaults
#

# ---- grb_name should have format e.g., "GRB070201"
#      we append GRB prefix if missing unless we are analysing a
#      MOCK GRB.
if not (grb_name.startswith('MOCK')) and not (grb_name.startswith('GRB')):
    grb_name = 'GRB' + grb_name

# ---- if grb_name begins with MOCK then we are doing a MOCK analysis.
if grb_name.startswith('MOCK'):
    mockAnalysis = 1
else:
    mockAnalysis = 0

# -------------------------------------------------------------------------
#      Test to see if we are running on Atlas.
# -------------------------------------------------------------------------

# ---- Get partial hostname.
hostname = socket.gethostname()

# ---- Get full hostame.
fullhostname = socket.getfqdn()

# ---- Check hostname and set flag if necessary.
if 'atlas' in fullhostname:
    atlasFlag = 1
elif 'h2' in hostname:
    atlasFlag = 1
elif 'coma' in fullhostname:
    atlasFlag = 1
else:
    atlasFlag = 0

# -------------------------------------------------------------------------
#      Status message.  Report all supplied arguments.
# -------------------------------------------------------------------------

print >> sys.stdout
print >> sys.stdout, "####################################################"
print >> sys.stdout, "#              X-GRB Search Pipeline               #"
print >> sys.stdout, "####################################################"
print >> sys.stdout
print >> sys.stdout, "Parsed input arguments:"
print >> sys.stdout
print >> sys.stdout, "     parameters file:", params_file
print >> sys.stdout, "        trigger time:", trigger_time
print >> sys.stdout, "        trigger name:", grb_name
print >> sys.stdout, "     right ascension:", ra
print >> sys.stdout, "         declination:", decl
print >> sys.stdout, "         sky pos err:", sky_pos_err
if injdistrib:
    print >> sys.stdout, "          injdistrib:", injdistrib
if ra2 and decl2 and sky_pos_err2:
    print >> sys.stdout, "   right ascension 2:", ra2
    print >> sys.stdout, "       declination 2:", decl2
    print >> sys.stdout, "       sky pos err 2:", sky_pos_err2
if injdistrib2:
    print >> sys.stdout, "         injdistrib2:", injdistrib2
print >> sys.stdout, "    detector network:", detector
if network_selection:
    print >> sys.stdout, "   network selection: automatic"
print >> sys.stdout, "            mdc path:", mdc_path
print >> sys.stdout, "           grid type:", grid_type
if grid_type == 'file':
    print >> sys.stdout, "       grid sim file:", grid_sim_file
print >> sys.stdout, "     condor priority:", condorPriority
if mergingCutsPath:
    print >> sys.stdout, "   merging cuts from:", mergingCutsPath
if atlasFlag:
    print >> sys.stdout, "    running on atlas: yes"
if xtmvaFlag:
    print >> sys.stdout, "       running XTMVA: yes"
print >> sys.stdout

# ---- Write ASCII file holding setUpJobs command.

summary_file = 'grb_summary.txt'
# ---- Append to summary file.
sfile = open(summary_file, 'a')
sfile.write('\t'.join(['\nname', 'gps', 'ra', 'dec', 'network', 'numSky', 'numBG', 'analyse', '\n']))
sfile.write('\t'.join([grb_name, str(trigger_time), str(ra), str(decl)]))
sfile.close()

# ---- We will record the command line arguments to setUpJobs in a file called
#      grb.param.
#      This file is used by xgrbwebpage.py which expects the short form of
#      the options to have been used
command_string = 'setUpJobs '
with open('setUpJobs.param', 'w') as f:
    f.write(command_string + ' '.join(sys.argv[1:]))

# -------------------------------------------------------------------------
#      Preparatory.
# -------------------------------------------------------------------------

# ---- Generate unique id tag.
uuidtag = str(uuid.uuid4()).replace('-', '')

# ---- Record the current working directory in a string.
cwdstr = "."

# ---- Make directory to store text files (segment lists, parameter
#      files, etc.) that will be input to X-Pipeline.  This is done
#      lsto minimize clutter in the working directory.
try:
    os.mkdir('input')
except:
    pass  # -- Kludge: should probably fail with error message.

# ---- Find files which define merging cuts
mergingCutsString = ""
print mergingCutsPath
if mergingCutsPath:
    preCutFile = glob.glob(mergingCutsPath + '/*xmake_args_tuned_pre.txt')
    cutFile = glob.glob(mergingCutsPath + '/*xmake_args_tuned.txt')
    origResults = glob.glob(mergingCutsPath + '/*closedbox.mat')
    mergingCutsString = cutFile[0] + " " + origResults[0]
    if preCutFile:
        mergingCutsString = mergingCutsString + " " + preCutFile[0]

# -------------------------------------------------------------------------
#      Read configuration file.
# -------------------------------------------------------------------------

# ---- Status message.
print >> sys.stdout, "Parsing parameters (ini) file ..."

# ---- Check the params_file exists
if not os.path.isfile(params_file):
    print >> sys.stderr, "Error: non existent parameter file: ", \
        params_file
    sys.exit(1)

# Set some ini file defaults
doAsymmetricBackground = 0
backgroundAsymmetryFactor = 0.5

# ---- Create configuration-file-parser object and read parameters file.
cp = ConfigParser.ConfigParser()
cp.read(params_file)

if cp.has_option('tags', 'version'):
    ini_version = cp.get('tags', 'version')
    print >> sys.stdout, "Parameter file CVS tag:", ini_version

# ---- Check for a seed value for matlab's random number generator.
try:
    seed = int(cp.get('parameters', 'seed'))
except:
    seed = 931316785
    print >> sys.stdout, "Warning: No seed specified in configuration file."
    print >> sys.stdout, "         seed will be set to: ", seed

# ---- Matlab seed can take values between 0 and 2^31-2.
if (seed > pow(2, 31) - 2) or (seed < 0):
    print >> sys.stderr, "Error: seed must have value between 0 and 2^31-2"
    sys.exit(1)

# ---- NOTE: The following reading of variables can be split up and
#      moved into the relevant sections of the script where the
#      variables are actually used.

# ---- Read needed variables from [parameters] and [background] sections.
background_period = cp.getint('background', 'backgroundPeriod')
if cp.has_option('parameters', 'doAsymmetricBackground'):
    doAsymmetricBackground = cp.getint('parameters', 'doAsymmetricBackground')
if cp.has_option('parameters', 'backgroundAsymmetryFactor'):
    backgroundAsymmetryFactor = cp.getfloat('parameters', 'backgroundAsymmetryFactor')
blockTime = cp.getint('parameters', 'blockTime')
whiteningTime = cp.getfloat('parameters', 'whiteningTime')
transientTime = 4 * whiteningTime
onSourceBeginOffset = cp.getint('parameters', 'onSourceBeginOffset')
onSourceEndOffset = cp.getint('parameters', 'onSourceEndOffset')
onSourceEndOffset = max(onSourceEndOffset, manualEndOffset)
onSourceTimeLength = onSourceEndOffset - onSourceBeginOffset
outputType = cp.get('parameters', 'outputType')
xparseoutputtype.parse(outputType, cp)
jobsPerWindow = int(math.ceil(float(onSourceTimeLength) / float(blockTime - 2 * transientTime)))
onSourceWindowLength = 2 * transientTime + jobsPerWindow * (blockTime - 2 * transientTime)
minimumFrequency = cp.getint('parameters', 'minimumFrequency')
maximumFrequency = cp.getint('parameters', 'maximumFrequency')

channelListLine = cp.get('input', 'channelList')
channelList = channelListLine.split(',')
frameTypeListLine = cp.get('input', 'frameTypeList')
frameTypeList = frameTypeListLine.split(',')

# ---- Interval of data to be analysed.
# ---- Allow for asymmetric background analyses, if needed by the online analysis
# ---- Flag to be read from ini file
if doAsymmetricBackground == 0:
    print >> sys.stdout, "Running analysis with symmetric background"
    start_time = int(trigger_time - background_period / 2)
    end_time = int(trigger_time + background_period / 2)
# ---- introduce fractional background asymmetry
else:
    if backgroundAsymmetryFactor < 1.0:
        print >> sys.stdout, "CAUTION: Running analysis with asymmetric background"
        start_time = int(trigger_time - background_period * backgroundAsymmetryFactor)
        end_time = int(trigger_time + background_period * (1.0 - backgroundAsymmetryFactor))
    else:
        print >> sys.stderr, "ERROR: Running analysis with asymmetric background but with wrong fractional asymmetry. backgroundAsymmetryFactor should be less than 1.0"
        sys.exit(1)
duration = int(end_time - start_time)

###### Clean start here
# ---- We will copy all ifo data and mdc frame caches to the location
#      stored in frameCacheAll.
frameCacheAll = 'input/framecache.txt'

# ---- Read [input] channel parameters.
detectorListLine = cp.get('input', 'detectorList')
detectorList = detectorListLine.split(',')
virtualDetectorList = detectorList
if cp.has_option('input', 'virtualDetectorList'):
    virtualDetectorListLine = cp.get('input', 'virtualDetectorList')
    virtualDetectorList = virtualDetectorListLine.split(',')
    print >> sys.stdout, " "
    print >> sys.stdout, "********************************************************************************"
    print >> sys.stdout, "  WARNING: using virtual detectors. "
    print >> sys.stdout, "       real detector network:", detectorList
    print >> sys.stdout, "    virtual detector network:", virtualDetectorList
    print >> sys.stdout, "  The real detector list will be used for segments, frame finding, data quality"
    print >> sys.stdout, "  criteria, and calibration uncertainties. The virtual detector list will be"
    print >> sys.stdout, "  used for the search sky grid and determining likelihoods, lag files, and MDC"
    print >> sys.stdout, "  frames. The channels.txt file will contain both lists."
    print >> sys.stdout, "********************************************************************************"
    print >> sys.stdout, " "
channelListLine = cp.get('input', 'channelList')
channelList = channelListLine.split(',')
frameTypeListLine = cp.get('input', 'frameTypeList')
frameTypeList = frameTypeListLine.split(',')

# ---- Variables that may or may not be defined in .ini file:

# ---- Check for frame cache for real ifo data
try:
    dataFrameCache = cp.get('input', 'frameCacheFile')
except:
    print >> sys.stdout, "Warning: No frameCacheFile file specified in " \
                         "[input] section of configuration file."
    print >> sys.stdout, "        A frameCache for the ifo data file will be " \
                         "generated automatically."
    dataFrameCache = None

# ---- Check for a seed value for matlab's random number generator.
try:
    seed = int(cp.get('parameters', 'seed'))
except:
    seed = 931316785
    print >> sys.stdout, "Warning: No seed specified in configuration file."
    print >> sys.stdout, "         seed will be set to: ", seed

# ---- Matlab seed can take values between 0 and 2^31-2.
if (seed > pow(2, 31) - 2) or (seed < 0):
    print >> sys.stderr, "Error: seed must have value between 0 and 2^31-2"
    sys.exit(1)

# ---- Get datafind server.
try:
    datafind_server = cp.get('datafind', 'datafind_server')
except:
    datafind_server = os.environ['LIGO_DATAFIND_SERVER']
# ---- Get datafind executable e.g., ligo_data_find.
datafind_exec = cp.get("datafind", 'datafind_exec')
# ---- Get segfind executable e.g., ligolw_segment_query.
segfind_exec = cp.get("datafind", "segfind_exec")
# ---- Get segs_from_cats executable e.g., ligolw_ligolw_segments_from_cats.
segs_from_cats_exec = cp.get("datafind", "segs_from_cats_exec")
# ---- Get ligolw_print executable e.g., ligolw_print.
ligolw_print_exec = cp.get("datafind", "ligolw_print_exec")

# ---- Status message.
print >> sys.stdout, "... finished parsing parameters (ini) file."
print >> sys.stdout

# -------------------------------------------------------------------------
#      Validate list of detectors given.
# -------------------------------------------------------------------------

# ---- KLUDGE:TODO: Move this below automatic network selection so that we
#      only perform this once???

# ---- Status message.
print >> sys.stdout, "Comparing requested network to list of known detectors ..."

# ---- For each detector specified with the --detector option, compare to
#      the list of known detectors from the .ini file.  Keep only the requested
#      detectors and corresponding channel name and frame type.
#      KLUDGE:TODO: Should exit with error message if any of the detectors
#      is not recognized.
# ---- Indices of the detectors requested for this analysis.
keepIndex = []
for i in range(0, len(detector)):
    for ii in range(0, len(detectorList)):
        if detector[i] == detectorList[ii]:
            keepIndex.append(ii)
# ---- Sort indices so that order matches that used in ini file.
keepIndex.sort()
# ---- We now have a list of the indices of the detectors requested for the
#      analysis.  Keep only these.  Note that we over-write the 'detector'
#      list because we want to make sure the order matches the channel and
#      frameType lists.
detector = []
virtualDetector = []
channel = []
frameType = []
for jj in range(0, len(keepIndex)):
    detector.append(detectorList[keepIndex[jj]])
    virtualDetector.append(virtualDetectorList[keepIndex[jj]])
    channel.append(channelList[keepIndex[jj]])
    frameType.append(frameTypeList[keepIndex[jj]])

# ---- Status message.
print >> sys.stdout, "... finished validating network.          "
print >> sys.stdout

# -------------------------------------------------------------------------
#      Retrieve single-IFO segment lists for analysis period.
# -------------------------------------------------------------------------

# ---- Write time range to a temporary segment file named gps_range.txt.
#      We'll then read this file into a ScienceData object.  It's a hack, but
#      it seems that the only way to populate ScienceData objects is to read
#      segments from a file.
f = open('input/gps_range.txt', 'w')
time_range_string = '1 ' + str(start_time) + ' ' + str(end_time) + ' ' + str(duration) + '\n'
f.write(time_range_string)
f.close()
# ---- Read full analysis time range back in to a ScienceData object for easy manipulation.
analysis_segment = pipeline.ScienceData()
analysis_segment.read('input/gps_range.txt', blockTime)

# ---- Prepare storage for full segment lists.
full_segment_list = []
# ---- Prepare storage for lists of analysis and veto segment filenames.
analysis_seg_files = []
veto_seg_files = []

# If simulating noise skip all segment and veto related stuff
if cp.has_option('parameters', 'makeSimulatedNoise'):
    for ifoIdx in range(0, len(detector)):
        ifo = detector[ifoIdx]
        print 'Making simulated noise, creating temp seg file'
        background_duration = cp.getint('background', 'backgroundPeriod')
        startOfSeg = int(trigger_time) - background_duration / 2 - 1000
        endOfSeg = int(trigger_time) + background_duration / 2 + 1000
        f = open('segments_{0}.txt'.format(ifo), 'w')
        f.write('0 {0} {1} {2}'.format(startOfSeg, endOfSeg, endOfSeg - startOfSeg))
        f.close()
        analysis_seg_files.append('segments_{0}.txt'.format(ifo))
        veto_seg_files.append("None")

else:
    # ---- If generateSegs ==0 then user should have supplied segment-list and
    #      veto-list for each ifo used.
    if int(cp.get('segfind', 'generateSegs')) == 0:
        # ---- Loop over ifos we are considering.
        for ifoIdx in range(0, len(detector)):
            ifo = detector[ifoIdx]

            print 'Retrieving analysis segment list for ', ifo
            # ---- Get name of segment file and check that it exists.
            analysis_seg_files.append(cp.get(ifo, 'segment-list'))
            if not os.path.isfile(analysis_seg_files[ifoIdx]):
                print >> sys.stderr, "Error: non existent segment list file: ", \
                    analysis_seg_files[ifoIdx]
                sys.exit(1)

            print 'Retrieving veto segment list for ', ifo
            # ---- Get name of veto file and check that it exists.
            if cp.has_option(ifo, "veto-list"):
                veto_seg_files.append(cp.get(ifo, "veto-list"))
                if not os.path.isfile(veto_seg_files[ifoIdx]):
                    print >> sys.stderr, "Error: non existent veto list file: ", \
                        veto_seg_files[ifoIdx]
                    sys.exit(1)
            else:
                veto_seg_files.append("None")

    # ---- If generateSegs ~= 0 then we will generate segment-list and veto-list
    #      for each ifo.
    else:
        print 'Generating veto segment lists for all ifos '
        # ---- Set output dir for cat 1,2,3,4,5 veto files
        segs_from_cats_output_dir = "input/"
        if not (segs_from_cats_output_dir.endswith('/')):
            segs_from_cats_output_dir = segs_from_cats_output_dir + "/"

        # ---- Run segs_from_cats_exec to determine cat 1,2,3,4,5 vetos
        segs_from_cats_call = ' '.join([segs_from_cats_exec,
                                        "--segment-url", cp.get("segfind", "segment-url"),
                                        "--veto-file", cp.get("segfind", "veto-file"),
                                        "--gps-start-time", str(start_time),
                                        "--gps-end-time", str(end_time),
                                        "--output-dir", segs_from_cats_output_dir,
                                        "--separate-categories"])
        if cp.has_option("segfind", "useDMTFile"):
            if int(cp.get("segfind", "useDMTFile")):
                segs_from_cats_call = ' '.join([segs_from_cats_call, "--dmt-file"])
        print >> sys.stdout, segs_from_cats_call
        os.system(segs_from_cats_call)

        for ifoIdx in range(0, len(detector)):
            ifo = detector[ifoIdx]

            vetoTags = [1, 2, 4]
            for catIdx in vetoTags:

                # ---- Construct name of veto files.
                vetocat_filename = ''.join([segs_from_cats_output_dir, ifo,
                                            "-VETOTIME_CAT", str(catIdx), "-", str(start_time), "-", str(duration)])
                vetocat_filename_XML = vetocat_filename + ".xml"
                vetocat_filename_TXT = ''.join(["input/", ifo, "-veto-cat", str(catIdx), ".txt"])

                # ---- Check file exists.
                if not (os.path.isfile(vetocat_filename_XML)):
                    print >> sys.stderr, "Error: Problem creating veto file:", \
                        vetocat_filename_XML
                    sys.exit(1)

                # ---- Convert XML file to TXT format.
                segsToTxtCall = ' '.join([ligolw_print_exec,
                                          "--table segment --column start_time --column end_time",
                                          "--delimiter ' '",
                                          vetocat_filename_XML,
                                          "| awk '{print NR  \" \" $1 \" \" $2 \" \" $2-$1}' >",
                                          vetocat_filename_TXT])
                os.system(segsToTxtCall)

            print 'Generating science segment list for ', ifo
            seg_filename = ''.join(["input/", ifo, "-seg"])
            seg_filename_XML = ''.join([seg_filename, ".xml"])
            seg_filename_TXT = ''.join([seg_filename, ".txt"])

            segFindCommand = ' '.join([segfind_exec,
                                       "--query-segments",
                                       "--segment-url", cp.get("segfind", "segment-url"),
                                       "--gps-start-time", str(start_time),
                                       "--gps-end-time", str(end_time),
                                       "--include-segments", cp.get(ifo, "include-segments"),
                                       "--output-file", seg_filename_XML])
            if cp.has_option("segfind", "useDMTFile"):
                if int(cp.get("segfind", "useDMTFile")):
                    segFindCommand = ' '.join([segFindCommand, "--dmt-file"])
            print >> sys.stdout, segFindCommand
            os.system(segFindCommand);
            print '... finished generating segment list.'

            print 'Converting segment list from XML to TXT file: '
            segsToTxtCall = ' '.join([ligolw_print_exec,
                                      "--table segment",
                                      "--column start_time",
                                      "--column end_time",
                                      "--delimiter",
                                      "' '",
                                      seg_filename_XML,
                                      "| awk '{print NR  \" \" $1 \" \" $2 \" \" $2-$1}' >",
                                      seg_filename_TXT])
            os.system(segsToTxtCall)
            print '... finished converting segment list to TXT file.'

            # ---- Read in science and veto segments.
            sciseg = fromsegwizard(open(seg_filename_TXT));
            sciseg.coalesce()
            cat1veto = fromsegwizard(open("input/" + ifo + "-veto-cat1.txt"));
            cat1veto.coalesce()
            cat2veto = fromsegwizard(open("input/" + ifo + "-veto-cat2.txt"));
            cat2veto.coalesce()
            cat4veto = fromsegwizard(open("input/" + ifo + "-veto-cat4.txt"));
            cat4veto.coalesce()

            # ---- Subtract cat1veto flags from the science segments.
            sciseg_cat1 = sciseg - cat1veto;
            sciseg_cat1.coalesce()

            # ---- Write out newly constructed segment list.
            filename = ''.join(["input/", ifo, "_science_cat1.txt"])
            print 'Writing file: ', filename
            f = open(filename, "w");
            tosegwizard(f, sciseg_cat1);
            f.flush();
            f.close()
            analysis_seg_files.append(filename)

            # ---- Add cat2veto and cat4veto segments for each ifo.
            cat24veto = cat2veto + cat4veto;
            cat24veto.coalesce()
            # ---- Write out newly constructed veto list.
            filename = ''.join(["input/", ifo, "_cat24veto.txt"])
            print 'Writing file: ', filename
            f = open(filename, "w");
            tosegwizard(f, cat24veto);
            f.flush();
            f.close()
            veto_seg_files.append(filename)

# ---- Read in segment_lists to ScienceData object.
for ifoIdx in range(0, len(detector)):
    ifo = detector[ifoIdx]

    # ---- Read full segment list into a ScienceData object for easy
    #      manipulation.  Throw away science segment shorter than the
    #      blockTime value read from the configuration file.
    print 'Reading segment list from file ', analysis_seg_files[ifoIdx]
    full_segment = pipeline.ScienceData()
    full_segment.read(analysis_seg_files[ifoIdx], blockTime)
    print '... finished reading segment list.'

    # ---- Now restrict to desired analysis time range around trigger_time.
    full_segment.intersection(analysis_segment)
    # ---- Finally, append segment for this detector to the full list.
    full_segment_list.append(full_segment)

# ---- Read in segment_lists to ScienceData object.
for ifoIdx in range(0, len(detector)):
    ifo = detector[ifoIdx]

    # ---- Read full segment list into a ScienceData object for easy
    #      manipulation.  Throw away science segment shorter than the
    #      blockTime value read from the configuration file.
    print 'Reading segment list from file ', analysis_seg_files[ifoIdx]
    full_segment = pipeline.ScienceData()
    full_segment.read(analysis_seg_files[ifoIdx], blockTime)
    print '... finished reading segment list.'

    # ---- Now restrict to desired analysis time range around trigger_time.
    full_segment.intersection(analysis_segment)
    # ---- Finally, append segment for this detector to the full list.
    full_segment_list.append(full_segment)

# -------------------------------------------------------------------------
#      Choose detector network based on on-source data quality.
# -------------------------------------------------------------------------

# ---- Pulled the segment lists stuff outside of the "if network_selection"
#      statement since we need these to test the off-source segments.
# ---- Get cat1 and cat2 segment files for all 5 ifos.
#      Use 'None' when no file exists.
all_detectors = ['H1', 'H2', 'L1', 'G1', 'V1']
cat1_segment_file_list = []
cat2_segment_file_list = []
for ifo in all_detectors:
    try:
        # ----- Did we consider current ifo.
        idx = detector.index(ifo)
        cat1_segment_file_list.append(analysis_seg_files[idx])
        cat2_segment_file_list.append(veto_seg_files[idx])
    except (ValueError):
        cat1_segment_file_list.append("None")
        cat2_segment_file_list.append("None")

# ---- Write string listing detectors
detectorStr = ''
detectorStrTilde = ''
for ifo in detector:
    detectorStr = detectorStr + ifo
    detectorStrTilde = detectorStrTilde + ifo + '~'
detectorStrTilde = detectorStrTilde[0:len(detectorStrTilde) - 1]

if network_selection and blockTime < 256:
    print >> sys.stderr, "Warning: network selection does not currently ", \
        "work for blockTimes < 256s \n"

if network_selection:
    print >> sys.stdout, "\nSelecting ifo network from ", detector

    # ---- Write file containing GRB trigger time.
    ftriggertime = open('input/trigger_time.txt', 'w')
    ftriggertime.write("%f\n" % trigger_time)
    ftriggertime.close()

    # ---- Write file containing time offsets for on-source.
    ftimeoffsets = open('input/time_offsets.txt', 'w')
    for ifo in detector:
        ftimeoffsets.write("0 ")
    ftimeoffsets.close()

    network_outputFile = 'input/xnetworkselection_onsource.dat'

    xnetworkselectionCall = ' '.join(["xnetworkselection",
                                      detectorStr,
                                      "input/trigger_time.txt",
                                      "input/time_offsets.txt",
                                      cat1_segment_file_list[0],
                                      cat1_segment_file_list[1],
                                      cat1_segment_file_list[2],
                                      cat1_segment_file_list[3],
                                      cat1_segment_file_list[4],
                                      cat2_segment_file_list[0],
                                      cat2_segment_file_list[1],
                                      cat2_segment_file_list[2],
                                      cat2_segment_file_list[3],
                                      cat2_segment_file_list[4],
                                      network_outputFile,
                                      str(onSourceBeginOffset),
                                      str(onSourceEndOffset),
                                      str(transientTime),
                                      str(onSourceWindowLength)
                                      ])

    print >> sys.stdout, xnetworkselectionCall
    os.system(xnetworkselectionCall)

    fnet = open(network_outputFile)
    network_selection_on = fnet.read()
    fnet.close()

    if network_selection_on.endswith("\n"):
        network_selection_on = network_selection_on[0:len(network_selection_on) - 1]
    detectorStr = network_selection_on

    # ---- Figure out which if our ifos made it into the network.
    network_selection_on_list = []
    retained_ifo_indices = []
    full_segment_list_updated = []
    channel_updated = []
    frameType_updated = []
    # ---- skip GRB if the network is not well determined
    if network_selection_on[0] != 'X':
        # ---- Loop over the ifos we originally considered.
        for ifoIdx in range(0, len(detector)):
            ifo = detector[ifoIdx]
            # ---- If this ifo is in our new network.
            if network_selection_on.count(ifo):
                network_selection_on_list.append(ifo)
                full_segment_list_updated.append(full_segment_list[ifoIdx])
                retained_ifo_indices.append(ifoIdx)
                channel_updated.append(channel[ifoIdx])
                frameType_updated.append(frameType[ifoIdx])

    # ---- Update channel list.
    channel = channel_updated;
    # ---- Update frameType list.
    frameType = frameType_updated;

    # ---- Update list of segments.
    full_segment_list = full_segment_list_updated

    # ---- Update list of ifos we are using.
    detector = network_selection_on_list

# -------------------------------------------------------------------------
#      Choose appropriate likelihoods and lags for this network.
# -------------------------------------------------------------------------

# ---- Append to summary file.
sfile = open(summary_file, 'a')
sfile.write('\t' + detectorStr)
sfile.close()

print >> sys.stdout, " "

if len(detector) == 0:
    print >> sys.stderr, "Error:No ifos in network!!!"
    sys.exit(1)

elif len(detector) == 1:
    print >> sys.stdout, "One ifo in network: ", detector
    lagType = []
    likelihoodType = "likelihoodType_1det1site"

elif len(detector) == 2:
    print >> sys.stdout, "Two misaligned ifos in network: ", virtualDetector
    lagType = "lags_2det2site"
    likelihoodType = "likelihoodType_2det2site"

elif len(detector) == 3:
    print >> sys.stdout, "Three ifos at three sites: ", virtualDetector
    lagType = "lags_3det3site"
    likelihoodType = "likelihoodType_3det3site"

elif len(detector) == 4:
    print >> sys.stdout, "Four ifos at four sites: ", virtualDetector
    lagType = "lags_4det4site"
    likelihoodType = "likelihoodType_4det4site"

elif len(detector) == 5:
    print >> sys.stdout, "Five ifos at five sites: ", virtualDetector
    lagType = "lags_5det5site"
    likelihoodType = "likelihoodType_5det5site"

# -----------------------------------------------------------------------------
#               Construct tilde-separated list of sites
# -----------------------------------------------------------------------------

# ---- Initialise tilde-separated list of sites.
siteStrTilde = ''
for iDet in range(0, len(virtualDetector)):
    # ---- Get name of current site from current (virtual) detector.
    siteTemp = virtualDetector[iDet][0]
    # ---- Add current site to list only if does not already appear in it.
    if siteStrTilde.count(siteTemp) == 0:
        siteStrTilde = '~'.join([siteStrTilde, siteTemp])

# ---- Remove preceding tilde.
siteStrTilde = siteStrTilde[1:len(siteStrTilde)]

# -----------------------------------------------------------------------------
#               Construct tilde-separated list of detectors
# -----------------------------------------------------------------------------

# ---- Real detector list: for reading frames, segments, etc.
detectorStr = ''
detectorStrTilde = ''
for ifo in detector:
    detectorStr = detectorStr + ifo
    detectorStrTilde = detectorStrTilde + ifo + '~'
detectorStrTilde = detectorStrTilde[0:len(detectorStrTilde) - 1]

# ---- Real frame type, for reading frames.
frameTypeStrTilde = ''
for frameTypeName in frameType:
    frameTypeStrTilde = frameTypeStrTilde + frameTypeName + '~'
frameTypeStrTilde = frameTypeStrTilde[0:len(frameTypeStrTilde) - 1]

# -----------------------------------------------------------------------------
#         Having figured out network read in appropriate lag file.
# -----------------------------------------------------------------------------

# ---- We only need to read in a lag file if our network has 2 or more ifos.
if lagType:
    try:
        lagFile = cp.get('background', lagType)
    except:
        print >> sys.stdout, "Warning: No lagFile specified in configuration file."
        print >> sys.stdout, "         No time lag jobs will be made."
        lagFile = None

    if lagFile:
        if not os.path.isfile(lagFile):
            print >> sys.stderr, "Error: non existant lag file: ", lagFile
            sys.exit(1)
else:
    lagFile = None

print >> sys.stdout, "Using lag file: ", lagFile

# -----------------------------------------------------------------------------
#         Having figured out network read in appropriate likelihood types.
# -----------------------------------------------------------------------------

try:
    likelihoodTypeStr = cp.get('parameters', likelihoodType)
except:
    print >> sys.stderr, "Error: required likelihoodType not specified in " \
                         "configuration file."
    sys.exit(1)

print >> sys.stdout, "Using likelihoods: ", likelihoodTypeStr

####Clean to here

# -----------------------------------------------------------------------------
#      Write Matlab-formatted parameters files.
# -----------------------------------------------------------------------------

# ---- We will write three sets of parameters files:  one on-source file,
#      one off-source file, and (for each waveform set and injection scale)
#      one injections file.

# ---- Status message.
print >> sys.stdout, "Writing Matlab-formatted parameter files ..."

# ---- Write all options available in the parameters section to a file.
parameters = cp.options('parameters')

# ---- Parameter files for MDC waveform analyses, if requested.
if cp.has_option('mdc', 'mdc_sets'):
    # ---- Read [mdc] sets and injection scales.  If mdc_sets is empty or specifies
    #      unknown MDC sets then the script will have already exited when trying to
    #      write the mdcchannel file above.
    mdc_setsList = cp.get('mdc', 'mdc_sets')
    mdc_sets = mdc_setsList.split(',')
    # ---- Write one parameters file for each (mdc set, injection scale) pair.
    for set in mdc_sets:
        if cp.has_section(set) & cp.has_option(set, 'injectionScales'):
            # ---- This check lets you specify different injection scales for
            #      each MDC set.
            injectionScalesList = cp.get(set, 'injectionScales')
            injectionScales = injectionScalesList.split(',')
        else:
            # ---- Otherwise, use the injection scales specified in
            #      the [injection] section.
            injectionScalesList = cp.get('injection', 'injectionScales')
            injectionScales = injectionScalesList.split(',')

        # ---- Write a separate parameter file for each injection scale.
        scale_counter = 0
        for injectionScale in injectionScales:
            f = open("input/parameters_" + set + "_" + str(scale_counter) + ".txt", 'w')
            # ---- First write framecache file, channel file, event file, and sky position.
            f.write('channelFileName:input/channels.txt' + '\n')
            f.write('frameCacheFile:' + frameCacheAll + '\n')
            f.write('eventFileName:input/event_' + set + '.txt' + '\n')
            f.write('skyPositionList:' + skyPositionList + '\n')
            f.write('skyCoordinateSystem:earthfixed' + '\n')
            f.write('likelihoodtype:' + likelihoodTypeStr + '\n')
            # ---- Now write all of the other parameters from the parameters section.
            #      We ignore the likelihoodType_* lines since this is handled above.
            for i in range(0, len(parameters)):
                if not (parameters[i].startswith("likelihoodtype")):
                    value = cp.get('parameters', parameters[i])
                    if parameters[i] == "outputtype" and value == "clusters" and not (disableFastInjections):
                        f.write('outputtype:injectionclusters\n')
                    elif parameters[i] == "onsourceendoffset":
                        f.write('onsourceendoffset:' + str(onSourceEndOffset) + '\n')
                    elif parameters[i] == "circtimeslidestep":
                        continue
                    else:
                        f.write(parameters[i] + ':' + value + '\n')
            # ---- Write mdc info.
            f.write('mdcChannelFileName:input/channels_' + set + '.txt' + '\n')
            f.write('injectionFileName:input/injection_' + set + '.txt' + '\n')
            f.write('injectionScale:' + str(injectionScale) + '\n')
            if outputType == 'seedless':
                f.write('seedlessparams:input/seedless_simulation.txt\n')
            f.close()
            scale_counter = scale_counter + 1

# ---- Status message.
print >> sys.stdout, "... finished writing parameter files.     "
print >> sys.stdout

# -------------------------------------------------------------------------
#      Write channel file.
# -------------------------------------------------------------------------

# ---- Status message.
print >> sys.stdout, "Writing Matlab-formatted channel file ...      "

# ---- For each detector, write the corresponding channel name, frame type,
#      and virtual channel name to the channels file to be read by xdetection.
f = open('input/channels.txt', 'w')
for i in range(0, len(detector)):
    f.write(detector[i] + ':' + channel[i] + ' ' + frameType[i] + ' ' + virtualDetector[i] + ':' + channel[i] + '\n')
f.close()

# ---- Status message.
print >> sys.stdout, "... finished writing channel file.        "
print >> sys.stdout

# -------------------------------------------------------------------------
#      Determine MDCs to process, write mdcChannelFiles.
# -------------------------------------------------------------------------

# ---- Check for MDC sets.
if cp.has_option('mdc', 'mdc_sets'):

    # ---- Status message.
    print >> sys.stdout, "Writing Matlab-formatted MDC channel files " \
                         "and framecache files... "

    # ---- Get list of MDC sets to process.
    mdc_setsList = cp.get('mdc', 'mdc_sets')
    mdc_sets = mdc_setsList.split(',')
    # print >> sys.stdout, "mdc_sets:", mdc_sets

    # ---- We will create a list of all the log files for each mdc set
    mdc_log_files = []

    # ---- Make MDC channels file for each set.
    for setIdx in range(len(mdc_sets)):
        set = mdc_sets[setIdx]
        # print >> sys.stdout, "set:", set
        if cp.has_section(set):
            # ---- Read channel parameters for this mdc set.
            mdcChannelListLine = cp.get(set, 'channelList')
            mdcChannelList = mdcChannelListLine.split(',')
            mdcFrameTypeListLine = cp.get(set, 'frameTypeList')
            mdcFrameTypeList = mdcFrameTypeListLine.split(',')
            numberOfChannels = cp.get(set, 'numberOfChannels')
            # ---- Keep only info for detectors requested for the analysis.
            mdcChannel = []
            mdcFrameType = []
            for jj in range(0, len(keepIndex)):
                mdcChannel.append(mdcChannelList[keepIndex[jj]])
                mdcFrameType.append(mdcFrameTypeList[keepIndex[jj]])

            # ---- For each detector, write the
            #      corresponding channel name and frame type to a file.
            f = open('input/channels_' + set + '.txt', 'w')
            for i in range(0, len(detector)):
                # ---- if we are doing a MOCK analysis we must not add on
                #      grb_name to mdcFrameType.
                if not (mockAnalysis):
                    # ---- mdcFrameTypes have format: H1_SGC554Q8d9_ON_GRB060211B
                    # ---- from params file mdcFrameTypes of format: H1_SGC554Q8d9_ON_
                    #      we append last underscore if missing and append grb_name.
                    if not (mdcFrameType[i].endswith('_')):
                        mdcFrameType[i] = mdcFrameType[i] + '_'
                    mdcFrameType[i] = mdcFrameType[i] + grb_name

                f.write(detector[i] + ':' + mdcChannel[i] + ' ' + mdcFrameType[i] + '\n')

            f.close()
            # ---- end loop over ifo

            # -------------------------------------------------------------------------
            #                         Find MDC frames.
            # -------------------------------------------------------------------------

            # ---- Check to see if mdc frame cache has been specified in config file.
            try:
                mdcFrameCache = cp.get(set, 'frameCacheFile')
            except:
                print >> sys.stdout, "Warning: No frameCacheFile file specified " \
                                     "in [" + set + "] section of configuration file."
                print >> sys.stdout, "         A frameCache for the ifo data file " \
                                     "will be generated automatically."
                mdcFrameCache = None

            if mdcFrameCache:
                # ---- Check that the frame cache file specified actually exists.
                if not os.path.isfile(mdcFrameCache):
                    print >> sys.stderr, "Error: non existant framecache: ", mdcFrameCache
                    sys.exit(1)

                # ---- If the specified mdc frame cache exists then concat it
                #      other frame caches.
                command = 'cat ' + mdcFrameCache + '  >> ' + frameCacheAll
                os.system(command)

            # ---- If the mdcFrameCache was not specified we generate it here.
            #      Note that we look for frames using the virtual detector name
            #      to ensure the MDC injection data is consistent with the
            #      detector being simulated.
            else:
                for i in range(0, len(detector)):
                    # ---- generate frame cache file for MDCs
                    if not mdcFrameCache:
                        # ---- Status message.
                        print >> sys.stdout, "Writing MDC framecache file for " \
                                             "mdcset: " + set + ", ifo: " + virtualDetector[i] + " ..."
                        # ---- Clear away any pre-existing mdcframecache files.
                        os.system('rm -f mdcframecache_temp.txt')

                        # ---- Construct dataFind command.
                        dataFindCommand = ' '.join([datafind_exec,
                                                    "--server", datafind_server,
                                                    "--observatory", virtualDetector[i][0],
                                                    "--type", mdcFrameType[i],
                                                    "--gps-start-time", str(start_time),
                                                    "--gps-end-time", str(end_time),
                                                    "--url-type file",
                                                    "--lal-cache",
                                                    " > mdclalcache.txt"])
                        # ---- Issue dataFind command.
                        print "calling dataFind:", dataFindCommand
                        os.system(dataFindCommand)
                        print "... finished call to dataFind."

                        # ---- Convert lalframecache file to readframedata format.
                        print "calling convertlalcache:"
                        os.system('convertlalcache.pl mdclalcache.txt mdcframecache_temp.txt')
                        os.system('cat mdcframecache_temp.txt >> ' + frameCacheAll)
                        print "... finished call to convertlalcache."
                        # ---- Clean up.
                        os.system('rm -f mdcframecache_temp.txt mdclalcache.txt')

                        # ---- Status message.
                        print >> sys.stdout, "... finished writing MDC framecache file."
                        print >> sys.stdout

            # -------------------------------------------------------------------------
            #   Create a list of the mdc log files and create an mdc segment list.
            # -------------------------------------------------------------------------

            if not (mdc_path):
                print >> sys.stderr, "Error: mdc_path must be specified if we are using mdcs."
                print >> sys.stderr, "Use --mdc-path to specify it."
                sys.exit(1)

            # ---- check dir names end in '/'
            if not (mdc_path.endswith('/')):
                mdc_path = mdc_path + '/'
            mdc_grbdir = grb_name + '/'

            # ---- mdcFrameType[i] will have name in format H1_SGC100Q8d9_ON_GRB051105
            #      logs are in dir structure:
            #      /data/node5/eharstad/ExtTrigMDC/GRB051105/SGC1000Q8d9_ON/logs/
            #      ExtTrigMDC-SGC1000Q8d9_ON_GRB051105-815207086-256-Log.txt

            # ---- Remove <ifo>_ and _GRB* part from mdcFrameType.
            if mockAnalysis:
                strList0 = mdcFrameType[i].rsplit('-')
                mdcType = strList0[1]
            else:
                strList0 = mdcFrameType[i].rsplit('_')
                mdcType = strList0[1] + '_' + strList0[2]

            mdc_log_glob = mdc_path + grb_name + '/' + mdcType + '/logs/ExtTrigMDC-' + mdcType + '*.txt'
            print >> sys.stdout, ''
            print >> sys.stdout, 'Getting mdc log files from ' + mdc_log_glob
            mdc_log_files.append(glob.glob(mdc_log_glob))

            # ---- Report error if no log files found.
            if not (len(mdc_log_files[setIdx])):
                print >> sys.stderr, 'Error: No ExtTrigMDC*.txt log files in ' + mdc_log_glob
                sys.exit(1)

            # ---- If these are on source mdcs check we only have one log file.
            if mdcType.count('ON'):
                if len(mdc_log_files[setIdx]) > 1:
                    print >> sys.stderr, 'Error: We only expect one ON source ExtTrigMDC*.txt log file in ' + mdc_log_glob
                    sys.exit(1)

            # ---- Extract start time of each mdc block from its log file name
            #      use this to create a segment list which we later use to
            #      figure out which mdc blocks have good data quality flags.
            mdc_segs = []
            for fileIdx in range(0, len(mdc_log_files[setIdx])):
                # ---- We need to extract start times for each log file.
                # ---- We are in a loop over mdc sets.
                strList = mdc_log_files[setIdx][fileIdx].rsplit('-')

                # ---- Choose element of strList counting back from end of strList in case
                #      dir names contain a hyphen which would throw off our counting.
                mdc_start_time = int(strList[len(strList) - 3])
                mdc_block_time = int(strList[len(strList) - 2])
                mdc_segs.append([mdc_start_time, mdc_block_time])

            # ---- Sort our segments on mdc_start_time.
            mdc_segs_sorted = sorted(mdc_segs, key=operator.itemgetter(0))

            # ---- Write mdc segtment list.
            fmdcseg = open('input/segment_' + set + '.txt', 'w')
            for segIdx in range(0, len(mdc_segs_sorted)):
                mdc_start_time = mdc_segs_sorted[segIdx][0]
                mdc_block_time = mdc_segs_sorted[segIdx][1]
                mdc_end_time = mdc_start_time + mdc_block_time
                time_range_string = str(segIdx) + ' ' + \
                                    str(mdc_start_time) + ' ' + str(mdc_end_time) + \
                                    ' ' + str(mdc_block_time) + '\n'
                fmdcseg.write(time_range_string)
            fmdcseg.close()

        else:
            print >> sys.stdout, "Error: MDC set ", set, \
                " is not defined in the parameters file.  Exiting."
            print >> sys.stdout
            sys.exit(1)

    # ---- Status message.
    print >> sys.stdout, "... finished writing MDC channel and frame files.   "
    print >> sys.stdout

# -------------------------------------------------------------------------
#    Make coincidence segment list for MDCs.
# -------------------------------------------------------------------------

# ---- Check for MDC sets.
if cp.has_option('mdc', 'mdc_sets'):

    # ---- Status message.
    print >> sys.stdout, "Writing MDC event files ...          "

    # ---- Get list of MDC sets to process.
    mdc_setsList = cp.get('mdc', 'mdc_sets')
    mdc_sets = mdc_setsList.split(',')

    for set in mdc_sets:
        # ---- Read mdc segments into a "ScienceData" object.
        mdc_segment = pipeline.ScienceData()
        mdc_segment.read('input/segment_' + set + '.txt', blockTime)

        # ---- Now get the intersection of all of the detector segment lists with this
        #      on-source list. Note that the segment lists mst be sorted by start time
        #      for intersection to work properly
        mdc_coincidence_segment = copy.deepcopy(mdc_segment)
        for det in full_segment_list:
            mdc_coincidence_segment.intersection(det)

        # ---- Do some checking... check we have some MDCs in coinc...

        # ---- At this point, the ScienceData object mdc_segment contains the
        #      mdc segments.  Write this to the mdc event file.
        f = open('input/event_' + set + '.txt', 'w')
        # ---- We also rewrite our segment files so they only contain the segs
        #      we are going to analyse
        fmdcseg = open('input/segment_' + set + '.txt', 'w')
        # ---- loop over coinc segs
        for i in range(mdc_coincidence_segment.__len__()):
            duration = mdc_coincidence_segment.__getitem__(i).end() - \
                       mdc_coincidence_segment.__getitem__(i).start()
            if (duration == blockTime):
                time_range_string = str(mdc_coincidence_segment.__getitem__(i).start() \
                                        + blockTime / 2) + '\n'
                f.write(time_range_string)
                time_range_string = str(i) + ' ' + \
                                    str(mdc_coincidence_segment.__getitem__(i).start()) \
                                    + ' ' + str(mdc_coincidence_segment.__getitem__(i).end()) \
                                    + ' ' + str(mdc_coincidence_segment.__getitem__(i).end() \
                                                - mdc_coincidence_segment.__getitem__(i).start()) + '\n'
                fmdcseg.write(time_range_string)
            elif (duration > blockTime):
                # ---- this should not be possible
                print >> sys.stderr, "Error: something has gone wrong in creating MDC segment list "
                sys.exit(1)

        f.close()
        fmdcseg.close()

    # ---- Status message.
    print >> sys.stdout, "... finished writing MDC event files."
    print >> sys.stdout

    # -------------------------------------------------------------------------
    #                Write log files for  off-source MDCs.
    # -------------------------------------------------------------------------

    # ---- Now we know which mdc log files we will need lets cat them to create
    #      a single mdc log file containing all the injections we will analyse
    # ---- Status message.
    print >> sys.stdout, "Writing off-source MDC log files ...          "

    mdc_log_file_concat = []
    for setIdx in range(len(mdc_sets)):
        set = mdc_sets[setIdx]
        mdc_log_file_concat.append('input/injection_' + set + '.txt')

        # ---- loop over the mdc blocks we will analyse
        for i in range(mdc_coincidence_segment.__len__()):
            mdc_start_time = mdc_coincidence_segment.__getitem__(i).start()

            for mdc_log_file in mdc_log_files[setIdx]:
                if mdc_log_file.count(str(mdc_start_time)):
                    command = 'cat ' + mdc_log_file + ' >> ' + mdc_log_file_concat[setIdx]
                    os.system(command)

    # ---- Status message.
    print >> sys.stdout, "... finished writing off-source MDC event file."
    print >> sys.stdout

# -------------------------------------------------------------------------
#    Make coincidence segment list for on-source, zero-lag segment.
# -------------------------------------------------------------------------

# ---- Status message.
print >> sys.stdout, "Writing on-source event file ...          "

# ---- Now make segment lists for coincidence operation.  First determine
#      segment list for zero lag, and verify that the on-source time is
#      contained by a segment, else quit with error.
# ---- On source period: +/- minimumSegmentLength / 2 around trigger time.
on_source_start_time = int(trigger_time + onSourceBeginOffset - transientTime)
on_source_end_time = int(trigger_time + onSourceEndOffset + transientTime)

# ---- Write time range to a temporary segment file named on_source_interval.txt.
#      We'll then read this file into a ScienceData object.  It's a hack, but
#      it seems that the only way to populate ScienceData objects is to read
#      segments from a file.
f = open('input/on_source_interval.txt', 'w')
time_range_string = '1 ' + str(on_source_start_time) + ' ' \
                    + str(int(on_source_start_time + onSourceWindowLength)) + ' ' + str(blockTime) + '\n'
f.write(time_range_string)
f.close()

# ---- Read on-source time range into a "ScienceData" object.
on_source_segment = pipeline.ScienceData()
on_source_segment.read('input/on_source_interval.txt', blockTime)

# ---- Now get the intersection of all of the detector segment lists with
#      this on-source list.
coincidence_segment = copy.deepcopy(on_source_segment)
for det in full_segment_list:
    coincidence_segment.intersection(det)

# ---- If on source interval is a coincidence segment, then the intersection of
#      this interval with the "not" coincidence should be empty.
not_coincidence_segment = copy.deepcopy(coincidence_segment)
not_coincidence_segment.invert()
overlap = not_coincidence_segment.intersection(on_source_segment)
if overlap != 0:
    print "Error: on-source period is not a coincidence segment of the specified network."
    for seg in on_source_segment:
        print "on source period:", seg.start(), " ", seg.end()
    for seg in coincidence_segment:
        print "coincidence period:", seg.start(), " ", seg.end()
    sys.exit(1)

# ---- At this point, the ScienceData object on_source_segment contains the
#      on-source zero-lag segment.  Write this to the on-source event file.
f = open('input/event_on_source.txt', 'w')
fseg = open('input/segment_on_source.txt', 'w')

fwin = open('input/window_on_source.txt', 'w')
fwin.write(str(int(trigger_time)) + ' 0' * len(detector) + '\n')
fwin.close()

# ---- Split coincidence segment list into "chunks".
coincidence_segment.make_chunks(blockTime, 2 * transientTime)
if len(coincidence_segment) > 1:
    print "Error: The on source segment should not have holes? This one seem to have holes inside."
    sys.exit(1)

# ---- Generate sky positions for patch about ra, dec at trigger_time.
if int(cp.get('input', 'usexchooseskylocations')) and sky_pos_err:
    skyPosFilename_trigger = 'input/sky_positions_trigger_time.txt'

    if grid_type == 'line':
        print >> sys.stdout, "Calling xchooseskylocations1 to generate ", skyPosFilename_trigger
        xchooseskylocationsCall = ' '.join(["xchooseskylocations1",
                                            str(ra),
                                            str(decl),
                                            str(trigger_time),
                                            str(sky_pos_err),
                                            cp.get('input', 'numSigmaSkyPos'),
                                            siteStrTilde,
                                            cp.get('input', 'delayTol'),
                                            skyPosFilename_trigger,
                                            '0'])

        print >> sys.stdout, xchooseskylocationsCall
        os.system(xchooseskylocationsCall)

    elif grid_type == 'timedelay':
        print >> sys.stdout, "Calling xchoosetimedelays to generate ", skyPosFilename_trigger
        xchoosetimedelaysCall = ' '.join(["xchoosetimedelays",
                                          str(ra),
                                          str(decl),
                                          str(trigger_time),
                                          siteStrTilde,
                                          cp.get('input', 'delayTol'),
                                          skyPosFilename_trigger,
                                          '0'])

        print >> sys.stdout, xchoosetimedelaysCall
        os.system(xchoosetimedelaysCall)

    elif grid_type == 'healpix' or grid_type == 'circular':
        print >> sys.stdout, "Calling xmakeskygrid to generate ", skyPosFilename_trigger
        if ra2 and decl2 and sky_pos_err2:
            ra_str = str(ra) + "~" + str(ra2)
            decl_str = str(decl) + "~" + str(decl2)
            sky_pos_err_str = str(sky_pos_err) + "~" + str(sky_pos_err2)
        else:
            ra_str = str(ra)
            decl_str = str(decl)
            sky_pos_err_str = str(sky_pos_err)
        xmakeskygridCall = ' '.join(["xmakeskygrid", ra_str, decl_str,
                                     str(trigger_time), sky_pos_err_str, cp.get('input', 'numSigmaSkyPos'),
                                     siteStrTilde, cp.get('input', 'delayTol'), skyPosFilename_trigger,
                                     grid_type, '0'])
        print >> sys.stdout, xmakeskygridCall
        os.system(xmakeskygridCall)

    elif grid_type == 'file':
        print >> sys.stdout, "Calling xconvertfilegrid to generate ", skyPosFilename_trigger
        xconvertfilegridCall = ' '.join(
            ['xconvertfilegrid', str(sky_pos_err), str(trigger_time), skyPosFilename_trigger])
        print >> sys.stdout, xconvertfilegridCall
        os.system(xconvertfilegridCall)

    elif grid_type == 'ipn':
        print >> sys.stdout, "Error: IPN grids are currently unsupported. Please use circular or line instead."
        sys.exit(1)

    elif grid_type == 'opt':
        print >> sys.stdout, "Error: Optimized position grids are currently unsupported. Please use circular or line instead."
        sys.exit(1)

    else:
        print >> sys.stdout, "Error: Choice of sky position grid is unrecognized. Please use circular or line."
        sys.exit(1)

seg = coincidence_segment[0]
for iSeg in range(len(seg)):
    # ---- Write event to event file.
    time_range_string = str((seg.__getitem__(iSeg).start() + \
                             seg.__getitem__(iSeg).end()) / 2) + \
                        ' 0' * len(detector) + '\n'
    f.write(time_range_string)
    # ---- Write segment to segment file.
    time_range_string = '0 ' + str(int(seg.__getitem__(iSeg).start())) \
                        + ' ' + str(int(seg.__getitem__(iSeg).end())) \
                        + ' ' + str(int(seg.__getitem__(iSeg).end() \
                                        - seg.__getitem__(iSeg).start())) + '\n'
    fseg.write(time_range_string)
    gpsBlockCenterTime = (seg.__getitem__(iSeg).start() + seg.__getitem__(iSeg).end()) / 2

    # ---- If user has set usexchooseskylocations flag to 1 in params file we now
    #      compute a list of sky positions we need to search and write these to a
    #      file.
    if int(cp.get('input', 'usexchooseskylocations')) and sky_pos_err:
        skyPosFilename = 'input/sky_positions_' + str(iSeg) + '.txt'
        print >> sys.stdout, "Calling xconvertskylocations to generate ", skyPosFilename
        xconvertskylocationsCall = ' '.join(["xconvertskylocations",
                                             str(skyPosFilename_trigger),
                                             str(trigger_time),
                                             str(gpsBlockCenterTime),
                                             skyPosFilename])
        print >> sys.stdout, xconvertskylocationsCall
        os.system(xconvertskylocationsCall)

        # ---- Check that the output file has been created.
        if not os.path.isfile(skyPosFilename):
            print >> sys.stderr, "Error creating ", skyPosFilename
            sys.exit(1)

        # ---- Count number of sky positions.
        numSky = len(open(skyPosFilename).readlines())

        # ---- Set skyPositionList arg that will be written to matlab format
        #      parameters files.
        skyPositionList = skyPosFilename

    # ---- If user has not specified a sky position error we will search only a
    #      single sky position.
    else:
        # ---- Convert right ascension, declination to Earth-fixed coordinates.
        print >> sys.stdout, "Calling xconvertgrbtoearth ..."
        xconvert_command = ' '.join([
            "xconvertgrbtoearth",
            "input/earthfixedcoordinates" + str(iSeg) + ".txt",
            str(ra), str(decl), str(gpsBlockCenterTime)])
        os.system(xconvert_command)
        # ---- Load earth-fixed coordinates back in.
        fEarthFixed = open('input/earthfixedcoordinates' + str(iSeg) + '.txt', 'r')
        phitheta = fEarthFixed.read()
        fEarthFixed.close()
        phithetaList = phitheta.split(' ')
        phi = float(phithetaList[0])
        theta = float(phithetaList[1])
        print >> sys.stdout, "GRB position in Earth-fixed coordinates (rad):"
        print >> sys.stdout, "    phi = ", phi
        print >> sys.stdout, "    theta = ", theta

        # ---- Set number of sky positions.
        numSky = 1

        # ---- Set skyPositionList arg that will be written to matlab format
        #      parameters files.
        skyPositionList = '[' + str(theta) + ',' + str(phi) + ']'

    # ---- Parameters file for on-source analysis.
    fParam = open('input/parameters_on_source_' + str(iSeg) + '.txt', 'w')
    # ---- First write framecache file, channel file, event file, and sky position.
    fParam.write('channelFileName:input/channels.txt' + '\n')
    fParam.write('frameCacheFile:' + frameCacheAll + '\n')
    fParam.write('eventFileName:input/event_on_source.txt' + '\n')
    fParam.write('skyPositionList:' + skyPositionList + '\n')
    fParam.write('skyCoordinateSystem:earthfixed' + '\n')
    fParam.write('likelihoodtype:' + likelihoodTypeStr + '\n')
    # ---- Now write all of the other parameters from the parameters section.
    #      We ignore the likelihoodType_* lines since this is handled above.
    for i in range(0, len(parameters)):
        if not (parameters[i].startswith("likelihoodtype")):
            value = cp.get('parameters', parameters[i])
            if parameters[i] == "onsourceendoffset":
                fParam.write('onsourceendoffset:' + str(onSourceEndOffset) + '\n')
            elif parameters[i] == "circtimeslidestep":
                continue
            else:
                fParam.write(parameters[i] + ':' + value + '\n')
    if outputType == 'seedless':
        fParam.write('seedlessparams:input/seedless_onsource.txt\n')
    fParam.close()

    # ---- Parameters file for ul-source analysis.
    fParam = open('input/parameters_ul_source_' + str(iSeg) + '.txt', 'w')
    # ---- First write framecache file, channel file, event file, and sky position.
    fParam.write('channelFileName:input/channels.txt' + '\n')
    fParam.write('frameCacheFile:' + frameCacheAll + '\n')
    fParam.write('eventFileName:input/event_on_source.txt' + '\n')
    fParam.write('skyPositionList:' + skyPositionList + '\n')
    fParam.write('skyCoordinateSystem:earthfixed' + '\n')
    fParam.write('likelihoodtype:' + likelihoodTypeStr + '\n')
    # ---- Now write all of the other parameters from the parameters section.
    #      We ignore the likelihoodType_* lines since this is handled above.
    for i in range(0, len(parameters)):
        if not (parameters[i].startswith("likelihoodtype") or parameters[i].endswith("ecimateRate")):
            value = cp.get('parameters', parameters[i])
            if parameters[i] == "onsourceendoffset":
                fParam.write('onsourceendoffset:' + str(onSourceEndOffset) + '\n')
            elif parameters[i] == "circtimeslidestep":
                continue
            else:
                fParam.write(parameters[i] + ':' + value + '\n')
    fParam.write('decimateRate:100\n')
    fParam.write('superDecimateRate:100\n')
    if outputType == 'seedless':
        fParam.write('seedlessparams:input/seedless_ul.txt\n')
    fParam.close()

    # ---- Parameters file for off-source analysis.
    fParam = open('input/parameters_off_source_' + str(iSeg) + '.txt', 'w')
    # ---- First write framecache file, channel file, event file, and sky position.
    fParam.write('channelFileName:input/channels.txt' + '\n')
    fParam.write('frameCacheFile:' + frameCacheAll + '\n')
    fParam.write('eventFileName:input/event_off_source.txt' + '\n')
    fParam.write('skyPositionList:' + skyPositionList + '\n')
    fParam.write('skyCoordinateSystem:earthfixed' + '\n')
    fParam.write('likelihoodtype:' + likelihoodTypeStr + '\n')
    # ---- Now write all of the other parameters from the parameters section.
    #      We ignore the likelihoodType_* lines since this is handled above.
    for i in range(0, len(parameters)):
        if not (parameters[i].startswith("likelihoodtype")):
            value = cp.get('parameters', parameters[i])
            if parameters[i] == "onsourceendoffset":
                fParam.write('onsourceendoffset:' + str(onSourceEndOffset) + '\n')
            else:
                fParam.write(parameters[i] + ':' + value + '\n')
    if outputType == 'seedless':
        fParam.write('seedlessparams:input/seedless_offsource.txt\n')
    fParam.close()

    # ---- Parameter files for on-the-fly simulated waveform analyses, if requested.
    if cp.has_section('waveforms'):
        # ---- Read [injection] parameters.  If waveform_set is empty then no
        #      files will be written.
        waveform_set = cp.options('waveforms')
        # ---- Write one parameters file for each (waveform set, injection scale) pair.
        for set in waveform_set:
            if cp.has_section(set) & cp.has_option(set, 'injectionScales'):
                # ---- This check lets you specify different injection scales and
                #      spacing for each waveform set.
                injectionScalesList = cp.get(set, 'injectionScales')
                injectionScales = injectionScalesList.split(',')
            else:
                # ---- Otherwise, use the injection scales and spacing specified in
                #      the [injection] section.
                injectionScalesList = cp.get('injection', 'injectionScales')
                injectionScales = injectionScalesList.split(',')

            # ---- If we do long injections we will have one single parameter file
            if longInjections == True:
                fParam = open("input/parameters_simulation_" + set + "_0_" + str(iSeg) + ".txt", 'w')
                # ---- First write framecache file, channel file, event file, and sky position.
                fParam.write('channelFileName:input/channels.txt' + '\n')
                fParam.write('frameCacheFile:' + frameCacheAll + '\n')
                fParam.write('eventFileName:input/event_inj_source.txt' + '\n')
                fParam.write('catalogdirectory:input/' + '\n')
                fParam.write('skyPositionList:' + skyPositionList + '\n')
                fParam.write('skyCoordinateSystem:earthfixed' + '\n')
                fParam.write('likelihoodtype:' + likelihoodTypeStr + '\n')
                # ---- Now write all of the other parameters from the parameters section.
                #      We ignore the likelihoodType_* lines since this is handled above.
                for i in range(0, len(parameters)):
                    if not (parameters[i].startswith("likelihoodtype")):
                        value = cp.get('parameters', parameters[i])
                        if parameters[i] == "outputtype" and value == "clusters" and not (disableFastInjections):
                            fParam.write('outputtype:injectionclusters\n')
                        elif parameters[i] == "onsourceendoffset":
                            fParam.write('onsourceendoffset:' + str(onSourceEndOffset) + '\n')
                        elif parameters[i] == "circtimeslidestep":
                            continue
                        else:
                            fParam.write(parameters[i] + ':' + value + '\n')

                # ---- Write simulations info.  The specified injection file
                #      will be written later.
                fParam.write('injectionFileName:input/injection_' + set + '.txt' + '\n')
                fParam.write('injectionScale:' + str(injectionScalesList[:]) + '\n')
                # fParam.write('catalogdirectory:' + XPIPELINE_ROOT  + '/waveforms\n')
                if outputType == 'seedless':
                    fParam.write('seedlessparams:input/seedless_simulation.txt\n')
                fParam.close()
            else:
                # ---- If not long inj, write a separate parameter file for each injection scale.
                scale_counter = 0
                for injectionScale in injectionScales:
                    fParam = open(
                        "input/parameters_simulation_" + set + "_" + str(scale_counter) + "_" + str(iSeg) + ".txt", 'w')
                    # ---- First write framecache file, channel file, event file, and sky position.
                    fParam.write('channelFileName:input/channels.txt' + '\n')
                    fParam.write('frameCacheFile:' + frameCacheAll + '\n')
                    fParam.write('eventFileName:input/event_inj_source.txt' + '\n')
                    fParam.write('catalogdirectory:input/' + '\n')
                    fParam.write('skyPositionList:' + skyPositionList + '\n')
                    fParam.write('skyCoordinateSystem:earthfixed' + '\n')
                    fParam.write('likelihoodtype:' + likelihoodTypeStr + '\n')
                    # ---- Now write all of the other parameters from the parameters section.
                    #      We ignore the likelihoodType_* lines since this is handled above.
                    for i in range(0, len(parameters)):
                        if not (parameters[i].startswith("likelihoodtype")):
                            value = cp.get('parameters', parameters[i])
                            if parameters[i] == "outputtype" and value == "clusters" and not (disableFastInjections):
                                fParam.write('outputtype:injectionclusters\n')
                            elif parameters[i] == "onsourceendoffset":
                                fParam.write('onsourceendoffset:' + str(onSourceEndOffset) + '\n')
                            elif parameters[i] == "circtimeslidestep":
                                continue
                            else:
                                fParam.write(parameters[i] + ':' + value + '\n')

                    # ---- Write simulations info.  The specified injection file
                    #      will be written later.
                    fParam.write('injectionFileName:input/injection_' + set + '.txt' + '\n')
                    fParam.write('injectionScale:' + str(injectionScale) + '\n')
                    # fParam.write('catalogdirectory:' + XPIPELINE_ROOT  + '/waveforms\n')
                    if outputType == 'seedless':
                        fParam.write('seedlessparams:input/seedless_simulation.txt\n')
                    fParam.close()
                    scale_counter = scale_counter + 1

f.close()
fseg.close()

# ---- Status message.
print >> sys.stdout, "... finished writing on-source event file."
print >> sys.stdout

# ---- Append to summary file.
sfile = open(summary_file, 'a')
sfile.write('\t' + str(numSky))
sfile.close()

# -------------------------------------------------------------------------
#    Copy waveform catalogs (if specified) to input/.
# -------------------------------------------------------------------------

if catalog_dir:
    print >> sys.stdout, "Copying waveform catalogs to input/ ..."
    cpCommand = ' '.join(['cp ' + catalog_dir + '/*.mat input/'])
    os.system(cpCommand)
    print >> sys.stdout, "... finished copying waveform catalogs."
    print >> sys.stdout

# -------------------------------------------------------------------------
#    Make off-source coincidence segment lists for all lags.
# -------------------------------------------------------------------------

# ---- Status message.
print >> sys.stdout, "Writing off-source event file ...          "

# ---- First remove the on-source times from all detector segment lists.
off_source_segment = copy.deepcopy(on_source_segment)
off_source_segment.invert()
for det in full_segment_list:
    det.intersection(off_source_segment)

# -------------------------------------------------------------------------
#    Copy waveform catalogs (if specified) to input/.
# -------------------------------------------------------------------------

if catalog_dir:
    print >> sys.stdout, "Copying waveform catalogs to input/ ..."
    cpCommand = ' '.join(['cp ' + catalog_dir + '/*.mat input/'])
    os.system(cpCommand)
    print >> sys.stdout, "... finished copying waveform catalogs."
    print >> sys.stdout

# ---- Keep track of number of off-source events.
numOff = 0

# ---- Make event list and segment list files for the zero-lag off-source times.
f = open('input/window_off_source.txt', 'w')
# ---- Make a temporary copy of the segment lists.
lag_full_segment_list = copy.deepcopy(full_segment_list)
# ---- List of lags for each detector (0 in this case)
line = ' 0' * len(detector)
# ---- Now take coincidence of segment lists.
lag_coincidence_list = copy.deepcopy(lag_full_segment_list[0])
for i in range(1, len(detector)):
    lag_coincidence_list.intersection(lag_full_segment_list[i])
# ---- Split coincidence segment list into "chunks".
lag_coincidence_list.make_chunks(onSourceWindowLength, 2 * transientTime)
for seg in lag_coincidence_list:
    for i in range(len(seg)):
        # ---- Write event to event file.
        time_range_string = str(int(seg.__getitem__(i).start() - \
                                    onSourceBeginOffset + transientTime)) + line + '\n'
        f.write(time_range_string)
f.close()

# ---- Now open lag file (if any) and write event file for all non-zero lags.
# ---- We'll supply network dependent-defaults.
#      Lag file will have one lag per detector; any of them may be zero.
if lagFile:
    f = open('input/window_off_source.txt', 'a')
    lag_list = open(lagFile, mode='r')
    for line in lag_list:
        # ---- Extract time lag for each detector.
        lags = line.split(None)
        if len(lags) != len(detector):
            print >> sys.stderr, "Error: the lag file should have number of " \
                                 "columns equal to the the number of detectors we are analysing. " \
                                 " Lag file: ", lagFile
            sys.exit(1)
        # ---- Make a time-lagged copy of the segment lists.
        lag_full_segment_list = copy.deepcopy(full_segment_list)
        # ---- Time shift segment list of each detector.
        for i in range(len(detector)):
            for seg in lag_full_segment_list[i]:
                seg.set_start(seg.start() - int(lags[i]))  # -- SUBTRACT lag
                seg.set_end(seg.end() - int(lags[i]))  # -- SUBTRACT lag
        # # ---- Sanity check: dump segments for each ifo to screen.
        # print
        # print "List of analysis segments for each detector", detector, ":"
        # for det_list in lag_full_segment_list:
        #     for seg in det_list:
        #         print seg.start(), seg.end()
        # ---- Now take coincidence of time-lagged segment lists.
        lag_coincidence_list = copy.deepcopy(lag_full_segment_list[0])
        for i in range(1, len(detector)):
            lag_coincidence_list.intersection(lag_full_segment_list[i])
        # ---- Split coincidence segment list into "chunks".
        lag_coincidence_list.make_chunks(onSourceWindowLength, 2 * transientTime)
        for seg in lag_coincidence_list:
            for i in range(len(seg)):
                time_range_string = str(int(seg.__getitem__(i).start() - \
                                            onSourceBeginOffset + transientTime)) + ' ' + line
                f.write(time_range_string)
    f.close()

# ---- Status message.
print >> sys.stdout, "... finished writing off-source event file."
print >> sys.stdout

# -----------------------------------------------------------------------------
#      Read in off-source event file and check each event passes meets our
#                            network criteria.
# -----------------------------------------------------------------------------
if 1:
    # KLUDGE so that we don't have to reindent the code below

    print >> sys.stdout, "Applying network criteria to our off-source events."

    # ---- Get triggerTimes and timeOffsets for each off-source event.

    # ---- Write file containing off-source event centre times,
    #      trigger_time_off.txt using input/event_off_source.txt.
    awkCommand = ' '.join(["awk",
                           "'{print $1}'",
                           "input/window_off_source.txt",
                           ">", "input/trigger_time_off.txt"])
    os.system(awkCommand)

    # ---- Write file containing off-source event lag times,
    #      time_offsets_off.txt using input/event_off_source.txt.

    awkStr = ''
    for idx in range(0, len(detector)):
        awkStr = awkStr + " \" \" " + " $" + str(idx + 2)

    awkCommand = ' '.join(["awk",
                           "'{print ", awkStr, "}'",
                           "input/window_off_source.txt",
                           ">", "input/time_offsets_off.txt"])
    os.system(awkCommand)

    # ---- Find network for each off-source event using xnetworkselection.m.
    network_outputFile = 'input/xnetworkselection_offsource.dat'

    xnetworkselectionCall = ' '.join(["xnetworkselection",
                                      detectorStr,
                                      "input/trigger_time_off.txt",
                                      "input/time_offsets_off.txt",
                                      cat1_segment_file_list[0],
                                      cat1_segment_file_list[1],
                                      cat1_segment_file_list[2],
                                      cat1_segment_file_list[3],
                                      cat1_segment_file_list[4],
                                      cat2_segment_file_list[0],
                                      cat2_segment_file_list[1],
                                      cat2_segment_file_list[2],
                                      cat2_segment_file_list[3],
                                      cat2_segment_file_list[4],
                                      network_outputFile,
                                      str(onSourceBeginOffset),
                                      str(onSourceEndOffset),
                                      str(transientTime),
                                      str(onSourceWindowLength)
                                      ])

    print >> sys.stdout, xnetworkselectionCall
    os.system(xnetworkselectionCall)

    # ---- Discard off-source events which do not contain the ifos in
    #      our network.

    # ---- Read in event_off_source.txt
    fevents = open('input/window_off_source.txt', 'r')
    events = fevents.readlines()
    fevents.close()

    # ---- Read in network strings from network_outputFile.
    fnetworks = open(network_outputFile, 'r')
    networks = fnetworks.readlines()
    fnetworks.close()

    eventListTempFilename = "input/window_off_source_temp.txt"
    eventListTemp = open(eventListTempFilename, 'w')

    # ---- Check events and networks list have the same length.
    if not (len(events) == len(networks)):
        print >> sys.stderr, "Error: off-source networks and events lists " \
                             "should have the same length"
        sys.exit(1)

    # ---- Number of off-source events before we discard any.
    # ---- This is equivalent to the number of zero and external lags
    # ---- mulitplied by the number of internal lags
    # See xdetection.m line 1045
    internalSlides = 1
    if cp.has_option('parameters', 'circtimeslidestep'):
        circTimeSlides = cp.getint('parameters', 'circtimeslidestep')
        if len(detector) == 1:
            internalSlides = 1
        elif len(detector) == 2:
            internalSlides = np.arange(0, blockTime - 2 * transientTime - circTimeSlides, circTimeSlides).size
        elif len(detector) == 3:
            internalSlides = np.arange(0, blockTime / 2 - transientTime - circTimeSlides, circTimeSlides).size
        else:
            raise ValueError('Circtimeslides not set up for number of detectors given')

    origNumOff = len(events) * internalSlides

    # ---- Keep track of how many off-source jobs we have after
    #     discarding those with bad networks.
    numOff = 0

    # ---- If the user has specified the number of background jobs
    #      get this variable.
    if cp.has_option('background', 'numJobs'):
        background_numJobs = int(cp.get('background', 'numJobs'))
        if background_numJobs > origNumOff:
            print >> sys.stderr, "We have only ", origNumOff, "background jobs"
            print >> sys.stderr, "Error: Specify more lags to get desired " \
                                 "number of background jobs: numJobs = ", background_numJobs
            sys.exit(1)

    elif FAP or FAR:
        if FAP > 50.0:
            background_numJobs = 2 * (100. / (100.0 - FAP))
        elif (FAP > 0) and (FAP < 1):
            background_numJobs = 2 * (100. / FAP)
        else:
            raise ValueError('FAP number unusual, are you sure this is what you want')
        if background_numJobs > origNumOff:
            print >> sys.stderr, "We have only ", origNumOff, "background jobs"
            print >> sys.stderr, "Error: Specify more lags to get desired " \
                                 "number of background jobs: numJobs = ", background_numJobs
            sys.exit(1)
    else:
        background_numJobs = origNumOff

    # ---- Do these strings contain the ifos in the detector list.
    for idx in range(0, len(networks)):
        # ---- For each off-source network we will count how many
        #      ifos from our selected network it contains.
        # ---- We will discard any off-source events whose corresponding
        #      network does not contain all of the ifos in our
        #      selected network.
        numIfo = 0

        # ---- skip network if it is not well determined
        if networks[idx][0] != 'X':
            # ---- Loop over ifos in our selected network.
            for ifo in detector:
                numIfo = numIfo + networks[idx].count(ifo)

        # ---- If the off-source network contains all of the ifos
        #      in our selected network we will write out the details
        #      of the corresponding off-source event to a temporary file.
        if numIfo == len(detector):
            if numOff < background_numJobs:
                eventListTemp.write(events[idx])
                numOff += 1 * internalSlides

    eventListTemp.close()

    # ---- Replace events_off_source.txt with new updated file containing
    #      only those events whose networks contain the ifos in our
    #      selected network.
    mvCommand = ' '.join(['mv',
                          eventListTempFilename,
                          'input/window_off_source.txt'])
    os.system(mvCommand)

    print >> sys.stdout, "We retain the " + str(numOff) + " jobs from a total of " + \
                         str(origNumOff) + " off-source jobs that satisfy " \
                                           "our network criteria.\n"

# ---- Append to summary file.
sfile = open(summary_file, 'a')
sfile.write('\t' + str(numOff))
sfile.close()

# ---- If we do not have the required number of off-source jobs tell
#      the user and exit.
if cp.has_option('background', 'numJobs'):
    background_numJobs = int(cp.get('background', 'numJobs'))
    if numOff < background_numJobs:
        print >> sys.stderr, "Error: Specify more lags to get desired " \
                             "number of background jobs: numJobs = ", background_numJobs
        sys.exit(1)

# ---- Split window list into event list
fwin = open('input/window_off_source.txt', 'r')
windowList = fwin.readlines()
fwin.close()

fev = open('input/event_off_source.txt', 'w')
for window in windowList:
    windowWord = window.split()
    for iJob in range(jobsPerWindow):
        time_range_string = str(
            float(windowWord[0]) + onSourceBeginOffset + (blockTime - 2 * transientTime) * (0.5 + iJob))
        for iWord in range(1, len(windowWord)):
            time_range_string = time_range_string + ' ' + windowWord[iWord]
        time_range_string = time_range_string + '\n'
        fev.write(time_range_string)
fev.close()

# -----------------------------------------------------------------------------
#                   Find data frames, if necessary.
# -----------------------------------------------------------------------------

# ---- If dataFrameCache is specified and exists we will add it to frameCacheAll
if dataFrameCache:
    # ---- check the frameCache specified actually exists
    if not os.path.isfile(dataFrameCache):
        print >> sys.stderr, "Error: non existant framecache: ", dataFrameCache
        sys.exit(1)

    # ---- if the specified mdc frame cache exists then concat it other frame caches
    command = 'cat ' + dataFrameCache + '  >> ' + frameCacheAll
    os.system(command)

# ---- If dataFrameCache is not specified in the config file, then call dataFind
#      for each detector, and convert to readframedata-formatted framecache file.
else:
    # ---- Status message.
    print >> sys.stdout, "Writing framecache file for ifo data..."
    os.system('rm -f framecache_temp.txt')
    # ---- Loop over detectors.
    for i in range(0, len(detector)):
        # ---- Construct dataFind command.
        dataFindCommand = ' '.join([datafind_exec, \
                                    "--server", datafind_server, \
                                    "--observatory", detector[i][0], \
                                    "--type", frameType[i], \
                                    "--gps-start-time", str(start_time), \
                                    "--gps-end-time", str(end_time), \
                                    "--url-type file", "--gaps", "--lal-cache > lalcache.txt 2> ligo_data_find.err"])
        # ---- Issue dataFind command.
        print "calling dataFind:", dataFindCommand
        os.system(dataFindCommand)
        os.system('cat ligo_data_find.err')
        print "... finished call to dataFind."
        # ---- Convert lalframecache file to readframedata format.
        print "calling convertlalcache:"
        os.system('convertlalcache.pl lalcache.txt framecache_temp.txt')
        os.system('cat framecache_temp.txt >> ' + frameCacheAll)
        print "... finished call to convertlalcache."

        # ---- Read stderr log of ligo_data_find to see if there are any gaps in the frames.
        f = open('ligo_data_find.err', 'r')
        gaps_str = f.read()
        f.close()
        # ---- Note: the format of the ligo_data_find.err file depends on which data find executable
        #      we are using. If we're using ligo_data_find then the error file is always non-empty,
        #      due to a deprecation warning message. Strip this out before checking for gaps.
        if datafind_exec == 'ligo_data_find':
            # ---- File contains two lines of the form
            #        Warning: ligo_data_find has been deprecated in favour of gw_data_find, please consider using that executable, which takes the same arguments, and returnes the same results
            #        missing segments: [segment(866386702, 866393054), ..., segment(866477785, 866488107)]
            #      The code below is not expecting the warning message. Strip it out before
            #      continuing.
            print >> sys.stdout, "Attempting to parse gaps file for ligo_data_find"
            os.system('awk \'{ if (NR>1) print $0 }\' ligo_data_find.err > ligo_data_find_trimmed.err')
            os.system('mv ligo_data_find_trimmed.err ligo_data_find.err')
            # ---- Re-read error file -- it may be empty (the warning may have been the only line).
            f = open('ligo_data_find.err', 'r')
            gaps_str = f.read()
            f.close()
        os.system('rm ligo_data_find.err')

        # ---- Check to see if any of the missing frames overlap with our analysis segments.
        #      If they do, remove the times with missing frames from the segment lists.
        if gaps_str:
            # ---- The format of the ligo_data_find.err file depends on which data find executable
            #      we are using. Check which it is and act appropriately.
            if datafind_exec == 'ligo_data_find':
                # ---- (trimmed) File contains one line of the form
                #          missing segments: [segment(866386702, 866393054), ..., segment(866477785, 866488107)]
                # ---- Now proceed in confidence.
                gaps_str = gaps_str.replace('segment', 'segments.segment')
                # ---- Strip out segment list from the strerr log of ligo_data_find
                gaps_segments_str = 'segments.segmentlist(' + gaps_str[
                                                              gaps_str.index('['): gaps_str.index(']') + 1] + ')'
                # ---- Read gap segments into segment list
                gaps_segments = eval(gaps_segments_str)
                gaps_segments.coalesce()
                # ---- Need to write out these gap segments so we can read them
                #      in again as ScienceData object, we really should choose
                #      one type of segment object and use it everywhere.
                f = open("gaps.txt", "w");
                tosegwizard(f, gaps_segments);
                f.flush();
                f.close()
            elif datafind_exec == 'gw_data_find':
                # ---- File is of the form
                #        Missing segments:
                #        866386702.000000 866393054.000000
                #        866396828.000000 866404754.000000
                #        866410903.000000 866412664.000000
                #        866413722.000000 866415440.000000
                #        866477785.000000 866488107.000000
                #      Use awk to turn this into a file with the segwizard format of gaps.txt generated above.
                awkcmdfile_str = '{ if (NR==1) print \"# seg start stop duration\"; else if ($2==int($2)) print NR-2, int($1), int($2), int($2)-int($1); else print NR-2, int($1), int($2)+1, int($2)-int($1)+1}'
                awkfile = open('./awkfile', 'w')
                awkfile.write(awkcmdfile_str)
                awkfile.close()
                os.system('awk -f awkfile ligo_data_find.err > gaps.txt')
                os.system('rm awkfile')
            else:
                print >> sys.stderr, "Error: Do not know how to process gaps file produced by " + datafind_exec
                sys.exit(17)
            # ---- Need to write out these gap segments so we can read them
            #      in again as ScienceData object, we really should choose
            #      one type of segment object and use it everywhere.
            gaps_segments = pipeline.ScienceData()
            gaps_segments.read('gaps.txt', 0)
            os.system('rm gaps.txt')
            # ---- Identify any overlap between missing frames and full_segment_list
            gaps_segments.intersection(full_segment_list[i])
            if gaps_segments:
                print >> sys.stderr, "Error: missing frames in ", detector[i]
                for jj in range(gaps_segments.__len__()):
                    time_range_string = str(jj) + ' ' + \
                                        str(gaps_segments.__getitem__(jj).start()) \
                                        + ' ' + str(gaps_segments.__getitem__(jj).end()) \
                                        + ' ' + str(gaps_segments.__getitem__(jj).end() \
                                                    - gaps_segments.__getitem__(jj).start())
                    print time_range_string
                sys.exit(1)

    # ---- Clean up.
    os.system('rm -f framecache_temp.txt lalcache.txt')
    # ---- Set dataFrameCache variable to point to our new file.
    dataFrameCache = frameCacheAll
    # ---- Status message.
    print >> sys.stdout, "... finished writing framecache file for ifo data"
    print >> sys.stdout

# -------------------------------------------------------------------------
#      Write injection files for on-the-fly simulations, if needed.
# -------------------------------------------------------------------------

# ---- construct time segment(s) into which to injecting, choice between on-source and off-source injections
if offSourceInj:
    # ---- Off-source injections
    os.system('cp input/window_off_source.txt input/window_inj_source.txt')
    os.system('cp input/event_off_source.txt input/event_inj_source.txt')
else:
    # ---- On-source injections
    os.system('cp input/window_on_source.txt input/window_inj_source.txt')
    os.system('cp input/event_on_source.txt input/event_inj_source.txt')
injTimeRangeStr = ""
injTimeOffsetStr = ""
injCenterTime = []
injwindows = loadtxt('input/window_inj_source.txt')
event_inj_list = loadtxt('input/event_inj_source.txt')
if injwindows.ndim == 1:
    injwindows = [injwindows]
if event_inj_list.ndim == 1:
    event_inj_list = [event_inj_list]
for iEv in range(0, len(injwindows)):
    # ---- skip time-slid off-source, assume they are only at the top of
    #      the window list, this assumption is used later in the code
    if sum(abs(injwindows[iEv][1:])) > 0:
        break
    injTimeRangeStr = injTimeRangeStr + str(injwindows[iEv][0] + onSourceBeginOffset) + \
                      '~' + str(injwindows[iEv][0] + onSourceEndOffset) + '~'
    injTimeOffsetStr = injTimeOffsetStr + str(int(trigger_time) - injwindows[iEv][0]) + '~'
    injCenterTime.append(injwindows[iEv][0])
# remove trailing tilde
injTimeRangeStr = injTimeRangeStr[:-1]
injTimeOffsetStr = injTimeOffsetStr[:-1]

if cp.has_section('waveforms'):
    # ---- Read [injection] parameters.
    waveform_set = cp.options('waveforms')
    injectionInterval = cp.get('injection', 'injectionInterval')
    # ---- If we have second error circle, then adjust injectionInterval by a
    #      factor of 2 to put half the injections in each circle.
    if ra2 and decl2:
        injectionInterval_num = float(injectionInterval)
        if injectionInterval_num > 0:
            injectionInterval_num = 2 * injectionInterval_num
        elif injectionInterval_num < 0:
            injectionInterval_num = int(injectionInterval_num / 2)
        else:
            print >> sys.stderr, "Error: injectionInterval == 0"
            sys.exit(1)
        injectionInterval = str(injectionInterval_num)
    print >> sys.stdout, "Making injection files ..."
    for set in waveform_set:
        waveforms = cp.get('waveforms', set)
        baseinjfilename = "injection_" + set + ".txt"
        injfilename = "input/injection_" + set + ".txt"

        # ---- Use premade injection files if they exist [SARAH]
        if waveforms == baseinjfilename:
            command = ' '.join(["cp ", baseinjfilename, " input/"])
            os.system(command)
            print >> sys.stdout, "    Using-premade injection file:", injfilename

        # ---- setUpJobs script that was here before [SARAH]
        else:
            # ---- Construct command to make injection file for this waveform set.
            if ra2 and decl2:
                # ---- Call injection code twice, once for each error circle.
                # ---- Command to make injection file for first error circle.
                # ---- Wrap waveforms string in single quotes to escape any ; characters,
                #      which are used for generating random injection parameters.
                tmpwaveforms = ''.join(["'", waveforms, "'"])
                make_injection_file_command = ' '.join(["xmakegrbinjectionfile",
                                                        "circle1.txt", tmpwaveforms,
                                                        injTimeRangeStr,
                                                        injTimeOffsetStr,
                                                        injectionInterval, str(ra), str(decl), str(seed), grid_type,
                                                        grid_sim_file])
                # ---- Issue command to make injection file for this waveform set.
                print >> sys.stdout, "make_injection_file_command:", make_injection_file_command
                os.system(make_injection_file_command)
                # ---- Make and issue command to jitter injection file.
                #      Note that for the two-circle case we assume the sky position
                #      to be lognormal distributed.  If injdistrib, injdistrib2 are
                #      not specified then no jittering is done.
                if injdistrib:
                    jitter_injection_command = ' '.join(["xjitterinjectionskypositions",
                                                         "circle1.txt",
                                                         "circle1.txt",
                                                         injdistrib])
                print >> sys.stdout, "    Jittering: ", "circle1.txt"
                print >> sys.stdout, jitter_injection_command
                os.system(jitter_injection_command)
                # ---- Command to make injection file for second error circle.
                # ---- Wrap waveforms string in single quotes to escape any ; characters,
                #      which are used for generating random injection parameters.
                tmpwaveforms = ''.join(["'", waveforms, "'"])
                make_injection_file_command = ' '.join(["xmakegrbinjectionfile",
                                                        "circle2.txt", tmpwaveforms,
                                                        injTimeRangeStr,
                                                        injTimeOffsetStr,
                                                        injectionInterval, str(ra2), str(decl2), str(seed + 1),
                                                        grid_type, grid_sim_file])
                # ---- Issue command to make injection file for this waveform set.
                print >> sys.stdout, "make_injection_file_command:", make_injection_file_command
                os.system(make_injection_file_command)
                # ---- Make and issue command to jitter injection file.
                #      Note that for the two-circle case we assume the sky position
                #      to be lognormal distributed.  If injdistrib, injdistrib2 are
                #      not specified then no jittering is done.
                if injdistrib2:
                    jitter_injection_command = ' '.join(["xjitterinjectionskypositions",
                                                         "circle2.txt",
                                                         "circle2.txt",
                                                         injdistrib2])
                    print >> sys.stdout, "    Jittering: ", "circle2.txt"
                    print >> sys.stdout, jitter_injection_command
                    os.system(jitter_injection_command)
                # ---- Combine into a single file.
                combine_command = ' '.join(["sort -m circle1.txt circle2.txt >", injfilename])
                os.system(combine_command)
                os.system("rm circle1.txt circle2.txt")
            else:
                # ---- Wrap waveforms string in single quotes to escape any ; characters,
                #      which are used for generating random injection parameters.
                tmpwaveforms = ''.join(["'", waveforms, "'"])
                make_injection_file_command = ' '.join(["xmakegrbinjectionfile",
                                                        injfilename, tmpwaveforms,
                                                        injTimeRangeStr,
                                                        injTimeOffsetStr,
                                                        injectionInterval, str(ra), str(decl), str(seed), grid_type,
                                                        grid_sim_file])
                # ---- Issue command to make injection file for this waveform set.
                # ---- We'll overwrite this file later with miscalibrated and/or
                #      jittered versions, if desired.
                print >> sys.stdout, "    Writing :", injfilename
                print >> sys.stdout, make_injection_file_command
                os.system(make_injection_file_command)
                if injdistrib:
                    jitter_injection_command = ' '.join(["xjitterinjectionskypositions",
                                                         injfilename,
                                                         injfilename,
                                                         injdistrib])
                    print >> sys.stdout, "    Jittering: ", injfilename
                    print >> sys.stdout, jitter_injection_command
                    os.system(jitter_injection_command)

        # ---- Apply calibiration uncertainties to injections if required. We use
        #      the real detector (rather than the virtual detector) for determining
        #      calibration uncertainties, as the virtual detector may not have
        #      been operational at the time of the trigger.
        if int(cp.get('injection', 'miscalibrateInjections')) == 1:
            miscalib_injection_command = ' '.join(["xmiscalibrategrbinjectionfile",
                                                   injfilename,
                                                   injfilename,
                                                   detectorStrTilde,
                                                   frameTypeStrTilde])
            print >> sys.stdout, "    Miscalibrating :", injfilename
            print >> sys.stdout, miscalib_injection_command
            os.system(miscalib_injection_command)

    print >> sys.stdout, "... finished making injection files."
    print >> sys.stdout

# -------------------------------------------------------------------------
#      Create ini file for xtmva.py, if required.
# -------------------------------------------------------------------------

# ---- Procedure:
#      -> Copy the xtmva codes from the tmvadir location specified in the grb
#         ini file to a new local directory called xtmvapy. This local copy
#         will be used for the analysis to avoid conflicts if other xtmva
#         analyses are running simultaneously.
#      -> Write a bespoke ini file. Place it in the local run directory since
#         xtmva.py will look for it there.
#      -> To do: add a "post" script to the all_jobs dag that runs xtmva.py.
#         In fact this is probably easier to do in xgrbwebpage.py.
if xtmvaFlag:
    # ---- Extract required data from [xtmva] section.
    if cp.has_section('xtmva'):
        WFtrain = cp.get('xtmva', 'WFtrain')
        classifier = cp.get('xtmva', 'classifier')
        tmvadir = cp.get('xtmva', 'tmvadir')
        # ---- Copy xtmva scripts to the local directory.
        print >> sys.stdout, "Creating ./xtmvapy directory for xtmva analysis."
        os.system('rm -rf xtmvapy')
        os.system('mkdir xtmvapy')
        os.system('cp ' + tmvadir + '/*.* xtmvapy')
        # ---- Write ini file.
        print >> sys.stdout, "Generating ini file for xtmva analysis."
        xtmvainifile = open('./xtmva.ini', 'w')
        inistring = '[Settings]' + '\n'
        xtmvainifile.write(inistring)
        inistring = 'WFtrain=' + WFtrain + '\n'
        xtmvainifile.write(inistring)
        inistring = 'classifier=' + classifier + '\n'
        xtmvainifile.write(inistring)
        inistring = '[Folders]' + '\n'
        xtmvainifile.write(inistring)
        inistring = 'tmvadir=' + os.getcwd() + '/xtmvapy' + '\n'
        xtmvainifile.write(inistring)
        inistring = 'xout=xtmva_' + classifier + '\n'
        xtmvainifile.write(inistring)
        inistring = '[WFtest]' + '\n'
        xtmvainifile.write(inistring)
        if cp.has_section('waveforms'):
            waveform_set = cp.options('waveforms')
            for set in waveform_set:
                # ---- Add all sets to the testing list EXCEPT for the traininiget.
                if not (set == WFtrain):
                    # ---- Read the number of injections from the log file.
                    injfilename = "input/injection_" + set + ".txt"
                    injfile = open(injfilename)
                    injlist = injfile.readlines()
                    ninj = len(injlist)
                    injfile.close()
                    inistring = set + '=' + str(ninj) + '\n'
                    xtmvainifile.write(inistring)
        inistring = '[parameters]' + '\n'
        xtmvainifile.write(inistring)
        inistring = 'likelihoods=' + likelihoodTypeStr + '\n'
        xtmvainifile.write(inistring)
        xtmvainifile.close()
        print >> sys.stdout, " "
    else:
        print >> sys.stdout, "Error: xtmva analysis requested by ini file does not have an [xtmva] section. Exiting."
        sys.exit(4)

# -------------------------------------------------------------------------
#    Preparations for writing dags.
# -------------------------------------------------------------------------

# ---- Status message.
print >> sys.stdout, "Writing job submission files ... "

# ---- Retrieve job retry number from parameters file.
if cp.has_option('condor', 'retryNumber'):
    retryNumber = int(cp.get('condor', 'retryNumber'))
else:
    retryNumber = 0
if smartCluster == True:
    retryNumberClustered = 0

# ---- DAGman log file.
#      The path to the log file for condor log messages. DAGman reads this
#      file to find the state of the condor jobs that it is watching. It
#      must be on a local file system (not in your home directory) as file
#      locking does not work on a network file system.
log_file_on_source = cp.get('condor', 'dagman_log_on_source')
log_file_off_source = cp.get('condor', 'dagman_log_off_source')
if smartCluster == True:
    log_file_on_source_clustered = cp.get('condor', 'dagman_log_on_source') + '_clustered'
    log_file_off_source_clustered = cp.get('condor', 'dagman_log_off_source') + '_clustered'
if cp.has_section('waveforms'):
    log_file_simulations = cp.get('condor', 'dagman_log_simulations')
    if smartCluster == True:
        log_file_simulations_clustered = cp.get('condor', 'dagman_log_simulations') + '_clustered'
if cp.has_option('mdc', 'mdc_sets'):
    log_file_mdcs = cp.get('condor', 'dagman_log_mdcs')

# ---- Make directories to store the log files and error messages
#      from the nodes in the DAG
try:
    os.mkdir('logs')
except:
    pass
# ---- Make directory to store the output of our test job.
#      NOT TO BE DONE FOR PRODUCTION RUNS!
try:
    os.mkdir('output')
except:
    pass
try:
    os.mkdir('output/on_source')
except:
    pass
try:
    os.mkdir('output/ul_source')
except:
    pass
try:
    os.mkdir('output/off_source')
except:
    pass
# ---- now make the same directories only for clustered results.
if smartCluster == True:
    try:
        os.mkdir('output_clustered')
    except:
        pass
    try:
        os.mkdir('output_clustered/on_source')
    except:
        pass
    try:
        os.mkdir('output_clustered/off_source')
    except:
        pass
# ---- Make directories to hold results of injection runs - one for each
#      waveform and injection scale.
if cp.has_section('waveforms'):
    waveform_set = cp.options('waveforms')
    for set in waveform_set:
        # ---- The user can specify different injection scales for each
        #      waveform set by including a section with that name in the ini
        #      file.  Look for one.  If no special section for this waveform,
        #      then use the default injection scales from [injection].
        if cp.has_section(set) & cp.has_option(set, 'injectionScales'):
            injectionScalesList = cp.get(set, 'injectionScales')
            injectionScales = injectionScalesList.split(',')
        else:
            injectionScalesList = cp.get('injection', 'injectionScales')
            injectionScales = injectionScalesList.split(',')
        scale_counter = 0
        for injectionScale in injectionScales:
            try:
                os.mkdir('output/simulations_' + set + '_' + str(scale_counter))
            except:
                pass
            scale_counter = scale_counter + 1
            if smartCluster == True:
                try:
                    os.mkdir('output_clustered/simulations_' + set + '_' + str(scale_counter))
                except:
                    pass
if cp.has_option('mdc', 'mdc_sets'):
    mdc_setsList = cp.get('mdc', 'mdc_sets')
    mdc_sets = mdc_setsList.split(',')
    for set in mdc_sets:
        # ---- The user can specify different injection scales for each
        #      waveform set by including a section with that name in the ini
        #      file.  Look for one.  If no special section for this waveform,
        #      then use the default injection scales from [injection].
        if cp.has_section(set) & cp.has_option(set, 'injectionScales'):
            injectionScalesList = cp.get(set, 'injectionScales')
            injectionScales = injectionScalesList.split(',')
        else:
            injectionScalesList = cp.get('injection', 'injectionScales')
            injectionScales = injectionScalesList.split(',')
        scale_counter = 0
        for injectionScale in injectionScales:
            try:
                os.mkdir('output/simulations_' + set + '_' + str(scale_counter))
            except:
                pass
            scale_counter = scale_counter + 1

# -------------------------------------------------------------------------
#      Prepare xtmva dag.
# -------------------------------------------------------------------------

# ---- We initalise the dag here but do not write it until after all other
#      dags have been written (on-source, off-source, simulations). This is
#      because the xtmva dag is unique in that all other dags must complete
#      before it can run. We fix this dependency by adding all the xmerge
#      jobs as parents to the xtmva job.
if xtmvaFlag:
    print >> sys.stdout, "Writing xtmva dag ... "
    log_file_xtmva = cp.get('condor', 'dagman_log_on_source') + '_xtmva'
    print(log_file_xtmva)
    dag_xtmva = pipeline.CondorDAG(log_file_xtmva + uuidtag)
    dag_xtmva.set_dag_file('grb_xtmva')
    xtmvajob = xcondor.XtmvaJob(cp, len(detector))
    xtmvanode = xcondor.XtmvaNode(xtmvajob)
    xtmvanode.set_retry("1")
    xtmvanode.set_name("xtmva_on_source_" + xtmvanode.get_name())

# -------------------------------------------------------------------------
#      Write on-source dag.
# -------------------------------------------------------------------------

# ---- Create a dag to which we can add jobs.
dag = pipeline.CondorDAG(log_file_on_source + uuidtag)

# ---- Set the name of the file that will contain the DAG.
dag.set_dag_file('grb_on_source')

# ---- Make instance of XsearchJob.
job = xcondor.XsearchJob(cp)

if outputType == 'seedless':
    if doGPUOnSource == "true":
        job = xcondor.XsearchGPUJob(cp)

# ---- Make instance of XmergeJob.
mergejob = xcondor.XmergeJob(cp)
# ---- Put a single merge job node in mergejob.  This job will combine
#      into a single file the output of all of the off-source analysis jobs.
mergenode = xcondor.XmergeNode(mergejob)
if xtmvaFlag:
    xtmvanode.add_parent(mergenode)

# ---- if clustering.
if smartCluster == True:
    print >> sys.stdout, "Writing on-source clustering dag ... "
    print(log_file_on_source_clustered)
    dag_clustered = pipeline.CondorDAG(log_file_on_source_clustered + uuidtag)
    dag_clustered.set_dag_file('grb_on_source_clustered')
    mergeclusteredjob = xcondor.XmergeClusteredJob(cp, len(detector))
    mergeclusterednode = xcondor.XmergeClusteredNode(mergeclusteredjob)

# ---- Make analysis jobs for all segments (currently 1) in the on-source
#      segment list.
segmentList = pipeline.ScienceData()
segmentList.read('input/segment_on_source.txt', blockTime)

# ---- Read the number of chunks from the event list
event_on_file = open('input/event_on_source.txt')
event_on_list = event_on_file.readlines()
nOnEvents = len(event_on_list)
event_on_file.close()

# ---- Read from the parameters file how job results files are to be
#      distributed across nodes, and write that info to a file that
#      will be used by the post-processing scripts.
distributeOnSource = int(cp.get('output', 'distributeOnSource'))
if distributeOnSource == 1:
    jobNodeFileOnSource = cp.get('output', 'jobNodeFileOnSource')
    nodeList = open(jobNodeFileOnSource, 'w')
    nodeList.write("Number_of_detectors %d\n" % (len(detector)))
    for i in range(0, len(detector)):
        nodeList.write("%s\t" % (detector[i]))
    nodeList.write("\n")
    nodeList.write('event_on_source_file ')
    nodeList.write(cwdstr + "/input/event_on_source.txt \n")
    nodeList.write("Injection_file N/A \n")
    nodeList.write('Number_of_jobs ')
    nodeList.write("%d \n" % (len(segmentList)))
    nodeList.write('Number_of_jobs_per_node ')
    nodeList.write("%d \n" % (len(segmentList)))
    nodeList.write(cwdstr + " \n")

# ---- Add one node to the job for each segment to be analysed.
for i in range(len(segmentList)):
    node = xcondor.XsearchNode(job)
    # ---- Parameters file:
    matlab_param_file = cwdstr + "/input/parameters_on_source_" + str(i) + ".txt"
    node.set_param_file(matlab_param_file)
    node.set_x_jobnum(i)
    if distributeOnSource == 1:
        nodeList.write(cwdstr + "/output/on_source" + "/results_%d.mat \n" % (i))
    # ---- On-source results files are always written to the local
    #      output/on_source directory - there are very few such jobs.
    node.set_output_dir(os.path.join(cwdstr + "/output/on_source"))
    node.set_x_injnum('0')
    mergenode.add_parent(node)
    node.set_retry(retryNumber)
    # ---- Prepend human readable description to node name.
    node.set_name("xdetection_on_source_seg" + str(i) + "_" + node.get_name())
    dag.add_node(node)

# ---- Supply remaining XmergeJob node parameters, add job to the dag.
mergenode.set_dir_prefix("on_source/")
mergenode.set_sn_flag("0 " + mergingCutsString)
mergenode.set_retry(retryNumber)
# ---- Prepend human readable description to node name.
mergenode.set_name("xmerge_on_source_" + mergenode.get_name())
dag.add_node(mergenode)

# ---- do the same if clustering.
if smartCluster == True:
    mergeclusterednode.set_dir_prefix("on_source/")
    mergeclusterednode.set_sn_flag("0 " + mergingCutsString)
    mergeclusterednode.set_sc_flag("1")
    mergeclusterednode.set_retry(retryNumberClustered)
    mergeclusterednode.set_name("xmergeclustered_on_source_" + mergeclusterednode.get_name())
    dag_clustered.add_node(mergeclusterednode)

# ---- Write out the submit files needed by condor.
dag.write_sub_files()
# ---- Write out the DAG itself.
dag.write_dag()
# ---- Delete used dag job
del dag
del job
del mergejob
# --- if we cluster
if smartCluster == True:
    dag_clustered.write_sub_files()
    dag_clustered.write_dag()
    del dag_clustered
    del mergeclusteredjob
# --- close on source distribute file
if distributeOnSource == 1:
    nodeList.close()

# -------------------------------------------------------------------------
#      Write ul-source dag.
# -------------------------------------------------------------------------

# ---- Create a dag to which we can add jobs.
dag = pipeline.CondorDAG(log_file_on_source + uuidtag)

# ---- Set the name of the file that will contain the DAG.
dag.set_dag_file('grb_ul_source')

# ---- Make instance of XsearchJob.
job = xcondor.XsearchJob(cp)

if outputType == 'seedless':
    if doGPUUL == "true":
        job = xcondor.XsearchGPUJob(cp)

# ---- Make instance of XmergeJob.
mergejob = xcondor.XmergeJob(cp)
# ---- Put a single merge job node in mergejob.  This job will combine
#      into a single file the output of all of the off-source analysis jobs.
mergenode = xcondor.XmergeNode(mergejob)
if xtmvaFlag:
    xtmvanode.add_parent(mergenode)

# ---- Make analysis jobs for all segments (currently 1) in the on-source
#      segment list.
segmentList = pipeline.ScienceData()
segmentList.read('input/segment_on_source.txt', blockTime)

# ---- Read the number of chunks from the event list
event_on_file = open('input/event_on_source.txt')
event_on_list = event_on_file.readlines()
nOnEvents = len(event_on_list)
event_on_file.close()

# ---- Add one node to the job for each segment to be analysed.
for i in range(len(segmentList)):
    node = xcondor.XsearchNode(job)
    # ---- Parameters file:
    matlab_param_file = cwdstr + "/input/parameters_ul_source_" + str(i) + ".txt"
    node.set_param_file(matlab_param_file)
    node.set_x_jobnum(i)
    # ---- Ul-source results files are always written to the local
    #      output/ul_source directory - there are very few such jobs.
    node.set_output_dir(os.path.join(cwdstr + "/output/ul_source"))
    node.set_x_injnum('0')
    mergenode.add_parent(node)
    node.set_retry(retryNumber)
    # ---- Prepend human readable description to node name.
    node.set_name("xdetection_ul_source_seg" + str(i) + "_" + node.get_name())
    dag.add_node(node)

# ---- Supply remaining XmergeJob node parameters, add job to the dag.
mergenode.set_dir_prefix("ul_source/")
mergenode.set_sn_flag("0 " + mergingCutsString)
mergenode.set_retry(retryNumber)
# ---- Prepend human readable description to node name.
mergenode.set_name("xmerge_ul_source_" + mergenode.get_name())
dag.add_node(mergenode)

# ---- Write out the submit files needed by condor.
dag.write_sub_files()
# ---- Write out the DAG itself.
dag.write_dag()
# ---- Delete used dag job
del dag
del job
del mergejob

# -------------------------------------------------------------------------
#      Write off-source dag.
# -------------------------------------------------------------------------

# ---- Create a dag to which we can add jobs.
dag = pipeline.CondorDAG(log_file_off_source + uuidtag)

# ---- Set the name of the file that will contain the DAG.
dag.set_dag_file('grb_off_source')

# ---- Make instance of XsearchJob.
job = xcondor.XsearchJob(cp)

if outputType == 'seedless':
    if doGPUOffSource == "true":
        job = xcondor.XsearchGPUJob(cp)

# ---- Make instance of XmergeJob.
mergejob = xcondor.XmergeJob(cp)
# ---- Put a single merge job node in mergejob.  This job will combine
#      into a single file the output of all of the off-source analysis jobs.
mergenode = xcondor.XmergeNode(mergejob)
if xtmvaFlag:
    xtmvanode.add_parent(mergenode)

# ---- Load off-source segments.
# segmentList = pipeline.ScienceData()
# segmentList.read( 'input/segment_off_source.txt', blockTime )

# ---- KLUDGE FIX: now we have option of limiting number of
#      background jobs using ini file we should ensure that
#      we only run the correct number of jobs.
event_off_file = open('input/event_off_source.txt')
event_off_list = event_off_file.readlines()
nOffEvents = len(event_off_list)
event_off_file.close()
# ---- END OF KLUDGE FXI

# ---- Read how the user wants the results distributed (over nodes, or not)
#      and record this info to a file.
distributeOffSource = int(cp.get('output', 'distributeOffSource'))
if distributeOffSource == 1:
    nodePath = cp.get('output', 'nodePath')
    onNodeOffSourcePath = cp.get('output', 'onNodeOffSourcePath')
    nNodes = int(cp.get('output', 'nNodes'))
    jobNodeFileOffSource = cp.get('output', 'jobNodeFileOffSource')
    nodeList = open(jobNodeFileOffSource, 'w')
    nodeList.write("Number_of_detectors %d\n" % (len(detector)))
    for i in range(0, len(detector)):
        nodeList.write("%s\t" % (detector[i]))
    nodeList.write("\n")
    nodeList.write('event_off_source_file ')
    nodeList.write(cwdstr + "/input/event_off_source.txt \n")
    nodeList.write("Injection_file N/A \n")
    nodeList.write('Number_of_jobs ')
    nodeList.write("%d \n" % (nOffEvents))
    nJobsPerNode = int(nOffEvents / nNodes) + 1
    nodeList.write('Number_of_jobs_per_node ')
    nodeList.write("%d \n" % (nJobsPerNode))
    nodeOffset = int(cp.get('output', 'numberOfFirstNode'));

# ---- Check how many segments are to be bundled into each job, and create
#      job nodes accordingly.
maxInjNum = int(cp.get('output', 'maxInjNum'))
if cp.has_option('output', 'maxOffNum'):
    maxOffNum = int(cp.get('output', 'maxOffNum'))
else:
    maxOffNum = maxInjNum

# ---- Rescale by the number of sky position so that all jobs have the
#      same length regardless of the number of sky position
maxOffNum = math.ceil(float(maxOffNum) / math.sqrt(float(numSky)))
maxInjNum = math.ceil(float(maxInjNum) / math.sqrt(float(numSky)))

if maxOffNum == 0:
    # ---- Each segment is to be analysed as a separate job.  There may be
    #      a lot of them, so we will check below if the output files are to
    #      be distributed over the cluster nodes.
    for i in range(nOffEvents):
        node = xcondor.XsearchNode(job)
        matlab_param_file = cwdstr + "/input/parameters_off_source.txt"
        node.set_param_file(matlab_param_file)
        node.set_x_jobnum(i)
        if distributeOffSource == 1:
            # ---- Write output result file to a cluster node.
            # ---- Record path to each output result file.  Write results from
            #      nJobsPerNode jobs on each node.
            jobNumber = int(i / nJobsPerNode) + nodeOffset
            while ~(os.path.isdir(nodePath + "%d/" % (jobNumber))) & 1:
                print >> sys.stdout, "Waiting for automount to unmount ...\n"
                time.sleep(10)
            # ---- Write name of node before changing nodes.
            if 0 == i % nJobsPerNode:
                print >> sys.stdout, "Node number %d" % (jobNumber)
                nodeList.write(nodePath + "%d/ \n" % (jobNumber))
                # ---- Create directory for results files.
                fullPath = nodePath + "%d/" % (jobNumber) + \
                           onNodeOffSourcePath + "/off_source"
                if ~(os.path.isdir(fullPath)) & 1:
                    os.makedirs(fullPath)
                else:
                    print >> sys.stdout, "**WARNING** path: " + fullPath \
                                         + " already exists, previous results may be overwritten\n"

            node.set_output_dir(os.path.join(fullPath))
            nodeList.write(fullPath + "/results_%d.mat \n" % (i))
        else:
            # ---- Output file to local output/off_source directory.
            node.set_output_dir(os.path.join(cwdstr + "/output/off_source"))
        node.set_x_injnum('0')
        mergenode.add_parent(node)
        node.set_retry(retryNumber)
        # ---- Prepend human readable description to node name.
        node.set_name("xdetection_off_source_seg" + str(i) + "_" + node.get_name())
        dag.add_node(node)
else:
    # ---- This option bundles together segments so that maxOffNum segments
    #      are analysed by each condor job node.
    #      In this case all output files come back to the local output/off_source
    #      directory.
    nSets = int(math.ceil(float(nOffEvents) / float(maxOffNum)))
    for i in range(nSets):
        node = xcondor.XsearchNode(job)
        matlab_param_file = cwdstr + "/input/parameters_off_source_" + str(
            int(math.floor((jobsPerWindow * i) / nSets))) + ".txt"
        node.set_param_file(matlab_param_file)
        node.set_x_jobnum("%d-" % (i * maxOffNum) + "%d" % (min((i + 1) * maxOffNum - 1, nOffEvents - 1)))
        node.set_output_dir(os.path.join(cwdstr + "/output/off_source"))
        node.set_x_injnum('0')
        mergenode.add_parent(node)
        node.set_retry(retryNumber)
        # ---- Prepend human readable description to node name.
        node.set_name("xdetection_off_source_seg" + str(i) + "_" + node.get_name())
        dag.add_node(node)

# ---- Supply remaining XmergeJob node parameters, add job to the dag.
mergenode.set_dir_prefix("off_source/")
mergenode.set_sn_flag("0 " + mergingCutsString)
mergenode.set_retry(retryNumber)
# ---- Prepend human readable description to node name.
mergenode.set_name("xmerge_off_source_" + mergenode.get_name())
dag.add_node(mergenode)
# ---- do the same if clustering.
if smartCluster == True:
    print >> sys.stdout, "Writing off-source clustered dag ... "
    dag_clustered = pipeline.CondorDAG(log_file_off_source_clustered + uuidtag)
    dag_clustered.set_dag_file('grb_off_source_clustered')
    mergeclusteredjob = xcondor.XmergeClusteredJob(cp, len(detector))
    mergeclusterednode = xcondor.XmergeClusteredNode(mergeclusteredjob)
    mergeclusterednode.set_dir_prefix("off_source/")
    mergeclusterednode.set_sn_flag("0 " + mergingCutsString)
    mergeclusterednode.set_sc_flag("1")
    mergeclusterednode.set_retry(retryNumberClustered)
    mergeclusterednode.set_name("xmergeclustered_off_source_" + mergeclusterednode.get_name())
    dag_clustered.add_node(mergeclusterednode)

# ---- Write out the submit files needed by condor.
dag.write_sub_files()
# ---- Write out the DAG itself.
dag.write_dag()
# ---- Delete used dag and jobs
del dag
del job
del mergejob
# --- Close file recording distribution of off-source results.
if distributeOffSource == 1:
    nodeList.close()
if smartCluster == True:
    dag_clustered.write_sub_files()
    dag_clustered.write_dag()
    del dag_clustered
    del mergeclusteredjob

# -------------------------------------------------------------------------
#      Write on-the-fly simulations dags - one for each waveform set.
# -------------------------------------------------------------------------

# ---- All injection scales for a given waveform set will be handled by a
#      single dag.
if cp.has_section('waveforms'):

    # ---- Read [injection] parameters.
    waveform_set = cp.options('waveforms')

    # ---- Read how distribute results on node and write to file
    distributeSimulation = int(cp.get('output', 'distributeSimulation'))

    if distributeSimulation == 1:
        nodePath = cp.get('output', 'nodePath')
        onNodeSimulationPath = cp.get('output', 'onNodeSimulationPath')
        nNodes = int(cp.get('output', 'nNodes'))
        jobNodeFileSimulationPrefix = cp.get('output', 'jobNodeFileSimulationPrefix')
        nodeOffset = int(cp.get('output', 'numberOfFirstNode'));
        jobNumber = nodeOffset - 1

    # ---- Write one dag for each waveform set.
    for set in waveform_set:
        # ---- The user can specify different injection scales for each
        #      waveform set by including a section with that name in the ini
        #      file.  Look for one.  If no special section for this waveform,
        #      then use the default injection scales from [injection].
        if cp.has_section(set) & cp.has_option(set, 'injectionScales'):
            injectionScalesList = cp.get(set, 'injectionScales')
            injectionScales = injectionScalesList.split(',')
        else:
            injectionScalesList = cp.get('injection', 'injectionScales')
            injectionScales = injectionScalesList.split(',')

        # ---- Create a dag to which we can add jobs.
        dag = pipeline.CondorDAG(log_file_simulations + "_" + set + uuidtag)

        # ---- Set the name of the file that will contain the DAG.
        dag.set_dag_file("grb_simulations_" + set)

        # ---- Make instance of XsearchJob.
        job = xcondor.XsearchJob(cp)

        if outputType == 'seedless':
            if doGPUSimulation == "true":
                job = xcondor.XsearchGPUJob(cp)

        mergejob = xcondor.XmergeJob(cp)

        if smartCluster == True:
            print >> sys.stdout, 'Writing dag for on-the-fly clustered injection set: ' + set
            dag_clustered = pipeline.CondorDAG(log_file_simulations_clustered + "_" + set + uuidtag)
            dag_clustered.set_dag_file("grb_simulations_clustered_" + set)
            mergeclusteredjob = xcondor.XmergeClusteredJob(cp, len(detector))

        # ---- Make analysis jobs for all segments in the on-source segment list.
        #      Read segment list from file.
        segmentList = pipeline.ScienceData()
        segmentList.read('input/segment_on_source.txt', blockTime)

        # ---- Read injection file to determine number of injections
        #      for this set.
        #      Use system call to wc to figure out how many lines are
        #      in the injection file.
        os.system('wc input/injection_' + set + \
                  '.txt | awk \'{print $1}\' > input/' + set + '.txt')
        f = open('input/' + set + '.txt')
        numberOfInjections = int(f.readline())
        f.close()
        os.system('cat input/injection_' + set + \
                  '.txt | awk \'{printf \"%.9f\\n\",$1+$2*1e-9}\'' + \
                  ' > input/gps' + set + '.txt')
        f = open('input/gps' + set + '.txt')
        injection_list_time = f.readlines()
        f.close()

        if longInjections == True:
            # ---- this method appends to an existing trigger file whatever bits of a long
            # waveform are in adjacent segments
            # The functionality is as follows: injection X is done first in segment 0 with parameters_0
            # then if straddling next segment is done in segment 1 with parameters_1 but the results are
            # appended to the existing trigger file
            mergenode = []
            if smartCluster == True:
                mergeclusterednode = []
            for injectionScale in injectionScales:
                mergenode.append(xcondor.XmergeNode(mergejob))
                if smartCluster == True:
                    mergeclusterednode.append(xcondor.XmergeClusteredNode(mergeclusteredjob))
            if not (reUseInj):
                # ---- Set buffer for handling long injections.
                longInjSegBuffer = 0
                if set.startswith('adi-a'):
                    longInjSegBuffer = 20
                if set.startswith('adi-b'):
                    longInjSegBuffer = 6
                if set.startswith('adi-c'):
                    longInjSegBuffer = 132
                if set.startswith('adi-d'):
                    longInjSegBuffer = 74
                if set.startswith('adi-e'):
                    longInjSegBuffer = 43
                if set.startswith('mva'):
                    longInjSegBuffer = 132
                if set.startswith('mediummixed'):
                    longInjSegBuffer = 6
                if set.startswith('longmixed'):
                    longInjSegBuffer = 132
                if set.startswith('ebbh-a'):
                    longInjSegBuffer = 7
                if set.startswith('ebbh-d'):
                    longInjSegBuffer = 4
                if set.startswith('ebbh-e'):
                    longInjSegBuffer = 4

                # ---- simplified method to inject, a la allsky.py
                for iInj in range(numberOfInjections):
                    thisInjSeg = []
                    for i in range(len(segmentList)):
                        if abs(float(event_on_list[i].split(' ')[0]) - float(
                                injection_list_time[iInj])) <= blockTime / 2 - transientTime + longInjSegBuffer:
                            thisInjSeg.append(i)

                    nodeList = []
                    for i in range(len(thisInjSeg)):
                        if thisInjSeg:
                            thisInjSeg.sort()
                            node = xcondor.XsearchNode(job)
                            matlab_param_file = cwdstr + "/input/parameters_simulation_" + set + "_0_" + str(
                                thisInjSeg[i]) + ".txt"
                            node.set_param_file(matlab_param_file)
                            # --- method of grouping together segments for one condor job
                            # node.set_x_jobnum("%d-"%(thisInjSeg[0]) + "%d"%(thisInjSeg[-1]))
                            # --- we use multiple jobs but output written to a common trigger mat file
                            node.set_x_jobnum(thisInjSeg[i])
                            node.set_output_dir(os.path.join(cwdstr + '/output/simulations_' + set + '_'))
                            node.set_x_injnum(str(iInj + 1))
                            for scale_counter in range(len(injectionScales)):
                                mergenode[scale_counter].add_parent(node)
                            node.set_retry(retryNumber)
                            # ---- Prepend human readable description to node name.
                            node.set_name(
                                "xdetection_simulation_" + set + "_inj" + str(iInj + 1) + "_" + node.get_name())
                            if len(thisInjSeg) == 1:
                                # ---- Add job node to dag
                                dag.add_node(node)
                            else:
                                # ---- Add job node to a list for parent-child relation
                                nodeList.append(node)

                    # --- if we have long injections make sure chunks are always added after the previous chunk
                    # --- in order of their segments, so xappendinjection can be applied correctly
                    if len(thisInjSeg) > 1:
                        for j in range(len(thisInjSeg) - 1):
                            parentNode = nodeList[j]
                            childNode = nodeList[j + 1]
                            childNode.add_parent(parentNode)
                            dag.add_node(parentNode)
                        dag.add_node(nodeList[-1])

            # ---- Loop over injection scales.
            for scale_counter in range(len(injectionScales)):
                # ---- Point to already produced injection results if provided.
                if reUseInj:
                    mergenode[scale_counter].set_dir_prefix(mergingCutsPath + '/../output/simulations_' \
                                                            + set + '_' + str(scale_counter) + '/')
                else:
                    mergenode[scale_counter].set_dir_prefix('simulations_' + set + '_' + str(scale_counter) + '/')
                mergenode[scale_counter].set_sn_flag("1 " + mergingCutsString)
                mergenode[scale_counter].set_retry(retryNumber)
                # ---- Prepend human readable description to node name.
                mergenode[scale_counter].set_name("xmerge_simulation_" + set + "_injScale" \
                                                  + str(scale_counter) + "_" + mergenode[scale_counter].get_name())
                dag.add_node(mergenode[scale_counter])
                if smartCluster == True:
                    # ---- Point to already produced injection results if provided.
                    if reUseInj:
                        mergeclusterednode[scale_counter].set_dir_prefix(mergingCutsPath + '/../output/simulations_' \
                                                                         + set + '_' + str(scale_counter) + '/')
                    else:
                        mergeclusterednode[scale_counter].set_dir_prefix(
                            'simulations_' + set + '_' + str(scale_counter) + '/')
                    mergeclusterednode[scale_counter].set_sn_flag("1 " + mergingCutsString)
                    mergeclusterednode[scale_counter].set_sc_flag("1")
                    mergeclusterednode[scale_counter].set_retry(retryNumberClustered)
                    # ---- Prepend human readable description to node name.
                    mergeclusterednode[scale_counter].set_name("xmergeclustered_simulation_" + set + "_injScale" \
                                                               + str(scale_counter) + "_" + mergeclusterednode[
                                                                   scale_counter].get_name())
                    dag_clustered.add_node(mergeclusterednode[scale_counter])
        else:
            # ---- Loop over injection scales.
            scale_counter = 0
            for injectionScale in injectionScales:
                mergenode = xcondor.XmergeNode(mergejob)
                if xtmvaFlag:
                    xtmvanode.add_parent(mergenode)
                if smartCluster == True:
                    mergeclusterednode = xcondor.XmergeClusteredNode(mergeclusteredjob)
                # Skip injection trigger production if path to already available triggers provided
                if not (reUseInj):
                    # ---- Loop over segments
                    for i in range(len(segmentList)):
                        # ---- For debug only
                        # print('We do not have injections that are done at the block border, we use standard GRB injection placing')
                        if 0 == maxInjNum:
                            # ---- Create job node.
                            node = xcondor.XsearchNode(job)
                            # ---- Assign first argument: parameters file
                            matlab_param_file = cwdstr + "/input/parameters_simulation_" \
                                                + set + "_" + str(scale_counter) + '_' + str(i) + ".txt"
                            node.set_param_file(matlab_param_file)
                            # ---- Assign second argument: job (segment) number
                            # node.set_x_jobnum("%d-"%(thisInjSeg[0]) + "%d"%(thisInjSeg[-1]))
                            node.set_x_jobnum(i)
                            # ---- Assign third argument: output directory
                            # ---- Check to see if distributing results files over nodes.
                            if 1 == distributeSimulation & 0 == maxInjNum:
                                # ---- Yes: determine output directories and make sure they exist.
                                #      Record directories in a file.
                                jobNumber = (jobNumber + 1 - nodeOffset) % nNodes + nodeOffset
                                nodeList = open(jobNodeFileSimulationPrefix + '_' + set \
                                                + "_seg%d" % (i) + "_injScale" + injectionScale + '.txt', 'w')
                                nodeList.write("Number_of_detectors %d\n" % (len(detector)))
                                for j in range(0, len(detector)):
                                    nodeList.write("%s\t" % (detector[j]))
                                nodeList.write("\n")
                                nodeList.write('event_simulation_file ')
                                nodeList.write(cwdstr + "/input/event_on_source.txt \n")
                                nodeList.write('Injection_file ')
                                nodeList.write(cwdstr + "/input/injection_" + set + ".txt \n")
                                nodeList.write('Number_of_jobs ')
                                nodeList.write("%d \n" % (numberOfInjections))
                                # nJobsPerNode = int(numberOfInjections/nNodes) + 1
                                nJobsPerNode = numberOfInjections
                                nodeList.write('Number_of_jobs_per_node ')
                                nodeList.write("%d \n" % (nJobsPerNode))
                                # write path for each result file, on each node write results from
                                # nJobsPerNode jobs
                                # jobNumber = int((injectionNumber-1)/nJobsPerNode) + nodeOffset
                                while ~(os.path.isdir(nodePath + "%d/" % (jobNumber))) & 1:
                                    print >> sys.stdout, "Waiting for automount to unmount ...\n"
                                    time.sleep(10)
                                # Write name of node before changing nodes
                                # if 0 == (injectionNumber-1) % nJobsPerNode:
                                print >> sys.stdout, "Node number %d" % (jobNumber)
                                nodeList.write(nodePath + "%d/ \n" % (jobNumber))
                                # Create directory for results files
                                fullPath = nodePath + "%d/" % (jobNumber) + onNodeSimulationPath \
                                           + "simulations_" + set + '_' + str(scale_counter)
                                if ~(os.path.isdir(fullPath)) & 1:
                                    os.makedirs(fullPath)
                                else:
                                    print >> sys.stdout, "**WARNING** path: " + fullPath \
                                                         + " already exists, previous results may be overwritten\n"
                                node.set_output_dir(os.path.join(fullPath))
                                for injectionNumber in range(1, numberOfInjections + 1):
                                    nodeList.write(fullPath + "/results_%d" % (i) \
                                                   + "_%d.mat \n" % (injectionNumber))
                                nodeList.close()
                            else:
                                # ---- No: Set output directory to local.
                                node.set_output_dir(os.path.join(cwdstr + \
                                                                 '/output/simulations_' + set + '_' + str(
                                    scale_counter)))
                                # ---- Assign fourth argument: injection number
                                #      KLUDGE: This will screw up injections if more than
                                #      one segment; injection number iterates only over
                                #      injections that fall within analysis interval.
                            node.set_x_injnum("1-%d" % (numberOfInjections))
                            mergenode.add_parent(node)
                            node.set_retry(retryNumber)
                            # ---- Prepend human readable description to node name.
                            node.set_name("xdetection_simulation_" + set + "_seg" \
                                          + str(i) + "_injScale" + str(scale_counter) + "_" + node.get_name())
                            dag.add_node(node)
                        else:
                            for iWindow in range(len(injCenterTime)):
                                thisSegmentInjStart = 1e10
                                thisSegmentInjNumber = 0
                                for iInj in range(numberOfInjections):
                                    if abs(float(event_inj_list[i + iWindow * jobsPerWindow][0]) - float(
                                            injection_list_time[iInj])) <= blockTime / 2 - transientTime:
                                        thisSegmentInjNumber += 1
                                        thisSegmentInjStart = min(thisSegmentInjStart, iInj)
                                for iInjRange in range(int(math.ceil(float(thisSegmentInjNumber) / float(maxInjNum)))):
                                    node = xcondor.XsearchNode(job)
                                    matlab_param_file = cwdstr + "/input/parameters_simulation_" \
                                                        + set + "_" + str(scale_counter) + "_" + str(i) + ".txt"
                                    node.set_param_file(matlab_param_file)
                                    node.set_x_jobnum(i + iWindow * jobsPerWindow)
                                    node.set_output_dir(os.path.join(cwdstr \
                                                                     + '/output/simulations_' + set + '_' + str(
                                        scale_counter)))
                                    node.set_x_injnum("%d" % (thisSegmentInjStart + iInjRange * maxInjNum + 1) + "-" \
                                                      + "%d" % (thisSegmentInjStart + min((iInjRange + 1) * maxInjNum,
                                                                                          thisSegmentInjNumber)))
                                    mergenode.add_parent(node)
                                    node.set_retry(retryNumber)
                                    # ---- Prepend human readable description to node name.
                                    node.set_name("xdetection_simulation_" + set + "_seg" + \
                                                  str(i + iWindow * jobsPerWindow) + "_injScale" + str(scale_counter) \
                                                  + "_injRange" + str(iInjRange) + "_" + node.get_name())
                                    dag.add_node(node)
                                    # ---- Add job node to the dag.
                # ---- Continue on to the next injection scale.
                # point to already produced injection results if provided
                if reUseInj:
                    mergenode.set_dir_prefix(
                        mergingCutsPath + '/../output/simulations_' + set + '_' + str(scale_counter) + '/')
                else:
                    mergenode.set_dir_prefix('simulations_' + set + '_' + str(scale_counter) + '/')
                mergenode.set_sn_flag("0 " + mergingCutsString)
                mergenode.set_retry(retryNumber)
                # ---- Prepend human readable description to node name.
                mergenode.set_name("xmerge_simulation_" + set + "_injScale" \
                                   + str(scale_counter) + "_" + mergenode.get_name())
                dag.add_node(mergenode)
                if smartCluster == True:
                    # ---- Point to already produced injection results if provided.
                    if reUseInj:
                        mergeclusterednode.set_dir_prefix(mergingCutsPath + '/../output/simulations_' \
                                                          + set + '_' + str(scale_counter) + '/')
                    else:
                        mergeclusterednode.set_dir_prefix('simulations_' + set + '_' + str(scale_counter) + '/')
                    mergeclusterednode.set_sn_flag("1 " + mergingCutsString)
                    mergeclusterednode.set_sc_flag("1")
                    mergeclusterednode.set_retry(retryNumberClustered)
                    # ---- Prepend human readable description to node name.
                    mergeclusterednode.set_name("xmergeclustered_simulation_" + set + "_injScale" \
                                                + str(scale_counter) + "_" + mergeclusterednode.get_name())
                    dag_clustered.add_node(mergeclusterednode)
                scale_counter = scale_counter + 1

        # ---- Write out the submit files needed by condor.
        dag.write_sub_files()
        # ---- Write out the DAG itself.
        dag.write_dag()

        # ---- Delete used dag job
        del dag
        del job
        del mergejob
        if smartCluster == True:
            dag_clustered.write_sub_files()
            dag_clustered.write_dag()
            del dag_clustered
            del mergeclusteredjob

# -------------------------------------------------------------------------
#      Write MDC simulation dags - one for each MDC set.
# -------------------------------------------------------------------------

# ---- All injection scales for a given MDC set will be handled by a
#      single dag.

# ---- Check for MDC sets.
if cp.has_option('mdc', 'mdc_sets'):

    # ---- Status message.
    print >> sys.stdout, "Writing MDC job dag files ... "

    # ---- Get list of MDC sets to process.
    mdc_setsList = cp.get('mdc', 'mdc_sets')
    mdc_sets = mdc_setsList.split(',')

    # ---- Check how many MDC segments are to be bundled into each xdetection job.
    maxMDCSegNum = int(cp.get('output', 'maxMDCSegNum'))

    # ---- Read how the user wants the results distributed (over nodes, or not)
    #      and record this info to a file.
    distributeSimulation = int(cp.get('output', 'distributeSimulation'))
    if distributeSimulation == 1:
        nodePath = cp.get('output', 'nodePath')
        onNodeSimulationPath = cp.get('output', 'onNodeSimulationPath')
        nNodes = int(cp.get('output', 'nNodes'))
        jobNodeFileSimulationPrefix = cp.get('output', 'jobNodeFileSimulationPrefix')
        nodeOffset = int(cp.get('output', 'numberOfFirstNode'));
        jobNumber = nodeOffset - 1

    # ---- Write one dag for each waveform set.
    for set in mdc_sets:
        print 'Writing dag for MDC set:' + set
        if cp.has_section(set) & cp.has_option(set, 'injectionScales'):
            injectionScalesList = cp.get(set, 'injectionScales')
            injectionScales = injectionScalesList.split(',')
        else:
            injectionScalesList = cp.get('injection', 'injectionScales')
            injectionScales = injectionScalesList.split(',')

        # ---- Create a dag to which we can add jobs.
        dag = pipeline.CondorDAG(log_file_simulations + "_" + set + uuidtag)

        # ---- Set the name of the file that will contain the DAG.
        dag.set_dag_file("grb_" + set)

        # ---- Make instance of XsearchJob.
        job = xcondor.XsearchJob(cp)

        # ---- Make instance of XmergeJob. This job will merge the results files
        #      produced by the several analysis nodes.
        mergejob = xcondor.XmergeJob(cp)

        #      Make analysis jobs for all segments in the MDC segment list.
        #      Read segment list from file.
        segFileName = 'input/segment_' + set + '.txt'
        if not os.path.isfile(segFileName):
            print >> sys.stderr, "Error: non existant segment file: ", segFileName
            sys.exit(1)

        segmentList = []
        segmentList = pipeline.ScienceData()
        segmentList.read(segFileName, blockTime)

        # ---- Read ini file to determine number of injections for this set.
        numberOfInjections = int(cp.get(set, 'numberOfChannels'))

        # ---- Loop over injection scales.
        scale_counter = 0
        for injectionScale in injectionScales:
            # ---- Merge all results for a single waveform+injection scale.
            mergenode = xcondor.XmergeNode(mergejob)
            if xtmvaFlag:
                xtmvanode.add_parent(mergenode)

            # ---- Set up of jobs depends on how many injections are to be done
            #      by each job: a fixed number (maxInjNum,maxMDCSegNum), or all
            #      (maxInjNum==0,maxMDCSegNum==0).
            if maxInjNum == 0 and maxMDCSegNum == 0:
                # ---- Each analysis job will analyse any and all injections in
                #      its analysis segment.
                i = 0

                # ---- Create job node.
                node = xcondor.XsearchNode(job)
                # ---- Assign first argument: parameters file
                matlab_param_file = cwdstr + "/input/parameters_" + set \
                                    + "_" + str(scale_counter) + ".txt"
                node.set_param_file(matlab_param_file)
                # ---- Assign second argument: job (segment) number
                node.set_x_jobnum(i)
                # ---- Assign third argument: output directory
                # ---- Check to see if distributing results files over nodes.
                if 1 == distributeSimulation & 0 == maxInjNum:
                    # ---- Yes: determine output directories and make sure they exist.
                    #      Record directories in a file.
                    jobNumber = (jobNumber + 1 - nodeOffset) % nNodes + nodeOffset
                    nodeList = open(jobNodeFileSimulationPrefix + '_' + set \
                                    + "_seg%d" % (i) + "_injScale" + injectionScale + '.txt', 'w')
                    nodeList.write("Number_of_detectors %d\n" % (len(detector)))
                    for j in range(0, len(detector)):
                        nodeList.write("%s\t" % (detector[j]))
                    nodeList.write("\n")
                    nodeList.write('event_simulation_file ')
                    nodeList.write(cwdstr + "/input/event_on_source.txt \n")
                    nodeList.write('Injection_file ')
                    nodeList.write(cwdstr + "/input/injection_" + set + ".txt \n")
                    nodeList.write('Number_of_jobs ')
                    nodeList.write("%d \n" % (numberOfInjections))
                    nJobsPerNode = numberOfInjections
                    nodeList.write('Number_of_jobs_per_node ')
                    nodeList.write("%d \n" % (nJobsPerNode))
                    # write path for each result file, on each node write results from
                    # nJobsPerNode jobs
                    # jobNumber = int((injectionNumber-1)/nJobsPerNode) + nodeOffset
                    while ~(os.path.isdir(nodePath + "%d/" % (jobNumber))) & 1:
                        print >> sys.stdout, "Waiting for automount to unmount ...\n"
                        time.sleep(10)
                    # Write name of node before changing nodes
                    # if 0 == (injectionNumber-1) % nJobsPerNode:
                    print >> sys.stdout, "Node number %d" % (jobNumber)
                    nodeList.write(nodePath + "%d/ \n" % (jobNumber))
                    # Create directory for results files
                    fullPath = nodePath + "%d/" % (jobNumber) + onNodeSimulationPath \
                               + "_" + set + '_' + str(scale_counter)
                    if ~(os.path.isdir(fullPath)) & 1:
                        os.makedirs(fullPath)
                    else:
                        print >> sys.stdout, "**WARNING** path: " + fullPath + \
                                             " already exists, previous results may be overwritten\n"
                    node.set_output_dir(os.path.join(fullPath))
                    for injectionNumber in range(1, numberOfInjections + 1):
                        nodeList.write(fullPath + "/results_%d" % (i) + \
                                       "_%d.mat \n" % (injectionNumber))
                    nodeList.close()
                else:
                    # ---- No: Set output directory to local.
                    node.set_output_dir(os.path.join(cwdstr + \
                                                     '/output/simulations_' + set + '_' + str(scale_counter)))
                # ---- Assign fourth argument: injection number
                #      KLUDGE: This will screw up injections if more than
                #      one segment; injection number iterates only over
                #      injections that fall within analysis interval.
                node.set_x_injnum("1-%d" % (numberOfInjections))
                mergenode.add_parent(node)
                node.set_retry(retryNumber)
                # ---- Prepend human readable description to node name.
                node.set_name("xdetection_simulation_" + set + "_injScale" \
                              + str(scale_counter) + "_" + node.get_name())
                dag.add_node(node)
            # ---- if maxInjNum and maxMDCSegNum not 0
            else:
                # ---- Analyse maxInjNum injections in each job.  In this case output
                #      files will go to the local directory output/simulations_*.
                segJobs = range(int(math.ceil(float(len(segmentList)) / float(maxMDCSegNum))))
                injJobs = range(int(math.ceil(float(numberOfInjections) / float(maxInjNum))))
                for iSegRange in segJobs:
                    for iInjRange in injJobs:
                        node = xcondor.XsearchNode(job)
                        matlab_param_file = cwdstr + "/input/parameters_" + set \
                                            + "_" + str(scale_counter) + ".txt"
                        node.set_param_file(matlab_param_file)

                        if len(segJobs) == 1:
                            # ---- if we only have one segment
                            node.set_x_jobnum('0')
                        else:
                            node.set_x_jobnum("%d" % (iSegRange * maxMDCSegNum) + "-" + \
                                              "%d" % (min((iSegRange + 1) * maxMDCSegNum - 1, len(segmentList) - 1)))

                        node.set_output_dir(os.path.join(cwdstr + '/output/simulations_' \
                                                         + set + '_' + str(scale_counter)))

                        # ---- WARNING - do not set injNum = 0 when running MDCs or
                        #      we will not recreate the channel name properly in xdetection
                        node.set_x_injnum("%d" % (iInjRange * maxInjNum + 1) + "-" \
                                          + "%d" % (min((iInjRange + 1) * maxInjNum, numberOfInjections)))

                        mergenode.add_parent(node)
                        node.set_retry(retryNumber)
                        # ---- Prepend human readable description to node name.
                        node.set_name("xdetection_simulation_" + set + "_seg" \
                                      + str(iSegRange) + "_injScale" + str(scale_counter) \
                                      + "_injRange" + str(iInjRange) + "_" + node.get_name())
                        dag.add_node(node)

            # ---- Add job node to the dag.
            # ---- Continue on to the next injection scale.
            mergenode.set_dir_prefix('simulations_' + set + '_' + str(scale_counter) + '/')
            mergenode.set_sn_flag("0 " + mergingCutsString)
            mergenode.set_retry(retryNumber)
            # ---- Prepend human readable description to node name.
            mergenode.set_name("xmerge_simulation_" + set + "_seg" + \
                               "_injScale" + str(scale_counter) + "_" + mergenode.get_name())
            dag.add_node(mergenode)
            scale_counter = scale_counter + 1

        # ---- end loop over injections scales

        # ---- Write out the submit files needed by condor.
        dag.write_sub_files()
        # ---- Write out the DAG itself.
        dag.write_dag()

        # ---- Delete used dag job
        del dag
        del job
        del mergejob
        # ---- end loop overmdc sets

# -------------------------------------------------------------------------
#      Write xtmva dag.
# -------------------------------------------------------------------------

if xtmvaFlag:
    dag_xtmva.add_node(xtmvanode)
    dag_xtmva.write_sub_files()
    dag_xtmva.write_dag()
    del dag_xtmva
    del xtmvajob

# -------------------------------------------------------------------------
#      Write single dag containing all jobs.
# -------------------------------------------------------------------------

# ---- Use grep to combine all dag files into a single dag, with the
#      PARENT-CHILD relationships listed at the end.
print "Combining all jobs into a single dag ..."
os.system('rm -f grb_alljobs.dag')
os.system('echo "DOT xpipeline_triggerGen.dot" > .dag_temp')
os.system('grep -h -v PARENT *.dag >> .dag_temp')
os.system('grep -h PARENT *.dag >> .dag_temp')
os.system('mv .dag_temp grb_alljobs.dag')

# -------------------------------------------------------------------------
#      Finished.
# -------------------------------------------------------------------------

# ---- Status message.
print >> sys.stdout, "... finished writing job submission files. "
print >> sys.stdout

print >> sys.stdout, "############################################"
print >> sys.stdout, "#           Completed.                     #"
print >> sys.stdout, "############################################"

# ---- Append to summary file.
sfile = open(summary_file, 'a')
sfile.write('\t 1')
sfile.close()

# ---- Exit cleanly
sys.exit(0)


# -------------------------------------------------------------------------
#      Leftover code samples.
# -------------------------------------------------------------------------

# # ---- Make data find job node.
# df_job = pipeline.LSCDataFindJob( 'cache','logs', cp )

# # ---- Make an empty list to hold the datafind jobs.
# df_list = []

# # ---- Loop over detectors and prepare a datafind job for each.
# for ifo in ['H1', 'H2', 'L1']:
#   df = pipeline.LSCDataFindNode( df_job )
#   df.set_start( 700000000 )
#   df.set_end( 700000100 )
#   df.set_observatory( ifo[0] )
#   df.set_type('RDS_R_L1')
#   df.set_post_script('/why/oh/why/oh/why.sh')
#   df.add_post_script_arg(df.get_output())
#   dag.add_node(df)
#   df_list.append(df)

