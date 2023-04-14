#!/usr/bin/env python 

import os
import json
import platform
import argparse
import sys
import traceback

# for readability
from subprocess import call
from subprocess import check_output
from subprocess import check_call
from subprocess import CalledProcessError

from os import path
from os import makedirs
from os.path import normpath

from string import find
from urllib import urlretrieve


# ROVER BASE #
class RoverMods:
    PIPE_TO_STDOUT = not sys.stdout.isatty()

    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'

    @staticmethod
    def Header(line):
        if(RoverMods.PIPE_TO_STDOUT):
            return line

        return RoverMods.HEADER + line + RoverMods.ENDC

    @staticmethod
    def Blue(line):
        if(RoverMods.PIPE_TO_STDOUT):
            return line
        
        return RoverMods.BLUE + line + RoverMods.ENDC

    @staticmethod
    def Green(line):
        if(RoverMods.PIPE_TO_STDOUT):
            return line
        
        return RoverMods.GREEN + line + RoverMods.ENDC

    @staticmethod
    def Yellow(line):
        if(RoverMods.PIPE_TO_STDOUT):
            return line
        
        return RoverMods.YELLOW + line + RoverMods.ENDC
    
    @staticmethod
    def White(line):
        if(RoverMods.PIPE_TO_STDOUT):
            return line
        
        return RoverMods.WHITE + line + RoverMods.ENDC

    @staticmethod
    def Red(line):
        if(RoverMods.PIPE_TO_STDOUT):
            return line
        
        return RoverMods.RED + line + RoverMods.ENDC

    @staticmethod
    def Bold(line):
        if(RoverMods.PIPE_TO_STDOUT):
            return line
        
        return RoverMods.BOLD + line + RoverMods.ENDC

    @staticmethod
    def Underline(line):
        if(RoverMods.PIPE_TO_STDOUT):
            return line
        
        return RoverMods.UNDERLINE + line + RoverMods.ENDC   
    
def RoverPrint(line):
    print(RoverMods.Bold(RoverMods.Header('** ' + RoverMods.Underline('ROVER'))) + ' ' + (str(line)))

def UnexpectedRoverException(exc_info):
    RoverPrint(
        RoverMods.Red(
            'CAUGHT AN UNEXPECTED EXCEPTION: \"'
            + RoverMods.White(f'{str(exc_info[1])}')
            + '\" of type: %s' % (str(exc_info[0]))
        )
    )
    RoverPrint(RoverMods.White(f'{str(traceback.print_tb(exc_info[2]))}'))
    os._exit(1) # bail out immediately to avoid possibly futzing up the state, or printing unhelpful messages. 


# probably a pretty shaky interpretation of the semantic versioning 2.0.0 standard (http://semver.org/)
# I really focused on clauses 9, 10 and 11
class SemanticVersion:
    # this is python overloading the '>' operator
    def __gt__(self, other):
        return next(
            (
                True
                for index, val in enumerate(self.VersionTuple[0])
                if self.VersionTuple[0][index] > other.VersionTuple[0][index]
            ),
            True
            if (len(self.VersionTuple) < len(other.VersionTuple))
            else len(self.VersionTuple) >= 2
            and (self.VersionTuple[1] > other.VersionTuple[1]),
        )

    def GetVersionTuple(self, versionStr):       
        # a version string potentially looks like this:
        # 0.0.0-alpha-00000
        # the first part is canonical: 0.0.0 - it is ordered by the 'ol intuitive manner
        # the second part is 'build metadata' - it is ordered lexically
        middleIndex = versionStr.find('-')
        if middleIndex != -1:
            # otherwise, we'll slice in two
            return versionStr[:middleIndex].split('.'), versionStr[middleIndex:]

        array = versionStr.split('.')
        return ([array])
    
    def __str__(self):
        return self.VersionString

    def __init__(self, versionStr):
        self.VersionTuple = self.GetVersionTuple(versionStr)
        self.VersionString = versionStr

# END ROVER BASE #

