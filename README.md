# SCRAPE API

## DESKRIPSI
Platform scraping API untuk developer.
Kirim URL, dapat data JSON.
Target: researcher, startup, data team.

---

## CARA KERJA (UNTUK AI AGENT)

### Langkah 1: Baca README.md
Baca file ini untuk pahami project scope, fitur, aturan.

### Langkah 2: Baca report.md
Baca /mnt/hdd/ares-workspace/scrape-api/report.md

### Langkah 3: Tentukan Task
- Jika report.md **tidak ada atau kosong** → mulai RESEARCH
- Jika report.md **ada** → eksekusi task yang tertulis

### Langkah 4: Eksekusi

#### Jika RESEARCH (DELEGATE_TASK):
```
DELEGATE_TASK:
  goal: "deskripsi research"
  model: "deepseek-reasoner"
  context: "konteks tambahan"
  output: "lokasi output file"
```
- Research **minimal 30 menit** (TIMER WAJIB)
- Jangan terburu-buru
- Baca dokumentasi resmi
- Cari referensi dari multiple sumber
- Analisa competitor secara mendalam
- Bandingkan approaches
- Simpan SEMUA findings di data/research/
- Setelah selesai → update report.md dengan findings + rekomendasi next

#### Jika BUILD:
- Baca report.md untuk lihat spesifikasi
- Build sesuai spesifikasi
- Code harus jalan (bukan pseudocode)
- Error handling wajib ada
- Logging wajib ada
- Simpan di src/
- Setelah selesai → update report.md dengan hasil + rekomendasi next

#### Jika TEST & FIX:
- Baca report.md untuk lihat apa yang harus ditest
- Test semua fitur yang sudah dibuild
- Kalau ada bug → fix langsung
- Simpan hasil test di data/checkpoints/
- Setelah selesai → update report.md dengan hasil test + rekomendasi next

### Langkah 5: Update report.md
Setelah selesai task, update report.md dengan:
- Apa yang selesai
- Apa yang ditemukan
- Rekomendasi next task
- Checkpoint files

---

## TIMER RULES (WAJIB DIPATUHI)

### Cara Pakai Timer:
1. Catat waktu mulai di report.md
2. Format:
   ```
   ## TIMER:
   - Start: 2026-06-04 08:00:00
   - Minimal: 30 menit
   - Status: IN PROGRESS
   ```
3. Setelah selesai → update status ke COMPLETE
4. Simpan findings di data/research/

### Minimal Waktu per Task:
| Task       | Minimal Waktu | Keterangan |
|------------|---------------|------------|
| RESEARCH   | 30 menit      | Baca dokumentasi, cari referensi, analisa competitor |
| BUILD      | 1 jam         | Tulis code, test manual, error handling |
| TEST & FIX | 30 menit      | Unit test, integration test, fix bugs |

**PENTING:**
- JANGAN terburu-buru
- Research harus mendalam, bukan sekedar baca 1-2 artikel
- Build harus quality, bukan sekedar jalan
- Test harus comprehensive, bukan sekedar pass
- Fix harus proper, bukan sekedar workaround

---

## DELEGATE TASK RULES

### Kapan Pakai Delegate Task?
- Research mendalam (market, competitor, teknologi)
- Analisa kompleks (security audit, architecture review)
- Task yang butuh reasoning tinggi

### Kapan Gak Perlu?
- Build biasa (coding)
- Test & Fix biasa
- Documentation

### Format di report.md:
```markdown
## CURRENT TASK:
DELEGATE_TASK:
  goal: "Research market size dan competitor untuk scraping API"
  model: "deepseek-reasoner"
  context: "Analisa ScraperAPI, Bright Data, Oxylabs. Bandingkan harga, fitur, teknologi."
  output: "data/research/market-analysis.md"
```

### Rules:
1. Hanya untuk RESEARCH phase
2. Model: deepseek-reasoner
3. Minimal 30 menit eksekusi
4. Simpan hasil di data/research/
5. Return findings ke report.md

