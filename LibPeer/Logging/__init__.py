from LibPeer.Logging import ansi

import sys
import inspect
import subprocess


class log:
	enabled = True
	level = 1
	output = sys.stdout
	levels = ["DEBUG", "MESSAGE", "INFO", "WARNING", "ERROR", "CRITICAL", "MELTDOWN"]
	
	level_formats = [
			(lambda f: f.colour(ansi.COLOUR_WHITE)),                                          # DEBUG
			(lambda f: f.colour(ansi.COLOUR_WHITE).bold()),                                   # MESSAGE
			(lambda f: f.colour(ansi.COLOUR_CYAN).bold()),                                    # INFORMATION
			(lambda f: f.colour(ansi.COLOUR_YELLOW).bold()),                                  # WARNING
			(lambda f: f.colour(ansi.COLOUR_RED).bold()),                                     # ERROR
			(lambda f: f.colour(ansi.COLOUR_WHITE).highlight(ansi.COLOUR_RED).bold()),        # CRITICAL
			(lambda f: f.colour(ansi.COLOUR_WHITE).highlight(ansi.COLOUR_RED).bold().blink()) # MELTDOWN
			]
	

	@staticmethod
	def debug(message):
		identifier = log.get_identifier(2)
		log.log(0, identifier, message)

	@staticmethod
	def msg(message):
		identifier = log.get_identifier(2)
		log.log(1, identifier, message)

	@staticmethod
	def info(message):
		identifier = log.get_identifier(2)
		log.log(2, identifier, message)

	@staticmethod
	def warn(message):
		identifier = log.get_identifier(2)
		log.log(3, identifier, message)

	@staticmethod
	def error(message):
		identifier = log.get_identifier(2)
		log.log(4, identifier, message)

	@staticmethod
	def critical(message):
		identifier = log.get_identifier(2)
		log.log(5, identifier, message)

	@staticmethod
	def meltdown(message):
		identifier = log.get_identifier(2)
		log.log(6, identifier, message)


	@staticmethod
	def log(level, identifier, message):
		if(log.enabled and level >= log.level):
			# Find out the longest name in the levels
			space = 0
			for lvl in log.levels:
				if(len(lvl) > space):
					space = len(lvl)

			# Padding is nice
			space += 2

			levelText = log.levels[level]
			levelText = " "*(space - len(levelText)) + levelText

			logHeader = "%s  " % (log.level_formats[level](ansi.Formatter(levelText)).string)


			# Prepend the identifier to the message
			message = "[%s] %s" % (identifier, message)
			
			# Get terminal size
			rows, columns = subprocess.check_output(['stty', 'size']).decode().split()
			columns = int(columns)
			
			resetLevel = len(levelText) + 2

			messageLines = message

			if(len(message) + resetLevel > columns and columns > resetLevel):
				messageLines = message[:columns - resetLevel]
				message = message[columns - resetLevel:]

				while(message != ""):
					messageLines += "\n" + " "*(resetLevel) + message[:columns - resetLevel]
					message = message[columns - resetLevel:]
				

			log.output.write("%s%s\n" % (logHeader, messageLines))

	@staticmethod
	def get_identifier(iterations=1):
		frame = inspect.currentframe()
		for i in range(iterations):
			frame = frame.f_back

		function_name = frame.f_code.co_name
		
		identifier = "@sm %s" % function_name

		if "self" in frame.f_locals:
			identifier = str(frame.f_locals["self"].__class__.__name__)

		return identifier

	@staticmethod
	def settings(enabled, level=1, output=sys.stdout):
		"""set settings on the logger, options are:
			settings(enabled, [level, [output]])
				enabled: a boolean turning on or off logging,
				level: an int from 0 to 6 to filter out messages of less important
					   6 being the most important, 0 being the least
				output: the output to write to
		"""
		log.enabled = enabled
		log.level = level
		log.output = output
