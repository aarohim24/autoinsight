#!/bin/bash
# Quick diagnosis script for Render deployment issues

echo "🔍 Checking Render Deployment Status..."
echo ""

# Check health endpoint
echo "📊 Health Check:"
curl -s https://autoinsight-lc8i.onrender.com/health | python3 -m json.tool 2>/dev/null || echo "❌ Backend not responding"

echo ""
echo "📋 Troubleshooting Steps:"
echo ""
echo "1. ✅ Check Render Environment Variables:"
echo "   - Go to https://dashboard.render.com"
echo "   - Select your service: autoinsight-backend"
echo "   - Click 'Environment' tab"
echo "   - Verify GROQ_API_KEY is set (not empty)"
echo ""
echo "2. 🔄 Redeploy Service:"
echo "   - In Render dashboard, click 'Manual Deploy'"
echo "   - Or push a commit: git commit --allow-empty -m 'trigger deploy'"
echo "   - git push origin main"
echo ""
echo "3. 📜 Check Logs:"
echo "   - In Render dashboard, click 'Logs' tab"
echo "   - Look for 'startup_ok' message"
echo ""
echo "4. ✅ Verify Variables are Set:"
curl -s https://autoinsight-lc8i.onrender.com/health 2>/dev/null | grep -o '"groq_key_set":[^,}]*' || echo "   Could not check"
echo ""
echo "If groq_key_set is still false after redeploy, follow the steps above."
