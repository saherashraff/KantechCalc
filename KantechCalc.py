import tkinter as tk
from tkinter import ttk, messagebox
import math

# ------------------------------------------------------------
# 1. HARDWARE DATA
# ------------------------------------------------------------
RAID_DATA = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U Rack 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20],
    ["2U Rack 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

JBOD_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
    ["1U RAID (JBOD)", "ADVER00N0NP16G", 32, 100, 4, 3750.00],
    ["2U 200 Ch (JBOD)", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 160, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 320, 1, 770.85],
]

DEFAULT_HDD_PRICES = {
    1: 93.75, 2: 122.95, 4: 218.75, 6: 281.25, 8: 395.85, 
    10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1, 22: 1145.85, 
    24: 1447.95, 26: 1700.00
}

# ------------------------------------------------------------
# 2. UPDATED LOGIC FUNCTIONS
# ------------------------------------------------------------
def get_best_hdd(required_tb, slots, parity, price_dict):
    """
    Enforces a minimum of 2 drives for any RAID, then adds parity.
    RAID 5: min 2 data + 1 parity = 3 drives
    RAID 6: min 2 data + 2 parity = 4 drives
    """
    if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "cost": 0}
    best_h_cost = float('inf')
    best_h_cfg = None
    valid_prices = {k: v for k, v in price_dict.items() if v > 0}
    
    for cap, price in sorted(valid_prices.items()):
        # Step 1: Calculate drives needed for data
        data_drives = math.ceil(required_tb / cap)
        
        # Step 2: Enforce minimum of 2 drives for data IF using RAID
        if parity > 0:
            data_drives = max(data_drives, 2)
            
        # Step 3: Add parity drives
        total_drives = data_drives + parity
        
        # Step 4: Check if total fits in the hardware slots
        if total_drives <= slots:
            total_price = total_drives * price
            if total_price < best_h_cost:
                best_h_cost = total_price
                best_h_cfg = {"qty": total_drives, "cap": cap, "cost": total_price}
                
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER CALCULATOR - STRICT RAID MINIMUMS")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Camera Input ")
        self.nb.add(self.t2, text=" 2. Per-NVR Solution ")
        self.nb.add(self.t3, text=" 3. HDD Price List ")

        # --- TAB 1 ---
        f = ttk.Frame(self.t1, padding=10); f.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f, width=10); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        
        btn_f = ttk.Frame(self.t1); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add/Update Row", command=self.save_camera).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Clear All", command=self.clear_all_cams).pack(side="left", padx=5)

        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=12)
        for c, h in zip(self.tree["columns"], ["Camera Type","Qty","Mbps","GB/Cam"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 2 ---
        f_b = ttk.Frame(self.t2, padding=15); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        mode_cb = ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly")
        mode_cb.pack(side="left", padx=5)
        ttk.Button(f_b, text="GENERATE INDIVIDUAL REPORTS", command=self.find_cheapest).pack(side="left", padx=5)
        
        self.res_txt = tk.Text(self.t2, bg="#0d0d0d", fg="#33ff33", font=("Consolas", 10))
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 3 ---
        pf = ttk.Frame(self.t3, padding=20); pf.pack()
        self.p_ents = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{cap}TB Price: $").grid(row=r, column=c*2, sticky="e", pady=2)
            e = ttk.Entry(pf, width=12); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1, padx=10, pady=2)
            self.p_ents[cap] = e
        ttk.Button(self.t3, text="SAVE NEW PRICES", command=self.save_prices).pack()

    def save_prices(self):
        for cap, entry in self.p_ents.items(): self.hdd_prices[cap] = float(entry.get())
        messagebox.showinfo("Success", "Price database updated.")

    def save_camera(self):
        try:
            d = (self.ents["Name"].get(), int(self.ents["Qty"].get()), float(self.ents["Mbps"].get()), float(self.ents["GB"].get()))
            self.tree.insert("", "end", values=d)
        except: pass

    def clear_all_cams(self):
        for i in self.tree.get_children(): self.tree.delete(i)

    def find_cheapest(self):
        cams_data = []
        t_mbps, t_tb, t_cams = 0, 0, 0
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            qty = int(v[1]); mbps = float(v[2]); gb = float(v[3])
            cams_data.append({"name": v[0], "qty": qty, "mbps": mbps, "tb": gb/1024})
            t_cams += qty; t_mbps += (mbps*qty); t_tb += ((gb/1024)*qty)
        
        if t_cams == 0: return

        mode = self.mode_var.get()
        if mode == "Holis": hw_list, parity = HOLIS_DATA, 0
        elif mode == "RAID 5": hw_list, parity = RAID_DATA, 1
        elif mode == "RAID 6": hw_list, parity = RAID_DATA, 2
        else: hw_list, parity = JBOD_DATA, 0
        
        final_list = []
        for m in hw_list:
            n_qty = max(math.ceil(t_cams / m[2]), math.ceil(t_mbps / m[3]))
            h_cost, h_cfg = get_best_hdd(t_tb / n_qty, m[4], parity, self.hdd_prices)
            while not h_cfg and n_qty < 50: 
                n_qty += 1
                h_cost, h_cfg = get_best_hdd(t_tb / n_qty, m[4], parity, self.hdd_prices)
            if h_cfg:
                total_cost = (m[5] + h_cost) * n_qty
                final_list.append({"total": total_cost, "m": m, "n_qty": n_qty, "h": h_cfg})

        final_list.sort(key=lambda x: x['total'])
        self.res_txt.delete("1.0", tk.END)
        if not final_list: return
        best = final_list[0]

        self.res_txt.insert(tk.END, f"SYSTEM REPORT ({mode})\n")
        self.res_txt.insert(tk.END, f"Total Solution Cost: ${best['total']:,.2f}\n")
        self.res_txt.insert(tk.END, f"Total Hardware: {best['n_qty']} Unit(s)\n")
        self.res_txt.insert(tk.END, "="*55 + "\n\n")

        # Breakdown per individual NVR
        for unit_id in range(1, best['n_qty'] + 1):
            self.res_txt.insert(tk.END, f"--- UNIT {unit_id} SPECIFICATIONS ---\n")
            self.res_txt.insert(tk.END, f"Model:   {best['m'][1]} ({best['m'][0]})\n")
            self.res_txt.insert(tk.END, f"Storage: {best['h']['qty']} x {best['h']['cap']}TB Drives\n")
            
            self.res_txt.insert(tk.END, "Camera List:\n")
            u_mbps, u_tb = 0, 0
            for cam in cams_data:
                c_per_nvr = cam['qty'] / best['n_qty']
                if c_per_nvr > 0:
                    self.res_txt.insert(tk.END, f"  - {cam['name']}: {c_per_nvr:.1f} cameras\n")
                    u_mbps += (cam['mbps'] * c_per_nvr)
                    u_tb += (cam['tb'] * c_per_nvr)
            
            self.res_txt.insert(tk.END, f"\nUnit Load: {u_mbps:.1f} Mbps | {u_tb:.2f} TB\n")
            self.res_txt.insert(tk.END, "-"*55 + "\n")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("900x850"); app = CCTVApp(r); r.mainloop()
