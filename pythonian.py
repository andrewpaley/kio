from datetime import datetime
import io
import logging
import traceback
#import os
import socket
import threading
import time
import concurrent.futures

from kqml import KQMLModule, KQMLReader, KQMLPerformative, KQMLList, KQMLDispatcher, KQMLToken, KQMLString

logger = logging.getLogger('Pythonian')
logger.setLevel(logging.DEBUG)

class Pythonian(KQMLModule):
    name = "Pythonian" # This is the name of the agent to register with

    def __init__(self, **kwargs):
        # Call the parent class' constructor which sends a registration
        # message, setting the agent's name to be recognized by the
        # Facilitator.
        if 'localPort' in kwargs:
            self.localPort = kwargs['localPort']
            del kwargs['localPort']
        else:
            self.localPort = 8950
        super(Pythonian, self).__init__(name = self.name, **kwargs)
        self.starttime = datetime.now()
        # tracking functions related to asks and achieves
        self.achieves = dict()
        self.asks = dict()
        # subscription stuff
        self.subscribers = dict() # query:[subscribe,msgs]
        self.subcribe_data_old = dict()
        self.subcribe_data_new = dict()
        self.polling_interval = 1
        self.poller = threading.Thread(target=self.poll_for_subscription_updates, args=[])
        # Finally, start the listener for incoming messages
        self.listenSoc = socket.socket()
        self.listenSoc.bind(('', self.localPort))
        self.listenSoc.listen(10)
        self.listener = threading.Thread(target=self.listen, args = [])
        # ready to go
        self.state = 'idle'
        self.ready = True
        self.poller.start()
        self.listener.start()


    def add_achieve(self, name, fn):
        self.achieves[name] = fn

    def add_ask(self, name, fn, pattern, subscribable=False):
        self.asks[name] = fn
        #self.advertise(pattern)
        if subscribable:
            self.subscribers[pattern] = list()
            self.advertise_subscribe(pattern)

    # Override
    def register(self):
        if self.name is not None:
            perf = KQMLPerformative('register')
            perf.set('sender', self.name)
            perf.set('receiver', 'facilitator')
            content = KQMLList(['"socket://'+self.host +':'+str(self.localPort)+'"', 'nil', 'nil', self.localPort])
            perf.set('content', content)
            self.send(perf)
            

    # Not sure if this is needed
    def close_socket(self):
        self.dispatcher.shutdown()
        self.socket.close()

    def listen(self):
        logger.debug('listening')
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:        
            while self.ready:
                conn,addr = self.listenSoc.accept()
                logger.debug('received connection')
                sw = socket.SocketIO(conn, 'w')
                self.out = io.BufferedWriter(sw)
                sr = socket.SocketIO(conn, 'r')
                inp = KQMLReader(io.BufferedReader(sr))
                self.dispatcher = KQMLDispatcher(self, inp, self.name)
                executor.submit(self.dispatcher.start)

    # Override
    # defualt impl does an exit on eof
    def receive_eof(self):
        #self.close_socket()
        pass

    #Override
    def receive_ask_one(self, msg, content):
        # get predicate
        pred = content.head()
        # get the bounded args
        bounded = []
        for each in content.data[1:]:
            if str(each[0]) != '?':
                bounded.append(each)
        # make the query
        results = self.asks[pred](*bounded)
        # create response
        resp_type = msg.get('response')
        self.responsd_to_query(msg, content, results, resp_type)

    # Override
    def receive_achieve(self, msg, content):
        if content.head() == 'task':
            action = content.get('action')
            if action:
                self.handle_achieve_action(msg, content, action)
            else:
                self.error_reply(msg, 'no action for achieve task provided')
        elif content.head() == 'actionSequence':
            self.error_reply(msg, 'unexpected achieve command: actionSequence')
        elif content.head() == 'eval':
            self.error_reply(msg, 'unexpected achieve command: eval')
        else:
            self.error_reply(msg, 'unexpected achieve command: ' + content.head())


    # Override
    def receive_tell(self, msg, content):
        logger.debug('received tell: ' + str(content))
        reply_msg = KQMLPerformative('tell')
        reply_msg.set('sender', self.name)
        reply_msg.set('content', None)
        self.reply(msg, reply_msg)

    # Override
    def receive_subscribe(self, msg, content):
        logger.debug('received subscribe: ' + str(content))
        # content performative should be an ask-all
        if content.head() == 'ask-all':
            # if we kept track of msg ideas, could check for that, but we aren't
            # content of content is the query that we care about
            query = content.get('content') # as a KQMLList?
            query_string = query.to_string()
            if query.head() in self.asks and query_string in self.subscribers:
                self.subscribers[query_string].append(msg)
                self.subcribe_data_old[query_string] = None
                self.subcribe_data_new[query_string] = None
                reply_msg = KQMLPerformative('tell')
                reply_msg.set(':sender', self.name)
                reply_msg.set('content', ':ok')
                self.reply(msg, reply_msg)


    # Override
    #ping performative doesn't seem to be supported in pykqml
    # handling 'other' to catch ping and otherwise throw error
    def receive_other_performative(self, msg):
        if (msg.head() == 'ping'):
            self.receive_ping(msg)
        else:
            self.error_reply(msg, 'unexpected performative: ' + str(msg))

    def advertise(self, pattern):
        self.connect(self.host, self.port)
        msg = KQMLPerformative('advertise')
        msg.set('sender', self.name)
        msg.set('receiver', 'facilitator')
        reply_id = 'id'+str(self.reply_id_counter)
        msg.set('reply-with', reply_id)
        self.reply_id_counter += 1
        content = KQMLPerformative('ask-all')
        content.set('receiver', self.name)
        content.set('in-reply-to', reply_id)
        content.set('content', pattern)
        msg.set('content', content)
        self.send(msg)
        self.close_socket()

    def advertise_subscribe(self, pattern):
        self.connect(self.host, self.port)
        msg = KQMLPerformative('advertise')
        msg.set('sender', self.name)
        msg.set('receiver', 'facilitator')
        reply_id = 'id'+str(self.reply_id_counter)
        msg.set('reply-with', reply_id)
        self.reply_id_counter += 1
        subscribe = KQMLPerformative('subscribe')
        subscribe.set('receiver', self.name)
        subscribe.set('in-reply-to', reply_id)
        content = KQMLPerformative('ask-all')
        content.set('receiver', self.name)
        content.set('in-reply-to', reply_id)
        #content.set('language', 'fire')
        content.set('content', pattern)
        subscribe.set('content', content)
        msg.set('content', subscribe)
        self.send(msg)
        self.close_socket()

    def responsd_to_query(self, msg, content, results, resp_type):
        if resp_type == None or resp_type == ':pattern':
            self.respond_with_pattern(msg, content, results)
        else:
            self.respond_with_bindings(msg, content, results)

    def respond_with_pattern(self, msg, content, results):
        reply_content = KQMLList(content.head())
        results_list = results if isinstance(results, list) else [results]
        result_index = 0
        arg_len = len(content.data[1:])
        for i, each in enumerate(content.data[1:]):
            if str(each[0]) == '?':
                #add result
                if i == arg_len and result_index < len(results_list)-1:
                    # shove the rest of the results into this one var
                    reply_content.append(listify(results_list[result_index:]))
                else:
                    reply_content.append(listify(results_list[result_index]))
                    result_index += 1
            else:
                reply_content.append(each)
        reply_msg = KQMLPerformative('tell')
        reply_msg.set('sender', self.name)
        reply_msg.set('content', reply_content)
        self.reply(msg, reply_msg)

    def respond_with_bindings(self, msg, content, results):
        reply_content = KQMLList(content.head())
        results_list = results if isinstance(results, list) else [results]
        result_index = 0
        arg_len = len(content.data[1:])
        bindings_list = list()
        for i, each in enumerate(content.data[1:]):
            if str(each[0]) == '?':
                #add result
                if i == arg_len and result_index < len(results_list)-1:
                    # shove the rest of the results into this one var
                    pair = (each, results_list[result_index:])
                    bindings_list.append(pair)
                else:
                    pair = (each, results_list[result_index])
                    result_index += 1
                    bindings_list.append(pair)
        reply_msg = KQMLPerformative('tell')
        reply_msg.set('sender', self.name)
        reply_msg.set('content', listify(bindings_list))
        self.reply(msg, reply_msg)


    def handle_achieve_action(self, msg, content, action):
        if action.head() in self.achieves:
            try:
                args = action.data[1:]
                results = self.achieves[action.head()](*args)
                logger.debug("Return of achieve: " + str(results))
                reply = KQMLPerformative('tell')
                reply.set('sender', self.name)
                results_list = listify(results)
                reply.set('content', results_list)
                self.reply(msg, reply)
            except Exception as ex:
                logger.debug(traceback.print_exc())
                self.error_reply(msg, 'An error occurred while executing: ' + action.head())
        else:
            self.error_reply(msg, 'unknown action: ' + action.head())


    def receive_ping(self, msg):
        reply = KQMLPerformative('update')
        reply.set('sender', self.name)
        #reply.set('receiver', msg.get('sender'))
        #reply.set('in-reply-to', msg.get('reply-with'))
        reply_content = KQMLList([':agent', self.name])
        reply_content.append(':uptime')
        reply_content.append(self.uptime())
        # I think .set('status', ':OK') can be used here
        reply_content.append(':status')
        reply_content.append(':OK')
        reply_content.append(':state')
        reply_content.append('idle')
        reply_content.append(':machine')
        reply_content.append(socket.gethostname())
        reply.set('content', reply_content)
        self.reply(msg, reply)

    def poll_for_subscription_updates(self):
        logger.debug("Running subcription poller")
        while self.ready:
            for query,new_data in self.subcribe_data_new.items():
                if new_data is not None:
                    for msg in self.subscribers[query]:
                        ask = msg.get('content')
                        query = ask.get('content')
                        logger.debug("Sending subscption update for " + str(query))
                        # TODO, check for bindings or pattern, refactor to check in one place
                        resp_type = ask.get('response')
                        self.responsd_to_query(msg, query, new_data, resp_type)    
                        #self.respond_with_bindings(msg, query, new_data)
                        self.subcribe_data_old[query] = new_data
            for query,_ in self.subcribe_data_new.items():
                self.subcribe_data_new[query] = None        
            time.sleep(self.polling_interval)

    def update_query(self, query, *args):
        if query in self.subcribe_data_old and self.subcribe_data_old[query] != args:
            logger.debug("Updating " + str(query) + " with " + str(args))
            self.subcribe_data_new[query] = args


    def insert_data(self, receiver, data, wm_only = False):
        msg = KQMLPerformative('insert')
        msg.set('sender', self.name)
        msg.set('receiver', receiver)
        if wm_only:
            msg.append(':wm-only?')
        msg.set('content', listify(data))
        self.connect(self.host, self.port)
        self.send(msg)

    def achieve_on_agent(self, receiver, data):
            msg = KQMLPerformative('achieve')
            msg.set('sender', self.name)
            msg.set('receiver', receiver)
            msg.set('content', listify(data))
            self.connect(self.host, self.port)
            self.send(msg)

    def uptime(self):
        now = datetime.now()
        years = now.year-self.starttime.year
        #months
        if now.year==self.starttime.year: months = now.month - self.starttime.month
        else: months = 12 - self.starttime.month + now.month
        #days
        if now.month == self.starttime.month: days = now.day - self.starttime.day
        elif self.starttime.month in [1, 3, 5, 7, 8, 10, 12]:
            days = 31 - self.starttime.day + now.day
        elif self.starttime.month in [4, 6, 9, 11]:
            days = 30 - self.starttime.day + now.day
        else: days = 28 - self.starttime.day + now.day
        #hours
        if self.starttime.day == now.day: hours = now.hour - self.starttime.hour
        else: hours = 24 - self.starttime.hour + now.hour
        #minutes
        if self.starttime.hour == now.hour: minutes = now.minute - self.starttime.minute
        else: minutes = 60 - self.starttime.minute + now.minute
        #seconds
        if self.starttime.minute == now.minute: seconds = now.second - self.starttime.second
        else: seconds = 60 - self.starttime.second + now.second
        return str('('+ " ".join([str(i) for i in [years, months, days, hours, minutes, seconds]]) + ')')

