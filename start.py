import subprocess
import sys

def main():
    """Run the FastAPI server using uvicorn with reload enabled."""
    print("🚀 Starting the Medical Dashboard Backend...")
    try:
        # We use uv run uvicorn directly as requested
        subprocess.run(["uvicorn", "app.main:app", "--reload"], shell=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

    
