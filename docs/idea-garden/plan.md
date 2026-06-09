# 想法花园 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a zero-friction "experiment assistant" PWA that reframes starting anything as a low-stakes experiment, with a lightweight companion that grows with each check-in.

**Architecture:** Next.js 15 App Router full-stack app. SQLite via better-sqlite3 for local persistence. Server Actions for all mutations. Client components only where animation or multi-step state is required.

**Tech Stack:** Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, better-sqlite3, Framer Motion, next-pwa, @anthropic-ai/sdk (Haiku 4.5), Vitest, @testing-library/react

**Scope:** Phase 1 MVP — Features 1-5 + PWA. No 灵感潜水池 (Phase 2).

**Project location:** Create as a sibling directory to `get-to-know-yourself`, e.g. `~/Desktop/AI Projects/idea-garden/`

---

## File Map

```
idea-garden/
├── app/
│   ├── layout.tsx                Root layout (PWA meta, fonts, theme)
│   ├── page.tsx                  主屏 (companion + check-in + bubbles)
│   ├── capture/page.tsx          快捷捕捉 (single input, < 10s)
│   ├── activate/page.tsx         激活流 server shell
│   ├── activate/ActivateFlow.tsx 激活流 5-step client component
│   ├── experiment/page.tsx       当前实验 + 签到 + 荣耀谢幕
│   ├── experiment/CheckinPanel.tsx  3-tier check-in client component
│   ├── experiment/CoolingPanel.tsx  荣耀谢幕 client component
│   ├── archive/page.tsx          档案馆 book shelf
│   ├── archive/[id]/page.tsx     单次实验详情
│   └── api/ai/route.ts           AI suggestions endpoint (Claude Haiku)
├── components/
│   ├── companion/Companion.tsx   Renders emoji per type/variant/stage
│   ├── idea-bubble/IdeaBubble.tsx       Single bubble chip
│   └── idea-bubble/IdeaBubbleList.tsx   Animated bubble group
├── lib/
│   ├── db.ts                     SQLite singleton + initSchema()
│   ├── ai.ts                     generateActivationSuggestions / generateArchiveSuggestions
│   └── daily-prompt.ts           getDailyPrompt(date) — deterministic rotation
├── actions/
│   ├── ideas.ts                  createIdea, listFloatingIdeas, updateIdeaStatus
│   ├── experiments.ts            createDraft, activateExperiment, checkin, checkAndStartCooling, completeExperiment, getActiveExperiment
│   └── archives.ts               createArchive, listArchives, getArchive
├── types/
│   └── index.ts                  All shared TypeScript interfaces
└── public/
    ├── manifest.json             PWA manifest
    └── icons/                    192×192 + 512×512 PNG icons
```

---

## Task 0: Project Scaffold

**Files:**
- Create: `idea-garden/` (new Next.js project)
- Create: `idea-garden/.env.local`

- [ ] **Step 1: Bootstrap Next.js 15 app**

```bash
cd "~/Desktop/AI Projects"
npx create-next-app@latest idea-garden \
  --typescript --tailwind --eslint --app \
  --no-src-dir --import-alias "@/*"
cd idea-garden
```

- [ ] **Step 2: Install runtime dependencies**

```bash
npm install better-sqlite3 @anthropic-ai/sdk framer-motion next-pwa lucide-react
npm install -D @types/better-sqlite3
```

- [ ] **Step 3: Install shadcn/ui**

```bash
npx shadcn@latest init
# Choose: Default style, Zinc base color, CSS variables yes
npx shadcn@latest add button input textarea slider badge card
```

- [ ] **Step 4: Install test dependencies**

```bash
npm install -D vitest @vitejs/plugin-react @testing-library/react @testing-library/user-event jsdom @testing-library/jest-dom
```

- [ ] **Step 5: Add vitest config**

Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, '.') },
  },
})
```

Create `vitest.setup.ts`:
```typescript
import '@testing-library/jest-dom'
```

Add to `package.json` scripts:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 6: Create .env.local**

```bash
cat > .env.local << 'EOF'
ANTHROPIC_API_KEY=your_key_here
DB_PATH=./data/idea-garden.db
EOF
mkdir -p data
echo "data/*.db" >> .gitignore
```

- [ ] **Step 7: Verify scaffold**

```bash
npm run dev
# Should open http://localhost:3000 without errors
```

---

## Task 1: Types

**Files:**
- Create: `types/index.ts`
- Create: `types/index.test.ts`

- [ ] **Step 1: Write type validation test**

Create `types/index.test.ts`:
```typescript
import { describe, it, expectTypeOf } from 'vitest'
import type { Idea, FearTag, CompanionVariant } from './index'

