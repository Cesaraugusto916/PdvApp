import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import keyboard

# Adjust path to import database modules
UI_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(UI_DIR)
sys.path.insert(0, PROJECT_ROOT)

from database import db_manager

class SimulatorApp:
    def __init__(self):
        # Initialize Database connection
        db_manager.init_db()
        self.products = db_manager.get_all_products()
        
        # State
        self.cart_items = {} # barcode -> {product_details, qty}
        
        # Color Palette
        self.bg_color = "#0B0F19"
        self.card_color = "#1E293B"
        self.btn_color = "#4F46E5"
        self.btn_hover = "#6366F1"
        self.cyan_color = "#06B6D4"
        self.green_color = "#10B981"
        self.red_color = "#EF4444"
        self.text_white = "#FFFFFF"
        self.text_gray = "#94A3B8"
        
        # Root window setup
        self.root = tk.Tk()
        self.root.title("Simulador de Frente de Caixa (PDV) - Material de Construção")
        self.root.geometry("980x640")
        self.root.configure(bg=self.bg_color)
        
        # Set dark-mode style for ttk tabs
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        self.style.configure("TNotebook.Tab", 
                             background=self.card_color, 
                             foreground=self.text_white, 
                             padding=[15, 6], 
                             font=("Inter", 9, "bold"),
                             borderwidth=0)
        self.style.map("TNotebook.Tab",
                       background=[("selected", self.btn_color)],
                       foreground=[("selected", self.text_white)])
        
        self._build_layout()
        
        # Global bindings within the app window
        self.root.bind("<F12>", self._on_f12_press)
        
        # Auto-focus the barcode entry
        self.barcode_entry.focus_set()
        
        self.root.mainloop()
        
    def _build_layout(self):
        # Main split container
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=self.bg_color, bd=0, sashwidth=4)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # --- LEFT PANEL: Product Catalog ---
        left_frame = tk.Frame(main_paned, bg=self.bg_color)
        main_paned.add(left_frame, minsize=520)
        
        catalog_title = tk.Label(
            left_frame,
            text="📦 Catálogo de Produtos (Bipe Rápido)",
            font=("Inter", 14, "bold"),
            fg=self.text_white,
            bg=self.bg_color
        )
        catalog_title.pack(anchor="w", pady=(0, 10))
        
        # Tabs for categories
        self.notebook = ttk.Notebook(left_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Group products by category
        categories = {}
        for p in self.products:
            cat = p["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)
            
        for cat_name, cat_prods in categories.items():
            tab_frame = tk.Frame(self.notebook, bg=self.bg_color)
            self.notebook.add(tab_frame, text=cat_name)
            
            # Scrollable canvas for products
            canvas = tk.Canvas(tab_frame, bg=self.bg_color, highlightthickness=0)
            scrollbar = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=canvas.yview)
            scroll_content = tk.Frame(canvas, bg=self.bg_color)
            
            scroll_content.bind(
                "<Configure>",
                lambda e, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scroll_content, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=10)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
            
            # Grid layout for products in this tab
            for idx, p in enumerate(cat_prods):
                row = idx // 2
                col = idx % 2
                self._build_product_card(scroll_content, p, row, col)
                
        # --- RIGHT PANEL: Digital Bill & Keyboard entry ---
        right_frame = tk.Frame(main_paned, bg=self.card_color, bd=2, highlightthickness=1, highlightbackground="#334155")
        main_paned.add(right_frame, minsize=400)
        
        # Digital Bill Header
        bill_header = tk.Frame(right_frame, bg=self.card_color)
        bill_header.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        tk.Label(
            bill_header,
            text="🛒 Cupom Fiscal Virtual",
            font=("Inter", 13, "bold"),
            fg=self.text_white,
            bg=self.card_color
        )
        bill_header.pack(anchor="w")
        
        # Input Section (Manual / Simulated Keyboard Input)
        input_frame = tk.Frame(right_frame, bg=self.card_color, pady=10)
        input_frame.pack(fill=tk.X, padx=15)
        
        tk.Label(
            input_frame,
            text="Entrada do Leitor (Código):",
            font=("Inter", 9),
            fg=self.text_gray,
            bg=self.card_color
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        self.barcode_var = tk.StringVar()
        self.barcode_entry = tk.Entry(
            input_frame,
            textvariable=self.barcode_var,
            font=("Inter", 12, "bold"),
            bg="#0F172A",
            fg=self.cyan_color,
            insertbackground=self.cyan_color,
            bd=1,
            relief=tk.SOLID
        )
        self.barcode_entry.grid(row=1, column=0, columnspan=2, sticky="ew", ipady=6)
        input_frame.columnconfigure(0, weight=1)
        
        self.barcode_entry.bind("<Return>", self._on_barcode_enter)
        
        # Table list of Items
        self.items_tree = ttk.Treeview(
            right_frame, 
            columns=("name", "price", "qty", "total"), 
            show="headings", 
            selectmode="browse"
        )
        self.items_tree.heading("name", text="Produto")
        self.items_tree.heading("price", text="Preço")
        self.items_tree.heading("qty", text="Qtd")
        self.items_tree.heading("total", text="Total")
        
        self.items_tree.column("name", width=180, anchor="w")
        self.items_tree.column("price", width=70, anchor="e")
        self.items_tree.column("qty", width=40, anchor="center")
        self.items_tree.column("total", width=80, anchor="e")
        
        # Custom Treeview Styling for Dark Mode
        self.style.configure("Treeview", 
                             background="#0F172A", 
                             fieldbackground="#0F172A", 
                             foreground=self.text_white, 
                             rowheight=26,
                             font=("Inter", 9))
        self.style.configure("Treeview.Heading", 
                             background=self.card_color, 
                             foreground=self.text_white, 
                             font=("Inter", 9, "bold"))
        
        self.items_tree.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Total Readout
        total_frame = tk.Frame(right_frame, bg=self.card_color)
        total_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(
            total_frame,
            text="TOTAL DA COMPRA:",
            font=("Inter", 10, "bold"),
            fg=self.text_gray,
            bg=self.card_color
        ).pack(side=tk.LEFT)
        
        self.total_label = tk.Label(
            total_frame,
            text="R$ 0,00",
            font=("Inter", 18, "bold"),
            fg=self.green_color,
            bg=self.card_color
        )
        self.total_label.pack(side=tk.RIGHT)
        
        # Divider
        divider2 = tk.Frame(right_frame, bg="#334155", height=1)
        divider2.pack(fill=tk.X, padx=15, pady=10)
        
        # Actions Panel
        actions_frame = tk.Frame(right_frame, bg=self.card_color, pady=10)
        actions_frame.pack(fill=tk.X, padx=15)
        
        # Clear Cart Button
        clear_btn = tk.Button(
            actions_frame,
            text="❌ Limpar Carrinho",
            font=("Inter", 10, "bold"),
            bg="#2D3748",
            fg=self.text_white,
            activebackground="#4A5568",
            activeforeground=self.text_white,
            bd=0,
            cursor="hand2",
            padx=10,
            pady=8,
            command=self._clear_cart
        )
        clear_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Finalize Button
        self.finalize_btn = tk.Button(
            actions_frame,
            text="🔔 Finalizar Venda (F12)",
            font=("Inter", 10, "bold"),
            bg=self.green_color,
            fg=self.text_white,
            activebackground="#059669",
            activeforeground=self.text_white,
            bd=0,
            cursor="hand2",
            padx=10,
            pady=8,
            command=self._finalize_sale
        )
        self.finalize_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Helpful info label
        help_lbl = tk.Label(
            right_frame,
            text="💡 O Listener em background intercepta as teclas digitadas pelo Simulador.",
            font=("Inter", 7, "italic"),
            fg=self.text_gray,
            bg=self.card_color,
            wraplength=350,
            justify="center"
        )
        help_lbl.pack(pady=(0, 10))

    def _build_product_card(self, parent, product, row, col):
        card = tk.Frame(parent, bg=self.card_color, bd=1, relief=tk.SOLID, highlightthickness=0, highlightbackground="#334155")
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        
        # Label Info inside card
        name_lbl = tk.Label(
            card,
            text=product["name"],
            font=("Inter", 9, "bold"),
            fg=self.text_white,
            bg=self.card_color,
            anchor="w",
            justify="left",
            wraplength=200
        )
        name_lbl.pack(fill=tk.X, padx=10, pady=(10, 2))
        
        meta_frame = tk.Frame(card, bg=self.card_color)
        meta_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        
        price_lbl = tk.Label(
            meta_frame,
            text=f"R$ {product['price']:.2f}",
            font=("Inter", 10, "bold"),
            fg=self.cyan_color,
            bg=self.card_color
        )
        price_lbl.pack(side=tk.LEFT)
        
        code_lbl = tk.Label(
            meta_frame,
            text=f"Cód: {product['id']}",
            font=("Inter", 8),
            fg=self.text_gray,
            bg=self.card_color
        )
        code_lbl.pack(side=tk.RIGHT)
        
        # Click action buttons
        btn_frame = tk.Frame(card, bg=self.card_color)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Click to Scan Button (Types standard keyboard event)
        scan_btn = tk.Button(
            btn_frame,
            text="🔌 Simular Bip Físico",
            font=("Inter", 8, "bold"),
            bg="#2D3748",
            fg=self.cyan_color,
            activebackground=self.cyan_color,
            activeforeground="#0F172A",
            bd=0,
            cursor="hand2",
            pady=4,
            command=lambda: self._simulate_keyboard_scan(product["id"])
        )
        scan_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        # Add Direct Button
        add_btn = tk.Button(
            btn_frame,
            text="➕ Adicionar",
            font=("Inter", 8, "bold"),
            bg=self.btn_color,
            fg=self.text_white,
            activebackground=self.btn_hover,
            activeforeground=self.text_white,
            bd=0,
            cursor="hand2",
            pady=4,
            command=lambda: self._add_product_directly(product["id"])
        )
        add_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

    def _add_product_directly(self, barcode):
        """Directly updates the simulator's local cart programmatically."""
        product = db_manager.get_product(barcode)
        if not product:
            return
            
        if barcode in self.cart_items:
            self.cart_items[barcode]["qty"] += 1
        else:
            self.cart_items[barcode] = {
                "name": product["name"],
                "price": product["price"],
                "qty": 1
            }
        self._refresh_bill()
        self.barcode_entry.focus_set()

    def _simulate_keyboard_scan(self, barcode):
        """
        Simulates physical barcode scanning.
        Injects the keyboard keystrokes directly into the focused entry,
        which triggers the background listener's global hook.
        """
        # Focus the barcode text box in our app
        self.barcode_entry.focus_set()
        self.barcode_entry.select_range(0, tk.END)
        
        # Execute keyboard typing simulation in a small background thread to avoid GUI freeze
        self.root.after(100, lambda: self._type_digits_via_keyboard(barcode))

    def _type_digits_via_keyboard(self, barcode):
        kb_controller = keyboard.Controller()
        # Type each digit simulating scanner speed
        for char in barcode:
            kb_controller.press(char)
            kb_controller.release(char)
            time.sleep(0.01)
        # Type Enter to process scan
        kb_controller.press(keyboard.Key.enter)
        kb_controller.release(keyboard.Key.enter)

    def _on_barcode_enter(self, event):
        """Triggered when the user scans/types a barcode and hits Enter in the entry box."""
        barcode = self.barcode_var.get().strip()
        self.barcode_var.set("") # Clear input field
        
        if barcode:
            product = db_manager.get_product(barcode)
            if product:
                self._add_product_directly(barcode)
            else:
                messagebox.showwarning("Produto não cadastrado", f"Código {barcode} não encontrado no banco de dados.")

    def _refresh_bill(self):
        # Clear treeview items
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
            
        total_sum = 0.0
        for barcode, details in self.cart_items.items():
            item_total = details["price"] * details["qty"]
            total_sum += item_total
            
            self.items_tree.insert(
                "", 
                tk.END, 
                values=(
                    details["name"], 
                    f"R$ {details['price']:.2f}", 
                    details["qty"], 
                    f"R$ {item_total:.2f}"
                )
            )
            
        self.total_label.configure(text=f"R$ {total_sum:.2f}")

    def _clear_cart(self):
        self.cart_items.clear()
        self._refresh_bill()
        self.barcode_entry.focus_set()

    def _finalize_sale(self):
        """Finalizes the sale by simulating the F12 keyboard press."""
        if not self.cart_items:
            messagebox.showwarning("Carrinho Vazio", "Adicione itens antes de finalizar a venda.")
            return
            
        # Simulate F12 key press globally.
        # This will trigger the background listener to intercept, save the sale, and show popup!
        kb_controller = keyboard.Controller()
        kb_controller.press(keyboard.Key.f12)
        kb_controller.release(keyboard.Key.f12)
        
        # Give a small delay and clear our local cart as the purchase is finalized
        self.root.after(300, self._clear_cart)

    def _on_f12_press(self, event):
        # If F12 pressed directly on the focused window, trigger finalization too
        self._finalize_sale()

if __name__ == "__main__":
    print("Iniciando Simulador de PDV Virtual...")
    SimulatorApp()
