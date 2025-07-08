#!/usr/bin/env python3
"""
File Optimizer Background Agent
Monitors file creation, detects redundancies, and optimizes project structure
"""

import os
import sys
import time
import hashlib
import difflib
import json
import argparse
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from collections import defaultdict
import re

class FileOptimizerAgent(FileSystemEventHandler):
    def __init__(self, watch_dir=".", config_file="optimizer-config.json"):
        self.watch_dir = Path(watch_dir)
        self.config_file = config_file
        self.file_hashes = {}
        self.similar_files = defaultdict(list)
        self.commands_found = defaultdict(list)
        self.optimization_log = []
        
        # Load configuration
        self.config = self.load_config()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('file-optimizer.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initial scan
        self.scan_existing_files()
    
    def load_config(self):
        """Load configuration settings"""
        default_config = {
            "similarity_threshold": 0.7,
            "auto_merge": False,
            "backup_before_merge": True,
            "ignore_patterns": [".git", "__pycache__", "*.pyc", "node_modules"],
            "file_types_to_monitor": [".py", ".sh", ".js", ".ts", ".yml", ".yaml", ".json", ".md"],
            "command_patterns": [
                r"docker\s+compose\s+\w+",
                r"docker\s+\w+",
                r"git\s+\w+",
                r"npm\s+\w+",
                r"pip\s+install",
                r"chmod\s+\+x"
            ]
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}. Using defaults.")
        
        return default_config
    
    def save_config(self):
        """Save current configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_file_hash(self, filepath):
        """Calculate file hash for duplicate detection"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None
    
    def get_file_content(self, filepath):
        """Get file content as string"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    def calculate_similarity(self, content1, content2):
        """Calculate similarity between two text contents"""
        matcher = difflib.SequenceMatcher(None, content1, content2)
        return matcher.ratio()
    
    def extract_commands(self, content):
        """Extract shell commands from file content"""
        commands = []
        for pattern in self.config["command_patterns"]:
            matches = re.findall(pattern, content, re.IGNORECASE)
            commands.extend(matches)
        return commands
    
    def should_ignore_file(self, filepath):
        """Check if file should be ignored based on patterns"""
        path_str = str(filepath)
        for pattern in self.config["ignore_patterns"]:
            if pattern in path_str or filepath.name.endswith(pattern.replace("*", "")):
                return True
        return False
    
    def scan_existing_files(self):
        """Initial scan of existing files"""
        self.logger.info("Starting initial file scan...")
        
        for root, dirs, files in os.walk(self.watch_dir):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self.config["ignore_patterns"])]
            
            for file in files:
                filepath = Path(root) / file
                if not self.should_ignore_file(filepath):
                    self.analyze_file(filepath)
        
        self.detect_redundancies()
        self.logger.info(f"Initial scan complete. Found {len(self.file_hashes)} files to monitor.")
    
    def analyze_file(self, filepath):
        """Analyze a single file for content and commands"""
        if not filepath.suffix in self.config["file_types_to_monitor"]:
            return
        
        # Calculate hash for duplicate detection
        file_hash = self.get_file_hash(filepath)
        if file_hash:
            self.file_hashes[str(filepath)] = file_hash
        
        # Extract content and commands
        content = self.get_file_content(filepath)
        if content:
            commands = self.extract_commands(content)
            if commands:
                self.commands_found[str(filepath)] = commands
    
    def detect_redundancies(self):
        """Detect redundant files and commands"""
        # Find duplicate files
        hash_to_files = defaultdict(list)
        for filepath, file_hash in self.file_hashes.items():
            hash_to_files[file_hash].append(filepath)
        
        duplicates = {k: v for k, v in hash_to_files.items() if len(v) > 1}
        if duplicates:
            self.logger.warning(f"Found {len(duplicates)} sets of duplicate files:")
            for file_hash, files in duplicates.items():
                self.logger.warning(f"  Duplicates: {files}")
        
        # Find similar files
        self.find_similar_files()
        
        # Find redundant commands
        self.find_redundant_commands()
    
    def find_similar_files(self):
        """Find files with similar content"""
        files_with_content = {}
        for filepath in self.file_hashes.keys():
            content = self.get_file_content(filepath)
            if content and len(content.strip()) > 50:  # Ignore very short files
                files_with_content[filepath] = content
        
        file_paths = list(files_with_content.keys())
        similar_pairs = []
        
        for i, path1 in enumerate(file_paths):
            for path2 in file_paths[i+1:]:
                similarity = self.calculate_similarity(
                    files_with_content[path1], 
                    files_with_content[path2]
                )
                if similarity >= self.config["similarity_threshold"]:
                    similar_pairs.append((path1, path2, similarity))
        
        if similar_pairs:
            self.logger.warning(f"Found {len(similar_pairs)} pairs of similar files:")
            for path1, path2, similarity in similar_pairs:
                self.logger.warning(f"  {similarity:.2%} similar: {path1} <-> {path2}")
    
    def find_redundant_commands(self):
        """Find redundant commands across files"""
        command_to_files = defaultdict(list)
        for filepath, commands in self.commands_found.items():
            for command in commands:
                command_to_files[command].append(filepath)
        
        redundant_commands = {k: v for k, v in command_to_files.items() if len(v) > 1}
        if redundant_commands:
            self.logger.info(f"Found {len(redundant_commands)} redundant commands:")
            for command, files in redundant_commands.items():
                self.logger.info(f"  '{command}' in: {files}")
    
    def generate_optimization_suggestions(self):
        """Generate suggestions for optimization"""
        suggestions = []
        
        # Suggest merging similar files
        # Suggest consolidating commands
        # Suggest creating utility scripts
        
        return suggestions
    
    def create_consolidated_script(self, script_name="consolidated-commands.sh"):
        """Create a consolidated script with all unique commands"""
        all_commands = set()
        for commands in self.commands_found.values():
            all_commands.update(commands)
        
        script_content = "#!/bin/bash\n"
        script_content += "# Auto-generated consolidated script\n"
        script_content += "# Generated by File Optimizer Agent\n\n"
        
        # Group commands by type
        docker_commands = [cmd for cmd in all_commands if 'docker' in cmd.lower()]
        git_commands = [cmd for cmd in all_commands if 'git' in cmd.lower()]
        other_commands = [cmd for cmd in all_commands if 'docker' not in cmd.lower() and 'git' not in cmd.lower()]
        
        if docker_commands:
            script_content += "# Docker Commands\n"
            for cmd in sorted(docker_commands):
                script_content += f"# {cmd}\n"
            script_content += "\n"
        
        if git_commands:
            script_content += "# Git Commands\n"
            for cmd in sorted(git_commands):
                script_content += f"# {cmd}\n"
            script_content += "\n"
        
        if other_commands:
            script_content += "# Other Commands\n"
            for cmd in sorted(other_commands):
                script_content += f"# {cmd}\n"
            script_content += "\n"
        
        with open(script_name, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_name, 0o755)
        self.logger.info(f"Created consolidated script: {script_name}")
    
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory:
            filepath = Path(event.src_path)
            if not self.should_ignore_file(filepath):
                self.logger.info(f"New file detected: {filepath}")
                time.sleep(0.1)  # Brief delay to ensure file is written
                self.analyze_file(filepath)
                self.detect_redundancies()
    
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory:
            filepath = Path(event.src_path)
            if not self.should_ignore_file(filepath):
                self.analyze_file(filepath)
    
    def generate_report(self):
        """Generate optimization report"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files_monitored": len(self.file_hashes),
            "files_with_commands": len(self.commands_found),
            "unique_commands": len(set(cmd for commands in self.commands_found.values() for cmd in commands)),
            "suggestions": self.generate_optimization_suggestions()
        }
        
        with open("optimization-report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        self.logger.info("Generated optimization report: optimization-report.json")
        return report

def main():
    parser = argparse.ArgumentParser(description="File Optimizer Background Agent")
    parser.add_argument("--watch-dir", default=".", help="Directory to monitor")
    parser.add_argument("--config", default="optimizer-config.json", help="Configuration file")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--report", action="store_true", help="Generate report and exit")
    parser.add_argument("--consolidate", action="store_true", help="Create consolidated script and exit")
    
    args = parser.parse_args()
    
    agent = FileOptimizerAgent(args.watch_dir, args.config)
    
    if args.report:
        report = agent.generate_report()
        print(json.dumps(report, indent=2))
        return
    
    if args.consolidate:
        agent.create_consolidated_script()
        return
    
    if args.daemon:
        # Run as background daemon
        observer = Observer()
        observer.schedule(agent, args.watch_dir, recursive=True)
        observer.start()
        
        try:
            agent.logger.info(f"File Optimizer Agent started. Monitoring: {args.watch_dir}")
            while True:
                time.sleep(10)
                # Periodic optimization check
                agent.detect_redundancies()
        except KeyboardInterrupt:
            observer.stop()
            agent.logger.info("File Optimizer Agent stopped.")
        
        observer.join()
    else:
        # One-time scan
        agent.logger.info("One-time optimization scan complete.")
        agent.generate_report()

if __name__ == "__main__":
    main() 