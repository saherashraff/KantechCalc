import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass

# -------------------------
# CORE LOGIC (UNCHANGED)
# -------------------------


@dataclass
class DCDevice:
    dc_number: int
    smart_card: int = 0
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

    def calculate_totals(self):
        readers = self.smart_card + self.fingerprint
        inputs = (
            self.door_sensor
            + self.rex_button
            + self.push_button
            + self.break_glass
            + self.buzzer
            + self.magnetic_lock
            + self.ddl_sensors
            + self.double_door_lock
        )
        outputs = (
            self.magnetic_lock
            + self.electric_lock
            + self.ddl_sensors
            + self.double_door_lock
        )
        return readers, inputs, outputs


# -------------------------
# GUI APPLICATION
# -------------------------


class AccessControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Access Control System Calculator")
        self.dc_lines = []

        self.entries = {}
        self.build_form()
        self.build_table()

    def build_form(self):
        frame = ttk.LabelFrame(self.root, text="Add DC Line")
        frame.pack(fill="x", padx=10, pady=10)

        fields = [
            "smart_card",
            "fingerprint",
            "door_sensor",
            "magnetic_lock",
            "electric_lock",
            "rex_button",
            "push_button",
            "break_glass",
            "buzzer",
            "double_door_lock",
            "ddl_sensors",
        ]

        for i, field in enumerate(fields):
            ttk.Label(frame, text=field.replace("_", " ").title()).grid(
                row=i, column=0, sticky="w"
            )
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, "0")
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.entries[field] = entry

        ttk.Button(frame, text="Add DC Line", command=self.add_dc_line).grid(
            row=len(fields), column=0, columnspan=2, pady=10
        )

    def build_table(self):
        self.table = ttk.Treeview(
            self.root, columns=("Readers", "Inputs", "Outputs"), show="headings"
        )
        self.table.heading("Readers", text="Readers")
        self.table.heading("Inputs", text="Inputs")
        self.table.heading("Outputs", text="Outputs")
        self.table.pack(fill="both", expand=True, padx=10, pady=10)

    def add_dc_line(self):
        try:
            values = {k: int(v.get()) for k, v in self.entries.items()}
        except ValueError:
            messagebox.showerror("Input Error", "All values must be integers")
            return

        dc = DCDevice(dc_number=len(self.dc_lines) + 1, **values)
        self.dc_lines.append(dc)

        readers, inputs, outputs = dc.calculate_totals()
        self.table.insert("", "end", values=(readers, inputs, outputs))

        messagebox.showinfo("Success", f"DC Line {dc.dc_number} added")


# -------------------------
# RUN APP
# -------------------------

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("600x500")
    app = AccessControlApp(root)
    root.mainloop()
