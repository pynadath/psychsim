from Tkinter import *
import Pmw

class MultiListbox(Pmw.MegaWidget):
    def __init__(self, master, lists, **kw):
        optiondefs = (
            # Callbacks (dp)
            ('doublecommand', None, None),
            ('rowselectcommand', None, None),
            ('colselectcommand', None, None),
            )
        self.defineoptions(kw, optiondefs)
	Pmw.MegaWidget.__init__(self, master)
	self.lists = []
	for label,width in lists:
            self.addList(label,width)
	frame = Frame(self.component('hull'))
        frame.pack(side='right', fill=Y)
	Label(frame, borderwidth=1, relief='raised').pack(fill=X)
	sb = Scrollbar(frame, orient='vertical', command=self._scroll)
	sb.pack(expand='yes', fill='y')
	self.lists[0]['yscrollcommand']=sb.set

    def addList(self,label,width,before=None):
        """dp"""
        try:
            frame = self.createcomponent('frame %s' % (label),(),None,Frame,
                                         (self.component('hull'),))
        except ValueError:
            # Already exists
            return
        if not before is None:
            try:
                widget = self.component('frame %s' % (before))
            except KeyError:
                before = None
        if before is None:
            frame.pack(side='left', expand='yes', fill='both')
        else:
            frame.pack(side='left', expand='yes', fill='both',before=widget)
        widget = self.createcomponent('label %s' % (label),(),label,Label,
                                      (frame, ),
                                      text=label, borderwidth=1,
                                      anchor='w',height=1,width=width,
                                      relief='raised',wraplength=0)
        widget.bind('<Button-1>', lambda e,s=self,l=label:s.selectColumn(e,l))
        widget.pack(fill='x')
        lb = self.createcomponent('list %s' % (label),(),label,Listbox,
                                  (frame, ),
                                  width=width, borderwidth=0,
                                  selectborderwidth=0,
                                  relief='flat', exportselection='false')
        lb.pack(expand='yes', fill='both')
        if before is None:
            self.lists.append(lb)
        else:
            # Insert in correct order
            for index in range(len(self.lists)):
                if self.lists[index] is self.component('list %s' % (before)):
                    self.lists.insert(index,lb)
                    break
            else:
                self.lists.append(lb)
        lb.bind('<Double-ButtonRelease-1>', lambda e, s=self: s._double(e))
        lb.bind('<B1-Motion>', lambda e, s=self: s._select(e.y))
        lb.bind('<Button-1>', lambda e, s=self: s._select(e.y))
        lb.bind('<Shift-1>', lambda e, s=self: s._select(e.y,'shift'))
        lb.bind('<Control-1>', lambda e, s=self: s._select(e.y,'ctrl'))
        lb.bind('<Leave>', lambda e: 'break')
        lb.bind('<B2-Motion>', lambda e, s=self: s._b2motion(e.x, e.y))
        lb.bind('<Button-2>', lambda e, s=self: s._button2(e.x, e.y))

    def delList(self,label):
        """dp"""
        widget = self.component('list %s' % (label))
        for index in range(len(self.lists)):
            if self.lists[index] is widget:
                break
        else:
            raise UserWarning,'Unable to find list %s to delete' % (label)
        del self.lists[index]
        self.destroycomponent('list %s' % (label))
        self.destroycomponent('label %s' % (label))
        self.destroycomponent('frame %s' % (label))
        
    def selectColumn(self,event,label):
        """dp"""
        self.selection_clear(0,'end')
        widget = self.component('list %s' % (label))
        widget.selection_set(0,'end')
        if self['colselectcommand']:
            self['colselectcommand'](label)
        
    def _select(self, y,modifier=None):
	row = self.lists[0].nearest(y)
        if modifier is None:
            self.selection_clear(0, 'end')
            self.selection_set(row)
        elif modifier == 'shift':
            selection = list(self.curselection())
            if row < selection[0]:
                self.selection_set(row,selection[0])
            else:
                self.selection_set(selection[0],row)
        if self['rowselectcommand']:
            self['rowselectcommand'](row)
	return 'break'
        
    def _double(self,event,modifier=None):
        """dp"""
	row = self.lists[0].nearest(event.y)
        if self['doublecommand']:
            self['doublecommand'](row,event)
	return 'break'

    def _button2(self, x, y):
	for l in self.lists: l.scan_mark(x, y)
	return 'break'

    def _b2motion(self, x, y):
	for l in self.lists: l.scan_dragto(x, y)
	return 'break'

    def _scroll(self, *args):
	for l in self.lists:
	    apply(l.yview, args)

    def curselection(self):
	return self.lists[0].curselection()

    def delete(self, first, last=None):
	for l in self.lists:
	    l.delete(first, last)

    def get(self, first, last=None):
	result = []
	for l in self.lists:
	    result.append(l.get(first,last))
	if last: return apply(map, [None] + result)
	return result
	    
    def index(self, index):
	self.lists[0].index(index)

    def insert(self, index, *elements):
	for e in elements:
	    i = 0
	    for l in self.lists:
		l.insert(index, e[i])
		i = i + 1

    def size(self):
	return self.lists[0].size()

    def see(self, index):
	for l in self.lists:
	    l.see(index)

    def selection_anchor(self, index):
	for l in self.lists:
	    l.selection_anchor(index)

    def selection_clear(self, first, last=None):
	for l in self.lists:
	    l.selection_clear(first, last)

    def selection_includes(self, index):
	return self.lists[0].selection_includes(index)

    def selection_set(self, first, last=None):
	for l in self.lists:
	    l.selection_set(first, last)

if __name__ == '__main__':
    tk = Tk()
    Label(tk, text='MultiListbox').pack()
    mlb = MultiListbox(tk, (('Subject', 40), ('Sender', 20), ('Date', 10)))
    for i in range(1000):
	mlb.insert(END, ('Important Message: %d' % i, 'John Doe', '10/10/%04d' % (1900+i)))
    mlb.pack(expand=YES,fill=BOTH)
    tk.mainloop()

