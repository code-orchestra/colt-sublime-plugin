import sublime, sublime_plugin
import os.path

class RunWithColtCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		mainDocument = self.view.file_name()
		basedir = os.path.dirname(mainDocument)

		settings = sublime.load_settings("Preferences.sublime-settings")
		if not settings.has("coltPath") :
			sublime.error_message("COLT path is not specified, go to Preferences -> COLT")
			return

		coltPath = settings.get("coltPath")

		print coltPath
		