class RoverSettings:
    # Setting dev mode to True means that we keep a folder around.
    # By Design DevMode is triggered if there is a pre-existing working directory
    # By Design, when in DevMode we do not run any git commands.
    # By Design, when in DevMode we do not clean up anything.
    _DevMode=False

    # This function needs to be here, because otherwise we wouldnt be able to change DevMode. 
    def FetchOSVariables():
        try:
            os_release_path = '/etc/os-release'

            # according to the man page, we should fall back here if the canonical os-release is missing.
            if not path.exists(os_release_path):
                os_release_path = '/usr/lib/os-release'

            os_vars = {}
            with open(os_release_path) as f:
                for line in f:
                    line = line.strip()

                    if not line: # skip blank lines
                        continue

                    data = line.split('=')
                    os_vars[str(data[0]).strip('\n\"')] = str(data[1]).strip('\n\"')

            return os_vars
        except IOError:
            RoverPrint(RoverMods.Red('requires \'/etc/os-release/\' to exist. For more information, try ' + RoverMods.White('man os-release')))
        except:
            RoverSettings._DevMode = True # to prevent cleanup (to support investigation)
            RoverPrint(RoverMods.Red('CAUGHT AN UNEXPECTED EXCEPTION: \"' + RoverMods.White("%s") + '\" of type: %s'%(str(sys.exc_info()[1]), str(sys.exc_info()[0]))))
            RoverPrint(RoverMods.Red(RoverMods.White('%s')%(str(sys.exc_info()[3]))))

    _OsVars                             = FetchOSVariables()
    _Rid                                = '%s.%s-x64'%(_OsVars['ID'], _OsVars['VERSION_ID'])
    _Moniker                            = '%s-dotnet'%(_Rid)
    _ScriptDirectory                    = str(path.dirname(path.abspath(__file__)))
    _LaunchedFromDirectory              = os.getcwd()
    
    _WorkingDirectory                   = path.join(_LaunchedFromDirectory, _Moniker)
    _srcDirectory                       = path.join(_WorkingDirectory, "src")
    _objDirectory                       = path.join(_WorkingDirectory, "obj")
    _binDirectory                       = path.join(_WorkingDirectory, "bin")

    @staticmethod
    def SetWorkingDirectory(working_dir):
        RoverSettings._WorkingDirectory                   = working_dir
        RoverSettings._srcDirectory                       = path.join(working_dir, "src")
        RoverSettings._objDirectory                       = path.join(working_dir, "obj")
        RoverSettings._binDirectory                       = path.join(working_dir, "bin")


    PayloadPath                         = str('')
    PatchTargetPath                     = _binDirectory
    BuildSet                            = []
    Patch                               = True

    CoreCLRBinDirectory                 = ''
    CoreFXBinDirectory                  = ''
    CoreSetupBinDirectory               = ''
    LibUVBinDirectory                   = ''

    PatchTarget_Shared                  = ''
    PatchTarget_SDK                     = ''
    PatchTarget_Host                    = ''

    DotNetCommitHash                    = ''

    @staticmethod
    def MaxPrecedence(versionStrA, versionStrB):
        versionA = SemanticVersion(versionStrA)
        versionB = SemanticVersion(versionStrB)

        return max(versionA, versionB)


    @staticmethod
    def SelectGreatestPrecendenceDirectory(containerDirectory):
        maxVersion = '0.0.0-alpha-00000'

        for root, dirs, files in os.walk(containerDirectory):
            for dirName in dirs:
                maxVersion = RoverSettings.MaxPrecedence(dirName, maxVersion)
                
            break # just 'walk' the top level.
        
        return str(maxVersion)
    
    @staticmethod
    def SetPatchTargetPath(pathToFolder):
        if path.exists(pathToFolder):
            RoverSettings.PatchTargetPath = pathToFolder
            # require there to be a Microsoft.NETCore.App in the shared
            # we will locate the highest version;
            shared_containerFolder = path.join(pathToFolder, path.join('shared', 'Microsoft.NETCore.App'))
            RoverSettings.PatchTarget_Shared   = path.join(shared_containerFolder, RoverSettings.SelectGreatestPrecendenceDirectory(shared_containerFolder)) 

            # will locate the highest version and patch that
            sdk_containerFolder = path.join(pathToFolder, path.join('sdk'))
            RoverSettings.PatchTarget_SDK      = path.join(sdk_containerFolder, RoverSettings.SelectGreatestPrecendenceDirectory(sdk_containerFolder))
            
            # require the host to be 'fxr', then we take the highest version.
            host_containerFolder = path.join(pathToFolder, path.join('host', 'fxr'))
            RoverSettings.PatchTarget_Host     = path.join(host_containerFolder, RoverSettings.SelectGreatestPrecendenceDirectory(host_containerFolder))


