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
# Logic Functions
# ------------------------------------------------------------

def get_cheapest_hdd_config(required_tb, max_slots, parity_lvl, hdd_list):
    """Finds the cheapest HDD config, preferring fewer drives if costs are similar."""
    best_cost = float('inf')
    best_cfg = None
    
    for cap, price in hdd_list:
        data_drives = ceil(required_tb / cap)
        total_drives = data_drives + parity_lvl
        
        if (parity_lvl + 1) <= total_drives <= max_slots:
            cost = total_drives * price
            # Logic: If cheaper, take it. If same price, take the one with FEWER drives.
            if cost < best_cost or (cost == best_cost and best_cfg and total_drives < best_cfg['qty']):
                best_cost = cost
                best_cfg = {'cap': cap, 'qty': total_drives, 'usable': data_drives * cap, 'cost': cost}
    return best_cost, best_cfg

def assign_cameras_min_storage(nvr_units, camera_types):
    """Evenly distributes TB load across NVR units."""
    nvrs = []
    for n in nvr_units:
        nvrs.append({'obj': n, 'rem_c': n.cameras, 'rem_t': int(n.throughput * 1000), 
                     'assigned': defaultdict(int), 'cur_st': 0.0})
    
    sorted_types = sorted(camera_types, key=lambda x: x['st'], reverse=True)
    for c_type in sorted_types:
        rem = c_type['qty']
        while rem > 0:
            best_idx = -1
            min_st = float('inf')
            for i, n in enumerate(nvrs):
                if n['rem_c'] > 0 and n['rem_t'] >= int(c_type['tp'] * 1000):
                    if n['cur_st'] < min_st:
                        min_st = n['cur_st']
                        best_idx = i
            if best_idx == -1: return None
            nvrs[best_idx]['rem_c'] -= 1
            nvrs[best_idx]['rem_t'] -= int(c_type['tp'] * 1000)
            nvrs[best_idx]['assigned'][c_type['id']] += 1
            nvrs[best_idx]['cur_st'] += c_type['st']
            rem -= 1
    return nvrs

