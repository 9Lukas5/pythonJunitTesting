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

def convertToUTF8(filePath):
    print('convert files to utf-8')
    encoding = Popen(['file', '-i', filePath], stdout=PIPE)
    encoding = encoding.stdout.read().decode('utf-8').split('=')[-1]
    Popen(['iconv', filePath, '-f', encoding, '-t', 'utf-8', '-o', filePath]).wait()

def buildSources(testDir, solDir):
    sourceFiles = ''
    testClasses = ''
    localCP = CLASSPATH

    localCP += ':' + testDir + '/'
    for root, subdirs, files in os.walk(testDir):
        for f in files:
            if (f.endswith('.java')):
                convertToUTF8(os.path.join(root, f))
                sourceFiles += ' ' + os.path.join(root, f)
                testClasses += ' ' + os.path.relpath(os.path.join(root, f), testDir).replace('.java', '').replace('/', '.')

    classCount = len(testClasses.strip().split(' '))
    if (os.path.isdir(solDir) != True):
        result = 'bla\n'
        for c in testClasses.strip().split(' '):
            result += 'Result for testing class ' + c + '\n Points 0\n'
        return result.split('Result for testing class')[1:classCount+1]

    localCP += ':' + solDir + '/'
    for root, subdirs, files in os.walk(solDir):
        for f in files:
            if (f.endswith('.java')):
                convertToUTF8(os.path.join(root, f))
                sourceFiles += ' ' + os.path.join(root, f)

    Popen(JAVA8_HOME + '/bin/javac -cp ' + localCP + sourceFiles, shell=True, cwd=testDir).wait()
    p = Popen(JAVA8_HOME + '/bin/java -cp ' + localCP + ' org.junit.runner.JUnitCore ' + testClasses, shell=True, cwd=testDir, stdout=PIPE, preexec_fn=os.setsid)
    try:
        stdout, other = p.communicate(timeout=30)
        stdout = stdout.decode('utf-8')

        for c in testClasses.strip().split(' '):
            if (("Result for testing class" + c) not in stdout):
                stdout += 'Result for testing class ' + c + '\n Points 0\n'

    except TimeoutExpired:
        print('timed-out, kill...')
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        stdout = 'bla\n'# Result for testing class something.' + f.replace('.java', 'Test') + '\n Points 0'
        for c in testClasses.strip().split(' '):
            stdout += 'Result for testing class ' + c + '\n Points 0\n'

    return stdout.split('Result for testing class')[1:classCount+1]

def download(student, task):
    targetPath = os.path.join('./', 'abgaben', student.name)
    if (os.path.isdir(targetPath) != True):
        os.makedirs(targetPath)

    if (os.path.isdir(os.path.join(targetPath, task))):
        rmtree(os.path.join(targetPath, task))

    repoURL = ""
    vcs     = ""
    command = ""
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

    Popen([vcs, command, repoURL, os.path.join(targetPath, task)]).wait()

def printHelp():
    print('TODO: print help')


#=================================#
#            main method          #
#=================================#

if (os.path.isfile(os.path.join(os.getcwd(), '.markerfileswp1testfolder')) != True):
    raise Exception ('working dir is missing marker file to identify CWD as test folder')

if (len(sys.argv) < 2):
    printHelp()
    exit(0)

validModes = {'download', 'test'}
if (sys.argv[1] not in validModes):
    raise Exception('no valid sub program given')

mode = sys.argv[1]

args = dict(item.replace('"', '').split('=') for item in sys.argv[2:])

if ('kind' not in args):
    raise Exception("no mode given. Exiting")

if ('task' not in args):
    raise Exception("no task given. Exiting")

studenten = list()

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

elif (args['kind'] == 'all'):
    if ('studenten' not in args or os.path.isfile(args['studenten']) != True):
        raise Exception('no students list given')

    
    with open(args['studenten']) as f:
        for line in f:
            if (line != '\n' and not line.startswith('#')):
                line = line.replace('\n', '')
                student = Student()
                student.name, student.vcs, student.alias = line.split('\t')
                studenten.append(student)
    f.close()

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

elif (mode == 'test'):
    if ('test' not in args):
        raise ValueError("don't know what testclasses you want to use")

    scratchTaskPath = os.path.join('..', 'Scratch', args['test'], 'test')
    copytree(scratchTaskPath, args['task'], symlinks=True)

    results = dict()
    for s in studenten:
        print('testing solution from Student: ' + s.name)
        junitLog = buildSources(os.path.join(os.getcwd(), args['task']),\
            os.path.join(os.getcwd(), 'abgaben', s.name, args['task'], 'src'))

        for part in junitLog:
            lines = part.split('\n')
            testName = lines[0].replace(':', '').strip().split('.')[-1]
            if testName not in results:
                results[testName] = TestErgebnis(testName)

            for line in lines:
                if 'Points' in line:
                    reachedPoints = line.replace('Points', '').strip()
                    results[testName].points[s] = reachedPoints

    rmtree(args['task'])

    resultsPath = os.path.join(os.getcwd(), 'results')
    if (os.path.isfile(resultsPath)):
        raise Exception('there is a results file, can\'t make a folder with that name')
    if (os.path.isdir(resultsPath) != True):
        os.makedirs(resultsPath)

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
