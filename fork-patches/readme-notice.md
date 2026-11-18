<!-- fork-notice:start -->
> [!NOTE]
> **This is the JokerGermany fork of [noiwid/HAFamilyLink](https://github.com/noiwid/HAFamilyLink).**
> `main` is rebuilt automatically every day: latest upstream `main` + the patches on the [`fork-patches`](https://github.com/JokerGermany/HAFamilyLink/tree/fork-patches) branch. Everything below this box is the upstream README, unchanged; its links, badges and install buttons point to upstream.
> The fork adds a Steam login to the auth service. It is needed by **[SteamPlaytime](https://github.com/JokerGermany/SteamPlaytime)** (Steam playtime and parental controls from Home Assistant). Upstream declined to include it ([PR #106](https://github.com/noiwid/HAFamilyLink/pull/106): Steam is a separate platform and does not belong in a Family Link integration), which is why this fork exists. Please report problems with the Steam additions here, not upstream.

## Fork additions: Steam login in the auth service

The auth service (`familylink-playwright/`) gets an extra Steam login that stores the Steam session cookies (optionally unlocked with the Steam Family View / parental PIN) to `STEAM_STATE_FILE`. The [SteamPlaytime](https://github.com/JokerGermany/SteamPlaytime) scripts read that file and call `POST /api/steam/login` when the session needs a refresh. The Home Assistant integration itself is not changed.

| Endpoint | Purpose |
|----------|---------|
| `GET /api/steam/health` | Whether Steam support is on, where the state file is, when cookies were last saved |
| `POST /api/steam/login` | Opens Chromium on the Steam store (watch and log in through the noVNC view), waits until the session cookies exist, saves them |
| `GET /api/steam/cookies` | The saved cookies, values shortened to 8 characters |

| Environment variable | Default | Meaning |
|----------------------|---------|---------|
| `STEAM_ENABLED` | `true` | `false` makes `/api/steam/login` answer 404 |
| `STEAM_PROFILE_DIR` | `/share/steam-auth/profile` | Persistent Chromium profile, so a later login reuses the session |
| `STEAM_STATE_FILE` | `/share/steam-auth/steam-state.json` | Where the cookies are written |
| `STEAM_LOGIN_TIMEOUT` | `300` | Seconds to wait for the login |
| `STEAM_REQUIRE_PARENTAL` | `false` | Also wait for the Family View cookie (`steamparental` or `steamMachineAuth*`) |
| `STEAM_PARENTAL_PIN` | empty | If set (with `STEAM_REQUIRE_PARENTAL=true`), the PIN is entered automatically |

**Use it with the standalone container of this fork:** `ghcr.io/jokergermany/familylink-auth:standalone`, or build it yourself from `familylink-playwright/Dockerfile.standalone`. Mount a folder for the Steam data, e.g. `-v /path/to/homeassistant/config/steam-auth:/share/steam-auth:rw`, so Home Assistant sees the state file as `/config/steam-auth/steam-state.json`. A complete Podman/systemd unit is in the [SteamPlaytime README](https://github.com/JokerGermany/SteamPlaytime#readme). The Home Assistant add-on still pulls upstream's image (`ghcr.io/noiwid/familylink-auth`) and has no Steam options, so it does not contain the Steam login.

> **Security.** The Steam endpoints are not behind the `API_KEY` that protects `/api/cookies`, and the state file holds a full Steam session. Keep port 8099 on your LAN only, as for the Google login.

---
<!-- fork-notice:end -->
