import os.path
import subprocess
import sublime

from xml.etree.ElementTree import Element, SubElement, tostring, parse

from xml.etree import ElementTree # part of python distribution
from elementtree import SimpleXMLTreeBuilder # part of your codebase
if (sublime.platform() != "osx") and (sublime.platform() != "windows") :
        ElementTree.XMLTreeBuilder = SimpleXMLTreeBuilder.TreeBuilder

class ColtPreferences(object):
        NAME = "Preferences.sublime-settings"

def isColtFile(view):
        if view.file_name() is None :
                return False

        filename = view.file_name().lower()
        return filename.endswith(".js") or filename.endswith(".htm") or filename.endswith(".html")

def getProjectWorkingDir(projectPath): 
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

def addToWorkingSet(newProjectPath):
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

def runCOLT(settings, projectPath):
        coltPath = settings.get("coltPath")

        platform = sublime.platform()

        command = []

        if platform == "osx" :
            command.append("open")
            command.append("-n")
            command.append("-a")
            command.append(coltPath)
        elif platform == "windows" :
                if not coltPath.endswith('colt.exe') :
                    coltPath += "\\colt.exe"

                command.append(coltPath)  
        else :
                # sublime.error_message("Unsupported platform: " + platform)
                command.append(coltPath)
        if not projectPath == None :
            command.append(projectPath)

        subprocess.Popen(command)                 

def exportProject(window, mainDocumentPath, basedir, overrides):
        launcherType = overrides["launcherType"]
        
        mainDocumentName = ""
        if  mainDocumentPath != "" :
            mainDocumentName = os.path.splitext(os.path.basename(mainDocumentPath))[0]

        # Root
        rootElement = Element("xml")

        rootElement.set("projectType", "JS")
        rootElement.set("isPlugin", "true")

        # Paths
        pathsElement = SubElement(rootElement, "paths")
        createElement("excludes-set", "out/**, .git/**, .*/**, **/*bak___", pathsElement)      

        # Build
        buildElement = SubElement(rootElement, "build")
        createElement("main-document", mainDocumentPath, buildElement)
        createElement("use-custom-output-path", "false", buildElement)
        createElement("out-path", "", buildElement)

        # Live
        liveElement = SubElement(rootElement, "live")
        # Settings
        settingsElement = SubElement(liveElement, "settings")
        createElement("clear-log", "false", settingsElement)
        createElement("disconnect", "true", settingsElement)

        # Launch
        launchElement = SubElement(liveElement, "launch")
        createElement("launcher", launcherType, launchElement)

        # Inner live
        innerLiveElement = SubElement(liveElement, "live")
        createElement("paused", "false", innerLiveElement)
        createElement("max-loop", "10000", innerLiveElement)
        createElement("simple-reload", "false", innerLiveElement)
        createElement("disable-in-minified", "true", innerLiveElement)

        coltProjectFilePath = basedir + os.sep + "autogenerated.colt"
        if os.path.exists(coltProjectFilePath) :
            rootElement = parse(coltProjectFilePath).getroot()
            # override launcher type if possible (BROWSER/NODE_WEBKIT)
            oldMain = rootElement.find("build").find("main-document").text
            if (mainDocumentPath == "") and oldMain.endswith(".js") and (launcherType != "NODE_JS") :
                # can't override NODE_JS
                return None
                
            launch = rootElement.find("live").find("launch")
            launch.find("launcher").text = launcherType
        
        if (mainDocumentPath != "") :
            rootElement.set("projectName", mainDocumentName)
            rootElement.find("build").find("main-document").text = mainDocumentPath
            
            try :
                rootElement.find("build").find("main-document").text = basedir + os.path.sep + overrides["colt-main-document"]
            except KeyError :
                pass
        
            if not mainDocumentPath.endswith(".js") :
                settings = sublime.load_settings(ColtPreferences.NAME)
                browserPathSetting = settings.get("coltBrowserPath", None)
                if browserPathSetting != None :
                
                    # set custom html launcher
                    launch = rootElement.find("live").find("launch")
                
                    browserPath = launch.find("browser-path")
                    if browserPath is None :
                        createElement("browser-path", "", launch)
                        browserPath = launch.find("browser-path")
                
                    browserPath.text = browserPathSetting


        coltProjectFile = open(coltProjectFilePath, "w")
        coltProjectFile.write(tostring(rootElement))
        coltProjectFile.close()

        return coltProjectFilePath

def createElement(name, value, parentElement):
        element = SubElement(parentElement, name)
        element.text = value
        return element                       
