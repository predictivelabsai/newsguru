# NewsGuru Test Coverage Report

Generated: 2026-04-17 07:32:48

**Total: 60 tests | Passed: 60 | Failed: 0**

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
| 42 | Chat: user message shown | PASS |  |
| 43 | Chat: assistant response present | PASS | 2 responses |
| 44 | Chat: share widget present | PASS |  |
| 45 | Topic /politics returns 200 | PASS |  |
| 46 | Topic /technology returns 200 | PASS |  |
| 47 | Invalid topic redirects | PASS | url=http://localhost:5020/topic/nonexistent |
| 48 | Story clusters table exists | PASS |  |
| 49 | Article clusters table exists | PASS |  |
| 50 | Topic modeler: get_daily_clusters works | PASS | 5 clusters |
| 51 | Chat tool: get_story_clusters registered | PASS |  |
| 52 | Article cards render with related coverage field | PASS | no crash on load |
| 53 | API /api/trending returns 200 | PASS |  |
| 54 | API /api/journalists returns 200 | PASS |  |
| 55 | API /api/sources returns 200 | PASS |  |
| 56 | SSE /sse/feed returns 200 | PASS |  |
| 57 | Language switch without login redirects to /login | PASS |  |
| 58 | Mobile: tab bar visible | PASS |  |
| 59 | Mobile: left pane hidden | PASS |  |
| 60 | Session: history links present | PASS | 8 sessions |

## Test Categories

- **Page Load**: 16/16 passed
- **Authentication**: 6/6 passed
- **Static Pages**: 13/13 passed
- **Treemap**: 6/6 passed
- **Journalist Map**: 9/9 passed
- **Topic Modeling**: 3/3 passed
- **Chat**: 12/12 passed
- **Navigation**: 5/5 passed
- **API**: 3/3 passed
- **SSE**: 1/1 passed
- **Language**: 1/1 passed
- **Mobile**: 2/2 passed
- **Session**: 1/1 passed

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
- [08-topic-politics.png](../screenshots/regression/08-topic-politics.png)
- [09-mobile.png](../screenshots/regression/09-mobile.png)