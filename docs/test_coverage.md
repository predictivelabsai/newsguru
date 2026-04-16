# NewsGuru Test Coverage Report

Generated: 2026-04-16 21:17:41

**Total: 45 tests | Passed: 45 | Failed: 0**

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
| 12 | Starter cards present | PASS | found 6 (0 ok if session has history) |
| 13 | Live feed has articles | PASS | 20 items |
| 14 | Login page returns 200 | PASS |  |
| 15 | Login has email field | PASS |  |
| 16 | Register page returns 200 | PASS |  |
| 17 | Register has name field | PASS |  |
| 18 | Methodology page returns 200 | PASS |  |
| 19 | Methodology: has scoring table | PASS |  |
| 20 | Methodology: has philosophy | PASS |  |
| 21 | Methodology: has distribution | PASS |  |
| 22 | Treemap page returns 200 | PASS |  |
| 23 | Treemap: Plotly chart rendered | PASS |  |
| 24 | Treemap: 'What is this?' link | PASS |  |
| 25 | Treemap in chat: iframe present | PASS |  |
| 26 | Treemap in chat: headlines below | PASS |  |
| 27 | Journalist chart page returns 200 | PASS |  |
| 28 | Journalist map: Plotly rendered | PASS |  |
| 29 | Journalist map in chat: iframe present | PASS |  |
| 30 | Journalist map in chat: journalist list below | PASS |  |
| 31 | Left pane: Journalist Map link | PASS |  |
| 32 | Chat: user message shown | PASS |  |
| 33 | Chat: assistant response present | PASS | 2 responses |
| 34 | Chat: share widget present | PASS |  |
| 35 | Topic /politics returns 200 | PASS |  |
| 36 | Topic /technology returns 200 | PASS |  |
| 37 | Invalid topic redirects | PASS | url=http://localhost:5020/topic/nonexistent |
| 38 | API /api/trending returns 200 | PASS |  |
| 39 | API /api/journalists returns 200 | PASS |  |
| 40 | API /api/sources returns 200 | PASS |  |
| 41 | SSE /sse/feed returns 200 | PASS |  |
| 42 | Language switch without login redirects to /login | PASS |  |
| 43 | Mobile: tab bar visible | PASS |  |
| 44 | Mobile: left pane hidden | PASS |  |
| 45 | Session: history links present | PASS | 8 sessions |

## Test Categories

- **Page Load**: 15/15 passed
- **Authentication**: 5/5 passed
- **Static Pages**: 5/5 passed
- **Treemap**: 5/5 passed
- **Journalist Map**: 7/7 passed
- **Chat**: 9/9 passed
- **Navigation**: 4/4 passed
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
- [05-treemap-standalone.png](../screenshots/regression/05-treemap-standalone.png)
- [06-treemap-in-chat.png](../screenshots/regression/06-treemap-in-chat.png)
- [06b-journalist-standalone.png](../screenshots/regression/06b-journalist-standalone.png)
- [06c-journalist-in-chat.png](../screenshots/regression/06c-journalist-in-chat.png)
- [07-chat-response.png](../screenshots/regression/07-chat-response.png)
- [08-topic-politics.png](../screenshots/regression/08-topic-politics.png)
- [09-mobile.png](../screenshots/regression/09-mobile.png)