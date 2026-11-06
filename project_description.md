# 🏛️ IIT (ISM) Dhanbad — Exam Paper Generator & Grading System
## Comprehensive Project Description, Architectural Features & Change Log

---

## 📌 Executive Overview

The **IIT (ISM) Dhanbad Exam Paper Generator & Grading System** is an enterprise-grade academic assessment automation platform designed specifically for the **Department of Computer Science and Engineering** at the **Indian Institute of Technology (Indian School of Mines), Dhanbad**.

The system addresses the operational bottlenecks of university-level exam administration:
1. **Academic Integrity & Anti-Copying**: Eliminates student answer copying in large examination halls by producing individualized, randomized examination papers where both question selection and multiple-choice options are shuffled per student while maintaining equivalent test difficulty across all papers.
2. **Duplex Print-Optimized Formatting**: Typesets camera-ready, institutional examination sheets via LaTeX (`pdflatex`) adhering strictly to official IIT (ISM) Dhanbad branding, departmental formatting guidelines, mathematical formula rendering, and tight 1-page or 2-page duplex layout constraints (preventing page spillovers during bulk double-sided printing).
3. **Multi-Course & Multi-Bank Isolation**: Supports multiple course instances simultaneously (e.g. *Theory Courses* like `Compiler Design - NCSC302` alongside *Practical Labs* like `Compiler Design Lab - NCSC302-CSC302`), each with independent topic pools, question banks, paper prefixes, and generated bundles.
4. **End-to-End Evaluation & Archival**: Accommodates automated answer key generation, TA paper scoring with option-permutation resolution, bulk grade export (CSV/Excel), and master archiving sheets for institute records.

---

## 🏗️ System Architecture & Codebase Structure

The application follows a clean, decoupled architecture built on **FastAPI (Python 3.10+)** on the backend and modern vanilla modular JavaScript (ES6+) with institutional light styling on the frontend.

```text
QUIZ generator/
├── app/
│   ├── config.py                 # Centralized settings (Pydantic & python-dotenv)
│   ├── database.py               # SQLite schema, WAL mode, get_db() context manager
│   ├── main.py                   # FastAPI app entry point & structured logging
│   ├── models.py                 # Pydantic schemas (Bank, Pool, Question, Paper, Grade)
│   ├── routers/
│   │   ├── banks.py              # Bank CRUD, pool metadata, and storage cleanup
│   │   ├── questions.py          # Question CRUD, LaTeX/Excel file imports, stats
│   │   ├── papers.py             # Paper generation dispatch, viewing, PDF/LaTeX downloads
│   │   ├── grading.py            # Student response grading and evaluation
│   │   └── results.py            # Gradebook reporting, distribution analytics, CSV export
│   ├── services/
│   │   ├── generator.py          # Anti-collision algorithm, weighted sampling, option shuffler
│   │   ├── grader.py             # Grading engine resolving shuffled options to raw values
│   │   ├── latex_gen.py          # Jinja2 LaTeX compilation, pdflatex runner, Poppler fallback
│   │   ├── latex_import.py       # Robust Master LaTeX parser (tabularx, lstlisting, verb)
│   │   ├── templates_service.py  # Downloadable Master LaTeX (.tex) & Excel (.xlsx) builders
│   │   └── export_service.py     # Color-coded Excel workbook & CSV answer key exporters
│   └── templates/
│       ├── paper.tex.j2          # Student question paper LaTeX template (Duplex 2-page)
│       ├── bulk_papers.tex.j2    # Merged bulk PDF bundle LaTeX template
│       ├── master_paper.tex.j2   # Master question paper template (without answers)
│       └── answer_keys.tex.j2    # Master answer keys sheet LaTeX template
├── static/
│   ├── index.html                # Single-page interface with tabbed views & accessible modals
│   ├── css/
│   │   └── style.css             # Oxford Navy / Academic Gold theme, KaTeX styling, utility classes
│   ├── img/
│   │   └── iit_logo.png          # Official IIT (ISM) Dhanbad institutional seal
│   └── js/
│       ├── app.js                # Core app state, bank switcher, toast alerts, API client
│       ├── admin.js              # UI orchestrator, dropdown controls, math rendering triggers
│       ├── banks.js              # Bank switching, creation modal, and deletion confirmation
│       ├── pools.js              # Topic pool tabs, pool selector, add/rename/delete pool
│       ├── questions.js          # Question CRUD, live search, type filter, file import modals
│       ├── generator.js          # Exam presets, pool question sliders, generation trigger
│       ├── papers.js             # Paper listing, Document View vs. Live PDF Viewer toggle
│       ├── answers.js            # Answer key grid view, CSV/Excel/PDF export triggers
│       ├── grading.js            # Interactive TA grading interface
│       └── results.js            # Gradebook table, score distribution charts, export
├── tests/
│   ├── test_latex_import.py      # LaTeX syntax, math, lstlisting, and answer comment tests
│   ├── test_generator.py         # UID generation, weighted sampling, and option shuffling tests
│   ├── test_grader.py            # Scoring logic with option permutation resolution tests
│   ├── test_database.py          # Context manager commit/rollback tests
│   ├── test_services.py          # Template and export service validation tests
│   ├── test_banks.py             # Bank configuration and directory partitioning tests
│   └── test_api_models.py        # Pydantic validation tests
├── generated_papers/             # Output directory partitioned by bank (bank_1/, bank_21/)
├── pyproject.toml                # Project build system & Ruff linter configuration
├── requirements.txt              # Production dependencies
├── quiz.db                       # SQLite database (WAL mode)
└── run.py                        # Local development runner
```

