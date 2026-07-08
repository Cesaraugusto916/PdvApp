import os
import sys
import subprocess
import PyInstaller.__main__

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def build():
    print("=" * 60)
    # 1. Verify environment
    main_path = os.path.join(PROJECT_ROOT, "main.py")
    if not os.path.exists(main_path):
        print(f"[ERRO] Arquivo principal '{main_path}' não encontrado.")
        sys.exit(1)
        
    print("[INFO] Iniciando processo de empacotamento do PdvApp...")
    print(f"[INFO] Pasta do projeto: {PROJECT_ROOT}")
    
    # 2. PyInstaller Arguments
    pyinstaller_args = [
        main_path,
        "--onefile",
        "--name=PdvApp",
        # Bundle data folder inside the executable
        # Format is "source;destination" on Windows
        f"--add-data={os.path.join(PROJECT_ROOT, 'data')}{os.pathsep}data",
        # Explicitly declare pynput platform hook modules
        "--hidden-import=pynput.keyboard._win32",
        "--hidden-import=pynput.mouse._win32",
        # Clean cache
        "--clean",
    ]
    
    print(f"[INFO] Parâmetros de compilação: {pyinstaller_args}")
    
    # 3. Execute compilation
    try:
        PyInstaller.__main__.run(pyinstaller_args)
        print("\n" + "=" * 60)
        print("[SUCESSO] COMPILACAO CONCLUIDA COM SUCESSO!")
        print("=" * 60)
        print(f"O executável foi gerado em: {os.path.join(PROJECT_ROOT, 'dist', 'PdvApp.exe')}")
        print("Para testar:")
        print("  1. Inicie o Listener em uma janela de comando:")
        print("     .\\dist\\PdvApp.exe --listener")
        print("  2. Em outra janela, abra o Simulador:")
        print("     .\\dist\\PdvApp.exe")
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERRO] Ocorreu uma falha durante o empacotamento: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
