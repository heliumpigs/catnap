#!/usr/bin/env python
import sys, httplib2, socket, os, urllib, Queue, traceback
from threading import Thread
from optparse import OptionParser
from xml import sax

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
    
def detab_contents(contents):
    lines = contents.splitlines()
    
    if len(lines) > 0 and lines[0].strip() == '':
        lines = lines[1:]
    if len(lines) > 0 and lines[-1].strip() == '':
        lines = lines[:-1]
    
    whitespace = ''
    if len(lines) > 0:
        stripped = lines[0].lstrip()
        
        if len(stripped) < len(lines[0]):
            diff = len(lines[0]) - len(stripped)
            whitespace = lines[0][:diff]
            
    if whitespace != '':
        for i in xrange(0, len(lines)):
            if lines[i].startswith(whitespace):
                lines[i] = lines[i][len(whitespace):]
                
    actual = StringIO()
    for line in lines:
        actual.write(line)
        actual.write('\n')
        
    value = actual.getvalue()
    actual.close()
    return value

def tab_contents(contents, num_spaces):
    tabbed = StringIO()
    spaces = ' ' * num_spaces
    
    for line in contents.splitlines():
        tabbed.write(spaces)
        tabbed.write(line)
        tabbed.write('\n')
    
    tabbed_contents = tabbed.getvalue()
    tabbed.close()
    return tabbed_contents

class RequestBody(object):
    def __init__(self, type):
        self.type = type
        
        if type == 'post':
            self.value = {}
        else:
            self.value = ''
        
    def __str__(self):
        if self.type == 'contents':
            return self.value
        elif self.type == 'post':
            return urllib.urlencode(self.value)
        elif self.type == 'file':
            path = os.path.join(os.path.dirname(self.file), contents.strip())
            
            with open(path) as file:
                return file.read()
        else:
            raise ValueError('unknown type: ' + self.type)
            
class ExpectedBody(object):
    def __init__(self, type):
        self.type = type
        
    def matches(self, request, contents):
        if self.type == 'python':
            vars = {
                'response': response,
                'contents': contents
            }
            
            exec self.value in vars
            return True
        elif self.type == 'text':
            return contents == self.value

class TestCase(object):
    def __init__(self, name):
        self.name = name
        self.auth = None
        self.body = None
        self.status = None
        self.expected = None
        self.headers = {}
        
class TestFileHandler(sax.ContentHandler):
    def __init__(self):
        self.tests = []
        self._buffer = None
    
    def startElement(self, name, attrs):
        if name == 'testcase':
            self._testcase = TestCase(attrs['name'])
            
        elif name == 'request':
            self._testcase.method = attrs['method']
            self._testcase.url = attrs['url']
        elif name == 'headers':
            self._cur_dict = self._testcase.headers
        elif name == 'auth':
            self._testcase.auth = (attrs['username'], attrs['password'])
        elif name == 'body':
            self._testcase.body = RequestBody(attrs['type'])
            self._cur_dict = self._testcase.body.value
        elif name == 'param':
            self._cur_param = attrs['name']
        
        elif name == 'expected':
            self._testcase.expected = ExpectedBody(attrs['type'])
        
            
        if self._buffer:
            self._buffer.close()
        self._buffer = StringIO()
            
    def characters(self, ch):
        self._buffer.write(ch)
    
    def endElement(self, name):
        contents = self._buffer.getvalue()
        
        if name == 'body':
            if self._testcase.body.type != 'post':
                self._testcase.body.value = contents
        elif name == 'status':
            self._testcase.status = int(contents.strip())
        elif name == 'param':
            self._cur_dict[self._cur_param] = contents
        elif name == 'expected':
            self._testcase.expected.value = detab_contents(contents)
        elif name == 'testcase':
            self.tests.append(self._testcase)
        
def parse_file(filename):
    handler = TestFileHandler()
    handler.file = filename
    
    parser = sax.make_parser()
    parser.setContentHandler(handler)
    
    with open(filename) as file:
        parser.parse(file)
        
    return handler.tests

verbose = False
pass_count = 0
fail_count = 0
                
def run(testcase):
    global verbose, pass_count, fail_count
    
    print 'Executing ' + testcase.name
    http = httplib2.Http()
    
    if testcase.auth:
        http.add_credentials(testcase.auth[0], testcase.auth[1])
    
    if testcase.body and testcase.body.type == 'post':
        testcase.headers['Content-type'] = 'application/x-www-form-urlencoded'
        
    try:
        body = str(testcase.body)
        response, contents = http.request(testcase.url, testcase.method, body=body, headers=testcase.headers)
        
        if testcase.status and testcase.status != response.status:
            print '  FAIL: Response status (%s) does not match expected value (%s)' % (response.status, testcase.status)
            
            if verbose:
                print '    Response content:'
                print tab_contents(contents, 6)
            
            fail_count += 1
            return
        
        if testcase.expected and not testcase.expected.matches(response, contents):
            print '  FAIL: Response content failed %s test' % testcase.expected.type
            print '    Test:'
            print tab_contents(testcase.expected, 6)
            print '    Response content:'
            print tab_contents(contents, 6)
            
            fail_count += 1
            
        pass_count += 1
        
    except Exception, e:
        fail_count += 1
        print '  FAIL: An error occurred (%s)' % str(e)
        
        traceback_buffer = StringIO()
        traceback.print_exc(file=traceback_buffer)
        
        traceback_str = traceback_buffer.getvalue()
        traceback_buffer.close()
        
        print tab_contents(traceback_str, 4)
    
def main():
    parser = OptionParser(usage="usage: %prog [options] <file 1> <file 2> ...")
    parser.add_option("-t", "--time", dest="timeout", action="store", type="int",
                      help="number of seconds before timeout (default 4)", default="4")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                      help="verbose output")
    parser.add_option("-s", "--threads", dest="threads", action="store", type="int",
                      help="number of concurrent tests to execute (default 1)", default="1")
    
    (options, args) = parser.parse_args()
    socket.timeout = options.timeout
    
    global verbose
    verbose = options.verbose
    
    tests = Queue.Queue()
    def worker():
        while True:
            testcase = tests.get()
            run(testcase)
            tests.task_done()
    
    for i in range(options.threads):
        thread = Thread(target=worker)
        thread.start()
    
    for arg in args:
        for testcase in parse_file(arg):
            tests.put(testcase)
            
    tests.join()
    
    global pass_count, fail_count
    print 'STATISTICS:'
    print '  PASSED: %s' % pass_count
    print '  FAILED: %s' % fail_count
    
if __name__ == '__main__':
    main()