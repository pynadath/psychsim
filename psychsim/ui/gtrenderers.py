import os
from abc import ABC, abstractmethod
import pygame
from pygame import gfxdraw


class Renderer(ABC):

    def handleInput(self ):
        keys = pygame.key.get_pressed()
    
    def __init__(self):
        pass

    @abstractmethod
    def DrawCircle(self, x, y, r, color):
        pass
    @abstractmethod
    def DrawRectangle(self, x, y, w, h, color):
        pass
    @abstractmethod
    def DrawImage(self, x, y, name, dimx, dimy):
        pass

class PixiRenderer(Renderer):
    def __init__(self, context):
        self.context = context 
    def DrawCircle(self, x, y, r, color):
        super().DrawCircle(x, y, r, color)
    def DrawRectangle(self, x, y, w, h, color):
        super().DrawRectangle(x, y, w, h, color)   
    def DrawImage(self, x, y, name, dimx, dimy):
        super().DrawImage(x, y, name, dimx, dimy)

class PyGameRenderer(Renderer):

    def setCaption(self, caption):
        pygame.display.set_caption(caption)

    def __init__(self, sWidth, sHeight):
        
        self._win = pygame.display.set_mode((sWidth, sHeight))

# pylint: disable=no-member 
        pygame.init()
# pylint: enable=no-member
        self.setCaption("Visualization")
        self.getImages()

    def getImages(self):
        self.hurricaneImages = {}
        self.hurricaneImages['cat1'] = pygame.image.load(os.path.join(os.path.dirname(__file__), 'images','hurricane_category_1.png'))
        self.hurricaneImages['cat2'] = pygame.image.load(os.path.join(os.path.dirname(__file__), 'images','hurricane_category_2.png'))
        self.hurricaneImages['cat3'] = pygame.image.load(os.path.join(os.path.dirname(__file__), 'images','hurricane_category_3.png'))
        self.hurricaneImages['cat4'] = pygame.image.load(os.path.join(os.path.dirname(__file__), 'images','hurricane_category_4.png'))
        self.hurricaneImages['cat5'] = pygame.image.load(os.path.join(os.path.dirname(__file__), 'images','hurricane_category_5.png'))
        

    def DrawCircle(self, x, y, r, color):
        super().DrawCircle(x, y, r, color)
        pygame.gfxdraw.filled_circle(self._win, x, y, r, color)
        pygame.gfxdraw.aacircle(self._win, x, y, r, (0,0,0))

    def DrawRectangle(self, x, y, w, h, color):
        super().DrawRectangle(x, y, w, h, color)   
        pygame.draw.rect(self._win, color, (x, y, w, h))

        #rect = pygame.draw.rect(self._win, color, (x, y, w, h))
        #mouse over code below
        # if rect.collidepoint(pygame.mouse.get_pos()):
        #     s = pygame.Surface((w,h), pygame.SRCALPHA)
        #     s.set_alpha(127)
        #     s.fill((127, 127, 127))                        
        #     self._win.blit(s, (x, y)) 

    def DrawImage(self, x, y, name, dimx, dimy):
        image = self.hurricaneImages['cat%d'%name]
        image = pygame.transform.smoothscale(image, (dimx, dimy))


        super().DrawImage(x, y, name, dimx, dimy)
        self._win.blit(image, (x, y))

    def preUpdate(self):
        self._win.fill((0,0,0))
    
    def update(self):

        pygame.time.delay(100)
        for event in pygame.event.get():
# pylint: disable=no-member 
            if event.type == pygame.QUIT:
# pylint: enable=no-member 
                pygame.display.quit()        
                return False
        self.handleInput()
        pygame.display.update()
        return True
    
    def CloseRenderer(self):
        pygame.display.quit()