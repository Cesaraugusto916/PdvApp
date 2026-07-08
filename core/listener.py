import os
import sys
import time
import subprocess
from pynput import keyboard
from database import db_manager

# Listener State
digit_buffer = []
last_key_time = 0
current_basket = []

# Constants
KEY_TIMEOUT = 1.5  # Seconds of inactivity before clearing buffer

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def launch_notification(basket_items):
    """Launches the notification window as a separate non-blocking process."""
    root_dir = get_project_root()
    main_path = os.path.join(root_dir, "main.py")
    
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        args = [sys.executable, "--notify"] + basket_items
    else:
        # Running as python script
        args = [sys.executable, main_path, "--notify"] + basket_items
        
    try:
        # Use CREATE_NO_WINDOW on Windows to prevent console flashing
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.Popen(args, creationflags=creationflags)
        print(f"\n[SISTEMA] Notificação visual disparada para os itens: {basket_items}")
    except Exception as e:
        print(f"\n[ERRO] Falha ao abrir notificação: {e}")

def on_press(key):
    global digit_buffer, last_key_time, current_basket
    
    current_time = time.time()
    
    # Auto-reset buffer if inactive for too long
    if current_time - last_key_time > KEY_TIMEOUT:
        digit_buffer.clear()
        
    last_key_time = current_time

    try:
        # 1. Capture numbers
        if hasattr(key, 'char') and key.char is not None:
            if key.char.isdigit():
                digit_buffer.append(key.char)
            else:
                # Clear buffer on non-digits to avoid mixing letters/numbers
                digit_buffer.clear()
                
        # 2. Capture Enter (verify barcode)
        elif key == keyboard.Key.enter:
            barcode = "".join(digit_buffer)
            digit_buffer.clear()
            
            if barcode:
                # Check if it's a valid product in the database
                product = db_manager.get_product(barcode)
                if product:
                    current_basket.append(barcode)
                    print(f"\n[BIP] Código Lido: {barcode} | Produto: {product['name']} | R$ {product['price']:.2f}")
                    print(f"      Carrinho Atual ({len(current_basket)} itens): {current_basket}")
                else:
                    # Ignore, was probably some other number entry
                    pass
                    
        # 3. Capture F12 (finalize sale)
        elif key == keyboard.Key.f12:
            if current_basket:
                print(f"\n[VENDA] Finalizando venda com {len(current_basket)} itens...")
                # Save to database
                sale_id = db_manager.save_sale(current_basket)
                if sale_id:
                    print(f"      Venda gravada no banco de dados. ID: {sale_id}")
                
                # Launch notification window with the list of items
                launch_notification(current_basket)
                
                # Reset current sale basket
                current_basket.clear()
            else:
                print("\n[AVISO] Tentativa de finalizar venda, mas o carrinho está vazio.")
                
    except Exception as e:
        print(f"\n[ERRO] Ocorreu uma exceção no listener: {e}")

def run_listener():
    """Starts the global keyboard hook listener."""
    db_manager.init_db()
    print("=" * 60)
    print("                PDVAPP - BACKGROUND LISTENER")
    print("=" * 60)
    print("[INFO] Iniciando capturador global de entradas...")
    print("[INFO] Escaneie códigos de barra no seu PDV ou digite os IDs (ex: 1001 + Enter).")
    print("[INFO] Pressione F12 para finalizar a venda e gerar recomendações.")
    print("[INFO] Pressione Ctrl+C nesta janela para encerrar.")
    print("-" * 60)
    
    # Start the listener in the main thread (blocking)
    with keyboard.Listener(on_press=on_press) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\n[SISTEMA] Encerrando Listener em background...")

if __name__ == "__main__":
    run_listener()
