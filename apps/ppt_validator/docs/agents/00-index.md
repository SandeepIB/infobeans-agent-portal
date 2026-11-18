# Agent Documents Index

| Agent | Type | Document |
|-------|------|----------|
| (all agents) | — | [agent-contract.md](agent-contract.md) — standard output contract |
| (all agents) | — | [agent-registry.md](agent-registry.md) — registry schema |
| Content Agent | llm | [content-agent.md](content-agent.md) |
| Story Agent | llm | [story-agent.md](story-agent.md) |
| Customer Focus Agent | llm | [customer-agent.md](customer-agent.md) |
| CIO Lens | llm | [cio-lens.md](cio-lens.md) |
| Proposal Context Agent | llm | [proposal-agent.md](proposal-agent.md) |
| Critic Agent | llm | [critic-agent.md](critic-agent.md) |
| Fix Agent | hybrid | [fix-agent.md](fix-agent.md) |
| Slide Design Match | rule | [slide-design-match.md](slide-design-match.md) |

## Adding a New Agent

See: [../development/adding-agent.md](../development/adding-agent.md)

## Common Patterns

All agents:
- Return the [Standard Agent Contract](agent-contract.md)
- Read prompts from [Prompt Library](../prompts/prompt-lifecycle.md)
- Read rules from [Rule Library](../rules/rule-library.md)
- Use `MockProvider` in tests
- Declare their context scope in the Agent Registry
