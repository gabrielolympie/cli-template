---
name: playwright-cli
description: Automates browser interactions for web testing, form filling, screenshots, and data extraction. Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, test web applications, or extract information from web pages.
allowed-tools: Bash(playwright-cli:*)
---

# Browser Automation with playwright-cli

## Quick start

```bash
# open new browser (always in headed mode by default)
playwright-cli open
# navigate to a page
playwright-cli goto https://playwright.dev
# interact with the page using refs from the snapshot
playwright-cli click e15
playwright-cli type "page.click"
playwright-cli press Enter
# take a screenshot
playwright-cli screenshot
# close the browser
playwright-cli close
```

## Commands

### Core

```bash
playwright-cli open --headed
# open and navigate right away
playwright-cli open --headed https://example.com/
playwright-cli goto https://playwright.dev
playwright-cli type "search query"
playwright-cli click e3
playwright-cli dblclick e7
playwright-cli fill e5 "user@example.com"
playwright-cli drag e2 e8
playwright-cli hover e4
playwright-cli select e9 "option-value"
playwright-cli upload ./document.pdf
playwright-cli check e12
playwright-cli uncheck e12
playwright-cli snapshot
playwright-cli snapshot --filename=after-click.yaml
playwright-cli eval "document.title"
playwright-cli eval "el => el.textContent" e5
playwright-cli dialog-accept
playwright-cli dialog-accept "confirmation text"
playwright-cli dialog-dismiss
playwright-cli resize 1920 1080
playwright-cli close
```

### Navigation

```bash
playwright-cli go-back
playwright-cli go-forward
playwright-cli reload
```

### Keyboard

```bash
playwright-cli press Enter
playwright-cli press ArrowDown
playwright-cli keydown Shift
playwright-cli keyup Shift
```

### Mouse

```bash
playwright-cli mousemove 150 300
playwright-cli mousedown
playwright-cli mousedown right
playwright-cli mouseup
playwright-cli mouseup right
playwright-cli mousewheel 0 100
```

### Save as

```bash
playwright-cli screenshot
playwright-cli screenshot e5
playwright-cli screenshot --filename=page.png
playwright-cli pdf --filename=page.pdf
```

### Tabs

```bash
playwright-cli tab-list
playwright-cli tab-new
playwright-cli tab-new https://example.com/page
playwright-cli tab-close
playwright-cli tab-close 2
playwright-cli tab-select 1
```

### Storage

```bash
playwright-cli state-load auth-state.json
playwright-cli state-save auth-state.json
playwright-cli cookie-list
playwright-cli cookie-get sessionid
playwright-cli cookie-set token abc123
playwright-cli cookie-delete sessionid
playwright-cli localstorage-set key value
playwright-cli localstorage-get key
playwright-cli sessionstorage-set key value
```

### Network

```bash
playwright-cli route https://api.example.com/*
playwright-cli route-list
playwright-cli unroute https://api.example.com/*
playwright-cli network
```

### DevTools

```bash
playwright-cli console
playwright-cli console warning
playwright-cli run-code "await page.goto('https://example.com'); await page.fill('input', 'text')"
playwright-cli tracing-start
playwright-cli tracing-stop
playwright-cli video-start
playwright-cli video-stop
```

### Available Options for `open`

- `--headed` - Run browser in headed mode (visible window) - **default**
- `--headless` - Run browser in headless mode (no visible window)
- `--browser chrome` - Use Chrome browser
- `--browser firefox` - Use Firefox browser
- `--browser webkit` - Use WebKit browser
- `--profile directory` - Use persistent browser profile

## Advanced Usage

### Running Code

```bash
playwright-cli run-code "await page.goto('https://example.com'); await page.fill('input', 'text')"
```

### Tracing

```bash
playwright-cli tracing-start
playwright-cli goto https://example.com
playwright-cli click e5
playwright-cli tracing-stop
```

### Video Recording

```bash
playwright-cli video-start
playwright-cli goto https://example.com
playwright-cli video-stop
```

### Request Mocking

```bash
playwright-cli route https://api.example.com/* --json='{"status": 200, "body": {"data": "mocked"}}'
```
