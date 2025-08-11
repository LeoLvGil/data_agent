import argparse
import sys

from .agent import create_session, chat_once


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the data agent from the command line.")
    parser.add_argument("--prompt", type=str, default=None, help="Single-turn user prompt. If omitted, enter interactive chat mode.")
    parser.add_argument("--interactive", action="store_true", help="Force interactive mode even if --prompt is provided.")
    parser.add_argument("--df_name", type=str, default="df", help="DataFrame variable name to store loaded CSV.")
    parser.add_argument("--csv_path", type=str, default=None, help="Local CSV file path to preload.")
    parser.add_argument("--csv_url", type=str, default=None, help="Direct URL of CSV (e.g., presigned).")
    parser.add_argument("--csv_b64", type=str, default=None, help="Base64-encoded CSV bytes to preload.")
    parser.add_argument("--csv_text", type=str, default=None, help="Raw CSV text to preload.")
    parser.add_argument("--sep", type=str, default=None, help="CSV delimiter (default: auto-detect).")
    parser.add_argument("--encoding", type=str, default=None, help="CSV encoding (default: pandas guess).")
    parser.add_argument("--images_dir", type=str, default=None, help="Directory to save figures. Overrides IMAGE_OUTPUT_DIR.")

    args = parser.parse_args(argv)

    # interactive session
    if args.interactive or not args.prompt:
        print("Interactive chat mode. Type 'exit' or 'quit' to leave.")
        session = create_session(images_dir=args.images_dir)
        if any([args.csv_path, args.csv_url, args.csv_b64, args.csv_text]):
            preload_msg = session.preload_csv(
                df_name=args.df_name,
                file_path=args.csv_path,
                file_url=args.csv_url,
                file_b64=args.csv_b64,
                csv_text=args.csv_text,
                sep=args.sep,
                encoding=args.encoding,
            )
            print(str(preload_msg))
        while True:
            try:
                user_input = input("You > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                return 0
            if user_input.lower() in {"exit", "quit"}:
                print("Bye.")
                return 0
            print(session.send(user_input))
    else:
        preload = None
        if any([args.csv_path, args.csv_url, args.csv_b64, args.csv_text]):
            preload = {
                "df_name": args.df_name,
                "file_path": args.csv_path,
                "file_url": args.csv_url,
                "file_b64": args.csv_b64,
                "csv_text": args.csv_text,
                "sep": args.sep,
                "encoding": args.encoding,
            }
        print(chat_once(args.prompt, images_dir=args.images_dir, preload=preload))
        return 0


if __name__ == "__main__":
    sys.exit(main())


