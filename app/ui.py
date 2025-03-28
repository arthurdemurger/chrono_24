import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, BooleanVar

from .core import CyclingCore
from .simulation import SimulationManager
from .utils import format_lap_duration

class CyclingEventApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chronomètre 24h - Vélo du Bois de la Cambre")
        self.root.geometry("1200x700")

        self.core = CyclingCore(self)
        self.simulation = SimulationManager(self)
        self.simulation_active = False

        # Construction de l'interface
        self.build_ui()

        # Lancement de la mise à jour du chrono
        self.core.update_timer()

    def build_ui(self):
        # ===============================
        # Section 1 : Haut (Chronomètre et Totaux)
        # ===============================
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.grid(row=0, column=0, columnspan=4, sticky="ew")

        self.label_elapsed = ttk.Label(top_frame, text="00:00:00", font=("Helvetica", 24))
        self.label_elapsed.grid(row=0, column=0, padx=20, sticky="w")

        start_button = ttk.Button(top_frame, text="Démarrer 24h", command=self.core.start_24h)
        start_button.grid(row=0, column=1, padx=10)

        self.label_rouleur_1_total = ttk.Label(top_frame, text="Total Rosaire (Bike 1): 0", font=("Helvetica", 12))
        self.label_rouleur_1_total.grid(row=0, column=2, padx=10)

        self.label_peloton_total = ttk.Label(top_frame, text="Total Peloton: 0", font=("Helvetica", 12))
        self.label_peloton_total.grid(row=0, column=3, padx=10)

        self.label_tma_total = ttk.Label(top_frame, text="Total TMA: 0", font=("Helvetica", 12))
        self.label_tma_total.grid(row=0, column=4, padx=10)

        # ===============================
        # Section 2 : Panneau de Boutons (Tours et Sélection Multiple)
        # ===============================
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.grid(row=1, column=0, columnspan=4, sticky="ew")

        btn_rouleur1 = ttk.Button(button_frame, text="Tour Vélo 1", command=self.core.record_rouleur_1)
        btn_rouleur1.grid(row=0, column=0, padx=5)

        btn_peloton = ttk.Button(button_frame, text="Tour Peloton", command=self.core.record_peloton)
        btn_peloton.grid(row=0, column=1, padx=5)

        btn_tma = ttk.Button(button_frame, text="Tour TMA", command=self.core.record_tma)
        btn_tma.grid(row=0, column=2, padx=5)

        selection_box = ttk.Labelframe(button_frame, text="Sélection multiple", padding=5)
        selection_box.grid(row=0, column=3, padx=5)

        self.chk_bike1 = BooleanVar(value=False)
        self.chk_peloton = BooleanVar(value=False)
        self.chk_tma = BooleanVar(value=False)

        c1 = ttk.Checkbutton(selection_box, text="Vélo 1", variable=self.chk_bike1)
        c1.pack(anchor="w")
        c2 = ttk.Checkbutton(selection_box, text="Peloton", variable=self.chk_peloton)
        c2.pack(anchor="w")
        c3 = ttk.Checkbutton(selection_box, text="TMA", variable=self.chk_tma)
        c3.pack(anchor="w")

        btn_selection = ttk.Button(selection_box, text="Tour sélection", command=self.record_selection)
        btn_selection.pack(pady=5)

        dummy_button = ttk.Button(button_frame, text="Ajouter Tour Manuellement", command=self.core.add_dummy_lap)
        dummy_button.grid(row=0, column=4, padx=5)

        undo_button = ttk.Button(button_frame, text="Annuler Dernier Tour", command=self.core.undo_last_lap)
        undo_button.grid(row=0, column=5, padx=5)

        reset_button = ttk.Button(button_frame, text="Réinitialiser", command=self.core.reset_laps)
        reset_button.grid(row=0, column=6, padx=5)

        manage_button = ttk.Button(button_frame, text="Gérer Tours", command=self.core.open_lap_management_window)
        manage_button.grid(row=0, column=7, padx=5)

        # ===============================
        # Section 3 : Sélection du Rider + File d'attente (Réorganisée et centrée)
        # ===============================
        section_frame = ttk.Frame(self.root, padding=10)
        section_frame.grid(row=3, column=0, columnspan=4, sticky="nsew")


        # --- Partie haute : Rouleur actuel ---
        current_frame = ttk.Frame(section_frame)
        current_frame.grid(row=0, column=0, sticky="n", padx=10, pady=10)

        self.current_rider_label = tk.Label(
            current_frame,
            text=f"Rouleur actuel : {self.core.current_rouleur}",
            font=("Helvetica", 18, "bold"),
            fg="white",
            bg="red",
            padx=20,
            pady=10
        )
        self.current_rider_label.pack(side="top", fill="x", expand=True)

        next_rider_button = ttk.Button(
            current_frame,
            text="Passer au rouleur suivant",
            command=self.core.next_rouleur
        )
        next_rider_button.pack(side="top", pady=5)

        # --- Partie basse : File d'attente et boutons de gestion ---
        list_btn_frame = ttk.Frame(section_frame)
        list_btn_frame.grid(row=0, column=1, sticky="n", padx=10, pady=10)

        # Cadre gauche : Treeview de la file d'attente
        list_frame = ttk.Frame(list_btn_frame)
        list_frame.grid(row=0, column=0, sticky="n", padx=10, ipady=20)

        self.queue_label = ttk.Label(list_frame,
                                     text="File d'attente des rouleurs",
                                     font=("Helvetica", 14, "bold"))
        self.queue_label.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="w")

        self.queue_tree = ttk.Treeview(list_frame, columns=("Riders",), show="headings", height=10)
        self.queue_tree.heading("Riders", text="Rouleur dans la file")
        self.queue_tree.column("Riders", width=200, anchor="center")
        self.queue_tree.grid(row=1, column=0, columnspan=2, sticky="w")

        # Sélection d’un rouleur
        self.rider_selector = ttk.Combobox(list_frame, values=self.core.riders, state="readonly")
        self.rider_selector.grid(row=3, column=0, sticky="w", padx=5, pady=5)

        add_rider_button = ttk.Button(list_frame, text="Ajouter à la file", command=self.core.add_to_queue)
        add_rider_button.grid(row=4, column=0, sticky="w", padx=5)

        # Ajout d'une scrollbar verticale pour le Treeview
        queue_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.queue_tree.yview)
        queue_scrollbar.grid(row=1, column=2, sticky="ns")
        self.queue_tree.configure(yscrollcommand=queue_scrollbar.set)

        # Cadre droit : Boutons de gestion
        btn_frame = ttk.Frame(list_btn_frame)
        btn_frame.grid(row=0, column=1, sticky="n", padx=10)

        # Boutons pour monter et descendre dans la file
        up_btn = ttk.Button(btn_frame, text="↑ Monter", command=self.core.move_rider_up)
        up_btn.grid(row=0, column=0, padx=5, pady=2, sticky="ew")

        down_btn = ttk.Button(btn_frame, text="↓ Descendre", command=self.core.move_rider_down)
        down_btn.grid(row=1, column=0, padx=5, pady=2, sticky="ew")

        # Bouton pour retirer le rouleur sélectionné via la Combobox
        remove_btn = ttk.Button(btn_frame, text="Retirer", command=self.core.remove_from_queue)
        remove_btn.grid(row=3, column=0, padx=5, pady=2, sticky="ew")

        # Bouton pour réinitialiser la file d'attente
        reset_btn = ttk.Button(btn_frame, text="🔁 Reset", command=self.core.confirm_reset_queue)
        reset_btn.grid(row=4, column=0, padx=5, pady=2, sticky="ew")

        # ===============================
        # Section 4 : Affichage de l'Écart (Gap)
        # ===============================
        self.label_gap = ttk.Label(self.root, text="Current gap: N/A",
                                   font=("Helvetica", 14, "bold"), foreground="red")
        self.label_gap.grid(row=4, column=0, columnspan=4, pady=10)

        # ===============================
        # Section 5 : Tableaux des Derniers Tours
        # ===============================
        tables_frame = ttk.Frame(self.root, padding=10)
        tables_frame.grid(row=5, column=0, columnspan=4, sticky="ew")

        bike1_frame = ttk.Frame(tables_frame)
        bike1_frame.grid(row=0, column=0, padx=10)
        self.build_table_with_header(bike1_frame, "Vélo 1")

        peloton_frame = ttk.Frame(tables_frame)
        peloton_frame.grid(row=0, column=1, padx=10)
        self.build_table_with_header(peloton_frame, "Peloton")

        tma_frame = ttk.Frame(tables_frame)
        tma_frame.grid(row=0, column=2, padx=10)
        self.build_table_with_header(tma_frame, "TMA")

        # ===============================
        # Section 6 : Statistiques, Export et Simulation
        # ===============================
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.grid(row=6, column=0, columnspan=4, sticky="ew")

        stats_button = ttk.Button(bottom_frame, text="Voir Statistiques", command=self.core.show_stats_window)
        stats_button.grid(row=0, column=0, padx=5)

        export_button = ttk.Button(bottom_frame, text="Exporter CSV", command=self.core.export_csv)
        export_button.grid(row=0, column=1, padx=5)

        sim_frame = ttk.Labelframe(bottom_frame, text="Simulation", padding=10)
        sim_frame.grid(row=0, column=2, padx=10)

        ttk.Label(sim_frame, text="Durée (min, secondes) :").grid(row=0, column=0, padx=5)
        self.sim_duration_entry = ttk.Entry(sim_frame, width=7)
        self.sim_duration_entry.insert(0, "4:0")
        self.sim_duration_entry.grid(row=0, column=1, padx=5)

        sim_button = ttk.Button(sim_frame, text="Démarrer", command=self.start_sim_with_duration)
        sim_button.grid(row=0, column=2, padx=5)

    def build_table_with_header(self, parent_frame, type_label):
        # En-tête du tableau
        header_frame = ttk.Frame(parent_frame)
        header_frame.pack(side="top", fill="x")

        label_current = ttk.Label(header_frame, text=f"{type_label} Current: 00:00",
                                  font=("Helvetica", 14, "bold"))
        label_current.pack(anchor="w")

        label_avg5 = ttk.Label(header_frame, text="Moyenne (5 derniers): N/A",
                               font=("Helvetica", 10))
        label_avg5.pack(anchor="w")

        label_diff1 = ttk.Label(header_frame, text="Écart vs X: N/A", font=("Helvetica", 10))
        label_diff1.pack(anchor="w")
        label_diff2 = ttk.Label(header_frame, text="Écart vs Y: N/A", font=("Helvetica", 10))
        label_diff2.pack(anchor="w")

        # Cadre contenant le tableau
        labelframe = ttk.LabelFrame(parent_frame, text=f"Derniers tours {type_label}", padding=10)
        labelframe.pack(side="top", fill="both", expand=True)

        tree = ttk.Treeview(labelframe,
                            columns=("lapnum", "rider", "laptime", "timediff", "lapdur"),
                            show="headings", height=10)
        columns = [
            ("lapnum", "Lap #", 60),
            ("rider", "Rider", 90),
            ("laptime", "Lap Time", 90),
            ("timediff", "Time Diff", 90),
            ("lapdur", "Lap Duration", 90)
        ]
        for col, head, width in columns:
            tree.heading(col, text=head)
            tree.column(col, width=width, anchor="center")
        tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(labelframe, orient="vertical", command=tree.yview)
        scroll.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scroll.set)

        # Stockage des références selon le type
        if type_label == "Vélo 1":
            self.header_bike1_current = label_current
            self.header_bike1_avg5 = label_avg5
            self.header_bike1_diff1 = label_diff1
            self.header_bike1_diff2 = label_diff2
            self.bike1_tree = tree
        elif type_label == "Peloton":
            self.header_peloton_current = label_current
            self.header_peloton_avg5 = label_avg5
            self.header_peloton_diff1 = label_diff1
            self.header_peloton_diff2 = label_diff2
            self.peloton_tree = tree
        else:
            self.header_tma_current = label_current
            self.header_tma_avg5 = label_avg5
            self.header_tma_diff1 = label_diff1
            self.header_tma_diff2 = label_diff2
            self.tma_tree = tree

    def record_selection(self):
        checked = []
        if self.chk_bike1.get():
            checked.append("Vélo 1")
        if self.chk_peloton.get():
            checked.append("Peloton")
        if self.chk_tma.get():
            checked.append("TMA")

        if not checked:
            messagebox.showinfo("Info", "Aucune sélection cochée.")
            return

        for grp in checked:
            if grp == "Vélo 1":
                self.core.record_rouleur_1()
            elif grp == "Peloton":
                self.core.record_peloton()
            else:
                self.core.record_tma()

    def start_sim_with_duration(self):
        if self.simulation_active:
            messagebox.showwarning("Erreur", "Une simulation est déjà en cours.")
            return

        val = self.sim_duration_entry.get().strip()
        if ':' in val:
            parts = val.split(':')
            if len(parts) == 2:
                try:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    if minutes < 0 or seconds < 0:
                        raise ValueError("Les valeurs doivent être positives.")
                    duration_secs = (minutes * 60) + seconds
                    self.simulation_active = True
                    self.simulation.start_simulation(duration=duration_secs)
                except ValueError:
                    messagebox.showerror("Erreur", "Veuillez entrer une durée valide (ex: 2:30 pour 2 minutes 30 secondes).")
            else:
                messagebox.showerror("Erreur", "Veuillez entrer une durée au format 'minutes:secondes'.")
        else:
            try:
                valf = float(val)
                if valf <= 0:
                    raise ValueError
                duration_secs = valf * 60
                self.simulation.start_simulation(duration=duration_secs)
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un nombre valide ou une durée au format 'minutes:secondes'.")

    def run(self):
        self.root.mainloop()
