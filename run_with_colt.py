import sublime, sublime_plugin
import os.path

from xml.etree.ElementTree import Element, SubElement, tostring

class RunWithColtCommand(sublime_plugin.TextCommand):
        def run(self, edit):
                mainDocument = self.view.file_name()
                basedir = os.path.dirname(mainDocument) # TODO: ask user for base dir?

                settings = sublime.load_settings("Preferences.sublime-settings")
                if not settings.has("coltPath") :
                        sublime.error_message("COLT path is not specified, go to Preferences -> COLT")
                        return

                coltPath = settings.get("coltPath")

                print coltPath

                # Root
                rootElement = Element("xml")

                rootElement.set("projectName", mainDocument) # TODO: file name only
                rootElement.set("projectType", "JS")

                # Paths
                pathsElement = SubElement(rootElement, "paths")
                self.createElement("sources-set", "**/*.js, -lib/*.js", pathsElement)
                self.createElement("excludes-set", "out/**, .git/**, .*/**, **/*bak___", pathsElement)
                self.createElement("reloads-set", "**/*.htm*, **/*.css, **/*.png", pathsElement)        

                # Build
                buildElement = SubElement(rootElement, "build")
                self.createElement("main-document", mainDocument, buildElement)
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

                print tostring(rootElement)
                

        def createElement(self, name, value, parentElement):
                element = SubElement(parentElement, name)
                element.text = value
                return element

