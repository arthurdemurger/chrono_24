import tkinter as tk
import time
import json

class SimulationManager:
    def __init__(self, app):
        self.app = app
        self.simulation_running = False  # Indicateur de l'état de la simulation
        self.start_time = None
        self.duration_seconds = 240.0  # 4 min par défaut

        try:
            with open("data/coordinates_transformed.json", "r") as f:
                self.coordinates = json.load(f)
        except FileNotFoundError:
            self.coordinates = []
            print("Fichier coordinates_transformed.json introuvable.")

    def start_simulation(self, duration=None):
        """
        Lance la simulation même si elle a déjà été fermée auparavant.
        `duration` est en secondes (float). S'il est None, on garde 240.0.
        """
        if self.simulation_running:
            print("Une simulation est déjà en cours.")
            return  # Si la simulation est déjà en cours, on ne fait rien

        if duration is not None:
            self.duration_seconds = duration
        if not self.coordinates:
            return

        # Crée/rouvre la fenêtre
        self.simulation_running = True
        self.start_time = time.time()

        self.win = tk.Toplevel(self.app.root)
        self.win.title("Simulation")

        # Pour détecter la fermeture -> on repasse simulation_running à False
        self.win.protocol("WM_DELETE_WINDOW", self.on_close_window)

        self.canvas = tk.Canvas(self.win, width=400, height=400, bg="white")
        self.canvas.pack()

        # Trace le parcours
        for i in range(1, len(self.coordinates)):
            self.canvas.create_line(
                self.coordinates[i - 1][0], self.coordinates[i - 1][1],
                self.coordinates[i][0], self.coordinates[i][1],
                fill="blue"
            )

        # Crée le point rouge
        if self.coordinates:
            x0, y0 = self.coordinates[0]
            self.dot = self.canvas.create_oval(x0-5, y0-5, x0+5, y0+5, fill="red")
        else:
            self.dot = None

        self.update_simulation()

    def update_simulation(self):
        if not self.simulation_running or not self.coordinates:
            return

        elapsed = time.time() - self.start_time
        total = self.duration_seconds
        progress = elapsed / total

        if progress < 1.0:
            index = int(progress * len(self.coordinates))
            if index >= len(self.coordinates):
                index = len(self.coordinates) - 1
            x, y = self.coordinates[index]
            if self.dot:
                self.canvas.coords(self.dot, x-5, y-5, x+5, y+5)
            self.win.after(50, self.update_simulation)
        else:
            # Fin de la simulation
            self.simulation_running = False
            self.app.simulation_active = False  # Mise à jour de l'état dans l'application

    def on_close_window(self):
        """
        Appelé quand on ferme la fenêtre simulation. On repasse la variable
        simulation_running à False pour autoriser un nouveau lancement.
        """
        self.simulation_running = False
        self.app.simulation_active = False  # Mise à jour de l'état dans l'application
        self.win.destroy()
