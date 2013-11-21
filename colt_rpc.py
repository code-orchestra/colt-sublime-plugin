import sublime
import urllib2
import json

runAfterAuthorization = None

class ColtPreferences(object):
    NAME = "Preferences.sublime-settings"

class ColtConnection(object):
    port = -1
    messageId = 1

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
    response = urllib2.urlopen(req, jsonRequestStr)
    return json.loads(response.read())

def startLive():
    securityToken = getSecurityToken()
    if not getSecurityToken() is None :                        
        runRPC(ColtConnection.port, "startLive", [ securityToken ])

