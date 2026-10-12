"""Start the Buyora website + API:   python run.py"""
import argparse

from app import create_app


def main():
    parser = argparse.ArgumentParser(description="Run the Buyora store (website + API).")
    parser.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to open it to other devices on your network")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--reset", action="store_true",
                        help="drop and recreate all Buyora tables (deletes all data)")
    args = parser.parse_args()

    app = create_app({"RESET_DATABASE": args.reset})
    if args.reset:
        print("MySQL tables reset.")
    print("\n  Buyora is running")
    print(f"  Website : http://localhost:{args.port}")
    print(f"  API     : http://localhost:{args.port}/api/health")
    print(f"  Admin   : {app.config['ADMIN_EMAIL']}  /  {app.config['ADMIN_PASSWORD']}   (change this!)")
    print("  Stop    : press Ctrl + C\n")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
