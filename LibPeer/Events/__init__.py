from LibPeer.Logging import log

class Event:
	def __init__(self):
		self.subscribers = []

	def subscribe(self, callback):
		self.subscribers.append(callback)

	def call(self, *args):
		for sub in self.subscribers:
			sub(*args)



class KeyedEvent:
	def __init__(self):
		self.subscribers = {}

	def subscribe(self, key, callback):
		self.subscribers[key] = callback

	def call(self, key, *args):
		if(key in self.subscribers):			
			self.subscribers[key](*args)
		else:
			log.warn("no subscriber for key '%s'" % key)

class Receipt:
	def __init__(self):
		self.on_success = None
		self.on_failure = None
		self.complete = False
		self.error = False

	def subscribe(self, success, failure=None):
		self.on_success = success
		self.on_failure = failure

	def success(self):
		self.complete = True
		if(self.on_success != None):
			self.on_success()


	def failure(self, message=""):
		self.error = True
		self.complete = True
		if(self.on_failure != None):
			self.on_failure(message)
		else:
			log.error("an error occurred with message '%s', but the Receipt has no failure callback" % message)


class ImmediateReceipt(Receipt):
	def subscribe(self, success, failure=None):
		self.on_success = success
		self.on_failure = failure
		self.succeeded()