---

## ⚡ Complete Feature Breakdown

### 1. Multi-Bank & Course Isolation
- **Independent Course Repositories**: Create and manage multiple question banks independently (e.g. *Compiler Design* Theory vs. *Compiler Design Lab* Practical).
- **Per-Bank Metadata**: Each bank maintains its unique subject name, official course code (e.g. `NCSC302`), paper prefix (e.g. `CD`, `CDL`), and custom pool configuration.
- **Hierarchical Storage Isolation**: Generated PDFs and bundles are automatically stored under dedicated subdirectories (`generated_papers/bank_{id}/`), eliminating file collision across courses.
- **Safe Bank Deletion**: Deleting a bank automatically removes all associated questions, generated papers, database records, and physical PDF caches cleanly via `shutil.rmtree`.

### 2. Variable Topic Pools
- **Dynamic Pool Allocation**: Supports any number of pools (1 to 50 pools per bank) rather than a rigid fixed count.
- **Pool Management**: Create new pools on the fly, rename existing pools (e.g., *Pool 1: Lexical Analysis*, *Pool 2: Syntax Analysis*), or delete pools along with their questions.
- **Live Coverage Dashboard**: Visual progress bars in the sidebar display question counts per pool in real-time, helping instructors identify under-populated topic areas.

### 3. Question Bank & Smart LaTeX / Excel Importers
- **Multi-Format Question Support**:
  - **Objective (MCQs)**: 4 options with exact correct option tracking.
  - **Subjective**: Descriptive and multi-step programming/theory problems with custom mark allocations.
- **Live Search & Type Filtering**: Instant search across question text, option choices, and topics with real-time result counters and single-click clear.
- **Client-Side KaTeX Formula Rendering**: Full rendering support for inline math (`$...$`, `\(...\)`) and display math (`$$...$$`, `\[...\]`).
- **Monospace Code Snippets**: Full formatting for `\begin{lstlisting}` code blocks and `\texttt{...}` inline identifiers.
- **Master LaTeX Parser**:
  - Ingests raw LaTeX documents containing `\begin{tabularx}`, `\begin{enumerate}`, and `\hfill \textbf{[2 Marks]}` tags.
  - Extracts correct answers from inline comments (`% ans: B` or `% answer: C`), bolded labels (`\textbf{(b)}`), or trailing answer key sections.
  - Automatically sanitizes verbatim blocks (`\verb|...|`) into `\texttt{...}` with proper LaTeX escaping (`\%`, `\_`, `\&`, `\textbackslash{}`), preventing compilation crashes inside tables.
  - **Interactive Pool Distribution Modal**: Choose to distribute imported questions evenly across selected existing pools or auto-generate new pools.
