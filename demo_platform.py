import os
import time
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from rich.align import Align

console = Console()

def run_demo(base_url: str):
    console.print(Panel(Align.center("[bold cyan]Agent Eval Platform - Production Demo[/bold cyan]\n[dim]Testing Live API Endpoints[/dim]"), border_style="cyan"))

    # 1. Health Check
    with console.status("[bold green]Checking API Health...", spinner="dots"):
        try:
            res = requests.get(f"{base_url}/health")
            res.raise_for_status()
            time.sleep(0.5) # Slight delay for dramatic effect in CLI
            console.print("[bold green]✓ API is healthy and reachable![/bold green]")
        except Exception as e:
            console.print(f"[bold red]✗ Failed to reach API at {base_url}: {e}[/bold red]")
            return

    # 2. Create a Task
    task_payload = {
        "question": "What is the capital of India?",
        "expected_answer": "The capital of India is New Delhi.",
        "required_tools": ["lookup_data"]
    }
    
    with console.status("[bold blue]Creating Evaluation Task...", spinner="bouncingBar"):
        time.sleep(0.5)
        res = requests.post(f"{base_url}/tasks", json=task_payload)
        if res.status_code == 200:
            task = res.json()
            console.print("\n[bold green]✓ Task Created Successfully[/bold green]")
            
            task_table = Table(title="New Task Details", show_header=True, header_style="bold magenta", expand=True)
            task_table.add_column("ID", style="dim", justify="center")
            task_table.add_column("Question")
            task_table.add_column("Expected Answer")
            task_table.add_column("Tools")
            
            task_table.add_row(
                str(task.get("id", "-")),
                task.get("question", ""),
                task.get("expected_answer", ""),
                ", ".join(task.get("required_tools", []))
            )
            console.print(task_table)
            console.print("\n")
        else:
            console.print(f"[bold red]✗ Failed to create task: {res.text}[/bold red]")
            return

    # 3. Trigger Evaluation
    console.print("[bold yellow]Triggering AI Agent Evaluation (This will take a moment as the agent thinks...)[/bold yellow]")
    
    with Progress(
        SpinnerColumn(spinner_name="point"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Evaluating Agent Actions in real-time...", total=None)
        start_time = time.time()
        
        # Make the request to trigger evaluations
        res = requests.post(f"{base_url}/evaluations/run")
        duration = time.time() - start_time
        
    if res.status_code == 200:
        results = res.json().get("results", [])
        console.print(f"[bold green]✓ Evaluation Completed in {duration:.2f} seconds[/bold green]\n")
        
        # Display Results
        res_table = Table(title="Evaluation Results", show_header=True, header_style="bold cyan", expand=True)
        res_table.add_column("Task ID", justify="center")
        res_table.add_column("Agent Answer")
        res_table.add_column("Score", justify="center")
        res_table.add_column("Status", justify="center")
        
        for r in results:
            scores_dict = r.get("scores", {})
            score = scores_dict.get("correctness", 0.0)
            # Threshold for passing is usually 0.7 or 0.8 depending on the evaluator logic
            status_color = "green" if score > 0.7 else "red"
            status_text = "PASS" if score > 0.7 else "FAIL"
            
            res_table.add_row(
                str(r.get("task_id", "-")),
                str(r.get("agent_output", "N/A")),
                f"{score:.2f}",
                f"[bold {status_color}]{status_text}[/bold {status_color}]"
            )
            
        console.print(res_table)
        console.print(Panel(Align.center(f"[bold green]Demo execution finished successfully![/bold green]\nProcessed {len(results)} total tasks."), border_style="green"))
    else:
        console.print(f"[bold red]✗ Evaluation failed: {res.text}[/bold red]")

if __name__ == "__main__":
    import sys
    
    # Accept URL from command line or use a default
    if len(sys.argv) > 1:
        URL = sys.argv[1].rstrip("/")
    else:
        URL = os.getenv("API_URL", "http://localhost:8000")
        console.print("[dim italic]No URL provided as argument. Using default.[/dim italic]")
        console.print("[dim italic]Usage: python demo_platform.py https://<your-vercel-app>.vercel.app[/dim italic]\n")
        
    run_demo(URL)
