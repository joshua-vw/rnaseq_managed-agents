"""
generate_readset.py — Start a Managed Agents session to generate a GenPipes readset file.

Usage:
    python generate_readset.py --fastq-dir /path/to/fastq/root [--metadata /path/to/meta1.json ...] [--include _3M] [--exclude _3M]

The script:
  1. Recursively scans --fastq-dir for *.fastq.gz (and .fastq, .fq.gz, .fq) files.
  2. Optionally filters files by --include or --exclude string patterns.
  3. Reads any provided metadata files (ENCODE JSON, Nanuq CSV, or plain text).
  4. Opens a Managed Agents session and sends everything to the readset-generator agent.
  5. Runs an interactive loop so you can answer the agent's clarifying questions.
  6. Writes the final readset.tsv to --output (default: ./readset.tsv).
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

# ── Config ─────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "agent_config.json"
FASTQ_EXTENSIONS = {".fastq.gz", ".fastq", ".fq.gz", ".fq"}


# ── Helpers ─────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(
            "agent_config.json not found. Run setup.py first to create the agent and environment."
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def scan_fastq_files(root: Path, include: str = None, exclude: str = None) -> list[str]:
    """Recursively find all FASTQ files under root, sorted.

    Args:
        include: Only include files whose filename contains this string (e.g. '_3M').
        exclude: Exclude files whose filename contains this string (e.g. '_3M').
    """
    found = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            suffixes = "".join(path.suffixes)
            if suffixes in FASTQ_EXTENSIONS or path.suffix in FASTQ_EXTENSIONS:
                if include and include not in path.name:
                    continue
                if exclude and exclude in path.name:
                    continue
                found.append(str(path.resolve()))
    return found


def read_metadata_file(path: Path) -> str:
    """Read a metadata file and return its contents as a labelled string.

    For JSON files, strips large keys that are not useful for readset generation
    to keep the message size within context window limits.
    """
    # Keys to strip from ENCODE experiment JSONs — large and not needed for readset generation
    ENCODE_KEYS_TO_DROP = {
        "files",           # 864 KB of file download URLs — FASTQ paths come from directory scan
        "analyses",        # processed data references
        "related_series",  # links to other experiments
    }

    try:
        content = path.read_text(encoding="utf-8")

        if path.suffix == ".json":
            try:
                data = json.loads(content)
                original_size = len(content)
                for key in ENCODE_KEYS_TO_DROP:
                    data.pop(key, None)
                content = json.dumps(data, indent=2)
                trimmed_size = len(content)
                dropped_kb = (original_size - trimmed_size) / 1024
                if dropped_kb > 1:
                    print(f"  Trimmed {path.name}: removed {dropped_kb:.0f} KB of unused fields.")
            except json.JSONDecodeError:
                pass  # not valid JSON, send as-is

        return f"--- Metadata file: {path.name} ---\n{content}\n"
    except Exception as e:
        return f"--- Metadata file: {path.name} [ERROR reading: {e}] ---\n"


def build_initial_message(fastq_files: list[str], metadata_blocks: list[str]) -> str:
    """Construct the opening user message for the agent session."""
    lines = [
        "Please generate a GenPipes readset TSV for the following dataset.\n",
        "## FASTQ files found\n",
    ]
    for f in fastq_files:
        lines.append(f"  {f}")
    lines.append("")

    if metadata_blocks:
        lines.append("## Metadata files\n")
        for block in metadata_blocks:
            lines.append(block)
    else:
        lines.append(
            "No metadata files were provided. "
            "Please infer what you can from filenames and ask me about anything unclear.\n"
        )

    lines.append(
        "\nPlease follow your interaction protocol: "
        "report your inferences, flag ambiguities, ask any questions you need, "
        "then output the final readset TSV."
    )
    return "\n".join(lines)


def extract_tsv(text: str) -> str | None:
    """Extract content from a ```readset.tsv ... ``` fenced block, if present."""
    match = re.search(r"```readset\.tsv\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: any TSV-looking fenced block starting with the Sample header
    match = re.search(r"```(?:tsv)?\s*\n(Sample\t.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def stream_agent_response(client: anthropic.Anthropic, session_id: str, user_text: str) -> str:
    """Send a user message, poll for events, and return the full response text."""

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
    seen_event_ids = set()

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
            print(f"  [DEBUG] event: {event.type} {event.id}")
            if event.type == "session.error":
                print(f"  [ERROR DETAIL] {event}")

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


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate a GenPipes readset TSV via Managed Agents.")
    parser.add_argument(
        "--fastq-dir",
        required=True,
        type=Path,
        help="Root directory to scan for FASTQ files (searched recursively).",
    )
    parser.add_argument(
        "--metadata",
        nargs="*",
        type=Path,
        default=[],
        help="Optional metadata files (ENCODE JSON, Nanuq CSV, etc.).",
    )
    parser.add_argument(
        "--include",
        type=str,
        default=None,
        help="Only include FASTQ files whose filename contains this string (e.g. '_3M').",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default=None,
        help="Exclude FASTQ files whose filename contains this string (e.g. '_3M').",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("readset.tsv"),
        help="Where to write the final readset TSV (default: ./readset.tsv).",
    )
    args = parser.parse_args()

    # ── Validate inputs ─────────────────────────────────────────────────────────
    if not args.fastq_dir.is_dir():
        sys.exit(f"--fastq-dir does not exist or is not a directory: {args.fastq_dir}")

    for meta in args.metadata:
        if not meta.exists():
            sys.exit(f"Metadata file not found: {meta}")

    if args.include and args.exclude:
        sys.exit("--include and --exclude cannot be used together.")

    # ── Load config ─────────────────────────────────────────────────────────────
    config = load_config()
    agent_config = config["agents"]["rnaseq-readset-generator"]
    agent_id = agent_config["id"]
    agent_version = agent_config["version"]
    environment_id = config["environment_id"]

    client = anthropic.Anthropic()

    # ── Scan FASTQ files ────────────────────────────────────────────────────────
    print(f"Scanning {args.fastq_dir} for FASTQ files...")
    if args.include:
        print(f"  Filter: including only files containing '{args.include}'")
    if args.exclude:
        print(f"  Filter: excluding files containing '{args.exclude}'")

    fastq_files = scan_fastq_files(args.fastq_dir, include=args.include, exclude=args.exclude)
    if not fastq_files:
        sys.exit("No FASTQ files found. Check the --fastq-dir path and any --include/--exclude filters.")
    print(f"  Found {len(fastq_files)} FASTQ file(s).")

    # ── Read metadata ────────────────────────────────────────────────────────────
    metadata_blocks = [read_metadata_file(m) for m in args.metadata]
    if metadata_blocks:
        print(f"  Loaded {len(metadata_blocks)} metadata file(s).")

    # ── Open session ─────────────────────────────────────────────────────────────
    print(f"\nOpening session with agent {agent_id}...")
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": agent_id, "version": agent_version},
        environment_id=environment_id,
    )
    print(f"  Session ID: {session.id}\n")

    # ── First turn ───────────────────────────────────────────────────────────────
    initial_message = build_initial_message(fastq_files, metadata_blocks)

    print("=" * 70)
    print("AGENT")
    print("=" * 70)

    full_response = stream_agent_response(client, session.id, initial_message)
    print("\n")

    # ── Interactive loop ─────────────────────────────────────────────────────────
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

        full_response = stream_agent_response(client, session.id, user_input)
        print("\n")
        tsv_content = extract_tsv(full_response)

    # ── Write output ─────────────────────────────────────────────────────────────
    if tsv_content:
        args.output.write_text(tsv_content + "\n", encoding="utf-8")
        print(f"✓ Readset TSV written to {args.output.resolve()}")

        # Quick validation: check column count on first data row
        lines = tsv_content.splitlines()
        if len(lines) >= 2:
            header_cols = lines[0].count("\t") + 1
            data_cols = lines[1].count("\t") + 1
            if header_cols != data_cols:
                print(
                    f"  ⚠ Column count mismatch: header has {header_cols}, "
                    f"first data row has {data_cols}. Review the output."
                )
            else:
                print(f"  ✓ {header_cols} columns, {len(lines) - 1} readset row(s).")
    else:
        print("No readset TSV was extracted from the session. Check the conversation above.")


if __name__ == "__main__":
    main()