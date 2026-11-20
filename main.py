"""Arranque de Nexo TI. Python 3.11+, sin dependencias de terceros."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Nexo TI · Mesa de soporte")
    parser.add_argument("--demo", action="store_true", help="Usar un espacio de demostración independiente")
    parser.add_argument("--data-dir", type=Path, help="Directorio de datos alternativo")
    args = parser.parse_args()
    from nexo.storage import Store, default_data_dir
    directory = args.data_dir or default_data_dir(args.demo)
    store = Store(directory)
    if args.demo:
        from nexo.demo import seed_demo
        seed_demo(store)
    try:
        from nexo.ui import App
        App(store, demo=args.demo).mainloop()
    finally:
        store.close()


if __name__ == "__main__":
    main()
