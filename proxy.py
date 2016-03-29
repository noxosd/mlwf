#!/usr/bin/python

import socket, select, time, requests, random, string

class Fuzzer:
    def __init__(self, url, query_arguments, method):
        self.url = url
        self.query_arguments = query_arguments
        self.method = method
        self.session = requests.Session()
        self.load_vectors()

    def load_vectors(self):
        # Placeholder. Make loading from file later
        self.mirror_vectors = {"HTMLi":"<s>Test</s>","XSS":"<script>alert(1)</script>", "Another XSS":"\"alert(1)"}

    def fuzz(self):
        to_fuzz = []
        print self.query_arguments
        for k,v in self.query_arguments.iteritems():
            if v == "*":
                to_fuzz.append(k)
        print "To fuzz: ", to_fuzz
        
        #Generating couple of random strings
        fuzz_strings = []
        for i in range(3):
            fuzz_strings.append(''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(i)))        
        original_resp = self.send(self.query_arguments)
        print "Original status code: %d" % (original_resp.status_code)
        for param in to_fuzz:
            fuzz_query_arguments = self.query_arguments
            for fuzz_str in fuzz_strings:
                print fuzz_str
                fuzz_query_arguments[param] = fuzz_str
                resp = self.send(fuzz_query_arguments)
                if resp.status_code != original_resp.status_code:
                    print "BOOM! Different answer at \"%s\" string" % (fuzz_str)
         #Testing mirror vectors
            for vector in self.mirror_vectors.keys():
                fuzz_query_arguments[param] = self.mirror_vectors[vector]
                resp = self.send(fuzz_query_arguments)
                if string.find(resp.text, self.mirror_vectors[vector]) != -1:
                    print "BOOM! Argument %s vulnerable to %s attack with %s vector" % (param, vector, self.mirror_vectors[vector])
         #Testing special characters
            for spec_char in range(37):
                fuzz_query_arguments[param] = chr(spec_char)
                resp = self.send(fuzz_query_arguments)
                if resp.status_code != original_resp.status_code:
                    print "BOOM! Different answer at %d special char" % (resp.status_code)

    def send(self, query_arguments):
        if self.method == "POST":
            req = requests.post(self.url, data = query_arguments)
        elif self.method == "GET":
            req = requests.get(self.url, params = query_arguments)            
        return req
            
        

class Forwarder:
    def __init__(self):
        self.forwarder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, host, port=80):
        print "Connecting to: %s:%d" % (host, port)
        self.forwarder.connect((host, port))
        return self.forwarder

class HTTP_Parser:
    def __init__(self, data):
        self.data = data
        self.query = None
        self.data_query = None
    def parse(self):
        print "============================================"
        lines = self.data.split("\r\n")
#        for i in lines:
#            print "Line: " + i        
        self.method, self.host, self.http_version = lines[0].split(" ")
        if self.host[1].isdigit():
            print "RESPONSE. Do not proceed"
            return            
        self.host, self.query = self.host.split("?") if "?" in self.host else (self.host, None)
        self.uri = self.host
        self.schema, self.host = self.host.split("://")
        self.host, self.url = self.host.split("/", 1)
        print "Method: %s" % (self.method)
        print "Schema: %s" % (self.schema)
        print "URI: %s" % (self.uri)
        print "URL: %s" % (self.url)
        print "Host: %s" % (self.host)
        if self.query:
            print "Query: %s" % (self.query)
            self.query_arguments = self.parse_query(self.query)
            print "Query arguments: ", self.query_arguments
            fuzz = Fuzzer(self.uri, self.query_arguments, self.method).fuzz()
        if len(lines[-1])>0:
            self.data_query = lines[-1]
            print "Data: %s" % self.data_query
            self.data_query_arguments = self.parse_query(self.data_query)
            fuzz = Fuzzer(self.uri, self.data_query_arguments, self.method).fuzz()
        print "============================================"
 
    def parse_query(self, query):
        query_arguments = []
        query_arguments.extend(query.split("&"))
        return {k:v for k,v in (x.split("=") for x in query_arguments)}

class Proxy:
    def __init__(self, host="0.0.0.0", port=8000):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(10)
    
    def main_loop(self):
        print "Entering main loop"
        delay = 100
        self.input_list = []
        self.input_list.append(self.server)
        self.channel = {}
        while True:
            time.sleep(0.5)
            input, output, exceptready = select.select(self.input_list, [], [])
            for self.s in input:
                if self.s == self.server:
                    self.on_accept()
                    break         
                data  = self.on_recv()
   
    def on_accept(self):
        clientsock, clientaddr = self.server.accept()
        print "Client (%s, %s) connected" % clientaddr
        data = clientsock.recv(2048)
        parser = HTTP_Parser(data)
        parser.parse()
        forwarder = Forwarder().connect(parser.host)
        self.input_list.append(clientsock)
        self.input_list.append(forwarder)
        self.channel[clientsock] = forwarder
        self.channel[forwarder] = clientsock
        forwarder.send(data)
    
    def on_recv(self):
        data = self.s.recv(2048)
        if data:
            parser = HTTP_Parser(data)
            parser.parse()
        self.channel[self.s].send(data)


def main():
    proxy = Proxy()
    proxy.main_loop()

if __name__=="__main__":
    main()