if path.exists(RoverSettings._WorkingDirectory):
    RoverPrint(RoverMods.Header(RoverMods.Red('FORCED SETTINGS CHANGE: DEV MODE \'ON\' ')))
    RoverPrint(RoverMods.Yellow(('will skip all git commands.')))
    RoverPrint(RoverMods.Yellow(('requires the deletion of the directory \'%s\' to reset the dev-mode trigger.'%(RoverSettings._WorkingDirectory))))

    RoverSettings._DevMode=True

# A 'Rover Shell Call' is a shell call that we want to be reproduceable in the event of a failure. 
# namely, something that a developer can go in and 'drill in' on without running the entirety of the 
# build again.
def RoverShellCall(cmd, cwd = None):
    if not cwd:
        cwd = os.getcwd()

    try:
        check_call(cmd, shell=True, cwd=cwd)

    except CalledProcessError as repro_data:
        RoverSettings._DevMode = True

        repro_filename = 'rover_failure-repro.sh'
        repro_destination = path.join(cwd, repro_filename)

        # when the call fails, print a repro to the working directory.
        with open(repro_destination, 'w') as repro_file:
            repro_file.writelines(['#!/usr/bin/env bash\n', repro_data.cmd + '\n'])

        if os.getuid() == 0:
            call(f'chmod +x {repro_filename}', shell=True, cwd=cwd)

        RoverPrint(RoverMods.Red('has detected a failure. A repro shell script has been placed at ') + RoverMods.Yellow(repro_destination))
        RoverPrint(RoverMods.White('To reproduce the failure:\n\tcd %s\n\t./%s'%(cwd, repro_filename)))
        RoverPrint(RoverMods.Red('is forcefully closing. Note that re-running Rover will execute it with DevMode enabled (no git commands will be run)'))

        os._exit(1) # if we fail a check_call then we want to bail out asap so the dev can investigate.


##
## ROVER FUNCTION DEFINITIONS
##

# detination_folder is expected to be relative to the _ScriptDirectory. 
# payload path is expected to be a dotnet-cli tarball.
def SpawnPatchTarget(destination_folder, payload_path):
    try:
        if payload_path and not path.isabs(payload_path):
            payload_path = path.join(RoverSettings._LaunchedFromDirectory, payload_path)

        if not path.isabs(destination_folder):
            destination_folder = path.join(RoverSettings._LaunchedFromDirectory, destination_folder)

        if not path.exists(str(payload_path)):
            fallback_url = 'https://dotnetcli.blob.core.windows.net/dotnet/Sdk/rel-1.0.0/dotnet-dev-debian-x64.latest.tar.gz'               

            payload_filename    = 'dotnet.latest.tar.gz'
            payload_path        = path.join(RoverSettings._objDirectory, payload_filename)

            if not path.exists(payload_path):
                RoverPrint(
                    RoverMods.Blue(
                        f'is downloading latest .NET CLI for bootstrapping ({payload_filename})'
                    )
                )

            urlretrieve(fallback_url, payload_path)

        # lets force the path to be made absolute - assuming that the payload path is relative to the directory we launched the script from.
        # otherwise if we have an abs path already - fantastic.

        RoverShellCall(f'tar xf {payload_path} -C {destination_folder}')
    except:
        RoverSettings._DevMode = True
        UnexpectedRoverException(sys.exc_info())

    RoverSettings.SetPatchTargetPath(path.join(RoverSettings._ScriptDirectory, destination_folder))

