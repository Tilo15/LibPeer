from LibPeer.Logging import log

class Event:
	def __init__(self):
		self.subscribers = []
		self.subscriber_args = {}

	def subscribe(self, callback, *custom_args):
		self.subscribers.append(callback)
		self.subscriber_args[callback] = custom_args

	def call(self, *args):
		for sub in self.subscribers:
			sub(*args, *self.subscriber_args[sub])



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
		self.args = ()
		self.complete = False
		self.error = False

	def subscribe(self, success, failure=None, args=()):
		self.on_success = success
		self.on_failure = failure
		self.args = args

	def success(self):
		self.complete = True
		if(self.on_success != None):
			self.on_success(*self.args)


	def failure(self, message=""):
		self.error = True
		self.complete = True
		if(callable(self.on_failure)):
			self.on_failure(message, *self.args)
		else:
			log.error("an error occurred with message '%s', but the Receipt has no failure callback" % message)


class ImmediateReceipt(Receipt):
	def subscribe(self, success, failure=None):
		self.on_success = success
		self.on_failure = failure
		self.success()
