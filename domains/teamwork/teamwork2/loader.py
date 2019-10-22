from Tkinter import *

stored = []
MAP_SIZE_X = 0
MAP_SIZE_Y = 0

F_ACTORS = 0
F_START_LOC = []
F_GOAL_LOC = []

E_ACTORS = 0
E_START_LOC = []
E_PATROL_RANGE = 5

D_ACTORS = 0
D_START_LOC = []

BASE = [0.0, 0.0]
DISTRACTOR = [0.0, 0.0]
ENEMY = [0.0, 0.0, 0.0]
AGENT = [0.0, 0.0]

ready = False

class BaseLoader:

    def __init__(self, master):
        master.wm_title("Scenario Config")
        labels = ["Map Size X", "Map Size Y", "Soldiers", "Enemies", "Bases"]  # Display text
        fields = []  # Fields for storing entries
        for i in range(0, 5):
            Label(master, text=labels[i]).grid(row=i)
            fields.append(Entry(master, width=5))
            fields[i].grid(row=i, column=1)

        labels = ["Soldier Rewards:", "S/G Dist", "S/E Dist",
                  "Base Rewards:", "H/E Dist", "H Cost",
                  "Helicopter Rewards:", "H/E Dist", "S/E Dist",
                  "Enemy Rewards:", "S/E Dist", "H/E Dist", "S/G Dist"]
        weights = [None] * 14

        for i in range(0, len(labels)):
            Label(master, text=labels[i]).grid(row=i + 6)
            if i % 3 or i == 12:
                weights[i] = Entry(master, width=5)
                weights[i].grid(row=i + 6, column=1)

        def configure():
            for i in range(0, 5):
                fields[i].configure(state='disabled')

            newWindow = Toplevel(master)
            app = AdvancedLoader(newWindow, fields)


        def load_default():
            defaults = [8, 5, 1, 1, 1]
            for i in range(0, 5):
                fields[i].configure(state='normal')
                fields[i].delete(0, 'end')
                fields[i].insert(0, defaults[i])

            default_weights = [None, 0.5, -0.5, None, 0.5, 0.2, None, -1.0, 1.0, None, 0.5, 0.6, -1.0]
            for i in range(0, len(labels)):
                if i % 3 or i == 12:
                    weights[i].delete(0, 'end')
                    weights[i].insert(0, default_weights[i])

        def run_configuration():
            global stored
            global MAP_SIZE_X
            global MAP_SIZE_Y
            global F_ACTORS
            global F_START_LOC
            global F_GOAL_LOC
            global E_ACTORS
            global E_START_LOC
            global E_PATROL_RANGE
            global D_ACTORS
            global D_START_LOC
            global BASE
            global DISTRACTOR
            global ENEMY
            global AGENT
            global ready
            MAP_SIZE_X = int(fields[0].get())
            MAP_SIZE_Y = int(fields[1].get())
            F_ACTORS = int(fields[2].get())
            F_START_LOC = stored[0]
            F_GOAL_LOC = stored[1]
            E_ACTORS = int(fields[3].get())
            E_START_LOC = stored[2]
            D_ACTORS = int(fields[4].get())
            D_START_LOC = stored[3]
            AGENT = [float(weights[1].get()), float(weights[2].get())]
            BASE = [float(weights[4].get()), float(weights[5].get())]
            DISTRACTOR = [float(weights[7].get()), float(weights[8].get())]
            ENEMY = [float(weights[10].get()), float(weights[11].get()), float(weights[12].get())]

            # print('MAP_SIZE_X: ' + self.MAP_SIZE_X)
            # print('MAP_SIZE_Y: ' + self.MAP_SIZE_Y)
            # print('self.F_ACTORS: ' + self.F_ACTORS)
            # print('self.F_START_LOC')
            # print(self.F_START_LOC)
            # print('self.F_GOAL_LOC')
            # print(self.F_GOAL_LOC)
            # print('self.E_ACTORS' + self.E_ACTORS)
            # print('self.E_START_LOC')
            # print(self.E_START_LOC)
            # print('self.D_ACTORS' + self.D_ACTORS)
            # print('self.D_START_LOC')
            # print(self.D_START_LOC)
            # print(self.AGENT)
            # print(self.BASE)
            # print(self.DISTRACTOR)
            ready = True
            # print(self.ENEMY)
            # [soldier_locations_values, soldier_goals_values, enemy_locations_values, base_locations_values]
            master.quit()


        Button(master, text='Configure', command=configure).grid(row=100, column=0, sticky=E + W, pady=4)
        Button(master, text='Default', command=load_default).grid(row=100, column=1, sticky=E + W, pady=4)
        Button(master, text='Save', command=run_configuration).grid(row=101, column=0, sticky=E + W, pady=4)


