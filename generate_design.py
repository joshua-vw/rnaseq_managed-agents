"""
generate_design.py — Start a Managed Agents session to generate a GenPipes design file.

Usage:
    python generate_design.py --readset readset.tsv [--output design.tsv]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import anthropic

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "agent_config.json"
AGENT_NAME = "rnaseq-design-generator"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit("agent_config.json not found. Run setup.py first.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def extract_tsv(text: str) -> str | None:
    match = re.search(r"```design\.tsv\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```(?:tsv)?\s*\n(Sample\tContrast.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def stream_agent_response(
    client: anthropic.Anthropic,
    session_id: str,
    user_text: str,
    seen_event_ids: set,  # persisted across calls
) -> str:
    client.beta.sessions.events.send(
        session_id=session_id,
        events=[
            {
                "type": "user.message",
                "content": [{"type": "text", "text": user_text}],
            }
        ],
    )

    full_response = ""

    while True:
        response = client.beta.sessions.events.list(
            session_id=session_id,
            order="asc",
            limit=100,
        )

        done = False
        for event in response.data:
            if event.id in seen_event_ids:
                continue
            seen_event_ids.add(event.id)

            if event.type == "agent.message":
                for block in event.content:
                    if hasattr(block, "text"):
                        print(block.text, end="", flush=True)
                        full_response += block.text
            elif event.type in {"session.status_idle", "session.status_terminated"}:
                print()
                done = True
                break

        if done:
            return full_response

        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a GenPipes design TSV via Managed Agents."
    )
    parser.add_argument("--readset", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("design.tsv"))
    args = parser.parse_args()

    if not args.readset.exists():
        sys.exit(f"Readset file not found: {args.readset}")

    config = load_config()
    if AGENT_NAME not in config["agents"]:
        sys.exit(f"Agent '{AGENT_NAME}' not found in agent_config.json. Run setup.py.")

    agent_cfg = config["agents"][AGENT_NAME]
    environment_id = config["environment_id"]
    client = anthropic.Anthropic()

    readset_content = args.readset.read_text(encoding="utf-8")
    print(f"Loaded readset: {args.readset.resolve()}")

    print(f"\nOpening session with agent {agent_cfg['id']}...")
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": agent_cfg["id"], "version": agent_cfg["version"]},
        environment_id=environment_id,
    )
    print(f"  Session ID: {session.id}\n")

    initial_message = (
        "Here is the readset TSV. Please parse it, show me the readsets you found, "
        "then ask me how to assign them to contrast groups.\n\n"
        f"```readset.tsv\n{readset_content}\n```"
    )

    print("=" * 70)
    print("AGENT")
    print("=" * 70)

    # seen_event_ids persists for the entire session
    seen_event_ids: set[str] = set()

    full_response = stream_agent_response(client, session.id, initial_message, seen_event_ids)
    print("\n")

    tsv_content = extract_tsv(full_response)

    while tsv_content is None:
        try:
            user_input = input("YOU > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended by user.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("Exiting session.")
            break

        print("\n" + "=" * 70)
        print("AGENT")
        print("=" * 70)

        full_response = stream_agent_response(client, session.id, user_input, seen_event_ids)
        print("\n")
        tsv_content = extract_tsv(full_response)

    if tsv_content:
        args.output.write_text(tsv_content + "\n", encoding="utf-8")
        print(f"✓ Design TSV written to {args.output.resolve()}")
        lines = tsv_content.splitlines()
        if len(lines) >= 2:
            contrasts = {line.split("\t")[1] for line in lines[1:] if "\t" in line}
            print(f"  ✓ {len(lines) - 1} readset row(s), {len(contrasts)} contrast group(s): {', '.join(sorted(contrasts))}")
    else:
        print("No design TSV was extracted from the session. Check the conversation above.")


if __name__ == "__main__":
    main()