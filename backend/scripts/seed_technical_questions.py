"""One-time content-curation script for the RAG technical-question bank.
Not an Alembic migration - embedding computation is slow and needs the
local model loaded, not idempotent-migration-shaped.

Run manually, from the backend/ directory, after `alembic upgrade head`:

    python -m scripts.seed_technical_questions

Safe to re-run: clears and re-inserts every row rather than appending
duplicates.
"""

import asyncio

import structlog
from sqlalchemy import delete

from app.core.db import get_session_factory
from app.core.embeddings import embed_text
from app.models.technical_question import TechnicalQuestion

logger = structlog.get_logger(__name__)


QUESTIONS: list[dict] = [
    # --- DBMS ---
    {
        "question_text": (
            "What are the ACID properties of a database transaction? Give "
            "a concrete example of a bug that occurs if Isolation is lost."
        ),
        "topic": "DBMS",
        "tech_stack": ["SQL", "PostgreSQL", "MySQL"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "Explain database normalization up to 3NF. Why would you "
            "deliberately denormalize a table in a real system?"
        ),
        "topic": "DBMS",
        "tech_stack": ["SQL"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "How does a B-tree index speed up a query, and when can adding "
            "an index actually make a table slower to use?"
        ),
        "topic": "DBMS",
        "tech_stack": ["SQL", "PostgreSQL"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "What's the difference between an INNER JOIN, a LEFT JOIN, and "
            "a FULL OUTER JOIN? Give an example query for each."
        ),
        "topic": "DBMS",
        "tech_stack": ["SQL"],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "What causes a deadlock between two database transactions, and "
            "how does Postgres detect and resolve one?"
        ),
        "topic": "DBMS",
        "tech_stack": ["SQL", "PostgreSQL"],
        "difficulty": "hard",
        "seniority": "senior",
    },
    {
        "question_text": (
            "When would you reach for a NoSQL document store like MongoDB "
            "instead of a relational database? What do you give up?"
        ),
        "topic": "DBMS",
        "tech_stack": ["MongoDB", "NoSQL", "SQL"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "How would you shard a large Postgres table across multiple "
            "machines, and what query patterns does sharding make harder?"
        ),
        "topic": "DBMS",
        "tech_stack": ["PostgreSQL", "Distributed Systems"],
        "difficulty": "hard",
        "seniority": "senior",
    },
    {
        "question_text": (
            "What's the N+1 query problem in an ORM, and how do you fix it?"
        ),
        "topic": "DBMS",
        "tech_stack": ["SQL", "ORM", "SQLAlchemy", "Django"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    # --- Operating Systems ---
    {
        "question_text": (
            "What's the difference between a process and a thread? What "
            "does each cost to create and switch between?"
        ),
        "topic": "OS",
        "tech_stack": [],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "What are the four conditions required for a deadlock to "
            "occur, and how does breaking just one of them prevent it?"
        ),
        "topic": "OS",
        "tech_stack": [],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "Explain virtual memory and paging. What happens on a page fault?"
        ),
        "topic": "OS",
        "tech_stack": [],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "What's the difference between a mutex and a semaphore? Give "
            "an example where you'd need a semaphore specifically."
        ),
        "topic": "OS",
        "tech_stack": ["Concurrency"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "Compare preemptive and cooperative scheduling. Why did most "
            "modern OSes move to preemptive?"
        ),
        "topic": "OS",
        "tech_stack": [],
        "difficulty": "hard",
        "seniority": "senior",
    },
    {
        "question_text": (
            "What happens, step by step, when you run a program from the "
            "shell - from the exec() call to the first instruction?"
        ),
        "topic": "OS",
        "tech_stack": ["Linux"],
        "difficulty": "hard",
        "seniority": "senior",
    },
    # --- Networking ---
    {
        "question_text": (
            "What's the difference between TCP and UDP? Give a real "
            "protocol/use case built on each."
        ),
        "topic": "Networking",
        "tech_stack": [],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "Walk through what happens during a TLS handshake when you "
            "visit an HTTPS site."
        ),
        "topic": "Networking",
        "tech_stack": ["HTTPS", "TLS"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "How does DNS resolution work, from typing a URL to getting "
            "an IP address back?"
        ),
        "topic": "Networking",
        "tech_stack": ["DNS"],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "What's the difference between a load balancer operating at "
            "L4 versus L7? When would you need L7?"
        ),
        "topic": "Networking",
        "tech_stack": ["Load Balancing", "System Design"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "Compare REST and GraphQL for an API. What problem does "
            "GraphQL actually solve, and what does it cost you?"
        ),
        "topic": "Networking",
        "tech_stack": ["REST", "GraphQL", "API Design"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "How does a WebSocket connection differ from regular HTTP "
            "requests, and why would you use one over polling?"
        ),
        "topic": "Networking",
        "tech_stack": ["WebSockets"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    # --- OOP & Design ---
    {
        "question_text": (
            "Explain encapsulation, inheritance, and polymorphism with a "
            "real example from something you've built."
        ),
        "topic": "OOP",
        "tech_stack": [],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            '"Favor composition over inheritance" - what problem with '
            "deep inheritance hierarchies does this advice avoid?"
        ),
        "topic": "OOP",
        "tech_stack": ["Design Patterns"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "Pick one SOLID principle and explain it with a before/after "
            "example of code that violates then follows it."
        ),
        "topic": "OOP",
        "tech_stack": ["SOLID", "Design Patterns"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "What's the difference between an abstract class and an "
            "interface? When would you pick one over the other?"
        ),
        "topic": "OOP",
        "tech_stack": [],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "Describe a situation where you used (or would use) the "
            "Observer or Strategy design pattern."
        ),
        "topic": "OOP",
        "tech_stack": ["Design Patterns"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    # --- System Design basics ---
    {
        "question_text": (
            "What's the difference between horizontal and vertical "
            "scaling? What kind of application is hard to scale "
            "horizontally?"
        ),
        "topic": "System Design",
        "tech_stack": [],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "Design a URL shortener at a high level: what are the main "
            "components, and where's the bottleneck at scale?"
        ),
        "topic": "System Design",
        "tech_stack": ["System Design"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "Explain the CAP theorem. Which two would you pick for a "
            "shopping cart service, and why?"
        ),
        "topic": "System Design",
        "tech_stack": ["Distributed Systems"],
        "difficulty": "hard",
        "seniority": "senior",
    },
    {
        "question_text": (
            "When would you put a message queue (like Kafka or RabbitMQ) "
            "between two services instead of calling one directly?"
        ),
        "topic": "System Design",
        "tech_stack": ["Kafka", "RabbitMQ", "Message Queues"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "How would you design a rate limiter for a public API? "
            "Compare token bucket versus sliding window."
        ),
        "topic": "System Design",
        "tech_stack": ["System Design", "API Design"],
        "difficulty": "hard",
        "seniority": "senior",
    },
    {
        "question_text": (
            "What are the tradeoffs between caching at the CDN, "
            "application, and database layer?"
        ),
        "topic": "System Design",
        "tech_stack": ["Caching", "Redis", "CDN"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "Design the high-level architecture for a real-time chat "
            "app's message delivery. How do you handle a recipient who's "
            "offline?"
        ),
        "topic": "System Design",
        "tech_stack": ["System Design", "WebSockets"],
        "difficulty": "hard",
        "seniority": "senior",
    },
    # --- Python ---
    {
        "question_text": (
            "What is the GIL in CPython, and how does it affect a "
            "CPU-bound multithreaded program versus an I/O-bound one?"
        ),
        "topic": "Python",
        "tech_stack": ["Python"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "Why is using a mutable default argument (like a list) in a "
            "Python function signature a common bug?"
        ),
        "topic": "Python",
        "tech_stack": ["Python"],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "What's the difference between a Python generator and "
            "returning a list? When does the difference actually matter?"
        ),
        "topic": "Python",
        "tech_stack": ["Python"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "Explain what a Python decorator does under the hood. Write "
            "one that times a function's execution."
        ),
        "topic": "Python",
        "tech_stack": ["Python"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "How does async/await work in Python? What actually happens "
            "if you call a blocking function inside an async function?"
        ),
        "topic": "Python",
        "tech_stack": ["Python", "asyncio"],
        "difficulty": "hard",
        "seniority": "senior",
    },
    # --- JavaScript / TypeScript ---
    {
        "question_text": (
            "Explain the JavaScript event loop: how do the call stack, "
            "task queue, and microtask queue interact?"
        ),
        "topic": "JavaScript",
        "tech_stack": ["JavaScript"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "What's a closure in JavaScript? Give an example of a real bug "
            "caused by misunderstanding one (e.g. in a loop)."
        ),
        "topic": "JavaScript",
        "tech_stack": ["JavaScript"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "What's the difference between var, let, and const in terms "
            "of scoping and hoisting?"
        ),
        "topic": "JavaScript",
        "tech_stack": ["JavaScript"],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "Compare callbacks, Promises, and async/await for handling "
            "asynchronous code in JavaScript."
        ),
        "topic": "JavaScript",
        "tech_stack": ["JavaScript"],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "How does prototypal inheritance in JavaScript differ from "
            "classical (class-based) inheritance?"
        ),
        "topic": "JavaScript",
        "tech_stack": ["JavaScript"],
        "difficulty": "hard",
        "seniority": "senior",
    },
    # --- General CS / Algorithms ---
    {
        "question_text": (
            "What's the time and space complexity of a hash table lookup "
            "in the average and worst case? What causes the worst case?"
        ),
        "topic": "Algorithms",
        "tech_stack": [],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "When would you choose recursion over an iterative loop, and "
            "what's the real cost of choosing recursion?"
        ),
        "topic": "Algorithms",
        "tech_stack": [],
        "difficulty": "easy",
        "seniority": "entry",
    },
    {
        "question_text": (
            "Compare quicksort and mergesort: time complexity, space "
            "complexity, and when you'd actually prefer one."
        ),
        "topic": "Algorithms",
        "tech_stack": [],
        "difficulty": "medium",
        "seniority": "mid",
    },
    {
        "question_text": (
            "What's the difference between a stack and a queue, and give "
            "a real system that's built around each."
        ),
        "topic": "Algorithms",
        "tech_stack": [],
        "difficulty": "easy",
        "seniority": "entry",
    },
]


async def main() -> None:
    async with get_session_factory()() as db:
        await db.execute(delete(TechnicalQuestion))
        for entry in QUESTIONS:
            embedding = await embed_text(
                entry["question_text"], task_type="RETRIEVAL_DOCUMENT"
            )
            db.add(TechnicalQuestion(**entry, embedding=embedding))
        await db.commit()
    logger.info("seed_technical_questions.done", count=len(QUESTIONS))


if __name__ == "__main__":
    asyncio.run(main())
