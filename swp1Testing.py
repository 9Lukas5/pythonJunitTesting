import sys
import os
import signal
from subprocess import Popen, PIPE, TimeoutExpired
from shutil import copytree, rmtree
import environmentVariables

#=================================#
#            global vars          #
#=================================#
server      = environmentVariables.server
user        = environmentVariables.user
repoRoot    = environmentVariables.repoRoot
JAVA8_HOME  = environmentVariables.JAVA8_HOME
JUNIT_HOME  = environmentVariables.JUNIT_HOME
CLASSPATH   = environmentVariables.CLASSPATH

class Student(object):
    def __init__(self):
        self.name = ""
        self.vcs = ""
        self.alias = ""

    def toString(self):
        toReturn = ''
        toReturn += 'name:\t' + self.name + '\n'
        toReturn += 'vcs:\t' + self.vcs + '\n'
        toReturn += 'alias:\t' + self.alias
        return toReturn

class TestErgebnis(object):
    def __init__(self, name):
        self.name = name
        self.points = dict()

# this method makes sure, that the files are all in utf-8 format
def convertToUTF8(filePath):
    print('convert files to utf-8')
    encoding = Popen(['file', '-i', filePath], stdout=PIPE)
    encoding = encoding.stdout.read().decode('utf-8').split('=')[-1]
    Popen(['iconv', filePath, '-f', encoding, '-t', 'utf-8', '-o', filePath]).wait()

def buildSources(testDir, solDir):
    sourceFiles = ''
    testClasses = ''
    # get classpath from the environment variables predefined CP
    localCP = CLASSPATH

    # add the current testDir to the classpath
    localCP += ':' + testDir + '/'

    # walk through the test dir
    for root, subdirs, files in os.walk(testDir):
        for f in files:
            # convert all java files to utf-8 and add them to the source
            # files and the testClasses list
            if (f.endswith('.java')):
                convertToUTF8(os.path.join(root, f))
                sourceFiles += ' ' + os.path.join(root, f)
                testClasses += ' ' + os.path.relpath(os.path.join(root, f), testDir).replace('.java', '').replace('/', '.')

    # if somehow there's no solution, workaround the non existent jUnit
    # output and generated a own output of zero points
    classCount = len(testClasses.strip().split(' '))
    if (os.path.isdir(solDir) != True):
        result = 'bla\n'
        for c in testClasses.strip().split(' '):
            result += 'Result for testing class ' + c + '\n Points 0\n'
        return result.split('Result for testing class')[1:classCount+1]

    # add the solution dir of the student to the CP
    localCP += ':' + solDir + '/'
    for root, subdirs, files in os.walk(solDir):
        for f in files:
            # convert all java files to utf-8 and add them to the
            # sources list
            if (f.endswith('.java')):
                convertToUTF8(os.path.join(root, f))
                sourceFiles += ' ' + os.path.join(root, f)

    # compile all files from the sources list
    Popen(JAVA8_HOME + '/bin/javac -cp ' + localCP + sourceFiles, shell=True, cwd=testDir).wait()

    # run all testclasses we found beforehand
    p = Popen(JAVA8_HOME + '/bin/java -cp ' + localCP + ' org.junit.runner.JUnitCore ' + testClasses, shell=True, cwd=testDir, stdout=PIPE, preexec_fn=os.setsid)

    # make sure that the script isn't blocked, if a student made a endless loop^^
    try:
        stdout, other = p.communicate(timeout=30)
        stdout = stdout.decode('utf-8')

        logPath = os.path.join(solDir, "..", "JUnitlog.txt")
        with open(logPath, 'w') as f:
            f.write(stdout)
        f.close()

    # if a student made a endless loop, write zero points to the log
    except TimeoutExpired:
        print('timed-out, kill...')
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        stdout = 'bla\n'# Result for testing class something.' + f.replace('.java', 'Test') + '\n Points 0'
        for c in testClasses.strip().split(' '):
            stdout += 'Result for testing class ' + c + '\n Points 0\n'

    # check the jUnit log if there are results for all classes.
    # if one's missing, there wen't something bad, so we rate it
    # with zero points
    for c in testClasses.strip().split(' '):
        if (("Result for testing class " + c) not in stdout):
            stdout = 'Result for testing class ' + c + '\n Points 0\n' + stdout
    stdout = "<empty line>" + stdout

    # give back the splitted results log, containing points for
    # all to be tested classes
    return stdout.split('Result for testing class')[1:classCount+1]

def download(student, task):
    # local path where all downloads are going to, is in
    # abgaben/studentsUserName
    targetPath = os.path.join('./', 'abgaben', student.name)

    # if this is the first download we make for this student
    # create a new folder with his/her name
    if (os.path.isdir(targetPath) != True):
        os.makedirs(targetPath)

    # if we downloaded this task earlier yet, delete the local copy first
    # to make sure we don't have any leftovers
    if (os.path.isdir(os.path.join(targetPath, task))):
        rmtree(os.path.join(targetPath, task))

    repoURL = ""
    vcs     = ""
    command = ""

    # dependant on the given vcs create the approprieate download
    # command
    if (server == "local"):
        if (student.vcs == "svn"):
            repoURL = "file:///" + repoRoot + student.name + "/" + task
            vcs = "svn"
            command = "checkout"
        elif (student.vcs == "git"):
            repoURL = repoRoot + student.name + "/GIT/" + task + ".git"
            vcs = "git"
            command = "clone"
        else:
            raise Exception('unknown vcs system')
    else:
        if (student.vcs == 'svn'):
            repoURL = 'svn+ssh://'\
                + user\
                + '@' + server\
                + ':' + repoRoot\
                + student.name + '/'\
                + task
            vcs = "svn"
            command = "checkout"
        elif (student.vcs == 'git'):
            repoURL = user\
                + '@' + server\
                + ':' + repoRoot\
                + student.name + '/GIT/'\
                + task + '.git'
            vcs = "git"
            command = "clone"
        else:
            raise Exception('unknown vcs system')

    # open a new task, running the constructed download command
    Popen([vcs, command, repoURL, os.path.join(targetPath, task)]).wait()

