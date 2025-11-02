# Customer Portal Validation Checklist

## Pre-Flight Checks

### 1. Installation
```bash
cd /Users/uday/code/aws-msp/aws-msp-cloud-copy/frontend/customer-portal
npm install
```

Expected: No errors, all dependencies installed

### 2. Backend Running
```bash
# Check backend health
curl http://localhost:8000/health
```

Expected: `{"status": "healthy", ...}`

### 3. Start Development Server
```bash
npm run dev
```

Expected: Server starts on http://localhost:5174

## Functional Testing

### 4. Load Application
Open: http://localhost:5174

**Expected UI Elements:**
- ✅ Header: "Customer Support Portal"
- ✅ Settings panel (collapsed): "API Settings (Optional)"
- ✅ Welcome message: "Welcome to Customer Support"
- ✅ Message input box at bottom
- ✅ Send button visible

### 5. Test Chat Functionality

**Test 1: Simple Message**
1. Type: "Hello, can you help me?"
2. Click Send (or press Enter)

**Expected:**
- ✅ User message appears (blue, right-aligned)
- ✅ Loading indicator appears
- ✅ Assistant response streams in (gray, left-aligned)
- ✅ Response completes within 3-5 seconds
- ✅ No console errors

**Test 2: Multi-line Message**
1. Type: "I have multiple questions" (press Shift+Enter)
2. Type: "Can you help with all of them?"
3. Click Send

**Expected:**
- ✅ Message preserves line breaks
- ✅ Both lines visible in user message

**Test 3: Long Conversation**
1. Send 5 different messages
2. Verify conversation history persists
3. Scroll works correctly

**Expected:**
- ✅ All messages visible
- ✅ Auto-scrolls to latest message
- ✅ Timestamps displayed correctly

### 6. Test Settings Panel

**Test 1: Open Settings**
1. Click "API Settings (Optional)"

**Expected:**
- ✅ Panel expands
- ✅ Shows two input fields (OpenAI, OpenRouter)
- ✅ Shows "Save Keys" and "Clear Keys" buttons

**Test 2: Save API Keys**
1. Enter dummy OpenAI key: `sk-test123`
2. Enter dummy OpenRouter key: `sk-or-v1-test456`
3. Click "Save Keys"

**Expected:**
- ✅ Button shows "Saved!" temporarily
- ✅ Keys persist in localStorage
- ✅ Keys sent with next message

**Test 3: Clear API Keys**
1. Click "Clear Keys"

**Expected:**
- ✅ Input fields cleared
- ✅ localStorage keys removed

### 7. Test Error Handling

**Test 1: Backend Offline**
1. Stop backend service
2. Send message

**Expected:**
- ✅ Error message displayed in chat
- ✅ User message remains visible
- ✅ No empty assistant messages

**Test 2: Invalid API Key**
1. Enter invalid OpenRouter key in settings
2. Send message

**Expected:**
- ✅ Backend returns error
- ✅ Error shown to user
- ✅ User can retry

### 8. Test Persistence

**Test 1: User ID**
1. Open browser console
2. Run: `localStorage.getItem('user_id')`

**Expected:**
- ✅ UUID present (e.g., "123e4567-e89b-12d3-a456-426614174000")

**Test 2: Conversation Persistence**
1. Send 3 messages
2. Refresh page

**Expected (if backend supports):**
- ✅ User ID persists
- ✅ Can start new conversation

**Test 3: Clear Conversation**
1. Click "Clear" button
2. Confirm dialog

**Expected:**
- ✅ All messages cleared
- ✅ New conversation started
- ✅ Input box focused

### 9. Test Responsive Design

**Test 1: Mobile View**
1. Resize browser to 375px width

**Expected:**
- ✅ Layout adapts
- ✅ Messages stack properly
- ✅ Input box remains visible
- ✅ No horizontal scroll
- ✅ "Send" button text hidden on mobile

**Test 2: Tablet View**
1. Resize browser to 768px width

**Expected:**
- ✅ Layout looks good
- ✅ Max-width container (4xl) centered

### 10. Browser Console Check

**Expected:**
- ✅ No errors in console
- ✅ No warnings (except React dev mode warnings)
- ✅ Network requests successful (200 OK)

## Performance Testing

### 11. Streaming Performance
1. Send message
2. Observe token arrival

**Expected:**
- ✅ Tokens appear smoothly
- ✅ No lag or stuttering
- ✅ Response feels real-time

### 12. Memory Leaks
1. Send 20+ messages
2. Check memory usage (Chrome DevTools)

**Expected:**
- ✅ Memory usage stable
- ✅ No continuous growth

## Production Build

### 13. Build Application
```bash
npm run build
```

**Expected:**
- ✅ No build errors
- ✅ `dist/` directory created
- ✅ Assets optimized

### 14. Preview Production Build
```bash
npm run preview
```

**Expected:**
- ✅ Server starts
- ✅ Application works identically to dev mode

## Final Checklist

- [ ] All files created (16 total)
- [ ] Dependencies installed without errors
- [ ] Dev server starts on port 5174
- [ ] Can send and receive messages
- [ ] Streaming works correctly
- [ ] Settings panel functional
- [ ] API keys can be saved/cleared
- [ ] Error handling works
- [ ] User ID persists
- [ ] Responsive on mobile/tablet
- [ ] No console errors
- [ ] Production build succeeds
- [ ] Clean, professional UI

## Common Issues

### Issue: "Cannot connect to backend"
**Solution:**
- Verify backend running: `curl http://localhost:8000/health`
- Check Vite proxy config in vite.config.ts
- Ensure no firewall blocking port 8000

### Issue: "Streaming not working"
**Solution:**
- Check backend returns `Content-Type: text/event-stream`
- Verify SSE format in backend response
- Check browser network tab for connection

### Issue: "API keys not persisting"
**Solution:**
- Check localStorage enabled in browser
- Clear cache and try again
- Check browser console for errors

### Issue: "Messages not displaying"
**Solution:**
- Check React DevTools for component state
- Verify messages array populated in useChat hook
- Check browser console for rendering errors

## Success Criteria

✅ All 14 tests pass
✅ No critical bugs
✅ Clean, professional UI
✅ Responsive design works
✅ Production build succeeds
✅ Ready for deployment
