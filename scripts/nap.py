#!/usr/bin/env python
import sys, httplib2, socket, Queue, traceback
from catnap import util, model
from threading import Thread
from optparse import OptionParser

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

verbose = False
pass_count = 0
fail_count = 0
       
def run(testcase, use_cookies, cookie):
    """Runs a specified testcase"""
    global verbose, pass_count, fail_count
    
    print 'Executing ' + testcase.name
    http = httplib2.Http()
    
    if testcase.auth:
        http.add_credentials(testcase.auth[0], testcase.auth[1])
    
    #Content-type must be application/x-www-form-urlencoded if we are sending
    #POST parameters
    if testcase.body and testcase.body.type == 'post':
        testcase.headers['Content-type'] = 'application/x-www-form-urlencoded'

    if use_cookies and cookie:
        testcase.headers['Cookie'] = cookie
        
    try:
        response, contents = http.request(testcase.url, testcase.method, body=str(testcase.body), headers=testcase.headers)

        if use_cookies and 'set-cookie' in response:
            cookie = response['set-cookie']
        
        #Check that the status matches the expected value if specified
        if testcase.expected_status and testcase.expected_status != response.status:
            print '  FAIL: Response status (%s) does not match expected value (%s)' % (response.status, testcase.expected_status)
            
            if verbose:
                print '    Response content:'
                print util.tab_contents(contents, 6)
            
            fail_count += 1
            return cookie
        
        #Check that the response contents matches the expected if specified
        if testcase.expected_body and not testcase.expected_body.matches(response, contents):
            print '  FAIL: Response content failed'
            print '    Test (%s):' % testcase.expected_body.type
            print util.tab_contents(testcase.expected_body.contents, 6)
            print '    Response content:'
            print util.tab_contents(contents, 6)
            
            fail_count += 1
            
        pass_count += 1
        
    except Exception, e:
        #If an error was thrown, then the test case failed; print the stack
        #trace
        
        fail_count += 1
        print '  FAIL: An error occurred (%s)' % str(e)
        
        traceback_buffer = StringIO()
        traceback.print_exc(file=traceback_buffer)
        
        traceback_str = traceback_buffer.getvalue()
        traceback_buffer.close()
        
        print util.tab_contents(traceback_str, 4)

    return cookie
    
def main():
    """Runs Catnap"""
    
    parser = OptionParser(usage="usage: %prog [options] <file 1> <file 2> ...")
    parser.add_option("-t", "--time", dest="timeout", action="store", type="int",
                      help="number of seconds before timeout (default 4)", default="4")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                      help="verbose output")
    parser.add_option("-s", "--threads", dest="threads", action="store", type="int",
                      help="number of concurrent tests to execute (default 1)", default="1")
    parser.add_option("-c", "--cookies", dest="cookies", action="store_true",
                      help="Enable support for cookies (disabled by default)")
    
    (options, args) = parser.parse_args()
    socket.timeout = options.timeout
    
    global verbose
    verbose = options.verbose
    
    #Make the worker execute each test case in the queue
    tests = Queue.Queue()

    def worker():
        cookie = None

        while True:
            testcase = tests.get()
            cookie = run(testcase, options.cookies, cookie)
            tests.task_done()
    
    #Creates multiple threads that execute the worker, specified as a parameter
    for i in range(options.threads):
        thread = Thread(target=worker)
        thread.setDaemon(True)
        thread.start()
    
    #Parse each of the files and enqueue the test cases
    for arg in args:
        for testcase in model.parse_file(arg):
            tests.put(testcase)

    tests.join()
    
    global pass_count, fail_count
    print 'STATISTICS:'
    print '  PASSED: %s' % pass_count
    print '  FAILED: %s' % fail_count
    
if __name__ == '__main__':
    main()