---

## TOOLS/SKILLS YANG BISA DIPAKE

### Research (DEEP ANALYSIS)
| Tool | Fungsi | Kapan Pakai |
|------|--------|-------------|
| `delegate_task` | Research mendalam dengan deepseek-reasoner | Market analysis, competitor analysis, technology research |
| `web_search` | Cari referensi online | Cari artikel, documentation, tutorials |
| `web_extract` | Baca konten website | Baca documentation, blog posts |
| `browser_navigate` | Buka website | Kunjungi competitor, cek fitur |
| `browser_snapshot` | Ambil screenshot | Bukti visual competitor |
| `read_file` | Baca file lokal | Baca code yang udah ada |
| `search_files` | Cari di codebase | Cari pattern, reference |

### Build (CODE DEVELOPMENT)
| Tool | Fungsi | Kapan Pakai |
|------|--------|-------------|
| `terminal` | Jalankan command | Install dependencies, run scripts |
| `write_file` | Tulis file baru | Buat module, config, documentation |
| `patch` | Edit file existing | Fix code, update config |
| `execute_code` | Run Python code | Test logic, data processing |
| `read_file` | Baca file | Cek code sebelum edit |

### Test & Fix (QUALITY ASSURANCE)
| Tool | Fungsi | Kapan Pakai |
|------|--------|-------------|
| `terminal` | Jalankan test | pytest, unittest, integration test |
| `read_file` | Baca error log | Cek log untuk debugging |
| `patch` | Fix code | Perbaiki bug |
| `browser_navigate` | Test web UI | Cek dashboard, API docs |
| `execute_code` | Run test script | Custom test scenarios |

### Automation (WORKFLOW)
| Tool | Fungsi | Kapan Pakai |
|------|--------|-------------|
| `cronjob` | Schedule tasks | Auto-run setiap jam |
| `delegate_task` | Parallel execution | Research + Build barengan |
| `process` | Background tasks | Long-running processes |

---

## FITUR (WAJIB SELESAI MINGGU 1)

### Core Engine
- [ ] Scrape halaman web statis
- [ ] Scrape halaman web dinamis (JavaScript)
- [ ] Extract data berdasarkan selector
- [ ] Auto-detect data structure
- [ ] Handle pagination

### API Layer
- [ ] REST API endpoint
- [ ] /scrape → single URL
- [ ] /batch → multiple URL
- [ ] /status → check job status
- [ ] Response: JSON, CSV

### Auth & Security
- [ ] API key authentication
- [ ] Rate limiting (per key)
- [ ] Input validation
- [ ] Error handling
- [ ] CORS support

### Features
- [ ] Proxy rotation
- [ ] User-agent rotation
- [ ] Retry mechanism
- [ ] Webhook callback
- [ ] Scheduler (auto-scrape)
- [ ] Data export (JSON, CSV)

### Dashboard
- [ ] Usage statistics
- [ ] API key management
- [ ] Job history
- [ ] Error logs
- [ ] Billing info

### Billing
- [ ] Free tier (100 req/hari)
- [ ] Starter ($19/bulan - 10K req)
- [ ] Pro ($49/bulan - 50K req)
- [ ] Stripe integration

---

## TECH STACK

### Backend
- FastAPI (Python)
- cdp-browser-use (scraping engine)
- SQLite (database awal)
- Redis (caching + rate limit)
- Celery (async task)
- Docker (containerization)

### Frontend
- React/Next.js
- Tailwind CSS
- Recharts (analytics)

### Infrastructure
- Render.com (deploy)
- Cloudflare (CDN + DNS)
- Stripe (billing)
- Resend (email)

---

## ATURAN DEVELOPMENT