def CloneRepositories(cwd,
                        coreclr_commit_hash, 
                        corefx_commit_hash,
                        dotnet_commit_hash):
    try:
        if not path.exists(path.join(cwd, 'coreclr')):
            RoverShellCall('git clone http://www.github.com/dotnet/coreclr', cwd=cwd)
            RoverShellCall(
                f'git checkout {coreclr_commit_hash}',
                cwd=path.join(cwd, 'coreclr'),
            )

        if not path.exists(path.join(cwd, 'corefx')):
            RoverShellCall('git clone http://www.github.com/dotnet/corefx', cwd=cwd)
            RoverShellCall(
                f'git checkout {corefx_commit_hash}',
                cwd=path.join(cwd, 'corefx'),
            )

        if not path.exists(path.join(cwd, 'core-setup')):
            RoverShellCall('git clone http://www.github.com/dotnet/core-setup', cwd=cwd)
            RoverShellCall(
                f'git checkout {dotnet_commit_hash}',
                cwd=path.join(cwd, 'core-setup'),
            )   

        if not path.exists(path.join(cwd, 'libuv')):
            RoverShellCall('git clone http://www.github.com/libuv/libuv', cwd=cwd)
            # we are fixed to using libuv 1.9.0 - this is the commit hash for that (https://github.com/libuv/libuv/commit/229b3a4cc150aebd6561e6bd43076eafa7a03756)
            RoverShellCall(
                'git checkout 229b3a4cc150aebd6561e6bd43076eafa7a03756',
                cwd=path.join(cwd, 'libuv'),
            )   

        else:
            RoverPrint(RoverMods.Yellow(('DEVMODE IS ON. Skipping all git calls : I.e. you must manually control git your self.')))

    except:
        RoverSettings._DevMode = True
        UnexpectedRoverException(sys.exc_info())



def BuildNativeComponents(  coreclr_git_directory,
                            corefx_git_directory,
                            core_setup_git_directory,
                            libuv_git_directory):
    try:
        RoverPrint(RoverMods.Blue('is building the .NET GitHub repositories.'))

        # Build CoreCLR
        # skipping non-essential for bootstrapping.
        if 'coreclr' in RoverSettings.BuildSet:
            RoverShellCall('./build.sh x64 release skiptests skipnuget', cwd=coreclr_git_directory)

        if 'corefx' in RoverSettings.BuildSet:
            if path.exists(path.join(corefx_git_directory, 'src', 'Native', 'build-native.sh')):
                RoverShellCall(
                    './build-native.sh x64 release Linux --numProc 1',
                    cwd=f"{corefx_git_directory}/src/Native",
                )
            else:
                RoverShellCall('./build.sh native x64 release', cwd=corefx_git_directory) 

        # Build corehost from core-setup
        # TODO: Pull versions from the runtimes.
        if 'core-setup' in RoverSettings.BuildSet:
            RoverShellCall(
                f'./build.sh --arch x64 --rid {RoverSettings._Rid} --hostver 0.0.0 --fxrver 0.0.0 --policyver 0.0.0 --commithash {RoverSettings.DotNetCommitHash}',
                cwd=f"{core_setup_git_directory}/src/corehost",
            )

        # Build libUV
        if 'libuv' in RoverSettings.BuildSet:
            RoverShellCall('./autogen.sh',     cwd=libuv_git_directory)
            RoverShellCall('./configure',      cwd=libuv_git_directory)
            RoverShellCall('make',             cwd=libuv_git_directory)

    except:
        RoverSettings._DevMode = True
        UnexpectedRoverException(sys.exc_info())


