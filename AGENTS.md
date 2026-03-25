Always answer in Korean.

Treat this workspace as the PPE Guard project.

# PPE Guard Workspace Rules

## 1. Project Context
This project is an internal, on-premise PPE inspection solution for enterprise environments.

Core structure:
- Frontend connects to the backend server
- Backend is built with Flask API
- Backend connects to the customer database
- Frontend must not directly connect to the customer DB
- Deployment target is an internal network environment
- Backend is packaged and deployed with Docker
- Environment-specific values are managed through `.env` or configuration files

## 2. Architecture Principles
When proposing or editing code, preserve this default architecture:
- Frontend: input, server connection, result view
- Backend: validation, business logic, DB integration, result persistence
- Customer DB: accessed only by backend

Do not suggest architectures where:
- frontend directly accesses customer DB
- sensitive DB credentials are embedded in client code
- cloud-only deployment is assumed by default

## 3. Database Integration Rules
Assume customer environments may differ.

When handling DB-related tasks:
- prefer configuration-driven integration
- separate customer master data from service-owned tables
- treat employee/user identifiers as mapping keys
- recommend schema guide / DDL / mapping guide when needed
- do not assume identical table names or column names across customers

Default principle:
- customer-owned tables remain under customer control
- service-owned tables can be defined separately for app data such as request history, results, and logs

## 4. Deployment Rules
Assume on-premise deployment by the customer or infrastructure administrator.

When discussing deployment:
- prioritize Docker-based backend deployment
- mention `.env` or config-based setup when relevant
- distinguish clearly between application logic and infra/operator responsibilities
- do not assume SaaS-first operations unless explicitly requested

## 5. Product Scope Rules
Prioritize MVP scope first.

MVP includes:
- server connection
- video file or webcam input
- Flask processing API
- result save/query
- customer DB integration
- Docker deployment
- environment configuration guide

Treat these as lower priority unless explicitly requested:
- license/product key
- advanced admin page
- complex authorization system
- multi-tenant cloud architecture
- large-scale monitoring platform

## 6. PRD / Document Writing Rules
When writing PRD, proposal, or technical documents for this project:
- use formal and practical business language
- keep structure consistent with enterprise documentation
- separate environment configuration guide from DB schema/integration guide
- clearly distinguish required scope from future extension scope
- avoid overly speculative features

## 7. Coding Rules for This Workspace
When generating code:
- prefer Python for backend examples unless another language is already required
- keep Flask-based structure simple and production-aware
- avoid unnecessary abstraction
- preserve the current architecture and naming conventions
- make minimal, targeted changes only

## 8. Decision Default
If requirements are ambiguous, default to:
- enterprise internal deployment
- backend-mediated DB integration
- configuration-based environment differences
- maintainable MVP-first design