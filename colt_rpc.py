import sublime
import urllib2
import json
import colt
import calendar, time
import os
import threading

from colt import ColtPreferences

runAfterAuthorization = None

class ColtConnection(object):
    port = -1
    messageId = 1
    activeSessions = 0

def coltStateUpdate():
    if isConnected() :
        ColtConnection.activeSessions = getActiveSessionsCount()

def isConnected():
    return ColtConnection.port != -1

def hasActiveSessions():
    return ColtConnection.activeSessions > 0

def disconnect():
    ColtConnection.port = -1    
    ColtConnection.messageId = 1
    ColtConnection.activeSessions = 0

    sublime.status_message("Disconnected from COLT")

def runAfterAuthorization():
    if not runAfterAuthorization is None :
        runAfterAuthorization()
        runAfterAuthorization = None
        return

def authorize(window):
    if getSecurityToken() is None :
        makeNewSecurityToken(True, window)
    else :
        runAfterAuthorization()

def getSecurityToken(): 
    settings = sublime.load_settings(ColtPreferences.NAME)
    if not settings.has("securityToken") :
            return None

    return settings.get("securityToken")

def makeNewSecurityToken(newRequest, window):
    if newRequest :
        try :
            requestShortCode()
        except Exception :
            sublime.error_message("Can't request an authorization key from COLT. Make sure COLT is active and running")
            return

    window.show_input_panel("Enter the short key displayed in COLT:", "", onShortKeyInput, None, None)

def onShortKeyInput(shortCode):
    if shortCode :
        try :
            token = obtainAuthToken(shortCode)
            if token is None :
                sublime.error_message("Invalid short code entered")        
                authorize()

                settings = sublime.load_settings(ColtPreferences.NAME)
                settings.set("securityToken", token)
                sublime.save_settings(ColtPreferences.NAME)
                sublime.status_message("Successfully authorized with COLT")

                runAfterAuthorization()
        except Exception:
            sublime.error_message("Can't authorize with COLT. Make sure COLT is active and running")
            return
    else :
        sublime.error_message("Short authorization key can't be empty")  
        authorize(sublime.active_window())

def obtainAuthToken(shortCode):
    response = runRPC(ColtConnection.port, "obtainAuthToken", [ shortCode ])
    if response.has_key("error") :
            return None

    return response["result"]

def requestShortCode():
    runRPC(ColtConnection.port, "requestShortCode", [ "Sublime Plugin" ])	    

def runRPC(port, methodName, params):                  
    jsonRequest = None
    
    messageId = ColtConnection.messageId
    ColtConnection.messageId += 1

    if (params is None) :
            jsonRequest = { "jsonrpc" : "2.0", "method" : methodName, "id": messageId }
    else :
            jsonRequest = { "jsonrpc" : "2.0", "method" : methodName, "params": params, "id": messageId }                        

    jsonRequestStr = json.dumps(jsonRequest)

    url = "http://localhost:" + str(port) + "/rpc/coltService"
    req = urllib2.Request(url)
    response = None

    try :
        response = urllib2.urlopen(req, jsonRequestStr)
    except Exception :
        disconnect()
        raise
    
    return json.loads(response.read())

def reload():
    return runRPC(ColtConnection.port, "reload", [ getSecurityToken() ])

def startLive():
    securityToken = getSecurityToken()
    if not getSecurityToken() is None :                        
        runRPC(ColtConnection.port, "startLive", [ securityToken ])

def getState():
    return runRPC(ColtConnection.port, "getState", None)

def getActiveSessionsCount():
    try :
        jsonState = getState()
        return len(jsonState["result"]["activeConnections"])
    except Exception :
        return 0

def getContextForPosition(filePath, position, currentContent, contextType):
    return runRPC(ColtConnection.port, "getContextForPosition", [ getSecurityToken(), filePath, position, currentContent, contextType ])

def establishConnection(port):
    ColtConnection.port = port
    sublime.status_message("Established connection with COLT on port " + port)
    time.sleep(2)

def initAndConnect(settings, projectPath): 
    sublime.status_message("Trying to establish connection with COLT...")

    port = locateCOLTServicePort(projectPath)
    if not port is None :
        establishConnection(port)
        return port

    colt.runCOLT(settings)
    
    timeout = 20
    while timeout > 0 :
        time.sleep(0.3)
        timeout -= 0.3

        port = locateCOLTServicePort(projectPath)
        if not port is None :
            establishConnection(port)
            return port

    sublime.error_message("Can't establish connection with COLT")
    return None

def locateCOLTServicePort(projectPath): 
    port = getRPCPortForProject(projectPath)
    if port is None :
        return None

    try :
        runRPC(port, "ping", None)                        
    except Exception:
        return None

    return port   

def getRPCPortForProject(projectPath):
    storageDir = colt.getProjectWorkingDir(projectPath)
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

def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t

set_interval(coltStateUpdate, 0.8)    
