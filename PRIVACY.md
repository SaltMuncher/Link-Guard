# Privacy

## Network

The program has no code that opens network connections. A test scans the sources for network modules. The single running instance is found through a Unix socket or Windows named pipe in the user's own folders, protected by a random key (`ipc.key`). It only understands ping, show and quit.

## What is stored

| Data | Where | Notes |
| --- | --- | --- |
| Settings | `config.json` | yes/no switches |
| Custom rules | `custom_rules.json` | written by you |
| IPC key | `ipc.key` | random |
| Debug log | `linkguard.log` | off by default, trimmed at 1 MB, event type and site name only, never full links |
| History | memory only | never written to disk, cleared with Clear history, by turning it off, or when the program quits |

The clipboard is read only to see if it holds a single http or https link. Anything else is ignored.

## Limits

- A link with no known tracking is reported as clean, not as safe.
- Short links are flagged, never expanded.
- Known redirect wrappers (for example `l.facebook.com`) are replaced by the destination written inside the link. Other apparent redirects are flagged only.
- Pop-ups request the foreground and stay on top where the system allows it. Full-screen apps and Wayland desktops can refuse, and then a notification (Linux) or taskbar flash (Windows) is used.
