# Customer Support Portal

AI-powered customer support chatbot with RAG (Retrieval-Augmented Generation).

## Features

- Real-time streaming chat responses
- RAG-powered knowledge base search
- Optional API key configuration
- Clean, responsive UI
- Persistent conversations
- User ID tracking via localStorage

## Tech Stack

- React 18 + TypeScript
- Vite (dev server + build tool)
- Tailwind CSS (styling)
- lucide-react (icons)

## Prerequisites

- Node.js 18+ and npm
- Backend API running on port 8000

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (port 5174)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Development

The app will be available at: http://localhost:5174

### API Integration

The frontend proxies API requests to the backend:
- `/api/*` → `http://localhost:8000/api/*` (configured in vite.config.ts)

### Backend Endpoints Used

- `POST /api/chat/message` - Send chat message (SSE streaming)
- `POST /api/chat/conversations` - Create new conversation
- `GET /api/chat/conversations/{user_id}` - Get user conversations
- `GET /api/chat/conversations/{id}/messages` - Get conversation messages

## Configuration

### Optional API Keys

Users can provide their own API keys via the settings panel (collapsed by default):

1. Click "API Settings (Optional)" at the top
2. Enter OpenAI API key (for embeddings)
3. Enter OpenRouter API key (for chat)
4. Click "Save Keys"

Keys are stored in localStorage and sent with each request. If not provided, backend uses demo keys.

### User ID

A random UUID is generated on first visit and stored in localStorage. This persists conversations across sessions.

## Project Structure

```
customer-portal/
├── src/
│   ├── components/
│   │   ├── ChatInterface.tsx      # Main chat UI
│   │   ├── MessageBubble.tsx      # Individual message display
│   │   └── SettingsPanel.tsx      # API key configuration
│   ├── hooks/
│   │   └── useChat.ts             # Chat logic + SSE streaming
│   ├── utils/
│   │   └── cn.ts                  # Tailwind class merging
│   ├── types.ts                   # TypeScript interfaces
│   ├── App.tsx                    # Root component
│   ├── main.tsx                   # React entry point
│   └── index.css                  # Global styles + Tailwind
├── index.html                     # HTML entry point
├── vite.config.ts                 # Vite configuration
├── tailwind.config.js             # Tailwind configuration
├── tsconfig.json                  # TypeScript configuration
└── package.json                   # Dependencies
```

## Features Detail

### Streaming Responses

Messages stream in real-time using Server-Sent Events (SSE):
- User sees tokens appearing as they're generated
- Loading indicator while waiting
- Auto-scroll to latest message

### Error Handling

- Network errors shown inline
- Failed requests don't leave empty messages
- Clear error messages for users

### Keyboard Shortcuts

- `Enter` - Send message
- `Shift+Enter` - New line in message

## Deployment

### Production Build

```bash
npm run build
```

Output: `dist/` directory with static files

### Serve Static Files

```bash
# Using Vite preview
npm run preview

# Or any static file server
npx serve dist
```

### Environment Variables

Create `.env` file (copy from `.env.example`):

```bash
VITE_API_URL=http://your-backend-url:8000
```

## Troubleshooting

### Backend Connection Issues

1. Verify backend is running: `curl http://localhost:8000/health`
2. Check Vite proxy config in `vite.config.ts`
3. Check browser console for CORS errors

### Streaming Not Working

1. Check browser supports SSE (all modern browsers do)
2. Verify backend returns correct `Content-Type: text/event-stream`
3. Check network tab for SSE connection

### API Keys Not Saving

1. Check localStorage is enabled in browser
2. Clear localStorage: `localStorage.clear()` in console
3. Check browser console for errors

## License

MIT
