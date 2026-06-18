import os
import sys
import subprocess
import socket
import webbrowser
import time
import threading

def get_free_port(start_port=8501):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1

def run_streamlit_inline(port, app_path):
    import streamlit.web.bootstrap as bootstrap
    flag_options = {
        "server.port": port,
        "global.developmentMode": False,
        "browser.gatherUsageStats": False,
        "server.headless": True,
    }
    bootstrap.load_config_options(flag_options=flag_options)
    flag_options["_is_running_with_streamlit"] = True
    bootstrap.run(app_path, "streamlit run", [], flag_options)

if __name__ == "__main__":
    # Force PyInstaller to bundle modules and their dependencies
    if False:
        import app
        import analytics
        import data_loader

    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base_path, "app.py")

    # If --run-server is specified, run Streamlit server inline (mainly for PyInstaller bundle)
    if len(sys.argv) > 1 and sys.argv[1] == "--run-server":
        port = int(sys.argv[2])
        run_streamlit_inline(port, app_path)
        sys.exit(0)

    # Launcher logic
    port = get_free_port(8501)
    url = f"http://localhost:{port}"

    print("=========================================")
    print("Iniciando Dashboard Comercial MYM...")
    print(f"Puerto detectado: {port}")
    print(f"URL local: {url}")
    print("=========================================")

    # Determine command to run the server
    if is_frozen:
        cmd = [sys.executable, "--run-server", str(port)]
    else:
        # Development mode: run Python subprocess with streamlit module
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            app_path,
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ]

    # Start the streamlit server subprocess
    try:
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )
    except Exception as e:
        print(f"Error al iniciar el proceso de Streamlit: {e}")
        sys.exit(1)

    # Thread to open webbrowser after server starts up
    def open_browser():
        time.sleep(2.0)
        print("Abriendo el navegador...")
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    # Monitor output from the subprocess
    def monitor_stream(stream, name):
        for line in stream:
            print(f"[{name}] {line.strip()}")

    threading.Thread(target=monitor_stream, args=(p.stdout, "STREAMLIT"), daemon=True).start()
    threading.Thread(target=monitor_stream, args=(p.stderr, "ERROR"), daemon=True).start()

    # Keep launcher alive and monitor process life
    try:
        while True:
            ret = p.poll()
            if ret is not None:
                print(f"El proceso de Streamlit terminó con código: {ret}")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nCerrando el servidor...")
        p.terminate()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
        print("Servidor finalizado.")