def listify(possible_list):
    if isinstance(possible_list, list):
        new_list = [listify(each) for each in possible_list]
        return KQMLList(new_list)
    elif isinstance(possible_list, tuple):
        if len(possible_list) == 2:
            # assume dotted pair
            car = listify(possible_list[0])
            cdr = listify(possible_list[1])
            return KQMLList([car, KQMLToken('.'), cdr])
        else:
            # otherwise treat same as list
            new_list = [listify(each) for each in possible_list]
            return KQMLList(new_list)
    elif isinstance(possible_list, str):
        if ' ' in possible_list:
            if possible_list[0] == '(' and possible_list[-1] == ')':
                # WARNING: This is very incomplete!
                terms = possible_list[1:-1].split()
                return KQMLList([listify(t) for t in terms])
            else:
                return KQMLString(possible_list)
        else:
            return KQMLToken(possible_list)
    elif isinstance(possible_list, dict):
        return KQMLList([listify(pair) for pair in possible_list.items()])
    else:
        return KQMLToken(str(possible_list))

def convert_to_boolean(to_be_bool):
    """
    Since KQML is based on lisp, and (at least for now) messages are coming from lisp land (i.e., Companion), we use some lisp conventions to determine how a KQML element should be converted to a Boolean.  
    If the KQML element is <code>nil</code> or <code>()</code> then <code>convert_to_boolean</code> will return <code>False</code>.  Otherwise, it returns <code>True</code>.
    """
    if isinstance(to_be_bool, KQMLToken) and to_be_bool.data == "nil":
        return False
    if isinstance(to_be_bool, KQMLList) and len(to_be_bool) == 0:
        return False
    return True

def convert_to_int(to_be_int):
    """
    Most data being received by Pythonian will be a KQMLToken.  This function gets the data of the KQMLToken and casts it to an int.
    """
    if isinstance(to_be_int, KQMLToken):
        return int(to_be_int.data)
    if isinstance(to_be_int, KQMLString):
        return int(to_be_int.data)
    # Throw error
    return to_be_int

def convert_to_list(to_be_list):
    if isinstance(to_be_list, KQMLList):
        # could recurse but.... nah!
        return to_be_list.data
    else:
        return to_be_list


def test(foo):
    print(foo)
    return 1

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    a = Pythonian(host='localhost', port=9000, localPort=8950, debug=True)
    a.add_achieve('test', test)
    a.achieve_on_agent('interaction-manager', "(initializeToMExp ?gpool)")