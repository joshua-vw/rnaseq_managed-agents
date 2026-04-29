from dotenv import load_dotenv
import anthropic
import json

load_dotenv()

client = anthropic.Anthropic()

# Create the agent (do this once, save the ID)
agent = client.beta.agents.create(
    name="rnaseq-monitor",
    model="claude-sonnet-4-6",
    system="You are a helpful assistant monitoring an RNA-seq pipeline.",
    tools=[{"type": "agent_toolset_20260401"}],
)

# Create the environment (do this once, save the ID)
environment = client.beta.environments.create(
    name="rnaseq-env",
    config={"type": "cloud", "networking": {"type": "unrestricted"}},
)

# Save IDs to a file so other scripts can use them
ids = {
    "agent_id": agent.id,
    "agent_version": agent.version,
    "environment_id": environment.id,
}

with open("agent_config.json", "w") as f:
    json.dump(ids, f, indent=2)

print(f"Agent ID: {agent.id}")
print(f"Environment ID: {environment.id}")
print("Saved to agent_config.json")