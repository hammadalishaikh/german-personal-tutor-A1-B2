# 🇩🇪 German Personal Tutor (A1 → B2)

A free German coach for personal, non-commercial use. It teaches you from **complete beginner (A1) to upper-intermediate (B2)**,
with lessons, exercises and grading by Google's Gemini AI.

Run it **on your own laptop**, where all your data stays on your hard drive, or **in the cloud**, where you can use it from any device.

▶️ **Video guide:** [docs/setup-guide.mp4](docs/setup-guide.mp4). It walks through both options.
<sub>Narration: AI clone of the creator's own voice.</sub>

---

## What it does

| | |
|---|---|
| 📈 **8 stages, A1 → B2** | Each stage has its own topics for **Grammar, Vocabulary, Listening, Reading, Writing and Speaking**. |
| 🇬🇧 **English help for beginners** | At **A1 and A2**, every explanation, instruction and correction is in **English**, with German examples and translations. At **B1** it switches to German with English hints. **B2** is German only. |
| 🧑‍🏫 **Lesson first, then practice** | "Teach me a concept first" explains a topic, then the coach gives exercises and grades them. |
| 🎯 **You choose how you pass** | **Percentage** (pick 60–90%) or the **Goethe exam standard**: 60%+ in *each* of Lesen, Hören, Schreiben and Sprechen, like the real Goethe-Zertifikat. You move up a stage by yourself. |
| 📚 **Study Hub** | A week-by-week plan, a grammar checklist for each level that ticks itself as you improve, and progress by topic. |
| 🗂️ **Vocabulary** | Gemini builds the word list for your level (e.g. "A2: 312 words"). A daily vocab check counts how many you know. |
| 📖 **Grammar tables** | 46 reference tables behind toggle switches: pronouns, articles, modal verbs, Konjunktiv II, prepositions, adjective endings … |

| Stage | Level | Focus |
|---|---|---|
| 1 | A1 | German basics: sein/haben, present tense, questions, articles, nicht/kein |
| 2 | A2 | Everyday German: Perfekt, modal verbs, separable verbs, Dativ, prepositions |
| 3 | A2.2 → B1 | Core consolidation: word order, subordinate clauses, Akkusativ/Dativ |
| 4 | B1 | Everyday communication: appointments, housing, work, opinions |
| 5 | B1+ | Complex grammar: relative clauses, Konjunktiv II, passive |
| 6 | B1+ → B2 | Transition: connectors, nominalisation, formal language |
| 7 | B2 | Production: formal emails, reports, presentations, debates |
| 8 | B2 | Goethe-style exam practice and fluency |

---

## Choose how to run it

| | 💻 **Option A: On your laptop** | ☁️ **Option B: In the cloud** |
|---|---|---|
| Your data | In the `data` folder on **your hard drive** | In your own Supabase database |
| Who can open it | **Only your computer** (`localhost`) | You, from **any device** (phone, other laptops) |
| Accounts you need | Only a free **Gemini key** | GitHub, Google AI Studio, Supabase, Streamlit (all free) |
| Setup time | ~5 minutes | ~15 minutes |
| Needs your laptop on | Yes | No |

Both run the same app. You need a Gemini key either way, because the AI teacher runs at Google.

---

## Option A: On your laptop 💻

1. **Install Python** (version 3.10 or newer) from **https://www.python.org/downloads/**.
   On Windows, tick **"Add Python to PATH"** on the first screen of the installer.
2. **Download the app:** on this page click the green **Code** button → **Download ZIP**, and unzip it
   anywhere (e.g. *Documents*). If you use git, `git clone` works too.
3. **Start it:**
   - **Windows:** double-click **`start_local.bat`**.
   - **Mac / Linux:** open a terminal in the folder and run `bash start_local.sh`.

   The first start installs the required packages, which takes a minute or two. Then your browser opens
   **http://localhost:8501**.
4. **Paste your Gemini key** when the app asks for it, then click **Save and start**. That happens only once.
   To get a key, go to **https://aistudio.google.com** → sign in → **Get API key** → **Create API key** → copy it.

That's it. 🎉 To stop the app, close the black window. To start it again, double-click `start_local.bat`.

**Where is my data?** In the **`data`** folder inside the app folder: your progress, exercises, plan and
vocabulary as readable JSON files, plus your Gemini key in `data/settings.json`. **Copy this folder now and
then as a backup.** It's your whole progress. The app only listens on `localhost`, so other devices on your
Wi-Fi can't open it.

---

## Option B: In the cloud ☁️

### Step 1: Your own copy (GitHub)
1. Create a GitHub account at **https://github.com/signup** (skip this if you have one).
2. Open this repository and click **Fork** (top right) → **Create fork**.

### Step 2: Gemini API key (Google AI Studio)
1. Go to **https://aistudio.google.com** and sign in with your Google account.
2. Click **Get API key** → **Create API key** and copy it.
   ⚠️ Never share it and never paste it into a file on GitHub. It only goes into Streamlit's **Secrets** (Step 4).

