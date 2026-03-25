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
        data_drives = ceil(required_tb / cap) if cap > 0 else 999
        total_drives = data_drives + parity_lvl
        if parity_lvl + 1 <= total_drives <= max_slots:
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
        self.root.title("CCTV Storage & Hardware Optimizer")
        self.camera_list = []
        self.setup_ui()

    def setup_ui(self):
        # Input Frame
        input_frame = ttk.LabelFrame(self.root, text=" Add Camera Types ", padding=10)
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(input_frame, text="Quantity:").grid(row=0, column=0)
        self.ent_qty = ttk.Entry(input_frame, width=10)
        self.ent_qty.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Mbps:").grid(row=0, column=2)
        self.ent_mbps = ttk.Entry(input_frame, width=10)
        self.ent_mbps.grid(row=0, column=3, padx=5)

        ttk.Label(input_frame, text="TB/Cam:").grid(row=0, column=4)
        self.ent_tb = ttk.Entry(input_frame, width=10)
        self.ent_tb.grid(row=0, column=5, padx=5)

        ttk.Button(input_frame, text="Add Type", command=self.add_camera).grid(row=0, column=6, padx=10)

        # Listbox for cameras
        self.tree = ttk.Treeview(self.root, columns=("Qty", "Mbps", "TB"), show="headings", height=5)
        self.tree.heading("Qty", text="Quantity")
        self.tree.heading("Mbps", text="Throughput (Mbps)")
        self.tree.heading("TB", text="Storage (TB)")
        self.tree.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # RAID Settings
        settings_frame = ttk.Frame(self.root)
        settings_frame.grid(row=2, column=0, pady=5)
        ttk.Label(settings_frame, text="RAID Level:").pack(side="left")
        self.raid_var = tk.IntVar(value=5)
        ttk.Radiobutton(settings_frame, text="RAID 5", variable=self.raid_var, value=5).pack(side="left", padx=5)
        ttk.Radiobutton(settings_frame, text="RAID 6", variable=self.raid_var, value=6).pack(side="left", padx=5)

        ttk.Button(self.root, text="CALCULATE OPTIMAL SOLUTION", command=self.calculate).grid(row=3, column=0, pady=10)

        # Results Area
        self.txt_res = tk.Text(self.root, height=15, width=80, state="disabled", font=("Consolas", 10))
        self.txt_res.grid(row=4, column=0, padx=10, pady=10)

    def add_camera(self):
        try:
            q, m, t = int(self.ent_qty.get()), float(self.ent_mbps.get()), float(self.ent_tb.get())
            cam_id = len(self.camera_list) + 1
            self.camera_list.append({'id': cam_id, 'qty': q, 'tp': m, 'st': t})
            self.tree.insert("", "end", values=(q, m, t))
            for ent in [self.ent_qty, self.ent_mbps, self.ent_tb]: ent.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values")

    def calculate(self):
        if not self.camera_list:
            messagebox.showwarning("Warning", "Add at least one camera type.")
            return

        nvrs = [NVR(*row) for row in RAID_DATA]
        raid_lvl = self.raid_var.get()
        parity = 1 if raid_lvl == 5 else 2
        
        # We simplify the search here for the GUI to keep it responsive
        total_c = sum(c['qty'] for c in self.camera_types_raw())
        nvr_sorted = sorted(nvrs, key=lambda x: x.price)
        
        # Finding best combo (Logic from previous step)
        best_cost = float('inf')
        best_data = None

        # Simplified search: Try increasing counts of each NVR type
        for n_type in nvr_sorted:
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

        self.display_results(best_cost, best_data, raid_lvl)

    def camera_types_raw(self):
        return self.camera_list

    def display_results(self, cost, data, raid):
        self.txt_res.config(state="normal")
        self.txt_res.delete("1.0", tk.END)
        if not data:
            self.txt_res.insert(tk.END, "No valid hardware configuration found.")
        else:
            res_str = f"OPTIMAL TOTAL COST: ${cost:,.2f}\n" + "="*50 + "\n"
            for i, entry in enumerate(data):
                n, h = entry['obj'], entry['h_cfg']
                res_str += f"NVR {i+1}: {n.name} ({n.part})\n"
                res_str += f"  - Load: {entry['cur_st']:.2f} TB | Throughput: {(n.throughput - entry['rem_t']/1000):.2f} Mbps\n"
                res_str += f"  - HDDs: {h['qty']} x {h['cap']} TB (RAID {raid}) | Usable: {h['usable']:.2f} TB\n"
                res_str += f"  - Unit + Storage Cost: ${n.price + h['cost']:,.2f}\n" + "-"*30 + "\n"
            self.txt_res.insert(tk.END, res_str)
        self.txt_res.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = CCTVApp(root)
    root.mainloop()
