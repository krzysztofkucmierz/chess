
from theme import Theme

class Config:
    def __init__(self):
        self.themes = []
        self._add_themes()
        self.idx=0
        self.theme = self.themes[self.idx]
    
    def change_theme(self):
        self.idx += 1
        self.idx %= len(self.themes)
        self.theme = self.themes[self.idx]
    
    def _add_themes(self):
        green = Theme((234, 234, 200), (119, 154, 88), (244, 247, 116), (177, 195, 51), '#C86464', '#C84646')
        brown = Theme((235, 209, 166), (165, 117, 80), (245, 234, 100), (209, 185, 59), '#C86464', '#C84646')
        blue = Theme((229, 228, 200), (60, 95, 135), (123, 187, 227), (43, 119, 191), '#C86464', '#C84646')
        gray = Theme((120, 119, 118), (86, 85, 84), (99, 126, 143), (82, 102, 128), '#C86464', '#C84646')
        
        self.themes = [green, brown, blue, gray]