### Folder Structure
```
/mnt/hdd/ares-workspace/scrape-api/
├── README.md ← rules, fitur, alur (INI FILE UTAMA)
├── report.md ← status, task, checkpoint (UPDATE SETIAP SELESAI)
├── src/ ← source code
│   ├── main.py ← FastAPI app
│   ├── scraper/ ← scraping engine
│   ├── api/ ← API endpoints
│   ├── auth/ ← authentication
│   ├── models/ ← database models
│   ├── utils/ ← helper functions
│   └── config/ ← configuration
├── tests/ ← test files
│   ├── unit/ ← unit tests
│   ├── integration/ ← integration tests
│   └── e2e/ ← end-to-end tests
├── data/
│   ├── research/ ← hasil research
│   └── checkpoints/ ← progress
├── docs/ ← dokumentasi
│   ├── api/ ← API documentation
│   └── architecture/ ← architecture docs
├── config/ ← configuration files
├── docker/ ← docker files
│   ├── Dockerfile
│   └── docker-compose.yml
└── scripts/ ← automation scripts
    ├── deploy.sh
    └── test.sh
```

### Rules
1. **BACA README.md DULU** sebelum mulai apapun
2. **BACA report.md** untuk lihat task saat ini
3. Semua file di dalam folder project
4. **UPDATE report.md** setiap selesai task
5. Simpan checkpoint di data/checkpoints/
6. Research dulu baru build
7. Test semua fitur sebelum lanjut
8. Fix bugs sebelum fitur baru
9. Documentasi update setiap fitur

### Quality Gates
- Code harus bisa jalan (bukan pseudocode)
- Test harus pass sebelum commit
- Error handling wajib ada
- Logging wajib ada
- Documentation wajib update

---

## ALUR DEVELOPMENT (77 TASKS, 7 HARI)

### HARI 1 (KAMIS) - 11 TASKS
| Jam  | Fase       | Task                                      |
|------|------------|-------------------------------------------|
| 08:00 | Research  | Market size, demand analysis              |
| 10:00 | Research  | Competitor analysis (ScraperAPI, Bright Data) |
| 12:00 | Build     | Setup project structure                   |
| 14:00 | Build     | Core scraper engine (statik)              |
| 16:00 | Test & Fix| Test scraper manual                       |
| 18:00 | Research  | Teknologi scraping (headless browser, proxy) |
| 20:00 | Build     | Scraper engine (dinamis/JavaScript)       |
| 22:00 | Test & Fix| Test scraper dinamis                      |
| 00:00 | Research  | API design patterns                       |
| 02:00 | Build     | API skeleton (FastAPI)                    |
| 04:00 | Test & Fix| Test API skeleton                         |

### HARI 2 (JUMAT) - 11 TASKS
| Jam  | Fase       | Task                                      |
|------|------------|-------------------------------------------|
| 08:00 | Research  | Authentication methods (API key, OAuth)   |
| 10:00 | Research  | Rate limiting algorithms                  |
| 12:00 | Build     | API key authentication                    |
| 14:00 | Build     | Rate limiting                             |
| 16:00 | Test & Fix| Test auth + rate limiting                 |
| 18:00 | Research  | Input validation best practices           |
| 20:00 | Build     | Input validation + error handling         |
| 22:00 | Test & Fix| Test validation + error handling          |
| 00:00 | Research  | Dashboard UI/UX design                    |
| 02:00 | Build     | Basic dashboard (React)                   |
| 04:00 | Test & Fix| Test dashboard                            |

### HARI 3 (SABTU) - 11 TASKS
| Jam  | Fase       | Task                                      |
|------|------------|-------------------------------------------|
| 08:00 | Research  | Billing integration (Stripe API)          |
| 10:00 | Research  | Subscription models                       |
| 12:00 | Build     | Stripe integration                        |
| 14:00 | Build     | Subscription management                   |
| 16:00 | Test & Fix| Test billing flow                         |
| 18:00 | Research  | Monitoring & logging best practices       |
| 20:00 | Build     | Logging system                            |
| 22:00 | Test & Fix| Test logging                              |
| 00:00 | Research  | Error tracking (Sentry)                   |
| 02:00 | Build     | Sentry integration                        |
| 04:00 | Test & Fix| Test error tracking                       |

