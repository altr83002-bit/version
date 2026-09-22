# TokenKeeper

Discord token keeper — stores tokens, keeps them alive forever via heartbeat loop, and exposes slash commands for management.

## Commands

| Command | What it does |
|---|---|
| `/add tokens:<paste>` | Add tokens via text paste |
| `/add file:<.txt>` | Add tokens from file upload |
| `/token start` | Launch keepalive for ALL stored tokens |
| `/token start index:3` | Start keepalive for token #3 only |
| `/token stop` | Stop all keepalives |
| `/token stop index:3` | Stop one token's keepalive |
| `/token list` | Show all tokens (masked) + alive status |
| `/token remove index:3` | Remove token #3 from storage |
| `/token clear` | Wipe everything |
| `/token export` | Download tokens.txt |
| `/token count` | Quick count + alive count |
| `/joiner invite:discord.gg/abc` | Mass join a server with all tokens |
| `/joiner invite:... limit:50 delay:1200` | Join with cap + custom delay |
| `/leave guild_id:123456789` | Make all tokens leave a guild |
| `/utilities status` | Overall keeper health |
| `/utilities ping` | Check which tokens are valid/dead |
| `/utilities info` | Fetch username/nitro/verified for each token |
| `/utilities nitro` | List only tokens with active Nitro |

## Railway Deploy

1. Fork/push this repo to GitHub
2. New project on Railway → deploy from GitHub
3. Set environment variables:
   - `DISCORD_TOKEN` — your bot token
   - `OWNER_IDS` — your Discord user ID(s), comma separated
4. **Add a Volume** at `/data` so tokens survive redeploys
5. Set `DATA_DIR=/data` in Railway env vars
6. Deploy — bot auto-starts keepalive for all stored tokens on boot

## How Keepalive Works

Every stored token fires `GET /api/v10/users/@me` every 4 minutes (configurable via `KEEPALIVE_INTERVAL_S`). This counts as activity, keeps the session considered online, and auto-removes tokens that return 401 (dead/banned). All sessions run as concurrent asyncio tasks — no blocking, no thread overhead. Deploy stays live as long as Railway is running.
