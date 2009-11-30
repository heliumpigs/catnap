try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

def detab_contents(contents):
    """
    Removes formatting tabs from Python code so it can be executed without a
    syntax error
    """
    lines = contents.splitlines()
    
    #Remove the first and last line if they're blank
    if len(lines) > 0 and lines[0].strip() == '':
        lines = lines[1:]
    if len(lines) > 0 and lines[-1].strip() == '':
        lines = lines[:-1]
    
    #Get the amount of whitespace in the first line of code
    whitespace = ''
    if len(lines) > 0:
        stripped = lines[0].lstrip()
        
        if len(stripped) < len(lines[0]):
            diff = len(lines[0]) - len(stripped)
            whitespace = lines[0][:diff]
            
    #Remove that amount of whitespace from each line
    if whitespace != '':
        for i in xrange(0, len(lines)):
            if lines[i].startswith(whitespace):
                lines[i] = lines[i][len(whitespace):]
                
    #Write out the code
    actual = StringIO()
    for line in lines:
        actual.write(line)
        actual.write('\n')
        
    value = actual.getvalue()
    actual.close()
    return value

def tab_contents(contents, num_spaces):
    """
    Inserts the specified amount of spaces in front of each line of the contents
    """
    tabbed = StringIO()
    spaces = ' ' * num_spaces
    
    for line in contents.splitlines():
        tabbed.write(spaces)
        tabbed.write(line)
        tabbed.write('\n')
    
    tabbed_contents = tabbed.getvalue()
    tabbed.close()
    return tabbed_contents