# Backend Deployment Guide

This guide covers deploying the AutoInsight backend to production-grade platforms with free or low-cost options.

## ⚡ Quick Comparison

| Platform | Pricing | Free Tier | Pros | Cons |
|----------|---------|-----------|------|------|
| **Render** | $7/month | 750 hrs/mo | Reliable, easy, free Postgres | Sleeps after 15 min inactivity |
| **Railway** | Pay-as-you-go | $5 credit/mo | Simple, good docs | Can be expensive |
| **Heroku** | $7-50/month | ❌ None | Popular, easy | Expensive |
| **Fly.io** | $5/month | ✅ Generous | Lightweight, fast | CLI-focused |
| **PythonAnywhere** | $5/month | Limited | Python-specific | Limited flexibility |

---

## 🚀 Recommended: Deploy on Render.com

### Why Render?
- ✅ Free tier available (750 hours/month = always on)
- ✅ Auto-deploys from GitHub
- ✅ Simple configuration
- ✅ Generous free Postgres database
- ✅ No credit card required to start
- ✅ Email-based sign up

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub (recommended)
3. Connect your GitHub account

### Step 2: Create a New Web Service
1. Dashboard → New → Web Service
2. Select your `autoinsight` repository
3. Configure:
   - **Name**: `autoinsight-backend` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free` (optional plan)

### Step 3: Set Environment Variables
In Render Dashboard → Your Service → Environment:

```
GROQ_API_KEY=gsk-your-actual-key
REDIS_URL=redis://default:password@your-redis-host:port
LOG_LEVEL=INFO
SESSION_TTL_SECONDS=3600
CACHE_TTL_SECONDS=3600
```

**Note**: For free tier, skip Redis and use in-memory storage (set in code).

### Step 4: Configure Redis (Optional)
If you want Redis for production:
- Render → New → Redis
- Select Free tier
- Copy connection string to `REDIS_URL`

### Step 5: Deploy
- Push code to GitHub `main` branch
- Render auto-deploys (takes 2-3 minutes)
- Your API is live at: `https://autoinsight-backend.onrender.com`

### Step 6: Update Frontend
Update `frontend-next/.env.local`:
```
NEXT_PUBLIC_API_URL=https://autoinsight-backend.onrender.com/api
BACKEND_URL=https://autoinsight-backend.onrender.com/api
```

---

## 🚀 Alternative: Deploy on Fly.io

### Why Fly.io?
- ✅ Lightweight (perfect for API)
- ✅ Fast edge deployment
- ✅ Good free tier
- ✅ Generous bandwidth

### Quick Setup
```bash
# 1. Install Fly CLI
curl -L https://fly.io/install.sh | sh

# 2. Sign up
flyctl auth signup

# 3. Deploy
flyctl launch
# Follow prompts, set GROQ_API_KEY when asked
```

---

## 🚀 Alternative: Deploy on Heroku (Paid)

### Why Heroku?
- ✅ Simple Git-based deployment
- ✅ Excellent documentation
- ✅ Industry standard

### Quick Setup
```bash
# 1. Install Heroku CLI
brew tap heroku/brew && brew install heroku

# 2. Login
heroku login

# 3. Create app
heroku create autoinsight-backend

# 4. Set environment variables
heroku config:set GROQ_API_KEY="gsk-your-key"

# 5. Deploy
git push heroku main
```

---

## 📋 Pre-Deployment Checklist

Before deploying, ensure:

- [ ] All code is committed to GitHub
- [ ] `.env` file is in `.gitignore` (never commit secrets!)
- [ ] `requirements.txt` is up to date: `pip freeze > requirements.txt`
- [ ] Dockerfile works locally: `docker build -t autoinsight .`
- [ ] Backend starts: `uvicorn backend.main:app --reload`
- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] All tests pass: `pytest`

---

## 🔧 Environment Variables Needed

### Required
- `GROQ_API_KEY` - Your Groq API key from console.groq.com

### Optional (with defaults)
- `REDIS_URL` - Leave empty to use in-memory storage
- `SESSION_TTL_SECONDS` - Default: 3600
- `CACHE_TTL_SECONDS` - Default: 3600
- `LOG_LEVEL` - Default: INFO

---

## 🚨 Common Issues & Fixes

### Issue: "Module not found" error
```bash
# Solution: Update requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "update dependencies"
git push
```

### Issue: Port binding error
```
# Render/Heroku/Fly set $PORT environment variable
# Our code already handles this in start_prod.sh
```

### Issue: GROQ_API_KEY not found
```bash
# Check if set in platform dashboard
# Verify no typo in environment variable name
# Restart service after setting
```

### Issue: Memory usage high
```bash
# In-memory storage can consume memory
# Switch to Redis for production
# Or limit SESSION_TTL_SECONDS
```

---

## 🔗 Frontend Integration

Once backend is deployed, update frontend:

**`frontend-next/.env.local`**:
```
NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com/api
BACKEND_URL=https://your-backend-url.onrender.com/api
```

Then deploy frontend to:
- Vercel (recommended for Next.js)
- Netlify
- GitHub Pages

---

## 📊 Monitoring & Logging

### Render
- Dashboard → Your Service → Logs
- Real-time logs visible in UI

### Fly.io
```bash
flyctl logs
```

### Heroku
```bash
heroku logs --tail
```

---

## 💰 Cost Estimate

| Scenario | Monthly Cost |
|----------|-------------|
| Hobby (in-memory Redis) | Free (Render) or $5 (Fly.io) |
| Production (dedicated Redis) | $10-20 |
| High traffic | $20-50+ |

---

## ✅ Recommended Stack

For maximum value & reliability:
- **Backend**: Render ($7/month after free tier)
- **Frontend**: Vercel (free for hobby)
- **Database** (if needed): Render Postgres (free tier)
- **Total**: $7/month + Groq API credits

---

## 🎯 Next Steps

1. Choose a platform (Render recommended)
2. Follow the setup steps above
3. Test the API health endpoint
4. Update frontend environment variables
5. Deploy frontend to Vercel
6. Test full stack end-to-end
7. Monitor logs for any errors

---

## 📞 Support Links

- **Render Help**: https://render.com/docs
- **Fly.io Help**: https://fly.io/docs/
- **Heroku Help**: https://devcenter.heroku.com/

---

**Your backend is production-ready and can be deployed in minutes!** 🚀
