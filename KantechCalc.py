def run_logic(self, auto=True):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": str(v[0]), "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        
        if not cams: 
            messagebox.showwarning("Empty", "Please add cameras first.")
            return

        t_c, t_m, t_t = sum(c['qty'] for c in cams), sum(c['qty']*c['mbps'] for c in cams), sum(c['qty']*c['tb'] for c in cams)
        best_cost, best_cfg = float('inf'), None

        # Gather active units for both modes
        active_units = []
        if auto:
            mode = self.mode_var.get()
            hw_pool = RAID_DATA + (JBOD_ONLY_DATA if mode == "JBOD" else []) + (HOLIS_DATA if mode == "Holis" else [])
            # Auto mode evaluates pairs from the pool
            # (Keeping your original nested loop logic for Auto)
            # ... [Auto logic remains as per your original script] ...
        else:
            # --- ENHANCED MANUAL RATIO SPLIT ---
            for slot in self.manual_slots:
                name = slot['nvr'].get()
                if name != "None":
                    hw = [m for m in ALL_MODELS if m[1] == name][0]
                    parity = 1 if slot['mode'].get() == "RAID 5" else 2 if slot['mode'].get() == "RAID 6" else 0
                    active_units.append({"hw": hw, "mode": slot['mode'].get(), "parity": parity})
            
            num_u = len(active_units)
            if num_u == 1:
                # Single Unit Optimization
                u = active_units[0]
                if t_c <= u['hw'][2] and t_m <= u['hw'][3]:
                    h_cost, h_data = get_best_hdd(t_t, u['hw'][4], u['parity'], self.hdd_prices)
                    if h_data:
                        best_cfg = {"total": u['hw'][5] + h_cost, "units": [{"m": u['hw'], "c": t_c, "mb": t_m, "tb": t_t, "h": h_data, "mode": u['mode']}]}
            
            elif num_u >= 2:
                # Multi-Unit Ratio Optimization (Brute force best split)
                # We test different distributions to find the cheapest HDD + Hardware combo
                for c_a in range(1, t_c):
                    c_remaining = t_c - c_a
                    
                    # Split logic for first unit vs the rest
                    ratio_a = c_a / t_c
                    ma, ta = t_m * ratio_a, t_t * ratio_a
                    
                    u_a = active_units[0]
                    if c_a > u_a['hw'][2] or ma > u_a['hw'][3]: continue
                    ca, ha = get_best_hdd(ta, u_a['hw'][4], u_a['parity'], self.hdd_prices)
                    if not ha: continue

                    # Evaluate remaining load on subsequent units
                    # For simplicity in 3 or 4 units, we split the remainder equally 
                    # but check for validity and cost
                    rem_units = active_units[1:]
                    sub_cfg = []
                    sub_total_h_cost = 0
                    valid_split = True
                    
                    for i, u_rem in enumerate(rem_units):
                        # Distribute remainder
                        c_u = c_remaining // len(rem_units) + (1 if i < (c_remaining % len(rem_units)) else 0)
                        if c_u == 0: continue
                        
                        ratio_u = c_u / t_c
                        mu, tu = t_m * ratio_u, t_t * ratio_u
                        
                        if c_u > u_rem['hw'][2] or mu > u_rem['hw'][3]:
                            valid_split = False; break
                        
                        cu_cost, hu_data = get_best_hdd(tu, u_rem['hw'][4], u_rem['parity'], self.hdd_prices)
                        if not hu_data:
                            valid_split = False; break
                        
                        sub_total_h_cost += cu_cost
                        sub_cfg.append({"m": u_rem['hw'], "c": c_u, "mb": mu, "tb": tu, "h": hu_data, "mode": u_rem['mode']})
                    
                    if valid_split:
                        total_cost = u_a['hw'][5] + ca + sum(x['m'][5] for x in sub_cfg) + sub_total_h_cost
                        if total_cost < best_cost:
                            best_cost = total_cost
                            best_cfg = {"total": total_cost, "units": [{"m": u_a, "c": c_a, "mb": ma, "tb": ta, "h": ha, "mode": u_a['mode']}] + sub_cfg}

        # --- RENDER RESULTS ---
        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg:
            txt.insert(tk.END, self.generate_report(best_cfg, cams, t_c, t_m, t_t, "AUTO" if auto else "SMART MANUAL"))
        else:
            txt.insert(tk.END, "ERROR: No valid configuration found. The requirements exceed the physical capacity of these NVRs.")
