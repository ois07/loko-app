from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDList, TwoLineListItem
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.dialog import MDDialog
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.uix.widget import Widget
from kivy.metrics import dp
import sqlite3, os, datetime

DB_PATH = os.path.join(os.path.expanduser("~"), "locomotive.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS elements(id INTEGER PRIMARY KEY, name TEXT, scheme_key TEXT);
    CREATE TABLE IF NOT EXISTS faults(id INTEGER PRIMARY KEY, element_id INTEGER, code TEXT, description TEXT);
    CREATE TABLE IF NOT EXISTS norms(id INTEGER PRIMARY KEY, fault_id INTEGER, series TEXT, norm TEXT, method TEXT, source TEXT);
    CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, series TEXT, loco_num TEXT, element TEXT, fault TEXT, inspector TEXT, date TEXT, note TEXT);
    """)
    c.executemany("INSERT OR IGNORE INTO elements(id,name,scheme_key) VALUES (?,?,?)", [
        (1,"Ось","axle"),(2,"Бандаж - гребень","flange"),
        (3,"Бандаж - поверхность катания","tread"),
        (4,"Ступица","hub"),(5,"Диск/спицы","spokes"),
        (6,"Подшипник буксы","bearing"),(7,"Корпус буксы","box"),
        (8,"МОП","mop"),(9,"Тормозная колодка","brake")])
    c.execute("INSERT OR IGNORE INTO faults(id,element_id,code,description) VALUES (1,2,'ХЧ-001','Толщина гребня ниже нормы')")
    c.executemany("INSERT OR IGNORE INTO norms(fault_id,series,norm,method,source) VALUES (?,?,?,?,?)", [
        (1,"ТЭП70",">=25 мм","Обточить","Руководство ТЭП70"),
        (1,"ТЭП70БС",">=25 мм","Обточить","Руководство ТЭП70БС"),
        (1,"ЭП1",">=28 мм","Обточка профиля","Руководство ЭП1"),
        (1,"ЭП1М",">=28 мм","Обточка","Руководство ЭП1М"),
        (1,"ТМ18ДМ",">=25 мм","Обточка","Руководство ТМ18ДМ"),
        (1,"ЧМЭ3",">=25 мм","Обточка","Руководство ЧМЭ3")])
    conn.commit()
    return conn

class WheelScheme(Widget):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app; self.zones = []
        self.bind(pos=self.redraw, size=self.redraw)
        
    def redraw(self, *a):
        self.canvas.clear(); w,h = self.width,self.height
        if w<50 or h<50: return
        self.zones = []
        with self.canvas:
            Color(0.7,0.7,0.7)
            Rectangle(pos=(self.x+w*0.1,self.y+h*0.75),size=(w*0.8,h*0.08))
            self.zones.append((self.x+w*0.1,self.y+h*0.75,self.x+w*0.9,self.y+h*0.83,"axle"))
            Color(0.75,0.75,0.75)
            for r in (0.22,0.78):
                cx=self.x+w*r; cy=self.y+h*0.79
                Ellipse(pos=(cx-w*0.07,cy-h*0.06),size=(w*0.14,h*0.12))
                self.zones.append((cx-w*0.07,cy-h*0.06,cx+w*0.07,cy+h*0.06,"tread"))
            Color(1,0.7,0.3)
            for r in (0.1,0.9):
                cx=self.x+w*r; cy=self.y+h*0.79
                Rectangle(pos=(cx-w*0.04,cy-h*0.05),size=(w*0.08,h*0.1))
                self.zones.append((cx-w*0.04,cy-h*0.05,cx+w*0.04,cy+h*0.05,"box"))
            Color(0.8,0.6,0.85)
            Ellipse(pos=(self.x+w*0.42,self.y+h*0.76),size=(w*0.16,h*0.07))
            self.zones.append((self.x+w*0.42,self.y+h*0.76,self.x+w*0.58,self.y+h*0.83,"mop"))
            
            cx,cy=self.x+w*0.5,self.y+h*0.37; r=min(w*0.18,h*0.25)
            Color(0.75,0.75,0.75); Ellipse(pos=(cx-r,cy-r),size=(2*r,2*r))
            self.zones.append((cx-r,cy-r,cx+r,cy+r,"tread"))
            Color(0.88,0.88,0.88); Ellipse(pos=(cx-r*0.7,cy-r*0.7),size=(1.4*r,1.4*r))
            self.zones.append((cx-r*0.7,cy-r*0.7,cx+r*0.7,cy+r*0.7,"spokes"))
            Color(0.45,0.45,0.45); Ellipse(pos=(cx-r*0.25,cy-r*0.25),size=(r*0.5,r*0.5))
            self.zones.append((cx-r*0.25,cy-r*0.25,cx+r*0.25,cy+r*0.25,"hub"))
            Color(0.94,0.33,0.31); Rectangle(pos=(cx-r*0.25,cy-r-8),size=(r*0.5,8))
            self.zones.append((cx-r*0.25,cy-r-8,cx+r*0.25,cy-r,"flange"))
            Color(0.55,0.4,0.35); Rectangle(pos=(cx+r+5,cy-15),size=(18,30))
            self.zones.append((cx+r+5,cy-15,cx+r+23,cy+15,"brake"))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): return False
        for x1,y1,x2,y2,key in self.zones:
            if x1<=touch.x<=x2 and y1<=touch.y<=y2:
                self.app.select_element(key); return True
        return False

class LocoApp(MDApp):
    dialog=None; current_element=None; current_faults=[]
    
    def build(self):
        self.theme_cls.primary_palette="BlueGrey"
        self.conn=init_db()
        return self.build_screen()
        
    def build_screen(self):
        scr=MDScreen()
        main=MDBoxLayout(orientation="vertical",padding=dp(8),spacing=dp(6))
        
        top=MDBoxLayout(size_hint_y=None,height=dp(50),spacing=dp(6))
        self.series_field=MDTextField(text="ТЭП70",hint_text="Серия",mode="rectangle",size_hint_x=0.3)
        self.loco_field=MDTextField(text="",hint_text="Номер",mode="rectangle",size_hint_x=0.25)
        self.insp_field=MDTextField(text="",hint_text="Слесарь",mode="rectangle",size_hint_x=0.45)
        top.add_widget(self.series_field); top.add_widget(self.loco_field); top.add_widget(self.insp_field)
        main.add_widget(top)
        
        self.scheme=WheelScheme(self,size_hint_y=0.55); main.add_widget(self.scheme)
        self.sel_label=MDLabel(text="Кликни по элементу схемы",size_hint_y=None,height=dp(30))
        main.add_widget(self.sel_label)
        
        scroll=MDScrollView(size_hint_y=0.3)
        self.fault_list=MDList(); scroll.add_widget(self.fault_list); main.add_widget(scroll)
        
        btns=MDBoxLayout(size_hint_y=None,height=dp(50),spacing=dp(6))
        btns.add_widget(MDRaisedButton(text="История",on_release=lambda *a:self.show_history()))
        btns.add_widget(MDRaisedButton(text="Зафиксировать",on_release=lambda *a:self.save_record()))
        btns.add_widget(MDRaisedButton(text="Акт",on_release=lambda *a:self.save_act()))
        main.add_widget(btns); scr.add_widget(main); return scr
        
    def select_element(self,key):
        row=self.conn.execute("SELECT id,name FROM elements WHERE scheme_key=?",(key,)).fetchone()
        if not row: self.show_popup("Нет данных","Справочник пуст"); return
        self.current_element=row; self.sel_label.text=f"Элемент: {row[1]}"; self.load_faults()
        
    def load_faults(self):
        self.fault_list.clear_widgets()
        self.current_faults=self.conn.execute("SELECT id,code,description FROM faults WHERE element_id=?",(self.current_element[0],)).fetchall()
        for f in self.current_faults:
            self.fault_list.add_widget(TwoLineListItem(text=f[1],secondary_text=f[2],on_release=lambda x,fid=f[0]:self.show_fault(fid)))
            
    def show_fault(self,fid):
        row=self.conn.execute("SELECT code,description FROM faults WHERE id=?",(fid,)).fetchone()
        series=self.series_field.text.strip() or "ТЭП70"
        norm=self.conn.execute("SELECT norm,method,source FROM norms WHERE fault_id=? AND series=?",(fid,series)).fetchone()
        txt=f"{row[0]}: {row[1]}\n\n"
        txt+= (f"Норма ({series}): {norm[0]}\n\nМетод: {norm[1]}\n\nИсточник: {norm[2]}" if norm else f"Норма для {series} не заполнена")
        self.show_popup("Неисправность",txt)
        
    def save_record(self):
        if not self.current_element: self.show_popup("Внимание","Выбери элемент"); return
        self.conn.execute("INSERT INTO records(series,loco_num,element,fault,inspector,date,note) VALUES (?,?,?,?,?,?,?)",
            (self.series_field.text,self.loco_field.text,self.current_element[1],"",self.insp_field.text,datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),""))
        self.conn.commit(); self.show_popup("Готово","Осмотр записан")
        
    def show_history(self):
        if not self.current_element: self.show_popup("Внимание","Выбери элемент"); return
        rows=self.conn.execute("SELECT date,series,loco_num,inspector FROM records WHERE element=? ORDER BY date DESC LIMIT 15",(self.current_element[1],)).fetchall()
        if not rows: self.show_popup("История","Записей нет"); return
        txt="\n\n".join(f"{d} - {s}-{n} ({i})" for d,s,n,i in rows)
        self.show_popup("История",txt)
        
    def save_act(self):
        if not self.current_element: self.show_popup("Внимание","Выбери элемент"); return
        path=os.path.join(os.path.expanduser("~"),f"act_{datetime.datetime.now():%Y%m%d_%H%M}.txt")
        with open(path,"w",encoding="utf-8") as f:
            f.write(f"АКТ ОСМОТРА\n\nДата: {datetime.datetime.now():%d.%m.%Y %H:%M}\nЛокомотив: {self.series_field.text} № {self.loco_field.text}\nСлесарь: {self.insp_field.text}\nЭлемент: {self.current_element[1]}\n")
        self.show_popup("Акт сохранён",f"Файл:\n{path}")
        
    def show_popup(self,title,text):
        if self.dialog: self.dialog.dismiss()
        self.dialog=MDDialog(title=title,text=text,buttons=[MDFlatButton(text="OK",on_release=lambda *a:self.dialog.dismiss())])
        self.dialog.open()

if __name__ == "__main__":
    LocoApp().run()
