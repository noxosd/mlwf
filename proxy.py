#!/usr/bin/python

import socket, select, time, requests

class Fuzzer:
    def __init__(self, url, query_arguments, method):
        self.url = url
        self.query_arguments = query_arguments
        self.method = method
        self.session = requests.Session()
    def fuzz(self):
        req = requests.Request(self.method, self.url, self.query_arguments)
        prepped = req.prepare()
        resp = self.session.send(prepped)
        print "Server status code: %d" % (resp.status_code)
            
        

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
            print "RESPONSE"
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
        if len(lines[-1])>0:
            self.data_query = lines[-1]
            print "Data: %s" % self.data_query
            self.data_query_arguments = self.parse_query(self.data_query)
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
            if parser.query is not None:
                query_arguments = parser.query_arguments
                fuzzer = Fuzzer(parser.uri, query_arguments, parser.method).fuzz() 
            elif parser.data_query is not None:
                query_arguments = parser.data_query_arguments
                fuzzer = Fuzzer(parser.uri, query_arguments, parser.method).fuzz()
        self.channel[self.s].send(data)


def main():
    proxy = Proxy()
    proxy.main_loop()

if __name__=="__main__":
    main()
