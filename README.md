# Football MCP Server

An MCP (Model Context Protocol) server for coordinating football/soccer pickup games. Built with [FastMCP](https://gofastmcp.com), it lets AI assistants on platforms like Discord or Telegram help players organize games, find opponents, and manage rosters.

## Features

- **Game Management** — Create, find, and manage pickup games with location, date, time, game type, and surface preferences
- **Player Profiles** — Subscribe as an available player with position, skill level, location, and availability
- **Join Requests** — Players request to join games; organizers accept or reject
- **Multi-Platform** — Supports Discord, Telegram, and other platforms via platform user IDs
- **Auto-Close** — Games automatically close when they're within 2 hours of start time

## Architecture

```
app/
├── server.py                  # MCP server with all tool definitions
├── database/
│   ├── connection.py          # PostgreSQL connection (sync + async)
│   └── models.py              # SQLAlchemy models (User, Game, GamePlayer, JoinRequest)
└── services/
    ├── game_service.py        # Game CRUD, join requests, expiration logic
    └── user_service.py        # User profiles, subscriptions, player search
```

**Stack:** FastMCP 3.x · SQLAlchemy 2.0 (async) · PostgreSQL 16 · asyncpg

## Quick Start

### 1. Start PostgreSQL

```bash
docker compose up -d
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work with docker-compose)
```

### 4. Run the server

```bash
python -m app.server
```

The server starts on `http://0.0.0.0:8000/mcp` using streamable HTTP transport.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FOOTBALLBOT_DB_HOST` | `localhost` | PostgreSQL host |
| `FOOTBALLBOT_DB_PORT` | `5433` | PostgreSQL port |
| `FOOTBALLBOT_DB_NAME` | `footballbot` | Database name |
| `FOOTBALLBOT_DB_USER` | `postgres` | Database user |
| `FOOTBALLBOT_DB_PASSWORD` | `postgres` | Database password |

## MCP Tools

### Game Management

| Tool | Description |
|---|---|
| `create_game` | Create a new game (location, date, time, type, surface, players needed) |
| `find_games` | Find open games with optional filters (location, date, position) |
| `get_game_details` | Get full game details including player roster |
| `add_player_to_game` | Organizer directly adds a player to their game |

### Join Requests

| Tool | Description |
|---|---|
| `request_to_join_game` | Player sends a join request to a game |
| `accept_join_request` | Organizer accepts a join request |
| `reject_join_request` | Organizer rejects a join request |
| `get_pending_requests` | Organizer views pending join requests for their game |

### Player Profiles

| Tool | Description |
|---|---|
| `subscribe_player` | Register as an available player with preferences |
| `update_player_profile` | Update position, skill level, location, or availability |
| `find_players` | Search for available players by filters |

## Database Models

- **User** — Platform identity, profile (position, skill, location, availability), subscription status
- **Game** — Location, date/time, type (5v5/7v7/11v11), surface, capacity, status (open/full/closed/cancelled/completed)
- **GamePlayer** — Player-game association with position and status
- **JoinRequest** — Join request with status (pending/accepted/rejected) and optional message

## MCP Client Configuration

To connect to this server from an MCP client:

```json
{
  "mcpServers": {
    "footballbot": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```