def PatchTarget(patchTarget_folder,
                coreclr_bin_directory,
                corefx_native_bin_directory,
                core_setup_cli_bin_directory,
                libuv_bin_directory):
    try:
        if RoverSettings.Patch:
            RoverPrint(
                RoverMods.Blue(
                    f'is patching {RoverMods.Yellow(patchTarget_folder)}'
                )
            )

            # replace native dotnet in the base directory
            # from core_setup
            RoverShellCall(
                f'cp dotnet {path.join(patchTarget_folder)}',
                cwd=f'{core_setup_cli_bin_directory}/exe/',
            )

            # replace native files in 'shared' folder.
            # from coreclr
            RoverShellCall(
                f'cp *so {RoverSettings.PatchTarget_Shared}',
                cwd=coreclr_bin_directory,
            )
            RoverShellCall(
                f'cp corerun {RoverSettings.PatchTarget_Shared}',
                cwd=coreclr_bin_directory,
            )
            RoverShellCall(
                f'cp crossgen {RoverSettings.PatchTarget_Shared}',
                cwd=coreclr_bin_directory,
            )

            # from core_setup
            RoverShellCall(
                f'cp dotnet {RoverSettings.PatchTarget_Shared}',
                cwd=f'{core_setup_cli_bin_directory}/exe/',
            )
            RoverShellCall(
                f'cp libhostpolicy.so {RoverSettings.PatchTarget_Shared}',
                cwd=f'{core_setup_cli_bin_directory}/dll/',
            )
            RoverShellCall(
                f'cp libhostfxr.so {RoverSettings.PatchTarget_Shared}',
                cwd=f'{core_setup_cli_bin_directory}/fxr/',
            )

            # from corefxcd
            RoverShellCall(
                f'cp System.* {RoverSettings.PatchTarget_Shared}',
                cwd=corefx_native_bin_directory,
            )

            # from libuv
            RoverShellCall(
                f'cp libuv.so {RoverSettings.PatchTarget_Shared}',
                cwd=libuv_bin_directory,
            )

            # replace native files in 'sdk' folder.
            # from core_setup
            RoverShellCall(
                f'cp libhostpolicy.so {RoverSettings.PatchTarget_SDK}',
                cwd=f'{core_setup_cli_bin_directory}/dll/',
            )
            RoverShellCall(
                f'cp libhostfxr.so {RoverSettings.PatchTarget_SDK}',
                cwd=f'{core_setup_cli_bin_directory}/fxr/',
            )

            # replace native files in 'host' folder.
            # from core_setup
            RoverShellCall(
                f'cp libhostfxr.so {RoverSettings.PatchTarget_Host}',
                cwd=f'{core_setup_cli_bin_directory}/fxr/',
            )

            RoverPrint(
                RoverMods.Blue(
                    f'has finished patching {RoverMods.Yellow(patchTarget_folder)}'
                )
            )
    except:
        RoverSettings._DevMode = True
        UnexpectedRoverException(sys.exc_info())

##
## END ROVER FUNCTION DEFINITIONS
##

