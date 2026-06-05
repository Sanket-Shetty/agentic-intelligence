from __future__ import annotations

import argparse

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from agent.core import TransactionIntelligenceAgent


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Build a transaction intelligence report.")
    parser.add_argument("input", help="Transaction hash or user wallet address")
    parser.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="OpenAI model to use for function calling",
    )
    args = parser.parse_args()

    agent = TransactionIntelligenceAgent(model=args.model)
    report = agent.run(args.input)

    console = Console()
    console.print(Markdown(report))


if __name__ == "__main__":
    main()
