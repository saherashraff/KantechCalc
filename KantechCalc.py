import tkinter as tk
from tkinter import ttk, messagebox
from math import ceil
from collections import defaultdict

# ------------------------------------------------------------
# Hardware & Pricing Data
# ------------------------------------------------------------
RAID_DATA = [
    ["1U NVR", "ADVER00N0NP16G", 32, 50, 4, 3750],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.7],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.7],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000],
    ["2U 175 Ch", "ADVER00RN2K", 175, 1000, 12, 13854.2],
    ["2U Rack", "ADVER02RDK", 200, 1500, 12, 12812.5],
]

JBOD_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500],
    ["1U NVR", "ADVER00N0NP16G", 32, 100, 4, 3750],
    ["Desktop NVR", "ADVED00N0N5H", 50, 200, 2, 2291.7],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.5],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 80, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 160, 1, 770.85],
]

# Hard Drive Price List (TB, Price per Unit)
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
# Core Logic Functions
# ------------------------------------------------------------

def get_cheapest_hdd_config(required_tb, max_slots, parity_lvl, hdd_list):
    """Finds the absolute lowest price to meet TB requirement without over-filling slots."""
    best_cost = float('inf')
    best_cfg = None
    
    for cap, price in hdd_list:
        needed_data_drives = ceil(required_tb / cap)
        total_drives = needed_data_drives + parity_lvl
        
        if (parity_lvl + 1) <= total_drives <= max_slots:
            current_cost = total_drives * price
            # Priority 1: Cheapest Total Cost
            if current_cost < best_cost:
                best_cost = current_cost
                best_cfg = {'cap': cap, 'qty': total_drives, 'usable': needed_data_drives * cap, 'cost': current_cost}
            # Priority 2: If price is equal, use fewer drives
            elif current_cost == best_cost and best_cfg:
                if total_drives < best_cfg['qty']:
                    best_cfg = {'cap': cap, 'qty': total_drives, 'usable': needed_data_drives * cap, 'cost': current_cost}
    return best_cost, best_cfg

def assign_cameras_balanced(nvr_units, camera_types):
    """Distributes camera load evenly across NVRs for maximum storage efficiency."""
    nvrs = []
    for n in nvr_units:
        nvrs.append({
            'obj': n, 'rem_c': n.cameras, 'rem_t': int(n.throughput * 1000), 
            'assigned': defaultdict(int), 'cur_st': 0.0
        })
    
    sorted_types = sorted(camera_types, key=lambda x: x['st'], reverse=True)
    for c_type in sorted_types:
        for _ in range(c_type['qty']):
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
    return nvrs