describe('types', () => {
  it('Idea has required fields', () => {
    expectTypeOf<Idea>().toHaveProperty('id')
    expectTypeOf<Idea>().toHaveProperty('content')
    expectTypeOf<Idea>().toHaveProperty('status')
    expectTypeOf<Idea>().toHaveProperty('capturedAt')
  })

  it('FearTag is a union of 4 values', () => {
    const tag: FearTag = 'tired'
    expectTypeOf(tag).toMatchTypeOf<FearTag>()
  })

  it('CompanionVariant covers plant and animal variants', () => {
    const p: CompanionVariant = 'flower'
    const a: CompanionVariant = 'cat'
    expectTypeOf(p).toMatchTypeOf<CompanionVariant>()
    expectTypeOf(a).toMatchTypeOf<CompanionVariant>()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npm test -- types
# Expected: Cannot find module './index'
```

- [ ] **Step 3: Create types/index.ts**

```typescript
export type IdeaStatus = 'floating' | 'activating' | 'in_experiment' | 'frozen' | 'archived'
export type FearTag = 'tired' | 'no_time' | 'not_good_enough' | 'cant_persist'
export type CompanionType = 'plant' | 'animal'
export type PlantVariant = 'flower' | 'cactus' | 'bamboo' | 'moss'
export type AnimalVariant = 'cat' | 'rabbit' | 'totoro' | 'creature'
export type CompanionVariant = PlantVariant | AnimalVariant
export type CompanionStage = 0 | 1 | 2 | 3 | 4 | 5
export type EnergyTag = 'high' | 'medium' | 'low'
export type ExperimentStatus = 'active' | 'cooling' | 'completed'
export type DurationDays = 3 | 7 | 14 | 21

export interface Idea {
  id: string
  content: string
  status: IdeaStatus
  capturedAt: string
}

export interface ExperimentDraft {
  id: string
  ideaId: string
  why: string
  fearTags: FearTag[]
  firstStep: string
  durationDays: DurationDays
  companionType: CompanionType
  companionVariant: CompanionVariant
  createdAt: string
}

export interface Experiment {
  id: string
  ideaId: string
  draftId: string
  companionStage: CompanionStage
  startDate: string
  durationDays: number
  status: ExperimentStatus
}

export interface DailyLog {
  id: string
  experimentId: string
  date: string
  minData: string | null
  energyTag: EnergyTag | null
  createdAt: string
}

export interface Archive {
  id: string
  experimentId: string
  ideaId: string
  bestMoment: string
  learned: string
  restartStep: string
  exploredAt: string
  resurfaceAt: string
}

export interface ExperimentWithDetails extends Experiment {
  draft: ExperimentDraft
  idea: Idea
  dailyLogs: DailyLog[]
}

export interface AiSuggestions {
  why: [string, string, string]
  firstStep: [string, string, string]
}

export interface ArchiveSuggestions {
  bestMoment: [string, string, string]
  learned: [string, string, string]
  restartStep: [string, string, string]
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
npm test -- types
```

- [ ] **Step 5: Commit**

```bash
git add types/
git commit -m "feat: add shared TypeScript types"
```

---

## Task 2: Database Layer

**Files:**
- Create: `lib/db.ts`
- Create: `lib/db.test.ts`

- [ ] **Step 1: Write failing DB test**

Create `lib/db.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { initSchema, getDb } from './db'

describe('db', () => {
  let db: ReturnType<typeof getDb>

  beforeEach(() => {
    process.env.DB_PATH = ':memory:'
    // Reset singleton for in-memory test DB
    jest.resetModules?.()
    db = getDb()
    initSchema(db)
  })

  it('creates all required tables', () => {
    const tables = db
      .prepare("SELECT name FROM sqlite_master WHERE type='table'")
      .all() as { name: string }[]
    const names = tables.map(t => t.name)
    expect(names).toContain('ideas')
    expect(names).toContain('experiments')
    expect(names).toContain('experiment_drafts')
    expect(names).toContain('daily_logs')
    expect(names).toContain('archives')
  })

  it('inserts and retrieves an idea', () => {
    db.prepare(
      'INSERT INTO ideas (id, content, status, captured_at) VALUES (?, ?, ?, ?)'
    ).run('test-1', 'Learn to surf', 'floating', new Date().toISOString())

    const row = db.prepare('SELECT * FROM ideas WHERE id = ?').get('test-1') as any
    expect(row.content).toBe('Learn to surf')
    expect(row.status).toBe('floating')
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- db
```

- [ ] **Step 3: Create lib/db.ts**

```typescript
import Database from 'better-sqlite3'
import path from 'path'

let _db: Database.Database | null = null

export function getDb(): Database.Database {
  if (_db) return _db
  const dbPath = process.env.DB_PATH ?? path.join(process.cwd(), 'data', 'idea-garden.db')
  _db = new Database(dbPath)
  _db.pragma('journal_mode = WAL')
  _db.pragma('foreign_keys = ON')
  initSchema(_db)
  return _db
}

export function initSchema(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS ideas (
      id TEXT PRIMARY KEY,
      content TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'floating',
      captured_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS experiment_drafts (
      id TEXT PRIMARY KEY,
      idea_id TEXT NOT NULL REFERENCES ideas(id),
      why TEXT NOT NULL,
      fear_tags TEXT NOT NULL,
      first_step TEXT NOT NULL,
      duration_days INTEGER NOT NULL DEFAULT 7,
      companion_type TEXT NOT NULL,
      companion_variant TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS experiments (
      id TEXT PRIMARY KEY,
      idea_id TEXT NOT NULL REFERENCES ideas(id),
      draft_id TEXT NOT NULL REFERENCES experiment_drafts(id),
      companion_stage INTEGER NOT NULL DEFAULT 0,
      start_date TEXT NOT NULL,
      duration_days INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'active'
    );

    CREATE TABLE IF NOT EXISTS daily_logs (
      id TEXT PRIMARY KEY,
      experiment_id TEXT NOT NULL REFERENCES experiments(id),
      date TEXT NOT NULL,
      min_data TEXT,
      energy_tag TEXT,
      created_at TEXT NOT NULL,
      UNIQUE(experiment_id, date)
    );

    CREATE TABLE IF NOT EXISTS archives (
      id TEXT PRIMARY KEY,
      experiment_id TEXT NOT NULL REFERENCES experiments(id),
      idea_id TEXT NOT NULL REFERENCES ideas(id),
      best_moment TEXT NOT NULL,
      learned TEXT NOT NULL,
      restart_step TEXT NOT NULL,
      explored_at TEXT NOT NULL,
      resurface_at TEXT NOT NULL
    );
  `)
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
npm test -- db
```

- [ ] **Step 5: Commit**

```bash
git add lib/db.ts lib/db.test.ts
git commit -m "feat: add SQLite db layer with schema"
```

---

## Task 3: Server Actions — Ideas

**Files:**
- Create: `actions/ideas.ts`
- Create: `actions/ideas.test.ts`

- [ ] **Step 1: Write failing tests**

Create `actions/ideas.test.ts`:
```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import Database from 'better-sqlite3'
import { initSchema } from '../lib/db'

const db = new Database(':memory:')
initSchema(db)

vi.mock('../lib/db', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/db')>()
  return { ...actual, getDb: () => db }
})

const { createIdea, listFloatingIdeas, updateIdeaStatus } = await import('./ideas')

describe('ideas actions', () => {
  beforeEach(() => { db.exec('DELETE FROM ideas') })

  it('createIdea inserts and returns an idea with floating status', async () => {
    const idea = await createIdea('Learn to draw')
    expect(idea.content).toBe('Learn to draw')
    expect(idea.status).toBe('floating')
    expect(idea.id).toBeTruthy()
  })

  it('listFloatingIdeas returns only floating ideas', async () => {
    await createIdea('Idea A')
    await createIdea('Idea B')
    const list = await listFloatingIdeas()
    expect(list).toHaveLength(2)
    expect(list.every(i => i.status === 'floating')).toBe(true)
  })

  it('updateIdeaStatus changes status so it no longer appears in floating list', async () => {
    const idea = await createIdea('Dance')
    await updateIdeaStatus(idea.id, 'frozen')
    const list = await listFloatingIdeas()
    expect(list).toHaveLength(0)
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- ideas
```

- [ ] **Step 3: Create actions/ideas.ts**

```typescript
'use server'

import { randomUUID } from 'crypto'
import { getDb } from '@/lib/db'
import type { Idea, IdeaStatus } from '@/types'

export async function createIdea(content: string): Promise<Idea> {
  const db = getDb()
  const idea: Idea = {
    id: randomUUID(),
    content: content.trim(),
    status: 'floating',
    capturedAt: new Date().toISOString(),
  }
  db.prepare(
    'INSERT INTO ideas (id, content, status, captured_at) VALUES (?, ?, ?, ?)'
  ).run(idea.id, idea.content, idea.status, idea.capturedAt)
  return idea
}

export async function listFloatingIdeas(): Promise<Idea[]> {
  const db = getDb()
  const rows = db
    .prepare("SELECT * FROM ideas WHERE status = 'floating' ORDER BY captured_at DESC")
    .all() as any[]
  return rows.map(rowToIdea)
}

export async function listAllIdeas(): Promise<Idea[]> {
  const db = getDb()
  return (db.prepare('SELECT * FROM ideas ORDER BY captured_at DESC').all() as any[]).map(rowToIdea)
}

export async function updateIdeaStatus(id: string, status: IdeaStatus): Promise<void> {
  getDb().prepare('UPDATE ideas SET status = ? WHERE id = ?').run(status, id)
}

function rowToIdea(row: any): Idea {
  return { id: row.id, content: row.content, status: row.status as IdeaStatus, capturedAt: row.captured_at }
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
npm test -- ideas
```

- [ ] **Step 5: Commit**

```bash
git add actions/ideas.ts actions/ideas.test.ts
git commit -m "feat: add ideas server actions"
```

---

## Task 4: Server Actions — Experiments

**Files:**
- Create: `actions/experiments.ts`
- Create: `actions/experiments.test.ts`

- [ ] **Step 1: Write failing tests**

Create `actions/experiments.test.ts`:
```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import Database from 'better-sqlite3'
import { initSchema } from '../lib/db'

const db = new Database(':memory:')
initSchema(db)

vi.mock('../lib/db', async (orig) => {
  const actual = await orig<typeof import('../lib/db')>()
  return { ...actual, getDb: () => db }
})

const seedIdea = () =>
  db.prepare('INSERT INTO ideas (id, content, status, captured_at) VALUES (?, ?, ?, ?)')
    .run('idea-1', 'Learn guitar', 'floating', new Date().toISOString())

const { createDraft, activateExperiment, checkin, getActiveExperiment, checkAndStartCooling } =
  await import('./experiments')

describe('experiments actions', () => {
  beforeEach(() => {
    db.exec('DELETE FROM daily_logs; DELETE FROM experiments; DELETE FROM experiment_drafts; DELETE FROM ideas')
    seedIdea()
  })

  it('createDraft saves draft and returns it', async () => {
    const draft = await createDraft({
      ideaId: 'idea-1', why: 'I love music', fearTags: ['tired'],
      firstStep: 'Watch one YouTube lesson', durationDays: 7,
      companionType: 'plant', companionVariant: 'flower',
    })
    expect(draft.why).toBe('I love music')
    expect(draft.fearTags).toEqual(['tired'])
  })

  it('activateExperiment creates experiment and marks idea as in_experiment', async () => {
    const draft = await createDraft({
      ideaId: 'idea-1', why: 'x', fearTags: [], firstStep: 'x',
      durationDays: 7, companionType: 'animal', companionVariant: 'cat',
    })
    const exp = await activateExperiment(draft.id)
    expect(exp.status).toBe('active')
    expect(exp.companionStage).toBe(0)
    const row = db.prepare('SELECT status FROM ideas WHERE id = ?').get('idea-1') as any
    expect(row.status).toBe('in_experiment')
  })

  it('checkin creates daily log and increments companion stage', async () => {
    const draft = await createDraft({
      ideaId: 'idea-1', why: 'x', fearTags: [], firstStep: 'x',
      durationDays: 7, companionType: 'plant', companionVariant: 'cactus',
    })
    const exp = await activateExperiment(draft.id)
    const updated = await checkin(exp.id, { minData: 'Played 10 min', energyTag: 'medium' })
    expect(updated.companionStage).toBe(1)
    const logs = db.prepare('SELECT * FROM daily_logs WHERE experiment_id = ?').all(exp.id)
    expect(logs).toHaveLength(1)
  })

  it('minimal checkin (no text) still increments stage', async () => {
    const draft = await createDraft({
      ideaId: 'idea-1', why: 'x', fearTags: [], firstStep: 'x',
      durationDays: 3, companionType: 'plant', companionVariant: 'moss',
    })
    const exp = await activateExperiment(draft.id)
    const updated = await checkin(exp.id, {})
    expect(updated.companionStage).toBe(1)
  })

  it('checkAndStartCooling sets status to cooling after 3 inactive days', async () => {
    const draft = await createDraft({
      ideaId: 'idea-1', why: 'x', fearTags: [], firstStep: 'x',
      durationDays: 7, companionType: 'plant', companionVariant: 'flower',
    })
    const exp = await activateExperiment(draft.id)
    const oldDate = new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    db.prepare('UPDATE experiments SET start_date = ? WHERE id = ?').run(oldDate, exp.id)
    await checkAndStartCooling()
    const updated = db.prepare('SELECT status FROM experiments WHERE id = ?').get(exp.id) as any
    expect(updated.status).toBe('cooling')
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- experiments
```

- [ ] **Step 3: Create actions/experiments.ts**

```typescript
'use server'

import { randomUUID } from 'crypto'
import { getDb } from '@/lib/db'
import type {
  Experiment, ExperimentDraft, ExperimentWithDetails,
  DailyLog, CompanionStage, EnergyTag,
  CompanionType, CompanionVariant, FearTag, DurationDays,
} from '@/types'

interface CreateDraftInput {
  ideaId: string
  why: string
  fearTags: FearTag[]
  firstStep: string
  durationDays: DurationDays
  companionType: CompanionType
  companionVariant: CompanionVariant
}

export async function createDraft(input: CreateDraftInput): Promise<ExperimentDraft> {
  const db = getDb()
  const draft: ExperimentDraft = {
    id: randomUUID(), ideaId: input.ideaId, why: input.why,
    fearTags: input.fearTags, firstStep: input.firstStep,
    durationDays: input.durationDays, companionType: input.companionType,
    companionVariant: input.companionVariant, createdAt: new Date().toISOString(),
  }
  db.prepare(`
    INSERT INTO experiment_drafts
      (id, idea_id, why, fear_tags, first_step, duration_days, companion_type, companion_variant, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(draft.id, draft.ideaId, draft.why, JSON.stringify(draft.fearTags),
    draft.firstStep, draft.durationDays, draft.companionType, draft.companionVariant, draft.createdAt)
  return draft
}

export async function activateExperiment(draftId: string): Promise<Experiment> {
  const db = getDb()
  const draftRow = db.prepare('SELECT * FROM experiment_drafts WHERE id = ?').get(draftId) as any
  if (!draftRow) throw new Error(`Draft ${draftId} not found`)
  const exp: Experiment = {
    id: randomUUID(), ideaId: draftRow.idea_id, draftId,
    companionStage: 0, startDate: new Date().toISOString().split('T')[0],
    durationDays: draftRow.duration_days, status: 'active',
  }
  db.prepare(`
    INSERT INTO experiments (id, idea_id, draft_id, companion_stage, start_date, duration_days, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(exp.id, exp.ideaId, exp.draftId, exp.companionStage, exp.startDate, exp.durationDays, exp.status)
  db.prepare("UPDATE ideas SET status = 'in_experiment' WHERE id = ?").run(exp.ideaId)
  return exp
}

interface CheckinInput { minData?: string; energyTag?: EnergyTag }

export async function checkin(experimentId: string, input: CheckinInput): Promise<Experiment> {
  const db = getDb()
  const today = new Date().toISOString().split('T')[0]
  db.prepare(`
    INSERT INTO daily_logs (id, experiment_id, date, min_data, energy_tag, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(experiment_id, date) DO UPDATE SET
      min_data = excluded.min_data, energy_tag = excluded.energy_tag
  `).run(randomUUID(), experimentId, today, input.minData ?? null, input.energyTag ?? null, new Date().toISOString())
  const expRow = db.prepare('SELECT * FROM experiments WHERE id = ?').get(experimentId) as any
  const newStage = Math.min(5, (expRow.companion_stage as number) + 1) as CompanionStage
  db.prepare('UPDATE experiments SET companion_stage = ? WHERE id = ?').run(newStage, experimentId)
  return rowToExperiment({ ...expRow, companion_stage: newStage })
}

export async function getActiveExperiment(): Promise<ExperimentWithDetails | null> {
  const db = getDb()
  const expRow = db.prepare(
    "SELECT * FROM experiments WHERE status IN ('active','cooling') ORDER BY start_date DESC LIMIT 1"
  ).get() as any
  if (!expRow) return null
  const draftRow = db.prepare('SELECT * FROM experiment_drafts WHERE id = ?').get(expRow.draft_id) as any
  const ideaRow = db.prepare('SELECT * FROM ideas WHERE id = ?').get(expRow.idea_id) as any
  const logRows = db.prepare('SELECT * FROM daily_logs WHERE experiment_id = ? ORDER BY date').all(expRow.id) as any[]
  return {
    ...rowToExperiment(expRow),
    draft: rowToDraft(draftRow),
    idea: { id: ideaRow.id, content: ideaRow.content, status: ideaRow.status, capturedAt: ideaRow.captured_at },
    dailyLogs: logRows.map(r => ({
      id: r.id, experimentId: r.experiment_id, date: r.date,
      minData: r.min_data, energyTag: r.energy_tag, createdAt: r.created_at,
    })),
  }
}

export async function checkAndStartCooling(): Promise<void> {
  const db = getDb()
  const expRow = db.prepare("SELECT * FROM experiments WHERE status = 'active'").get() as any
  if (!expRow) return
  const lastLog = db.prepare(
    'SELECT date FROM daily_logs WHERE experiment_id = ? ORDER BY date DESC LIMIT 1'
  ).get(expRow.id) as any
  const lastDate = lastLog?.date ?? expRow.start_date
  const daysSince = Math.floor((Date.now() - new Date(lastDate).getTime()) / 86400000)
  if (daysSince >= 3) {
    db.prepare("UPDATE experiments SET status = 'cooling' WHERE id = ?").run(expRow.id)
  }
}

export async function completeExperiment(experimentId: string): Promise<void> {
  getDb().prepare("UPDATE experiments SET status = 'completed' WHERE id = ?").run(experimentId)
}

function rowToExperiment(row: any): Experiment {
  return {
    id: row.id, ideaId: row.idea_id, draftId: row.draft_id,
    companionStage: row.companion_stage as CompanionStage,
    startDate: row.start_date, durationDays: row.duration_days, status: row.status,
  }
}

function rowToDraft(row: any): ExperimentDraft {
  return {
    id: row.id, ideaId: row.idea_id, why: row.why,
    fearTags: JSON.parse(row.fear_tags), firstStep: row.first_step,
    durationDays: row.duration_days, companionType: row.companion_type,
    companionVariant: row.companion_variant, createdAt: row.created_at,
  }
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
npm test -- experiments
```

- [ ] **Step 5: Commit**

```bash
git add actions/experiments.ts actions/experiments.test.ts
git commit -m "feat: add experiments server actions with cooling detection"
```

---

## Task 5: Server Actions — Archives

**Files:**
- Create: `actions/archives.ts`
- Create: `actions/archives.test.ts`

- [ ] **Step 1: Write failing tests**

Create `actions/archives.test.ts`:
```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import Database from 'better-sqlite3'
import { initSchema } from '../lib/db'

const db = new Database(':memory:')
initSchema(db)
vi.mock('../lib/db', async (orig) => {
  const actual = await orig<typeof import('../lib/db')>()
  return { ...actual, getDb: () => db }
})

const seed = () => {
  db.prepare('INSERT INTO ideas (id, content, status, captured_at) VALUES (?, ?, ?, ?)').run('i1', 'Surf', 'in_experiment', new Date().toISOString())
  db.prepare('INSERT INTO experiment_drafts (id, idea_id, why, fear_tags, first_step, duration_days, companion_type, companion_variant, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)').run('d1', 'i1', 'fun', '[]', 'buy board', 7, 'plant', 'flower', new Date().toISOString())
  db.prepare('INSERT INTO experiments (id, idea_id, draft_id, companion_stage, start_date, duration_days, status) VALUES (?, ?, ?, ?, ?, ?, ?)').run('e1', 'i1', 'd1', 3, '2026-06-01', 7, 'cooling')
}

const { createArchive, listArchives, getArchive } = await import('./archives')

describe('archives actions', () => {
  beforeEach(() => {
    db.exec('DELETE FROM archives; DELETE FROM daily_logs; DELETE FROM experiments; DELETE FROM experiment_drafts; DELETE FROM ideas')
    seed()
  })

  it('createArchive saves archive and sets resurfaceAt 90 days out', async () => {
    const a = await createArchive({ experimentId: 'e1', ideaId: 'i1', bestMoment: 'Caught wave', learned: 'Balance', restartStep: 'Book lesson' })
    expect(a.bestMoment).toBe('Caught wave')
    const diff = new Date(a.resurfaceAt).getTime() - new Date(a.exploredAt).getTime()
    expect(Math.round(diff / 86400000)).toBe(90)
  })

  it('createArchive marks experiment completed and idea archived', async () => {
    await createArchive({ experimentId: 'e1', ideaId: 'i1', bestMoment: 'x', learned: 'y', restartStep: 'z' })
    const exp = db.prepare('SELECT status FROM experiments WHERE id = ?').get('e1') as any
    const idea = db.prepare('SELECT status FROM ideas WHERE id = ?').get('i1') as any
    expect(exp.status).toBe('completed')
    expect(idea.status).toBe('archived')
  })

  it('listArchives and getArchive work correctly', async () => {
    const created = await createArchive({ experimentId: 'e1', ideaId: 'i1', bestMoment: 'x', learned: 'y', restartStep: 'z' })
    expect(await listArchives()).toHaveLength(1)
    const fetched = await getArchive(created.id)
    expect(fetched?.id).toBe(created.id)
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- archives
```

- [ ] **Step 3: Create actions/archives.ts**

```typescript
'use server'

import { randomUUID } from 'crypto'
import { getDb } from '@/lib/db'
import type { Archive } from '@/types'

interface CreateArchiveInput {
  experimentId: string
  ideaId: string
  bestMoment: string
  learned: string
  restartStep: string
}

export async function createArchive(input: CreateArchiveInput): Promise<Archive> {
  const db = getDb()
  const now = new Date()
  const resurfaceAt = new Date(now)
  resurfaceAt.setDate(resurfaceAt.getDate() + 90)
  const archive: Archive = {
    id: randomUUID(), experimentId: input.experimentId, ideaId: input.ideaId,
    bestMoment: input.bestMoment, learned: input.learned, restartStep: input.restartStep,
    exploredAt: now.toISOString(), resurfaceAt: resurfaceAt.toISOString(),
  }
  db.prepare(`
    INSERT INTO archives (id, experiment_id, idea_id, best_moment, learned, restart_step, explored_at, resurface_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(archive.id, archive.experimentId, archive.ideaId, archive.bestMoment,
    archive.learned, archive.restartStep, archive.exploredAt, archive.resurfaceAt)
  db.prepare("UPDATE experiments SET status = 'completed' WHERE id = ?").run(input.experimentId)
  db.prepare("UPDATE ideas SET status = 'archived' WHERE id = ?").run(input.ideaId)
  return archive
}

export async function listArchives(): Promise<Archive[]> {
  return (getDb().prepare('SELECT * FROM archives ORDER BY explored_at DESC').all() as any[]).map(rowToArchive)
}

export async function getArchive(id: string): Promise<Archive | null> {
  const row = getDb().prepare('SELECT * FROM archives WHERE id = ?').get(id) as any
  return row ? rowToArchive(row) : null
}

function rowToArchive(row: any): Archive {
  return {
    id: row.id, experimentId: row.experiment_id, ideaId: row.idea_id,
    bestMoment: row.best_moment, learned: row.learned, restartStep: row.restart_step,
    exploredAt: row.explored_at, resurfaceAt: row.resurface_at,
  }
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
npm test -- archives
```

- [ ] **Step 5: Commit**

```bash
git add actions/archives.ts actions/archives.test.ts
git commit -m "feat: add archives server actions"
```

---

## Task 6: Design Tokens + Daily Prompt

**Files:**
- Modify: `app/globals.css`
- Create: `lib/daily-prompt.ts`
- Create: `lib/daily-prompt.test.ts`

- [ ] **Step 1: Write daily-prompt test**

Create `lib/daily-prompt.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { getDailyPrompt } from './daily-prompt'

describe('getDailyPrompt', () => {
  it('returns a non-empty string', () => {
    expect(getDailyPrompt('2026-06-09')).toBeTruthy()
  })

  it('is deterministic for same date', () => {
    expect(getDailyPrompt('2026-06-09')).toBe(getDailyPrompt('2026-06-09'))
  })

  it('returns different prompts across 3 consecutive days', () => {
    const results = new Set(['2026-06-09', '2026-06-10', '2026-06-11'].map(getDailyPrompt))
    expect(results.size).toBeGreaterThan(1)
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- daily-prompt
```

- [ ] **Step 3: Create lib/daily-prompt.ts**

```typescript
const PROMPTS = [
  '今天收集的最小数据是什么？',
  '有什么让你意外的发现？',
  '今天做了还是没做？都可以写。',
  '用一句话描述今天的感受。',
  '有什么比你预想的更容易？',
  '遇到了什么小阻力？',
  '今天最值得记录的一刻是？',
]

export function getDailyPrompt(dateStr: string): string {
  const hash = dateStr.split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0)
  return PROMPTS[hash % PROMPTS.length]
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
npm test -- daily-prompt
```

- [ ] **Step 5: Add design tokens to app/globals.css**

Replace the entire `:root` block:
```css
:root {
  --color-bg: oklch(98% 0.01 85);
  --color-surface: oklch(96% 0.015 80);
  --color-surface-raised: oklch(100% 0 0);
  --color-text: oklch(22% 0.02 60);
  --color-text-muted: oklch(55% 0.02 60);
  --color-accent: oklch(72% 0.18 55);
  --color-accent-soft: oklch(92% 0.07 55);
  --color-success: oklch(68% 0.16 145);
}

body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: system-ui, -apple-system, sans-serif;
}
```

- [ ] **Step 6: Commit**

```bash
git add lib/daily-prompt.ts lib/daily-prompt.test.ts app/globals.css
git commit -m "feat: add design tokens and daily-prompt rotation"
```

---

## Task 7: AI Suggestions

**Files:**
- Create: `lib/ai.ts`
- Create: `lib/ai.test.ts`
- Create: `app/api/ai/route.ts`

- [ ] **Step 1: Write failing test**

Create `lib/ai.test.ts`:
```typescript
import { describe, it, expect, vi } from 'vitest'

vi.mock('@anthropic-ai/sdk', () => ({
  default: class {
    messages = {
      create: vi.fn().mockResolvedValue({
        content: [{ type: 'text', text: JSON.stringify({
          why: ['我喜欢创作', '它让我放松', '我想表达自己'],
          firstStep: ['今晚看一个教程', '买一个基础工具', '试5分钟'],
        })}],
      }),
    }
  },
}))

const { generateActivationSuggestions } = await import('./ai')

describe('generateActivationSuggestions', () => {
  it('returns 3 why and 3 firstStep options', async () => {
    const result = await generateActivationSuggestions('Learn to draw')
    expect(result.why).toHaveLength(3)
    expect(result.firstStep).toHaveLength(3)
    expect(typeof result.why[0]).toBe('string')
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- ai
```

- [ ] **Step 3: Create lib/ai.ts**

```typescript
import Anthropic from '@anthropic-ai/sdk'
import type { AiSuggestions, ArchiveSuggestions } from '@/types'

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

export async function generateActivationSuggestions(ideaContent: string): Promise<AiSuggestions> {
  const message = await client.messages.create({
    model: 'claude-haiku-4-5-20251001',
    max_tokens: 400,
    messages: [{
      role: 'user',
      content: `You are helping someone start a low-stakes experiment on: "${ideaContent}"

Respond ONLY with valid JSON (no markdown):
{"why":["reason1","reason2","reason3"],"firstStep":["action1","action2","action3"]}

Rules:
- why: 3 short (<12 words) reasons in first-person Chinese starting with 我
- firstStep: 3 ultra-small actions (<15 words each) doable in under 30 minutes, first-person Chinese`,
    }],
  })
  const text = message.content[0].type === 'text' ? message.content[0].text : '{}'
  return JSON.parse(text) as AiSuggestions
}

export async function generateArchiveSuggestions(
  ideaContent: string,
  logSummary: string,
): Promise<ArchiveSuggestions> {
  const message = await client.messages.create({
    model: 'claude-haiku-4-5-20251001',
    max_tokens: 500,
    messages: [{
      role: 'user',
      content: `Someone finished an experiment on: "${ideaContent}". Notes: "${logSummary}"

Respond ONLY with valid JSON (no markdown):
{"bestMoment":["o1","o2","o3"],"learned":["o1","o2","o3"],"restartStep":["o1","o2","o3"]}

All options: first-person Chinese, under 15 words each.`,
    }],
  })
  const text = message.content[0].type === 'text' ? message.content[0].text : '{}'
  return JSON.parse(text) as ArchiveSuggestions
}
```

- [ ] **Step 4: Create app/api/ai/route.ts**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { generateActivationSuggestions, generateArchiveSuggestions } from '@/lib/ai'

export async function POST(req: NextRequest) {
  const body = await req.json()
  if (body.type === 'activation') {
    return NextResponse.json(await generateActivationSuggestions(body.ideaContent))
  }
  if (body.type === 'archive') {
    return NextResponse.json(await generateArchiveSuggestions(body.ideaContent, body.logSummary ?? ''))
  }
  return NextResponse.json({ error: 'Unknown type' }, { status: 400 })
}
```

- [ ] **Step 5: Run — expect PASS**

```bash
npm test -- ai
```

- [ ] **Step 6: Commit**

```bash
git add lib/ai.ts lib/ai.test.ts app/api/
git commit -m "feat: add Claude Haiku AI suggestions endpoint"
```

---

## Task 8: Companion Component

**Files:**
- Create: `components/companion/Companion.tsx`
- Create: `components/companion/Companion.test.tsx`

- [ ] **Step 1: Write failing test**

Create `components/companion/Companion.test.tsx`:
```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Companion } from './Companion'

describe('Companion', () => {
  it('renders an img role element', () => {
    render(<Companion type="plant" variant="flower" stage={0} />)
    expect(screen.getByRole('img', { name: /companion/i })).toBeTruthy()
  })

  it('shows different emoji at stage 0 vs stage 3', () => {
    const { rerender, getByRole } = render(<Companion type="plant" variant="flower" stage={0} />)
    const s0 = getByRole('img', { name: /companion/i }).textContent
    rerender(<Companion type="plant" variant="flower" stage={3} />)
    const s3 = getByRole('img', { name: /companion/i }).textContent
    expect(s0).not.toBe(s3)
  })

  it('shows 休眠 label when isCooling', () => {
    render(<Companion type="animal" variant="cat" stage={2} isCooling />)
    expect(screen.getByText(/休眠/)).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- Companion
```

- [ ] **Step 3: Create components/companion/Companion.tsx**

```typescript
'use client'

import { motion } from 'framer-motion'
import type { CompanionType, CompanionVariant, CompanionStage } from '@/types'

const STAGE_LABELS = ['种子', '发芽', '小苗', '开花', '盛放', '满开']

const PLANT_STAGES: Record<string, string[]> = {
  flower:  ['🌰', '🌱', '🌿', '🌸', '🌺', '🌻'],
  cactus:  ['🌰', '🌱', '🪴', '🌵', '🌵', '🌵'],
  bamboo:  ['🌰', '🌱', '🌿', '🎋', '🎋', '🎍'],
  moss:    ['🌰', '🌱', '🍀', '🌿', '🍃', '🌳'],
}

const ANIMAL_STAGES: Record<string, string[]> = {
  cat:     ['🥚', '🐣', '🐱', '😸', '😻', '🐈'],
  rabbit:  ['🥚', '🐣', '🐰', '🐇', '🐇', '🐇'],
  totoro:  ['🥚', '🐣', '🐭', '🐹', '🐼', '🐨'],
  creature:['🥚', '🐣', '🦎', '🦕', '🦖', '🐉'],
}

interface CompanionProps {
  type: CompanionType
  variant: CompanionVariant
  stage: CompanionStage
  isCooling?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export function Companion({ type, variant, stage, isCooling = false, size = 'md' }: CompanionProps) {
  const map = type === 'plant' ? PLANT_STAGES : ANIMAL_STAGES
  const emoji = map[variant]?.[stage] ?? '🌱'
  const label = isCooling ? '休眠中' : STAGE_LABELS[stage]
  const sizeClass = { sm: 'text-4xl', md: 'text-7xl', lg: 'text-9xl' }[size]

  return (
    <div className="flex flex-col items-center gap-2">
      <motion.span
        role="img"
        aria-label={`companion ${emoji}`}
        className={sizeClass}
        animate={isCooling
          ? { scale: [1, 0.92, 1], opacity: [1, 0.6, 1] }
          : { scale: [1, 1.04, 1] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      >
        {isCooling ? '😴' : emoji}
      </motion.span>
      <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{label}</span>
    </div>
  )
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
npm test -- Companion
```

- [ ] **Step 5: Commit**

```bash
git add components/companion/
git commit -m "feat: add Companion component with 5-stage growth"
```

---

## Task 9: IdeaBubble Components

**Files:**
- Create: `components/idea-bubble/IdeaBubble.tsx`
- Create: `components/idea-bubble/IdeaBubbleList.tsx`
- Create: `components/idea-bubble/IdeaBubble.test.tsx`

- [ ] **Step 1: Write failing test**

Create `components/idea-bubble/IdeaBubble.test.tsx`:
```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { IdeaBubble } from './IdeaBubble'
import type { Idea } from '@/types'

const idea: Idea = { id: '1', content: 'Learn to surf', status: 'floating', capturedAt: '2026-06-09T00:00:00Z' }

describe('IdeaBubble', () => {
  it('renders idea content', () => {
    render(<IdeaBubble idea={idea} onActivate={vi.fn()} />)
    expect(screen.getByText('Learn to surf')).toBeTruthy()
  })

  it('calls onActivate with the idea when clicked', () => {
    const onActivate = vi.fn()
    render(<IdeaBubble idea={idea} onActivate={onActivate} />)
    fireEvent.click(screen.getByRole('button'))
    expect(onActivate).toHaveBeenCalledWith(idea)
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- IdeaBubble
```

- [ ] **Step 3: Create components/idea-bubble/IdeaBubble.tsx**

```typescript
'use client'

import { motion } from 'framer-motion'
import type { Idea } from '@/types'

interface IdeaBubbleProps {
  idea: Idea
  onActivate: (idea: Idea) => void
}

export function IdeaBubble({ idea, onActivate }: IdeaBubbleProps) {
  return (
    <motion.button
      layout
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0, opacity: 0 }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.97 }}
      onClick={() => onActivate(idea)}
      className="px-4 py-2 rounded-full text-sm font-medium cursor-pointer"
      style={{
        background: 'var(--color-accent-soft)',
        color: 'var(--color-text)',
        border: '1.5px solid var(--color-accent)',
      }}
    >
      {idea.content}
    </motion.button>
  )
}
```

- [ ] **Step 4: Create components/idea-bubble/IdeaBubbleList.tsx**

```typescript
'use client'

import { AnimatePresence } from 'framer-motion'
import { IdeaBubble } from './IdeaBubble'
import type { Idea } from '@/types'

interface IdeaBubbleListProps {
  ideas: Idea[]
  onActivate: (idea: Idea) => void
}

export function IdeaBubbleList({ ideas, onActivate }: IdeaBubbleListProps) {
  if (ideas.length === 0) return (
    <p className="text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
      还没有浮动的想法 — 先记录一个吧
    </p>
  )
  return (
    <div className="flex flex-wrap gap-3 justify-center">
      <AnimatePresence>
        {ideas.map(idea => <IdeaBubble key={idea.id} idea={idea} onActivate={onActivate} />)}
      </AnimatePresence>
    </div>
  )
}
```

- [ ] **Step 5: Run — expect PASS**

```bash
npm test -- IdeaBubble
```

- [ ] **Step 6: Commit**

```bash
git add components/idea-bubble/
git commit -m "feat: add IdeaBubble components"
```

---

## Task 10: /capture Page

**Files:**
- Create: `app/capture/page.tsx`

- [ ] **Step 1: Create app/capture/page.tsx**

```typescript
import { redirect } from 'next/navigation'
import { createIdea } from '@/actions/ideas'

export default function CapturePage() {
  async function capture(formData: FormData) {
    'use server'
    const content = formData.get('content') as string
    if (content?.trim()) await createIdea(content.trim())
    redirect('/')
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6"
      style={{ background: 'var(--color-bg)' }}>
      <div className="w-full max-w-sm space-y-6">
        <h1 className="text-2xl font-semibold text-center">有个想法？</h1>
        <form action={capture} className="space-y-4">
          <textarea
            name="content"
            autoFocus
            placeholder="就一句话，不用完整"
            rows={3}
            className="w-full p-4 rounded-2xl text-base resize-none outline-none"
            style={{ background: 'var(--color-surface-raised)', border: '1.5px solid var(--color-accent-soft)' }}
          />
          <button type="submit"
            className="w-full py-3 rounded-full font-medium text-white"
            style={{ background: 'var(--color-accent)' }}>
            存下来 ✓
          </button>
        </form>
        <a href="/" className="block text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
          返回
        </a>
      </div>
    </main>
  )
}
```

- [ ] **Step 2: Verify in browser**

```bash
npm run dev
# Open http://localhost:3000/capture
# Type an idea → submit → should redirect to / without error
```

- [ ] **Step 3: Commit**

```bash
git add app/capture/
git commit -m "feat: add /capture quick-entry page"
```

---

## Task 11: /activate Multi-Step Flow

**Files:**
- Create: `app/activate/ActivateFlow.tsx`
- Create: `app/activate/page.tsx`

- [ ] **Step 1: Create app/activate/ActivateFlow.tsx**

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createDraft, activateExperiment } from '@/actions/experiments'
import type { Idea, FearTag, CompanionType, CompanionVariant, DurationDays, AiSuggestions } from '@/types'

const FEAR_OPTIONS: { tag: FearTag; label: string }[] = [
  { tag: 'tired', label: '怕累' },
  { tag: 'no_time', label: '怕没时间' },
  { tag: 'not_good_enough', label: '怕做不好' },
  { tag: 'cant_persist', label: '怕坚持不住' },
]
const PLANT_OPTIONS = ['flower','cactus','bamboo','moss'] as const
const ANIMAL_OPTIONS = ['cat','rabbit','totoro','creature'] as const
const PLANT_EMOJI: Record<string,string> = { flower:'🌸', cactus:'🌵', bamboo:'🎋', moss:'🍀' }
const ANIMAL_EMOJI: Record<string,string> = { cat:'🐱', rabbit:'🐰', totoro:'🐹', creature:'🥚' }
const DURATION_OPTIONS: DurationDays[] = [3, 7, 14, 21]

const FALLBACK_SUGGESTIONS: AiSuggestions = {
  why: ['我对这件事充满好奇', '它能让我感到愉悦', '我一直想尝试'],
  firstStep: ['今晚花5分钟了解一下', '找一个相关的参考资料', '和朋友聊聊这个想法'],
}

export function ActivateFlow({ ideas }: { ideas: Idea[] }) {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [selectedIdea, setSelectedIdea] = useState<Idea | null>(null)
  const [suggestions, setSuggestions] = useState<AiSuggestions>(FALLBACK_SUGGESTIONS)
  const [why, setWhy] = useState('')
  const [fearTags, setFearTags] = useState<FearTag[]>([])
  const [firstStep, setFirstStep] = useState('')
  const [companionType, setCompanionType] = useState<CompanionType>('plant')
  const [companionVariant, setCompanionVariant] = useState<CompanionVariant>('flower')
  const [durationDays, setDurationDays] = useState<DurationDays>(7)
  const [loading, setLoading] = useState(false)

  async function selectIdea(idea: Idea) {
    setSelectedIdea(idea)
    setLoading(true)
    try {
      const res = await fetch('/api/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'activation', ideaContent: idea.content }),
      })
      if (res.ok) setSuggestions(await res.json())
    } catch { /* use fallback */ }
    setLoading(false)
    setStep(1)
  }

  async function submit() {
    if (!selectedIdea || !why || !firstStep) return
    setLoading(true)
    const draft = await createDraft({
      ideaId: selectedIdea.id, why, fearTags, firstStep,
      durationDays, companionType, companionVariant,
    })
    await activateExperiment(draft.id)
    router.push('/experiment')
  }

  const btnStyle = (active: boolean) => ({
    background: active ? 'var(--color-accent)' : 'var(--color-surface-raised)',
    color: active ? 'white' : 'var(--color-text)',
    border: `1.5px solid ${active ? 'var(--color-accent)' : 'var(--color-accent-soft)'}`,
  })

  if (step === 0) return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">选一个想法开始实验</h2>
      {ideas.length === 0
        ? <p style={{ color: 'var(--color-text-muted)' }}>还没有想法，先去记录一个吧</p>
        : ideas.map(idea => (
          <button key={idea.id} onClick={() => selectIdea(idea)}
            className="w-full text-left p-4 rounded-2xl"
            style={{ background: 'var(--color-surface-raised)', border: '1.5px solid var(--color-accent-soft)' }}>
            {idea.content}
          </button>
        ))}
    </div>
  )

  if (loading) return <p className="text-center py-8">生成建议中...</p>

  if (step === 1) return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">「{selectedIdea?.content}」吸引你的是？</h2>
      {suggestions.why.map(w => (
        <button key={w} onClick={() => { setWhy(w); setStep(2) }}
          className="w-full text-left p-4 rounded-2xl" style={btnStyle(why === w)}>
          {w}
        </button>
      ))}
    </div>
  )

  if (step === 2) return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">有点担心什么？（可多选）</h2>
      <div className="flex flex-wrap gap-3">
        {FEAR_OPTIONS.map(({ tag, label }) => (
          <button key={tag}
            onClick={() => setFearTags(p => p.includes(tag) ? p.filter(t => t !== tag) : [...p, tag])}
            className="px-4 py-2 rounded-full text-sm" style={btnStyle(fearTags.includes(tag))}>
            {label}
          </button>
        ))}
      </div>
      <button onClick={() => setStep(3)} className="w-full py-3 rounded-full font-medium text-white"
        style={{ background: 'var(--color-accent)' }}>
        继续 →
      </button>
    </div>
  )

  if (step === 3) return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">最小的第一步是？</h2>
      {suggestions.firstStep.map(s => (
        <button key={s} onClick={() => { setFirstStep(s); setStep(4) }}
          className="w-full text-left p-4 rounded-2xl" style={btnStyle(firstStep === s)}>
          {s}
        </button>
      ))}
    </div>
  )

  if (step === 4) return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-medium">选一个陪伴</h2>
        <div className="flex gap-3">
          {(['plant', 'animal'] as CompanionType[]).map(t => (
            <button key={t} onClick={() => {
              setCompanionType(t)
              setCompanionVariant(t === 'plant' ? 'flower' : 'cat')
            }} className="flex-1 py-2 rounded-full text-sm" style={btnStyle(companionType === t)}>
              {t === 'plant' ? '🌱 植物' : '🐣 动物'}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-3">
          {(companionType === 'plant' ? PLANT_OPTIONS : ANIMAL_OPTIONS).map(v => (
            <button key={v} onClick={() => setCompanionVariant(v)}
              className="px-4 py-2 rounded-full text-sm" style={btnStyle(companionVariant === v)}>
              {(companionType === 'plant' ? PLANT_EMOJI : ANIMAL_EMOJI)[v]} {v}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-3">
        <h2 className="text-lg font-medium">实验持续多久？</h2>
        <div className="flex gap-3">
          {DURATION_OPTIONS.map(d => (
            <button key={d} onClick={() => setDurationDays(d)}
              className="flex-1 py-2 rounded-full text-sm" style={btnStyle(durationDays === d)}>
              {d}天
            </button>
          ))}
        </div>
      </div>
      <button onClick={submit} disabled={loading}
        className="w-full py-4 rounded-full font-semibold text-white text-lg"
        style={{ background: 'var(--color-accent)' }}>
        {loading ? '启动中...' : '🚀 开始实验'}
      </button>
    </div>
  )

  return null
}
```

- [ ] **Step 2: Create app/activate/page.tsx**

```typescript
import { listFloatingIdeas } from '@/actions/ideas'
import { ActivateFlow } from './ActivateFlow'

export default async function ActivatePage() {
  const ideas = await listFloatingIdeas()
  return (
    <main className="min-h-screen p-6" style={{ background: 'var(--color-bg)' }}>
      <div className="max-w-sm mx-auto space-y-6">
        <h1 className="text-2xl font-semibold text-center">启动实验</h1>
        <ActivateFlow ideas={ideas} />
      </div>
    </main>
  )
}
```

- [ ] **Step 3: Verify in browser**

```bash
npm run dev
# Open http://localhost:3000/activate
# Complete all 5 steps — should redirect to /experiment after submit
```

- [ ] **Step 4: Commit**

```bash
git add app/activate/
git commit -m "feat: add /activate multi-step experiment flow"
```

---

## Task 12: /experiment Page

**Files:**
- Create: `app/experiment/CheckinPanel.tsx`
- Create: `app/experiment/CoolingPanel.tsx`
- Create: `app/experiment/page.tsx`

- [ ] **Step 1: Create app/experiment/CheckinPanel.tsx**

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { checkin } from '@/actions/experiments'
import type { ExperimentWithDetails, EnergyTag } from '@/types'

interface Props {
  experiment: ExperimentWithDetails
  dailyPrompt: string
  alreadyCheckedIn: boolean
}

export function CheckinPanel({ experiment, dailyPrompt, alreadyCheckedIn }: Props) {
  const router = useRouter()
  const [tier, setTier] = useState<'minimal'|'standard'|'deep'|null>(null)
  const [minData, setMinData] = useState('')
  const [energyTag, setEnergyTag] = useState<EnergyTag|null>(null)
  const [done, setDone] = useState(alreadyCheckedIn)

  async function doCheckin(data?: { minData?: string; energyTag?: EnergyTag }) {
    await checkin(experiment.id, data ?? {})
    setDone(true)
    router.refresh()
  }

  if (done) return (
    <div className="text-center space-y-2 py-6">
      <div className="text-4xl">✅</div>
      <p className="font-medium">今天已出发</p>
      <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
        连续 {experiment.dailyLogs.length} 天 · 第 {experiment.companionStage} 级
      </p>
    </div>
  )

  const btnBase = "w-full py-3 rounded-2xl text-sm"
  const softBtn = { background: 'var(--color-surface-raised)', border: '1.5px solid var(--color-accent-soft)' }
  const accentBtn = { background: 'var(--color-accent)' }

  if (!tier) return (
    <div className="space-y-3">
      <p className="text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>今天想怎么打卡？</p>
      <button onClick={() => doCheckin()} className="w-full py-4 rounded-2xl font-semibold text-white text-lg"
        style={accentBtn}>
        今天已出发 ✓
      </button>
      <button onClick={() => setTier('standard')} className={btnBase} style={softBtn}>✏️ 写一句话</button>
      <button onClick={() => setTier('deep')} className={btnBase} style={softBtn}>💭 深度记录</button>
    </div>
  )

  if (tier === 'standard') return (
    <div className="space-y-4">
      <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{dailyPrompt}</p>
      <textarea value={minData} onChange={e => setMinData(e.target.value)}
        rows={3} placeholder="一句话就够了"
        className="w-full p-4 rounded-2xl resize-none outline-none text-sm"
        style={{ background: 'var(--color-surface-raised)', border: '1.5px solid var(--color-accent-soft)' }} />
      <button onClick={() => doCheckin({ minData: minData || undefined })}
        className="w-full py-3 rounded-full font-medium text-white" style={accentBtn}>
        完成 ✓
      </button>
    </div>
  )

  const ENERGY: { tag: EnergyTag; label: string; emoji: string }[] = [
    { tag: 'high', label: '很有劲', emoji: '⚡' },
    { tag: 'medium', label: '还好', emoji: '😊' },
    { tag: 'low', label: '有点累', emoji: '🌙' },
  ]

  return (
    <div className="space-y-4">
      <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{dailyPrompt}</p>
      <textarea value={minData} onChange={e => setMinData(e.target.value)}
        rows={4} placeholder="详细记录一下..."
        className="w-full p-4 rounded-2xl resize-none outline-none text-sm"
        style={{ background: 'var(--color-surface-raised)', border: '1.5px solid var(--color-accent-soft)' }} />
      <div className="flex gap-2">
        {ENERGY.map(e => (
          <button key={e.tag} onClick={() => setEnergyTag(e.tag)}
            className="flex-1 py-2 rounded-full text-sm"
            style={{ background: energyTag === e.tag ? 'var(--color-accent)' : 'var(--color-surface-raised)', color: energyTag === e.tag ? 'white' : 'var(--color-text)', border: '1.5px solid var(--color-accent-soft)' }}>
            {e.emoji} {e.label}
          </button>
        ))}
      </div>
      <button onClick={() => doCheckin({ minData: minData || undefined, energyTag: energyTag ?? undefined })}
        className="w-full py-3 rounded-full font-medium text-white" style={accentBtn}>
        完成 ✓
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Create app/experiment/CoolingPanel.tsx**

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createArchive } from '@/actions/archives'
import type { ExperimentWithDetails, ArchiveSuggestions } from '@/types'

const FALLBACK: ArchiveSuggestions = {
  bestMoment: ['第一次真正尝试了这件事', '发现它比想象中有趣', '看到了一点点进展'],
  learned: ['启动比坚持更重要', '我对这件事的感觉更清晰了', '这个方向值得继续探索'],
  restartStep: ['下次先从最简单的部分开始', '找一个朋友一起做', '设置一个更短的实验周期'],
}

export function CoolingPanel({ experiment }: { experiment: ExperimentWithDetails }) {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [suggestions, setSuggestions] = useState<ArchiveSuggestions>(FALLBACK)
  const [bestMoment, setBestMoment] = useState('')
  const [learned, setLearned] = useState('')
  const [restartStep, setRestartStep] = useState('')
  const [loading, setLoading] = useState(false)

  async function loadSuggestions() {
    setLoading(true)
    const logSummary = experiment.dailyLogs.filter(l => l.minData).map(l => l.minData).join('；')
    try {
      const res = await fetch('/api/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'archive', ideaContent: experiment.idea.content, logSummary }),
      })
      if (res.ok) setSuggestions(await res.json())
    } catch { /* use fallback */ }
    setLoading(false)
    setStep(1)
  }

  async function finish() {
    await createArchive({ experimentId: experiment.id, ideaId: experiment.ideaId, bestMoment, learned, restartStep })
    router.push('/archive')
  }

  const optionStyle = (selected: boolean) => ({
    background: 'var(--color-surface-raised)',
    border: `1.5px solid ${selected ? 'var(--color-accent)' : 'var(--color-accent-soft)'}`,
  })

  if (step === 0) return (
    <div className="space-y-4 text-center">
      <div className="text-4xl">🌙</div>
      <p className="font-medium">实验进入了冷却期</p>
      <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
        做个 1 分钟的小回顾？这不是失败，是「已探索」。
      </p>
      <button onClick={loadSuggestions} disabled={loading}
        className="w-full py-3 rounded-full font-medium text-white"
        style={{ background: 'var(--color-accent)' }}>
        {loading ? '准备中...' : '开始荣耀谢幕 →'}
      </button>
    </div>
  )

  const steps = [
    { q: '最爽的瞬间是？', opts: suggestions.bestMoment, set: setBestMoment, val: bestMoment, next: 2 },
    { q: '学到了什么？', opts: suggestions.learned, set: setLearned, val: learned, next: 3 },
    { q: '下次重启的第一步？', opts: suggestions.restartStep, set: setRestartStep, val: restartStep, next: 4 },
  ]
  const current = steps[step - 1]

  if (step >= 1 && step <= 3 && current) return (
    <div className="space-y-3">
      <p className="font-medium">{current.q}</p>
      {current.opts.map(s => (
        <button key={s} onClick={() => { current.set(s); setStep(current.next) }}
          className="w-full text-left p-3 rounded-2xl text-sm" style={optionStyle(current.val === s)}>
          {s}
        </button>
      ))}
    </div>
  )

  return (
    <div className="space-y-6 text-center">
      <div className="text-5xl">🏆</div>
      <div>
        <p className="font-semibold text-lg">实验已完成</p>
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
          「{experiment.idea.content}」已成功探索
        </p>
      </div>
      <button onClick={finish}
        className="w-full py-3 rounded-full font-medium text-white"
        style={{ background: 'var(--color-success)' }}>
        盖下「已探索」印章 ✓
      </button>
    </div>
  )
}
```

- [ ] **Step 3: Create app/experiment/page.tsx**

```typescript
import { getActiveExperiment, checkAndStartCooling } from '@/actions/experiments'
import { getDailyPrompt } from '@/lib/daily-prompt'
import { Companion } from '@/components/companion/Companion'
import { CheckinPanel } from './CheckinPanel'
import { CoolingPanel } from './CoolingPanel'
import Link from 'next/link'

export default async function ExperimentPage() {
  await checkAndStartCooling()
  const experiment = await getActiveExperiment()
  const today = new Date().toISOString().split('T')[0]

  if (!experiment) return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 gap-6"
      style={{ background: 'var(--color-bg)' }}>
      <p style={{ color: 'var(--color-text-muted)' }}>还没有进行中的实验</p>
      <Link href="/activate" className="px-6 py-3 rounded-full font-medium text-white"
        style={{ background: 'var(--color-accent)' }}>
        启动第一个实验
      </Link>
    </main>
  )

  const alreadyCheckedIn = experiment.dailyLogs.some(l => l.date === today)
  const isCooling = experiment.status === 'cooling'

  return (
    <main className="min-h-screen p-6" style={{ background: 'var(--color-bg)' }}>
      <div className="max-w-sm mx-auto space-y-8">
        <div className="text-center space-y-1">
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            第 {experiment.dailyLogs.length + 1} 天 · {experiment.idea.content}
          </p>
        </div>
        <div className="flex justify-center">
          <Companion type={experiment.draft.companionType} variant={experiment.draft.companionVariant}
            stage={experiment.companionStage} isCooling={isCooling} size="lg" />
        </div>
        <div className="p-6 rounded-3xl" style={{ background: 'var(--color-surface-raised)' }}>
          {isCooling
            ? <CoolingPanel experiment={experiment} />
            : <CheckinPanel experiment={experiment} dailyPrompt={getDailyPrompt(today)} alreadyCheckedIn={alreadyCheckedIn} />
          }
        </div>
        <div className="flex justify-center gap-6 text-sm" style={{ color: 'var(--color-text-muted)' }}>
          <Link href="/">← 主屏</Link>
          <Link href="/archive">档案馆</Link>
        </div>
      </div>
    </main>
  )
}
```

- [ ] **Step 4: Verify in browser — test all 3 check-in tiers**

```bash
npm run dev
# Open http://localhost:3000/experiment
# Try: tap ✓ / write 1 line / deep mode
# Simulate cooling: manually set start_date 4 days ago in SQLite
# Verify CoolingPanel appears and completes the archive flow
```

- [ ] **Step 5: Commit**

```bash
git add app/experiment/
git commit -m "feat: add /experiment daily check-in and cooling archive flow"
```

---

## Task 13: Home Page + Layout

**Files:**
- Modify: `app/page.tsx`
- Modify: `app/layout.tsx`

- [ ] **Step 1: Update app/layout.tsx**

```typescript
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '想法花园',
  description: '启动了已经很好了',
  manifest: '/manifest.json',
  appleWebApp: { capable: true, statusBarStyle: 'default', title: '想法花园' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  )
}
```

- [ ] **Step 2: Update app/page.tsx**

```typescript
import { getActiveExperiment } from '@/actions/experiments'
import { listFloatingIdeas } from '@/actions/ideas'
import { Companion } from '@/components/companion/Companion'
import { IdeaBubbleList } from '@/components/idea-bubble/IdeaBubbleList'
import Link from 'next/link'
import { redirect } from 'next/navigation'

export default async function HomePage() {
  const [experiment, ideas] = await Promise.all([getActiveExperiment(), listFloatingIdeas()])
  const today = new Date().toISOString().split('T')[0]
  const checkedInToday = experiment?.dailyLogs.some(l => l.date === today) ?? false

  async function handleActivate(ideaId: string) {
    'use server'
    redirect(`/activate?idea=${ideaId}`)
  }

  return (
    <main className="min-h-screen flex flex-col p-6 gap-8" style={{ background: 'var(--color-bg)' }}>
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-semibold">想法花园</h1>
        <Link href="/archive" className="text-sm" style={{ color: 'var(--color-text-muted)' }}>档案馆</Link>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center gap-6">
        {experiment ? (
          <>
            <Companion type={experiment.draft.companionType} variant={experiment.draft.companionVariant}
              stage={experiment.companionStage} isCooling={experiment.status === 'cooling'} size="lg" />
            <p className="text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
              {experiment.idea.content}
            </p>
            {checkedInToday
              ? <div className="px-6 py-3 rounded-full text-sm"
                  style={{ background: 'var(--color-accent-soft)', color: 'var(--color-accent)' }}>
                  ✓ 今天已出发
                </div>
              : <Link href="/experiment" className="px-8 py-4 rounded-full font-semibold text-white text-lg"
                  style={{ background: 'var(--color-accent)' }}>
                  今天已出发 ✓
                </Link>
            }
          </>
        ) : (
          <>
            <div className="text-7xl">🌱</div>
            <p className="text-center" style={{ color: 'var(--color-text-muted)' }}>还没有进行中的实验</p>
            <Link href="/activate" className="px-8 py-4 rounded-full font-semibold text-white"
              style={{ background: 'var(--color-accent)' }}>
              启动第一个实验
            </Link>
          </>
        )}
      </div>

      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium">浮动想法</span>
          <Link href="/capture" className="text-sm" style={{ color: 'var(--color-accent)' }}>+ 记录</Link>
        </div>
        <IdeaBubbleList ideas={ideas} onActivate={async (idea) => {
          'use server'
          redirect(`/activate?idea=${idea.id}`)
        }} />
      </div>
    </main>
  )
}
```

- [ ] **Step 3: Verify full flow in browser**

```bash
npm run dev
# Full golden path:
# / → /capture (type idea) → / (bubble appears) → /activate (5 steps) → /experiment (check in) → /archive
```

- [ ] **Step 4: Commit**

```bash
git add app/page.tsx app/layout.tsx
git commit -m "feat: add home page with companion, check-in CTA, and idea bubbles"
```

---

## Task 14: Archive Pages

**Files:**
- Create: `app/archive/page.tsx`
- Create: `app/archive/[id]/page.tsx`

- [ ] **Step 1: Create app/archive/page.tsx**

```typescript
import { listArchives } from '@/actions/archives'
import Link from 'next/link'

export default async function ArchivePage() {
  const archives = await listArchives()

  return (
    <main className="min-h-screen p-6" style={{ background: 'var(--color-bg)' }}>
      <div className="max-w-sm mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">档案馆</h1>
          <Link href="/" className="text-sm" style={{ color: 'var(--color-text-muted)' }}>← 主屏</Link>
        </div>
        {archives.length === 0
          ? <div className="text-center py-12 space-y-3">
              <div className="text-5xl">📚</div>
              <p style={{ color: 'var(--color-text-muted)' }}>还没有归档的实验</p>
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                每完成一个实验，它就会成为这里的一本书
              </p>
            </div>
          : <div className="grid grid-cols-2 gap-4">
              {archives.map(a => (
                <Link key={a.id} href={`/archive/${a.id}`}
                  className="p-4 rounded-2xl space-y-2 hover:scale-105 transition-transform"
                  style={{ background: 'var(--color-surface-raised)', border: '1.5px solid var(--color-accent-soft)' }}>
                  <div className="text-3xl">📖</div>
                  <p className="text-sm font-medium line-clamp-2">{a.bestMoment}</p>
                  <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    {new Date(a.exploredAt).toLocaleDateString('zh-CN')}
                  </p>
                </Link>
              ))}
            </div>
        }
      </div>
    </main>
  )
}
```

- [ ] **Step 2: Create app/archive/[id]/page.tsx**

```typescript
import { getArchive } from '@/actions/archives'
import { notFound } from 'next/navigation'
import Link from 'next/link'

export default async function ArchiveDetailPage({ params }: { params: { id: string } }) {
  const archive = await getArchive(params.id)
  if (!archive) notFound()

  return (
    <main className="min-h-screen p-6" style={{ background: 'var(--color-bg)' }}>
      <div className="max-w-sm mx-auto space-y-6">
        <Link href="/archive" className="text-sm" style={{ color: 'var(--color-text-muted)' }}>← 档案馆</Link>
        <div className="text-center space-y-2">
          <div className="text-5xl">🏆</div>
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
            已探索 · {new Date(archive.exploredAt).toLocaleDateString('zh-CN')}
          </p>
        </div>
        {[
          { label: '最爽的瞬间', value: archive.bestMoment, emoji: '✨' },
          { label: '学到了', value: archive.learned, emoji: '💡' },
          { label: '下次重启的第一步', value: archive.restartStep, emoji: '🚀' },
        ].map(({ label, value, emoji }) => (
          <div key={label} className="p-4 rounded-2xl space-y-2"
            style={{ background: 'var(--color-surface-raised)' }}>
            <p className="text-sm font-medium" style={{ color: 'var(--color-text-muted)' }}>{emoji} {label}</p>
            <p>{value}</p>
          </div>
        ))}
        <p className="text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
          将于 {new Date(archive.resurfaceAt).toLocaleDateString('zh-CN')} 重新出现在灵感池
        </p>
      </div>
    </main>
  )
}
```

- [ ] **Step 3: Verify in browser**

```bash
npm run dev
# /archive — should show empty state or book grid after completing experiment
```

- [ ] **Step 4: Commit**

```bash
git add app/archive/
git commit -m "feat: add archive list and detail pages"
```

---

## Task 15: PWA Config

**Files:**
- Create: `public/manifest.json`
- Modify: `next.config.ts`

- [ ] **Step 1: Create public/manifest.json**

```json
{
  "name": "想法花园",
  "short_name": "想法花园",
  "description": "启动了已经很好了",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#fdf8f0",
  "theme_color": "#f5a623",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "shortcuts": [
    {
      "name": "记录想法",
      "short_name": "记录",
      "url": "/capture",
      "icons": [{ "src": "/icons/icon-192.png", "sizes": "192x192" }]
    }
  ]
}
```

- [ ] **Step 2: Generate placeholder icons**

Create `scripts/gen-icons.mjs`:
```javascript
import sharp from 'sharp'
import fs from 'fs'

fs.mkdirSync('public/icons', { recursive: true })

const makeSvg = (size) => `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">
  <rect width="${size}" height="${size}" rx="${size * 0.2}" fill="#f5a623"/>
  <text x="${size/2}" y="${size * 0.72}" font-size="${size * 0.52}" text-anchor="middle">🌱</text>
</svg>`

await sharp(Buffer.from(makeSvg(192))).png().toFile('public/icons/icon-192.png')
await sharp(Buffer.from(makeSvg(512))).png().toFile('public/icons/icon-512.png')
console.log('Icons generated ✓')
```

```bash
npm install -D sharp
node scripts/gen-icons.mjs
```

- [ ] **Step 3: Update next.config.ts**

```typescript
import type { NextConfig } from 'next'
// @ts-ignore
import withPWA from 'next-pwa'

const nextConfig: NextConfig = { reactStrictMode: true }

export default withPWA({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true,
  skipWaiting: true,
})(nextConfig)
```

- [ ] **Step 4: Verify manifest**

```bash
npm run build && npm start
# Open http://localhost:3000/manifest.json — verify JSON response
# Chrome DevTools → Application → Manifest — verify fields
# Mobile: "Add to Home Screen" should appear
```

- [ ] **Step 5: Commit**

```bash
git add public/ next.config.ts scripts/
git commit -m "feat: add PWA manifest with /capture home screen shortcut"
```

---

## Task 16: Run All Tests

- [ ] **Step 1: Run full test suite**

```bash
npm test
# Expected: all tests PASS
# Test files: types, db, ideas, experiments, archives, daily-prompt, ai, Companion, IdeaBubble
```

- [ ] **Step 2: Fix any failures**

If any test fails, investigate the error and fix the implementation (not the test, unless the test has a genuine bug).

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: verify all tests pass for MVP phase 1"
```

---

## Self-Review

**Spec coverage:**
- ✅ 功能1 想法孵化器: Tasks 9 (IdeaBubble) + 10 (/capture) + 13 (Home)
- ✅ 功能2 实验许可证 + AI辅填: Tasks 7 (ai.ts) + 11 (/activate)
- ✅ 功能3 单任务实验区 + 三层签到: Task 12 (CheckinPanel)
- ✅ 功能4 荣耀档案馆: Tasks 5 (archives actions) + 12 (CoolingPanel) + 14 (/archive)
- ✅ 功能5 陪伴物 5级成长: Task 8 (Companion) + wired through experiments
- ✅ PWA + /capture shortcut: Task 15
- ✅ 冷却自动检测 (3天未签到): Included in Task 4 (checkAndStartCooling)

**Type consistency:**
- `createDraft` input → `ExperimentDraft` fields: match ✅
- `checkin(experimentId, {minData?, energyTag?})` → `CheckinPanel` call: match ✅
- `createArchive` input → `Archive` interface: match ✅
- `Companion` props `(type, variant, stage)` → types in `types/index.ts`: match ✅
- `getActiveExperiment` returns `ExperimentWithDetails` — includes `.draft.companionType` used in Home and Experiment pages: match ✅

**Placeholder scan:** No TBDs, TODOs, or "similar to Task N" shorthand found.
