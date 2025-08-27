import os
import sys
import json
import time
import signal
import random
import subprocess
import shutil
import platform
from pathlib import Path
from datetime import datetime
import threading
import atexit
import webbrowser

class ExhibitionController:
    def __init__(self, config_path="exhibition_config.json", prompts_path="prompts.csv"):
        """Initialize the exhibition controller."""
        self.processes = []
        self.threads = []
        self.running = True
        self.system = platform.system()  # 'Windows', 'Darwin' (macOS), 'Linux'

        print(f"Detected OS: {self.system}")

        self.load_config(config_path)
        self.load_prompts(prompts_path)
        self.auto_detect_paths()
        self.setup_directories()
        self.setup_cleanup()
    def load_prompts(self, prompts_path):
        """Load prompts from a CSV file."""
        import csv
        self.prompts = {'Descriptions': [], 'Materials': [], 'Objects': []}
        try:
            with open(prompts_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, None)
                if not headers:
                    print("Error: prompts.csv is empty or missing headers.")
                    return
                # Find the indices for Description, Material, Object (case-insensitive, ignore extra columns)
                desc_idx = mat_idx = obj_idx = None
                for i, h in enumerate(headers):
                    h_clean = h.strip().lower()
                    if h_clean.startswith('description') and desc_idx is None:
                        desc_idx = i
                    elif h_clean.startswith('material') and mat_idx is None:
                        mat_idx = i
                    elif h_clean.startswith('object') and obj_idx is None:
                        obj_idx = i
                if desc_idx is None or mat_idx is None or obj_idx is None:
                    print("Error: Could not find required columns in prompts.csv. Expected headers: Description, Material, Object.")
                    return
                for row in reader:
                    # Skip rows with missing or empty values in any of the three columns
                    if len(row) > max(desc_idx, mat_idx, obj_idx):
                        desc = row[desc_idx].strip()
                        mat = row[mat_idx].strip()
                        obj = row[obj_idx].strip()
                        if desc and mat and obj:
                            self.prompts['Descriptions'].append(desc)
                            self.prompts['Materials'].append(mat)
                            self.prompts['Objects'].append(obj)
            if not all(self.prompts.values()):
                print("Warning: Some prompt categories are empty in prompts.csv.")
        except Exception as e:
            print(f"Error loading prompts from {prompts_path}: {e}")
        
    def load_config(self, config_path):
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
    
    def auto_detect_paths(self):
        """Auto-detect and validate paths based on OS."""
        print("\n→ Auto-detecting paths...")
        
        # Auto-detect Point-E directory if not specified
        if not self.config.get('pointe_dir') or self.config['pointe_dir'] == "auto":
            pointe_dir = self.find_pointe_directory()
            if pointe_dir:
                self.config['pointe_dir'] = str(pointe_dir)
                print(f"  ✓ Found Point-E: {pointe_dir}")
            else:
                print("  ✗ Could not find Point-E directory")
                self.request_path('pointe_dir', "Point-E repository")
        
        # Auto-detect viewer directory
        if not self.config.get('viewer_dir') or self.config['viewer_dir'] == "auto":
            viewer_dir = self.find_viewer_directory()
            if viewer_dir:
                self.config['viewer_dir'] = str(viewer_dir)
                self.config['viewer_models_dir'] = str(viewer_dir / 'models')
                print(f"  ✓ Found viewer: {viewer_dir}")
            else:
                print("  ✗ Could not find local3dviewer directory")
                self.request_path('viewer_dir', "local3dviewer")
        
        # Auto-detect conda/venv environment
        if not self.config.get('pointe_env') or self.config['pointe_env'] == "auto":
            env_path = self.find_python_env()
            if env_path:
                self.config['pointe_env'] = str(env_path)
                self.config['env_type'] = self.detect_env_type(env_path)
                print(f"  ✓ Found {self.config['env_type']}: {env_path}")
            else:
                print("  ! No environment specified, using system Python")
                self.config['pointe_env'] = None
                self.config['env_type'] = 'system'
        
        # Set temp directory based on OS
        if not self.config.get('temp_dir') or self.config['temp_dir'] == "auto":
            if self.system == "Windows":
                self.config['temp_dir'] = str(Path.home() / 'AppData' / 'Local' / 'Temp' / 'exhibition')
            else:  # macOS and Linux
                self.config['temp_dir'] = '/tmp/exhibition'
            print(f"  ✓ Temp dir: {self.config['temp_dir']}")
        
        # Save auto-detected config
        self.save_config()
    
    def find_pointe_directory(self):
        """Search for Point-E directory in common locations."""
        possible_locations = [
            Path.cwd(),  # Current directory
            Path.cwd().parent,  # Parent directory
            Path.home() / 'Desktop',
            Path.home() / 'Documents',
            Path.home() / 'Downloads',
            Path.home() / 'point-e-finetuning',
            Path.home() / 'point-e',
        ]
        
        for location in possible_locations:
            if location.exists():
                # Look for Point-E specific files
                for item in location.rglob('finetune'):
                    if item.is_dir() and (item.parent / 'config').exists():
                        return item.parent
        return None
    
    def find_viewer_directory(self):
        """Search for local3dviewer directory."""
        possible_locations = [
            Path.cwd() / 'local3dviewer',
            Path.cwd().parent / 'local3dviewer',
            Path.home() / 'Desktop' / 'local3dviewer',
            Path.home() / 'Documents' / 'local3dviewer',
        ]
        
        for location in possible_locations:
            if location.exists() and (location / 'models').exists():
                return location
        return None
    
    def find_python_env(self):
        """Find conda or venv environment."""
        # Check if we're already in an environment
        conda_prefix = os.environ.get('CONDA_PREFIX')
        if os.environ.get('CONDA_DEFAULT_ENV') and conda_prefix:
            return Path(conda_prefix)
        venv_path = os.environ.get('VIRTUAL_ENV')
        if venv_path:
            return Path(venv_path)
        
        # Search for environments
        possible_envs = []
        
        # Check for conda environments
        if self.system == "Windows":
            conda_paths = [
                Path.home() / 'miniconda3' / 'envs',
                Path.home() / 'anaconda3' / 'envs',
                Path('C:\\ProgramData\\miniconda3\\envs'),
                Path('C:\\ProgramData\\anaconda3\\envs'),
            ]
        else:  # macOS and Linux
            conda_paths = [
                Path.home() / 'miniconda3' / 'envs',
                Path.home() / 'anaconda3' / 'envs',
                Path('/opt/conda/envs'),
                Path('/usr/local/conda/envs'),
            ]
        
        for conda_dir in conda_paths:
            if conda_dir.exists():
                for env in conda_dir.iterdir():
                    if env.is_dir() and 'point' in env.name.lower():
                        return env
        
        # Check for venv in Point-E directory
        if self.config.get('pointe_dir'):
            pointe_path = Path(self.config['pointe_dir'])
            venv_path = pointe_path / 'venv'
            if venv_path.exists():
                return venv_path
            env_path = pointe_path / 'env'
            if env_path.exists():
                return env_path
        
        return None
    
    def detect_env_type(self, env_path):
        """Detect if environment is conda or venv."""
        env_path = Path(env_path)
        if (env_path / 'conda-meta').exists():
            return 'conda'
        elif (env_path / 'pyvenv.cfg').exists():
            return 'venv'
        else:
            return 'unknown'
    
    def request_path(self, key, description):
        """Request user to input a path."""
        print(f"\nPlease enter the path to {description}:")
        path = input("> ").strip()
        self.config[key] = path
    
    def save_config(self):
        """Save the updated configuration."""
        with open('exhibition_config_detected.json', 'w') as f:
            json.dump(self.config, f, indent=4)
        print("\n✓ Configuration saved to exhibition_config_detected.json")
            
    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        Path(self.config['temp_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.config['viewer_models_dir']).mkdir(parents=True, exist_ok=True)
    
    def setup_cleanup(self):
        """Setup cleanup handlers for graceful shutdown."""
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n\nShutting down exhibition system...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def get_python_cmd(self):
        """Get the correct Python command for the environment."""
        if self.config.get('pointe_env') and self.config['env_type'] != 'system':
            env_path = Path(self.config['pointe_env'])
            
            if self.system == "Windows":
                if self.config['env_type'] == 'conda':
                    return str(env_path / 'python.exe')
                else:  # venv
                    return str(env_path / 'Scripts' / 'python.exe')
            else:  # macOS and Linux
                return str(env_path / 'bin' / 'python')
        return sys.executable  # Use current Python
    
    def run_command(self, cmd, cwd=None):
        """Run a command with proper environment activation."""
        if self.config.get('pointe_env') and self.config['env_type'] != 'system':
            env_path = Path(self.config['pointe_env'])
            
            if self.config['env_type'] == 'conda':
                # Use conda run for conda environments
                if self.system == "Windows":
                    # Find conda executable
                    conda_base = env_path.parent.parent
                    conda_exe = conda_base / 'Scripts' / 'conda.exe'
                    if not conda_exe.exists():
                        conda_exe = conda_base / 'condabin' / 'conda.bat'
                    
                    full_cmd = f"{conda_exe} run -n {env_path.name} {cmd}"
                else:
                    # macOS/Linux
                    full_cmd = f"conda run -n {env_path.name} {cmd}"
                
                return subprocess.run(full_cmd, shell=True, capture_output=True, text=True, cwd=cwd)
            
            else:  # venv or direct python call
                # Replace 'python' with the full path to the environment's python
                python_cmd = self.get_python_cmd()
                if cmd.startswith('python'):
                    cmd = cmd.replace('python', python_cmd, 1)
                
                return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        else:
            # No environment, use system Python
            return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    
    def generate_random_prompt(self):
        """Generate a random prompt from word arrays loaded from csv."""
        import random
        if not (self.prompts['Descriptions'] and self.prompts['Materials'] and self.prompts['Objects']):
            print("Error: Prompts not loaded or empty. Check prompts.csv.")
            return "default object"
        description = random.choice(self.prompts['Descriptions'])
        material = random.choice(self.prompts['Materials'])
        object_type = random.choice(self.prompts['Objects'])
        return f"{description} {material} {object_type}".strip()
    
    def generate_object(self):
        """Complete pipeline to generate one object."""
        prompt = self.generate_random_prompt()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        print(f"\n{'='*60}")
        print(f"[{timestamp}] Generating: '{prompt}'")
        print('='*60)

        # Step 1: Generate point cloud
        temp_pc = Path(self.config['temp_dir']) / f"temp_{timestamp}.npz"

        print("→ Generating point cloud...")
        # Always use the correct Python executable from get_python_cmd()
        python_cmd = self.get_python_cmd()
        cmd = f'{python_cmd} -m finetune.inference --config config/config.yaml --prompt "{prompt}" --out {temp_pc}'
        
        # Set up environment to ensure Point-E subprocess can find python
        env = os.environ.copy()
        if self.config.get('pointe_env') and self.config['env_type'] == 'venv':
            # Add venv bin directory to PATH so 'python' resolves correctly
            venv_bin = Path(self.config['pointe_env']) / 'bin'
            env['PATH'] = f"{venv_bin}:{env.get('PATH', '')}"
        
        # Stream output for progress visibility
        process = subprocess.Popen(cmd, shell=True, cwd=self.config['pointe_dir'], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            if process.stdout is not None:
                for line in process.stdout:
                    print(line, end='')
            process.wait()
        except Exception as e:
            print(f"Error during point cloud generation: {e}")
            process.terminate()
            return False
        if process.returncode != 0:
            print(f"✗ Failed to generate point cloud (exit code {process.returncode})")
            return False
        print("✓ Point cloud generated")
        
        # Step 2: Convert to mesh
        print("→ Converting to mesh...")
        mesh_cmd = f"python scripts/pointclouds_to_mesh.py --input {temp_pc}"
        result = self.run_command(mesh_cmd, cwd=self.config['pointe_dir'])
        
        if result.returncode != 0:
            print(f"✗ Failed to convert to mesh: {result.stderr}")
            return False
        
        mesh_ply = temp_pc.with_suffix('.ply')
        print("✓ Mesh created")
        
        # Step 3: Convert PLY to OBJ
        print("→ Converting to OBJ...")
        obj_path = self.convert_ply_to_obj(mesh_ply)
        
        if not obj_path:
            return False
        
        # Step 4: Copy to viewer directory
        target_path = Path(self.config['viewer_models_dir']) / "model1.obj"
        shutil.copy2(obj_path, target_path)
        
        # Create simple MTL file
        self.create_mtl(target_path.with_suffix('.mtl'))
        
        # Save prompt for reference
        prompt_file = Path(self.config['viewer_models_dir']) / "last_prompt.txt"
        with open(prompt_file, 'w') as f:
            f.write(f"{datetime.now().isoformat()}\n{prompt}")
        
        print(f"✓ Object saved to viewer: {target_path}")
        
        # Cleanup temp files
        self.cleanup_temp()
        
        return True
    
    def convert_ply_to_obj(self, ply_path):
        """Convert PLY to OBJ using Python in environment."""
        obj_path = ply_path.with_suffix('.obj')
        
        # Create a temporary conversion script
        convert_script = Path(self.config['temp_dir']) / "convert.py"
        script_content = f"""
import sys
try:
    import trimesh
    mesh = trimesh.load(r"{ply_path}")
    mesh.export(r"{obj_path}")
    print("Conversion successful")
except Exception as e:
    print(f"Conversion failed: {{e}}")
    sys.exit(1)
"""
        with open(convert_script, 'w') as f:
            f.write(script_content)
        
        python_cmd = self.get_python_cmd()
        result = self.run_command(f"{python_cmd} {convert_script}", cwd=self.config['temp_dir'])
        
        if result.returncode == 0:
            print("✓ Converted to OBJ")
            return obj_path
        else:
            print(f"✗ Failed to convert to OBJ: {result.stdout}")
            return None
    
    def create_mtl(self, mtl_path):
        """Create a default MTL material file."""
        mtl_content = """# Default material
newmtl default
Ka 0.2 0.2 0.2
Kd 0.8 0.8 0.8
Ks 0.0 0.0 0.0
Ns 10.0
d 1.0
illum 1
"""
        with open(mtl_path, 'w') as f:
            f.write(mtl_content)
    
    def cleanup_temp(self):
        """Clean up temporary files."""
        temp_dir = Path(self.config['temp_dir'])
        if temp_dir.exists():
            for file in temp_dir.glob("temp_*"):
                try:
                    file.unlink()
                except:
                    pass
    
    def generation_loop(self):
        """Background thread for continuous generation."""
        interval = self.config.get('generation_interval', 600)
        
        # Generate first object immediately
        self.generate_object()
        
        while self.running:
            time.sleep(interval)
            if self.running:
                self.generate_object()
    
    def start_viewer_server(self):
        """Start the local 3D viewer HTTP server."""
        print("\n→ Starting 3D viewer server...")
        viewer_dir = self.config['viewer_dir']
        
        # Start HTTP server in viewer directory
        cmd = [sys.executable, "-m", "http.server", "8000"]
        
        if self.system == "Windows":
            # Windows: Hide console window for server
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(cmd, cwd=viewer_dir, startupinfo=startupinfo)
        else:
            # macOS/Linux
            process = subprocess.Popen(cmd, cwd=viewer_dir)
        
        self.processes.append(process)
        print("✓ Viewer server started on http://localhost:8000")
        return process
    
    def open_browser(self):
        """Open browser in incognito/private mode."""
        print("→ Opening browser...")
        time.sleep(3)  # Give server time to start
        
        url = "http://localhost:8000"
        
        # Try to use webbrowser module first (cross-platform)
        try:
            if self.system == "Darwin":  # macOS
                # Use AppleScript for private window
                script = f'''
                tell application "Google Chrome"
                    activate
                    make new window with properties {{mode:"incognito"}}
                    set URL of active tab of front window to "{url}"
                end tell
                '''
                subprocess.run(['osascript', '-e', script])
            elif self.system == "Windows":
                # Windows
                browser = self.config.get('browser', 'chrome').lower()
                if browser == 'chrome':
                    subprocess.Popen(['start', 'chrome', '--incognito', '--start-fullscreen', url], shell=True)
                elif browser == 'edge':
                    subprocess.Popen(['start', 'msedge', '--inprivate', '--start-fullscreen', url], shell=True)
                else:
                    webbrowser.open(url)
            else:
                # Linux
                browsers = ['google-chrome', 'chromium', 'firefox']
                for browser in browsers:
                    try:
                        if 'chrome' in browser or 'chromium' in browser:
                            subprocess.Popen([browser, '--incognito', '--start-fullscreen', url])
                        else:
                            subprocess.Popen([browser, '-private-window', url])
                        break
                    except:
                        continue
            
            print("✓ Browser opened")
        except Exception as e:
            print(f"Could not open browser automatically: {e}")
            print(f"Please open {url} manually in private/incognito mode")
    
    def cleanup(self):
        """Clean up all processes on exit."""
        print("\nCleaning up...")
        self.running = False
        
        # Terminate all subprocess
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # Clean temp files
        self.cleanup_temp()
        
        # Kill browser if needed
        if self.config.get('close_browser_on_exit', False):
            if self.system == "Darwin":
                subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to close windows'])
            elif self.system == "Windows":
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
        
        print("✓ Cleanup complete")
    
    def check_dependencies(self):
        """Check if required packages are installed."""
        print("\n→ Checking dependencies...")
        
        python_cmd = self.get_python_cmd()
        
        # Check trimesh
        check_cmd = f"{python_cmd} -c \"import trimesh; print('trimesh OK')\""
        result = self.run_command(check_cmd)
        
        if result.returncode != 0:
            print("  ✗ trimesh not installed")
            print("  → Installing trimesh...")
            install_cmd = f"{python_cmd} -m pip install trimesh"
            result = self.run_command(install_cmd)
            if result.returncode == 0:
                print("  ✓ trimesh installed")
            else:
                print("  ✗ Failed to install trimesh")
                print("    Please install manually: pip install trimesh")
        else:
            print("  ✓ trimesh is installed")
    
    def run(self):
        """Main exhibition runtime."""
        print("\n" + "="*60)
        print("         EXHIBITION CONTROLLER STARTING")
        print("="*60)
        
        # Check dependencies
        self.check_dependencies()
        
        # Start viewer server
        self.start_viewer_server()
        
        # Start generation thread
        gen_thread = threading.Thread(target=self.generation_loop, daemon=True)
        gen_thread.start()
        self.threads.append(gen_thread)
        
        # Open browser
        time.sleep(2)
        self.open_browser()
        
        print("\n" + "="*60)
        print("     EXHIBITION RUNNING - Press Ctrl+C to stop")
        print("="*60)
        print(f"\nGenerating new objects every {self.config.get('generation_interval', 600)} seconds")
        print("Viewer URL: http://localhost:8000")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

if __name__ == "__main__":
    controller = ExhibitionController()
    controller.run()
