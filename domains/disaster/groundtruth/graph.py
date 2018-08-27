from pygraphml import GraphMLParser
parser = GraphMLParser()
g = parser.parse('/tmp/psygraph.xml')
g.show()
