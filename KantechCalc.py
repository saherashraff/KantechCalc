def run_logic(self, auto):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": v[0], "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        if not cams: return
        
        best_cfg, best_total_cost = None, float('inf')

        if auto:
            mode = self.mode_var.get()
            parity = 1 if mode == "RAID 5" else 2 if mode == "RAID 6" else 0
            search_list = [n for n in self.nvr_list if n[6] == "RAID"] if parity > 0 else self.nvr_list

            for num_units in range(1, 3):
                for combo in itertools.combinations_with_replacement(search_list, num_units):
                    splits = [1.0] if num_units == 1 else [x/100.0 for x in range(1, 100)]
                    for r1 in splits:
                        u_list, cur_cams = [], [dict(c) for c in cams]
                        ratios = [r1, 1.0-r1] if num_units == 2 else [1.0]
                        valid = True
                        for i, ratio in enumerate(ratios):
                            u_brk, u_mb, u_tb, u_c = {}, 0, 0, 0
                            for c in cur_cams:
                                take = math.floor(c['qty']*ratio) if i == 0 and num_units > 1 else c['qty']
                                u_brk[c['name']] = take; u_mb += take*c['mbps']; u_tb += take*c['tb']; u_c += take
                                c['qty'] -= take
                            hc, hd = get_best_hdd(u_tb, combo[i][4], parity, self.hdd_prices)
                            if hd and u_c <= combo[i][2] and u_mb <= combo[i][3]:
                                u_list.append({"m": combo[i], "c_total": u_c, "cam_breakdown": u_brk, "mb": u_mb, "tb": u_tb, "h": hd, "mode": mode})
                            else: valid = False; break
                        if valid:
                            total = sum(u['m'][5] + u['h']['cost'] for u in u_list)
                            if total < best_total_cost: best_total_cost, best_cfg = total, {"total": total, "units": u_list}
        else:
            # --- FIXED MANUAL MODE (BRUTE FORCE 1% ACROSS USER SELECTION) ---
            active_hw = []
            for nv, mv, cb in self.manual_slots:
                if nv.get() != "None":
                    hw = next(n for n in self.nvr_list if n[1] == nv.get())
                    parity = 1 if mv.get() == "RAID 5" else 2 if mv.get() == "RAID 6" else 0
                    active_hw.append({"m": hw, "mode": mv.get(), "p": parity})
            
            if not active_hw: return

            num = len(active_hw)
            # If 1 NVR, 100% load. If 2 NVRs, check all 1% - 99% distributions
            splits = [1.0] if num == 1 else [x/100.0 for x in range(1, 100)]
            
            for r1 in splits:
                u_list, cur_cams = [], [dict(c) for c in cams]
                ratios = [r1, 1.0-r1] if num == 2 else [1.0/num]*num # Basic support for 3+ split
                valid = True
                
                for i, ratio in enumerate(ratios):
                    u_brk, u_mb, u_tb, u_c = {}, 0, 0, 0
                    for c in cur_cams:
                        # Logic: NVR A gets the ratio, NVR B (the last one) gets the remainder
                        take = math.floor(c['qty']*ratio) if i < num-1 else c['qty']
                        u_brk[c['name']] = take; u_mb += take*c['mbps']; u_tb += take*c['tb']; u_c += take
                        c['qty'] -= take
                    
                    hc, hd = get_best_hdd(u_tb, active_hw[i]['m'][4], active_hw[i]['p'], self.hdd_prices)
                    # Check if the split actually fits on the hardware you picked
                    if hd and u_c <= active_hw[i]['m'][2] and u_mb <= active_hw[i]['m'][3]:
                        u_list.append({"m": active_hw[i]['m'], "c_total": u_c, "cam_breakdown": u_brk, "mb": u_mb, "tb": u_tb, "h": hd, "mode": active_hw[i]['mode']})
                    else:
                        valid = False
                        break
                
                if valid:
                    total = sum(u['m'][5] + u['h']['cost'] for u in u_list)
                    # For manual mode, we find the "Best Split" (lowest price) for the NVRs you chose
                    if total < best_total_cost:
                        best_total_cost = total
                        best_cfg = {"total": total, "units": u_list}

        # Update text display
        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg:
            txt.insert("1.0", self.generate_detailed_report(best_cfg, "AUTO" if auto else "MANUAL"))
        else:
            txt.insert("1.0", "ERROR: NO VALID SPLIT FOUND\nThe cameras are too heavy for the NVRs you selected.\nTry choosing units with higher Mbps or Channel counts.")
