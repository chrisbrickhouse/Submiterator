#!/usr/bin/python

import os
import re
import sys
import json
import time

TOTAL_NUM = 2
LABEL = 't_foo'
NUM_RESPONSES = 0
LOCK_NAME = '.'+LABEL+'.lock'
DELAY = 300  # in seconds

def read_config(nameofexperimentfiles):
    config_file = nameofexperimentfiles + ".config"

    settings = open(config_file, 'r')
    json_string = settings.read()
    settings.close()
    config_dict = json.loads(re.sub("\n", "", json_string))
    return(config_dict)

def write_config(nameofexperimentfiles,config_dict):
    config_file = nameofexperimentfiles + '.config'
    with open(config_file,'w') as settings:
        json.dump(config_dict,settings)

def prepare(nameofexperimentfiles, output_dir=""):
    """From submiterator.py"""

    dict = read_config(nameofexperimentfiles)

    locationofCLT = os.environ['MTURK_CMD_HOME']

    if not os.path.exists(locationofCLT) or locationofCLT == '/':
        raise Exception("Error: please set your 'MTURK_CMD_HOME' environment variable to your AWS directory.")

    if dict["rewriteProperties"] == "yes":
        old_properties_file = open(locationofCLT + "/bin/mturk.properties", 'r').readlines()
        backup = open(locationofCLT + "/bin/mturk.properties.backup", 'w')
        for line in old_properties_file:
            backup.write(line + '\n')
        backup.close()
        new_properties_file = open(locationofCLT + "/bin/mturk.properties", 'w')
        if (dict["liveHIT"] == "yes"):
            for line in old_properties_file:
                if "://mechanicalturk.sandbox.amazonaws.com/?Service=AWSMechanicalTurkRequester" in line:
                    new_properties_file.write("# service_url=https://mechanicalturk.sandbox.amazonaws.com/?Service=AWSMechanicalTurkRequester\n")
                elif "://mechanicalturk.amazonaws.com/?Service=AWSMechanicalTurkRequester" in line:
                     new_properties_file.write("service_url=https://mechanicalturk.amazonaws.com/?Service=AWSMechanicalTurkRequester\n")
                else:
                    new_properties_file.write(line)
        else:
            for line in old_properties_file:
                if "://mechanicalturk.sandbox.amazonaws.com/?Service=AWSMechanicalTurkRequester" in line:
                    new_properties_file.write("service_url=https://mechanicalturk.sandbox.amazonaws.com/?Service=AWSMechanicalTurkRequester\n")
                elif "://mechanicalturk.amazonaws.com/?Service=AWSMechanicalTurkRequester" in line:
                    new_properties_file.write("# service_url=https://mechanicalturk.amazonaws.com/?Service=AWSMechanicalTurkRequester\n")
                else:
                    new_properties_file.write(line)
        new_properties_file.close()
        print "Old mturk.properties file backed up at " + locationofCLT + "/bin/mturk.properties.backup"

    # write the .question file, which tells MTurk where to find your external HIT.
    question = open(output_dir + nameofexperimentfiles + ".question", 'w')
    question.write("<?xml version='1.0'?><ExternalQuestion xmlns='http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd'><ExternalURL>" + dict["experimentURL"] + "</ExternalURL><FrameHeight>"+ dict["frameheight"] +"</FrameHeight></ExternalQuestion>")
    question.close()

    #write the .properties file.
    properties = open(output_dir + nameofexperimentfiles + ".properties", 'w')
    properties.write("title: " + dict["title"] + "\ndescription: " + dict["description"] + "\nkeywords: " + dict["keywords"] + "\nreward: " + dict["reward"] + "\nassignments: " + dict["numberofassignments"] + "\nannotation: ${condition}\nassignmentduration:" + dict["assignmentduration"] + "\nhitlifetime:" + dict["hitlifetime"] + "\nautoapprovaldelay:" + dict["autoapprovaldelay"])
    if (dict["USonly?"] == "y" or dict["USonly?"] == "Y" or dict["USonly?"] == "yes" or dict["USonly?"] == "Yes" or dict["USonly?"] == "true" or dict["USonly?"] == "True" or dict["USonly?"] == "T" or dict["USonly?"] == "1"):
        properties.write("\nqualification.1:00000000000000000071\nqualification.comparator.1:EqualTo\nqualification.locale.1:US\nqualification.private.1:false")
    if (dict["minPercentPreviousHITsApproved"] != "none"):
        properties.write("\nqualification.2:000000000000000000L0\nqualification.comparator.2:GreaterThanOrEqualTo\nqualification.value.2:" + dict["minPercentPreviousHITsApproved"] + "\nqualification.private.2:false")
    if (dict["doesNotHaveQualification"] != "none"):
        properties.write("\nqualification.3:" + dict["doesNotHaveQualification"] + "\nqualification.comparator.3:DoesNotExist\nqualification.private.3:true")
    properties.close()

    #write the .input file. "conditions::" in the file experiment-settings.txt can be followed by any number of condition names, separated by a comma.
    input = open(output_dir + nameofexperimentfiles + ".input", 'w')
    input.write("condition\n")
    num = 1
    conditions = dict["conditions"]
    conditionlist = conditions.split(",")
    for x in conditionlist:
        input.write(submiterator_stringify(num) + " " + x + " \n")
        num = num + 1
    input.close()

