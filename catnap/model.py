import os, urllib, util, pickle
from xml import sax

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

class RequestBody(object):
    """Descriptor of the body sent from the client when the request is made"""
    
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
            raise ValueError('unknown type: ' + str(self.type))
            
class ExpectedBody(object):
    """Descriptor of the body expected back from the server"""
    
    def __init__(self, type, contents=None):
        self.type = type
        self.contents = contents
        
    def matches(self, response, contents):
        """
        Returns true if the contents from the server matches the expected body
        """
        
        if self.type == 'python':
            vars = {
                'response': response,
                'contents': contents
            }
            
            exec self.contents in vars
            return True
        elif self.type == 'text':
            return contents == self.value

class TestCase(object):
    """Descriptor of a test case"""
    
    def __init__(self, name, method, url, headers={}, auth=None, body=None, expected_status=None, expected_body=None):
        """
        Creates a new testcase.
        name - The name of the testcase
        method - The HTTP verb to use
        url - The URL to request
        headers - HTTP headers to use
        auth - A tuple of (username, password) authentication credentials
        body - A RequestBody object specifying the input body
        expected_status - The expected response status
        expected_body - An ExpectedBody object specifying the response's expected body
        """
        
        self.name = name
        self.method = method
        self.url = url
        self.headers = headers
        self.auth = auth
        self.body = body
        self.expected_status = expected_status
        self.expected_body = expected_body
        
class TestFileHandler(sax.ContentHandler):
    """Parses a test XML file"""
    
    def __init__(self):
        self.tests = []
        self._buffer = None
    
    def startElement(self, name, attrs):
        if name == 'testcase':
            self._testcase = TestCase(attrs['name'], None, None)
            
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
            self._testcase.expected.value = util.detab_contents(contents)
        elif name == 'testcase':
            self.tests.append(self._testcase)
        
def parse_file(filename):
    """Parses a test file into a list of test cases"""
    
    if filename.endswith('.p'):
        return parse_pickle(filename)
    elif filename.endswith('.xml'):
        return parse_xml(filename)
    else:
        print 'Unknown filetype for %s - it should have a .p or .xml extension. Attempting to open with XML first, pickle second.'
        
        try:
            return parse_xml(filename)
        except:
            return parse_pickle(filename)

def parse_pickle(filename):
    """Parses a pickle file into a list of test cases"""
    
    with open(filename) as file:
        return pickle.load(file)

def parse_xml(filename):
    """Parses an XML file into a list of test cases"""
    
    handler = TestFileHandler()
    handler.file = filename
    
    parser = sax.make_parser()
    parser.setContentHandler(handler)
    
    with open(filename) as file:
        parser.parse(file)
        
    return handler.tests