from LibPeer.Events import Receipt
from threading import Condition
from twisted.internet import reactor
from LibPeer.Logging import log


class ReceiptAwaiter:
    def __init__(self, function, *args):
        self.error = True
        self.exception = None
        self.condition: Condition = Condition()

        reactor.callFromThread(self.call, function, args)

        with self.condition:
            self.condition.wait()
        
        if(self.error):
            raise self.exception

    def on_success(self):
        with self.condition:
            self.error = False
            self.condition.notify()

    def on_error(self, message):
        with self.condition:
            self.error = True
            self.exception = Exception(message)
            self.condition.notify()

    def call(self, function, args):
        try:
            res: Receipt = function(*args)
            res.subscribe(self.on_success, self.on_error)
        except Exception as e:
            with self.condition:
                log.error("An exception occurred while running the awaited call, see the exception on the waiting thread for details")
                self.exception = e
                self.error = True
                self.condition.notify()
            
    