import uvicorn as uvicorn

from h3_test_task.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