def posthit(label):
    os.system(
        """
        HERE=`pwd`
        cd $MTURK_CMD_HOME/bin

        NAME_OF_EXPERIMENT_FILES=""" + label + """
        label=$HERE/$NAME_OF_EXPERIMENT_FILES
        ./loadHITs.sh -label "$label" -input "$label.input" -question "$label.question" -properties "$label.properties" -maxhits 1
        """
        )

def post(label):
    prepare(label)
    posthit(label)

def rename_results(label):
    fl = os.listdir('.')
    results_files = [x for x in fl if label in x and '.results' in x]
    nums = [int(x.split('_')[-1].split('.')[0]) for x in results_files]
    file_num = max(nums)+1
    os.rename(label+'.results',label+'_'+file_num+'.results')

def main():
    global TOTAL_NUM
    global LABEL
    global NUM_RESPONSES
    global LOCK_NAME
    global DELAY

    if os.path.isfile(LOCK_NAME+'~'):
        raise Exception('Process already running.')
    else:
        with open(LOCK_NAME+'~','w') as f:
            f.write(LABEL)

    while NUM_RESPONSES < TOTAL_NUM:
        if os.path.isfile(LOCK_NAME):
            time.sleep(DELAY)
            continue
        else:
            with open(LOCK_NAME,'w') as f:
                f.write(LABEL)
            post(LABEL)
            time.sleep(DELAY)
        results = os.popen("""
            HERE=`pwd`
            cd $MTURK_CMD_HOME/bin

            NAME_OF_EXPERIMENT_FILES=""" + label + """
            export NAME_OF_EXPERIMENT_FILES
            label="$HERE/$NAME_OF_EXPERIMENT_FILES"
            ./getResults.sh -successfile "$label.success" -outputfile "$label.results"
            """)
        for line in results:
            print(line[:-1])
        completion_data = results[6].split(' ')[2].split('/')
        if int(completion_data[0]) == int(completion_data[1]):
            os.remove(LOCK_NAME)
            rename_results(LABEL)
        NUM_RESPONSES += int(completion_data[0])
        NUM_LEFT = TOTAL_NUM - NUM_RESPONSES
        if NUM_LEFT <= 0:
            continue
        elif NUM_LEFT < int(completion_data[1]):
            conf = read_config(LABEL)
            conf["numberofassignments"] = NUM_LEFT
            write_config(LABEL,conf)
    os.remove(LOCK_NAME+'~')

try:
    main()
finally:
    os.remove(LOCK_NAME)
    os.remove(LOCK_NAME+'~')