- **Multi-Sheet Excel Importer**: Imports Excel workbooks (`.xlsx`) with multiple sheets (one sheet per TA or topic pool).
- **One-Click Template Downloads**: Download standardized Excel templates or publication-ready Master LaTeX `.tex` starter files directly from the UI.

### 4. Randomized Paper Generation Engine
- **Sequential Standardized UIDs**: Formats clean, deterministic codes (e.g. `CD-2026-1` to `CD-2026-150`).
- **Least-Used Weighted Sampling**:
  $$\text{Weight} = \frac{1}{\text{times\_used} + 1}$$
  Guarantees that questions used least frequently in past exams are prioritized, minimizing question fatigue across batches.
- **Zero In-Paper Collisions**: Strict sampling without replacement ensures no student ever receives duplicate questions.
- **Anti-Copying Option Permutation**: Options (a, b, c, d) are shuffled independently per paper while preserving mathematical and text integrity.
- **Flexible Drawing Modes**:
  - *Balanced Mode*: Automatically distributes questions equally across all selected pools.
  - *Custom Slider Mode*: Allows the instructor to specify the exact number of questions drawn from each specific pool.
- **Exam Presets**:
  - *Quiz / Mid-Term*: 5 questions, 2 marks each, 30 minutes, randomized shuffling on.
  - *End-Semester Examination*: Comprehensive, 50 marks, 3 hours, standardized master mode.

### 5. LaTeX Typesetting & Duplex Print Optimization
- **Duplex 2-Page Constraint Enforcement**:
  - Specifically engineered LaTeX geometry (`margin=1.1cm`, `\ttfamily\scriptsize` listings, `aboveskip=2.5pt`, `belowskip=2.5pt`, `\vspace{0.16cm}`) ensuring comprehensive 10-question exams with code blocks fit on **exactly 2 pages** (1 physical sheet printed double-sided).
  - Eliminates orphan questions spilling over to a 3rd page.
- **Institutional IIT (ISM) Dhanbad Header**: Includes the official institute crest, Department of Computer Science & Engineering banner, course metadata, student name/admission number blanks, and instructions box.
- **Bulk Printing Bundle**: Compiles all student papers into a single contiguous multi-page PDF (`all_papers_bundle.pdf`, e.g., exactly 300 pages for 150 students).
- **Master Question Paper**: Compiles an archival question paper containing all bank questions without highlighted answers.
- **Dual-Mode Paper Previewer**: Embedded modal with instant tabs to toggle between high-fidelity HTML Document View and Live interactive PDF Viewer.

### 6. Answer Keys, Grading & Analytics
- **Master Answer Key Sheet**: Compiles tabular answer keys (Q1..QN) for all generated papers into a printable TA grading sheet.
- **Excel & CSV Export**:
  - Generates color-coded Excel sheets with individual columns for each question, styled with distinct pastels (A = soft blue, B = soft green, C = soft amber, D = soft purple).
  - Clean CSV format for integration with institutional grading databases.
- **Interactive TA Grading Interface**:
  - Select paper code and mark student choices with a single click.
  - Automatically maps student's chosen option letter back through that specific paper's permutation to evaluate against the master key.
- **Gradebook & Analytics**:
  - Roll number assignment and student result ledger.
  - Real-time score distribution bar charts and difficulty analytics.
  - Single-click CSV grade export for Dean (Academic) records.

---

## 📝 Chronological Change Log & Enhancements

### Phase 1: Core Foundation & Initial Capabilities
- Initial single-bank paper generator with SQLite backend and basic LaTeX Jinja2 templating.
- Implementation of weighted question selection (`1 / (times_used + 1)`).
- Implementation of 4-way option shuffling per student paper.
- Excel `.xlsx` multi-sheet parser for question imports.

