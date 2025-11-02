# Customer Portal File Structure

```
customer-portal/
├── .env.example                           # Environment variables template
├── .eslintrc.cjs                          # ESLint configuration
├── .gitignore                             # Git ignore patterns
├── FILE_STRUCTURE.md                      # This file
├── IMPLEMENTATION_SUMMARY.md              # Technical implementation details
├── index.html                             # HTML entry point
├── package.json                           # NPM dependencies and scripts
├── postcss.config.js                      # PostCSS configuration
├── QUICK_START.md                         # 1-minute setup guide
├── README.md                              # Main documentation
├── setup.sh                               # Automated setup script
├── tailwind.config.js                     # Tailwind CSS configuration
├── tsconfig.json                          # TypeScript configuration
├── tsconfig.node.json                     # TypeScript config for Vite
├── VALIDATION.md                          # Testing checklist
├── vite.config.ts                         # Vite dev server config
│
└── src/                                   # Source code directory
    ├── App.tsx                            # Root React component
    ├── index.css                          # Global styles + Tailwind
    ├── main.tsx                           # React entry point
    ├── types.ts                           # TypeScript interfaces
    │
    ├── components/                        # React components
    │   ├── ChatInterface.tsx              # Main chat UI (260 lines)
    │   ├── MessageBubble.tsx              # Message display (75 lines)
    │   └── SettingsPanel.tsx              # API key config (130 lines)
    │
    ├── hooks/                             # Custom React hooks
    │   └── useChat.ts                     # Chat logic + SSE (165 lines)
    │
    └── utils/                             # Utility functions
        └── cn.ts                          # Tailwind class merger (5 lines)
```

## File Count Summary

| Category | Count | Description |
|----------|-------|-------------|
| **Configuration** | 6 | Build/dev configs (package.json, vite, ts, tailwind) |
| **Documentation** | 5 | README, guides, validation |
| **React App** | 5 | Entry points, main component, types |
| **Components** | 3 | ChatInterface, MessageBubble, SettingsPanel |
| **Hooks** | 1 | useChat (chat logic + SSE streaming) |
| **Utils** | 1 | cn (class name utility) |
| **Scripts** | 1 | setup.sh |
| **Other** | 2 | .gitignore, .env.example |
| **TOTAL** | **24** | Complete application |

## Lines of Code

| File | Lines | Purpose |
|------|-------|---------|
| `src/components/ChatInterface.tsx` | 260 | Main chat UI |
| `src/hooks/useChat.ts` | 165 | Chat logic + SSE |
| `src/components/SettingsPanel.tsx` | 130 | Settings panel |
| `src/components/MessageBubble.tsx` | 75 | Message display |
| `vite.config.ts` | 20 | Dev server config |
| `package.json` | 40 | Dependencies |
| Other files | ~50 | Configs, types, utils |
| **TOTAL** | **~740** | Core application code |

## Directory Purposes

### Root Directory
- Configuration files (vite, typescript, tailwind, postcss)
- Documentation (README, guides, validation)
- Package management (package.json)
- Git configuration (.gitignore)

### `src/`
Main application source code:
- React entry points (main.tsx, App.tsx)
- Global styles (index.css)
- Type definitions (types.ts)

### `src/components/`
React UI components:
- **ChatInterface:** Full-page chat layout with header, messages, input
- **MessageBubble:** Individual message rendering (user/assistant)
- **SettingsPanel:** Collapsible API key configuration

### `src/hooks/`
Custom React hooks:
- **useChat:** Handles all chat logic (send, stream, state management)

### `src/utils/`
Utility functions:
- **cn:** Tailwind class name merging (clsx + tailwind-merge)

## Key Files Explained

### Configuration Files

**package.json**
- Dependencies: react, react-dom, lucide-react, clsx, tailwind-merge
- Dev dependencies: vite, typescript, tailwind, eslint
- Scripts: dev (port 5174), build, preview

**vite.config.ts**
- Port: 5174
- Proxy: `/api/*` → `http://localhost:8000/api/*`
- React plugin configured

**tsconfig.json**
- Target: ES2020
- Module: ESNext
- Strict mode enabled
- JSX: react-jsx

**tailwind.config.js**
- Custom primary color palette (blue theme)
- Content: index.html + all src files

### Documentation Files

**README.md** (comprehensive)
- Features overview
- Tech stack details
- Setup instructions
- Project structure
- Deployment guide
- Troubleshooting

**QUICK_START.md** (1-minute guide)
- Fast setup commands
- Prerequisites checklist
- Common troubleshooting

**VALIDATION.md** (testing)
- 14 test categories
- Step-by-step validation
- Success criteria
- Common issues + solutions

**IMPLEMENTATION_SUMMARY.md** (technical)
- Architecture decisions
- API integration details
- File-by-file breakdown
- Success criteria

### Source Code Files

**src/main.tsx**
- React entry point
- Renders App component
- StrictMode wrapper

**src/App.tsx**
- Root component
- Simply renders ChatInterface

**src/types.ts**
- TypeScript interfaces
- Message, Conversation, ChatRequest
- StreamEvent types

**src/components/ChatInterface.tsx**
- Main application component
- Header with title and clear button
- Settings panel integration
- Messages area with scroll
- Input box with send button
- Loading/error states

**src/components/MessageBubble.tsx**
- Displays individual messages
- User vs assistant styling
- Timestamps
- Line break formatting
- Avatar icons

**src/components/SettingsPanel.tsx**
- Collapsible panel
- OpenAI + OpenRouter key inputs
- Save/clear functionality
- localStorage persistence
- Visual feedback

**src/hooks/useChat.ts**
- User ID generation/persistence
- Send message function
- SSE streaming implementation
- Message state management
- Error handling
- Abort controller

**src/utils/cn.ts**
- Class name utility
- Combines clsx + tailwind-merge
- For conditional Tailwind classes

## Build Output

After `npm run build`:

```
dist/
├── index.html                 # Optimized HTML
├── assets/
│   ├── index-[hash].js        # Bundled JavaScript
│   ├── index-[hash].css       # Bundled CSS
│   └── [other-assets]         # Images, fonts, etc.
└── vite.svg                   # Vite logo
```

**Size:** ~150KB gzipped (estimated)

## Development Workflow

1. **Edit source:** Modify files in `src/`
2. **Hot reload:** Vite automatically reloads
3. **Type check:** TypeScript checks types on save
4. **Lint:** ESLint checks code quality
5. **Test:** Manual testing in browser
6. **Build:** `npm run build` for production

## Production Deployment

1. Run `npm run build`
2. Deploy `dist/` directory to static host
3. Configure reverse proxy for `/api/*` → backend
4. Serve `index.html` for all routes (SPA)

## Dependencies Size

```
node_modules/    ~500 MB (development)
dist/            ~500 KB (production)
src/             ~50 KB (source code)
```

## Git Strategy

**Tracked:**
- All source code (`src/`)
- Configuration files
- Documentation
- package.json, package-lock.json

**Ignored:**
- node_modules/
- dist/
- .env (use .env.example)
- *.local files
- Editor configs

## Maintenance

**Update dependencies:**
```bash
npm update
npm audit fix
```

**Check bundle size:**
```bash
npm run build
du -sh dist/
```

**Type check:**
```bash
npx tsc --noEmit
```

**Lint check:**
```bash
npm run lint
```

---

**Last Updated:** 2025-11-02
**Files:** 24 total
**Status:** Complete and ready for testing
