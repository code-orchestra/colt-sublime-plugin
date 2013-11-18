import sublime, sublime_plugin
import os.path

from xml.etree.ElementTree import Element, SubElement, tostring, parse

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
                self.runCOLT(settings)

        def onCOLTPathInput(self, inputPath):
                if inputPath and os.path.exists(inputPath) :
                        settings = sublime.load_settings("Preferences.sublime-settings")
                        settings.set("coltPath", inputPath)
                        sublime.save_settings("Preferences.sublime-settings")
                        run()
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
                # TODO: implement

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

