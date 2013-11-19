import sublime, sublime_plugin
import os.path
import subprocess
import urllib2
import json
import calendar, time

from xml.etree.ElementTree import Element, SubElement, tostring, parse

class ColtConnection(object):
        port = -1

class RunWithColtCommand(sublime_plugin.WindowCommand):
        
        def run(self):
                settings = sublime.load_settings("Preferences.sublime-settings")
                if not settings.has("coltPath") :                        
                        sublime.error_message("COLT path is not specified, please enter the path")
                        self.window.show_input_panel("COLT Path:", "", self.onCOLTPathInput, None, None)
                        return
                
                settings = sublime.load_settings("Preferences.sublime-settings")
                coltPath = settings.get("coltPath")
                
                if not os.path.exists(coltPath) :
                        sublime.error_message("COLT path specified is invalid, please enter the correct path")
                        self.window.show_input_panel("COLT Path:", "", self.onCOLTPathInput, None, None)
                        return

                settings = sublime.load_settings("Preferences.sublime-settings")
                coltPath = settings.get("coltPath")

                # Export COLT project
                coltProjectFilePath = self.exportProject()

                # Add project to workset file
                self.addToWorkingSet(coltProjectFilePath)

                # Run COLT
                self.initAndConnect(settings, coltProjectFilePath)

        def establishConnection(self, port):
                ColtConnection.port = port
                sublime.status_message("Established connection with COLT on port " + port)

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

                return None

        def locateCOLTServicePort(self, projectPath): 
                port = self.getRPCPortForProject(projectPath)
                if port is None :
                        return None

                try :
                        self.runRPC(port, "ping", None)                        
                except Exception:
                        return None

                return port                

        def runRPC(self, port, methodName, params):                  
                jsonRequest = None
                if (params is None) :
                        jsonRequest = { "jsonrpc" : "2.0", "method" : methodName, "id": 1 }
                else :
                        jsonRequest = { "jsonrpc" : "2.0", "method" : methodName, "params": params, "id": 1 }                        

                jsonRequestStr = json.dumps(jsonRequest)

                req = urllib2.Request("http://localhost:" + str(port) + "/rpc/coltService")
                response = urllib2.urlopen(req, jsonRequestStr)
                return json.loads(response.read())

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

        def getSecurityToken(self): 
                settings = sublime.load_settings("Preferences.sublime-settings")
                if not settings.has("securityToken") :
                        return None

                return settings.get("securityToken")

        def getRPCPortForProject(self, projectPath):
                storageDir = self.getProjectWorkingDir(projectPath)
                if storageDir is None :
                        return None

                rpcInfoFilePath = storageDir + os.sep + "rpc.info"
                if not os.path.exists(rpcInfoFilePath) :
                        return None

                #timePassedSinceModification = int(calendar.timegm(time.gmtime())) - int(os.path.getmtime(rpcInfoFilePath))
                #if (timePassedSinceModification > 2) :
                #        return None

                with open(rpcInfoFilePath, "r") as rpcInfoFile :
                        return rpcInfoFile.read().split(":")[1]

        def onCOLTPathInput(self, inputPath):
                if inputPath and os.path.exists(inputPath) :
                        settings = sublime.load_settings("Preferences.sublime-settings")
                        settings.set("coltPath", inputPath)
                        sublime.save_settings("Preferences.sublime-settings")
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

                coltProjectFilePath = basedir + os.sep + mainDocumentName + ".colt"
                coltProjectFile = open(coltProjectFilePath, "w")
                coltProjectFile.write(tostring(rootElement))
                coltProjectFile.close()

                return coltProjectFilePath

        def createElement(self, name, value, parentElement):
                element = SubElement(parentElement, name)
                element.text = value
                return element

