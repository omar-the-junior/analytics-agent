# WorkbookSession tool-contract prototype (throwaway)

## Question

Can a chat-scoped `WorkbookSession` safely combine pandas queries with openpyxl commits while
preserving an immutable source, a five-version working history, exact Stable-ID diffs, and an
explicit confirmation gate? This is a throwaway terminal prototype for issue #4, not production
code or an LLM integration.

## Run

```powershell
uv run python prototypes/workbook_session_contract/run.py
```

The app creates temporary Session Workbooks for both supplied artifacts. Use the displayed keys
to inspect a query, safe rejection, staged insert/update/delete, an unconfirmed commit rejection,
and a confirmed commit followed by a query against the new active version. Use `v` to run the
interactive contract assertions for tool-computed KPIs and spreadsheet-formula preservation.