### Step 3: The database (Supabase)
1. Go to **https://supabase.com** → **Start your project**, and sign up (you can use GitHub).
2. Click **New project**. Choose a name, **save the database password**, and pick a region close to you.
   Wait ~2 minutes until the project is ready.
3. Open **SQL Editor** → **New query**. Copy **all** of [`schema.sql`](schema.sql), paste it, and click **Run**.
   You should see "Success. No rows returned".
4. Open **Project Settings** (⚙️) → **API Keys** and copy the **Project URL** (`https://abcdefgh.supabase.co`)
   and the **Secret key** (`sb_secret_…`). If the app later says *Invalid API key*, use the **`service_role`**
   key from the **Legacy API keys** tab instead.
   ⚠️ The secret key gives full access to your database. Only put it into Streamlit's Secrets.

### Step 4: Run the app (Streamlit Community Cloud)
1. Go to **https://share.streamlit.io** and **sign in with GitHub**.
2. Click **Create app** → **Deploy a public app from GitHub**. Repository: your fork; Branch: `main`;
   Main file path: `app.py`.
3. Click **Advanced settings**. In **Secrets**, paste this and fill in your values
   (same as [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)):
   ```toml
   GEMINI_API_KEY = "your-gemini-key"
   SUPABASE_URL = "https://your-project-id.supabase.co"
   SUPABASE_KEY = "your-supabase-secret-key"
   APP_PASSWORD = "choose-a-password"
   GEMINI_MODEL = "gemini-3.8-flash"
   LEARNER_ID = "me"
   ```
   `APP_PASSWORD` is optional but **recommended**. Your app's address is public, and without a password
   anyone who finds it could use your Gemini quota.
4. Click **Deploy** and wait 1–2 minutes. 🎉

When Supabase settings are present, the app saves to Supabase automatically. Without them, it saves to the local `data` folder.

---

## First steps in the app
1. **Pick your level** in the sidebar under *Choose my level*. Complete beginners stay at **Stage 1 (A1)**.
2. **Choose your passing rule** under *🎯 Passing rule*:
   - **Percentage:** pick the average score you need (60–90%, default 85%) over 8+ exercises.
   - **Goethe exam standard:** 60%+ in **each** of Lesen, Hören, Schreiben and Sprechen, with at least 3
     exercises each, like the Goethe-Zertifikat. A strong skill can't make up for a weak one.
     The sidebar shows ✅/⬜ for each skill.
3. Under **Today's adaptive lesson**, choose a skill (or *Auto*) and click **📘 Teach me a concept first**.
   Then **I understand, give me an exercise**, answer, and submit.
4. Scroll down to the **📚 Study Hub**:
   - **Syllabus → Vocabulary:** click **✨ Build my word list with Gemini** once per level, then do the
     10-word **vocab check** every day.
   - **Syllabus → Grammar:** the grammar points of your level tick themselves as you master them.
   - **Plan:** your week-by-week sessions.
5. At the very bottom, switch on **📖 German grammar tables** whenever you need to look something up.

**Tip:** short and often beats long and rare. 15–20 minutes a day, every day.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Windows: "python is not recognized" | Reinstall Python and tick **Add Python to PATH**, then start `start_local.bat` again. |
| "Port 8501 is already in use" | The app is already running. Open http://localhost:8501, or close the other window first. |
| Want a new Gemini key (local) | Delete `data/settings.json` and restart; the app asks again. |
| Cloud: "Cannot connect" after a break | Supabase **pauses free projects after about a week without use**. Open supabase.com → your project → **Restore project**, wait 2 minutes, reload the app. |
| Cloud: *Invalid API key* (Supabase) | Use the **Legacy API keys → `service_role`** key as `SUPABASE_KEY`. |
| Cloud: "…only last for this browser session" | The tables don't exist yet. Run [`schema.sql`](schema.sql) in the Supabase SQL Editor. |
| Gemini "busy", 503 or rate limit | The app automatically tries other Gemini models. If all are busy, wait a minute; the free tier has per-minute limits. |

Switching from laptop to cloud later starts a fresh database; your local `data` folder isn't uploaded automatically.

---

## Privacy and security
- **Laptop:** everything stays in the `data` folder, and the app only listens on `localhost`. Only your lessons, exercises and answers are sent to Google's Gemini API to be created and graded.
- **Cloud:** keys live only in **Streamlit Secrets**. `schema.sql` switches on **Row Level Security**, so Supabase's public key can't read your data; only your app, with the secret key, can.
- `.gitignore` keeps `secrets.toml` and the `data` folder out of git.
- Google's free Gemini tier may use prompts to improve its products. Check Google's current terms.

## License
[PolyForm Noncommercial License 1.0.0](LICENSE). Copyright © 2026 Sheikh Hammad Ali.

- ✅ **Allowed, for free:** using it to learn German, personal study, changing it for yourself, sharing it
  with others (with the license), and use by schools, charities, research and public institutions.
- ❌ **Not allowed:** any commercial use. That includes selling it, offering it as a paid service, or using
  it in a company's product or business.

Want to use it commercially? Contact me through [GitHub](https://github.com/hammadalishaikh) about a
commercial license.