# ------------------------------------------------------------
# GUI Application
# ------------------------------------------------------------

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Optimizer v3.0")
        self.camera_list = []
        self.setup_ui()

    def setup_ui(self):
        # Input Frame
        input_frame = ttk.LabelFrame(self.root, text=" Camera Settings (Storage in GB) ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        labels = ["Qty:", "Mbps:", "GB/Cam:"]
        self.entries = []
        for i, text in enumerate(labels):
            ttk.Label(input_frame, text=text).grid(row=0, column=i*2)
            ent = ttk.Entry(input_frame, width=8)
            ent.grid(row=0, column=i*2+1, padx=5)
            self.entries.append(ent)

        ttk.Button(input_frame, text="Add", command=self.add_camera).grid(row=0, column=6, padx=5)
        ttk.Button(input_frame, text="Clear", command=self.clear_cameras).grid(row=0, column=7)

        # Table
        self.tree = ttk.Treeview(self.root, columns=("ID", "Qty", "Mbps", "GB", "TotalTB"), show="headings", height=5)
        for col in ["ID", "Qty", "Mbps", "GB", "TotalTB"]: self.tree.heading(col, text=col)
        self.tree.pack(fill="x", padx=10, pady=5)

        # Tabs
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        self.tab_raid = ttk.Frame(self.tabs); self.tab_jbod = ttk.Frame(self.tabs); self.tab_holis = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_raid, text=" RAID "); self.tabs.add(self.tab_jbod, text=" JBOD "); self.tabs.add(self.tab_holis, text=" HOLIS ")

        # RAID Options
        self.raid_var = tk.IntVar(value=5)
        ttk.Radiobutton(self.tab_raid, text="RAID 5", variable=self.raid_var, value=5).pack(pady=5)
        ttk.Radiobutton(self.tab_raid, text="RAID 6", variable=self.raid_var, value=6).pack()

        # Action
        ttk.Button(self.root, text="GENERATE OPTIMAL BILL OF MATERIALS", command=self.calculate).pack(pady=10)

        # Text Results
        self.txt_res = tk.Text(self.root, height=18, width=85, state="disabled", font=("Consolas", 10), bg="#2b2b2b", fg="#ffffff")
        self.txt_res.pack(padx=10, pady=10)

    def add_camera(self):
        try:
            q, m, gb = int(self.entries[0].get()), float(self.entries[1].get()), float(self.entries[2].get())
            tb = gb / 1024
            cid = len(self.camera_list) + 1
            self.camera_list.append({'id': cid, 'qty': q, 'tp': m, 'st': tb, 'gb': gb})
            self.tree.insert("", "end", values=(cid, q, m, gb, f"{q*tb:.2f}"))
            for e in self.entries: e.delete(0, tk.END)
        except: messagebox.showerror("Error", "Check numeric inputs.")

    def clear_cameras(self):
        self.camera_list = []; [self.tree.delete(i) for i in self.tree.get_children()]

    def calculate(self):
        if not self.camera_list: return
        idx = self.tabs.index(self.tabs.select())
        if idx == 0: hw, parity, mode = [NVR(*r) for r in RAID_DATA], self.raid_var.get(), f"RAID {self.raid_var.get()}"
        elif idx == 1: hw, parity, mode = [NVR(*r) for r in JBOD_DATA], 0, "JBOD"
        else: hw, parity, mode = [NVR(*r) for r in HOLIS_DATA], 0, "HOLIS"

        total_c = sum(c['qty'] for c in self.camera_list)
        total_m = sum(c['qty'] * c['tp'] for c in self.camera_list)
        best_cost, best_data = float('inf'), None

        for model in hw:
            min_u = max(ceil(total_c / model.cameras), ceil(total_m / model.throughput))
            for q in range(min_u, min_u + 3):
                detailed = assign_cameras_min_storage([model]*q, self.camera_list)
                if detailed:
                    p_cost = 0; valid = True
                    for entry in detailed:
                        h_cost, h_cfg = get_cheapest_hdd_config(entry['cur_st'], entry['obj'].slots, parity, HDD_LIST)
                        if h_cfg: entry['h_cfg'], p_cost = h_cfg, p_cost + entry['obj'].price + h_cost
                        else: valid = False; break
                    if valid and p_cost < best_cost: best_cost, best_data = p_cost, detailed

        self.display(best_cost, best_data, mode)

    def display(self, cost, data, mode):
        self.txt_res.config(state="normal"); self.txt_res.delete("1.0", tk.END)
        if not data: self.txt_res.insert(tk.END, "No valid hardware configuration found.")
        else:
            self.txt_res.insert(tk.END, f"OPTIMAL {mode} SOLUTION | TOTAL COST: ${cost:,.2f}\n" + "="*70 + "\n")
            for i, ent in enumerate(data):
                n, h = ent['obj'], ent['h_cfg']
                cam_str = ", ".join([f"T{k}:{v}" for k,v in ent['assigned'].items()])
                self.txt_res.insert(tk.END, f"UNIT {i+1}: {n.name} ({n.part})\n")
                self.txt_res.insert(tk.END, f"  - Cameras: {cam_str}\n")
                self.txt_res.insert(tk.END, f"  - Load: {ent['cur_st']:.2f} TB | Bandwidth: {(n.throughput - ent['rem_t']/1000):.2f} Mbps\n")
                self.txt_res.insert(tk.END, f"  - Drives: {h['qty']} x {h['cap']} TB | Usable: {h['usable']:.2f} TB\n")
                self.txt_res.insert(tk.END, f"  - Unit Subtotal: ${n.price + h['cost']:,.2f}\n" + "-"*50 + "\n")
        self.txt_res.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("700x780"); app = CCTVApp(root); root.mainloop()
