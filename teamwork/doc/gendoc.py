import os
import string
import time

pydoc = "/usr/ucb/pydoc"
webroot = os.path.expanduser('~pynadath')+'/public_html'
def execute(cmd,dir=None):
    """Executes the specified command (in a particular working
    directory, if specified) and return the result"""
    if dir:
        oldDir = os.getcwd()
        os.chdir(dir)
    output = os.popen(cmd,'r')
    data = output.read()
    output.close()
    if dir:
        os.chdir(oldDir)
    return data


ignore = ['CVS','gendoc.py','original','doc','old','images','examples',
          'mei','data','pulp']

def generateJSTree(dir,depth=1):
    defaultLnk = "/~pynadath%smain.html" % (webpath)
    if depth == 1:
        parent = 'foldersTree'
        print '%s = gFld("Multiagent Python Classes","%s")' \
              % (parent,defaultLnk)
    else:
        parent = 'aux%d' % (depth-1)
    cmd = pydoc + " -w "+ dir
    execute(cmd)
    cmd = 'mv '+dir+'.html '+webroot+webpath
    execute(cmd)
    dir = dir + '.'
    files = os.listdir('.')
    files.sort()
    for f in files:
        if f in ignore:
            continue
        name = string.split(f,'.')
        if len(name) == 2:
            root = name[0]
            if name[1] == 'py' and root != '__init__':
                link = '/~pynadath' + webpath + dir + root+'.html'
                print 'insDoc(%s,gLnk("R","%s","%s"))' \
                      % (parent,root,link)
                cmd = pydoc+" -w "+ dir + root
                execute(cmd)
                cmd = 'mv '+dir+root+'.html '+webroot+webpath
                execute(cmd)
        else:
            olddir = os.getcwd()
            try:
                os.chdir(f)
                subdir = dir+f
            except OSError:
                subdir = None
            if subdir:
                print 'aux%d=insFld(%s,gFld("%s","%s"))' \
                      % (depth,parent,f,defaultLnk)
                generateJSTree(subdir,depth+1)
                os.chdir(olddir)

def generateTree(dir):
    cmd = pydoc + " -w "+ dir
    execute(cmd)
    cmd = 'mv '+dir+'.html '+webroot+webpath
    execute(cmd)
    dir = dir + '.'
    print '<UL>'
    files = os.listdir('.')
    files.sort()
    for file in files:
        if file in ignore:
            continue
        name = string.split(file,'.')
        if len(name) == 2:
            root = name[0]
            if name[1] == 'py' and root != '__init__':
                name = webpath + dir + root+'.html'
                print '<LI>'
                print '<A HREF="/~pynadath'+name+'">'+root+'</A>'
                print '</LI>'
                cmd = pydoc+" -w "+ dir + root
                execute(cmd)
                cmd = 'mv '+dir+root+'.html '+webroot+webpath
                execute(cmd)
        else:
            olddir = os.getcwd()
            try:
                os.chdir(file)
                subdir = dir+file
            except OSError:
                subdir = None
            if subdir:
                print '<LI>',file
                generateTree(subdir)
                print '</LI>'
                os.chdir(olddir)
    print '</UL>'


if __name__=='__main__':
    ## Typical usage of this command:
    ## cd ~www/teamcore/doc/COM-MTDP/src/
    ## python ~pynadath/workspace/teamwork/doc/gendoc.py > index.html


    # If true, generates a JavaScript-based documentation browser;
    # otherwise, generates a plain HTML browser
    JSflag = 1
    if JSflag:

        path = os.path.expanduser('~pynadath')
        webpath = '/doc/COM-MTDP/src/'

        os.chdir(path)
        os.chdir('workspace') 
        os.chdir('teamwork')
        generateJSTree('teamwork')
    else:
        path = os.path.expanduser('~pynadath')
        webpath = '/doc/COM-MTDP/src/'
        print '<!doctype html public "-//w3c//dtd html 4.0 transitional//en">'
        print '<html>'
        print '<head>'
        print '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">'
        print '<TITLE>Com-MTDP Source Code Documentation</TITLE>'
        print '</head>'
        print '<body>'
        print '<! bgcolor="#999999" TEXT="#000000" LINK="#B30E14" VLINK="#FFAF18" ALINK="#FFAF18">'

        os.chdir(path)
        os.chdir('python')
        os.chdir('teamwork')
        generateTree('teamwork')
        print '<HR>'
        print 'Auto-generated '+time.strftime('%x %X',time.localtime(time.time()))
        print "</BODY></HTML>"
