import os
import sys

# Ensure project root is in path for all relative imports
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def print_usage():
    print("=" * 60)
    print("               PDVAPP - SUITE INTELEGENTE DE PDV")
    print("=" * 60)
    print("\nModo de uso:")
    print("  python main.py             -> Abre o Simulador de PDV Virtual (Interface Gráfica)")
    print("  python main.py --listener  -> Inicia o interceptador de teclado em segundo plano")
    print("  python main.py --notify <ids> -> Dispara a janela de sugestão visual (uso interno)")
    print("\nExemplo:")
    print("  python main.py --notify 1001 1002")
    print("=" * 60)

def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == "--listener":
            from core.listener import run_listener
            run_listener()
            
        elif mode == "--notify":
            # Extract product IDs (ignore other flags)
            product_ids = [arg for arg in sys.argv[2:] if not arg.startswith('--')]
            if not product_ids:
                print("[ERRO] O parâmetro --notify precisa receber códigos de barras (ex: --notify 1001 1002)")
                sys.exit(1)
            
            from ui.notification_window import NotificationWindow
            NotificationWindow(product_ids)
            
        elif mode in ("--help", "-h"):
            print_usage()
            
        else:
            print(f"[ERRO] Modo de execução desconhecido: {mode}")
            print_usage()
            sys.exit(1)
    else:
        # Default mode: launch the GUI simulator
        from ui.simulator_app import SimulatorApp
        SimulatorApp()

if __name__ == "__main__":
    main()
