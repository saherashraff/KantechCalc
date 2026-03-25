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

# Hard Drive Price List (TB, Price)
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
# Optimization Logic
# ------------------------------------------------------------

def get_cheapest_hdd_config(required_tb, max_slots, parity_lvl, hdd_list):
    """
    Exhaustively searches for the lowest price combination.
    Does not care about drive count, only the $ total.
    """
    best_cost = float('inf')
    best_cfg = None
    
    for cap, price in hdd_list:
        # Calculate minimum drives of THIS size to cover TB + RAID overhead
        needed_data_drives = ceil(required_tb / cap)
        total_drives = needed_data_drives + parity_lvl
        
        # Validation: Must fit in NVR slots and meet RAID requirements
        if (parity_lvl + 1) <= total_drives <= max_slots:
            current_total_cost = total_drives * price
            
            # If this is the cheapest we've found so far, save it
            if current_total_cost < best_cost:
                best_cost = current_total_cost
                best_cfg = {
                    'cap': cap, 
                    'qty': total_drives, 
                    'usable': needed_data_drives * cap, 
                    'cost': current_total_cost
                }
    return best_cost, best_cfg

def assign_cameras_balanced(nvr_units, camera_types):
    """Distributes cameras to keep storage load balanced across NVRs."""
    nvrs = []
    for n in nvr_units:
        nvrs.append({
            'obj': n, 'rem_c': n.cameras, 'rem_t': int(n.throughput * 1000), 
            'assigned': defaultdict(int), 'cur_st': 0.0
        })
    
    # Sort cameras by Storage (TB) descending
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
# GUI
# ------------------------------------------------------------

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Absolute Cost Optimizer")
        self.camera_list = []
        self.setup_ui()

    def setup_ui(self):
        # Input Frame
        input_frame = ttk.LabelFrame(self.root, text=" Input Camera Details (GB) ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Qty:").grid(row=0, column=0)
        self.e_qty = ttk.Entry(input_frame, width=7); self.e_qty.grid(row=0, column=1)
        ttk.Label(input_frame, text="Mbps:").grid(row=0, column=2)
        self.e_mbps = ttk.Entry(input_frame, width=7); self.e_mbps.grid(row=0, column=3)
        ttk.Label(input_frame, text="GB:").grid(row=0, column=4)
        self.e_gb = ttk.Entry(input_frame, width=7); self.e_gb.grid(row=0, column=5)

        ttk.Button(input_frame, text="Add", command=self.add_cam).grid(row=0, column=6, padx=5)
        ttk.Button(input_frame, text="Reset", command=self.reset).grid(row=0, column=7)

        self.tree = ttk.Treeview(self.root, columns=("Q","M","GB","TotalTB"), show="headings", height=4)
        for c in ["Q","M","GB","TotalTB"]: self.tree.heading(c, text=c)
        self.tree.pack(fill="x", padx=10)

        # Tabs
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        self.t_raid, self.t_jbod, self.t_holis = ttk.Frame(self.tabs), ttk.Frame(self.tabs), ttk.Frame(self.tabs)
        self.tabs.add(self.t_raid, text="RAID"); self.tabs.add(self.t_jbod, text="JBOD"); self.tabs.add(self.t_holis, text="Holis")

        self.r_var = tk.IntVar(value=5)
        ttk.Radiobutton(self.t_raid, text="RAID 5", variable=self.r_var, value=5).pack(pady=5)
        ttk.Radiobutton(self.t_raid, text="RAID 6", variable=self.r_var, value=6).pack()

        ttk.Button(self.root, text="GENERATE CHEAPEST BOM", command=self.calculate).pack(pady=10)

        self.out = tk.Text(self.root, height=18, width=85, state="disabled", font=("Consolas", 10), bg="#0f0f0f", fg="#33ff33")
        self.out.pack(padx=10, pady=10)

    def add_cam(self):
        try:
            q, m, g = int(self.e_qty.get()), float(self.e_mbps.get()), float(self.e_gb.get())
            tb = (g / 1024)
            self.camera_list.append({'id': len(self.camera_list)+1, 'qty': q, 'tp': m, 'st': tb, 'gb': g})
            self.tree.insert("", "end", values=(q, m, g, f"{q*tb:.2f}"))
        except: pass

    def reset(self):
        self.camera_list = []; [self.tree.delete(i) for i in self.tree.get_children()]

    def calculate(self):
        if not self.camera_list: return
        idx = self.tabs.index(self.tabs.select())
        if idx == 0: hw, parity, mode = [NVR(*r) for r in RAID_DATA], self.r_var.get(), f"RAID {self.r_var.get()}"
        elif idx == 1: hw, parity, mode = [NVR(*r) for r in JBOD_DATA], 0, "JBOD"
        else: hw, parity, mode = [NVR(*r) for r in HOLIS_DATA], 0, "Holis"

        total_c = sum(c['qty'] for c in self.camera_list)
        total_m = sum(c['qty'] * c['tp'] for c in self.camera_list)
        best_p_cost, best_p_data = float('inf'), None

        for model in hw:
            # Check for multiple NVRs if needed
            min_u = max(ceil(total_c / model.cameras), ceil(total_m / model.throughput))
            for q in range(min_u, min_u + 2):
                result = assign_cameras_balanced([model]*q, self.camera_list)
                if result:
                    current_p_cost = 0; possible = True
                    for nvr_entry in result:
                        h_cost, h_cfg = get_cheapest_hdd_config(nvr_entry['cur_st'], nvr_entry['obj'].slots, parity, HDD_LIST)
                        if h_cfg:
                            nvr_entry['h_cfg'] = h_cfg
                            current_p_cost += nvr_entry['obj'].price + h_cost
                        else: possible = False; break
                    
                    if possible and current_p_cost < best_p_cost:
                        best_p_cost, best_p_data = current_p_cost, result

        self.show(best_p_cost, best_p_data, mode)

    def show(self, cost, data, mode):
        self.out.config(state="normal"); self.out.delete("1.0", tk.END)
        if not data: self.out.insert(tk.END, "No valid hardware configuration found.")
        else:
            self.out.insert(tk.END, f"MODE: {mode} | TOTAL ESTIMATED COST: ${cost:,.2f}\n" + "="*70 + "\n")
            total_drives_count = 0
            for i, ent in enumerate(data):
                n, h = ent['obj'], ent['h_cfg']
                total_drives_count += h['qty']
                self.out.insert(tk.END, f"UNIT {i+1}: {n.name} ({n.part})\n")
                self.out.insert(tk.END, f"  - Load: {ent['cur_st']:.2f} TB Needed\n")
                self.out.insert(tk.END, f"  - Drives: {h['qty']} x {h['cap']} TB | Total Usable: {h['usable']:.2f} TB\n")
                self.out.insert(tk.END, f"  - Slots Used: {h['qty']} of {n.slots}\n")
                self.out.insert(tk.END, f"  - Cost: ${n.price + h['cost']:,.2f}\n" + "-"*50 + "\n")
            self.out.insert(tk.END, f"\nSUMMARY: Total Drives in Project: {total_drives_count}")
        self.out.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("700x820"); app = CCTVApp(root); root.mainloop()