class AdvancedLoader:
    soldier_locations = []
    soldier_goals = []
    enemy_locations = []
    base_locations = []

    def __init__(self, master, fields):
        self.master = master
        soldiers_count = int(fields[2].get())
        enemies_count = int(fields[3].get())
        bases_count = int(fields[4].get())

        Label(master, text='x').grid(row=0, column=1)
        Label(master, text='y').grid(row=0, column=2)

        for i in range(0, soldiers_count):
            Label(master, text='Soldier' + str(i) + " Location:").grid(row=i + 1)
            soldier_x = Entry(master, width=5)
            soldier_x.grid(row=i + 1, column=1)
            soldier_x.insert(0, "1")
            soldier_y = Entry(master, width=5)
            soldier_y.grid(row=i + 1, column=2)
            soldier_y.insert(0, "2")
            location = [soldier_x, soldier_y]
            self.soldier_locations.append(location)

        for i in range(0, soldiers_count):
            Label(master, text='Soldier' + str(i) + " Goal:").grid(row=i + soldiers_count + 1)
            soldier_x = Entry(master, width=5)
            soldier_x.grid(row=i + soldiers_count + 1, column=1)
            soldier_x.insert(0, "5")
            soldier_y = Entry(master, width=5)
            soldier_y.grid(row=i + soldiers_count + 1, column=2)
            soldier_y.insert(0, "4")
            location = [soldier_x, soldier_y]
            self.soldier_goals.append(location)

        for i in range(0, enemies_count):
            Label(master, text='Enemy' + str(i) + " Location:").grid(row=i + 2 * soldiers_count + 1)
            enemy_x = Entry(master, width=5)
            enemy_x.grid(row=i + 2 * soldiers_count + 1, column=1)
            enemy_x.insert(0, "4")
            enemy_y = Entry(master, width=5)
            enemy_y.grid(row=i + 2 * soldiers_count + 1, column=2)
            enemy_y.insert(0, "3")
            location = [enemy_x, enemy_y]
            self.enemy_locations.append(location)

        for i in range(0, bases_count):
            Label(master, text='Base' + str(i) + " Location:").grid(row=i + 2 * soldiers_count + enemies_count + 1)
            base_x = Entry(master, width=5)
            base_x.grid(row=i + 2 * soldiers_count + enemies_count + 1, column=1)
            base_x.insert(0, "0")
            base_y = Entry(master, width=5)
            base_y.grid(row=i + 2 * soldiers_count + enemies_count + 1, column=2)
            base_y.insert(0, "0")
            location = [base_x, base_y]
            self.base_locations.append(location)

        Button(master, text='Save Locations', command=self.return_locations).grid(row=100, column=0, sticky=E + W,
                                                                                  pady=4)

    def return_locations(self):
        soldier_locations_values = []
        soldier_goals_values = []
        enemy_locations_values = []
        base_locations_values = []
        for i in range(0, len(self.soldier_locations)):
            soldier_locations_values.append(
                str(self.soldier_locations[i][0].get()) + ',' + str(self.soldier_locations[i][1].get()))
        # print(soldier_locations_values)

        for i in range(0, len(self.soldier_locations)):
            soldier_goals_values.append(
                str(self.soldier_goals[i][0].get()) + ',' + str(self.soldier_goals[i][1].get()))
        # print(soldier_goals_values)

        for i in range(0, len(self.enemy_locations)):
            enemy_locations_values.append(
                str(self.enemy_locations[i][0].get()) + ',' + str(self.enemy_locations[i][1].get()))
        # print(enemy_locations_values)

        for i in range(0, len(self.base_locations)):
            base_locations_values.append(
                str(self.base_locations[i][0].get()) + ',' + str(self.base_locations[i][1].get()))
        # print(base_locations_values)
        global stored
        stored = [soldier_locations_values, soldier_goals_values, enemy_locations_values, base_locations_values]