def printHelp():
    print('python3 swp1Testing.py [download|test] kind=[single|all]'
    + ' task=<name of task to be tested> test=<name of test>')
    print()
    print('\t useAlias=True\t-\t use the alias given for the results file')
    print()
    print('for kind=single:')
    print('\t student=<username of student>')
    print('\t vcs=[svn|git] version control system the student uses')
    print()
    print('for kind=all:')
    print('\t studenten=<file of students>')

#=================================#
#            main method          #
#=================================#

# for safety, the folder we run this script from, an empty file with
# the name underneath has to be present. If not, the program immediately
# stops.
if (os.path.isfile(os.path.join(os.getcwd(), '.markerfileswp1testfolder')) != True):
    raise Exception ('working dir is missing marker file to identify CWD as test folder')

if (len(sys.argv) < 2):
    printHelp()
    exit(0)

# we can download or test tasks that's it
validModes = {'download', 'test'}
if (sys.argv[1] not in validModes):
    raise Exception('no valid sub program given')

mode = sys.argv[1]

# split all other things into a map. Just because it's simpler
# and don't have to remember any correct order of the commands^^
args = dict(item.replace('"', '').split('=') for item in sys.argv[2:])

# we need to know if we should test a single student or a list of
# multiple students
if ('kind' not in args):
    raise Exception("no mode given. Exiting")

# which task to be tested or downloaded is also necessary
if ('task' not in args):
    raise Exception("no task given. Exiting")

# create a empty students list
studenten = list()

# if only a single student, we need to know a few additional things
# before we can start
if (args['kind'] == 'single'):
    s = Student()
    if ('student' not in args):
        raise ValueError('no name given')

    if ('vcs' not in args and mode == 'download'):
        raise ValueError('no vcs given')
    elif ('vcs' in args):
        s.vcs = args['vcs']

    if ("alias" in args):
        s.alias = args["alias"]

    s.name = args['student']

    studenten.append(s)

# if a list should be processed, the file with the list has to be given
elif (args['kind'] == 'all'):
    if ('studenten' not in args or os.path.isfile(args['studenten']) != True):
        raise Exception('no students list given')

    # add for each entry that isn't commented out with a hash a new
    # student to the list.
    with open(args['studenten']) as f:
        for line in f:
            if (line != '\n' and not line.startswith('#')):
                line = line.replace('\n', '')
                student = Student()
                student.name, student.vcs, student.alias = line.split('\t')
                studenten.append(student)
    f.close()

# if we should download a task, processing the students list, check
# for each if the name and vcs is given before trying to the download
if (mode == 'download'):
    for s in studenten:
        try:
            if (s.name == ''):
                raise ValueError('no name given')
            if (s.vcs == ''):
                raise ValueError('no vcs given')
            download(s, args['task'])
        except ValueError:
            pass

# if we should test, vcs isn't necessary, but we need to know how the
# test project is named
elif (mode == 'test'):
    if ('test' not in args):
        raise ValueError("don't know what testclasses you want to use")

    # create the path to the test-project and copy it to our current
    # path
    scratchTaskPath = os.path.join('..', 'Scratch', args['test'], 'test')
    copytree(scratchTaskPath, args['task'], symlinks=True)

    # create a map for the results that we can write a textfile after
    # testing all students
    results = dict()
    for s in studenten:
        print('testing solution from Student: ' + s.name)
        # result of buildSources gives us a array with the singles classes
        junitLog = buildSources(os.path.join(os.getcwd(), args['task']),\
            os.path.join(os.getcwd(), 'abgaben', s.name, args['task'], 'src'))

        # for each test extract the name and reached points for it
        for part in junitLog:
            lines = part.split('\n')
            testName = lines[0].replace(':', '').strip().split('.')[-1]
            if testName not in results:
                results[testName] = TestErgebnis(testName)

            for line in lines:
                if 'Points' in line:
                    reachedPoints = line.replace('Points', '').strip()
                    results[testName].points[s] = reachedPoints

    # after testing all students, remvoe the testfolder we copied again
    rmtree(args['task'])

    # if necessary create the folder for storing the result files
    resultsPath = os.path.join(os.getcwd(), 'results')
    if (os.path.isfile(resultsPath)):
        raise Exception('there is a results file, can\'t make a folder with that name')
    if (os.path.isdir(resultsPath) != True):
        os.makedirs(resultsPath)

    # write the results from the test to a textfile into the results
    # folder.
    # If we set the alias switch True, the file will contain the aliases
    # of the students instead of their user names.
    # Useful to be able to directly publish the results file
    for r in results:
        fPath = os.path.join(resultsPath, 'Points_' + args['task'] + '_' + r + '.txt')
        with open(fPath, 'w') as f:
            for st in results[r].points:
                if ("useAlias" in args and args["useAlias"] == "True"):
                    f.write(st.alias + '\t' + results[r].points[st] + '\n')
                else:
                    f.write(st.name + '\t' + results[r].points[st] + '\n')
        f.close()
        print (results[r].name)
        for st in results[r].points:
            if("useAlias" in args and args["useAlias"] == "True"):
                print(st.alias + '\t' + results[r].points[st])
            else:
                print(st.name + '\t' + results[r].points[st])

else:
    raise Exception("no valid mode given!")
