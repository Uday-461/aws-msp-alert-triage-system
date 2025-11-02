# Customer Portal - Quick Start Guide

## 1-Minute Setup

```bash
# Navigate to project
cd /Users/uday/code/aws-msp/aws-msp-cloud-copy/frontend/customer-portal

# Install dependencies (one time)
npm install

# Start development server
npm run dev
```

**Open:** http://localhost:5174

## Prerequisites Checklist

- [x] Node.js 18+ installed
- [x] Backend running on port 8000
- [x] npm installed

## Verify Backend

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", ...}
```

## First Test

1. Open http://localhost:5174
2. Type: "Hello, can you help me?"
3. Press Enter
4. See streaming response

**Expected:** Response appears word-by-word within 3 seconds

## Common Commands

```bash
# Development
npm run dev          # Start dev server (port 5174)

# Production
npm run build        # Build for production
npm run preview      # Preview production build

# Maintenance
npm install          # Install dependencies
npm run lint         # Check for errors
```

## Port Configuration

- **Frontend:** 5174 (Vite dev server)
- **Backend:** 8000 (FastAPI API)
- **Proxy:** `/api/*` → `http://localhost:8000/api/*`

## Optional: API Keys

1. Click "API Settings (Optional)" at top
2. Enter keys:
   - OpenAI: `sk-...` (embeddings)
   - OpenRouter: `sk-or-v1-...` (chat)
3. Click "Save Keys"

**If not provided:** Backend uses demo keys automatically

## Troubleshooting

### "Cannot connect to backend"
```bash
# Check backend is running
curl http://localhost:8000/health

# If not, start backend first
cd /Users/uday/code/aws-msp/aws-msp-cloud-copy/backend/chatbot-api
uvicorn main:app --reload --port 8000
```

### "Port 5174 already in use"
```bash
# Kill existing process
lsof -ti:5174 | xargs kill -9

# Or change port in vite.config.ts
```

### "npm install fails"
```bash
# Clear cache and retry
rm -rf node_modules package-lock.json
npm install
```

## File Locations

```
customer-portal/
├── src/
│   ├── components/          # UI components
│   ├── hooks/               # Chat logic
│   └── types.ts            # TypeScript types
├── package.json            # Dependencies
├── vite.config.ts          # Port and proxy config
└── README.md               # Full documentation
```

## Success Indicators

✅ Dev server starts without errors
✅ Browser opens to http://localhost:5174
✅ No console errors
✅ Can send messages
✅ Responses stream in real-time

## Next Steps

- Read `README.md` for full documentation
- Follow `VALIDATION.md` for testing checklist
- See `IMPLEMENTATION_SUMMARY.md` for technical details

## Support

**Common Issues:** See "Troubleshooting" section above
**Detailed Testing:** See `VALIDATION.md`
**API Integration:** See `IMPLEMENTATION_SUMMARY.md`

---

**That's it! You're ready to go.** 🚀
