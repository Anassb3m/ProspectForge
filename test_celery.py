from app.workers.tasks import ingest_market_play

def main():
    print("Dispatching Celery test job...")
    # Send an ingestion task
    task = ingest_market_play.delay(play_code="DEFAULT", mode="decp", limit=5)
    print(f"Dispatched task: {task.id}")
    
    print("Waiting for task to process...")
    # Wait for the task to finish (or we could restart worker here)
    result = task.get(timeout=30)
    print(f"Task result: {result}")

if __name__ == "__main__":
    main()
