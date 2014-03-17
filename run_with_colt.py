import sublime, sublime_plugin
import colt, colt_rpc
import functools
import os.path
import json
import re

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

def isAutosaveEnabled():
        settings = sublime.load_settings(ColtPreferences.NAME)
        return settings.get("autosave", False)

class ToggleAutosaveCommand(sublime_plugin.ApplicationCommand):
        def run(self):
                currentValue = isAutosaveEnabled()
                settings = sublime.load_settings(ColtPreferences.NAME)
                settings.set("autosave", not currentValue)
                sublime.save_settings(ColtPreferences.NAME)

        def description(self):
                if isAutosaveEnabled() :
                        return "Disable Autosave"
                else :
                        return "Enable Autosave"

class ColtAutosaveListener(sublime_plugin.EventListener):
        
        def on_modified(self, view):
                if colt.isColtFile(view) and colt_rpc.isConnected() and colt_rpc.hasActiveSessions() and isAutosaveEnabled() :
                        view.run_command("save")


class ColtCompletitions(sublime_plugin.EventListener):
        
        def on_query_completions(self, view, prefix, locations):                
                if not colt.isColtFile(view) :
                        return []

                position = getPositionEnd(view)
                
                requestVars = False

                if view.substr(position - 1) == "." :
                        position = position - 1
                else :
                        word = view.word(getPosition(view))
                        wordStart = word.begin()
                        if view.substr(wordStart - 1) == "." :
                                position = wordStart - 1
                        else :
                                if re.match ("\s*", view.substr(word)) != None :
                                    requestVars = True
                                else :
                                    return []

                if not colt_rpc.isConnected() or not colt_rpc.hasActiveSessions() :
                        return []

                response = None
                if requestVars == True :
                    response = colt_rpc.evaluateExpression(view.file_name(), "?", position, getContent(view))
                else :
                    response = colt_rpc.getContextForPosition(view.file_name(), position, getContent(view), "PROPERTIES")
                
                if response.has_key("error") :
                        return []

                result = response["result"]
                completitions = []
                if not result is None :
                        resultJSON = json.loads(result)
                        for resultStr in resultJSON :
                                if "{})" in resultStr :
                                        resultStr = resultStr.replace("{})", "")

                                replaceStr = resultStr
                                displayStr = resultStr
                                cursiveStr = ""

                                if "(" in resultStr :
                                        replaceStr = resultStr[:resultStr.index("(")]
                                        displayStr = replaceStr
                                        cursiveStr = resultStr

                                if cursiveStr != "" :
                                        displayStr = cursiveStr
                                        cursiveStr = ""
                                completitions.append((displayStr + "\t" + cursiveStr + "[COLT]", replaceStr.replace('$', '\$')))

                return completitions

class AbstractColtRunCommand(sublime_plugin.WindowCommand):
        runArg = None
        def run(self, nodeJs = None):
                self.runArg = nodeJs
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

                # if not here, any colt.runCOLT() call will fail, however plugin can still connect to running COLT
                return sublime.load_settings(ColtPreferences.NAME)    

        def onCOLTPathInput(self, inputPath):
                if inputPath and os.path.exists(inputPath) :
                        settings = sublime.load_settings(ColtPreferences.NAME)
                        settings.set("coltPath", inputPath)
                        sublime.save_settings(ColtPreferences.NAME)
                        self.run(self.runArg)
                else :
                        sublime.error_message("COLT path specified is invalid")   

        def is_enabled(self):
                if self.window.active_view() is None :
                        return False
                return colt.isColtFile(self.window.active_view())

