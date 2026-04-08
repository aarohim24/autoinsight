# 🚀 Vercel to Render Integration Guide

## Your Production URLs

| Service | URL |
|---------|-----|
| **Frontend (Vercel)** | https://autoinsight-peach.vercel.app |
| **Backend (Render)** | https://autoinsight-lc8i.onrender.com |
| **API Docs** | https://autoinsight-lc8i.onrender.com/docs |

---

## ✅ How to Connect Them

### Step 1: Open Vercel Dashboard
```
https://vercel.com/dashboard
```

### Step 2: Select Your Project
- Click on **autoinsight-peach** project

### Step 3: Add Environment Variable
1. Click **Settings** (top navigation)
2. Click **Environment Variables** (left sidebar)
3. Click **Add New** button
4. Fill in:
   - **Name**: `BACKEND_URL`
   - **Value**: `https://autoinsight-lc8i.onrender.com/api`
   - **Environment**: Select all (Production, Preview, Development)
5. Click **Save**

### Step 4: Redeploy
1. Go to **Deployments** tab
2. Find your latest deployment
3. Click the **3-dot menu** (...)
4. Select **Redeploy**
5. Wait for build to complete (takes ~2-3 minutes)

### Step 5: Test
1. Open https://autoinsight-peach.vercel.app
2. Upload a CSV file
3. Should analyze and generate insights!

---

## 🔧 How It Works

```
Browser → Vercel Frontend
         (https://autoinsight-peach.vercel.app)
            ↓
         Next.js API Proxy Routes (/api/*)
            ↓
         BACKEND_URL env variable
            ↓
         Render Backend API
         (https://autoinsight-lc8i.onrender.com/api)
            ↓
         CSV Processing + GROQ AI
```

---

## 📝 Environment Variables

### Vercel (Production)
```
BACKEND_URL = https://autoinsight-lc8i.onrender.com/api
```

### Local Development
```
BACKEND_URL = http://localhost:8000/api
```

---

## 🧪 Verify Connection

After deployment, test the connection:

```bash
# Check if Render backend is responding
curl https://autoinsight-lc8i.onrender.com/health

# Expected response:
# {"status":"ok","version":"1.2.0","groq_key_set":true}
```

---

## ⚠️ Troubleshooting

### "Backend unreachable" Error
1. Check Render backend is running
2. Verify BACKEND_URL is correct in Vercel
3. Wait for Vercel redeploy to complete
4. Hard refresh browser (Cmd+Shift+R)

### "GROQ API Key not set" Error
1. Check Render backend has GROQ_API_KEY env var
2. Verify key is correct
3. Restart Render service

### Still Not Working?
1. Check browser DevTools Network tab
2. Look for API errors
3. Check Render logs: Dashboard → Services → autoinsight-backend → Logs

---

## ✨ What's Included

### Frontend Features
- ✅ CSV upload (drag & drop)
- ✅ Data analysis & charts
- ✅ AI-generated insights (GROQ)
- ✅ Natural language queries
- ✅ Dark theme UI

### Backend Features
- ✅ FastAPI server
- ✅ CSV processing
- ✅ Data summarization
- ✅ GROQ LLM integration
- ✅ Rate limiting
- ✅ Session management
- ✅ Health checks

---

## 📞 Need Help?

Check these files in the repository:
- `QUICK_START.md` - Local setup guide
- `FIXES_APPLIED.md` - Technical details
- `STATUS.md` - Current deployment status
- `render.yaml` - Render configuration

---

## 🎉 You're All Set!

Your AutoInsight application is now:
- ✅ Frontend live on Vercel
- ✅ Backend live on Render
- ✅ Connected and ready to process data
- ✅ AI-powered with GROQ API

Start uploading CSVs and generating insights! 🚀
