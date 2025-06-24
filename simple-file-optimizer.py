#!/usr/bin/env python3
"""
Simple File Optimizer - No External Dependencies
Analyzes files for redundancies and optimization opportunities
"""

import os
import sys
import hashlib
import difflib
import json
import argparse
import re
from pathlib import Path
from collections import defaultdict

class SimpleFileOptimizer:
    def __init__(self, watch_dir="."):
        self.watch_dir = Path(watch_dir)
        self.file_hashes = {}
        self.commands_found = defaultdict(list)
        self.config = {
            "similarity_threshold": 0.7,
            "ignore_patterns": [".git", "__pycache__", "*.pyc", "node_modules", ".vscode"],
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
    
    def scan_files(self):
        """Scan all files in directory"""
        print(f"🔍 Scanning files in {self.watch_dir}...")
        
        for root, dirs, files in os.walk(self.watch_dir):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self.config["ignore_patterns"])]
            
            for file in files:
                filepath = Path(root) / file
                if not self.should_ignore_file(filepath):
                    self.analyze_file(filepath)
        
        print(f"✅ Found {len(self.file_hashes)} files to analyze")
    
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
    
    def find_duplicates(self):
        """Find duplicate files"""
        hash_to_files = defaultdict(list)
        for filepath, file_hash in self.file_hashes.items():
            hash_to_files[file_hash].append(filepath)
        
        duplicates = {k: v for k, v in hash_to_files.items() if len(v) > 1}
        
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} sets of duplicate files:")
            for file_hash, files in duplicates.items():
                print(f"   📋 Duplicates: {files}")
        else:
            print("\n✅ No duplicate files found")
        
        return duplicates
    
    def find_similar_files(self):
        """Find files with similar content"""
        print(f"\n🔍 Checking for similar files (threshold: {self.config['similarity_threshold']:.0%})...")
        
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
            print(f"⚠️  Found {len(similar_pairs)} pairs of similar files:")
            for path1, path2, similarity in similar_pairs:
                print(f"   📊 {similarity:.1%} similar: {Path(path1).name} ↔ {Path(path2).name}")
        else:
            print("✅ No significantly similar files found")
        
        return similar_pairs
    
    def find_redundant_commands(self):
        """Find redundant commands across files"""
        print(f"\n🔍 Analyzing commands across {len(self.commands_found)} files...")
        
        command_to_files = defaultdict(list)
        for filepath, commands in self.commands_found.items():
            for command in commands:
                command_to_files[command].append(filepath)
        
        redundant_commands = {k: v for k, v in command_to_files.items() if len(v) > 1}
        
        if redundant_commands:
            print(f"⚠️  Found {len(redundant_commands)} redundant commands:")
            for command, files in redundant_commands.items():
                file_names = [Path(f).name for f in files]
                print(f"   🔄 '{command}' appears in: {file_names}")
        else:
            print("✅ No redundant commands found")
        
        return redundant_commands
    
    def create_consolidated_script(self):
        """Create a consolidated script with all unique commands"""
        all_commands = set()
        for commands in self.commands_found.values():
            all_commands.update(commands)
        
        if not all_commands:
            print("ℹ️  No commands found to consolidate")
            return
        
        script_name = "consolidated-commands.sh"
        script_content = "#!/bin/bash\n"
        script_content += "# Auto-generated consolidated script\n"
        script_content += f"# Generated by Simple File Optimizer\n"
        script_content += f"# Total unique commands: {len(all_commands)}\n\n"
        
        # Group commands by type
        docker_commands = [cmd for cmd in all_commands if 'docker' in cmd.lower()]
        git_commands = [cmd for cmd in all_commands if 'git' in cmd.lower()]
        other_commands = [cmd for cmd in all_commands if 'docker' not in cmd.lower() and 'git' not in cmd.lower()]
        
        if docker_commands:
            script_content += "# Docker Commands\n"
            for cmd in sorted(docker_commands):
                script_content += f"echo 'Would run: {cmd}'\n"
            script_content += "\n"
        
        if git_commands:
            script_content += "# Git Commands\n"
            for cmd in sorted(git_commands):
                script_content += f"echo 'Would run: {cmd}'\n"
            script_content += "\n"
        
        if other_commands:
            script_content += "# Other Commands\n"
            for cmd in sorted(other_commands):
                script_content += f"echo 'Would run: {cmd}'\n"
            script_content += "\n"
        
        with open(script_name, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_name, 0o755)
        print(f"✅ Created consolidated script: {script_name}")
    
    def generate_report(self):
        """Generate comprehensive optimization report"""
        print("📊 OPTIMIZATION REPORT")
        print("=" * 50)
        
        # Scan files first
        self.scan_files()
        
        # Find issues
        duplicates = self.find_duplicates()
        similar_pairs = self.find_similar_files()
        redundant_commands = self.find_redundant_commands()
        
        # Summary
        print(f"\n📈 SUMMARY:")
        print(f"   📁 Files analyzed: {len(self.file_hashes)}")
        print(f"   📋 Files with commands: {len(self.commands_found)}")
        print(f"   🔄 Unique commands found: {len(set(cmd for commands in self.commands_found.values() for cmd in commands))}")
        print(f"   ⚠️  Duplicate file sets: {len(duplicates)}")
        print(f"   📊 Similar file pairs: {len(similar_pairs)}")
        print(f"   🔄 Redundant commands: {len(redundant_commands)}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if duplicates:
            print("   🗑️  Consider removing duplicate files")
        if similar_pairs:
            print("   🔗 Consider merging similar files")
        if redundant_commands:
            print("   📝 Consider creating shared utility scripts")
            self.create_consolidated_script()
        
        if not duplicates and not similar_pairs and not redundant_commands:
            print("   ✨ Project structure looks optimized!")
        
        print(f"\n🎯 Run with --consolidate to create utility scripts")

def main():
    parser = argparse.ArgumentParser(description="Simple File Optimizer")
    parser.add_argument("--watch-dir", default=".", help="Directory to analyze")
    parser.add_argument("--report", action="store_true", help="Generate optimization report")
    parser.add_argument("--consolidate", action="store_true", help="Create consolidated script")
    
    args = parser.parse_args()
    
    optimizer = SimpleFileOptimizer(args.watch_dir)
    
    if args.consolidate:
        optimizer.scan_files()
        optimizer.create_consolidated_script()
    elif args.report:
        optimizer.generate_report()
    else:
        # Default: generate report
        optimizer.generate_report()

if __name__ == "__main__":
    main() 