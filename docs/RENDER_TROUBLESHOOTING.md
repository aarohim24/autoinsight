# 🔧 Render Deployment Troubleshooting

Your backend is deployed at: `https://autoinsight-lc8i.onrender.com`

But it's showing `groq_key_set: false` - meaning the API key isn't loaded. Here's how to fix it.

## ⚠️ Common Issue: Environment Variables Not Set

### Quick Fix (2 minutes)

1. **Open Render Dashboard**
   - Go to https://dashboard.render.com
   - Select your service: `autoinsight-backend`

2. Click **Environment** Tab
   - Look for `GROQ_API_KEY`
   - If missing or empty, add it:
     ```
     GROQ_API_KEY = gsk-your-actual-key-from-console-groq-com
     ```

3. **Redeploy Service**
   - Click "Manual Deploy" button, OR
   - Push any commit to GitHub:
     ```bash
     git commit --allow-empty -m "redeploy on render"
     git push origin main
     ```

4. **Wait 2-3 minutes**
   - Check Render "Logs" tab
   - Should see: `startup_ok groq_key_prefix=gsk_bKz0...`

5. **Verify**
   ```bash
   curl https://autoinsight-lc8i.onrender.com/health
   # Should show: "groq_key_set": true
   ```

---

## 📋 Step-by-Step Environment Setup

### In Render Dashboard:

1. Go to **Dashboard** → Select **autoinsight-backend**
2. Click **Environment** tab
3. Add these variables:

| Variable | Value | Notes |
|----------|-------|-------|
| `GROQ_API_KEY` | `gsk_...` | Get from console.groq.com |
| `LOG_LEVEL` | `INFO` | Can be DEBUG for more logs |
| `SESSION_TTL_SECONDS` | `3600` | 1 hour session timeout |
| `CACHE_TTL_SECONDS` | `3600` | 1 hour cache timeout |

4. **Click "Save"** (important!)
5. Service will auto-redeploy

---

## 🔍 Checking Logs

In Render Dashboard, go to **Logs** tab:

### ✅ Good Log Output:
```
[info     ] cache_backend                  backend=memory_lru
[info     ] session_store_backend          backend=memory reason='No Redis configured'
[info     ] startup_ok                    groq_key_prefix=gsk_bKz0...
[info     ] startup_complete              allowed_origins=['*']
```

### ❌ Bad Log Output:
```
[error    ] no_groq_key                   hint='Set GROQ_API_KEY environment variable'
```
→ This means env var not set. Follow the fix above.

---

## 🧪 Testing the API

Once redeployed, test each endpoint:

### 1. Health Check
```bash
curl https://autoinsight-lc8i.onrender.com/health
```

Expected:
```json
{
  "status": "ok",
  "version": "1.2.0",
  "groq_key_set": true
}
```

### 2. Upload CSV
```bash
echo "name,age,salary
John,30,50000
Jane,28,55000" > test.csv

curl -X POST -F "file=@test.csv" \
  https://autoinsight-lc8i.onrender.com/api/upload-data
```

Expected:
```json
{
  "status": "ok",
  "session_id": "abc-123-def",
  "filename": "test.csv",
  "loaded_rows": 2,
  "columns": ["name", "age", "salary"]
}
```

### 3. Analyze Data
```bash
curl https://autoinsight-lc8i.onrender.com/api/analyze \
  -H "X-Session-Id: <session-id-from-above>"
```

---

## 🆘 Still Not Working?

### Issue: `groq_key_set` is still `false` after redeploy

**Solution:**
1. Delete the service and recreate:
   - Render Dashboard → Delete Service
   - Create new Web Service from scratch
   - Set env vars BEFORE deploying

2. Or use Fly.io instead:
   ```bash
   flyctl launch
   flyctl config:set GROQ_API_KEY="gsk_..."
   ```

### Issue: Build failing

**Check build logs:**
- Render Dashboard → **Logs** tab
- Look for error messages
- Common causes:
  - Missing dependencies → Update `requirements.txt`
  - Python version mismatch → Use Python 3.12
  - Port binding error → Already fixed in code

### Issue: Service keeps crashing

**Check logs for:**
```
ModuleNotFoundError: No module named 'X'
```

**Fix:**
```bash
pip install -r requirements.txt
git add requirements.txt
git commit -m "update dependencies"
git push origin main
```

---

## 🚀 After API Works: Connect Frontend

Update your Next.js frontend:

**`frontend-next/.env.local`**:
```
NEXT_PUBLIC_API_URL=https://autoinsight-lc8i.onrender.com/api
BACKEND_URL=https://autoinsight-lc8i.onrender.com/api
```

Then deploy frontend to Vercel:
```bash
cd frontend-next
vercel --prod
```

---

## 📊 Monitoring

### View Real-Time Logs
- Render Dashboard → Your Service → **Logs** tab
- Filters available by log level

### Check Metrics
- Render Dashboard → Your Service → **Metrics** tab
- CPU, Memory, Network usage

### Restart Service
- Render Dashboard → Your Service → **Settings** → **Restart Service**

---

## 💡 Tips

1. **Auto-redeploy on push**
   - Render auto-deploys when you push to `main` branch
   - No manual action needed

2. **Debugging locally vs. production**
   - Locally: `.env` file is used
   - Production (Render): Environment variables in dashboard
   - Never commit `.env` with real secrets!

3. **Add Redis for scaling**
   - Render → New → Redis
   - Copy connection string
   - Add to `REDIS_URL` env var
   - Redeploy

---

## ✅ Verification Checklist

Before declaring it "working":

- [ ] `curl /health` returns `groq_key_set: true`
- [ ] Can upload CSV file
- [ ] Can analyze data
- [ ] Can generate insights
- [ ] Frontend connects to backend URL
- [ ] No errors in Render logs

---

**Need more help?**
- Render Docs: https://render.com/docs
- Python on Render: https://render.com/docs/deploy-python
- Check backend logs in Render dashboard

You're almost there! Just set the env var and redeploy. 🚀