class GetAllCountsCommand(sublime_plugin.WindowCommand):
        ranges = []
    
        def run(self):
            # but 1st, clear every region this command could have created
            for p in GetAllCountsCommand.ranges:
                p[0].erase_regions(p[1])
                
            GetAllCountsCommand.ranges = []
                        
            if ColtConnection.activeSessions > 0:
                
                # getMethodCounts
                # {u'jsonrpc': u'2.0', u'id': 77, u'result': [{u'count': 1, u'position': 339, u'filePath': u'/Users/makc/Downloads/d3/bubles.js'}, ...
                resultJSON = colt_rpc.getMethodCounts()
                
                if resultJSON.has_key("error") or resultJSON["result"] is None :
                        # sublime.error_message("Can't read method counts")
                        return
                        
                for info in resultJSON["result"]:

                    position = info["position"]
                    filePath = info["filePath"]
                                        
                    count = info["count"]
                    
                    if count > 0:
                        if count > 9:
                            count = "infinity"
                    
                        for view in self.window.views():
                            if view.file_name() == filePath:
                                
                                # do not show count if there is an error in this line
                                noError = True
                                row = view.rowcol( position )[0]
                                for p in IdleWatcher.ranges:
                                    if p[4] == view.file_name() :
                                        if (row == view.rowcol( p[2] )[0]) :
                                            noError = False
                                
                                if noError :
                                    view.add_regions("counts." + str(position), [sublime.Region(position)],
                                        "scope", "../COLT/icons/" + str(count) + "@2x", sublime.HIDDEN)
                                    GetAllCountsCommand.ranges.append([view, "counts." + str(position)])
                    

class ColtShowLastErrorsCommand(sublime_plugin.WindowCommand):

    def run(self):
        items = []
        for p in IdleWatcher.ranges:
            items.append([p[3], "\tat " + p[4]])
        self.window.show_quick_panel(items, self.on_done)

    def on_done(self, picked):
        if picked == -1:
            return
        if picked >= len(IdleWatcher.ranges):
            return
        p = IdleWatcher.ranges[picked]
        self.window.open_file( p[4] + ":" + str(p[5]), sublime.ENCODED_POSITION )
        
    def is_enabled(self):
        return colt_rpc.isConnected() and colt_rpc.hasActiveSessions()


# ST2 version of http://www.sublimetext.com/docs/plugin-examples Idle Watcher
class IdleWatcher(sublime_plugin.EventListener):
    pending = 0
    ranges = []
    runtimeError = { "message" : "" }
    
    @staticmethod
    def clearErrors():
        for p in IdleWatcher.ranges:
            if  p[0] != None :
                p[0].erase_regions(p[1])

        IdleWatcher.ranges = []        
    
    def handleTimeout(self, view):
        self.pending = self.pending - 1
        if self.pending == 0:
            # There are no more queued up calls to handleTimeout, so it must have
            # been 800ms since the last modification
            self.onIdle(view)

    def onModified(self, view):
        self.pending = self.pending + 1
        # Ask for handleTimeout to be called in 800ms
        sublime.set_timeout(functools.partial(self.handleTimeout, view), 800)

    def printLogs(self):
        if ColtConnection.activeSessions > 0:
            resultJSON = colt_rpc.getLastLogMessages()
            if resultJSON.has_key("error") or resultJSON["result"] is None :
                return
                
            resultJSON2 = colt_rpc.getLastRuntimeError();
            if not (resultJSON2.has_key("error") or resultJSON2["result"] is None) :
                if IdleWatcher.runtimeError["message"] != resultJSON2["result"]["errorMessage"] :
                    # new runtime error - add to errors list
                    IdleWatcher.runtimeError = {
                        "position" : resultJSON2["result"]["position"],
                        "row" : resultJSON2["result"]["row"],
                        "filePath" : resultJSON2["result"]["filePath"],
                        "message" : resultJSON2["result"]["errorMessage"] }
                    resultJSON["result"].append(IdleWatcher.runtimeError)

            if len(resultJSON["result"]) > 0 :
                
                openConsole = False
                syntaxErrors = []
                
                for info in resultJSON["result"] :
                    if info["position"] > -1 :
                        # syntax error
                        if (len (info["message"]) == 0) :
                            # empty syntax error message signals that corresponding page was reloaded
                            for p in IdleWatcher.ranges:
                                if p[4] == info["filePath"]:
                                    if  p[0] != None :
                                        p[0].erase_regions(p[1])
                                    IdleWatcher.ranges.remove(p)
                        else :
                            # add to the list and print
                            syntaxErrors.append(info)
                            print("[COLT] " + info["message"])
                    else :
                        # just print it
                        print("[COLT] " + info["message"])
                        try :
                            if info["source"] == "License" :
                                openConsole = True
                        except KeyError :
                            # old colt
                            if re.match("^Maximum updates.*", info["message"]) :
                                openConsole = True
                    
                # now show syntax errors
                for info in syntaxErrors :
                    viewFound = None
                    for view in sublime.active_window().views():
                        if view.file_name() == info["filePath"]:
                            position = info["position"]
                            view.add_regions("error." + str(position), [sublime.Region(position)],
                                "scope", "../COLT/icons/error@2x", sublime.HIDDEN)
                            viewFound = view
                    IdleWatcher.ranges.append([viewFound, "error." + str(info["position"]), info["position"], info["message"], info["filePath"], info["row"]])
                        
                if openConsole :
                    sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": False})
            
            # also show errors in views opened later
            for p in IdleWatcher.ranges:
                if (p[0] == None) or (p[0].window() == None) :
                    for view in sublime.active_window().views():
                        if view.file_name() == p[4]:
                            view.add_regions(p[1], [sublime.Region(p[2])],
                                "scope", "../COLT/icons/error@2x", sublime.HIDDEN)
                            p[0] = view
                
        else :
            # clear all ranges
            IdleWatcher.clearErrors()
                
    def onIdle(self, view):
        #print "No activity in the past 800ms"
        self.printLogs()
        sublime.active_window().run_command("get_all_counts")
        sublime.set_timeout(functools.partial(self.onModified, view), 800)

    def on_modified(self, view):
        self.onModified(view)

    def on_selection_modified(self, view):
        self.onModified(view)
        
        # check selection for errors
        row = view.rowcol( view.sel()[0].begin() )[0]
        
        message = ""
        for p in IdleWatcher.ranges:
            if p[4] == view.file_name() :
                if (row == view.rowcol( p[2] )[0]) :
                    message = p[3]
                    
        # todo function signatures ??
        
        view.erase_status("colt_error")
        if (message != "") :
            view.set_status("colt_error", message)
    
    def on_activated(self, view):
        self.onModified(view)

                
