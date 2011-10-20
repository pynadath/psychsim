import Tkinter
import tkMessageBox
import Pmw
from teamwork.widgets.MultiWin import InnerWindow

class AARWin (Pmw.MegaWidget):

	def __init__(self, frame, **kw):
		optiondefs = (
			('title', 'AAR',Pmw.INITOPT),
			('x', 300, Pmw.INITOPT),
			('y', 120, Pmw.INITOPT),
			('width', 500, Pmw.INITOPT),
			('height', 300, Pmw.INITOPT),
			('font', ("Helvetica", 10, "bold"), Pmw.INITOPT),
			('debug', 0, Pmw.INITOPT),
			)
		self.defineoptions(kw, optiondefs)
		
		self.aar = InnerWindow(parent = frame,
				       title = self['title'],
				       x=self['x'],y=self['y'],
				       height = self['height'],
				       width = self['width'])
		# self.aarb = Pmw.LabeledWidget(self.aar.frame,
		# labelpos = 'n', label_text = "AAR Notes")

		self.aarHist = Pmw.ScrolledText(self.aar.frame,
						text_highlightthickness = 0,
						##											  text_background = "white",
						text_wrap  = "word",
						text_height = 10,
						text_width = 42)

		buttonframe = Tkinter.Frame(self.aar.frame)
		ps = Tkinter.Button(buttonframe, text='Save',
				    command= self.printText)
		ps.pack(side='left')
		buttonframe.pack(fill='x', side='top')
		
		self.aarHist.pack(fill = "both", expand = 1)
		# self.aarb.pack(fill = "both", expand = 1)
		self.aar.place(x = self['x'], y = self['y'],
			       width = self['width'], height = self['height'])
		self.aarHist.component('text').tag_config('bolden',
							  foreground='blue',
							  font=self['font'])
		self.aarHist.component('text').tag_config('black',
							  foreground='black',
							  font =self['font'])
		self.aarHist.component('text').tag_config('hot',
							  font = self['font'],
							  foreground='white',
							  background = 'blue')
		self.aarHist.component('text').tag_bind('hot','<Button-1>',
							lambda e: tkMessageBox.showwarning('Direct Perturbation','Direct Perturbation will invoke the simulation with the suggested perturbation. Not Implemented Yet'))
		
##			  AnalysisWins.append(self.aar)
		self.initialiseoptions()

	def clear(self):
		self.aarHist.clear()
		
	def printText(self, filename=None):
			if filename is None:
				from tkFileDialog import asksaveasfilename
				ftypes = [('Text files', '.txt'),
						  ('All files', '*')]
				filename = asksaveasfilename(filetypes=ftypes,
											 defaultextension='.txt')
				if not filename: return
			tkMessageBox.showerror('Unable to save',
								   'Unable to save window to file')
			self.aarHist.exportfile(filename)

	def displayTaggedText(self,tokens):
		"""Display text in window

		tokens: list of dictionaries, with each dictinoary
		structured as follows ---
		@keyword text:	 the text to insert
		@keyword position: where to insert that text (default: 'end')
		@keyword tag:		 the face tag to use (default: 'black')"""
		for token in tokens:
			try:
					position = token['position']
			except KeyError:
					position = 'end'
			try:
					tag = token['tag']
			except KeyError:
					tag = 'black'
			try:
					text = token['text']
			except KeyError:
					text = ''
			self.insertText(position,text,tag)

	def insertText(self,index,chars,tagList=()):
			cmd = self.makeTarget(index,chars,tagList)
			Tkinter._default_root.after(1,cmd)
							
	def __insertText(self,index,chars,tagList=()):
		self.aarHist.component('text').insert(index,chars,tagList)
		self.aarHist.component('text').see('end')

	def makeTarget(self,index,chars,tagList):
			return lambda s=self,i=index,c=chars,t=tagList:\
					s.__insertText(i,c,t)
		
	def addbutton(self,name,msg):
			self.insertText('end', name, ('hot'))
			self.insertText('end', msg, ('black'))
		
	def displayAAR(self, elements=('','','')):
		step,entity, result = elements
		self.insertText('end', step, ('bolden'))
		self.insertText('end', entity, ('black'))
		self.insertText('end', result, ('black'))

			
	def displayDebug(self, step, entity, result):
			if self['debug']:
				self.insertText('end', step, ('bolden'))
				self.insertText('end', entity)
				self.insertText('end', result)
			
	def displayAARred(self, step, entity, result):

			self.insertText('end', step, ('black'))
			self.insertText('end', entity)
			self.insertText('end', result)

	def log(self, act):
			self.insertText('end', getuser() + '::')
			self.insertText('end', act + '::')
			timeStr = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
			self.insertText('end', timeStr)