### Phase 2: Multi-Bank & Dynamic Pool Architecture
- Extended database schema to support multiple independent banks (`banks` table with foreign key relations).
- Added paper code prefixing (`CD` for Theory, `CDL` for Lab, etc.).
- Replaced fixed 5-pool limitation with dynamic pool creation (`pools` table), supporting arbitrary pool quantities.
- Added Bank Switcher dropdown and pool coverage bar charts in the sidebar.
- Added bank creation modal with course metadata fields and initial pool count selector.

### Phase 3: Master LaTeX Ingestion & Lab Examination Support
- Developed raw LaTeX parser in [`app/services/latex_import.py`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ%20generator/app/services/latex_import.py) to parse raw `.tex` files.
- Added parser support for `% ans: <letter>` comments, `\textbf{(b)}` bold indicators, and trailing Answer Key sections.
- Created `verb_to_texttt()` transformation to prevent LaTeX `\verb` crashes inside `tabularx` option cells.
- Parsed and inserted 45 questions for **Bank 2: Compiler Design Lab (ID 21)** across 3 pools (*C Programming/Algorithms*, *Lex/Flex*, *Yacc/Bison*).
- Added downloadable Master LaTeX starter template (`/api/questions/template/latex`).

### Phase 4: Duplex 2-Page Layout & UI Refinements
- Resolved 3-page overflow in code-heavy lab papers by tuning LaTeX geometry, font sizing, and row spacing in [`app/templates/paper.tex.j2`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ%20generator/app/templates/paper.tex.j2) and [`app/templates/bulk_papers.tex.j2`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ%20generator/app/templates/bulk_papers.tex.j2).
- Generated and verified 150 student papers (`CDL-2026-1` to `CDL-2026-150`) fitting strictly on 2 pages each, with bulk PDF bundle measuring exactly 300 pages ($150 \times 2$).
- Integrated KaTeX CDN for real-time mathematical expression rendering in question cards and modals.
- Added code block formatting (`.q-code-snippet` and `.q-inline-code`).
- Added Question Bank live search input with type filter dropdown and count badge.
- Added Document View / Live PDF Viewer tabbed toggle in the paper preview modal.
- Integrated official high-resolution IIT (ISM) Dhanbad seal (`static/img/iit_logo.png`).

### Phase 5: Architectural Refactoring & Safety Net
- **Frontend Decomposition**: Refactored the 1,614-line monolith `admin.js` into focused, single-responsibility ES6 modules:
  - `banks.js`: Bank switching, creation modal, delete confirmation.
  - `pools.js`: Dynamic pool tabs, pool select dropdowns, pool CRUD.
  - `questions.js`: Question rendering, search/filter, KaTeX render triggers, LaTeX/Excel imports.
  - `generator.js`: Form state, paper type presets, per-pool question sliders, generate dispatch.
  - `papers.js`: Generated paper table, paper preview modal, PDF preview iframe, paper deletion.
  - `admin.js`: Slim 110-line central orchestrator and global event coordinator.
- **Frontend Modernization (Adaptive App Shell & Material Design 3)**:
  - Replaced the 280px left sidebar with a slim, glassmorphic **Top Header (`.app-header`)** for desktop that maximizes horizontal workspace canvas to 100%.
  - Added an ergonomic **Mobile Bottom Navigation Bar (`.mobile-bottom-nav`)** that automatically activates on viewports $\le 860\text{px}$ for cross-platform app bundling (Electron/Tauri/Mobile Web).
  - Adopted a **Material Design 3 Modern Teal / Cyan** palette with full, zero-FOUC **Dark Mode** toggle and `localStorage` persistence.
  - Relocated paper generation information into an on-demand **"ℹ️ How It Works"** dialog, expanding the paper generator form to full width.
  - Redesigned the **Add/Edit Question Modal** into an ergonomic 820px layout with a dedicated metadata card, full-width options preventing truncation, and one-click "Correct" radio pills.
  - Built an **Interactive Question Import Staging & Dry-Run Preview Modal** with duplicate conflict resolution (`Skip` vs `Overwrite`), subjective LaTeX problem parsing, and Outcome-Based Education (OBE) difficulty/CO tag extraction.
