# MINDMAP (Dev)

```mermaid
flowchart TD
  A[Clowbot]:::doing

  A --> B[MVP baseline]:::doing
  B --> B1[Docker Compose: api/worker/postgres/redis/qdrant/minio]:::done
  B --> B2[Science grants workflow (mock)]:::done
  B --> B3[Health endpoint]:::done

  A --> J[Jarvis execution layer]:::doing
  J --> J1[Mindmap overview endpoint]:::done
  J --> J2[Custom Mindmaps endpoints]:::done
  J --> J3[Approvals Queue: pending_actions + approve/reject API]:::done
  J --> J4[Outbox: outbox_messages + list API]:::done
  J --> J5[ToolRegistry v1 (stub + audit)]:::done
  J --> J6[Worker execution for APPROVED actions]:::done
  J --> J7[Outbox Dispatcher (stub)]:::done
  J --> J8[Outbox Contract v1 + Preview Pack]:::doing
  J --> J9[Skill Runner v0]:::doing
  J --> J10[Portfolio Manager (PORTFOLIO.md + weekly review)]:::todo

  classDef done fill:#b7f7c5,stroke:#1f7a2e,color:#000;
  classDef doing fill:#ffe8a3,stroke:#8a6d00,color:#000;
  classDef todo fill:#e6e6e6,stroke:#666,color:#000;
```
