import tkinter as tk
from tkinter import ttk, messagebox
from math import ceil
from collections import defaultdict

# ------------------------------------------------------------
# Hardware Data
# ------------------------------------------------------------
RAID_DATA = [
    ["1U", "ADVER00N0NP16G", 32, 50, 4, 3750],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.7],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.7],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000],
    ["2U 175 Ch", "ADVER00RN2K", 175, 1000, 12, 13854.2],
    ["2U Rack", "ADVER02RDK", 200, 1500, 12, 12812.5],
]

JBOD_DATA = [
    ["Micro", "ADVEM00N0NP8AH", 8, 80, 1, 1500],
    ["1U", "ADVER00N0NP16G", 32, 100, 4, 3750],
    ["Desktop", "ADVED00N0N5H", 50, 200, 2, 2291.7],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.5],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 80, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 160, 1, 770.85],
]

HDD_LIST = [
    (1, 63.15), (2, 94.71), (3, 105.26), (4, 168.42), (6, 215.78),
    (8, 306.42), (10, 355.53), (12, 442.10), (14, 617.98), (18, 720.55),
    (22, 685.28), (24, 863.48), (26, 822.88)
]

class NVR:
    def __init__(self, name, part, cameras, throughput, slots, price):
        self.name, self.part, self.cameras = name, part, cameras
        self.throughput, self.slots, self.price = throughput, slots, price

# ------------------------------------------------------------
# Core Logic
# ------------------------------------------------------------

def get_cheapest_hdd_config(required_tb, max_slots, parity_lvl, hdd_list):
    best_cost = float('inf')
    best_cfg = None
    for cap, price in hdd_list:
        data_drives = ceil(required_tb / cap) if cap > 0 else 1
        total_drives = data_drives + parity_lvl
        # Constraints: JBOD (parity 0) needs >=1 drive, RAID needs >= parity+1
        min_drives = 1 if parity_lvl == 0 else parity_lvl + 1
        
        if min_drives <= total_drives <= max_slots:
            cost = total_drives * price
            if cost < best_cost:
                best_cost = cost
                best_cfg = {'cap': cap, 'qty': total_drives, 'usable': data_drives * cap, 'cost': cost}
    return best_cost, best_cfg

def assign_cameras_min_storage(nvr_units, camera_types):
    nvrs = []
    for n in nvr_units:
        nvrs.append({'obj': n, 'rem_c': n.cameras, 'rem_t': int(n.throughput * 1000), 
                     'assigned': defaultdict(int), 'cur_st': 0.0})
    
    sorted_types = sorted(camera_types, key=lambda x: x['st'], reverse=True)
    for c_type in sorted_types:
        rem_to_place = c_type['qty']
        while rem_to_place > 0:
            best_idx = -1
            min_storage = float('inf')
            for i, n in enumerate(nvrs):
                if n['rem_c'] > 0 and n['rem_t'] >= int(c_type['tp'] * 1000):
                    if n['cur_st'] < min_storage:
                        min_storage = n['cur_st']
                        best_idx = i
            if best_idx == -1: return None
            nvrs[best_idx]['rem_c'] -= 1
            nvrs[best_idx]['rem_t'] -= int(c_type['tp'] * 1000)
            nvrs[best_idx]['assigned'][c_type['id']] += 1
            nvrs[best_idx]['cur_st'] += c_type['st']
            rem_to_place -= 1
    return nvrs