if __name__ == "__main__":
    ##
    ##  COMMAND-LINE BEHAVIOR
    ##

    parser = argparse.ArgumentParser(description = 'This is the .NET CLI bootstrapping tool.')

    parser.add_argument('-build', metavar='b', nargs='*', default = ['coreclr', 'corefx', 'core-setup', 'libuv'],help='\'Builds\' all native components if no arguments are specified. Otherwise, specify one or more (space separated) arguments from the following : {' 
        + '%s, %s, %s, %s'%(RoverMods.Red('coreclr'), RoverMods.Blue('corefx'), RoverMods.Green('core-setup'), RoverMods.Yellow('libuv') +'}'))
    parser.add_argument('-nopatch', action='store_true', default=False, help='prevents the copying of specific native binaries from the pre-built repositories in to the destination directory.')
    parser.add_argument('-payload', nargs=1, help='Specify a path to a tarball (something that we can tar xf) that contains a version of the dotnet CLI.')
    parser.add_argument(
        '-to',
        type=str,
        default=f'{RoverSettings._Moniker}',
        help=f'allows you to overwrite the default staging directory (default is {RoverSettings._Moniker})',
    )

    args = parser.parse_args()

    if args.payload:
        RoverPrint('is using payload from \'' + RoverMods.White(str(args.payload)) + '\'')

    RoverPrint(f'Building: {RoverMods.White(str(args.build))}')
    RoverPrint(f'Patching? {RoverMods.White(str(not args.nopatch))}')

    RoverSettings.SetWorkingDirectory(normpath(str(args.to)))

    RoverPrint(f'Staging in {RoverSettings._WorkingDirectory}')
    RoverSettings.BuildSet = args.build

    # I am guessing that users are more inclined to want patching to happen whenever it can, and so I ask
    # for specificity in the instances that they do not want patching.
    RoverSettings.Patch = not args.nopatch 

    if args.payload:
        RoverSettings.PayloadPath = args.payload[0]
    ## 
    ## END COMMAND-LINE BEHAVIOR
    ##

    ##
    ## BEGIN DECLARATIONS
    ##

    coreclr_working_git_directory       = path.join(RoverSettings._srcDirectory, 'coreclr')
    corefx_working_git_directory        = path.join(RoverSettings._srcDirectory, 'corefx')
    core_setup_working_git_directory    = path.join(RoverSettings._srcDirectory, 'core-setup')
    libuv_working_git_directory         = path.join(RoverSettings._srcDirectory, 'libuv')

    default_coreclr_bin_directory = (
        f'{coreclr_working_git_directory}/bin/Product/Linux.x64.Release/'
    )
    default_corefx_native_bin_directory = (
        f'{corefx_working_git_directory}/bin/Linux.x64.Release/Native'
    )
    default_core_setup_cli_bin_directory = (
        f'{core_setup_working_git_directory}/src/corehost/cli'
    )
    default_libuv_bin_directory = f'{libuv_working_git_directory}/.libs'

    RoverSettings.CoreCLRBinDirectory   = default_coreclr_bin_directory
    RoverSettings.CoreFXBinDirectory    = default_corefx_native_bin_directory
    RoverSettings.CoreSetupBinDirectory = default_core_setup_cli_bin_directory
    RoverSettings.LibUVBinDirectory     = default_libuv_bin_directory

    platform_info                       = platform.uname()
    this_distro_name                    = str(platform.linux_distribution()[0]).lower()

    ##
    ## END DECLARATIONS
    ##

    ##
    ## BEGIN PROCEDURE
    ##

    try:
        os.putenv('ID',         RoverSettings._OsVars['ID'])
        os.putenv('VERSION_ID', RoverSettings._OsVars['VERSION_ID'])

        RoverPrint(RoverMods.Blue(f'RID: {RoverMods.Green(RoverSettings._Rid)}'))

        # Spawn our working directory
        if not path.exists(RoverSettings._WorkingDirectory):
            makedirs(RoverSettings._WorkingDirectory)

        if not path.exists(RoverSettings._srcDirectory):
            makedirs(RoverSettings._srcDirectory)

        if not path.exists(RoverSettings._objDirectory):
            makedirs(RoverSettings._objDirectory)

        if not path.exists(RoverSettings._binDirectory):
            makedirs(RoverSettings._binDirectory)

        SpawnPatchTarget(RoverSettings._binDirectory, RoverSettings.PayloadPath)

        # Fetch the commit hashes from the native files.
        coreclr_output      = check_output('strings libcoreclr.so | grep @\(#\)',     shell = True, cwd=RoverSettings.PatchTarget_Shared)
        corefx_output       = check_output('strings System.Native.so  | grep @\(#\)', shell = True, cwd=RoverSettings.PatchTarget_Shared)

        dotnet_commit_hash  = check_output('strings dotnet  | grep "[a-f0-9]\{40\}"',  shell = True, cwd=RoverSettings.PatchTarget_Shared)
        coreclr_commit_hash = coreclr_output[
            find(coreclr_output, 'Commit Hash: ') + len('Commit Hash: ') :
        ]
        corefx_commit_hash = corefx_output[
            find(corefx_output, 'Commit Hash: ') + len('Commit Hash: ') :
        ]

        RoverSettings.DotNetCommitHash = dotnet_commit_hash

        CloneRepositories(RoverSettings._srcDirectory,  
                            coreclr_commit_hash,
                            corefx_commit_hash,
                            dotnet_commit_hash)

        BuildNativeComponents(coreclr_working_git_directory, 
                            corefx_working_git_directory,  
                            core_setup_working_git_directory,  
                            libuv_working_git_directory)

        PatchTarget(RoverSettings.PatchTargetPath,
                    RoverSettings.CoreCLRBinDirectory,      
                    RoverSettings.CoreFXBinDirectory,
                    RoverSettings.CoreSetupBinDirectory,
                    RoverSettings.LibUVBinDirectory)

        RoverPrint(
            RoverMods.Green(
                'spawned a \'dotnet\' in %s'
                % RoverMods.Yellow(
                    f'./{path.relpath(RoverSettings.PatchTargetPath)}/'
                )
            )
            + RoverMods.Green('(enjoy!)')
        )
    except:
        RoverSettings._DevMode = True
        UnexpectedRoverException(sys.exc_info())


    ##
    ## END PROCEDURE
    ##
