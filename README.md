# 📄 IIT (ISM) Dhanbad — Exam Paper Generator & Grading System

> **Department of Computer Science and Engineering**  
> An automated, production-grade examination management system for generating unique, randomized, single-page LaTeX question papers, compiling merged bulk PDFs, resolving master TA answer keys, and grading student submissions.

---

## 🌟 Key Features

### 1. 🗂 Multi-Instance Question Banks & Variable Pools
* **Multiple Independent Banks ("Instances")**: Maintain separate question banks for different courses, quizzes, or semesters (e.g., *Compiler Design*, *Compiler Design Lab*, *Operating Systems*) side-by-side without ever needing to delete previous pools or papers. Each bank has its own paper code prefix (e.g., `CD-2026-1`, `CDL-2026-1`), pools, generated papers, answer keys, and grading results.
* **Variable Number of Topic Pools ($1 \dots M$)**: Add, rename, or remove any number of topic pools per bank (no hard limit of 5 pools).
* **Rich LaTeX Math & Code Snippets**: Full mathematical equations (`$...$`, `\[...\]`), code listings (`\begin{lstlisting} ... \end{lstlisting}`), inline tokens (`\texttt{}`), and verbatim macros.
* **Bulk Ingestion Support**:
  * **Excel Import (.xlsx / .xls)**: Multi-sheet TA format where each sheet corresponds to a pool (auto-creates as many pools as sheets in the workbook) or legacy flat format.
  * **Master LaTeX (.tex) Import**: Upload a complete raw master LaTeX exam document; choose whether to distribute extracted questions across selected existing pools or automatically create $K$ new pools.
  * **Downloadable Master LaTeX & Excel Templates**: Instant one-click download of blank templates (`master_questions_template.tex` and `questions_template.xlsx`) directly from the Import dropdown or modal.
  * **Web Form Entry**: Manual creation and editing with interactive question type and mark controls.
* **Master Question Paper Generator**: Generates a clean, publication-ready master question paper containing all bank questions without marked answers for departmental archives.

### 2. ⚡ Dynamic Paper Generation & Selective Pool Sampling
* **Selective Pool Sampling**: Choose **which subset of pools** to draw questions from when generating papers, with automatic even distribution across checked pools or a **custom per-pool question count override**.
* **Full-Width Ergonomic Generation Form**: Spacious layout with an on-demand **ℹ️ How It Works** dialog explaining sampling heuristics without consuming half the screen.
* **Flexible Paper Formats**:
  * **Objective (MCQ Quiz)**: Shuffle question order and ABCD options per student; customizable question counts (1–500 questions per paper).
  * **Subjective (Semester Paper)**: Standardized or randomized descriptive papers with custom marks per question.
* **Smart Anti-Collision & Weighted Selection**:
  * Prioritizes least-used questions so the entire bank is exercised evenly.
  * Samples without replacement per pool to guarantee zero duplicate questions on any paper.
  * Fingerprint hashing ensures no two students receive identical question sets.
* **Guaranteed Tight Multi-Page / Single-Page Layout**:
  * Integrated institutional logo (`iit_logo.png`) side-by-side with header text, preserving 100% of the page body.
  * Strict duplex alignment: 5-question quizzes fit on **exactly 1 page**, while 10-question papers with code listings fit on **strictly 2 pages** (1 physical sheet printed front and back), avoiding awkward 3-page spillover.
* **Bulk Compilation**:
  * Download individual papers as standalone PDFs or LaTeX sources.
  * Generate a single merged **Bulk PDF Bundle** (`all_papers_bundle.pdf`) containing all papers (e.g., 150 papers $\times$ 2 pages = exactly 300 pages) for one-click duplex printing.

### 3. 🎨 Modern Adaptive App Shell & Ergonomic UI
* **Desktop Top Header (60px Glassmorphic Bar)**:
  * Replaces cramped left sidebars with an expansive **100% full-width workspace**.
  * Houses institutional branding, segmented tab navigation pills, active bank switcher, and a **Pool Coverage Popover**.
