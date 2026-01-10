# RALPH-AGI Documentation Website - Deployment Information

## Live URL

**Temporary Manus Hosting:**  
https://3000-i1wlhoo22mockh1l4bgho-90b8cf24.us2.manus.computer

> **Note:** This is a temporary deployment on Manus infrastructure. For permanent hosting, connect this repository to Netlify or Vercel via GitHub integration.

---

## Deployment Options

### Option 1: Netlify (Recommended)

1. Push this repository to GitHub
2. Connect to Netlify via GitHub integration
3. Build settings:
   - **Build command:** `pnpm run build`
   - **Publish directory:** `dist/public`
   - **Node version:** 22.x

The `netlify.toml` file is already configured for SPA routing.

### Option 2: Vercel

1. Push this repository to GitHub
2. Import project to Vercel
3. Build settings:
   - **Framework:** Vite
   - **Build command:** `pnpm run build`
   - **Output directory:** `dist/public`

### Option 3: Self-Hosted

```bash
# Build the project
pnpm install
pnpm run build

# Run the production server
PORT=3000 node dist/index.js

# Or use PM2 for process management
pm2 start dist/index.js --name ralph-agi-docs
```

---

## Project Structure

```
ralph-agi-001/
├── client/                  # Frontend React application
│   ├── src/
│   │   ├── pages/          # Page components
│   │   │   ├── Home.tsx
│   │   │   ├── PRD.tsx
│   │   │   ├── Architecture.tsx
│   │   │   ├── GettingStarted.tsx
│   │   │   └── Analysis.tsx    # NEW: Comprehensive analysis
│   │   ├── components/     # Reusable components
│   │   └── App.tsx         # Main app with routing
├── server/                 # Express server for production
├── dist/                   # Build output
│   ├── public/            # Static assets
│   └── index.js           # Server bundle
├── COMPREHENSIVE_ANALYSIS_V2.md  # Source analysis document
├── ANNOUNCEMENT_TWEET.md         # Twitter announcement templates
└── netlify.toml           # Netlify configuration
```

---

## Pages Available

1. **Home** (`/`) - Overview and introduction
2. **PRD** (`/prd`) - Product Requirements Document
3. **Architecture** (`/architecture`) - Technical Architecture
4. **Getting Started** (`/getting-started`) - Quick Start Guide
5. **Analysis** (`/analysis`) - Comprehensive Analysis (NEW)
   - Overview tab
   - References tab (7 implementations)
   - Key Insights tab
   - Roadmap tab (12-week plan)
   - Comparison tab

---

## Features

- **Responsive Design** - Works on desktop, tablet, and mobile
- **Dark Mode** - Professional dark theme optimized for reading
- **Collapsible Sidebar** - Obsidian-style navigation
- **Tabbed Content** - Organized analysis with 5 tabs
- **GitHub Integration** - Direct link to repository
- **Professional Typography** - Optimized for technical documentation

---

## Technology Stack

- **Frontend:** React 19 + TypeScript + Vite
- **Styling:** TailwindCSS 4 + Radix UI components
- **Routing:** Wouter (lightweight React router)
- **Icons:** Lucide React
- **Animations:** Framer Motion
- **Server:** Express (production)

---

## Build Information

**Build Date:** January 10, 2026  
**Build Time:** ~5 seconds  
**Bundle Size:** 
- CSS: 130.97 kB (gzipped: 20.12 kB)
- JS: 577.78 kB (gzipped: 170.95 kB)

---

## Environment Variables

No environment variables required for basic deployment. Optional analytics:

- `VITE_ANALYTICS_ENDPOINT` - Umami analytics endpoint
- `VITE_ANALYTICS_WEBSITE_ID` - Umami website ID

---

## Maintenance

### Update Content

1. Edit page components in `client/src/pages/`
2. Rebuild: `pnpm run build`
3. Redeploy

### Add New Pages

1. Create new component in `client/src/pages/`
2. Add route in `client/src/App.tsx`
3. Add navigation item in `client/src/components/Layout.tsx`

---

## Support

For issues or questions:
- **GitHub:** https://github.com/hdiesel323/ralph-agi-001
- **Documentation:** See this website

---

## License

MIT License - See repository for details

---

**Built with ❤️ using Manus AI**