# ------------------------------------------------------------
# GUI Class
# ------------------------------------------------------------

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced CCTV BOM Optimizer")
        self.camera_list = []
        self.setup_ui()

    def setup_ui(self):
        # Input Frame
        input_frame = ttk.LabelFrame(self.root, text=" Camera Configuration (Storage in GB) ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Qty:").grid(row=0, column=0)
        self.ent_qty = ttk.Entry(input_frame, width=8); self.ent_qty.grid(row=0, column=1, padx=5)
        ttk.Label(input_frame, text="Mbps:").grid(row=0, column=2)
        self.ent_mbps = ttk.Entry(input_frame, width=8); self.ent_mbps.grid(row=0, column=3, padx=5)
        ttk.Label(input_frame, text="GB/Cam:").grid(row=0, column=4)
        self.ent_gb = ttk.Entry(input_frame, width=8); self.ent_gb.grid(row=0, column=5, padx=5)

        ttk.Button(input_frame, text="Add Camera", command=self.add_camera).grid(row=0, column=6, padx=5)
        ttk.Button(input_frame, text="Reset", command=self.clear_all).grid(row=0, column=7)

        # Table
        self.tree = ttk.Treeview(self.root, columns=("ID", "Qty", "Mbps", "GB", "TotalTB"), show="headings", height=5)
        for col in ["ID", "Qty", "Mbps", "GB", "TotalTB"]: self.tree.heading(col, text=col)
        self.tree.pack(fill="x", padx=10, pady=5)

        # Tabs
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        self.tab_raid, self.tab_jbod, self.tab_holis = ttk.Frame(self.tabs), ttk.Frame(self.tabs), ttk.Frame(self.tabs)
        self.tabs.add(self.tab_raid, text=" RAID Mode "); self.tabs.add(self.tab_jbod, text=" JBOD Mode "); self.tabs.add(self.tab_holis, text=" Holis Mode ")

        self.raid_var = tk.IntVar(value=5)
        ttk.Radiobutton(self.tab_raid, text="RAID 5 (1 Parity Drive)", variable=self.raid_var, value=5).pack(pady=10)
        ttk.Radiobutton(self.tab_raid, text="RAID 6 (2 Parity Drives)", variable=self.raid_var, value=6).pack()

        # Generate Button
        ttk.Button(self.root, text="GENERATE CHEAPEST BILL OF MATERIALS", command=self.calculate).pack(pady=10)

        # Output
        self.txt_res = tk.Text(self.root, height=18, width=90, state="disabled", font=("Consolas", 10), bg="#1e1e1e", fg="#33ff33")
        self.txt_res.pack(padx=10, pady=10)

    def add_camera(self):
        try:
            q, m, gb = int(self.ent_qty.get()), float(self.ent_mbps.get()), float(self.ent_gb.get())
            tb_val = gb / 1024
            cid = len(self.camera_list) + 1
            self.camera_list.append({'id': cid, 'qty': q, 'tp': m, 'st': tb_val, 'gb_orig': gb})
            self.tree.insert("", "end", values=(cid, q, m, gb, f"{q*tb_val:.2f}"))
            for e in [self.ent_qty, self.ent_mbps, self.ent_gb]: e.delete(0, tk.END)
        except: messagebox.showerror("Error", "Please enter valid numbers.")

    def clear_all(self):
        self.camera_list = []; [self.tree.delete(i) for i in self.tree.get_children()]

    def calculate(self):
        if not self.camera_list: return
        tab_idx = self.tabs.index(self.tabs.select())
        if tab_idx == 0: hw, parity, mode = [NVR(*r) for r in RAID_DATA], self.raid_var.get(), f"RAID {self.raid_var.get()}"
        elif tab_idx == 1: hw, parity, mode = [NVR(*r) for r in JBOD_DATA], 0, "JBOD"
        else: hw, parity, mode = [NVR(*r) for r in HOLIS_DATA], 0, "Holis"

        total_c = sum(c['qty'] for c in self.camera_list)
        total_m = sum(c['qty'] * c['tp'] for c in self.camera_list)
        best_project_cost, best_project_data = float('inf'), None

        for n_model in hw:
            # Check for multiple NVRs (1 unit, 2 units, etc.)
            min_u = max(ceil(total_c / n_model.cameras), ceil(total_m / n_model.throughput))
            for q in range(min_u, min_u + 3):
                units = [n_model] * q
                result = assign_cameras_balanced(units, self.camera_list)
                if result:
                    current_cost = 0; possible = True
                    for nvr in result:
                        h_cost, h_cfg = get_cheapest_hdd_config(nvr['cur_st'], nvr['obj'].slots, parity, HDD_LIST)
                        if h_cfg:
                            nvr['h_cfg'] = h_cfg
                            current_cost += nvr['obj'].price + h_cost
                        else: possible = False; break
                    
                    if possible and current_cost < best_project_cost:
                        best_project_cost = current_cost
                        best_project_data = result

        self.display_results(best_project_cost, best_project_data, mode)

    def display_results(self, cost, data, mode):
        self.txt_res.config(state="normal"); self.txt_res.delete("1.0", tk.END)
        if not data: self.txt_res.insert(tk.END, "No valid solution found.")
        else:
            self.txt_res.insert(tk.END, f"MODE: {mode} | TOTAL PROJECT COST: ${cost:,.2f}\n" + "="*80 + "\n")
            total_hdds = 0
            for i, nvr in enumerate(data):
                obj, h = nvr['obj'], nvr['h_cfg']
                total_hdds += h['qty']
                self.txt_res.insert(tk.END, f"UNIT {i+1}: {obj.name} ({obj.part})\n")
                self.txt_res.insert(tk.END, f"  - Cameras Assigned: {sum(nvr['assigned'].values())}\n")
                self.txt_res.insert(tk.END, f"  - Usable Storage Needed: {nvr['cur_st']:.2f} TB\n")
                self.txt_res.insert(tk.END, f"  - CHEAPEST HDD BOM: {h['qty']} x {h['cap']} TB (Usable: {h['usable']:.2f} TB)\n")
                self.txt_res.insert(tk.END, f"  - Slots Utilization: {h['qty']} of {obj.slots}\n")
                self.txt_res.insert(tk.END, f"  - Subtotal: ${obj.price + h['cost']:,.2f}\n" + "-"*60 + "\n")
            self.txt_res.insert(tk.END, f"FINAL SUMMARY:\nTotal NVRs: {len(data)}\nTotal HDDs: {total_hdds}\nTotal Cost: ${cost:,.2f}")
        self.txt_res.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("750x850"); app = CCTVApp(root); root.mainloop()
