"""
setup.py — Register all Managed Agents and create the shared Environment.

Run once before using any session scripts. Persists agent/environment IDs
to agent_config.json (gitignored).

To add a new agent: create agents/<name>_agent.py and import it here.
"""

import json
import os

from dotenv import load_dotenv
import anthropic

# Import agent definitions
from agents import readset_agent
from agents import design_agent

load_dotenv()

client = anthropic.Anthropic()

# ── Agents to register ────────────────────────────────────────────────────────
# Each entry is a module with NAME, MODEL, TOOLS, and SYSTEM_PROMPT defined.
AGENT_MODULES = [
    readset_agent,
    design_agent,
    # monitor_agent,
]

# ── Create environment ────────────────────────────────────────────────────────
print("Creating Environment...")
environment = client.beta.environments.create(
    name="rnaseq-env",
    config={"type": "cloud", "networking": {"type": "unrestricted"}},
)
print(f"  Environment ID: {environment.id}")

# ── Register agents ───────────────────────────────────────────────────────────
config = {
    "environment_id": environment.id,
    "environment_name": environment.name,
    "agents": {},
}

for module in AGENT_MODULES:
    print(f"\nCreating agent: {module.NAME}...")
    agent = client.beta.agents.create(
        name=module.NAME,
        model=module.MODEL,
        system=module.SYSTEM_PROMPT,
        tools=module.TOOLS,
    )
    print(f"  Agent ID: {agent.id}")
    config["agents"][module.NAME] = {
        "id": agent.id,
        "version": agent.version,
        "name": agent.name,
    }

# ── Write config ──────────────────────────────────────────────────────────────
config_path = os.path.join(os.path.dirname(__file__), "agent_config.json")
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"\nConfig written to {config_path}")
print("Done.")