# Architecture

```
LLM Client (Claude/GPT)
   | JSON-RPC stdio or HTTP/SSE
   v
edgar-mcp server
  server.py -> companies.py -> client.py -> SEC EDGAR API
           -> filings.py  -> client.py
           -> concepts.py -> client.py
```
