# 🚨 ACTION: Fix Your Render Backend (5 minutes)

## The Problem
Your backend is deployed at: https://autoinsight-lc8i.onrender.com/health

But it's showing: `"groq_key_set": false`

**Cause:** The `GROQ_API_KEY` environment variable is not set in Render dashboard.

## The Solution (2 steps)

### Step 1: Set the API Key in Render (1 minute)

1. Open: https://dashboard.render.com
2. Find your service: **autoinsight-backend**
3. Click **Environment** tab
4. Add this variable:
   ```
   GROQ_API_KEY = gsk-your-actual-key-from-console-groq-com
   ```
5. Click **Save**

### Step 2: Redeploy (1 minute)

Choose ONE:

**Option A: Click "Manual Deploy"** (fastest)
- Render Dashboard → Your Service → **Manual Deploy** button

**Option B: Push to GitHub**
```bash
cd /Users/aarohimathur/Desktop/autoinsight
git commit --allow-empty -m "trigger redeploy"
git push origin main
```

## Verify It Works (1 minute)

Wait 2-3 minutes, then test:

```bash
curl https://autoinsight-lc8i.onrender.com/health
```

You should see:
```json
{
  "status": "ok",
  "version": "1.2.0",
  "groq_key_set": true  ← Should be TRUE now
}
```

## That's It! 

Your API is now working. Next, connect your frontend:

**`frontend-next/.env.local`**:
```
BACKEND_URL=https://autoinsight-lc8i.onrender.com/api
```

Deploy frontend to Vercel:
```bash
cd frontend-next
vercel --prod
```

---

## 📖 Full Documentation

For more details, see: `docs/RENDER_TROUBLESHOOTING.md`

---

**Do this NOW and it'll be working in 5 minutes!** ⚡