class ColtReloadScriptCommand(sublime_plugin.WindowCommand):

        def run(self):
                view = self.window.active_view()

                fileName = view.file_name()
                position = getWordPosition(view)
                content = getContent(view)

                resultJSON = colt_rpc.reloadScriptAt(fileName, position, content)

        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt.isColtFile(view) and colt_rpc.isConnected() and colt_rpc.hasActiveSessions()

class ColtGoToDeclarationCommand(sublime_plugin.WindowCommand):

        def run(self):
                view = self.window.active_view()

                fileName = view.file_name()
                position = getWordPosition(view)
                content = getContent(view)

                resultJSON = colt_rpc.getDeclarationPosition(fileName, position, content)

                if resultJSON.has_key("error") or resultJSON["result"] is None :
                        # sublime.error_message("Can't find a declaration")
                        return

                row = resultJSON["result"]["optionalRow"]
                filePath = resultJSON["result"]["filePath"]

                targetView = self.window.open_file(filePath + ":" + str(row), sublime.ENCODED_POSITION)

        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt.isColtFile(view) and colt_rpc.isConnected() and colt_rpc.hasActiveSessions()

class ColtRunFunctionCommand(sublime_plugin.WindowCommand):

        def run(self):
                view = self.window.active_view()

                fileName = view.file_name()
                position = getWordPosition(view)
                content = getContent(view)
                
                methodId = colt_rpc.getMethodId(fileName, position, content)

                if methodId is None :
                        sublime.error_message("Can't figure out the function ID")
                        return

                if methodId.startswith('"') :
                        methodId = methodId[1:len(methodId)-1]

                colt_rpc.runMethod(methodId)
                
                self.window.run_command("get_all_counts")
        
        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt.isColtFile(view) and colt_rpc.isConnected() and colt_rpc.hasActiveSessions()
        
class ColtResetCallCountsCommand(sublime_plugin.WindowCommand):
        def run(self):
                colt_rpc.resetCallCounts()

                self.window.run_command("get_all_counts")

        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt.isColtFile(view) and colt_rpc.isConnected() and colt_rpc.hasActiveSessions()

class ColtViewCallCountCommand(sublime_plugin.WindowCommand):
        def run(self):
                view = self.window.active_view()

                outputPanel = self.window.get_output_panel("COLT")
                outputPanel.set_scratch(True)
                outputPanel.set_read_only(False)
                outputPanel.set_name("COLT")
                self.window.run_command("show_panel", {"panel": "output.COLT"})
                self.window.set_view_index(outputPanel, 1, 0)
                
                position = getWordPosition(view)
                resultJSON = colt_rpc.getCallCount(view.file_name(), position, getContent(view))

                if resultJSON.has_key("result") :
                        position = getPosition(view)
                        word = view.word(position)

                        result = resultJSON["result"]
                        if result is None :
                                self.appendToConsole(outputPanel, "Call count is not available")
                        else :
                                self.appendToConsole(outputPanel, "Call count: " + str(result))

        def appendToConsole(self, outputPanel, text):
                edit = outputPanel.begin_edit("COLT output")
                edit = outputPanel.begin_edit()
                outputPanel.insert(edit, outputPanel.size(), text + '\n')
                outputPanel.end_edit(edit)
                outputPanel.show(outputPanel.size())

        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt.isColtFile(view) and colt_rpc.isConnected() and colt_rpc.hasActiveSessions()

