# Python script to get flat file list (for Python containers like api)
GET_FILE_LIST_PYTHON = """
import json
import sys
from pathlib import Path

IGNORE_DIRS = {
    "__pycache__", ".git", "node_modules", ".next", "venv", "env",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".vscode", ".idea",
    "dist", "build", ".egg-info", "htmlcov", ".tox", ".nox",
}

SOURCE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".json",
    ".yaml", ".yml", ".md", ".txt", ".sql", ".sh", ".env", ".ini", ".toml",
}

def get_files(directory, source_only=False):
    directory = Path(directory)
    files = []
    
    def scan(current_dir):
        try:
            for entry in sorted(current_dir.iterdir(), key=lambda x: x.name.lower()):
                if entry.name.startswith(".") and entry.name not in {".env", ".gitignore"}:
                    continue
                
                if entry.is_dir():
                    if entry.name not in IGNORE_DIRS:
                        scan(entry)
                else:
                    if source_only:
                        ext = entry.suffix.lower()
                        if ext not in SOURCE_EXTENSIONS and ext != "":
                            continue
                    files.append(str(entry.relative_to(directory)))
        except PermissionError:
            pass
    
    scan(directory)
    return files

source_only = len(sys.argv) > 1 and sys.argv[1] == "True"
files = get_files(".", source_only=source_only)
"""

# Node.js script to get flat file list (for Node containers like app)
GET_FILE_LIST_NODE = """
const fs = require('fs');
const path = require('path');

const IGNORE_DIRS = new Set([
    '__pycache__', '.git', 'node_modules', '.next', 'venv', 'env',
    '.mypy_cache', '.pytest_cache', '.ruff_cache', '.vscode', '.idea',
    'dist', 'build', '.egg-info', 'htmlcov', '.tox', '.nox',
]);

const SOURCE_EXTENSIONS = new Set([
    '.py', '.ts', '.tsx', '.js', '.jsx', '.css', '.html', '.json',
    '.yaml', '.yml', '.md', '.txt', '.sql', '.sh', '.env', '.ini', '.toml',
]);

function getFiles(directory, sourceOnly = false) {
    const files = [];
    
    function scan(currentDir) {
        try {
            const entries = fs.readdirSync(currentDir, { withFileTypes: true });
            
            for (const entry of entries.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()))) {
                if (entry.name.startsWith('.') && !['.env', '.gitignore'].includes(entry.name)) continue;
                
                const fullPath = path.join(currentDir, entry.name);
                
                if (entry.isDirectory()) {
                    if (!IGNORE_DIRS.has(entry.name)) {
                        scan(fullPath);
                    }
                } else {
                    if (sourceOnly) {
                        const ext = path.extname(entry.name).toLowerCase();
                        if (ext && !SOURCE_EXTENSIONS.has(ext)) continue;
                    }
                    files.push(path.relative(directory, fullPath));
                }
            }
        } catch (err) {
            // Skip permission errors
        }
    }
    
    scan(directory);
    return files;
}

const args = process.argv.slice(2);
const sourceOnly = args[0] === 'True';
const files = getFiles('.', sourceOnly);
console.log(JSON.stringify(files));
"""
