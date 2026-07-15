from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local segmentation labeler")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Segmentation Labeler is available at http://{args.host}:{args.port}")
    uvicorn.run("seglabeler.api:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
