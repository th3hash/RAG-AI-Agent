# Attack Surface Map

This repository combines the Module 4 RAG pipeline with the Module 5 agent/tool loop.

| Pipeline stage | What lives here | Security topic |
|---|---|---|
| System prompt | Agent instructions and tool-use rules | System prompt leakage |
| Document store | PDF, chunks, embeddings, vector DB | Data / RAG poisoning |
| User question | Raw user-controlled input | Injection / jailbreaks / filter evasion |
| Tool calls | `search_documents`, `calculator` | Excessive agency |
| Tool results | Text returned by tools | Indirect prompt injection |
| Final answer | Model output | Sensitive information disclosure |

## Why the combined system matters

The agent can now act on information retrieved from the document store. This creates an additional boundary between:

```text
User
  ↓
Agent
  ↓
Tool
  ↓
Tool result
  ↓
Agent
  ↓
Final answer
```

The security exercises in later modules can use this locally controlled system as the target.

Only test systems and documents you own or have explicit authorization to test.


---
**Project by:** Hassan Ansari — [@trickyhash](https://instagram.com/trickyhash) · [@th3hash](https://github.com/th3hash)