### HARI 4 (MINGGU) - 11 TASKS
| Jam  | Fase       | Task                                      |
|------|------------|-------------------------------------------|
| 08:00 | Research  | Proxy rotation techniques                 |
| 10:00 | Research  | Anti-detection methods                    |
| 12:00 | Build     | Proxy rotation                            |
| 14:00 | Build     | User-agent rotation                       |
| 16:00 | Test & Fix| Test anti-detection                       |
| 18:00 | Research  | Webhook implementation                    |
| 20:00 | Build     | Webhook system                            |
| 22:00 | Test & Fix| Test webhook                              |
| 00:00 | Research  | Retry mechanisms                          |
| 02:00 | Build     | Retry logic                               |
| 04:00 | Test & Fix| Test retry                                |

### HARI 5 (SENIN) - 11 TASKS
| Jam  | Fase       | Task                                      |
|------|------------|-------------------------------------------|
| 08:00 | Research  | Scheduler design (cron, queue)            |
| 10:00 | Research  | Async task processing (Celery)            |
| 12:00 | Build     | Scheduler feature                         |
| 14:00 | Build     | Celery integration                        |
| 16:00 | Test & Fix| Test scheduler                            |
| 18:00 | Research  | Data export formats (JSON, CSV)           |
| 20:00 | Build     | Export feature                            |
| 22:00 | Test & Fix| Test export                               |
| 00:00 | Research  | Caching strategies (Redis)                |
| 02:00 | Build     | Redis integration                         |
| 04:00 | Test & Fix| Test caching                              |

### HARI 6 (SELASA) - 11 TASKS
| Jam  | Fase       | Task                                      |
|------|------------|-------------------------------------------|
| 08:00 | Research  | Security audit checklist                  |
| 10:00 | Research  | OWASP Top 10                              |
| 12:00 | Build     | Security hardening                        |
| 14:00 | Build     | CORS, CSP headers                         |
| 16:00 | Test & Fix| Penetration test                          |
| 18:00 | Research  | API documentation standards (OpenAPI)     |
| 20:00 | Build     | API documentation                         |
| 22:00 | Test & Fix| Test documentation                        |
| 00:00 | Research  | Docker best practices                     |
| 02:00 | Build     | Dockerfile + docker-compose               |
| 04:00 | Test & Fix| Test Docker                               |

### HARI 7 (RABU) - 11 TASKS
| Jam  | Fase       | Task                                      |
|------|------------|-------------------------------------------|
| 08:00 | Research  | Deployment strategies                     |
| 10:00 | Research  | CI/CD pipeline                            |
| 12:00 | Build     | Deploy scripts                            |
| 14:00 | Build     | CI/CD setup                               |
| 16:00 | Test & Fix| Test deploy                               |
| 18:00 | Research  | Performance optimization                  |
| 20:00 | Build     | Performance tuning                        |
| 22:00 | Test & Fix| Load test                                 |
| 00:00 | Research  | Final review checklist                    |
| 02:00 | Build     | Final polish                              |
| 04:00 | Test & Fix| Full integration test                     |

---

## TARGET CAPABILITY

### Minimum Viable Product
- Bisa scrape 1 URL → dapat JSON
- API key auth jalan
- Rate limiting jalan
- Basic dashboard jalan
- Billing jalan

### Stretch Goals
- Proxy rotation
- Webhook callback
- Scheduler
- Multi-format export
- Advanced dashboard

### Quality Target
- 90% test coverage
- <500ms response time
- 99.9% uptime
- Zero critical bugs
- Documentation lengkap

---

## MONETIZE

### Free Tier
- 100 request/hari
- 5 target
- Basic support

### Starter ($19/bulan)
- 10K request/bulan
- 20 target
- Webhook
- Email support

### Pro ($49/bulan)
- 50K request/bulan
- Semua target
- Proxy rotation
- Priority support

### Enterprise ($199+/bulan)
- Unlimited
- Dedicated proxy
- SLA
- Custom integration
