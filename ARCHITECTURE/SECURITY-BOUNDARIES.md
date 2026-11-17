# Security boundaries

Only explicit sources are authorized. Never silently capture passwords, private messages, browser sessions, keystrokes or unrelated content. Display active data sources and source permissions.

Treat JSON, text, source code and AI output as untrusted. Limit bytes, events, nesting where practical, numeric ranges, subprocess time, queue depth and memory. Avoid shell interpolation and arbitrary commands from data. Bind any future local server to loopback and authenticate state-changing operations.

Separate private runtime state from public repository evidence. Review exports before publishing. Never store tokens in source or logs. Do not change working credentials.

Limit benchmarks, allow cancellation, preserve graphics headroom and forbid overlapping resource-heavy runs. Preserve sibling projects and existing installations. Use transactions for database writes and temporary-file replacement for important exports.
