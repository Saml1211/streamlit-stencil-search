# Implementation Plan for Critical Enhancements  
*(Visio Stencil Search – Phase 1)*  

---

## 1. Search-Mode Clarity & Result-Source Distinction

### 1.1. Objectives  
- Make it obvious **where** results come from.  
- Default to "Stencil Directory Only"; users explicitly opt-in to document search.  

### 1.2. Action Steps  

| # | Task | Key Files / Modules | Notes |
|---|------|--------------------|-------|
| 1 | **Rename toggle** label to "Include Visio Document Shapes" + explanatory tooltip | `modules/Visio_Stencil_Explorer.py` | Already prototyped – finalize wording & i18n key. |
| 2 | **Add info banner** when document search is OFF (blue `st.info`) | Same file | Display under search bar once per session. |
| 3 | **Tag results** with `result_source` field (`stencil_directory` / `visio_document`) in `perform_search()` | Same file | Ensure database & document search inject the tag. |
| 4 | **Visual indicators** in result rows:  | • `modules/Visio_Stencil_Explorer.py`<br>• `custom_styles.css` | Add colored badge (`Stencil` vs `Document`). |
| 5 | **Grouped tabs** (Stencil / Document / All) when both sources present | Same | Use `st.tabs` for first-class UX. |
| 6 | **Unit tests** for tagging & grouping | `test_search_modes.py` (new) | Use pytest to assert correct tag counts. |

### 1.3. Required Resources  
- Streamlit (existing)  
- Minor CSS additions  
- Dev: 4-6 hrs

### 1.4. Potential Challenges  
- Large mixed result sets → performance in tab switching.  
- Badge CSS conflicts with high-contrast theme (address in Step 5).  

### 1.5. Measurable Outcomes  
- 🚀 100 % of result rows show correct badge.  
- 🙋 90 % of beta users correctly identify search mode (survey).  
- ⏱️ No measurable slowdown (<5 ms extra per 100 rows).

---

## 2. Persistent User Preferences

### 2.1. Objectives  
- Save key toggles (document search, FTS, limit, pagination, UI theme) across sessions.  
- Provide settings UI & reset-to-default.

### 2.2. Action Steps  

| # | Task | Key Files | Notes |
|---|------|-----------|-------|
| 1 | Implement `UserPreferences` class (JSON file storage) | `app/core/preferences.py` (new) | Methods: `get`, `set`, `save`, `load`. |
| 2 | Instantiate via `@st.cache_resource` and inject into session state | `app.py` | Single source of truth. |
| 3 | Replace hard-coded defaults with calls to prefs | All pages using `st.session_state` defaults | Search toggle, result limit, high contrast, etc. |
| 4 | Build **Settings** expander in sidebar | `modules/Visio_Stencil_Explorer.py` | Controls: search defaults, result/page, Visio auto-refresh. |
| 5 | **Reset** button → wipe JSON & reload defaults | Same | Call `prefs = UserPreferences(); prefs.save()`. |
| 6 | Unit tests for read/write & fallback logic | `test_preferences.py` (new) | Simulate corrupt JSON. |

### 2.3. Required Resources  
- Small JSON file (`app/data/user_preferences.json`)  
- ≈4 hrs dev + UX copy

### 2.4. Potential Challenges  
- File write permissions on restricted installs.  
- Backward compatibility when adding new prefs keys (use defaults).  

### 2.5. Measurable Outcomes  
- Preferences persist after browser refresh & Streamlit restart.  
- No error in log on corrupt/missing prefs (auto-recreate).  

---

## 3. Enhanced Error Handling & Diagnostics

### 3.1. Objectives  
- Provide user-friendly, actionable error messages.  
- Central diagnostics panel for logs & system status.

### 3.2. Action Steps  

| # | Task | Key Files | Notes |
|---|------|-----------|-------|
| 1 | Create `handle_visio_errors` decorator as wrapper | `app/core/error_utils.py` (new) | Categorize common COM errors. |
| 2 | Apply decorator to visio integration methods | `app/core/visio_integration.py` | Wrap dynamic attributes. |
| 3 | Implement `MemoryStreamHandler` for in-app logs | `app/core/logging_utils.py` | Keep last N entries. |
| 4 | Diagnostics sidebar expander (status + logs) | `modules/Visio_Stencil_Explorer.py` | Select log level dropdown. |
| 5 | "Copy logs" button -> clipboard (browser JS) | Same | For support tickets. |
| 6 | Integration tests simulating Visio unavailable | `test_error_paths.py` (new) | Expect wrapped error messages. |

