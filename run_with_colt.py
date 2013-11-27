import sublime, sublime_plugin
import colt, colt_rpc
import os.path
import json

from colt import ColtPreferences
from colt_rpc import ColtConnection

def getWordPosition(view):
        position = getPosition(view)
        return view.word(position).end()

def getPosition(view):
        for sel in view.sel() :
                return sel

        return None

def getPositionEnd(view):
        position = getPosition(view)
        if position is None :
                return - 1

        return position.end()

def getContent(view):
        return view.substr(sublime.Region(0, view.size()))

class ColtCompletitions(sublime_plugin.EventListener):
        
        def on_query_completions(self, view, prefix, locations):                
                if not colt.isColtFile(view) :
                        return []

                position = getPositionEnd(view)

                if view.substr(position - 1) == "." :
                        position = position - 1
                else :
                        wordStart = view.word(getPosition(view)).begin()
                        if view.substr(wordStart - 1) == "." :
                                position = wordStart - 1
                        else :
                                return []

                if not colt_rpc.isConnected() or not colt_rpc.hasActiveSessions() :
                        return []

                response = colt_rpc.getContextForPosition(view.file_name(), position, getContent(view), "PROPERTIES")
                if response.has_key("error") :
                        return []

                result = response["result"]
                if not result is None :
                        completitions = []
                        resultJSON = json.loads(result)
                        for resultStr in resultJSON :
                                completitions.append((resultStr + "\t(COLT suggested)", resultStr))

                return completitions

class AbstractColtRunCommand(sublime_plugin.WindowCommand):
        def run(self):
                return

        def getSettings(self):
                settings = sublime.load_settings(ColtPreferences.NAME)
                if not settings.has("coltPath") :                        
                        sublime.error_message("COLT path is not specified, please enter the path")
                        self.window.show_input_panel("COLT Path:", "", self.onCOLTPathInput, None, None)
                        return

                settings = sublime.load_settings(ColtPreferences.NAME)
                coltPath = settings.get("coltPath")
                
                if not os.path.exists(coltPath) :
                        sublime.error_message("COLT path specified is invalid, please enter the correct path")
                        self.window.show_input_panel("COLT Path:", "", self.onCOLTPathInput, None, None)
                        return

                return sublime.load_settings(ColtPreferences.NAME)    

        def onCOLTPathInput(self, inputPath):
                if inputPath and os.path.exists(inputPath) :
                        settings = sublime.load_settings(ColtPreferences.NAME)
                        settings.set("coltPath", inputPath)
                        sublime.save_settings(ColtPreferences.NAME)
                        self.run()
                else :
                        sublime.error_message("COLT path specified is invalid")   

        def is_enabled(self):
                if self.window.active_view() is None :
                        return False
                return colt.isColtFile(self.window.active_view())

class ColtViewValueCommand(sublime_plugin.WindowCommand):
        def run(self):
                view = self.window.active_view()
                position = getWordPosition(view)
                resultJSON = colt_rpc.getContextForPosition(view.file_name(), position, getContent(view), "VALUE")
                if resultJSON.has_key("result") :
                        position = getPosition(view)
                        word = view.word(position)

                        result = resultJSON["result"]
                        if result is None :
                                print view.substr(word) + " value: unknown"
                        else :
                                print view.substr(word) + " value: " + result                        

        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt.isColtFile(view) and colt_rpc.isConnected() and colt_rpc.hasActiveSessions()
        
class ColtReloadCommand(sublime_plugin.WindowCommand):
        def run(self):
                colt_rpc.reload()

        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt.isColtFile(view) and colt_rpc.isConnected() and colt_rpc.hasActiveSessions()

class StartColtCommand(AbstractColtRunCommand):

        def run(self):
                settings = self.getSettings()                
                
                # TODO: detect if colt is running and skip running it if it is
                colt.runCOLT(settings)

class OpenInColtCommand(AbstractColtRunCommand):

        def run(self):
                settings = self.getSettings()

                # Export COLT project
                coltProjectFilePath = colt.exportProject(self.window)

                # Add project to workset file
                colt.addToWorkingSet(coltProjectFilePath)

                # Run COLT
                colt_rpc.initAndConnect(settings, coltProjectFilePath)

                # Authorize
                colt_rpc.runAfterAuthorization = None
                colt_rpc.authorize(self.window)                                                          

class RunWithColtCommand(AbstractColtRunCommand):

        def run(self):
                settings = self.getSettings()

                # Export COLT project
                coltProjectFilePath = colt.exportProject(self.window)

                # Add project to workset file
                colt.addToWorkingSet(coltProjectFilePath)

                # Run COLT
                colt_rpc.initAndConnect(settings, coltProjectFilePath)

                # Authorize and start live
                colt_rpc.runAfterAuthorization = colt_rpc.startLive
                colt_rpc.authorize(self.window)                                                          