# ------------------------------------------------------------
# GUI Application
# ------------------------------------------------------------

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Hardware Optimizer")
        self.camera_list = []
        self.setup_ui()

    def setup_ui(self):
        # Top Input Area
        input_frame = ttk.LabelFrame(self.root, text=" Camera Entry (Storage in GB) ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Qty:").grid(row=0, column=0)
        self.ent_qty = ttk.Entry(input_frame, width=8)
        self.ent_qty.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Mbps:").grid(row=0, column=2)
        self.ent_mbps = ttk.Entry(input_frame, width=8)
        self.ent_mbps.grid(row=0, column=3, padx=5)

        ttk.Label(input_frame, text="GB/Cam:").grid(row=0, column=4)
        self.ent_gb = ttk.Entry(input_frame, width=8)
        self.ent_gb.grid(row=0, column=5, padx=5)

        ttk.Button(input_frame, text="Add Camera", command=self.add_camera).grid(row=0, column=6, padx=10)
        ttk.Button(input_frame, text="Clear All", command=self.clear_cameras).grid(row=0, column=7)

        # Camera Table
        self.tree = ttk.Treeview(self.root, columns=("ID", "Qty", "Mbps", "GB", "TotalTB"), show="headings", height=5)
        self.tree.heading("ID", text="Type")
        self.tree.heading("Qty", text="Qty")
        self.tree.heading("Mbps", text="Mbps")
        self.tree.heading("GB", text="GB/Cam")
        self.tree.heading("TotalTB", text="Total TB")
        self.tree.pack(fill="x", padx=10, pady=5)

        # Tab System for Mode
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_raid = ttk.Frame(self.tabs)
        self.tab_jbod = ttk.Frame(self.tabs)
        self.tab_holis = ttk.Frame(self.tabs)

        self.tabs.add(self.tab_raid, text=" RAID Mode ")
        self.tabs.add(self.tab_jbod, text=" JBOD Mode ")
        self.tabs.add(self.tab_holis, text=" Holis Mode ")

        # RAID Tab Content
        self.raid_var = tk.IntVar(value=5)
        ttk.Label(self.tab_raid, text="Select RAID Level:").pack(pady=5)
        ttk.Radiobutton(self.tab_raid, text="RAID 5 (1 Parity)", variable=self.raid_var, value=5).pack()
        ttk.Radiobutton(self.tab_raid, text="RAID 6 (2 Parity)", variable=self.raid_var, value=6).pack()

        # Calculation Button
        ttk.Button(self.root, text="RUN OPTIMIZER", command=self.calculate).pack(pady=10)

        # Results area
        self.txt_res = tk.Text(self.root, height=18, width=85, state="disabled", font=("Consolas", 10), bg="#f4f4f4")
        self.txt_res.pack(padx=10, pady=10)

    def add_camera(self):
        try:
            q = int(self.ent_qty.get())
            m = float(self.ent_mbps.get())
            gb = float(self.ent_gb.get())
            tb_conv = (gb / 1024) # Convert GB input to TB for backend
            
            cam_id = len(self.camera_list) + 1
            self.camera_list.append({'id': cam_id, 'qty': q, 'tp': m, 'st': tb_conv, 'gb_orig': gb})
            self.tree.insert("", "end", values=(cam_id, q, m, gb, f"{q * tb_conv:.2f}"))
            
            for ent in [self.ent_qty, self.ent_mbps, self.ent_gb]: ent.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Check your inputs. Use numbers only.")

    def clear_cameras(self):
        self.camera_list = []
        for item in self.tree.get_children(): self.tree.delete(item)

    def calculate(self):
        if not self.camera_list:
            messagebox.showwarning("Warning", "Please add camera types first.")
            return

        selected_tab = self.tabs.index(self.tabs.select())
        
        if selected_tab == 0: # RAID
            hardware = [NVR(*row) for row in RAID_DATA]
            parity = self.raid_var.get()
            mode_name = f"RAID {parity}"
        elif selected_tab == 1: # JBOD
            hardware = [NVR(*row) for row in JBOD_DATA]
            parity = 0
            mode_name = "JBOD"
        else: # Holis
            hardware = [NVR(*row) for row in HOLIS_DATA]
            parity = 0
            mode_name = "Holis"

        total_c = sum(c['qty'] for c in self.camera_list)
        best_cost = float('inf')
        best_data = None

        # Optimization Search
        for n_type in hardware:
            max_n = ceil(total_c / n_type.cameras) + 1
            for q in range(1, max_n + 1):
                units = [n_type] * q
                detailed = assign_cameras_min_storage(units, self.camera_list)
                if detailed:
                    project_cost = 0
                    valid = True
                    for entry in detailed:
                        h_cost, h_cfg = get_cheapest_hdd_config(entry['cur_st'], entry['obj'].slots, parity, HDD_LIST)
                        if h_cfg:
                            entry['h_cfg'] = h_cfg
                            project_cost += entry['obj'].price + h_cost
                        else:
                            valid = False; break
                    if valid and project_cost < best_cost:
                        best_cost = project_cost
                        best_data = detailed

        self.display_results(best_cost, best_data, mode_name)

    def display_results(self, cost, data, mode):
        self.txt_res.config(state="normal")
        self.txt_res.delete("1.0", tk.END)
        if not data:
            self.txt_res.insert(tk.END, f"SYSTEM ERROR: No valid hardware found for {mode} constraints.")
        else:
            header = f"MODE: {mode} | TOTAL PROJECT COST: ${cost:,.2f}\n"
            self.txt_res.insert(tk.END, header + "="*70 + "\n")
            
            for i, entry in enumerate(data):
                n, h = entry['obj'], entry['h_cfg']
                c_breakdown = ", ".join([f"T{tid}: {qty}" for tid, qty in entry['assigned'].items()])
                
                res = f"UNIT {i+1}: {n.name} ({n.part})\n"
                res += f"  - Cameras: {c_breakdown}\n"
                res += f"  - Load: {entry['cur_st']:.2f} TB | Bandwidth: {(n.throughput - entry['rem_t']/1000):.2f} Mbps\n"
                res += f"  - Storage: {h['qty']} x {h['cap']} TB | Usable: {h['usable']:.2f} TB\n"
                res += f"  - Unit Subtotal (Hardware + HDD): ${n.price + h['cost']:,.2f}\n"
                res += "-"*50 + "\n"
                self.txt_res.insert(tk.END, res)
        self.txt_res.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    # Set a reasonable window size
    root.geometry("700x750")
    app = CCTVApp(root)
    root.mainloop()