### 3.3. Required Resources  
- Logging module (already used)  
- 1 day dev/test

### 3.4. Potential Challenges  
- Streamlit textarea performance with large log buffers (truncate).  
- COM exceptions sometimes uninformative → map generically.  

### 3.5. Measurable Outcomes  
- 100 % of Visio errors produce categorized message.  
- Diagnostics shows latest 100 log lines in <50 ms render time.  

---

## 4. Performance Enhancements (Debounce + Preview Cache)

### 4.1. Objectives  
- Prevent redundant searches while typing.  
- Speed up preview rendering via disk cache.  

### 4.2. Action Steps  

| # | Task | Key Files | Notes |
|---|------|-----------|-------|
| 1 | Implement `DebounceSearch` helper (threading.Timer) | `app/core/utils.py` (new) | Delay 0.5 s default. |
| 2 | Integrate debouncer in search input on_change | `modules/Visio_Stencil_Explorer.py` | Replace immediate `perform_search()`. |
| 3 | Build `PreviewCache` class (PNG disk cache) | `app/core/preview_cache.py` (new) | `get_cached_preview` / `save_preview`. |
| 4 | Wrap `get_shape_preview` call with cache check | Same search module | Return cached img if fresh. |
| 5 | Cache management UI (show stats + clear) | Sidebar expander | Button triggers `preview_cache.clear_cache()`. |
| 6 | Benchmark before/after (search & preview) | `perf_notebook.ipynb` | Record median latency. |

### 4.3. Required Resources  
- PIL (already in reqs)  
- Disk space for cache (~50 MB)  
- 6-8 hrs dev/bench

### 4.4. Potential Challenges  
- Cache invalidation when stencil updated (use mtime).  
- Thread safety with debouncer in Streamlit's rerun model.  

### 4.5. Measurable Outcomes  
- Keystroke → query count reduced ≥70 %.  
- Preview repeat load time <100 ms (was >500 ms).  
- No debounce-missed query bug in manual QA.  

---

## 5. Search Logic Improvements (Advanced Query & Property Filters)

### 5.1. Objectives  
- Empower users with AND/OR, phrase, exclusion, property search.  
- Retain FTS performance advantages.

### 5.2. Action Steps  

| # | Task | Key Files | Notes |
|---|------|-----------|-------|
| 1 | Build `parse_search_query()` util (regex parse) | `app/core/query_parser.py` | Return structured dict. |
| 2 | Update `search_stencils_db()` to convert parsed query → effective FTS string | `modules/Visio_Stencil_Explorer.py` | AND = space; OR = `"term1 OR term2"`; NOT via post-filter. |
| 3 | Post-filter results for excluded terms & property matches | Same | Iterate results list. |
| 4 | Extend UI help (❓) with syntax doc | Help system | Provide examples. |
| 5 | Unit tests for parser & search result correctness | `test_advanced_search.py` | 10 cases min. |

### 5.3. Required Resources  
- Python `re` stdlib  
- 8-10 hrs dev/test

### 5.4. Potential Challenges  
- Complex queries may break FTS ranking → handle gracefully.  
- Property JSON varies (case, arrays) – normalize.  

### 5.5. Measurable Outcomes  
- Parser passes all unit tests.  
- User can find shape with `prop:Value` query in demo dataset.  
- No >10 % slowdown vs. baseline FTS search.  

---

## Summary Timeline (Effort Estimate)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | **Search-Mode Clarity** | Toggle, badges, tabs, unit tests |
| 2 | **User Preferences** | JSON prefs system, settings UI, reset |
| 3 | **Error Handling** | Decorators, diagnostics panel, tests |
| 4 | **Performance** | Debounce, preview cache, benchmarks |
| 5–6 | **Advanced Search Logic** | Parser, UI doc, tests |

Total effort ≈ **5–6 weeks** single-dev; parallelizable to shorten.

**Success Metrics:**  
- Search clarity survey score +30 %.  
- Avg search latency ↓ 25 %.  
- User-reported "can't find shape" tickets ↓ 50 %.  

> This plan provides a clear roadmap with actionable steps, resource needs, anticipated challenges, and measurable outcomes—ready to guide execution in a new development conversation. 