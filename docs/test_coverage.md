# NewsGuru Test Coverage Report

Generated: 2026-04-17 08:36:04

**Total: 86 tests | Passed: 86 | Failed: 0**

| # | Test | Status | Detail |
|---|------|--------|--------|
| 1 | Homepage returns 200 | PASS |  |
| 2 | 3-pane layout: left pane | PASS |  |
| 3 | 3-pane layout: right pane | PASS |  |
| 4 | 3-pane layout: chat input | PASS |  |
| 5 | Left pane: New Chat button | PASS |  |
| 6 | Left pane: Topics section | PASS |  |
| 7 | Left pane: Significance Map link | PASS |  |
| 8 | Left pane: Trending section | PASS |  |
| 9 | Left pane: Sources section | PASS |  |
| 10 | Left pane: Journalists section | PASS |  |
| 11 | Left pane: Methodology link | PASS |  |
| 12 | Left pane: About Us link | PASS |  |
| 13 | Starter cards present | PASS | found 6 (0 ok if session has history) |
| 14 | Live feed has articles | PASS | 20 items |
| 15 | Login page returns 200 | PASS |  |
| 16 | Login has email field | PASS |  |
| 17 | Register page returns 200 | PASS |  |
| 18 | Register has name field | PASS |  |
| 19 | Methodology page returns 200 | PASS |  |
| 20 | Methodology: has scoring table | PASS |  |
| 21 | Methodology: has philosophy | PASS |  |
| 22 | Methodology: has distribution | PASS |  |
| 23 | Methodology: has table of contents | PASS |  |
| 24 | Methodology: has journalist map section | PASS |  |
| 25 | Methodology: has data sources | PASS |  |
| 26 | About page returns 200 | PASS |  |
| 27 | About: has Predictive Labs | PASS |  |
| 28 | About: has transparency section | PASS |  |
| 29 | About: has significance explanation | PASS |  |
| 30 | Treemap page returns 200 | PASS |  |
| 31 | Treemap: Plotly chart rendered | PASS |  |
| 32 | Treemap: 'What is this?' link | PASS |  |
| 33 | Treemap in chat: iframe present | PASS |  |
| 34 | Treemap in chat: headlines below | PASS |  |
| 35 | Treemap in chat: share widget | PASS |  |
| 36 | Journalist chart page returns 200 | PASS |  |
| 37 | Journalist map: Plotly rendered | PASS |  |
| 38 | Journalist map in chat: iframe present | PASS |  |
| 39 | Journalist map in chat: journalist list below | PASS |  |
| 40 | Journalist map in chat: share widget | PASS |  |
| 41 | Left pane: Journalist Map link | PASS |  |
| 42 | News digest: user message shown | PASS |  |
| 43 | News digest: response present | PASS | 3 bubbles |
| 44 | News digest: no LLM text bloat | PASS |  |
| 45 | News digest: has structured sections | PASS |  |
| 46 | News digest: no error message | PASS |  |
| 47 | News digest: share widget present | PASS |  |
| 48 | Specific query: user message shown | PASS |  |
| 49 | Specific query: got response | PASS | 3 bubbles |
| 50 | Specific query: no error message | PASS |  |
| 51 | Specific query: share widget | PASS |  |
| 52 | Title: main news -> topic title | PASS | "Today's Top News" |
| 53 | Title: heatmap -> Significance Map | PASS | "Significance Map" |
| 54 | Title: journalist map | PASS | "Journalist Map" |
| 55 | Title: estonian media | PASS | "Estonian News Digest" |
| 56 | Title: business headlines | PASS | "Business Headlines" |
| 57 | Title: AI/tech | PASS | "Tech & AI News" |
| 58 | Starter caught: What are the main news today?... | PASS |  |
| 59 | Starter caught: Latest developments in AI and techn... | PASS |  |
| 60 | Starter caught: What's happening in global politics... | PASS |  |
| 61 | Starter caught: Top business and market headlines... | PASS |  |
| 62 | Starter caught: Most significant events this week... | PASS |  |
| 63 | Starter caught: What are Estonian media reporting?... | PASS |  |
| 64 | Estonian media: no error | PASS |  |
| 65 | Estonian media: has response | PASS |  |
| 66 | Topic click: fresh session (starter cards) | PASS | 6 cards |
| 67 | Topic /politics returns 200 | PASS |  |
| 68 | Topic /technology returns 200 | PASS |  |
| 69 | Invalid topic redirects | PASS | url=http://localhost:5020/topic/nonexistent |
| 70 | Story clusters table exists | PASS |  |
| 71 | Article clusters table exists | PASS |  |
| 72 | Topic modeler: get_daily_clusters works | PASS | 5 clusters |
| 73 | Chat tool: get_story_clusters registered | PASS |  |
| 74 | Chat tool: search_tavily registered | PASS |  |
| 75 | Chat tool: search_exa registered | PASS |  |
| 76 | Chat tool: get_recent_articles registered | PASS |  |
| 77 | Cluster card: renderer loads | PASS |  |
| 78 | Article cards render with related coverage field | PASS | no crash on load |
| 79 | API /api/trending returns 200 | PASS |  |
| 80 | API /api/journalists returns 200 | PASS |  |
| 81 | API /api/sources returns 200 | PASS |  |
| 82 | SSE /sse/feed returns 200 | PASS |  |
| 83 | Language switch without login redirects to /login | PASS |  |
| 84 | Mobile: tab bar visible | PASS |  |
| 85 | Mobile: left pane hidden | PASS |  |
| 86 | Session: history links present | PASS | 8 sessions |

## Test Categories

- **Page Load**: 23/23 passed
- **Authentication**: 9/9 passed
- **Static Pages**: 13/13 passed
- **Treemap**: 6/6 passed
- **Journalist Map**: 10/10 passed
- **Topic Modeling**: 3/3 passed
- **Chat**: 22/22 passed
- **Titles**: 0/0 passed
- **Fresh Sessions**: 1/1 passed
- **Navigation**: 7/7 passed
- **API**: 3/3 passed
- **SSE**: 1/1 passed
- **Language**: 1/1 passed
- **Mobile**: 2/2 passed
- **Session**: 2/2 passed

## Screenshots

All screenshots saved to `screenshots/regression/`

- [01-homepage.png](../screenshots/regression/01-homepage.png)
- [02-login.png](../screenshots/regression/02-login.png)
- [03-register.png](../screenshots/regression/03-register.png)
- [04-methodology.png](../screenshots/regression/04-methodology.png)
- [04b-about.png](../screenshots/regression/04b-about.png)
- [05-treemap-standalone.png](../screenshots/regression/05-treemap-standalone.png)
- [06-treemap-in-chat.png](../screenshots/regression/06-treemap-in-chat.png)
- [06b-journalist-standalone.png](../screenshots/regression/06b-journalist-standalone.png)
- [06c-journalist-in-chat.png](../screenshots/regression/06c-journalist-in-chat.png)
- [07-chat-response.png](../screenshots/regression/07-chat-response.png)
- [07-news-digest.png](../screenshots/regression/07-news-digest.png)
- [07b-specific-query.png](../screenshots/regression/07b-specific-query.png)
- [07c-estonian-media.png](../screenshots/regression/07c-estonian-media.png)
- [08-topic-politics.png](../screenshots/regression/08-topic-politics.png)
- [09-mobile.png](../screenshots/regression/09-mobile.png)