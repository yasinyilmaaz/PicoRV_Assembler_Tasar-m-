import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import os

class LinkerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Yusuf Polat | RISC-V Linker Integrated Management")
        self.root.geometry("1100x700")
        self.root.configure(bg="#1e1e2e") # Koyu tema
        
        self.files = []
        
        # --- ÜST BAŞLIK ---
        header = tk.Frame(root, bg="#1e1e2e")
        header.pack(fill=tk.X, pady=15)
        tk.Label(header, text="RISC-V LINKER ANALYZER", font=("Segoe UI", 18, "bold"), 
                 bg="#1e1e2e", fg="#cdd6f4").pack()

        # --- ANA PANEL ---
        main_pane = tk.Frame(root, bg="#1e1e2e")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=20)

        # 1. SOL SÜTUN: Dosyalar ve Ayarlar
        left_col = tk.Frame(main_pane, bg="#1e1e2e", width=250)
        left_col.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        tk.Label(left_col, text="AYARLAR & DOSYALAR", fg="#89b4fa", bg="#1e1e2e", font=("bold", 10)).pack(anchor="w")
        
        config_frame = tk.Frame(left_col, bg="#313244", padx=10, pady=10)
        config_frame.pack(pady=5, fill=tk.X)
        
        tk.Label(config_frame, text="T-Text:", bg="#313244", fg="#cdd6f4").grid(row=0, column=0, sticky="w")
        self.text_addr = tk.Entry(config_frame, width=12, bg="#181825", fg="#cdd6f4", insertbackground="white")
        self.text_addr.insert(0, "00000000")
        self.text_addr.grid(row=0, column=1, pady=2, padx=5)
        
        tk.Label(config_frame, text="T-Data:", bg="#313244", fg="#cdd6f4").grid(row=1, column=0, sticky="w")
        self.data_addr = tk.Entry(config_frame, width=12, bg="#181825", fg="#cdd6f4", insertbackground="white")
        self.data_addr.insert(0, "00001000")
        self.data_addr.grid(row=1, column=1, pady=2, padx=5)

        tk.Button(left_col, text="+ Obje Dosyası Ekle", command=self.add_files, bg="#89b4fa", fg="#1e1e2e", font=("bold", 9)).pack(pady=10, fill=tk.X)
        self.file_listbox = tk.Listbox(left_col, height=6, bg="#313244", fg="#cdd6f4", borderwidth=0)
        self.file_listbox.pack(pady=5, fill=tk.X)
        
        tk.Button(left_col, text="LINKLE VE ANALİZ ET", command=self.run_linker, bg="#a6e3a1", fg="#1e1e2e", font=("bold", 11)).pack(pady=15, fill=tk.X)

        # 2. ORTA SÜTUN: ESTAB Tablosu
        mid_col = tk.Frame(main_pane, bg="#1e1e2e", width=350)
        mid_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        tk.Label(mid_col, text="ESTAB (External Symbol Table)", fg="#fab387", bg="#1e1e2e", font=("bold", 10)).pack(anchor="w")
        
        # ESTAB için Treeview (Tablo görünümü)
        style = ttk.Style()
        style.configure("Treeview", background="#313244", foreground="#cdd6f4", fieldbackground="#313244", borderwidth=0)
        self.estab_tree = ttk.Treeview(mid_col, columns=("Symbol", "Address"), show='headings')
        self.estab_tree.heading("Symbol", text="Sembol Adı")
        self.estab_tree.heading("Address", text="Mutlak Adres (Hex)")
        self.estab_tree.column("Symbol", width=150)
        self.estab_tree.column("Address", width=120)
        self.estab_tree.pack(fill=tk.BOTH, expand=True)

        # 3. SAĞ SÜTUN: Output.mem Görüntüleyici
        right_col = tk.Frame(main_pane, bg="#1e1e2e")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(right_col, text="FIRMWARE (output.mem)", fg="#f9e2af", bg="#1e1e2e", font=("bold", 10)).pack(anchor="w")
        self.firmware_view = scrolledtext.ScrolledText(right_col, bg="#181825", fg="#f9e2af", font=("Consolas", 11), borderwidth=0)
        self.firmware_view.pack(fill=tk.BOTH, expand=True)

        # --- ALT PANEL: Log Ekranı ---
        tk.Label(root, text="Sistem Logları", fg="#9399b2", bg="#1e1e2e", font=("Consolas", 9)).pack(anchor="w", padx=30)
        self.log_text = tk.Text(root, height=5, bg="#11111b", fg="#a6e3a1", font=("Consolas", 9), borderwidth=0)
        self.log_text.pack(fill=tk.X, padx=25, pady=10)

    def add_files(self):
        new_files = filedialog.askopenfilenames(filetypes=[("Object Files", "*.o")])
        for f in new_files:
            if f not in self.files:
                self.files.append(f)
                self.file_listbox.insert(tk.END, os.path.basename(f))

    def parse_estab(self, linker_output):
        """Linker çıktısından ESTAB verilerini ayıklar ve tabloyu günceller."""
        # Tabloyu temizle
        for item in self.estab_tree.get_children():
            self.estab_tree.delete(item)
            
        lines = linker_output.split('\n')
        start_parsing = False
        for line in lines:
            if "ESTAB:" in line:
                start_parsing = True
                continue
            if start_parsing and "->" in line:
                parts = line.split("->")
                name = parts[0].strip()
                addr = parts[1].strip()
                self.estab_tree.insert("", tk.END, values=(name, addr))
            if "Linkleme" in line:
                start_parsing = False

    def run_linker(self):
        if not self.files:
            messagebox.showwarning("Uyarı", "Lütfen .o dosyalarını ekleyin!")
            return

        output_file = "output.mem"
        cmd = ["./linker.exe", "-Ttext", f"0x{self.text_addr.get()}", "-Tdata", f"0x{self.data_addr.get()}", "-o", output_file]
        cmd.extend(self.files)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Logları yazdır
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, result.stdout)
            
            # ESTAB Tablosunu Güncelle (Linker'ın printf çıktılarını parse eder)
            self.parse_estab(result.stdout)
            
            # Output.mem Görüntüle
            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    self.firmware_view.delete(1.0, tk.END)
                    self.firmware_view.insert(tk.END, f.read())
            
            messagebox.showinfo("Başarılı", "Linkleme ve Analiz Tamamlandı!")
        except Exception as e:
            messagebox.showerror("Linker Hatası", f"Çalıştırma Hatası: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LinkerGUI(root)
    root.mainloop()