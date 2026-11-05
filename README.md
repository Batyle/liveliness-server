# FaceAttend liveness server

The public anti-spoofing API for the FaceAttend Vercel website.

## Deploy on Vercel

1. Import this repository as a new Vercel project.
2. Select the **Container** framework preset.
3. Deploy, then open `https://YOUR-SERVICE.vercel.app/health`. It must return `{"ready": true}`.
4. In the FaceAttend frontend Vercel project, add `VITE_LIVENESS_API_URL` with the value `https://YOUR-SERVICE.vercel.app/liveness`, then redeploy that frontend.

The service accepts requests from `*.vercel.app` by default. For a custom frontend domain, add `LIVENESS_CORS_ORIGINS=https://your-domain.example` in the liveness project's Vercel environment variables and redeploy.