* **Mobile Bottom Navigation Bar**:
  * Automatically shifts tab controls to a thumb-friendly native bottom bar on smartphones and screens $\le 860\text{px}$.
  * Built for cross-platform app bundling (Electron, Tauri, PWA, or Capacitor/Mobile Web).
* **Material Design 3 & Persistent Dark Mode**:
  * Modern Teal / Cyan aesthetic with deep obsidian dark mode.
  * Instant zero-FOUC theme switching with `localStorage` persistence and OS `prefers-color-scheme` synchronization.
* **Relaxed Ergonomic Question Editor**:
  * Spacious 820px modal dialog with clear visual hierarchy.
  * Dedicated **Metadata & Classification Card** (Target Pool, Topic, Marks, Bloom's Difficulty, Outcome-Based Education CO tags).
  * **Full-Width Option Rows**: Eliminates text truncation for long technical statements and LaTeX formulas; includes an integrated one-click "Correct" radio pill on each row.
* **Advanced Question Import Engine**:
  * **Interactive Staging & Dry-Run Preview Modal**: Inspect parsed questions, verify counts, and view duplicate warnings before committing to the database.
  * **Subjective Question Extraction**: Automatically parses descriptive problems without options.
  * **Conflict Resolution**: Choose between `Skip existing` questions or `Overwrite & update`.

### 4. 🔑 Master Answer Keys for Evaluators
* **Dynamic Answer Resolution**: Automatically tracks and resolves the randomized options back to the correct letter (`A`, `B`, `C`, or `D`) for every paper code.
* **Printable Master PDF**: Clean, multi-column A4 sheet designed for TAs during examination evaluation.
* **Styled Excel & CSV Exports**: Formatted Excel export (`master_answer_keys.xlsx`) with color-coded ABCD choices for quick visual scanning.
* **Instant Key Lookup**: On-screen search tool allowing evaluators to select any paper code and view its correct sequence instantly.

### 5. ✏️ TA Grading & Evaluation
* **Bulk Excel Grading**:
  * Download pre-formatted grading templates.
  * Upload filled Excel sheets with student roll numbers, paper codes, and chosen options (`Q1..QN`).
  * Auto-evaluates hundreds of submissions in seconds against per-paper shuffled keys.
* **Single Student Manual Entry**: Interactive form allowing TAs to enter a student roll number, select answers via radio buttons, and view immediate pass/fail feedback.
* **Roll Number Verification**: Enforces IIT (ISM) roll number formats (e.g. `21CS0001`).

### 6. 📊 Results & Class Analytics
* **Real-Time Analytics Dashboard**: Real-time stats on total graded students, class average, pass rate, and high score.
* **Score Distribution Chart**: Visual histogram breakdown of scores.
* **Student Lookup**: Search any roll number to view question-by-question breakdown, student answers vs. correct answers, and assigned marks.
* **CSV Export**: One-click export of complete student results.

---

## 🏗 Tech Stack

* **Backend**: Python 3.10+, [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
* **Database**: SQLite3 (with WAL mode enabled for concurrent reads/writes)
* **Templating & Typesetting**: [Jinja2](https://palletsprojects.com/p/jinja/), [LaTeX / pdfLaTeX](https://www.latex-project.org/) (TeX Live / MiKTeX), Poppler Utilities (`pdfunite`)
* **Spreadsheets**: [openpyxl](https://openpyxl.readthedocs.io/)
* **Frontend**: Vanilla Modern ES6+ JavaScript, Material Design 3 CSS Tonal Architecture (no Node.js build toolchain required)

---

## 🖥️ Hardware Requirements for Online Hosting

Because the system runs **real-time LaTeX compilation (`pdflatex`)** and **high-speed PDF stitching (`pdfunite`)** in addition to a FastAPI web server, sizing the server appropriately ensures fast paper compilation without memory exhaustion or request timeouts.

### 📊 Recommended Sizing Tiers

| Sizing Tier | Concurrency & Scale | vCPU | RAM | Storage (SSD/NVMe) | Network | Typical Hosting Cost |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Minimal / Dev** | 1–3 faculty/TAs, 1–100 students, batches $\le 50$ papers | **1 vCPU** | **1 GB – 2 GB** | **10 GB – 15 GB** | 100 Mbps | **Free** (Oracle OCI / GCP Free) or **\$3.50/mo** (Hetzner CX22) |
| **Tier 2: Production (Recommended)** | 5–15 faculty/TAs, 100–600 students, bulk 300+ page merges | **2 vCPUs** | **2 GB – 4 GB** | **25 GB – 40 GB** | 1 Gbps | **\$4 – \$12/mo** (DigitalOcean / Hetzner CX32) |
| **Tier 3: Institutional Enterprise** | Multiple exams concurrently, 1,000+ students, 1,000+ page bundles | **4 vCPUs** | **8 GB** | **80 GB+** | 1 Gbps | Departmental On-Premise Server or **\$24 – \$40/mo** VPS |

---

### 🔍 Resource Bottleneck & Sizing Analysis

1. **CPU (Compute Core Load)**:
   - **`pdflatex` compilation** is a single-threaded, CPU-bound operation (~0.4s to 0.7s per 2-page duplex question paper).
   - A single CPU core handles generation smoothly for small classes.
   - For **2+ concurrent users** generating papers simultaneously, **2 vCPUs** prevent LaTeX compilation from stalling HTTP requests.
2. **RAM (Memory Footprint)**:
   - **FastAPI / Uvicorn baseline**: ~80 MB – 120 MB per worker.
   - **SQLite with WAL mode**: ~15 MB – 30 MB cache footprint.
   - **`pdflatex` process**: ~40 MB – 65 MB per active compilation process.
   - **`pdfunite` (Poppler bundle merger)**: Merging 150 individual 2-page PDFs into a 300-page book takes ~100 MB RAM for 0.2 seconds.
   - **Minimum Recommended RAM**: **2 GB** (ensures memory overhead during peak paper generation bursts without Linux OOM killer activation). If using a 1 GB instance, configure a **1 GB to 2 GB swapfile**.
3. **Storage (Disk I/O & Space)**:
   - **Operating System + Python Environment**: ~2.5 GB.
   - **TeX Live Packages (`texlive-latex-base`, `texlive-latex-extra`, `texlive-fonts-recommended`)**: ~850 MB – 1.2 GB.
   - **Generated PDF Storage & Archives**: An individual 2-page question paper is ~65 KB; a 150-paper bulk bundle is ~9.5 MB. 15 GB storage comfortably accommodates over 1,500 exams, automatic database snapshots, and SQLite WAL journals.
   - **Disk Speed**: **SSD or NVMe** is strongly recommended for fast temporary `.aux` and `.log` file I/O during LaTeX builds.
4. **Network Bandwidth**:
   - Downloading a merged 300-page exam bundle (~9.5 MB) takes under 1 second on a standard 100 Mbps connection. 25 GB to 50 GB monthly transfer is more than sufficient for thousands of student papers.

---

## 🌐 Online Deployment Guide

### Deployment Stack
* **OS**: Ubuntu 22.04 LTS / 24.04 LTS or Debian 12
* **Reverse Proxy**: Nginx (handling SSL/TLS termination via Let's Encrypt)
* **Application Daemon**: Systemd service managing Uvicorn / Gunicorn
* **PDF Engine**: `pdflatex` (TeX Live) + `pdfunite` (`poppler-utils`)

### Step-by-Step Production Setup on Linux VPS

```bash
# 1. Update OS and install runtime packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip git texlive-latex-base texlive-latex-extra texlive-fonts-recommended poppler-utils nginx

# 2. Clone repository and set up environment
git clone <your-repo-url> /var/www/quiz-generator
cd /var/www/quiz-generator
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Create a Systemd service (/etc/systemd/system/quiz-generator.service)
sudo bash -c 'cat > /etc/systemd/system/quiz-generator.service << EOF
[Unit]
Description=IIT (ISM) Quiz Generator Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/quiz-generator
Environment="PATH=/var/www/quiz-generator/.venv/bin:/usr/bin"
ExecStart=/var/www/quiz-generator/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'

# 4. Set directory permissions and start service
sudo chown -R www-data:www-data /var/www/quiz-generator
sudo systemctl daemon-reload
sudo systemctl enable --now quiz-generator

# 5. Configure Nginx with SSL (Certbot)
sudo apt install -y certbot python3-certbot-nginx
# Point domain to server IP and run:
# sudo certbot --nginx -d exam.cse.iitism.ac.in
```

Before running the application locally, ensure you have:

1. **Python 3.10 or higher**:
   ```bash
   python --version
   ```
2. **LaTeX Distribution** (with `pdflatex` available on PATH):
   * **Linux (Ubuntu/Debian)**:
     ```bash
     sudo apt update && sudo apt install texlive-latex-base texlive-latex-extra texlive-fonts-recommended
     ```
   * **macOS**:
     ```bash
     brew install --cask mactex-no-gui
     ```
   * **Windows**:
     Install [MiKTeX](https://miktex.org/download) or [TeX Live](https://www.tug.org/texlive/). Ensure `pdflatex.exe` is added to your system `PATH`.
3. **Git**:
   ```bash
   git --version
   ```

---

## 🚀 How to Pull & Run Locally

### Step 1: Clone the Repository
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd "QUIZ generator"
```

### Step 2: Set Up a Python Virtual Environment

* **On Linux / macOS**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

* **On Windows (Command Prompt / PowerShell)**:
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate
  ```

### Step 3: Install Required Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Verify LaTeX Availability
Verify that `pdflatex` is accessible:
```bash
pdflatex --version
```
*(If `pdflatex` is not installed, the app will still run and let you download `.tex` source files, but automatic PDF compilation requires `pdflatex`.)*

### Step 5: Start the Local Server
```bash
python run.py
```
Or run directly with Uvicorn:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 6: Open the Web Application
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 🌐 Online Deployment Guide

### Deployment Considerations
This application requires `pdflatex` (TeX Live) installed on the system to compile PDFs. Because TeX Live packages require ~500MB–1GB of disk, deployment is easiest using a **Docker container** or a **standard Linux VPS**.

### Option A: Free Tier Options
1. **Oracle Cloud Infrastructure (OCI) Always Free (Recommended)**:
   * Provides free ARM/AMD compute instances (up to 24GB RAM) with persistent storage and static public IP for life.
   * Simply create an Ubuntu instance, install `python3`, `git`, and `texlive`, and run with systemd / screen.
2. **Fly.io / Render.com (Docker Web Service)**:
   * Build using a `Dockerfile` based on `python:3.11-slim` with `apt-get install -y texlive-latex-base texlive-latex-extra texlive-fonts-recommended`.
   * *Note*: Render's free tier spins down on idle; attach a persistent volume for `quiz.db` and generated PDFs.

### Option B: Low-Cost Dedicated VPS ($3–$5 / Month)
For department-wide access without cold starts or memory limits:
* Providers: **Hetzner Cloud** (€3.50/mo), **DigitalOcean** ($4/mo Droplet), or an on-premise local server in the IIT (ISM) CSE Department.
* Simple setup:
  ```bash
  sudo apt update && sudo apt install -y python3-venv texlive-latex-base texlive-latex-extra texlive-fonts-recommended
  git clone <repo-url> && cd "QUIZ generator"
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

---

## 📁 Project Directory Structure

```text
├── app/
│   ├── database.py              # SQLite connection, schema definition & migrations
│   ├── main.py                  # FastAPI application setup & static mounts
│   ├── models.py                # Pydantic data validation schemas & defaults
│   ├── routers/
│   │   ├── grading.py           # Single & bulk Excel grading API endpoints
│   │   ├── papers.py            # Paper generation, PDFs, and answer key exports
│   │   ├── questions.py         # Question CRUD, Excel import, and Master LaTeX import
│   │   └── results.py           # Student results, search, CSV export & stats
│   ├── services/
│   │   ├── generator.py         # Paper sampling algorithm & question shuffler
│   │   ├── grader.py            # Response evaluation engine & score calculator
│   │   ├── latex_gen.py         # Jinja2-to-LaTeX compiler & pdflatex runner
│   │   └── latex_import.py      # Master LaTeX parser (.tex file extractor)
│   └── templates/
│       ├── answer_keys.tex.j2   # Printable Master Answer Key PDF template
│       ├── bulk_papers.tex.j2   # Combined multi-paper bundle LaTeX template
│       ├── master_paper.tex.j2  # Master Question Paper (all questions) template
│       └── paper.tex.j2         # Individual exam question paper LaTeX template
├── generated_papers/            # Cached output PDFs and merged bundles
├── static/
│   ├── css/
│   │   └── style.css            # Responsive dark glassmorphism styling
│   ├── img/
│   │   └── iit_logo.png         # Institutional logo asset
│   ├── js/
│   │   ├── admin.js             # Question bank & paper generator UI logic
│   │   ├── answers.js           # Answer keys table & quick-checker logic
│   │   ├── app.js               # Tab navigation, notifications & toast system
│   │   ├── grading.js           # Student evaluation & bulk Excel handler
│   │   └── results.js           # Results table, analytics & score distribution
│   └── index.html               # Single-page web dashboard interface
├── iit_logo.png                 # Official university logo emblem
├── quiz.db                      # Local SQLite database (auto-created on startup)
├── requirements.txt             # Python package dependencies
├── run.py                       # Local startup server script
└── README.md                    # Project documentation
```

---

## 📖 Usage Guide

### 1. Ingesting Questions
1. Navigate to the **Question Bank** tab.
2. Click **📥 Import Excel** to upload questions using the multi-sheet Excel template.
3. Or click **📥 Import Master LaTeX** to upload your raw master `.tex` file; questions are automatically extracted, deduplicated, and split across the 5 pools.
4. Correct answers in LaTeX can be specified via:
   * A comment in the question: `% ans: B`
   * A bold label: `\textbf{(b)}`
   * A trailing `Answer Key` section: `1. B`

### 2. Generating Question Papers
1. Navigate to the **Papers** tab.
2. Configure exam details: **Subject**, **Course Code**, **Exam Title**, **Exam Date**, **Questions / Paper** (e.g. 5, 10, etc.), and **Number of Sets**.
3. Toggle **Randomize questions & options across sets** on or off.
4. Click **⚡ Generate Papers**.
5. Once generated:
   * Click **👁 View** to preview any paper directly in your browser.
   * Click **🖨 Bulk Print All (PDF)** to print all sets in one merged file.

### 3. Evaluating Submissions
1. Navigate to the **TA Grading** tab.
2. **For bulk evaluation**: Click **⬇ Download Template**, fill in student roll numbers and responses (`Q1..QN`), and click **📥 Upload Excel Sheet**.
3. **For individual evaluation**: Enter the student's paper code (e.g. `CD-2026-1`) and roll number, select the options marked on their sheet, and click **✓ Grade Student**.

### 4. Viewing Results
1. Navigate to the **Results** tab.
2. Review overall pass rate, score distribution, and top scores.
3. Use **Student Lookup** to inspect individual response breakdowns.
4. Click **⬇ Export CSV** to download the final grade sheet.

---

## 🛠 Configuration & Customization

* **Change Default Course & Subject**: Update `DEFAULT_SUBJECT_NAME` and `DEFAULT_COURSE_CODE` in [`app/models.py`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ%20generator/app/models.py).
* **Custom Logo**: Replace [`iit_logo.png`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ%20generator/iit_logo.png) in the root directory with your institution's logo.
* **Server Port / Host**: Modify `host` and `port` in [`run.py`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ%20generator/run.py).

---

## 📄 License
Internal Academic Tool — Developed for the **Department of Computer Science and Engineering, IIT (ISM) Dhanbad**.

