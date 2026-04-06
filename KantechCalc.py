"""
Access Control System Calculator - Kantech & SWH/GSTAR
Modern GUI — fully rebuilt from original bytecode analysis
All business logic preserved exactly as in the original.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import json
import os

# ─── THEME ────────────────────────────────────────────────────────────────────
C = {
    'bg':           '#0f1117',
    'sidebar':      '#161b27',
    'card':         '#1c2133',
    'card2':        '#212840',
    'surface':      '#29304a',
    'border':       '#2e3650',
    'accent':       '#4a7fe0',
    'accent_h':     '#6595ed',
    'teal':         '#2dd4bf',
    'green':        '#4ade80',
    'orange':       '#fb923c',
    'red':          '#f87171',
    'txt':          '#e2e8f0',
    'txt2':         '#94a3b8',
    'txt3':         '#4a5568',
    'white':        '#ffffff',
}

F = {
    'h1':    ('Segoe UI', 18, 'bold'),
    'h2':    ('Segoe UI', 13, 'bold'),
    'h3':    ('Segoe UI', 11, 'bold'),
    'body':  ('Segoe UI', 10),
    'small': ('Segoe UI', 9),
    'mono':  ('Consolas', 10),
}

# ─── DATA MODELS ──────────────────────────────────────────────────────────────

@dataclass
class DCDevice:
    """Represents devices on a single DC line"""
    dc_number: int = 0
    smart_card: int = 0
    smart_card_reader: int = 0
    fingerprint: int = 0
    door_sensor: int = 0
    magnetic_lock: int = 0
    electric_lock: int = 0
    rex_button: int = 0
    push_button: int = 0
    break_glass: int = 0
    buzzer: int = 0
    double_door_lock: int = 0
    ddl_sensors: int = 0
    unmonitored_single_magnetic_lock: int = 0
    unmonitored_double_magnetic_lock: int = 0

    def calculate_totals(self):
        """Calculate readers, inputs, outputs for this DC line"""
        readers = self.smart_card + self.fingerprint
        inputs = (self.door_sensor + self.rex_button + self.push_button +
                  self.break_glass + self.ddl_sensors)
        outputs = (self.magnetic_lock + self.electric_lock + self.double_door_lock +
                   self.unmonitored_single_magnetic_lock +
                   self.unmonitored_double_magnetic_lock + self.buzzer)
        return {
            'readers':            readers,
            'inputs':             inputs,
            'outputs':            outputs,
            'smart_cards':        self.smart_card,
            'smart_card_readers': self.smart_card_reader,
            'fingerprints':       self.fingerprint,
        }

    def add_configuration(self, other_config):
        """Add another configuration to this DC line"""
        self.smart_card                      += other_config.smart_card
        self.smart_card_reader               += other_config.smart_card_reader
        self.fingerprint                     += other_config.fingerprint
        self.door_sensor                     += other_config.door_sensor
        self.magnetic_lock                   += other_config.magnetic_lock
        self.electric_lock                   += other_config.electric_lock
        self.rex_button                      += other_config.rex_button
        self.push_button                     += other_config.push_button
        self.break_glass                     += other_config.break_glass
        self.buzzer                          += other_config.buzzer
        self.double_door_lock                += other_config.double_door_lock
        self.ddl_sensors                     += other_config.ddl_sensors
        self.unmonitored_single_magnetic_lock  += other_config.unmonitored_single_magnetic_lock
        self.unmonitored_double_magnetic_lock  += other_config.unmonitored_double_magnetic_lock


@dataclass
class AccessDoorType:
    """Represents an Access Door Type configuration"""
    type_id: int = 0
    name: str = ""

    def __post_init__(self):
        self.config = DCDevice()

    def update_config(self, **kwargs):
        """Update the configuration of this door type"""
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)

    def get_totals(self):
        """Get totals for this door type"""
        return self.config.calculate_totals()

    def __str__(self):
        t = self.get_totals()
        return (f"Door Type {self.type_id} ({self.name}): "
                f"{t['readers']} readers, {t['inputs']} inputs, {t['outputs']} outputs")


@dataclass
class GSTARController:
    """GSTAR controller information from SWH Access.xlsx"""
    name: str = ""
    readers: int = 0
    inputs: int = 0
    outputs: int = 0
    price: float = 0
    number_of_acm: int = 0

    def can_handle_readers(self, required_readers):
        """Check if this controller can handle the reader requirements"""
        return self.readers >= required_readers


# ─── CALCULATION ENGINE ───────────────────────────────────────────────────────

class SWHControllerCalculator:
    """Calculator for SWH GSTAR controllers (one controller per DC line)"""

    def __init__(self):
        self.gstar_controllers = [
            GSTARController('GSTAR004 (4 readers)',   4,   8,  0, 1395, 0),
            GSTARController('GSTAR004 (8 readers)',   8,  16, 12, 2123, 0),
            GSTARController('GSTAR008',              24,  48, 24, 3125, 1),
            GSTARController('GSTAR016',              48,  96, 48, 4166, 2),
            GSTARController('GSTAR016 (24 readers)', 72, 144, 72, 5166, 3),
            GSTARController('GSTAR016 (32 readers)', 96, 192, 96, 6166, 4),
        ]
        self.swh_licenses = [
            {'name': 'CC9000-SL',  'max_readers': 12,   'cost': 0},
            {'name': 'CC9000-SM',  'max_readers': 32,   'cost': 0},
            {'name': 'CC9000-SN',  'max_readers': 64,   'cost': 0},
            {'name': 'CC9000-SP',  'max_readers': 128,  'cost': 0},
            {'name': 'CC9000-SQ',  'max_readers': 256,  'cost': 0},
            {'name': 'CC9000-SR',  'max_readers': 512,  'cost': 0},
            {'name': 'CC9000-SRP', 'max_readers': 1000, 'cost': 0},
            {'name': 'CC9000-SS',  'max_readers': 2500, 'cost': 0},
            {'name': 'CC9000-SSP', 'max_readers': 3500, 'cost': 0},
            {'name': 'CC9000-ST',  'max_readers': 5000, 'cost': 0},
        ]
        self.swh_expansion_modules = [
            {'name': 'AS0073-000', 'inputs': 8,  'outputs': 0, 'cost': 333},
            {'name': 'AS0074-000', 'inputs': 0,  'outputs': 8, 'cost': 395},
        ]

    def select_controller_for_readers(self, required_readers):
        """Select the cheapest GSTAR controller that meets or exceeds reader requirements"""
        suitable_controllers = [c for c in self.gstar_controllers
                                if c.can_handle_readers(required_readers)]
        if not suitable_controllers:
            return None
        suitable_controllers.sort(key=lambda c: c.price)
        return suitable_controllers[0]

    def calculate_expansion_for_swh(self, dc_inputs, dc_outputs, controller_inputs, controller_outputs):
        """Calculate SWH expansion modules needed for a DC line"""
        input_shortage  = max(0, dc_inputs  - controller_inputs)
        output_shortage = max(0, dc_outputs - controller_outputs)
        result = ''
        result += '\nI/O Analysis:\n'
        result += f'  Required: {dc_inputs} inputs, {dc_outputs} outputs\n'
        result += f'  Controller provides: {controller_inputs} inputs, {controller_outputs} outputs\n'
        result += f'  Shortage: {input_shortage} inputs, {output_shortage} outputs\n'

        if input_shortage <= 0 and output_shortage <= 0:
            result += '  ✅ No expansion modules needed\n'
            return {'modules': [], 'cost': 0, 'input_modules': 0,
                    'output_modules': 0, 'result': result}

        expansion_modules = []
        expansion_cost    = 0
        input_modules     = 0
        output_modules    = 0

        if input_shortage > 0:
            as0073_needed = int(np.ceil(input_shortage / 8))
            expansion_modules.append(f'AS0073-000 (x{as0073_needed})')
            expansion_cost += 333 * as0073_needed
            input_modules   = as0073_needed

        if output_shortage > 0:
            as0074_needed = int(np.ceil(output_shortage / 8))
            expansion_modules.append(f'AS0074-000 (x{as0074_needed})')
            expansion_cost += 395 * as0074_needed
            output_modules  = as0074_needed

        result += f'  Expansion solution: {expansion_modules}\n'
        result += f'  Expansion cost: ${expansion_cost}\n'
        return {'modules': expansion_modules, 'cost': expansion_cost,
                'input_modules': input_modules, 'output_modules': output_modules,
                'result': result}


# ─── KANTECH CONTROLLER SELECTION ─────────────────────────────────────────────

class KantechCalculator:
    """Kantech controller selection and expansion logic"""

    def __init__(self):
        self.controllers = {
            'kt-1':   {'price': 450,  'reader_slots': 1, 'inputs': 4,  'outputs': 2},
            'kt-2':   {'price': 750,  'reader_slots': 2, 'inputs': 8,  'outputs': 2},
            'kt-400': {'price': 1400, 'reader_slots': 4, 'inputs': 16, 'outputs': 4},
        }
        self.expansion_modules = [
            {'name': 'inout16 (16/0)', 'inputs': 16, 'outputs':  0, 'cost': 447},
            {'name': 'inout16 (12/4)', 'inputs': 12, 'outputs':  4, 'cost': 447},
            {'name': 'inout16 (8/8)',  'inputs':  8, 'outputs':  8, 'cost': 447},
            {'name': 'inout16 (4/12)', 'inputs':  4, 'outputs': 12, 'cost': 447},
            {'name': 'inout16 (0/16)', 'inputs':  0, 'outputs': 16, 'cost': 447},
            {'name': 'in16',           'inputs': 16, 'outputs':  0, 'cost': 470},
        ]

    def select_controllers_for_dc(self, dc_requirements):
        """Select controllers for a SINGLE DC line with SMART CARD READER support"""
        total_normal_readers = dc_requirements['smart_cards'] + dc_requirements['fingerprints']
        total_smart_readers  = dc_requirements['smart_card_readers']
        if total_smart_readers > 0:
            return self.select_controllers_with_smart_readers(total_normal_readers, total_smart_readers)
        return self.select_controllers_no_smart_readers(total_normal_readers)

    def select_controllers_no_smart_readers(self, total_normal_readers):
        """Original algorithm for systems without smart card readers"""
        best_solution = None
        best_cost     = float('inf')
        max_kt400 = max(1, total_normal_readers // 4 + 2)
        max_kt2   = max(1, total_normal_readers // 2 + 2)
        max_kt1   = max(1, total_normal_readers + 2)

        for kt400 in range(max_kt400 + 1):
            for kt2 in range(max_kt2 + 1):
                for kt1 in range(max_kt1 + 1):
                    if kt400 == 0 and kt2 == 0 and kt1 == 0:
                        continue
                    readers_provided = kt400 * 4 + kt2 * 2 + kt1 * 1
                    cost             = kt400 * 1400 + kt2 * 750 + kt1 * 450
                    if readers_provided >= total_normal_readers and cost < best_cost:
                        best_cost     = cost
                        best_solution = {
                            'kt-400': kt400, 'kt-2': kt2, 'kt-1': kt1,
                            'readers_provided': readers_provided,
                            'cost': cost,
                            'extra_readers': readers_provided - total_normal_readers,
                            'smart_card_readers_provided': 0,
                        }

        if best_solution:
            inputs_provided  = best_solution['kt-400'] * 16 + best_solution['kt-2'] * 8 + best_solution['kt-1'] * 4
            outputs_provided = best_solution['kt-400'] * 4  + best_solution['kt-2'] * 2 + best_solution['kt-1'] * 2
            return {**best_solution,
                    'inputs_provided': inputs_provided,
                    'outputs_provided': outputs_provided,
                    'algorithm': 'standard'}

        # Fallback: 1 kt-1
        return {'kt-400': 0, 'kt-2': 0, 'kt-1': 1,
                'readers_provided': 1, 'cost': 450,
                'extra_readers': 0, 'smart_card_readers_provided': 0,
                'algorithm': 'fallback', 'inputs_provided': 4, 'outputs_provided': 2}

    def select_controllers_with_smart_readers(self, total_normal_readers, total_smart_readers):
        """NEW: Special algorithm for systems WITH smart card readers"""
        best_solution = None
        best_cost     = float('inf')
        max_kt400 = max(1, (total_normal_readers + total_smart_readers) // 4 + 2)
        max_kt2   = max(1, (total_normal_readers + total_smart_readers) // 2 + 2)
        max_kt1   = max(1, (total_normal_readers + total_smart_readers) + 2)

        for kt400 in range(max_kt400 + 1):
            for kt2 in range(max_kt2 + 1):
                for kt1 in range(max_kt1 + 1):
                    if kt400 == 0 and kt2 == 0 and kt1 == 0:
                        continue
                    normal_capacity = kt400 * 4 + kt2 * 2 + kt1 * 1
                    smart_capacity  = kt400 * 4 + kt2 * 2 + kt1 * 1
                    cost            = kt400 * 1400 + kt2 * 750 + kt1 * 450
                    total_capacity  = normal_capacity + smart_capacity
                    total_required  = total_normal_readers + total_smart_readers
                    available_smart_slots = kt400 * 4 + kt2 * 2 + kt1 * 1

                    can_fit = (available_smart_slots >= total_smart_readers or
                               total_capacity >= total_required)
                    if not can_fit:
                        continue
                    if cost < best_cost:
                        best_cost = cost
                        smart_used           = min(total_smart_readers, available_smart_slots)
                        normal_used_for_smart = max(0, total_smart_readers - available_smart_slots)
                        normal_used_for_normal = total_normal_readers
                        best_solution = {
                            'kt-400': kt400, 'kt-2': kt2, 'kt-1': kt1,
                            'readers_provided': normal_capacity,
                            'smart_card_readers_provided': smart_capacity,
                            'cost': cost,
                            'extra_normal_readers': max(0, normal_capacity - normal_used_for_normal - normal_used_for_smart),
                            'extra_smart_readers':  max(0, smart_capacity  - smart_used),
                            'smart_used': smart_used,
                            'normal_used_for_smart': normal_used_for_smart,
                            'normal_used_for_normal': normal_used_for_normal,
                        }

        if best_solution:
            inputs_provided  = best_solution['kt-400'] * 16 + best_solution['kt-2'] * 8 + best_solution['kt-1'] * 4
            outputs_provided = best_solution['kt-400'] * 4  + best_solution['kt-2'] * 2 + best_solution['kt-1'] * 2
            return {**best_solution,
                    'inputs_provided': inputs_provided,
                    'outputs_provided': outputs_provided,
                    'algorithm': 'smart_reader'}

        # Fallback
        return {'kt-400': 0, 'kt-2': 0, 'kt-1': 1,
                'readers_provided': 1, 'smart_card_readers_provided': 1,
                'cost': 450, 'extra_normal_readers': 1, 'extra_smart_readers': 1,
                'smart_used': min(1, total_smart_readers),
                'normal_used_for_smart': max(0, total_smart_readers - 1),
                'normal_used_for_normal': total_normal_readers,
                'algorithm': 'fallback', 'inputs_provided': 4, 'outputs_provided': 2}

    def calculate_expansion_for_dc(self, dc_inputs, dc_outputs, controller_inputs, controller_outputs):
        """Calculate expansion modules needed for a SINGLE DC line"""
        input_shortage  = max(0, dc_inputs  - controller_inputs)
        output_shortage = max(0, dc_outputs - controller_outputs)
        result = ''
        result += '\nI/O Analysis:\n'
        result += f'  Required: {dc_inputs} inputs, {dc_outputs} outputs\n'
        result += f'  Controllers provide: {controller_inputs} inputs, {controller_outputs} outputs\n'
        result += f'  Shortage: {input_shortage} inputs, {output_shortage} outputs\n'

        if input_shortage <= 0 and output_shortage <= 0:
            result += '  ✅ No expansion modules needed\n'
            return {'modules': [], 'cost': 0, 'result': result}

        best_solution = {'modules': [], 'cost': float('inf'), 'result': result}

        # Try single-module solutions
        for module in self.expansion_modules:
            if module['inputs'] >= input_shortage and module['outputs'] >= output_shortage:
                solution = {'modules': [module['name']], 'cost': module['cost'], 'result': result}
                if solution['cost'] < best_solution['cost']:
                    best_solution = solution

        # Try two-module combinations
        for module1 in self.expansion_modules:
            for module2 in self.expansion_modules:
                total_inputs  = module1['inputs']  + module2['inputs']
                total_outputs = module1['outputs'] + module2['outputs']
                total_cost    = module1['cost']    + module2['cost']
                if total_inputs >= input_shortage and total_outputs >= output_shortage:
                    solution = {'modules': [module1['name'], module2['name']],
                                'cost': total_cost, 'result': result}
                    if solution['cost'] < best_solution['cost']:
                        best_solution = solution

        # Fallback: in16 + r8
        if best_solution['cost'] == float('inf'):
            expansion_modules = []
            expansion_cost    = 0
            if input_shortage > 0:
                in16_needed = int(np.ceil(input_shortage / 16))
                expansion_modules.append(f'in16 (x{in16_needed})')
                expansion_cost += 470 * in16_needed
            if output_shortage > 0:
                r8_needed = int(np.ceil(output_shortage / 8))
                expansion_modules.append(f'r8 (x{r8_needed})')
                expansion_cost += 470 * r8_needed
            best_solution = {'modules': expansion_modules, 'cost': expansion_cost, 'result': result}

        best_solution['result'] += f'  Expansion solution: {best_solution["modules"]}\n'
        best_solution['result'] += f'  Expansion cost: ${best_solution["cost"]}\n'
        return best_solution


# ─── CUSTOM WIDGETS ───────────────────────────────────────────────────────────

class Card(tk.Frame):
    def __init__(self, parent, title='', **kw):
        super().__init__(parent, bg=C['card'], relief='flat', bd=0, **kw)
        if title:
            hdr = tk.Frame(self, bg=C['card2'])
            hdr.pack(fill='x')
            tk.Label(hdr, text=title, font=F['h3'], bg=C['card2'],
                     fg=C['txt'], padx=14, pady=9).pack(side='left')
            tk.Frame(self, height=1, bg=C['border']).pack(fill='x')
        self.body = tk.Frame(self, bg=C['card'])
        self.body.pack(fill='both', expand=True, padx=14, pady=12)


class ModernBtn(tk.Button):
    def __init__(self, parent, text='', command=None, style='primary', **kw):
        styles = {
            'primary':  (C['accent'],   C['accent_h'],   C['white']),
            'success':  (C['teal'],     '#34d9c3',       C['bg']),
            'danger':   (C['red'],      '#ff9999',        C['white']),
            'ghost':    (C['surface'],  C['card2'],       C['txt']),
            'outline':  (C['card'],     C['surface'],     C['accent']),
        }
        bg, hbg, fg = styles.get(style, styles['primary'])
        super().__init__(parent, text=text, command=command,
                         bg=bg, fg=fg, font=F['body'],
                         relief='flat', bd=0, cursor='hand2',
                         padx=14, pady=7, activebackground=hbg, activeforeground=fg,
                         **kw)
        self.bind('<Enter>', lambda e: self.config(bg=hbg))
        self.bind('<Leave>', lambda e: self.config(bg=bg))


class LabeledEntry(tk.Frame):
    def __init__(self, parent, label, default='0', width=8, **kw):
        super().__init__(parent, bg=C['card'], **kw)
        tk.Label(self, text=label, font=F['small'], bg=C['card'],
                 fg=C['txt2'], anchor='w').pack(fill='x')
        self.var = tk.StringVar(value=str(default))
        e = tk.Entry(self, textvariable=self.var, font=F['body'],
                     bg=C['surface'], fg=C['txt'], insertbackground=C['txt'],
                     relief='flat', bd=0, width=width,
                     highlightthickness=1, highlightbackground=C['border'],
                     highlightcolor=C['accent'])
        e.pack(fill='x', ipady=5, ipadx=6)

    def get(self):
        return self.var.get()

    def set(self, v):
        self.var.set(str(v))


class StatusBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=C['sidebar'], height=28)
        self._lbl = tk.Label(self, text='● Ready', font=F['small'],
                             bg=C['sidebar'], fg=C['teal'], padx=12)
        self._lbl.pack(side='left', pady=4)

    def set(self, msg, kind='ok'):
        colors = {'ok': C['teal'], 'warn': C['orange'], 'error': C['red'], 'info': C['accent']}
        icons  = {'ok': '●', 'warn': '▲', 'error': '✕', 'info': 'ℹ'}
        self._lbl.config(text=f'{icons.get(kind,"●")} {msg}',
                         fg=colors.get(kind, C['teal']))


# ─── DEVICE FIELD DEFINITIONS ─────────────────────────────────────────────────

DEVICE_FIELDS = [
    ('smart_card',                       '🪪 Smart Card Readers'),
    ('smart_card_reader',                '💳 Smart Card Readers (Special)'),
    ('fingerprint',                      '🖐 Fingerprint Readers'),
    ('door_sensor',                      '🚪 Door Sensors'),
    ('magnetic_lock',                    '🔒 Magnetic Locks'),
    ('electric_lock',                    '⚡ Electric Locks'),
    ('rex_button',                       '🔵 REX Buttons'),
    ('push_button',                      '🟢 Push Buttons'),
    ('break_glass',                      '🔴 Break Glass'),
    ('buzzer',                           '🔔 Buzzers'),
    ('double_door_lock',                 '🔐 Double Door Locks'),
    ('ddl_sensors',                      '📡 DDL Sensors'),
    ('unmonitored_single_magnetic_lock', '🔓 Unmon. Single Mag Lock'),
    ('unmonitored_double_magnetic_lock', '🔓 Unmon. Double Mag Lock'),
]


# ─── MAIN GUI ─────────────────────────────────────────────────────────────────

class KantechDCCalculatorGUI:

    def __init__(self):
        self.dc_lines           = []
        self.access_door_types  = []
        self.swh_calculator     = SWHControllerCalculator()
        self.kantech_calc       = KantechCalculator()

        # Kantech controller pool (costs only)
        self.controllers = {
            'kt-1':   {'price': 450},
            'kt-2':   {'price': 750},
            'kt-400': {'price': 1400},
        }

        # Result stores
        self.kantech_all_results  = None
        self.kantech_grand_total  = 0
        self.gstar_results        = None
        self.swh_license_result   = None
        self.kantech_single_result = None
        self.swh_single_result    = None

        # License info
        self.license_info = {
            'special':    {'name': 'Kantech Special License',  'max_controllers': 32,
                           'description': 'For systems with 32 or fewer controllers (non-redundant)'},
            'corporate':  {'name': 'Kantech Corporate License', 'max_controllers': None,
                           'description': 'For systems with more than 32 controllers (non-redundant)'},
            'global':     {'name': 'Global License',
                           'description': 'Required for ANY redundancy configuration (replaces Special/Corporate)'},
            'gateway':    {'name': 'Gateway License',  'cost': 500,
                           'description': 'Required for gateway/server communication in redundant systems'},
            'redundancy': {'name': 'Redundancy License',
                           'description': 'Additional license for failover/redundancy capability'},
        }

        # Build UI
        self.root = tk.Tk()
        self.root.title('Access Control System Calculator')
        self.root.geometry('1280x820')
        self.root.configure(bg=C['bg'])
        self.root.minsize(960, 680)

        self.selected_dc_line_var  = tk.StringVar()
        self.selected_door_type_var = tk.StringVar()
        self.redundancy_var         = tk.BooleanVar(value=False)

        self.setup_styles()
        self.create_ui()

    # ── STYLES ────────────────────────────────────────────────────────────────

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('.',
            background=C['bg'], foreground=C['txt'], font=F['body'],
            troughcolor=C['surface'], borderwidth=0, relief='flat')

        style.configure('TNotebook',
            background=C['sidebar'], tabmargins=[0, 0, 0, 0])
        style.configure('TNotebook.Tab',
            background=C['sidebar'], foreground=C['txt2'],
            padding=[18, 10], font=F['body'], borderwidth=0)
        style.map('TNotebook.Tab',
            background=[('selected', C['card']), ('active', C['surface'])],
            foreground=[('selected', C['txt']), ('active', C['txt'])])

        style.configure('Treeview',
            background=C['card'], foreground=C['txt'],
            fieldbackground=C['card'], rowheight=30, font=F['body'],
            borderwidth=0)
        style.configure('Treeview.Heading',
            background=C['card2'], foreground=C['txt2'],
            font=F['h3'], borderwidth=0, relief='flat')
        style.map('Treeview', background=[('selected', C['accent'])])

        style.configure('TScrollbar',
            background=C['surface'], troughcolor=C['card'],
            arrowcolor=C['txt3'], borderwidth=0)

        style.configure('TCombobox',
            fieldbackground=C['surface'], background=C['surface'],
            foreground=C['txt'], selectbackground=C['accent'],
            arrowcolor=C['txt2'], borderwidth=0)
        style.map('TCombobox',
            fieldbackground=[('readonly', C['surface'])],
            foreground=[('readonly', C['txt'])])

        style.configure('TCheckbutton',
            background=C['card'], foreground=C['txt'], font=F['body'])
        style.map('TCheckbutton',
            background=[('active', C['card'])])

        style.configure('TRadiobutton',
            background=C['card'], foreground=C['txt'], font=F['body'])
        style.map('TRadiobutton',
            background=[('active', C['card'])])

    # ── LAYOUT SKELETON ───────────────────────────────────────────────────────

    def create_ui(self):
        # Top header bar
        self._build_header()

        # Main area: sidebar tabs + content
        main = tk.Frame(self.root, bg=C['bg'])
        main.pack(fill='both', expand=True)

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill='both', expand=True, padx=0, pady=0)

        self.create_main_tab()
        self.create_dc_lines_tab()
        self.create_door_types_tab()
        self.create_calculation_tab()
        self.create_license_tab()
        self.create_export_tab()

        # Status bar
        self.status = StatusBar(self.root)
        self.status.pack(fill='x', side='bottom')

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=C['sidebar'], height=60)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)

        # Logo / title
        left = tk.Frame(hdr, bg=C['sidebar'])
        left.pack(side='left', padx=20, pady=10)
        tk.Label(left, text='⚡', font=('Segoe UI', 22), bg=C['sidebar'],
                 fg=C['accent']).pack(side='left')
        tk.Label(left, text='Access Control Calculator',
                 font=F['h2'], bg=C['sidebar'], fg=C['txt']).pack(side='left', padx=8)

        # Version tag
        tk.Label(hdr, text='Kantech & SWH / GSTAR  v2.1',
                 font=F['small'], bg=C['sidebar'], fg=C['txt3']).pack(side='right', padx=20)

        tk.Frame(self.root, height=1, bg=C['border']).pack(fill='x')

    # ── MAIN TAB ──────────────────────────────────────────────────────────────

    def create_main_tab(self):
        frame = tk.Frame(self.notebook, bg=C['bg'])
        self.notebook.add(frame, text='  🏠 Home  ')

        # Two-column layout
        left  = tk.Frame(frame, bg=C['bg'])
        right = tk.Frame(frame, bg=C['bg'])
        left.pack(side='left',  fill='both', expand=True, padx=(16, 8),  pady=16)
        right.pack(side='right', fill='both', expand=True, padx=(8, 16), pady=16)

        # System status card
        status_card = Card(left, title='📊 System Status')
        status_card.pack(fill='x', pady=(0, 12))
        self.system_info_lbl = tk.Label(status_card.body,
            text='No DC lines or Door Types configured yet.\nUse the tabs above to get started.',
            font=F['body'], bg=C['card'], fg=C['txt2'], justify='left', anchor='w')
        self.system_info_lbl.pack(fill='x')

        # Quick-action card
        qa_card = Card(left, title='⚡ Quick Actions')
        qa_card.pack(fill='x', pady=(0, 12))
        btn_row = tk.Frame(qa_card.body, bg=C['card'])
        btn_row.pack(fill='x')
        ModernBtn(btn_row, '➕ Add DC Line',     command=self.show_add_dc_line_dialog, style='primary').pack(side='left', padx=(0,8))
        ModernBtn(btn_row, '🚪 Door Types',       command=lambda: self.notebook.select(2), style='ghost').pack(side='left', padx=(0,8))
        ModernBtn(btn_row, '📐 Calc Kantech',     command=self.calculate_all_kantech, style='ghost').pack(side='left', padx=(0,8))
        ModernBtn(btn_row, '📐 Calc SWH/GSTAR',  command=self.calculate_all_gstar, style='ghost').pack(side='left')

        # Overview card
        ov_card = Card(right, title='📋 System Overview')
        ov_card.pack(fill='both', expand=True)
        self.overview_text = scrolledtext.ScrolledText(
            ov_card.body, font=F['mono'], bg=C['surface'], fg=C['txt'],
            relief='flat', bd=0, wrap='word',
            insertbackground=C['txt'], state='disabled')
        self.overview_text.pack(fill='both', expand=True)

        self.update_system_info()

    def update_system_info(self):
        n_dc   = len(self.dc_lines)
        n_dt   = len(self.access_door_types)
        total_r = sum(d.calculate_totals()['readers'] for d in self.dc_lines)
        total_i = sum(d.calculate_totals()['inputs']  for d in self.dc_lines)
        total_o = sum(d.calculate_totals()['outputs'] for d in self.dc_lines)

        self.system_info_lbl.config(
            text=f'DC Lines: {n_dc}   •   Door Types: {n_dt}\n'
                 f'Total Readers: {total_r}   •   Inputs: {total_i}   •   Outputs: {total_o}')
        self.update_overview()

    def update_overview(self):
        self.overview_text.config(state='normal')
        self.overview_text.delete('1.0', 'end')
        txt = 'SYSTEM OVERVIEW\n' + '=' * 50 + '\n\n'
        if self.dc_lines:
            txt += 'DC LINES:\n' + '-' * 20 + '\n'
            for dc in self.dc_lines:
                t = dc.calculate_totals()
                txt += (f'DC Line {dc.dc_number}:  '
                        f'{t["readers"]} readers, {t["inputs"]} inputs, {t["outputs"]} outputs\n'
                        f'  Card: {dc.smart_card}  Smart: {dc.smart_card_reader}  '
                        f'Bio: {dc.fingerprint}  Sensor: {dc.door_sensor}\n')
        else:
            txt += 'No DC lines configured\n'
        txt += '\nDOOR TYPES:\n' + '-' * 20 + '\n'
        if self.access_door_types:
            for dt in self.access_door_types:
                txt += f'{dt}\n'
        else:
            txt += 'No door types defined\n'
        self.overview_text.insert('1.0', txt)
        self.overview_text.config(state='disabled')

    # ── DC LINES TAB ──────────────────────────────────────────────────────────

    def create_dc_lines_tab(self):
        frame = tk.Frame(self.notebook, bg=C['bg'])
        self.notebook.add(frame, text='  🔌 DC Lines  ')

        # Toolbar
        tb = tk.Frame(frame, bg=C['sidebar'])
        tb.pack(fill='x')
        tk.Label(tb, text='DC Line Management', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        btn_frame = tk.Frame(tb, bg=C['sidebar'])
        btn_frame.pack(side='right', padx=16, pady=8)
        ModernBtn(btn_frame, '➕ Add DC Line',    command=self.show_add_dc_line_dialog).pack(side='left', padx=4)
        ModernBtn(btn_frame, '✏️ Edit',           command=self.edit_selected_dc_line, style='ghost').pack(side='left', padx=4)
        ModernBtn(btn_frame, '🗑 Delete',          command=self.delete_selected_dc_line, style='danger').pack(side='left', padx=4)
        ModernBtn(btn_frame, '🔄 Refresh',         command=self.update_dc_lines_list, style='outline').pack(side='left', padx=4)
        tk.Frame(frame, height=1, bg=C['border']).pack(fill='x')

        # Treeview
        tree_card = Card(frame, title='DC Lines')
        tree_card.pack(fill='both', expand=True, padx=16, pady=16)

        cols = ('DC #', 'Card Readers', 'Smart Readers', 'Fingerprint',
                'Door Sensors', 'Inputs', 'Outputs', 'Mag Locks', 'Elec Locks')
        self.dc_tree = ttk.Treeview(tree_card.body, columns=cols, show='headings',
                                    selectmode='browse')
        col_widths = [60, 110, 120, 100, 110, 70, 70, 90, 90]
        for col, w in zip(cols, col_widths):
            self.dc_tree.heading(col, text=col)
            self.dc_tree.column(col, width=w, anchor='center')

        vsb = ttk.Scrollbar(tree_card.body, orient='vertical', command=self.dc_tree.yview)
        self.dc_tree.configure(yscrollcommand=vsb.set)
        self.dc_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self.dc_tree.bind('<<TreeviewSelect>>', self.on_dc_line_selected)

    def update_dc_lines_list(self):
        for row in self.dc_tree.get_children():
            self.dc_tree.delete(row)
        for dc in self.dc_lines:
            t = dc.calculate_totals()
            self.dc_tree.insert('', 'end', values=(
                f'DC {dc.dc_number}', dc.smart_card, dc.smart_card_reader,
                dc.fingerprint, dc.door_sensor, t['inputs'], t['outputs'],
                dc.magnetic_lock, dc.electric_lock))
        self.update_system_info()

    def on_dc_line_selected(self, event):
        sel = self.dc_tree.selection()
        if sel:
            vals = self.dc_tree.item(sel[0], 'values')
            self.selected_dc_line_var.set(vals[0])

    # ── DOOR TYPES TAB ────────────────────────────────────────────────────────

    def create_door_types_tab(self):
        frame = tk.Frame(self.notebook, bg=C['bg'])
        self.notebook.add(frame, text='  🚪 Door Types  ')

        # Toolbar
        tb = tk.Frame(frame, bg=C['sidebar'])
        tb.pack(fill='x')
        tk.Label(tb, text='Access Door Types', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        btn_frame = tk.Frame(tb, bg=C['sidebar'])
        btn_frame.pack(side='right', padx=16, pady=8)
        ModernBtn(btn_frame, '➕ Add Type',       command=self.show_add_door_type_dialog).pack(side='left', padx=4)
        ModernBtn(btn_frame, '✏️ Edit',           command=self.edit_selected_door_type, style='ghost').pack(side='left', padx=4)
        ModernBtn(btn_frame, '🗑 Delete',          command=self.delete_selected_door_type, style='danger').pack(side='left', padx=4)
        ModernBtn(btn_frame, '🔗 Apply to DC Line', command=self.apply_door_type_to_dc, style='success').pack(side='left', padx=4)
        tk.Frame(frame, height=1, bg=C['border']).pack(fill='x')

        tree_card = Card(frame, title='Door Types')
        tree_card.pack(fill='both', expand=True, padx=16, pady=16)

        cols = ('ID', 'Name', 'Card Readers', 'Smart Readers', 'Fingerprint',
                'Door Sensors', 'Inputs', 'Outputs')
        self.dt_tree = ttk.Treeview(tree_card.body, columns=cols, show='headings',
                                    selectmode='browse')
        col_widths = [50, 200, 110, 120, 100, 110, 70, 70]
        for col, w in zip(cols, col_widths):
            self.dt_tree.heading(col, text=col)
            self.dt_tree.column(col, width=w, anchor='center')

        vsb = ttk.Scrollbar(tree_card.body, orient='vertical', command=self.dt_tree.yview)
        self.dt_tree.configure(yscrollcommand=vsb.set)
        self.dt_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self.dt_tree.bind('<<TreeviewSelect>>', self.on_door_type_selected)

    def update_door_types_list(self):
        for row in self.dt_tree.get_children():
            self.dt_tree.delete(row)
        for dt in self.access_door_types:
            t = dt.get_totals()
            self.dt_tree.insert('', 'end', values=(
                dt.type_id, dt.name, dt.config.smart_card, dt.config.smart_card_reader,
                dt.config.fingerprint, dt.config.door_sensor, t['inputs'], t['outputs']))

    def on_door_type_selected(self, event):
        sel = self.dt_tree.selection()
        if sel:
            vals = self.dt_tree.item(sel[0], 'values')
            self.selected_door_type_var.set(f'Door Type {vals[0]}')

    # ── CALCULATIONS TAB ──────────────────────────────────────────────────────

    def create_calculation_tab(self):
        frame = tk.Frame(self.notebook, bg=C['bg'])
        self.notebook.add(frame, text='  📐 Calculations  ')

        panes = ttk.Notebook(frame)
        panes.pack(fill='both', expand=True, padx=0, pady=0)

        k_frame = tk.Frame(panes, bg=C['bg'])
        s_frame = tk.Frame(panes, bg=C['bg'])
        panes.add(k_frame, text='  Kantech System  ')
        panes.add(s_frame, text='  SWH / GSTAR System  ')

        self.create_kantech_calculation_frame(k_frame)
        self.create_swh_calculation_frame(s_frame)

    def _results_area(self, parent):
        """Shared results text widget with copy button."""
        card = Card(parent, title='📄 Calculation Results')
        card.pack(fill='both', expand=True, padx=16, pady=(0, 16))
        copy_btn = ModernBtn(card.body, '📋 Copy', style='outline')
        copy_btn.pack(anchor='e', pady=(0, 6))
        txt = scrolledtext.ScrolledText(
            card.body, font=F['mono'], bg=C['surface'], fg=C['txt'],
            relief='flat', bd=0, wrap='word', insertbackground=C['txt'],
            state='disabled')
        txt.pack(fill='both', expand=True)
        copy_btn.config(command=lambda: (
            self.root.clipboard_clear(),
            self.root.clipboard_append(txt.get('1.0', 'end')),
            self.status.set('Results copied to clipboard', 'ok')
        ))
        return txt

    def create_kantech_calculation_frame(self, parent):
        # Toolbar
        tb = tk.Frame(parent, bg=C['sidebar'])
        tb.pack(fill='x')
        tk.Label(tb, text='Kantech System Calculation', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        btn_f = tk.Frame(tb, bg=C['sidebar'])
        btn_f.pack(side='right', padx=16, pady=8)
        ModernBtn(btn_f, '⚙️ Calculate All', command=self.calculate_all_kantech).pack(side='left', padx=4)
        tk.Frame(parent, height=1, bg=C['border']).pack(fill='x')

        # Single DC line selector
        sel_card = Card(parent, title='Select DC Line (single calculation)')
        sel_card.pack(fill='x', padx=16, pady=16)
        row = tk.Frame(sel_card.body, bg=C['card'])
        row.pack(fill='x')
        tk.Label(row, text='DC Line:', font=F['body'], bg=C['card'], fg=C['txt2']).pack(side='left')
        self.kantech_dc_combo = ttk.Combobox(row, textvariable=self.selected_dc_line_var,
                                             state='readonly', width=25)
        self.kantech_dc_combo.pack(side='left', padx=8)
        ModernBtn(row, '▶ Calculate Selected', command=self.calculate_selected_kantech,
                  style='ghost').pack(side='left', padx=8)
        self.kantech_dc_combo.bind('<FocusIn>', lambda e: self._refresh_dc_combo(self.kantech_dc_combo))

        self.kantech_result_txt = self._results_area(parent)

    def create_swh_calculation_frame(self, parent):
        tb = tk.Frame(parent, bg=C['sidebar'])
        tb.pack(fill='x')
        tk.Label(tb, text='SWH / GSTAR System Calculation', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        btn_f = tk.Frame(tb, bg=C['sidebar'])
        btn_f.pack(side='right', padx=16, pady=8)
        ModernBtn(btn_f, '⚙️ Calculate All', command=self.calculate_all_gstar).pack(side='left', padx=4)
        ModernBtn(btn_f, '📜 License',        command=self.calculate_swh_license, style='ghost').pack(side='left', padx=4)
        tk.Frame(parent, height=1, bg=C['border']).pack(fill='x')

        sel_card = Card(parent, title='Select DC Line (single calculation)')
        sel_card.pack(fill='x', padx=16, pady=16)
        row = tk.Frame(sel_card.body, bg=C['card'])
        row.pack(fill='x')
        tk.Label(row, text='DC Line:', font=F['body'], bg=C['card'], fg=C['txt2']).pack(side='left')
        self.swh_dc_combo = ttk.Combobox(row, textvariable=self.selected_dc_line_var,
                                          state='readonly', width=25)
        self.swh_dc_combo.pack(side='left', padx=8)
        ModernBtn(row, '▶ Calculate Selected', command=self.calculate_selected_gstar,
                  style='ghost').pack(side='left', padx=8)
        self.swh_dc_combo.bind('<FocusIn>', lambda e: self._refresh_dc_combo(self.swh_dc_combo))

        self.swh_result_txt = self._results_area(parent)

    def _refresh_dc_combo(self, combo):
        combo['values'] = [f'DC Line {d.dc_number}' for d in self.dc_lines]

    def _write_result(self, widget, text):
        widget.config(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.config(state='disabled')

    # ── LICENSE TAB ───────────────────────────────────────────────────────────

    def create_license_tab(self):
        frame = tk.Frame(self.notebook, bg=C['bg'])
        self.notebook.add(frame, text='  📜 Licenses  ')

        panes = ttk.Notebook(frame)
        panes.pack(fill='both', expand=True)
        k_frame = tk.Frame(panes, bg=C['bg'])
        s_frame = tk.Frame(panes, bg=C['bg'])
        panes.add(k_frame, text='  Kantech Licenses  ')
        panes.add(s_frame, text='  SWH Licenses  ')

        self.create_kantech_license_frame(k_frame)
        self.create_swh_license_frame(s_frame)

    def create_kantech_license_frame(self, parent):
        tb = tk.Frame(parent, bg=C['sidebar'])
        tb.pack(fill='x')
        tk.Label(tb, text='Kantech License Calculation', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        tk.Frame(parent, height=1, bg=C['border']).pack(fill='x')

        cfg_card = Card(parent, title='System Configuration')
        cfg_card.pack(fill='x', padx=16, pady=16)
        row = tk.Frame(cfg_card.body, bg=C['card'])
        row.pack(fill='x')
        ttk.Checkbutton(row, text='Use Redundancy Configuration',
                        variable=self.redundancy_var).pack(side='left')
        tk.Label(row, text='  (Redundancy provides backup / failover capability)',
                 font=F['small'], bg=C['card'], fg=C['txt3']).pack(side='left')
        ModernBtn(cfg_card.body, '🔑 Calculate Kantech License Requirements',
                  command=self.calculate_kantech_license).pack(anchor='w', pady=(10, 0))

        self.kantech_lic_txt = self._results_area(parent)

    def create_swh_license_frame(self, parent):
        tb = tk.Frame(parent, bg=C['sidebar'])
        tb.pack(fill='x')
        tk.Label(tb, text='SWH License Calculation', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        tk.Frame(parent, height=1, bg=C['border']).pack(fill='x')

        btn_card = Card(parent)
        btn_card.pack(fill='x', padx=16, pady=16)
        ModernBtn(btn_card.body, '🔑 Calculate SWH License Requirements',
                  command=self.calculate_swh_license_gui).pack(anchor='w')

        self.swh_lic_txt = self._results_area(parent)

    # ── EXPORT TAB ────────────────────────────────────────────────────────────

    def create_export_tab(self):
        frame = tk.Frame(self.notebook, bg=C['bg'])
        self.notebook.add(frame, text='  💾 Export  ')

        tb = tk.Frame(frame, bg=C['sidebar'])
        tb.pack(fill='x')
        tk.Label(tb, text='Export Results', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        tk.Frame(frame, height=1, bg=C['border']).pack(fill='x')

        exp_card = Card(frame, title='📂 Export Options')
        exp_card.pack(fill='x', padx=16, pady=16)
        row = tk.Frame(exp_card.body, bg=C['card'])
        row.pack(fill='x')
        ModernBtn(row, '📊 Export Kantech → CSV',    command=self.export_kantech_results).pack(side='left', padx=(0,8))
        ModernBtn(row, '📊 Export SWH/GSTAR → CSV',  command=self.export_gstar_results,   style='success').pack(side='left', padx=(0,8))
        ModernBtn(row, '📋 Export System Summary',   command=self.export_system_summary,  style='ghost').pack(side='left')

        info_card = Card(frame, title='ℹ Info')
        info_card.pack(fill='x', padx=16)
        tk.Label(info_card.body,
                 text='Run calculations before exporting.\n'
                      'Files are saved as CSV and can be opened in Excel.',
                 font=F['body'], bg=C['card'], fg=C['txt2'], justify='left').pack(anchor='w')

    # ── DIALOG: ADD DC LINE ───────────────────────────────────────────────────

    def show_add_dc_line_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title('Add DC Line')
        dlg.geometry('540x680')
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(bg=C['bg'])
        dlg.resizable(True, True)

        # Header
        hdr = tk.Frame(dlg, bg=C['sidebar'])
        hdr.pack(fill='x')
        tk.Label(hdr, text='➕ Add DC Line', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        tk.Frame(dlg, height=1, bg=C['border']).pack(fill='x')

        # Method selector
        method_var = tk.StringVar(value='manual')
        mf = Card(dlg, title='Add Method')
        mf.pack(fill='x', padx=16, pady=12)
        for lbl, val in [('Manual Entry', 'manual'), ('Combine Door Types', 'combine')]:
            ttk.Radiobutton(mf.body, text=lbl, variable=method_var, value=val,
                            command=lambda: show_frame()).pack(anchor='w', pady=2)

        # Content area
        content = tk.Frame(dlg, bg=C['bg'])
        content.pack(fill='both', expand=True, padx=16)

        # --- Manual frame ---
        manual_frame = Card(content, title='Manual Configuration')
        entries = {}
        dc_entry = LabeledEntry(manual_frame.body, 'DC Line Number', default='1')
        dc_entry.pack(fill='x', pady=4)

        grid = tk.Frame(manual_frame.body, bg=C['card'])
        grid.pack(fill='x', pady=4)
        for i, (key, label) in enumerate(DEVICE_FIELDS):
            e = LabeledEntry(grid, label, default='0', width=6)
            e.grid(row=i // 2, column=i % 2, sticky='ew', padx=4, pady=2)
            entries[key] = e
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        def add_manual():
            try:
                dc_num = int(dc_entry.get())
                if dc_num < 0:
                    raise ValueError('dc_number cannot be negative')
                dev = DCDevice(dc_number=dc_num)
                for key, e in entries.items():
                    v = int(e.get())
                    if v < 0:
                        raise ValueError(f'{key} cannot be negative')
                    setattr(dev, key, v)
                self.dc_lines.append(dev)
                self.update_dc_lines_list()
                self.status.set(f'DC Line {dc_num} added successfully!', 'ok')
                dlg.destroy()
            except ValueError as ex:
                messagebox.showerror('Error', f'Invalid input: {ex}', parent=dlg)

        ModernBtn(manual_frame.body, '✅ Add DC Line', command=add_manual).pack(anchor='e', pady=8)

        # --- Combine frame ---
        combine_frame = Card(content, title='Select Door Types and Quantities')

        if not self.access_door_types:
            tk.Label(combine_frame.body, text='No door types defined yet!',
                     font=F['body'], bg=C['card'], fg=C['txt3']).pack()
        else:
            # Scrollable list
            canvas_f = tk.Frame(combine_frame.body, bg=C['card'])
            canvas_f.pack(fill='both', expand=True)
            canvas = tk.Canvas(canvas_f, bg=C['card'], highlightthickness=0, height=200)
            vsb = ttk.Scrollbar(canvas_f, orient='vertical', command=canvas.yview)
            canvas.configure(yscrollcommand=vsb.set)
            canvas.pack(side='left', fill='both', expand=True)
            vsb.pack(side='right', fill='y')
            inner = tk.Frame(canvas, bg=C['card'])
            win = canvas.create_window((0, 0), window=inner, anchor='nw')
            inner.bind('<Configure>', lambda e: canvas.configure(
                scrollregion=canvas.bbox('all')))
            canvas.bind('<Configure>', lambda e: canvas.itemconfig(win, width=e.width))

            dt_entries = {}
            for dt in self.access_door_types:
                row = tk.Frame(inner, bg=C['card'])
                row.pack(fill='x', pady=2)
                tk.Label(row, text=f'{dt.name} (ID {dt.type_id})',
                         font=F['body'], bg=C['card'], fg=C['txt'], width=30, anchor='w').pack(side='left')
                qty_e = LabeledEntry(row, 'Qty', default='0', width=5)
                qty_e.pack(side='left', padx=8)
                dt_entries[dt.type_id] = (dt, qty_e)

        dc_num_c = LabeledEntry(combine_frame.body, 'DC Line Number', default='1')
        dc_num_c.pack(fill='x', pady=6)

        def add_combined():
            if not self.access_door_types:
                return
            try:
                dc_num = int(dc_num_c.get())
                dev = DCDevice(dc_number=dc_num)
                used = 0
                for type_id, (dt, qty_e) in dt_entries.items():
                    qty = int(qty_e.get())
                    if qty < 0:
                        raise ValueError(f'Quantity for {dt.name} cannot be negative')
                    for _ in range(qty):
                        dev.add_configuration(dt.config)
                    used += qty
                if used == 0:
                    messagebox.showwarning('Warning', 'Please enter quantity > 0 for at least one door type', parent=dlg)
                    return
                self.dc_lines.append(dev)
                self.update_dc_lines_list()
                self.status.set(f'DC Line {dc_num} created with {used} door type(s)!', 'ok')
                dlg.destroy()
            except ValueError as ex:
                messagebox.showerror('Error', str(ex), parent=dlg)

        ModernBtn(combine_frame.body, '✅ Create DC Line', command=add_combined).pack(anchor='e', pady=8)

        def show_frame():
            manual_frame.pack_forget()
            combine_frame.pack_forget()
            if method_var.get() == 'manual':
                manual_frame.pack(fill='both', expand=True)
            else:
                combine_frame.pack(fill='both', expand=True)

        show_frame()

        # Footer
        tk.Frame(dlg, height=1, bg=C['border']).pack(fill='x', pady=(8, 0))
        ModernBtn(dlg, '✕ Cancel', command=dlg.destroy, style='ghost').pack(anchor='e', padx=16, pady=8)

    # ── DIALOG: ADD DOOR TYPE ─────────────────────────────────────────────────

    def show_add_door_type_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title('Add Access Door Type')
        dlg.geometry('460x580')
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(bg=C['bg'])

        hdr = tk.Frame(dlg, bg=C['sidebar'])
        hdr.pack(fill='x')
        tk.Label(hdr, text='🚪 Add Door Type', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        tk.Frame(dlg, height=1, bg=C['border']).pack(fill='x')

        name_card = Card(dlg)
        name_card.pack(fill='x', padx=16, pady=12)
        name_e = LabeledEntry(name_card.body, 'Door Type Name:', default='')
        name_e.pack(fill='x')

        dev_card = Card(dlg, title='Device Configuration')
        dev_card.pack(fill='both', expand=True, padx=16)
        entries = {}
        grid = tk.Frame(dev_card.body, bg=C['card'])
        grid.pack(fill='both', expand=True)
        for i, (key, label) in enumerate(DEVICE_FIELDS):
            e = LabeledEntry(grid, label, default='0', width=6)
            e.grid(row=i // 2, column=i % 2, sticky='ew', padx=4, pady=2)
            entries[key] = e
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        def add_door_type():
            name = name_e.get().strip()
            if not name:
                messagebox.showerror('Error', 'Please enter a door type name', parent=dlg)
                return
            try:
                dt = AccessDoorType(type_id=len(self.access_door_types) + 1, name=name)
                for key, e in entries.items():
                    v = int(e.get())
                    if v < 0:
                        raise ValueError(f'{key} cannot be negative')
                    setattr(dt.config, key, v)
                self.access_door_types.append(dt)
                self.update_door_types_list()
                self.status.set(f'Door Type "{name}" added!', 'ok')
                dlg.destroy()
            except ValueError as ex:
                messagebox.showerror('Error', f'Invalid input: {ex}', parent=dlg)

        tk.Frame(dlg, height=1, bg=C['border']).pack(fill='x', pady=(8, 0))
        btn_row = tk.Frame(dlg, bg=C['bg'])
        btn_row.pack(fill='x', padx=16, pady=8)
        ModernBtn(btn_row, '✅ Add', command=add_door_type).pack(side='left')
        ModernBtn(btn_row, '✕ Cancel', command=dlg.destroy, style='ghost').pack(side='right')

    # ── EDIT / DELETE DC LINE ─────────────────────────────────────────────────

    def edit_selected_dc_line(self):
        sel = self.dc_tree.selection()
        if not sel:
            messagebox.showwarning('Warning', 'Please select a DC line to edit')
            return
        vals = self.dc_tree.item(sel[0], 'values')
        dc_num = int(vals[0].split()[1])
        dc = next((d for d in self.dc_lines if d.dc_number == dc_num), None)
        if not dc:
            messagebox.showerror('Error', 'DC line not found')
            return
        self.show_edit_dc_line_dialog(dc)

    def show_edit_dc_line_dialog(self, dc):
        dlg = tk.Toplevel(self.root)
        dlg.title(f'Edit DC Line {dc.dc_number}')
        dlg.geometry('460x600')
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(bg=C['bg'])

        hdr = tk.Frame(dlg, bg=C['sidebar'])
        hdr.pack(fill='x')
        tk.Label(hdr, text=f'✏️ Edit DC Line {dc.dc_number}', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        tk.Frame(dlg, height=1, bg=C['border']).pack(fill='x')

        dev_card = Card(dlg, title='Device Configuration')
        dev_card.pack(fill='both', expand=True, padx=16, pady=12)
        entries = {}
        grid = tk.Frame(dev_card.body, bg=C['card'])
        grid.pack(fill='both', expand=True)
        for i, (key, label) in enumerate(DEVICE_FIELDS):
            e = LabeledEntry(grid, label, default=getattr(dc, key), width=6)
            e.grid(row=i // 2, column=i % 2, sticky='ew', padx=4, pady=2)
            entries[key] = e
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        def save_changes():
            try:
                for key, e in entries.items():
                    v = int(e.get())
                    if v < 0:
                        raise ValueError(f'{key} cannot be negative')
                    setattr(dc, key, v)
                self.update_dc_lines_list()
                self.status.set(f'DC Line {dc.dc_number} updated!', 'ok')
                dlg.destroy()
            except ValueError as ex:
                messagebox.showerror('Error', f'Invalid input: {ex}', parent=dlg)

        tk.Frame(dlg, height=1, bg=C['border']).pack(fill='x')
        btn_row = tk.Frame(dlg, bg=C['bg'])
        btn_row.pack(fill='x', padx=16, pady=8)
        ModernBtn(btn_row, '💾 Save', command=save_changes).pack(side='left')
        ModernBtn(btn_row, '✕ Cancel', command=dlg.destroy, style='ghost').pack(side='right')

    def delete_selected_dc_line(self):
        sel = self.dc_tree.selection()
        if not sel:
            messagebox.showwarning('Warning', 'Please select a DC line to delete')
            return
        vals = self.dc_tree.item(sel[0], 'values')
        dc_num = int(vals[0].split()[1])
        if messagebox.askyesno('Confirm', f'Delete DC Line {dc_num}?'):
            self.dc_lines = [d for d in self.dc_lines if d.dc_number != dc_num]
            self.update_dc_lines_list()
            self.status.set(f'DC Line {dc_num} deleted', 'warn')

    # ── EDIT / DELETE DOOR TYPE ───────────────────────────────────────────────

    def edit_selected_door_type(self):
        sel = self.dt_tree.selection()
        if not sel:
            messagebox.showwarning('Warning', 'Please select a door type to edit')
            return
        vals = self.dt_tree.item(sel[0], 'values')
        tid = int(vals[0])
        dt = next((d for d in self.access_door_types if d.type_id == tid), None)
        if not dt:
            messagebox.showerror('Error', 'Door type not found')
            return
        self.show_edit_door_type_dialog(dt)

    def show_edit_door_type_dialog(self, dt):
        dlg = tk.Toplevel(self.root)
        dlg.title(f'Edit Door Type: {dt.name}')
        dlg.geometry('460x580')
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(bg=C['bg'])

        hdr = tk.Frame(dlg, bg=C['sidebar'])
        hdr.pack(fill='x')
        tk.Label(hdr, text=f'✏️ Edit: {dt.name}', font=F['h2'],
                 bg=C['sidebar'], fg=C['txt'], padx=16, pady=12).pack(side='left')
        tk.Frame(dlg, height=1, bg=C['border']).pack(fill='x')

        name_card = Card(dlg)
        name_card.pack(fill='x', padx=16, pady=12)
        name_e = LabeledEntry(name_card.body, 'Door Type Name:', default=dt.name)
        name_e.pack(fill='x')

        dev_card = Card(dlg, title='Device Configuration')
        dev_card.pack(fill='both', expand=True, padx=16)
        entries = {}
        grid = tk.Frame(dev_card.body, bg=C['card'])
        grid.pack(fill='both', expand=True)
        for i, (key, label) in enumerate(DEVICE_FIELDS):
            e = LabeledEntry(grid, label, default=getattr(dt.config, key), width=6)
            e.grid(row=i // 2, column=i % 2, sticky='ew', padx=4, pady=2)
            entries[key] = e
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        def save_changes():
            name = name_e.get().strip()
            if not name:
                messagebox.showerror('Error', 'Please enter a door type name', parent=dlg)
                return
            try:
                dt.name = name
                for key, e in entries.items():
                    v = int(e.get())
                    if v < 0:
                        raise ValueError(f'{key} cannot be negative')
                    setattr(dt.config, key, v)
                self.update_door_types_list()
                self.status.set(f'Door Type "{name}" updated!', 'ok')
                dlg.destroy()
            except ValueError as ex:
                messagebox.showerror('Error', f'Invalid input: {ex}', parent=dlg)

        tk.Frame(dlg, height=1, bg=C['border']).pack(fill='x')
        btn_row = tk.Frame(dlg, bg=C['bg'])
        btn_row.pack(fill='x', padx=16, pady=8)
        ModernBtn(btn_row, '💾 Save', command=save_changes).pack(side='left')
        ModernBtn(btn_row, '✕ Cancel', command=dlg.destroy, style='ghost').pack(side='right')

    def delete_selected_door_type(self):
        sel = self.dt_tree.selection()
        if not sel:
            messagebox.showwarning('Warning', 'Please select a door type to delete')
            return
        vals = self.dt_tree.item(sel[0], 'values')
        tid = int(vals[0])
        dt = next((d for d in self.access_door_types if d.type_id == tid), None)
        if dt and messagebox.askyesno('Confirm', f'Delete Door Type "{dt.name}"?'):
            self.access_door_types = [d for d in self.access_door_types if d.type_id != tid]
            self.update_door_types_list()
            self.status.set(f'Door Type "{dt.name}" deleted', 'warn')

    def apply_door_type_to_dc(self):
        sel = self.dt_tree.selection()
        if not sel:
            messagebox.showwarning('Warning', 'Please select a door type to apply')
            return
        vals = self.dt_tree.item(sel[0], 'values')
        tid = int(vals[0])
        dt = next((d for d in self.access_door_types if d.type_id == tid), None)
        if not dt:
            messagebox.showerror('Error', 'Door type not found')
            return
        dc_num = len(self.dc_lines) + 1
        new_dc = DCDevice(dc_number=dc_num)
        new_dc.add_configuration(dt.config)
        self.dc_lines.append(new_dc)
        self.update_dc_lines_list()
        self.status.set(f'DC Line {dc_num} created using "{dt.name}" configuration!', 'ok')

    # ── KANTECH CALCULATIONS ───────────────────────────────────────────────────

    def calculate_all_kantech(self):
        if not self.dc_lines:
            messagebox.showwarning('Warning', 'No DC lines configured!')
            return
        self.kantech_all_results = []
        total_kt400 = total_kt2 = total_kt1 = 0
        total_ctrl_cost = total_exp_cost = 0
        smart_card_reader_system = False
        output = ('KANTECH SYSTEM CALCULATION — ALL DC LINES\n'
                  + '=' * 60 + '\n\n')

        for dc in self.dc_lines:
            req = dc.calculate_totals()
            ctrl = self.kantech_calc.select_controllers_for_dc(req)
            if not ctrl:
                output += f'❌ No controller combination found for DC Line {dc.dc_number}!\n\n'
                continue

            exp = self.kantech_calc.calculate_expansion_for_dc(
                req['inputs'], req['outputs'],
                ctrl['inputs_provided'], ctrl['outputs_provided'])

            total_cost = ctrl['cost'] + exp['cost']
            self.kantech_all_results.append({
                'requirements': req, 'controllers': ctrl,
                'expansion': exp, 'total_cost': total_cost,
                'dc_number': dc.dc_number,
            })
            total_kt400 += ctrl['kt-400']
            total_kt2   += ctrl['kt-2']
            total_kt1   += ctrl['kt-1']
            total_ctrl_cost += ctrl['cost']
            total_exp_cost  += exp['cost']
            if ctrl.get('algorithm') == 'smart_reader':
                smart_card_reader_system = True

            output += f'DC Line {dc.dc_number}\n'
            output += (f'  Requirements: {req["readers"]} readers '
                       f'({req["smart_cards"]} card, {req["smart_card_readers"]} smart card, '
                       f'{req["fingerprints"]} bio)\n')
            output += f'  Inputs: {req["inputs"]}, Outputs: {req["outputs"]}\n'
            if ctrl.get('algorithm') == 'smart_reader':
                output += '  [SMART CARD READER MODE]\n'
            output += (f'  Controllers: kt-400({ctrl["kt-400"]}), '
                       f'kt-2({ctrl["kt-2"]}), kt-1({ctrl["kt-1"]})\n')
            output += f'  Controller Cost: ${ctrl["cost"]:,}\n'
            output += f'  Total Cost for this line: ${total_cost:,}\n'
            output += '-' * 40 + '\n\n'

        grand_total = total_ctrl_cost + total_exp_cost
        self.kantech_grand_total = grand_total
        total_ctrl = total_kt400 + total_kt2 + total_kt1

        output += 'SUMMARY\n' + '=' * 60 + '\n'
        output += f'Total Controllers Needed:\n'
        output += f'  kt-400: {total_kt400} units  (${total_kt400 * 1400:,})\n'
        output += f'  kt-2:   {total_kt2} units  (${total_kt2 * 750:,})\n'
        output += f'  kt-1:   {total_kt1} units  (${total_kt1 * 450:,})\n'
        if smart_card_reader_system:
            output += '  Note: Using smart card reader optimized algorithm\n'
        output += f'Total controller cost: ${total_ctrl_cost:,}\n'
        output += f'Total expansion cost:  ${total_exp_cost:,}\n'
        output += f'GRAND TOTAL:           ${grand_total:,}\n\n'
        output += f'License Reference:\n'
        output += f'Total Controllers: {total_ctrl} '
        if total_ctrl <= 32:
            output += '→ Kantech Special License\n'
        else:
            output += '→ Kantech Corporate License\n'
        output += 'Note: For redundancy, migrate to Global + Gateway + Redundancy licenses\n'

        self._write_result(self.kantech_result_txt, output)
        self.status.set(f'Kantech calculation complete — Grand Total: ${grand_total:,}', 'ok')
        self.notebook.select(3)

    def calculate_selected_kantech(self):
        val = self.selected_dc_line_var.get()
        if not val:
            messagebox.showwarning('Warning', 'Please select a DC line')
            return
        try:
            dc_num = int(val.split()[-1])
        except Exception:
            messagebox.showerror('Error', 'Invalid DC line selection')
            return
        dc = next((d for d in self.dc_lines if d.dc_number == dc_num), None)
        if not dc:
            messagebox.showerror('Error', 'DC line not found')
            return

        req  = dc.calculate_totals()
        ctrl = self.kantech_calc.select_controllers_for_dc(req)
        if not ctrl:
            self._write_result(self.kantech_result_txt,
                               f'❌ No controller combination found for DC Line {dc_num}!\n')
            return

        exp  = self.kantech_calc.calculate_expansion_for_dc(
            req['inputs'], req['outputs'],
            ctrl['inputs_provided'], ctrl['outputs_provided'])
        self.kantech_single_result = {'requirements': req, 'controllers': ctrl, 'expansion': exp}

        out = (f'KANTECH SYSTEM CALCULATION — DC LINE {dc_num}\n'
               + '=' * 60 + '\n\n')
        out += 'Requirements:\n'
        out += f'  Total Readers: {req["readers"]}\n'
        out += f'  - Card Readers:       {req["smart_cards"]}\n'
        out += f'  - Smart Card Readers: {req["smart_card_readers"]}\n'
        out += f'  - Bio-metric Readers: {req["fingerprints"]}\n'
        out += f'  Inputs:  {req["inputs"]}\n'
        out += f'  Outputs: {req["outputs"]}\n\n'

        out += 'STEP 1: SELECT CONTROLLERS\n' + '-' * 40 + '\n'
        out += f'Selected Controllers for DC Line {dc_num}:\n'
        out += f'  kt-400: {ctrl["kt-400"]} units\n'
        out += f'  kt-2:   {ctrl["kt-2"]} units\n'
        out += f'  kt-1:   {ctrl["kt-1"]} units\n'
        out += f'  Controller Cost: ${ctrl["cost"]:,}\n'
        if ctrl.get('algorithm') == 'smart_reader':
            out += '\n⚠️  SMART CARD READER OPTIMIZATION ACTIVE\n'
            out += f'  Smart readers on smart slots: {ctrl.get("smart_used", 0)}\n'
            out += f'  Smart readers on normal slots: {ctrl.get("normal_used_for_smart", 0)}\n'
            out += f'  Normal readers: {ctrl.get("normal_used_for_normal", 0)}\n'
        out += f'\nController Capabilities:\n'
        out += f'  Inputs provided:  {ctrl["inputs_provided"]}\n'
        out += f'  Outputs provided: {ctrl["outputs_provided"]}\n'
        out += exp['result']
        out += f'\nFINAL COST BREAKDOWN:\n'
        out += f'  Controllers: ${ctrl["cost"]:,}\n'
        out += f'  Expansion:   ${exp["cost"]:,}\n'
        out += f'  TOTAL:       ${ctrl["cost"] + exp["cost"]:,}\n'

        self._write_result(self.kantech_result_txt, out)
        self.status.set(f'DC Line {dc_num} calculated — Total: ${ctrl["cost"]+exp["cost"]:,}', 'ok')

    # ── GSTAR / SWH CALCULATIONS ──────────────────────────────────────────────

    def calculate_all_gstar(self):
        if not self.dc_lines:
            messagebox.showwarning('Warning', 'No DC lines configured!')
            return
        self.gstar_results = {'all_results': [], 'total_controllers': 0,
                               'total_readers': 0, 'controller_counts': {},
                               'total_expansion_cost': 0,
                               'total_input_modules': 0, 'total_output_modules': 0}
        output = ('SWH/GSTAR SYSTEM CALCULATION — ALL DC LINES\n'
                  + '=' * 60 + '\n\n')
        grand_total = 0

        for dc in self.dc_lines:
            req  = dc.calculate_totals()
            ctrl = self.swh_calculator.select_controller_for_readers(req['readers'])
            if not ctrl:
                output += f'❌ No suitable GSTAR controller for DC Line {dc.dc_number}!\n\n'
                continue
            exp = self.swh_calculator.calculate_expansion_for_swh(
                req['inputs'], req['outputs'], ctrl.inputs, ctrl.outputs)
            total_cost = ctrl.price + exp['cost']
            grand_total += total_cost
            self.gstar_results['total_controllers'] += 1
            self.gstar_results['total_readers'] += req['readers']
            self.gstar_results['total_expansion_cost'] += exp['cost']
            self.gstar_results['total_input_modules']  += exp['input_modules']
            self.gstar_results['total_output_modules'] += exp['output_modules']
            self.gstar_results['controller_counts'][ctrl.name] = \
                self.gstar_results['controller_counts'].get(ctrl.name, 0) + 1
            self.gstar_results['all_results'].append({
                'dc_number': dc.dc_number, 'requirements': req,
                'controller': ctrl, 'expansion': exp, 'total_cost': total_cost})

            output += f'DC Line {dc.dc_number}\n'
            output += f'  Requirements: {req["readers"]} readers, {req["inputs"]} inputs, {req["outputs"]} outputs\n'
            output += f'  Selected Controller: {ctrl.name}\n'
            output += f'  Controller Price: ${ctrl.price:,}\n'
            output += f'  ACM Modules included: {ctrl.number_of_acm}\n'
            output += f'  Total Cost for this line: ${total_cost:,}\n'
            output += '-' * 40 + '\n\n'

        output += 'SUMMARY\n' + '=' * 60 + '\n'
        output += f'Total GSTAR Controllers: {self.gstar_results["total_controllers"]}\n'
        output += 'Controller Breakdown:\n'
        for name, cnt in self.gstar_results['controller_counts'].items():
            output += f'  {name}: {cnt} units\n'
        output += f'\nTotal Expansion Modules:\n'
        output += f'  AS0073-000 (8-input): {self.gstar_results["total_input_modules"]} units\n'
        output += f'  AS0074-000 (8-output): {self.gstar_results["total_output_modules"]} units\n'
        output += f'\nTotal controller cost: ${sum(r["controller"].price for r in self.gstar_results["all_results"]):,}\n'
        output += f'Total expansion cost:  ${self.gstar_results["total_expansion_cost"]:,}\n'
        output += f'GRAND TOTAL HARDWARE:  ${grand_total:,}\n'
        output += f'\nSYSTEM SUMMARY:\n'
        output += f'  Total DC Lines: {len(self.dc_lines)}\n'
        output += f'  Total Controllers Needed: {self.gstar_results["total_controllers"]}\n'
        output += f'  Total Readers in System: {self.gstar_results["total_readers"]}\n'
        output += f'  Total System Cost: ${grand_total:,}\n'

        self._write_result(self.swh_result_txt, output)
        self.status.set(f'SWH/GSTAR calculation complete — Total: ${grand_total:,}', 'ok')
        self.notebook.select(3)

    def calculate_selected_gstar(self):
        val = self.selected_dc_line_var.get()
        if not val:
            messagebox.showwarning('Warning', 'Please select a DC line')
            return
        try:
            dc_num = int(val.split()[-1])
        except Exception:
            messagebox.showerror('Error', 'Invalid DC line selection')
            return
        dc = next((d for d in self.dc_lines if d.dc_number == dc_num), None)
        if not dc:
            messagebox.showerror('Error', 'DC line not found')
            return

        req  = dc.calculate_totals()
        ctrl = self.swh_calculator.select_controller_for_readers(req['readers'])
        if not ctrl:
            self._write_result(self.swh_result_txt,
                               f'❌ No suitable GSTAR controller found for {req["readers"]} readers!\n')
            return
        exp = self.swh_calculator.calculate_expansion_for_swh(
            req['inputs'], req['outputs'], ctrl.inputs, ctrl.outputs)
        self.swh_single_result = {'requirements': req, 'controller': ctrl, 'expansion': exp}

        out = f'SWH GSTAR — DC LINE {dc_num} CALCULATION\n' + '=' * 60 + '\n\n'
        out += f'Requirements:\n'
        out += f'  Readers: {req["readers"]}\n'
        out += f'  Inputs:  {req["inputs"]}\n'
        out += f'  Outputs: {req["outputs"]}\n\n'
        out += 'STEP 1: SELECT GSTAR CONTROLLER\n' + '-' * 40 + '\n'
        out += f'Selected Controller for DC Line {dc_num}:\n'
        out += f'  Controller: {ctrl.name}\n'
        out += f'  Readers provided: {ctrl.readers}\n'
        out += f'  Controller Cost: ${ctrl.price:,}\n'
        out += f'  ACM Modules included: {ctrl.number_of_acm}\n'
        out += f'Controller I/O Capabilities:\n'
        out += f'  Inputs provided:  {ctrl.inputs}\n'
        out += f'  Outputs provided: {ctrl.outputs}\n'
        out += exp['result']
        out += f'\nFINAL COST BREAKDOWN:\n'
        out += f'  Controller: ${ctrl.price:,}\n'
        out += f'  Expansion:  ${exp["cost"]:,}\n'
        out += f'  ACM Modules: {ctrl.number_of_acm} included\n'
        out += f'  TOTAL:       ${ctrl.price + exp["cost"]:,}\n'

        self._write_result(self.swh_result_txt, out)
        self.status.set(f'DC Line {dc_num} GSTAR — Total: ${ctrl.price + exp["cost"]:,}', 'ok')

    # ── LICENSE CALCULATIONS ───────────────────────────────────────────────────

    def calculate_kantech_license(self):
        if not self.dc_lines:
            messagebox.showwarning('Warning', 'No DC lines configured!')
            return
        total_kt400 = total_kt2 = total_kt1 = 0
        for dc in self.dc_lines:
            req  = dc.calculate_totals()
            ctrl = self.kantech_calc.select_controllers_for_dc(req)
            if ctrl:
                total_kt400 += ctrl['kt-400']
                total_kt2   += ctrl['kt-2']
                total_kt1   += ctrl['kt-1']

        total_ctrl = total_kt400 + total_kt2 + total_kt1
        out = 'KANTECH LICENSE CALCULATION\n' + '=' * 60 + '\n\n'
        out += 'CONTROLLER SUMMARY:\n' + '-' * 40 + '\n'
        out += f'Total Controllers Needed: {total_ctrl}\n'
        out += f'  kt-400: {total_kt400} units\n'
        out += f'  kt-2:   {total_kt2} units\n'
        out += f'  kt-1:   {total_kt1} units\n\n'

        if self.redundancy_var.get():
            gw  = self.license_info['gateway']
            red = self.license_info['redundancy']
            out += 'REDUNDANCY CONFIGURATION SELECTED\n'
            out += '✅ Required License: Global License\n'
            out += '   Reason: Redundancy requires Global License (replaces Special/Corporate)\n'
            out += '   Description: Required for ANY redundancy configuration\n\n'
            out += 'ADDITIONAL LICENSES FOR REDUNDANCY:\n'
            out += f'   1. Gateway License\n'
            out += f'      Cost: ${gw["cost"]}\n'
            out += f'      Description: {gw["description"]}\n'
            out += f'   2. Redundancy License\n'
            out += f'      Description: {red["description"]}\n\n'
            out += 'LICENSE SUMMARY:\n'
            out += f'Total Controllers: {total_ctrl}\n'
            out += 'Configuration: Redundant\n\n'
            out += 'PRIMARY LICENSE:\n  • Global License\n\n'
            out += 'ADDITIONAL LICENSES:\n'
            out += f'  • Gateway License: ${gw["cost"]}\n'
            out += '  • Redundancy License: contact vendor\n'
            out += f'TOTAL LICENSE COST: ${gw["cost"]} + Redundancy (contact vendor)\n'
        else:
            if total_ctrl <= 32:
                lic = self.license_info['special']
                reason = f'{total_ctrl} controllers ≤ 32'
            else:
                lic = self.license_info['corporate']
                reason = f'{total_ctrl} controllers > 32'
            out += f'✅ Required License: {lic["name"]}\n'
            out += f'   Reason: {reason}\n'
            out += f'   Description: {lic["description"]}\n\n'
            out += '\nLICENSE SUMMARY:\n'
            out += f'Total Controllers: {total_ctrl}\n'
            out += 'Configuration: Non-Redundant\n\n'
            out += f'  • {lic["name"]}\n'
            out += 'ADDITIONAL LICENSES: None\n'
            out += 'TOTAL LICENSE COST: $0 (included in controller cost)\n'

        self._write_result(self.kantech_lic_txt, out)
        self.status.set('Kantech license calculation complete', 'ok')

    def calculate_swh_license(self):
        if not self.gstar_results:
            messagebox.showwarning('Warning', 'Please calculate GSTAR controllers first!')
            return
        self.calculate_swh_license_gui()

    def calculate_swh_license_gui(self):
        if not self.dc_lines:
            messagebox.showwarning('Warning', 'No DC lines configured!')
            return
        total_readers = sum(dc.calculate_totals()['readers'] for dc in self.dc_lines)
        licenses = self.swh_calculator.swh_licenses

        out = 'SWH LICENSE CALCULATION\n' + '=' * 60 + '\n\n'
        out += 'SYSTEM SUMMARY:\n' + '-' * 40 + '\n'
        out += f'Total DC Lines: {len(self.dc_lines)}\n'
        out += f'Total Readers in System: {total_readers}\n\n'
        out += 'AVAILABLE SWH LICENSES:\n'
        suitable = []
        for lic in licenses:
            status = '✓ Suitable' if lic['max_readers'] >= total_readers else '✗ Insufficient'
            out += f'  {status}  {lic["name"]}  Max Readers: {lic["max_readers"]}\n'
            if lic['max_readers'] >= total_readers:
                suitable.append(lic)

        if suitable:
            best = min(suitable, key=lambda x: x['max_readers'])
            self.swh_license_result = best
            out += f'\n✅ RECOMMENDED LICENSE:\n'
            out += f'   License Name: {best["name"]}\n'
            out += f'   Maximum Readers Supported: {best["max_readers"]}\n'
            out += f'   Your System Readers: {total_readers}\n'
            out += f'   Available Capacity: {best["max_readers"] - total_readers} readers\n'
            out += f'   License Cost: ${best["cost"]} (included in controller cost)\n\n'
            out += 'LICENSE SUMMARY:\n'
            out += f'Total Readers: {total_readers}\n'
            out += f'Selected License: {best["name"]}\n'
            out += f'Total License Cost: ${best["cost"]}\n'
        else:
            out += '\n❌ NO SUITABLE LICENSE FOUND!\n'
            out += f'   Your system has {total_readers} readers\n'
            out += f'   Maximum available license supports {max(l["max_readers"] for l in licenses)} readers\n'
            out += '   Consider splitting the system or contacting SWH for enterprise solutions\n'

        self._write_result(self.swh_lic_txt, out)
        self.status.set(f'SWH license calculated for {total_readers} total readers', 'ok')

    # ── EXPORT ────────────────────────────────────────────────────────────────

    def _ask_save(self, default_name):
        return filedialog.asksaveasfilename(
            defaultextension='.csv',
            initialfile=default_name,
            filetypes=[('CSV Files', '*.csv'), ('All Files', '*.*')])

    def export_kantech_results(self):
        if not self.kantech_all_results:
            messagebox.showwarning('Warning', 'Please run Kantech calculations first!')
            return
        path = self._ask_save('kantech_results.csv')
        if not path:
            return
        try:
            rows = []
            for r in self.kantech_all_results:
                req = r['requirements']
                ctrl = r['controllers']
                exp  = r['expansion']
                rows.append({
                    'DC Line': r['dc_number'],
                    'Total Readers': req['readers'],
                    'Card Readers': req['smart_cards'],
                    'Smart Card Readers': req['smart_card_readers'],
                    'Fingerprint': req['fingerprints'],
                    'Inputs': req['inputs'],
                    'Outputs': req['outputs'],
                    'Algorithm': ctrl.get('algorithm', 'standard'),
                    'kt-400': ctrl['kt-400'],
                    'kt-2': ctrl['kt-2'],
                    'kt-1': ctrl['kt-1'],
                    'Controller Cost': ctrl['cost'],
                    'Expansion Modules': str(exp.get('modules', [])),
                    'Expansion Cost': exp['cost'],
                    'Total Cost': r['total_cost'],
                })
            pd.DataFrame(rows).to_csv(path, index=False)
            self.status.set(f'✅ Results exported to {os.path.basename(path)}', 'ok')
            messagebox.showinfo('Success', f'Results exported to {path}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to export: {e}')

    def export_gstar_results(self):
        if not self.gstar_results:
            messagebox.showwarning('Warning', 'Please run SWH/GSTAR calculations first!')
            return
        path = self._ask_save('gstar_results.csv')
        if not path:
            return
        try:
            rows = []
            for r in self.gstar_results['all_results']:
                req  = r['requirements']
                ctrl = r['controller']
                exp  = r['expansion']
                rows.append({
                    'DC Line': r['dc_number'],
                    'Readers': req['readers'],
                    'Inputs': req['inputs'],
                    'Outputs': req['outputs'],
                    'Controller': ctrl.name if ctrl else 'No suitable controller',
                    'Controller Cost': ctrl.price if ctrl else 'N/A',
                    'ACM Modules': ctrl.number_of_acm if ctrl else 'N/A',
                    'Expansion Modules': str(exp.get('modules', [])),
                    'Expansion Cost': exp['cost'],
                    'Total Cost': r['total_cost'],
                })
            summary = {
                'Total Controllers': self.gstar_results['total_controllers'],
                'Total Readers': self.gstar_results['total_readers'],
                'Total Expansion Cost': self.gstar_results['total_expansion_cost'],
                'AS0073-000 Modules': self.gstar_results['total_input_modules'],
                'AS0074-000 Modules': self.gstar_results['total_output_modules'],
            }
            if self.swh_license_result:
                summary['Selected License']  = self.swh_license_result['name']
                summary['Max Readers'] = f'Max Readers: {self.swh_license_result["max_readers"]}'
                summary['License Cost'] = self.swh_license_result['cost']
            with open(path, 'w', newline='') as f:
                pd.DataFrame(rows).to_csv(f, index=False)
                f.write('\nSYSTEM SUMMARY\n')
                for k, v in summary.items():
                    f.write(f'{k},{v}\n')
            self.status.set(f'✅ Results exported to {os.path.basename(path)}', 'ok')
            messagebox.showinfo('Success', f'Results exported to {path}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to export: {e}')

    def export_system_summary(self):
        if not self.dc_lines:
            messagebox.showwarning('Warning', 'No DC lines configured!')
            return
        path = self._ask_save('system_summary.csv')
        if not path:
            return
        try:
            rows = []
            for dc in self.dc_lines:
                t = dc.calculate_totals()
                rows.append({
                    'DC Line': dc.dc_number,
                    'Card Readers': dc.smart_card,
                    'Smart Card Readers': dc.smart_card_reader,
                    'Fingerprint': dc.fingerprint,
                    'Door Sensors': dc.door_sensor,
                    'Mag Locks': dc.magnetic_lock,
                    'Elec Locks': dc.electric_lock,
                    'REX Buttons': dc.rex_button,
                    'Push Buttons': dc.push_button,
                    'Break Glass': dc.break_glass,
                    'Buzzers': dc.buzzer,
                    'Double Door Locks': dc.double_door_lock,
                    'DDL Sensors': dc.ddl_sensors,
                    'Unmon Single Mag': dc.unmonitored_single_magnetic_lock,
                    'Unmon Double Mag': dc.unmonitored_double_magnetic_lock,
                    'Total Readers': t['readers'],
                    'Total Inputs': t['inputs'],
                    'Total Outputs': t['outputs'],
                })
            pd.DataFrame(rows).to_csv(path, index=False)
            self.status.set(f'✅ System summary exported to {os.path.basename(path)}', 'ok')
            messagebox.showinfo('Success', f'System summary exported to {path}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to export: {e}')

    def show_gstar_calculation(self):
        self.notebook.select(3)

    def run(self):
        self.root.mainloop()


def main():
    app = KantechDCCalculatorGUI()
    app.run()


if __name__ == '__main__':
    main()
