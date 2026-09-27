"""
ui.py
─────
Tkinter UI for the File Organizer.
All business logic is delegated to organizer.py.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

from organizer import organize_folder, undo_organize


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def ensure_desktop_shortcut():
    """Create a Desktop shortcut on first run of the compiled application."""
    try:
        if not getattr(sys, 'frozen', False):
            return  # Only active for the compiled .exe distribution

        target = os.path.abspath(sys.executable)

        # Locate the user's active Desktop (supports OneDrive folder redirection)
        desktop = None
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            ) as key:
                val, _ = winreg.QueryValueEx(key, "Desktop")
                desktop = os.path.expandvars(val)
        except Exception:
            pass

        if not desktop or not os.path.isdir(desktop):
            desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")

        if not os.path.isdir(desktop):
            return

        shortcut_path = os.path.join(desktop, "File Organizer.lnk")
        if os.path.exists(shortcut_path):
            return  # Shortcut already exists

        # Create shortcut via WScript.Shell without showing any console window
        vbs_content = (
            'Set WshShell = CreateObject("WScript.Shell")\n'
            f'Set Shortcut = WshShell.CreateShortcut("{shortcut_path}")\n'
            f'Shortcut.TargetPath = "{target}"\n'
            f'Shortcut.WorkingDirectory = "{os.path.dirname(target)}"\n'
            'Shortcut.Description = "File Organizer - SulamiDev"\n'
            f'Shortcut.IconLocation = "{target},0"\n'
            'Shortcut.Save\n'
        )
        temp_vbs = os.path.join(os.environ.get("TEMP", "."), "_create_shortcut.vbs")
        with open(temp_vbs, "w", encoding="utf-8") as f:
            f.write(vbs_content)

        import subprocess
        creation_flags = 0x08000000 if os.name == 'nt' else 0
        subprocess.run(["cscript", "//nologo", temp_vbs], creationflags=creation_flags, timeout=5)
        try:
            os.remove(temp_vbs)
        except OSError:
            pass
    except Exception:
        pass


class FileOrganizerApp(tk.Tk):
    """Main Tkinter window for the File Organizer application."""

    def __init__(self):
        super().__init__()
        self.title("File Organizer - Auto Sort")
        self.geometry("700x580")
        self.resizable(False, False)
        self.configure(bg="white")

        # Automatically ensure desktop shortcut on first run
        ensure_desktop_shortcut()

        # Load logo (using native Tkinter PhotoImage to eliminate heavy dependencies)
        self._logo_img = None
        self._icon_img = None

        icon_path = resource_path(os.path.join("images", "logo_icon.png"))
        if os.path.isfile(icon_path):
            try:
                self._icon_img = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, self._icon_img)
            except Exception:
                pass

        header_logo_path = resource_path(os.path.join("images", "logo_header.png"))
        if not os.path.isfile(header_logo_path):
            header_logo_path = resource_path(os.path.join("images", "logo.png"))

        if os.path.isfile(header_logo_path):
            try:
                self._logo_img = tk.PhotoImage(file=header_logo_path)
            except Exception:
                pass

        self.folder_path = tk.StringVar()
        self.status_var  = tk.StringVar(value="No folder selected.")

        self._build_ui()

    # ── UI Builder ────────────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        self._build_folder_selector()
        self._build_options()
        self._build_action_buttons()
        self._build_undo_button()
        self._build_log()
        self._build_status_bar()

    def _build_header(self):
        header = tk.Frame(self, bg="#C0392B", height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Left side – logo + title + subtitle
        left = tk.Frame(header, bg="#C0392B")
        left.pack(side="left", padx=20, pady=10)

        # Logo image (if loaded)
        if self._logo_img:
            tk.Label(
                left,
                image=self._logo_img,
                bg="#C0392B",
            ).pack(side="left", padx=(0, 12))

        # Text group
        text_group = tk.Frame(left, bg="#C0392B")
        text_group.pack(side="left")

        tk.Label(
            text_group,
            text="File Organizer",
            font=("Segoe UI", 22, "bold"),
            bg="#C0392B",
            fg="white",
        ).pack(anchor="w")

        tk.Label(
            text_group,
            text="Automatically sort your files by type",
            font=("Segoe UI", 10),
            bg="#C0392B",
            fg="#FFCCCC",
        ).pack(anchor="w", pady=(2, 0))

        # Right side – SulamiDev brand
        tk.Label(
            header,
            text="SulamiDev",
            font=("Segoe UI", 12, "bold"),
            bg="#C0392B",
            fg="#FFAAAA",
        ).pack(side="right", padx=20)

    def _build_folder_selector(self):
        sel_frame = tk.Frame(self, bg="white", pady=16)
        sel_frame.pack(fill="x", padx=30)

        tk.Label(
            sel_frame,
            text="Select Folder:",
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#333",
        ).pack(anchor="w")

        row = tk.Frame(sel_frame, bg="white")
        row.pack(fill="x", pady=6)

        tk.Entry(
            row,
            textvariable=self.folder_path,
            font=("Segoe UI", 10),
            bd=1,
            relief="solid",
            bg="#F9F9F9",
            fg="#222",
            state="readonly",
        ).pack(side="left", fill="x", expand=True, ipady=6)

        tk.Button(
            row,
            text="  Browse...  ",
            font=("Segoe UI", 10, "bold"),
            bg="#C0392B",
            fg="white",
            activebackground="#A93226",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self._browse_folder,
        ).pack(side="left", padx=(8, 0))

    def _build_options(self):
        opt_frame = tk.LabelFrame(
            self,
            text="  Options  ",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg="#C0392B",
            bd=1,
            relief="groove",
            padx=14,
            pady=10,
        )
        opt_frame.pack(fill="x", padx=30, pady=(0, 12))

        self.var_subfolders = tk.BooleanVar(value=False)
        self.var_undo       = tk.BooleanVar(value=True)

        tk.Checkbutton(
            opt_frame,
            text="Include sub-folders",
            variable=self.var_subfolders,
            font=("Segoe UI", 10),
            bg="white", fg="#333",
            activebackground="white",
            selectcolor="white",
        ).pack(side="left", padx=(0, 24))

        tk.Checkbutton(
            opt_frame,
            text="Save move log (undo support)",
            variable=self.var_undo,
            font=("Segoe UI", 10),
            bg="white", fg="#333",
            activebackground="white",
            selectcolor="white",
        ).pack(side="left")

    def _build_action_buttons(self):
        # Row frame to hold Organize + Open Folder side by side
        btn_row = tk.Frame(self, bg="white")
        btn_row.pack(fill="x", padx=30)

        tk.Button(
            btn_row,
            text="  Organize Files",
            font=("Segoe UI", 13, "bold"),
            bg="#C0392B",
            fg="white",
            activebackground="#A93226",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            pady=10,
            command=self._on_organize,
        ).pack(side="left", fill="x", expand=True)

        self._open_btn = tk.Button(
            btn_row,
            text="Open Folder",
            font=("Segoe UI", 10),
            bg="#2ECC71",
            fg="white",
            activebackground="#27AE60",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=14,
            command=self._open_folder,
        )
        # Hidden until organize completes

    def _build_undo_button(self):
        tk.Button(
            self,
            text="  Undo / Restore Files",
            font=("Segoe UI", 11),
            bg="#5D6D7E",
            fg="white",
            activebackground="#4A5568",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            pady=7,
            command=self._on_undo,
        ).pack(padx=30, fill="x", pady=(6, 0))

    def _build_log(self):
        tk.Label(
            self,
            text="Activity Log",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg="#C0392B",
        ).pack(anchor="w", padx=30, pady=(14, 2))

        log_frame = tk.Frame(self, bg="white")
        log_frame.pack(fill="both", expand=True, padx=30, pady=(0, 10))

        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_box = tk.Text(
            log_frame,
            font=("Consolas", 9),
            bg="#FFF8F8", fg="#222",
            bd=1, relief="solid",
            wrap="word",
            state="disabled",
            yscrollcommand=scrollbar.set,
        )
        self.log_box.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_box.yview)

        self.log_box.tag_config("info",    foreground="#555")
        self.log_box.tag_config("success", foreground="#1E8449")
        self.log_box.tag_config("error",   foreground="#C0392B")
        self.log_box.tag_config("header",  foreground="#C0392B",
                                           font=("Consolas", 9, "bold"))

    def _build_status_bar(self):
        tk.Label(
            self,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg="#F0F0F0", fg="#555",
            anchor="w",
            bd=1, relief="sunken",
        ).pack(fill="x", side="bottom", ipady=3)

    # ── Log Helpers ───────────────────────────────────────────────────────────
    def _log(self, text: str, tag: str = "info"):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ── Event Handlers ────────────────────────────────────────────────────────
    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select a folder to organize")
        if folder:
            self.folder_path.set(folder)
            self.status_var.set(f"Folder selected: {folder}")

    def _progress(self, filename: str, category: str, status: str):
        """Callback passed to organize_folder(); updates the log in real-time."""
        if status == "ok":
            self._log(f"  [OK]    {filename}  -->  {category}", "success")
        elif status == "skip":
            self._log(f"  [SKIP]  {filename}  (already sorted)", "info")
        elif status.startswith("error:"):
            self._log(f"  [ERR]   {filename}  -  {status[6:]}", "error")

    def _on_organize(self):
        folder = self.folder_path.get().strip()

        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Error", "The selected path is not a valid folder.")
            return

        # Confirmation dialog
        if not messagebox.askyesno(
            "Confirm Organize",
            f"Are you sure you want to organize the folder?\n\n"
            f"{folder}\n\n"
            f"Files will be sorted into sub-folders automatically."
        ):
            return

        self._clear_log()
        self._log("─" * 58, "header")
        self._log(f"  Organizing: {folder}", "header")
        self._log(f"  Date/Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "header")
        self._log("─" * 58, "header")

        # ── Delegate all work to the logic layer ──────────────────────────────
        result = organize_folder(
            folder=folder,
            include_subfolders=self.var_subfolders.get(),
            save_log=self.var_undo.get(),
            progress_callback=self._progress,
        )

        moved   = result["moved"]
        skipped = result["skipped"]
        errors  = result["errors"]
        log_path = result["log_path"]

        self._log("─" * 58, "header")
        self._log(f"  Moved: {moved}   Skipped: {skipped}   Errors: {errors}", "header")
        self._log("─" * 58, "header")

        self.status_var.set(
            f"Done - {moved} file(s) moved, {skipped} skipped, {errors} error(s)."
        )

        if log_path:
            self._log(f"  Log saved --> {log_path}", "info")

        # Show the Open Folder button (fill height to match Organize button)
        self._open_btn.pack(side="left", fill="y", padx=(8, 0))

        messagebox.showinfo(
            "Done!",
            f"Organizing complete!\n\n"
            f"Moved   : {moved}\n"
            f"Skipped : {skipped}\n"
            f"Errors  : {errors}",
        )

    def _undo_progress(self, filename: str, status: str):
        """Callback for undo_organize(); updates the log in real-time."""
        if status == "ok":
            self._log(f"  [RESTORED]  {filename}", "success")
        elif status == "skip":
            self._log(f"  [SKIP]      {filename}  (not found – already moved?)", "info")
        elif status.startswith("error:"):
            self._log(f"  [ERR]       {filename}  -  {status[6:]}", "error")

    def _on_undo(self):
        folder = self.folder_path.get().strip()

        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Error", "The selected path is not a valid folder.")
            return

        if not messagebox.askyesno(
            "Confirm Undo",
            "This will move all files back to their original locations.\n"
            "Are you sure?"
        ):
            return

        self._clear_log()
        self._log("─" * 58, "header")
        self._log(f"  Undoing: {folder}", "header")
        self._log(f"  Date/Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "header")
        self._log("─" * 58, "header")

        result = undo_organize(
            folder=folder,
            progress_callback=self._undo_progress,
        )

        if "error_msg" in result:
            self._log(f"  {result['error_msg']}", "error")
            self.status_var.set(result["error_msg"])
            messagebox.showerror("Undo Failed", result["error_msg"])
            return

        restored = result["restored"]
        skipped  = result["skipped"]
        errors   = result["errors"]

        self._log("─" * 58, "header")
        self._log(f"  Restored: {restored}   Skipped: {skipped}   Errors: {errors}", "header")
        self._log("─" * 58, "header")

        self.status_var.set(
            f"Undo done - {restored} restored, {skipped} skipped, {errors} error(s)."
        )

        messagebox.showinfo(
            "Undo Complete!",
            f"Files restored successfully!\n\n"
            f"Restored : {restored}\n"
            f"Skipped  : {skipped}\n"
            f"Errors   : {errors}",
        )

    def _open_folder(self):
        folder = self.folder_path.get().strip()
        if folder and os.path.isdir(folder):
            os.startfile(folder)
