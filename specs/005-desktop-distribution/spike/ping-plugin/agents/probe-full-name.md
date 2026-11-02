---
name: probe-full-name
description: Spike probe. Use to check whether a plugin subagent can call the ping tool listed by its full name
model: inherit
tools: mcp__plugin_spike-ping_ping__ping
---

Call the `ping` tool once and reply with exactly its result. If the tool is not
available to you, reply "ping not available" and list the tools you do have.