- **Backend Service Extraction**:
  - Extracted template builders from `questions.py` into [`app/services/templates_service.py`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ generator/app/services/templates_service.py).
  - Extracted openpyxl cell styling and CSV answer key streaming from `papers.py` into [`app/services/export_service.py`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ%20generator/app/services/export_service.py).
  - Centralized application constants, paths, and defaults into [`app/config.py`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ%20generator/app/config.py).
- **Database Context Management**: Added `@contextmanager def get_db()` in [`app/database.py`](file:///media/randomx/Windows/Users/nmea/Desktop/Compiler%20Design/QUIZ%20generator/app/database.py) with auto-commit, automatic rollback on error, and guaranteed connection closure.
- **Storage Partitioning**: Partitioned `generated_papers/` by bank ID (`generated_papers/bank_{id}/`) with backward-compatibility fallbacks.
- **Standardized Logging**: Replaced bare prints with structured Python standard `logging`.
- **Automated Test Suite**: Expanded standard `unittest` suite to **33 tests** covering LaTeX parsing, OBE tags, conflict resolution, UID generation, anti-collision weighted sampling, TA grading, and transactions.
- **Linting & Packaging**: Added `pyproject.toml` with Ruff configuration.

---

## 🖥️ Hardware Requirements & Sizing Specifications

| Component | Minimum (Lab / Testing) | Recommended (Department Production) | Institutional Enterprise |
| :--- | :--- | :--- | :--- |
| **Target Scale** | 1–100 students, 1 course | 100–600 students, bulk PDF generation | 1,000+ students, multiple exams |
| **CPU (vCPUs)** | **1 vCPU** (2.0 GHz+) | **2 vCPUs** (parallel LaTeX + API) | **4 vCPUs** (dedicated queue workers) |
| **RAM** | **1 GB – 2 GB** (+ 1GB swap) | **2 GB – 4 GB** | **8 GB** |
| **Disk (SSD/NVMe)**| **10 GB – 15 GB** | **25 GB – 40 GB** | **80 GB+** |
| **Network** | 100 Mbps | 1 Gbps | 1 Gbps |
| **Operating System**| Ubuntu 22.04 / 24.04 LTS | Ubuntu 22.04 / 24.04 LTS | Ubuntu 22.04 / 24.04 LTS / Debian 12 |

### Performance Characteristics:
- **`pdflatex` compilation**: ~0.4s – 0.7s per paper, ~45 MB RAM peak.
- **`pdfunite` merging**: ~0.2s for 150 papers (300 pages), ~100 MB RAM peak.
- **Database (SQLite WAL)**: <25 MB RAM, capable of >10,000 read queries/sec.

---

## 📊 Verification & Test Metrics

Running the automated test suite locally:
```bash
$ .venv/bin/python -m unittest discover tests
.................................
----------------------------------------------------------------------
Ran 33 tests in 0.038s

OK
```

### Current Database Status
| Bank ID | Course Name | Code Prefix | Active Pools | Questions | Generated Papers |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | Compiler Design (Theory) | `CD` | 5 Pools | 74 | 150 Papers |
| **21** | Compiler Design Lab (Practical) | `CDL` | 3 Pools | 45 | 150 Papers |

---

## 🚀 Deployment & Operations

### Local Development
```bash
# 1. Activate Python virtual environment
source .venv/bin/activate  # On Linux/macOS
# or .venv\Scripts\activate on Windows

# 2. Run test suite
python -m unittest discover tests

# 3. Launch the development server
python run.py
# Application is live at: http://127.0.0.1:8000
```

### Institutional Production Deployment
- **Docker Container**: Packages FastAPI with `texlive-latex-base`, `texlive-latex-extra`, and `poppler-utils` in a lightweight Alpine/Debian image.
- **Reverse Proxy**: Nginx with SSL termination (`https://exam.iitism.ac.in`) reverse proxying to Uvicorn workers on port 8000.
- **Environment Overrides**: All institutional metadata, ports, and directories are customizable via `.env` without modifying source code.
