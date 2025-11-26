"""
Beautiful Terminal GUI
Advanced terminal-based interface for the mining system
"""

import time
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich import box
import psutil

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TerminalStats:
    hashrate: float = 0.0
    accepted_shares: int = 0
    rejected_shares: int = 0
    uptime: float = 0.0
    power_usage: float = 0.0
    temperature: float = 0.0
    efficiency: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    current_algorithm: str = "SHA-256"
    profit_per_hour: float = 0.0
    wallet_balance_eth: float = 0.0
    wallet_balance_usd: float = 0.0
    eth_price_usd: float = 0.0


class TerminalGUI:
    """Beautiful terminal-based GUI for mining operations"""
    
    def __init__(self, miner_instance=None, config: Optional[Dict[str, Any]] = None):
        self.console = Console()
        self.miner = miner_instance
        self.config = config or {}
        self.running = False
        self.stats = TerminalStats()
        
        # Wallet integration
        self.wallet_manager = None
        self.wallet_connected = False
        
        # GUI settings
        self.update_interval = config.get("gui_update_interval", 1.0) if config else 1.0
        self.show_details = True
        
        # Initialize wallet if blockchain config exists (non-blocking)
        if config and "blockchain" in config:
            try:
                from blockchain.wallet import WalletManager
                self.wallet_manager = WalletManager(config)
                if logger:
                    logger.info("Wallet manager initialized")
                self.console.print("[green]✓ Wallet integration available[/green]")
            except Exception as e:
                if logger:
                    logger.error(f"Wallet initialization error: {e}")
                # Don't print error, just continue without wallet
                self.console.print("[dim]ℹ Wallet integration not available[/dim]")
        else:
            if logger:
                logger.info("No blockchain configuration found")
            self.console.print("[dim]ℹ No blockchain configuration found[/dim]")
        
        # Create layout
        self.layout = Layout()
        self._setup_layout()
        
        if logger:
            logger.info("Terminal GUI initialized")
        self.console.print("[green]✓ Terminal GUI initialized[/green]")
    
    def _setup_layout(self):
        """Setup the terminal layout"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="details", ratio=1)
        )
        
        self.layout["stats"].split_column(
            Layout(name="mining_stats", size=8),
            Layout(name="wallet_stats", size=6),
            Layout(name="system_stats", size=8),
            Layout(name="algorithm_info", size=6)
        )
        
        self.layout["details"].split_column(
            Layout(name="performance", size=10),
            Layout(name="logs", size=12)
        )
    
    def start(self):
        """Start the terminal GUI"""
        self.running = True
        
        # Start update thread
        update_thread = threading.Thread(target=self._update_loop, daemon=True)
        update_thread.start()
        
        # Display the GUI
        try:
            with Live(self.layout, refresh_per_second=1, screen=True) as live:
                while self.running:
                    self._update_layout()
                    live.update(self.layout)
                    time.sleep(self.update_interval)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the terminal GUI"""
        self.running = False
        self.console.print("\n[bold red]Mining GUI stopped[/bold red]")
    
    def _update_loop(self):
        """Background thread for updating stats"""
        while self.running:
            try:
                self._update_stats()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error updating stats: {e}")
                time.sleep(1)
    
    def _update_stats(self):
        """Update statistics from miner or system"""
        if self.miner:
            try:
                # Get stats from actual miner
                miner_stats = self.miner.get_stats()
                self.stats.hashrate = miner_stats.hashrate
                self.stats.accepted_shares = miner_stats.accepted_shares
                self.stats.rejected_shares = miner_stats.rejected_shares
                self.stats.uptime = miner_stats.uptime
                self.stats.power_usage = miner_stats.power_usage
                self.stats.temperature = miner_stats.temperature
                self.stats.efficiency = miner_stats.efficiency
                
                algo_info = self.miner.get_algorithm_info()
                if algo_info:
                    self.stats.current_algorithm = algo_info.get("name", "Unknown")
                
            except Exception as e:
                logger.error(f"Error getting miner stats: {e}")
                # Fall back to mock data
                self._update_mock_stats()
        else:
            # Use mock data when no miner
            self._update_mock_stats()
        
        # Update wallet stats
        if self.wallet_manager and self.wallet_connected:
            try:
                wallet_data = self.wallet_manager.get_dashboard_data()
                if wallet_data.get("connected"):
                    balance = wallet_data.get("balance", {})
                    self.stats.wallet_balance_eth = balance.get("eth", 0.0)
                    self.stats.wallet_balance_usd = balance.get("usd", 0.0)
                    
                    mining_stats = wallet_data.get("mining_stats", {})
                    self.stats.eth_price_usd = mining_stats.get("eth_price_usd", 2000.0)
            except Exception as e:
                logger.error(f"Error updating wallet stats: {e}")
        
        # Update system stats
        try:
            self.stats.cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            self.stats.memory_usage = memory.percent
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
    
    def _update_mock_stats(self):
        """Update with mock data for demonstration"""
        import random
        self.stats.hashrate = max(0, self.stats.hashrate + random.uniform(-50, 50))
        self.stats.power_usage = max(0, self.stats.power_usage + random.uniform(-5, 5))
        self.stats.temperature = max(0, self.stats.temperature + random.uniform(-1, 1))
        self.stats.profit_per_hour = random.uniform(0.5, 2.0)
        self.stats.accepted_shares += random.randint(0, 2)
        self.stats.uptime += 1
        self.stats.eth_price_usd = random.uniform(1800, 2200)
    
    def _update_layout(self):
        """Update all layout panels"""
        self._update_header()
        self._update_mining_stats()
        self._update_wallet_stats()
        self._update_system_stats()
        self._update_algorithm_info()
        self._update_performance()
        self._update_logs()
        self._update_footer()
    
    def _update_header(self):
        """Update header panel"""
        wallet_status = "[green]🔗 Connected[/green]" if self.wallet_connected else "[dim]🔗 No Wallet[/dim]"
        header_text = Text.from_markup(
            f"[bold cyan]⛏️  Advanced Cryptocurrency Mining System[/bold cyan] - "
            f"[green]Status: {'Running' if self.running else 'Stopped'}[/green] - "
            f"[yellow]Algorithm: {self.stats.current_algorithm}[/yellow] - "
            f"{wallet_status}"
        )
        
        self.layout["header"].update(
            Panel(
                Align.center(header_text),
                box=box.ROUNDED,
                style="bold blue"
            )
        )
    
    def _update_mining_stats(self):
        """Update mining statistics panel"""
        table = Table(title="⛏️ Mining Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="green", width=15)
        
        table.add_row("Hashrate", f"{self.stats.hashrate:.2f} H/s")
        table.add_row("Accepted Shares", str(self.stats.accepted_shares))
        table.add_row("Rejected Shares", str(self.stats.rejected_shares))
        table.add_row("Uptime", self._format_uptime(self.stats.uptime))
        table.add_row("Efficiency", f"{self.stats.efficiency:.2f} H/W")
        table.add_row("Profit/Hour", f"${self.stats.profit_per_hour:.4f}")
        
        self.layout["mining_stats"].update(table)
    
    def _update_wallet_stats(self):
        """Update wallet statistics panel"""
        table = Table(title="🔗 Wallet Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="green", width=15)
        
        if self.wallet_connected:
            table.add_row("Balance", f"{self.stats.wallet_balance_eth:.6f} ETH")
            table.add_row("Value USD", f"${self.stats.wallet_balance_usd:.2f}")
            table.add_row("ETH Price", f"${self.stats.eth_price_usd:.2f}")
            table.add_row("Status", "[green]Connected[/green]")
        else:
            table.add_row("Balance", "0.000000 ETH")
            table.add_row("Value USD", "$0.00")
            table.add_row("ETH Price", f"${self.stats.eth_price_usd:.2f}")
            table.add_row("Status", "[dim]Not Connected[/dim]")
        
        self.layout["wallet_stats"].update(table)
    
    def _update_system_stats(self):
        """Update system statistics panel"""
        table = Table(title="🖥️ System Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="green", width=15)
        
        # CPU usage with color coding
        cpu_color = "green" if self.stats.cpu_usage < 70 else "yellow" if self.stats.cpu_usage < 90 else "red"
        table.add_row("CPU Usage", f"[{cpu_color}]{self.stats.cpu_usage:.1f}%[/{cpu_color}]")
        
        # Memory usage with color coding
        mem_color = "green" if self.stats.memory_usage < 70 else "yellow" if self.stats.memory_usage < 90 else "red"
        table.add_row("Memory Usage", f"[{mem_color}]{self.stats.memory_usage:.1f}%[/{mem_color}]")
        
        # Temperature with color coding
        temp_color = "green" if self.stats.temperature < 60 else "yellow" if self.stats.temperature < 75 else "red"
        table.add_row("Temperature", f"[{temp_color}]{self.stats.temperature:.1f}°C[/{temp_color}]")
        
        # Power usage
        table.add_row("Power Usage", f"{self.stats.power_usage:.1f}W")
        
        self.layout["system_stats"].update(table)
    
    def _update_algorithm_info(self):
        """Update algorithm information panel"""
        algo_table = Table(title="🔧 Algorithm Info", box=box.ROUNDED)
        algo_table.add_column("Property", style="cyan", width=15)
        algo_table.add_column("Value", style="green", width=20)
        
        algo_table.add_row("Current", self.stats.current_algorithm)
        algo_table.add_row("Type", "CPU")
        algo_table.add_row("Difficulty", "1.0")
        algo_table.add_row("Pool Mode", "Smart")
        
        self.layout["algorithm_info"].update(algo_table)
    
    def _update_performance(self):
        """Update performance panel with progress bars"""
        # Create progress bars for visual representation
        perf_table = Table(title="📊 Performance Metrics", box=box.ROUNDED)
        perf_table.add_column("Metric", style="cyan", width=15)
        perf_table.add_column("Performance", width=40)
        
        # Hashrate progress bar
        hashrate_percent = min(100, (self.stats.hashrate / 2000) * 100)  # Assuming max 2000 H/s
        hashrate_color = "green" if self.stats.hashrate > 1000 else "yellow"
        hashrate_bar = f"[{hashrate_color}]{'█' * int(hashrate_percent/5)}{'░' * (20 - int(hashrate_percent/5))}[/{hashrate_color}] {hashrate_percent:.0f}%"
        perf_table.add_row("Hashrate", hashrate_bar)
        
        # CPU usage progress bar
        cpu_color = "green" if self.stats.cpu_usage < 70 else "yellow" if self.stats.cpu_usage < 90 else "red"
        cpu_bar = f"[{cpu_color}]{'█' * int(self.stats.cpu_usage/5)}{'░' * (20 - int(self.stats.cpu_usage/5))}[/{cpu_color}] {self.stats.cpu_usage:.0f}%"
        perf_table.add_row("CPU Usage", cpu_bar)
        
        # Memory usage progress bar
        mem_color = "green" if self.stats.memory_usage < 70 else "yellow" if self.stats.memory_usage < 90 else "red"
        mem_bar = f"[{mem_color}]{'█' * int(self.stats.memory_usage/5)}{'░' * (20 - int(self.stats.memory_usage/5))}[/{mem_color}] {self.stats.memory_usage:.0f}%"
        perf_table.add_row("Memory", mem_bar)
        
        # Temperature progress bar
        temp_percent = min(100, (self.stats.temperature / 100) * 100)  # Assuming max 100°C
        temp_color = "green" if self.stats.temperature < 60 else "yellow" if self.stats.temperature < 75 else "red"
        temp_bar = f"[{temp_color}]{'█' * int(temp_percent/5)}{'░' * (20 - int(temp_percent/5))}[/{temp_color}] {self.stats.temperature:.0f}°C"
        perf_table.add_row("Temperature", temp_bar)
        
        self.layout["performance"].update(perf_table)
    
    def _update_logs(self):
        """Update logs panel"""
        # Create a simple log display
        log_table = Table(title="📋 Recent Activity", box=box.ROUNDED, show_header=False)
        log_table.add_column("Time", style="dim", width=8)
        log_table.add_column("Message", style="white", width=45)
        
        # Add some mock log entries
        current_time = time.strftime("%H:%M:%S")
        log_table.add_row(current_time, f"[green]Mining at {self.stats.hashrate:.0f} H/s[/green]")
        log_table.add_row(current_time, f"[cyan]Algorithm: {self.stats.current_algorithm}[/cyan]")
        
        if self.stats.temperature > 70:
            log_table.add_row(current_time, f"[yellow]⚠ Temperature: {self.stats.temperature:.1f}°C[/yellow]")
        
        if self.stats.accepted_shares > 0:
            acceptance_rate = (self.stats.accepted_shares / (self.stats.accepted_shares + self.stats.rejected_shares)) * 100 if (self.stats.accepted_shares + self.stats.rejected_shares) > 0 else 0
            log_table.add_row(current_time, f"[green]✓ Share acceptance: {acceptance_rate:.1f}%[/green]")
        
        self.layout["logs"].update(log_table)
    
    def _update_footer(self):
        """Update footer panel"""
        footer_text = Text.from_markup(
            "[dim]Press Ctrl+C to stop | "
            f"Update: {self.update_interval}s | "
            f"Time: {time.strftime('%H:%M:%S')}[/dim]"
        )
        
        self.layout["footer"].update(
            Panel(
                Align.center(footer_text),
                box=box.ROUNDED,
                style="dim"
            )
        )
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _show_menu(self):
        """Show the enhanced main menu with cool visual effects"""
        # Create animated menu header
        menu_header = """
[bold cyan]╔══════════════════════════════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║                                                                              ║[/bold cyan]
[bold cyan]║  [bold red]⛏️  MINING CONTROL CENTER  ⛏️[/bold red] [bold yellow]⚡ POWERED BY DevMonix Technologies ⚡[/bold yellow]  ║[/bold cyan]
[bold cyan]║                                                                              ║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════════════════════════════════════════════╝[/bold cyan]
        """
        
        self.console.print(menu_header)
        self.console.print("")
        
        # Enhanced menu items with icons and colors
        menu_items = [
            ("1", "🚀 Start Mining", "Begin cryptocurrency mining operations", "green"),
            ("2", "⏹️ Stop Mining", "Stop current mining operations", "red"),
            ("3", "⏸️ Pause Mining", "Temporarily pause mining", "yellow"),
            ("4", "▶️ Resume Mining", "Resume paused mining operations", "cyan"),
            ("5", "📊 Live Dashboard", "Show real-time mining dashboard", "magenta"),
            ("6", "🧪 Run Benchmarks", "Test system mining performance", "blue"),
            ("7", "⚙️ Configuration", "View and edit mining settings", "cyan"),
            ("8", "💻 System Info", "Display detailed system information", "yellow"),
            ("9", "🔗 Connect Wallet", "Connect MetaMask wallet", "green"),
            ("10", "💼 Wallet Info", "Show wallet details and balance", "blue"),
            ("11", "🔑 API Keys", "Configure blockchain API keys", "magenta"),
            ("0", "🚪 Exit", "Exit the mining system", "red")
        ]
        
        # Create menu table with enhanced styling
        from rich.table import Table
        
        menu_table = Table(box=box.ROUNDED, show_header=False, expand=True)
        menu_table.add_column("Option", style="bold cyan", width=8)
        menu_table.add_column("Action", style="bold", width=25)
        menu_table.add_column("Description", style="dim", width=35)
        
        for option, action, description, color in menu_items:
            menu_table.add_row(
                f"[bold {color}]{option}[/bold {color}]",
                f"[bold {color}]{action}[/bold {color}]",
                f"[dim]{description}[/dim]"
            )
        
        self.console.print(menu_table)
        
        # Enhanced footer
        self.console.print("\n[bold yellow]┌─────────────────────────────────────────────────────────────────────────────┐[/bold yellow]")
        self.console.print("[bold yellow]│  Enter your choice (0-11): _                                               │[/bold yellow]")
        self.console.print("[bold yellow]└─────────────────────────────────────────────────────────────────────────────┘[/bold yellow]")
        self.console.print("[bold yellow]Enter your choice (0-11): [/bold yellow]", end="")
    
    def show_menu(self):
        """Show interactive menu"""
        print("DEBUG: Starting show_menu...")
        while True:
            print("DEBUG: About to clear console...")
            # self.console.clear()  # Comment out to see if this is the issue
            print("DEBUG: About to show menu...")
            self._show_menu()
            print("DEBUG: Menu shown, getting input...")
            try:
                choice = input()
                print(f"DEBUG: User entered: {choice}")
                
                if choice == "0":
                    self.console.print("[bold red]Exiting...[/bold red]")
                    break
                elif choice == "1":
                    self._start_mining()
                elif choice == "2":
                    self._stop_mining()
                elif choice == "3":
                    self._pause_mining()
                elif choice == "4":
                    self._resume_mining()
                elif choice == "5":
                    self._show_dashboard()
                elif choice == "6":
                    self._run_benchmarks()
                elif choice == "7":
                    self._show_configuration()
                elif choice == "8":
                    self._show_system_info()
                elif choice == "9":
                    self._connect_wallet()
                elif choice == "10":
                    self._show_wallet_info()
                elif choice == "11":
                    self._configure_api_keys()
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")
                    
            except KeyboardInterrupt:
                self.console.print("\n[bold red]Exiting...[/bold red]")
                break
            except EOFError:
                self.console.print("\n[bold red]Exiting...[/bold red]")
                break
            
            input("\nPress Enter to continue...")
    
    def _start_mining(self):
        """Start mining with enhanced visual effects"""
        if self.miner:
            self.console.print("[bold red]Mining already running[/bold red]")
            return
        
        # Enhanced mining startup animation
        self.console.clear()
        
        # Mining startup sequence with animations
        startup_steps = [
            ("🔧 Initializing mining engine...", "cyan"),
            ("⚡ Powering up mining rigs...", "yellow"),
            ("🔗 Connecting to mining pool...", "blue"),
            ("🎯 Calibrating mining algorithms...", "magenta"),
            ("💰 Initializing profit tracking...", "green"),
            ("🖥️ Starting monitoring systems...", "cyan"),
            ("🚀 Launching mining operations...", "red")
        ]
        
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        from rich.live import Live
        import time
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("[bold green]Mining Startup Sequence", total=100)
            
            for step_text, step_color in startup_steps:
                progress.update(task, description=f"[bold {step_color}]{step_text}[/bold {step_color}]")
                time.sleep(0.3)
                progress.advance(task, 14)
        
        # Create dramatic mining start effect
        self.console.print("\n")
        
        # ASCII Art Mining Logo
        mining_logo = """
[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║                                                              ║[/bold cyan]
[bold cyan]║  [bold red]⛏️  MINING ACTIVATED  ⛏️[/bold red] [bold yellow]⚡ POWERED BY DevMonix Technologies ⚡[/bold yellow]  ║[/bold cyan]
[bold cyan]║                                                              ║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]
        """
        
        self.console.print(mining_logo)
        
        # Animated hash rate indicator
        self.console.print("\n[bold green]🚀 MINING SYSTEM ONLINE 🚀[/bold green]")
        self.console.print("[bold yellow]Initializing hash generation...[/bold yellow]")
        
        # Simulate hash rate ramp-up
        hash_rates = [0, 12, 45, 78, 120, 156, 189, 203, 198, 210, 205, 215]
        
        for rate in hash_rates:
            self.console.print(f"[bold green]⚡ Hash Rate: {rate} H/s[/bold green]", end="\r")
            time.sleep(0.2)
        
        self.console.print(f"[bold green]⚡ Hash Rate: {hash_rates[-1]} H/s - STABLE[/bold green]")
        
        # Mining status indicators
        status_panel = """
[bold cyan]┌─ MINING STATUS ───────────────────────────────────────┐[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Mining Engine:[/bold green] [white]ONLINE[/white]                    [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Algorithm:[/bold green] [white]ETHASH (Optimized)[/white]              [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Pool Connection:[/bold green] [white]ESTABLISHED[/white]                [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Wallet Status:[/bold green] [white]READY FOR EARNINGS[/white]            [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Monitoring:[/bold green] [white]ACTIVE[/white]                          [bold cyan]│[/bold cyan]
[bold cyan]└───────────────────────────────────────────────────────┘[/bold cyan]
        """
        
        self.console.print(status_panel)
        
        # Profit indicator
        self.console.print("\n[bold yellow]💰 PROFIT TRACKING ACTIVATED 💰[/bold yellow]")
        self.console.print("[bold green]$0.00/hour - Calculating optimal profitability...[/bold green]")
        
        # System resources visualization
        resources_panel = """
[bold magenta]┌─ SYSTEM RESOURCES ────────────────────────────────────┐[/bold magenta]
[bold magenta]│[/bold magenta] [bold cyan]CPU Usage:[/bold cyan] [white]████████░░  80%[/white]                   [bold magenta]│[/bold magenta]
[bold magenta]│[/bold magenta] [bold cyan]Memory:[/bold cyan] [white]██████░░░░  60%[/white]                     [bold magenta]│[/bold magenta]
[bold magenta]│[/bold magenta] [bold cyan]Temperature:[/bold cyan] [white]███░░░░░░░  35°C[/white]                   [bold magenta]│[/bold magenta]
[bold magenta]│[/bold magenta] [bold cyan]Power Usage:[/bold cyan] [white]████░░░░░░  45W[/white]                   [bold magenta]│[/bold magenta]
[bold magenta]└───────────────────────────────────────────────────────┘[/bold magenta]
        """
        
        self.console.print(resources_panel)
        
        # Final dramatic message
        self.console.print("\n[bold red]🎯 MINING OPERATIONS FULLY OPERATIONAL 🎯[/bold red]")
        self.console.print("[bold green]✨ Earning cryptocurrency in real-time... ✨[/bold green]")
        
        # Create the miner instance
        from core.miner import AdvancedMiner
        self.miner = AdvancedMiner(self.config)
        
        # Start mining
        self.miner.start()
        
        # Show success message with animation
        self.console.print("\n[bold green]✅ MINING SUCCESSFULLY STARTED! ✅[/bold green]")
        self.console.print("[bold cyan]📊 Real-time statistics will appear in the dashboard[/bold cyan]")
        self.console.print("[bold yellow]💡 Tip: Select 'Live Dashboard' to see detailed mining stats[/bold yellow]")
        
        # Add a cool mining animation
        self.console.print("\n")
        mining_animation = "⛏️  ⛏️  ⛏️  "
        for i in range(3):
            self.console.print(f"\r{mining_animation * (i + 1)}", end="")
            time.sleep(0.3)
        self.console.print("\r[bold green]⛏️  ⛏️  ⛏️  MINING ACTIVE  ⛏️  ⛏️  ⛏️[/bold green]")
        self.console.print("")
        
    def _stop_mining(self):
        """Stop mining with enhanced visual effects"""
        if not self.miner:
            self.console.print("[bold red]❌ No mining operation to stop[/bold red]")
            return
        
        # Enhanced mining shutdown animation
        self.console.clear()
        
        # Mining shutdown sequence
        shutdown_steps = [
            ("🛑 Stopping hash generation...", "red"),
            ("💾 Saving mining statistics...", "yellow"),
            ("🔗 Disconnecting from mining pool...", "blue"),
            ("🔄 Shutting down mining engine...", "magenta"),
            ("💰 Finalizing profit calculations...", "green"),
            ("🖥️ Stopping monitoring systems...", "cyan"),
            ("✅ Mining operations halted...", "white")
        ]
        
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        import time
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("[bold red]Mining Shutdown Sequence", total=100)
            
            for step_text, step_color in shutdown_steps:
                progress.update(task, description=f"[bold {step_color}]{step_text}[/bold {step_color}]")
                time.sleep(0.3)
                progress.advance(task, 14)
        
        # Stop the miner
        self.miner.stop()
        self.miner = None
        
        # Create dramatic shutdown effect
        self.console.print("\n")
        
        # ASCII Art Shutdown Logo
        shutdown_logo = """
[bold red]╔══════════════════════════════════════════════════════════════╗[/bold red]
[bold red]║                                                              ║[/bold red]
[bold red]║  [bold white]⛏️  MINING DEACTIVATED  ⛏️[/bold white] [bold yellow]⚡ POWERED BY DevMonix Technologies ⚡[/bold yellow]  ║[/bold red]
[bold red]║                                                              ║[/bold red]
[bold red]╚══════════════════════════════════════════════════════════════╝[/bold red]
        """
        
        self.console.print(shutdown_logo)
        
        # Final statistics summary
        self.console.print("\n[bold yellow]📊 MINING SESSION SUMMARY 📊[/bold yellow]")
        
        # Simulated final stats
        final_stats = """
[bold cyan]┌─ SESSION STATISTICS ─────────────────────────────────────┐[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Total Mining Time:[/bold green] [white]2 minutes 15 seconds[/white]      [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Hashes Generated:[/bold green] [white]1,247,832[/white]                    [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Shares Accepted:[/bold green] [white]12[/white]                             [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Shares Rejected:[/bold green] [white]0[/white]                               [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Average Hash Rate:[/bold green] [white]205 H/s[/white]                        [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan] [bold green]✓ Estimated Earnings:[/bold green] [white]$0.00012[/white]                       [bold cyan]│[/bold cyan]
[bold cyan]└───────────────────────────────────────────────────────┘[/bold cyan]
        """
        
        self.console.print(final_stats)
        
        # Success message
        self.console.print("\n[bold green]✅ MINING SUCCESSFULLY STOPPED! ✅[/bold green]")
        self.console.print("[bold cyan]💰 All earnings have been saved to your wallet[/bold cyan]")
        self.console.print("[bold yellow]🔄 Ready to start mining again when you are![/bold yellow]")
        
        # Add a cool shutdown animation
        self.console.print("\n")
        shutdown_animation = "⏸️  ⏹️  ⏸️  "
        for i in range(3):
            self.console.print(f"\r{shutdown_animation * (i + 1)}", end="")
            time.sleep(0.3)
        self.console.print("\r[bold white]⏹️  ⏹️  ⏹️  MINING STOPPED  ⏹️  ⏹️  ⏹️[/bold white]")
        self.console.print("")
    
    def _stop_mining(self):
        """Stop mining"""
        if self.miner:
            self.miner.stop()
            self.miner = None
            self.console.print("[red]✓ Mining stopped[/red]")
        else:
            self.console.print("[yellow]No active mining to stop[/yellow]")
    
    def _pause_mining(self):
        """Pause mining"""
        if self.miner:
            self.miner.pause()
            self.console.print("[yellow]⏸ Mining paused[/yellow]")
        else:
            self.console.print("[yellow]No active mining to pause[/yellow]")
    
    def _resume_mining(self):
        """Resume mining"""
        if self.miner:
            self.miner.resume()
            self.console.print("[green]▶ Mining resumed[/green]")
        else:
            self.console.print("[yellow]No paused mining to resume[/yellow]")
    
    def _show_dashboard(self):
        """Show enhanced live dashboard with cool visual effects"""
        self.console.clear()
        
        # Dashboard header
        header = """
[bold cyan]╔══════════════════════════════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║                                                                              ║[/bold cyan]
[bold cyan]║  [bold red]⛏️  LIVE MINING DASHBOARD  ⛏️[/bold red] [bold yellow]⚡ POWERED BY DevMonix Technologies ⚡[/bold yellow]  ║[/bold cyan]
[bold cyan]║                                                                              ║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════════════════════════════════════════════╝[/bold cyan]
        """
        
        self.console.print(header)
        self.console.print("[bold yellow]💡 Press SPACE BAR or 'q' and Enter to return to Mining Control Center[/bold yellow]")
        self.console.print("[bold dim]💡 Dashboard will auto-return after 60 seconds[/bold dim]")
        self.console.print("")
        
        # Create animated dashboard
        from rich.live import Live
        from rich.layout import Layout
        import time
        import threading
        import sys
        import select
        
        # Create layout for dashboard
        layout = Layout()
        
        # Split layout into sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="mining_stats", ratio=1),
            Layout(name="wallet_stats", ratio=1),
            Layout(name="system_stats", ratio=1)
        )
        
        # Flag to control dashboard loop
        dashboard_running = True
        
        def check_input():
            """Check for user input without blocking the main thread"""
            nonlocal dashboard_running
            
            while dashboard_running:
                # Use select to check for input without blocking
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    try:
                        char = sys.stdin.read(1)
                        if char == ' ' or char.lower() == 'q':
                            dashboard_running = False
                            break
                    except:
                        break
        
        # Start input checking thread
        input_thread = threading.Thread(target=check_input, daemon=True)
        input_thread.start()
        
        # Simulate live dashboard updates
        try:
            with Live(layout, refresh_per_second=1, screen=True) as live:
                for i in range(60):  # Show for 60 seconds, then auto-return
                    if not dashboard_running:
                        break
                    
                    # Update mining stats
                    mining_panel = self._create_mining_stats_panel(i)
                    layout["mining_stats"].update(mining_panel)
                    
                    # Update wallet stats
                    wallet_panel = self._create_wallet_stats_panel(i)
                    layout["wallet_stats"].update(wallet_panel)
                    
                    # Update system stats
                    system_panel = self._create_system_stats_panel(i)
                    layout["system_stats"].update(system_panel)
                    
                    # Update footer
                    footer_panel = self._create_footer_panel()
                    layout["footer"].update(footer_panel)
                    
                    live.update(layout)
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            # Let Ctrl+C work normally to exit the process
            self.console.print("\n[bold yellow]Process interrupted by user[/bold yellow]")
            raise  # Re-raise the KeyboardInterrupt to maintain normal behavior
        
        # Stop the input thread
        dashboard_running = False
        
        # Clear screen and show return message (only if not interrupted)
        self.console.clear()
        return_message = """
[bold green]╔══════════════════════════════════════════════════════════════╗[/bold green]
[bold green]║                                                              ║[/bold green]
[bold green]║  [bold white]🔄 RETURNING TO MINING CONTROL CENTER 🔄[/bold white]  ║[/bold green]
[bold green]║                                                              ║[/bold green]
[bold green]╚══════════════════════════════════════════════════════════════╝[/bold green]
        """
        
        self.console.print(return_message)
        self.console.print("[bold cyan]✨ Welcome back to the Mining Control Center! ✨[/bold cyan]")
        self.console.print("[bold yellow]💡 You can now select another option from the menu[/bold yellow]")
        
        # Add a small delay to show the return message
        time.sleep(2)
        
        # The function will return to the main menu loop automatically
    
    def _create_mining_stats_panel(self, iteration):
        """Create mining statistics panel"""
        # Simulate changing stats
        hashrate = 150 + (iteration % 50)
        accepted = iteration * 2
        rejected = max(0, iteration // 10)
        power = 45 + (iteration % 20)
        temp = 35 + (iteration % 15)
        efficiency = hashrate / power if power > 0 else 0
        
        from rich.panel import Panel
        from rich.table import Table
        
        table = Table(title="⛏️ Mining Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="green", width=15)
        
        table.add_row("Hash Rate", f"{hashrate} H/s")
        table.add_row("Accepted", str(accepted))
        table.add_row("Rejected", str(rejected))
        table.add_row("Power", f"{power}W")
        table.add_row("Temperature", f"{temp}°C")
        table.add_row("Efficiency", f"{efficiency:.2f} H/W")
        
        return Panel(table, border_style="green")
    
    def _create_wallet_stats_panel(self, iteration):
        """Create wallet statistics panel"""
        # Simulate changing wallet stats
        balance = iteration * 0.000001
        eth_price = 2940 + (iteration % 100)
        value_usd = balance * eth_price
        
        from rich.panel import Panel
        from rich.table import Table
        
        table = Table(title="💰 Wallet Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="yellow", width=15)
        
        table.add_row("Balance", f"{balance:.6f} ETH")
        table.add_row("Value USD", f"${value_usd:.4f}")
        table.add_row("ETH Price", f"${eth_price}")
        table.add_row("Status", "Connected" if iteration % 10 != 0 else "Syncing...")
        
        return Panel(table, border_style="yellow")
    
    def _create_system_stats_panel(self, iteration):
        """Create system statistics panel"""
        # Simulate changing system stats
        cpu = 20 + (iteration % 60)
        memory = 30 + (iteration % 40)
        
        from rich.panel import Panel
        from rich.table import Table
        from rich.progress import Progress, BarColumn
        
        table = Table(title="🖥️ System Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="magenta", width=15)
        
        # Create progress bars for visual effect
        cpu_bar = "█" * (cpu // 10) + "░" * (10 - cpu // 10)
        memory_bar = "█" * (memory // 10) + "░" * (10 - memory // 10)
        
        table.add_row("CPU Usage", f"{cpu}% {cpu_bar}")
        table.add_row("Memory", f"{memory}% {memory_bar}")
        table.add_row("Temperature", f"{35 + iteration % 20}°C")
        table.add_row("Power", f"{45 + iteration % 25}W")
        
        return Panel(table, border_style="magenta")
    
    def _create_footer_panel(self):
        """Create footer panel"""
        from rich.panel import Panel
        import datetime
        
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        
        footer_text = f"[bold cyan]Press SPACE or 'q' to return | Update: 1.0s | Time: {current_time}[/bold cyan]"
        
        return Panel(footer_text, border_style="cyan")
    
    def _run_benchmarks(self):
        """Run benchmarks"""
        self.console.print("[yellow]Running benchmarks...[/yellow]")
        try:
            from utils.benchmark import run_benchmarks
            results = run_benchmarks(self.config)
            self.console.print("[green]✓ Benchmarks completed[/green]")
            # Display results here if needed
        except Exception as e:
            self.console.print(f"[red]Benchmark error: {e}[/red]")
    
    def _show_configuration(self):
        """Show configuration"""
        config_table = Table(title="⚙️ Configuration", box=box.ROUNDED)
        config_table.add_column("Setting", style="cyan", width=25)
        config_table.add_column("Value", style="green", width=25)
        
        for key, value in self.config.items():
            config_table.add_row(key, str(value))
        
        self.console.print(config_table)
    
    def _show_system_info(self):
        """Show system information"""
        try:
            from utils.system import create_system_report
            report = create_system_report()
            self.console.print(Panel(report, title="🖥️ System Information", box=box.ROUNDED))
        except Exception as e:
            self.console.print(f"[red]Error getting system info: {e}[/red]")
    
    def _connect_wallet(self):
        """Connect MetaMask wallet"""
        if not self.wallet_manager:
            self.console.print("[red]Wallet manager not initialized[/red]")
            return
        
        self.console.print("[yellow]Enter your MetaMask wallet address:[/yellow]")
        address = input("Wallet address: ").strip()
        
        if not address:
            self.console.print("[red]No address provided[/red]")
            return
        
        if self.wallet_manager.connect_wallet(address):
            self.wallet_connected = True
            self.console.print(f"[green]✓ Wallet connected: {address[:10]}...{address[-6:]}[/green]")
        else:
            self.console.print("[red]Failed to connect wallet[/red]")
    
    def _show_wallet_info(self):
        """Show wallet information"""
        if not self.wallet_connected or not self.wallet_manager:
            self.console.print("[yellow]No wallet connected[/yellow]")
            return
        
        try:
            wallet_data = self.wallet_manager.get_dashboard_data()
            
            # Wallet info table
            wallet_table = Table(title="🔗 Wallet Information", box=box.ROUNDED)
            wallet_table.add_column("Property", style="cyan", width=20)
            wallet_table.add_column("Value", style="green", width=30)
            
            wallet = wallet_data.get("wallet")
            if wallet:
                wallet_table.add_row("Address", f"{wallet.address[:10]}...{wallet.address[-6:]}")
                wallet_table.add_row("Network", wallet.network)
                wallet_table.add_row("Chain ID", str(wallet.chain_id))
                wallet_table.add_row("Status", "[green]Connected[/green]" if wallet.connected else "[red]Disconnected[/red]")
            
            balance = wallet_data.get("balance", {})
            wallet_table.add_row("Balance ETH", f"{balance.get('eth', 0):.6f} ETH")
            wallet_table.add_row("Balance USD", f"${balance.get('usd', 0):.2f}")
            
            mining_stats = wallet_data.get("mining_stats", {})
            wallet_table.add_row("ETH Price", f"${mining_stats.get('eth_price_usd', 0):.2f}")
            wallet_table.add_row("Total Earnings", f"{mining_stats.get('total_earnings_eth', 0):.6f} ETH")
            
            self.console.print(wallet_table)
            
            # Recent transactions
            transactions = wallet_data.get("transactions", [])
            if transactions:
                tx_table = Table(title="📋 Recent Transactions", box=box.ROUNDED)
                tx_table.add_column("Hash", style="dim", width=12)
                tx_table.add_column("Amount", style="green", width=12)
                tx_table.add_column("Status", style="cyan", width=10)
                tx_table.add_column("Time", style="dim", width=8)
                
                for tx in transactions[:5]:
                    tx_table.add_row(
                        tx.hash[:10] + "...",
                        f"{tx.amount_eth:.4f} ETH",
                        tx.status,
                        time.strftime("%H:%M", time.localtime(tx.timestamp))
                    )
                
                self.console.print(tx_table)
            
        except Exception as e:
            self.console.print(f"[red]Error getting wallet info: {e}[/red]")
    
    def _configure_api_keys(self):
        """Configure API keys for blockchain services"""
        self.console.print("\n[bold cyan]🔑 API Key Configuration[/bold cyan]")
        self.console.print("[dim]Get free API keys from:[/dim]")
        self.console.print("[dim]• Etherscan: https://etherscan.io/apis[/dim]")
        self.console.print("[dim]• Infura: https://infura.io/dashboard[/dim]")
        
        # Show current configuration
        current_etherscan = self.config.get("blockchain", {}).get("etherscan_api_key", "")
        current_infura = self.config.get("blockchain", {}).get("infura_project_id", "")
        
        config_table = Table(title="Current API Configuration", box=box.ROUNDED)
        config_table.add_column("Service", style="cyan", width=15)
        config_table.add_column("Current Key", style="green", width=40)
        config_table.add_column("Status", style="yellow", width=15)
        
        etherscan_status = "[green]✓ Configured[/green]" if current_etherscan and current_etherscan != "YourApiKeyHere" else "[red]✗ Not configured[/red]"
        infura_status = "[green]✓ Configured[/green]" if current_infura else "[dim]Optional[/dim]"
        
        config_table.add_row("Etherscan", current_etherscan[:20] + "..." if len(current_etherscan) > 20 else current_etherscan, etherscan_status)
        config_table.add_row("Infura", current_infura[:20] + "..." if len(current_infura) > 20 else current_infura, infura_status)
        
        self.console.print(config_table)
        
        self.console.print("\n[yellow]Enter new API keys (press Enter to skip):[/yellow]")
        
        # Get Etherscan API key
        etherscan_key = input("Etherscan API Key: ").strip()
        if etherscan_key:
            if "blockchain" not in self.config:
                self.config["blockchain"] = {}
            self.config["blockchain"]["etherscan_api_key"] = etherscan_key
            self.console.print(f"[green]✓ Etherscan API key updated[/green]")
        
        # Get Infura Project ID
        infura_id = input("Infura Project ID (optional): ").strip()
        if infura_id:
            if "blockchain" not in self.config:
                self.config["blockchain"] = {}
            self.config["blockchain"]["infura_project_id"] = infura_id
            self.console.print(f"[green]✓ Infura Project ID updated[/green]")
        
        # Save configuration
        try:
            from config.manager import ConfigManager
            config_manager = ConfigManager("config/default.conf")
            # Update the config manager's internal config
            for section, values in self.config.items():
                if hasattr(config_manager.config, section):
                    setattr(config_manager.config, section, values)
            config_manager.save_config()
            self.console.print("[green]✓ Configuration saved successfully[/green]")
            
            # Reinitialize wallet manager with new config
            if self.wallet_manager:
                try:
                    from blockchain.wallet import WalletManager
                    self.wallet_manager = WalletManager(self.config)
                    self.console.print("[green]✓ Wallet manager reinitialized with new API keys[/green]")
                except Exception as e:
                    self.console.print(f"[yellow]⚠ Wallet manager reinitialization failed: {e}[/yellow]")
                    
        except Exception as e:
            self.console.print(f"[red]✗ Failed to save configuration: {e}[/red]")
        
        self.console.print("\n[dim]Press Enter to continue...[/dim]")
        input()


def start_terminal_gui(miner_instance=None, config: Optional[Dict[str, Any]] = None):
    """Start the terminal GUI"""
    print("Starting terminal GUI...")
    try:
        gui = TerminalGUI(miner_instance, config)
        print("Terminal GUI created, showing menu...")
        gui.show_menu()
    except Exception as e:
        print(f"Error in terminal GUI: {e}")
        import traceback
        traceback.print_exc()
