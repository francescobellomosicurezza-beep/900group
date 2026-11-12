# Graph Report - novecento  (2026-11-12)

## Corpus Check
- 25 files · ~6,787 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .css 2, .example 1)

## Summary
- 204 nodes · 341 edges · 18 communities (10 shown, 8 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 28 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a98958e9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- views.py
- admin.py
- pdf.py
- models.py
- manage.py
- FlussoOrdineTest
- OrdineAdmin
- Gelateria Novecento — Menu di riferimento
- SedeAdminForm
- CategoriaForm
- Ordine
- RigaOrdine
- Novecento – Ordini punti vendita
- apps.py

## God Nodes (most connected - your core abstractions)
1. `FlussoOrdineTest` - 21 edges
2. `Ordine` - 17 edges
3. `Sede` - 16 edges
4. `Articolo` - 11 edges
5. `genera_pdf_ordine()` - 11 edges
6. `Gelateria Novecento — Menu di riferimento` - 11 edges
7. `SedeAdminForm` - 10 edges
8. `invia_ordine()` - 10 edges
9. `riepilogo()` - 10 edges
10. `categoria()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `SedeAdminForm` --uses--> `Sede`  [INFERRED]
  novecento/admin.py → novecento/models.py
- `ArticoloInline` --uses--> `Articolo`  [INFERRED]
  novecento/admin.py → novecento/models.py
- `categoria()` --uses--> `CategoriaForm`  [INFERRED]
  novecento/views.py → novecento/forms.py
- `Command` --uses--> `Sede`  [INFERRED]
  novecento/management/commands/crea_accesso_sede.py → novecento/models.py
- `CredenzialiSedeTest` --uses--> `Sede`  [INFERRED]
  novecento/tests.py → novecento/models.py

## Import Cycles
- None detected.

## Communities (18 total, 8 thin omitted)

### Community 0 - "views.py"
Cohesion: 0.11
Nodes (20): OperatoreForm, RiepilogoForm, SedeForm, Sede, Meta, annulla(), _bozza(), categoria() (+12 more)

### Community 1 - "admin.py"
Cohesion: 0.11
Nodes (6): ArticoloInline, Articolo, Meta, Unita, Categoria, Meta

### Community 2 - "pdf.py"
Cohesion: 0.12
Nodes (4): invia_ordine(), genera_pdf_ordine(), nome_file_pdf(), _stili()

### Community 3 - "models.py"
Cohesion: 0.11
Nodes (4): Command, Migration, Migration, Migration

### Community 6 - "OrdineAdmin"
Cohesion: 0.18
Nodes (4): ArticoloAdmin, CategoriaAdmin, OrdineAdmin, SedeAdmin

### Community 7 - "Gelateria Novecento — Menu di riferimento"
Cohesion: 0.17
Nodes (11): Caffetteria, Crêpes, Food, Gelateria — Coni, Gelateria — Coppe, Gelateria — Extra, Gelateria Novecento — Menu di riferimento, Gelateria — Vaschette da asporto (+3 more)

### Community 8 - "SedeAdminForm"
Cohesion: 0.27
Nodes (3): SedeAdminForm, Meta, CredenzialiSedeTest

### Community 10 - "Ordine"
Cohesion: 0.33
Nodes (3): Ordine, Meta, StatoInvio

### Community 11 - "RigaOrdine"
Cohesion: 0.33
Nodes (3): RigaOrdineInline, RigaOrdine, Meta

### Community 12 - "Novecento – Ordini punti vendita"
Cohesion: 0.33
Nodes (5): Amministrazione (`/admin/`), Avvio in locale, Flusso, Novecento – Ordini punti vendita, Test

## Knowledge Gaps
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Sede` connect `views.py` to `SedeAdminForm`, `admin.py`, `models.py`, `FlussoOrdineTest`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `FlussoOrdineTest` (e.g. with `Articolo` and `Categoria`) actually correct?**
  _`FlussoOrdineTest` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `views.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Why does `FlussoOrdineTest` connect `FlussoOrdineTest` to `views.py`, `admin.py`, `pdf.py`, `SedeAdminForm`, `Ordine`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `Ordine` (e.g. with `invia_ordine()` and `FlussoOrdineTest`) actually correct?**
  _`Ordine` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Should `admin.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11462450592885376 - nodes in this community are weakly interconnected._
- **Why does `Ordine` connect `Ordine` to `views.py`, `admin.py`, `pdf.py`, `models.py`, `FlussoOrdineTest`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._