# 🚀 Deploy Backend to Render.com (5 minutes)

This is the fastest way to get your AutoInsight backend live with zero infrastructure headaches.

## Why Render?

- ✅ **Free tier**: 750 hours/month (= always on)
- ✅ **GitHub auto-deploy**: Push code, it deploys automatically
- ✅ **No credit card** required to start
- ✅ **Reliable**: Industry-standard platform
- ✅ **Easy scaling**: Just change plan when you grow

## Step-by-Step Setup

### 1️⃣ Sign Up (2 minutes)

1. Go to **[render.com](https://render.com)**
2. Click **"Sign up"**
3. Choose **"Sign up with GitHub"** (recommended)
4. Authorize Render to access your GitHub account

### 2️⃣ Create Web Service (2 minutes)

1. In Render dashboard, click **"New +"**
2. Select **"Web Service"**
3. Connect your **autoinsight** repository
4. Fill in the form:

   | Field | Value |
   |-------|-------|
   | **Name** | `autoinsight-backend` |
   | **Environment** | `Python 3` |
   | **Region** | Pick closest to you (e.g., `us-east-1`) |
   | **Branch** | `main` |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
   | **Plan** | `Free` |

5. Click **"Create Web Service"**

### 3️⃣ Set Environment Variables (1 minute)

1. In Render dashboard, go to your service
2. Click **"Environment"** tab
3. Add these variables:

   ```
   GROQ_API_KEY = gsk-your-actual-key-from-console-groq-com
   LOG_LEVEL = INFO
   SESSION_TTL_SECONDS = 3600
   CACHE_TTL_SECONDS = 3600
   ```

4. Leave `REDIS_URL` empty (uses in-memory storage)
5. Click **"Save"**

### 4️⃣ Wait for Deploy (1 minute)

Watch the **"Logs"** tab as Render builds and deploys your app.

You'll see:
```
...
Building Python dependencies
Installing from requirements.txt
✓ Build successful
✓ Deploy successful
Live at: https://autoinsight-backend.onrender.com
```

## ✅ Verify It Works

### Check Health Endpoint
```bash
curl https://autoinsight-backend.onrender.com/health
```

Response:
```json
{
  "status": "ok",
  "version": "1.2.0",
  "groq_key_set": true
}
```

### Test Upload
```bash
# Create a test CSV
echo "name,age,salary
John,30,50000
Jane,28,55000" > test.csv

# Upload it
curl -X POST \
  -F "file=@test.csv" \
  https://autoinsight-backend.onrender.com/api/upload-data
```

## 🔄 Auto-Deploy on Push

Every time you push to `main` branch:

```bash
git add .
git commit -m "update something"
git push origin main
```

Render automatically:
1. Pulls latest code
2. Installs dependencies
3. Runs start command
4. Deploys in ~2 minutes

## 🔗 Connect Frontend

Update your frontend environment variables:

**`frontend-next/.env.local`**:
```
NEXT_PUBLIC_API_URL=https://autoinsight-backend.onrender.com/api
BACKEND_URL=https://autoinsight-backend.onrender.com/api
```

Then deploy frontend to Vercel:
```bash
cd frontend-next
vercel --prod
```

## 📊 Monitoring

In Render dashboard:
- **Logs**: Real-time output
- **Metrics**: CPU, Memory, Network usage
- **Deployments**: History of all deployments

## 💾 Adding a Database (Optional)

If you want persistent Redis:

1. In Render: **"New +" → "Redis"**
2. Select **Free** tier
3. Copy connection string
4. Paste into `REDIS_URL` environment variable
5. Redeploy

## 💰 Costs

| Plan | Price | For AutoInsight |
|------|-------|-----------------|
| Free | $0 | Great for hobby |
| Starter | $7/month | Recommended |
| Standard | $25/month | For higher traffic |

**Free tier includes**: 750 hours/month (= always on)

## 🎯 Next Steps

1. ✅ Deploy backend to Render
2. ✅ Verify health endpoint works
3. ✅ Deploy frontend to Vercel
4. ✅ Update frontend `.env.local`
5. ✅ Test full app end-to-end
6. ✅ Monitor logs for issues

## 📞 Need Help?

- **Render Docs**: https://render.com/docs
- **Python on Render**: https://render.com/docs/deploy-python
- **Troubleshooting**: Check logs in Render dashboard

---

**That's it! Your backend is now live on Render!** 🚀

No infrastructure to manage. No servers to SSH into. Just push code and it deploys.