class ColtViewValueCommand(sublime_plugin.WindowCommand):
        def run(self):
                view = self.window.active_view()

                outputPanel = self.window.get_output_panel("COLT")
                outputPanel.set_scratch(True)
                outputPanel.set_read_only(False)
                outputPanel.set_name("COLT")
                self.window.run_command("show_panel", {"panel": "output.COLT"})
                self.window.set_view_index(outputPanel, 1, 0)
                
                position = getWordPosition(view)
                
                expression = None
                for sel in view.sel() :
                    if expression is None :
                        expression = view.substr(sel)
                
                resultJSON = colt_rpc.evaluateExpression(view.file_name(), expression, position, getContent(view))
                if resultJSON.has_key("result") :
                        position = getPosition(view)
                        word = view.word(position)

                        result = resultJSON["result"]
                        if result is None :
                                self.appendToConsole(outputPanel, view.substr(word) + " value: unknown")
                        else :
                                self.appendToConsole(outputPanel, result)

        def appendToConsole(self, outputPanel, text):
                edit = outputPanel.begin_edit("COLT output")
                edit = outputPanel.begin_edit()
                outputPanel.insert(edit, outputPanel.size(), text + '\n')
                outputPanel.end_edit(edit)
                outputPanel.show(outputPanel.size())

        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt.isColtFile(view) and colt_rpc.isConnected() and colt_rpc.hasActiveSessions()
        
class ColtReloadCommand(sublime_plugin.WindowCommand):
        def run(self):
                IdleWatcher.clearErrors()
                colt_rpc.reload()

        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt_rpc.isConnected() and colt_rpc.hasActiveSessions()

class ColtClearLogCommand(sublime_plugin.WindowCommand):
        def run(self):
                colt_rpc.clearLog()

        def is_enabled(self):
                view = self.window.active_view()
                if view is None :
                        return False
                return colt_rpc.isConnected() and colt_rpc.hasActiveSessions()

class StartColtCommand(AbstractColtRunCommand):

        def run(self, nodeJs = None):
                settings = self.getSettings()                
                
                # TODO: detect if colt is running and skip running it if it is
                colt.runCOLT(settings, None)

        def is_enabled(self):
                return True


class RunWithColtCommand(AbstractColtRunCommand):
    
        html = None

        def run(self, nodeJs = None):
                settings = self.getSettings()
                
                # Check the file name
                file = self.window.active_view().file_name()
                
                coltProjectFilePath = ""

                # Export COLT project
                if nodeJs == "True" :
                    coltProjectFilePath = colt.exportProject(self.window, file)
                else :
                    if re.match('.*\\.html?$', file): # r'' for v3
                        RunWithColtCommand.html = file

                    if RunWithColtCommand.html is None :
                        # Try to run existing project
                        foundExistingProject = False
                        folders = self.window.folders()
                        if len(folders) > 0:
                            coltProjectFilePath = folders[0] + os.sep + "autogenerated.colt"
                            if os.path.exists(coltProjectFilePath) :
                                foundExistingProject = True
                        
                        if not foundExistingProject :
                            # Error message
                            sublime.error_message('This tab is not html file. Please open project main html and try again.')
                            return

                    else :
                        # Start using (possibly) different html file as main
                        coltProjectFilePath = colt.exportProject(self.window, RunWithColtCommand.html)

                # Add project to workset file
                colt.addToWorkingSet(coltProjectFilePath)

                if colt_rpc.locateCOLTServicePort(coltProjectFilePath) is None:
                    colt_rpc.runAfterAuthorization = None
                else:
                    colt_rpc.runAfterAuthorization = colt_rpc.startLive
                # Run COLT
                colt_rpc.initAndConnect(settings, coltProjectFilePath)

                # Authorize
                colt_rpc.authorize(self.window)                                                          
