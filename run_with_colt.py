import sublime, sublime_plugin
import os.path
import subprocess
import calendar, time
import colt_rpc

from xml.etree.ElementTree import Element, SubElement, tostring, parse
from colt_rpc import ColtConnection

class ColtCompletitions(sublime_plugin.EventListener):
        
        def on_query_completions(self, view, prefix, locations):                
                if (ColtConnection.port == -1) :
                        return []

                # TODO: implement
                return [ ("var1\t(COLT suggested)", "var1"), ("var2\t(COLT suggested)", "var2") ]

        def getWordPosition(self, view):
                position = self.getPosition(view)
                return view.word(position).end()

        def getPosition(self, view):
                for sel in view.sel() :
                        return sel

                return None

        def getPositionEnd(self, view):
                position = self.getPosition(view)
                if position is None :
                        return - 1

                return position.end()

        def getContent(self, view):
                return view.substr(sublime.Region(0, view.size()))


class RunWithColtCommand(sublime_plugin.WindowCommand):
        
        PREFERENCES_NAME = "Preferences.sublime-settings"

        def run(self):
                settings = sublime.load_settings(RunWithColtCommand.PREFERENCES_NAME)
                if not settings.has("coltPath") :                        
                        sublime.error_message("COLT path is not specified, please enter the path")
                        self.window.show_input_panel("COLT Path:", "", self.onCOLTPathInput, None, None)
                        return

                settings = sublime.load_settings(RunWithColtCommand.PREFERENCES_NAME)
                coltPath = settings.get("coltPath")
                
                if not os.path.exists(coltPath) :
                        sublime.error_message("COLT path specified is invalid, please enter the correct path")
                        self.window.show_input_panel("COLT Path:", "", self.onCOLTPathInput, None, None)
                        return

                settings = sublime.load_settings(RunWithColtCommand.PREFERENCES_NAME)
                coltPath = settings.get("coltPath")

                # Export COLT project
                coltProjectFilePath = self.exportProject()

                # Add project to workset file
                self.addToWorkingSet(coltProjectFilePath)

                # Run COLT
                self.initAndConnect(settings, coltProjectFilePath)

                # Authorize and start live
                colt_rpc.runAfterAuthorization = colt_rpc.startLive
                colt_rpc.authorize(self.window)

        def establishConnection(self, port):
                ColtConnection.port = port
                sublime.status_message("Established connection with COLT on port " + port)
                time.sleep(2)

        def initAndConnect(self, settings, projectPath): 
                sublime.status_message("Trying to establish connection with COLT...")

                port = self.locateCOLTServicePort(projectPath)
                if not port is None :
                        self.establishConnection(port)
                        return port

                self.runCOLT(settings)
                
                timeout = 20
                while timeout > 0 :
                        time.sleep(0.3)
                        timeout -= 0.3

                        port = self.locateCOLTServicePort(projectPath)
                        if not port is None :
                                self.establishConnection(port)
                                return port

                sublime.error_message("Can't establish connection with COLT")
                return None

        def locateCOLTServicePort(self, projectPath): 
                port = self.getRPCPortForProject(projectPath)
                if port is None :
                        return None

                try :
                        colt_rpc.runRPC(port, "ping", None)                        
                except Exception:
                        return None

                return port                

        def getProjectWorkingDir(self, projectPath): 
                storageFilePath = os.path.expanduser("~") + os.sep + ".colt" + os.sep + "storage.xml"

                if not os.path.exists(storageFilePath) :
                        return None

                projectSubDir = None
                storageRootElement = parse(storageFilePath).getroot()
                for storageElement in storageRootElement :
                        if storageElement.attrib["path"] == projectPath :
                                projectSubDir = storageElement.attrib["subDir"]
                                break

                if projectSubDir is None :
                        return None

                return os.path.expanduser("~") + os.sep + ".colt" + os.sep + "storage" + os.sep + projectSubDir

        def getRPCPortForProject(self, projectPath):
                storageDir = self.getProjectWorkingDir(projectPath)
                if storageDir is None :
                        return None

                rpcInfoFilePath = storageDir + os.sep + "rpc.info"
                if not os.path.exists(rpcInfoFilePath) :
                        return None

                timePassedSinceModification = int(calendar.timegm(time.gmtime())) - int(os.path.getmtime(rpcInfoFilePath))
                if (timePassedSinceModification > 2) :
                        return None

                with open(rpcInfoFilePath, "r") as rpcInfoFile :
                        return rpcInfoFile.read().split(":")[1]

        def onCOLTPathInput(self, inputPath):
                if inputPath and os.path.exists(inputPath) :
                        settings = sublime.load_settings(RunWithColtCommand.PREFERENCES_NAME)
                        settings.set("coltPath", inputPath)
                        sublime.save_settings(RunWithColtCommand.PREFERENCES_NAME)
                        self.run()
                else :
                        sublime.error_message("COLT path specified is invalid")


        def addToWorkingSet(self, newProjectPath):
                workingSetFilePath = os.path.expanduser("~") + os.sep + ".colt" + os.sep + "workingset.xml"
                projectsList = []

                # Populate projects list
                if os.path.exists(workingSetFilePath) :
                        workingSetElement = parse(workingSetFilePath).getroot()
                        for projectElement in workingSetElement :
                                projectPath = projectElement.attrib["path"]
                                if projectPath :
                                        projectsList.append(projectPath)

                # Remove project path from the list
                projectsList = filter(lambda projectPath : projectPath != newProjectPath, projectsList)

                # Push new project
                projectsList.insert(0, newProjectPath)

                # Save the list
                workingSetElement = Element("workingset")
                workingSetElement.set("openRecent", "true")

                for projectPath in projectsList :
                        projectElement = SubElement(workingSetElement, "project")
                        projectElement.set("path", projectPath)

                workingSetFile = open(workingSetFilePath, "w")
                workingSetFile.write(tostring(workingSetElement))
                workingSetFile.close()

        def runCOLT(self, settings):
                coltPath = settings.get("coltPath")

                # TODO: change to sublime.platform()
                if (os.name == "posix") :
                        # Mac, I hope
                        subprocess.Popen(["open", "-n", "-a", coltPath])
                else :
                        # Windows, I suppose
                        # TODO: implement
                        print "Unimplemented"                        

        def exportProject(self):
                mainDocumentPath = self.window.active_view().file_name()
                mainDocumentName = os.path.splitext(os.path.basename(mainDocumentPath))[0]
                basedir = os.path.dirname(mainDocumentPath) # TODO: ask user for base dir?

                # Root
                rootElement = Element("xml")

                rootElement.set("projectName", mainDocumentName)
                rootElement.set("projectType", "JS")

                # Paths
                pathsElement = SubElement(rootElement, "paths")
                self.createElement("sources-set", "**/*.js, -lib/*.js", pathsElement)
                self.createElement("excludes-set", "out/**, .git/**, .*/**, **/*bak___", pathsElement)
                self.createElement("reloads-set", "**/*.htm*, **/*.css, **/*.png", pathsElement)        

                # Build
                buildElement = SubElement(rootElement, "build")
                self.createElement("main-document", mainDocumentPath, buildElement)
                self.createElement("use-custom-output-path", "false", buildElement)
                self.createElement("out-path", "", buildElement)

                # Live
                liveElement = SubElement(rootElement, "live")
                # Settings
                settingsElement = SubElement(liveElement, "settings")
                self.createElement("clear-log", "false", settingsElement)
                self.createElement("disconnect", "true", settingsElement)

                # Launch
                launchElement = SubElement(liveElement, "launch")
                self.createElement("launcher", "DEFAULT", launchElement)

                # Inner live
                innerLiveElement = SubElement(liveElement, "live")
                self.createElement("paused", "false", innerLiveElement)
                self.createElement("max-loop", "10000", innerLiveElement)
                self.createElement("live-html-edit", "true", innerLiveElement)
                self.createElement("disable-in-minified", "true", innerLiveElement)

                coltProjectFilePath = basedir + os.sep + "autogenerated.colt"
                coltProjectFile = open(coltProjectFilePath, "w")
                coltProjectFile.write(tostring(rootElement))
                coltProjectFile.close()

                return coltProjectFilePath

        def createElement(self, name, value, parentElement):
                element = SubElement(parentElement, name)
                element.text = value
                return element

