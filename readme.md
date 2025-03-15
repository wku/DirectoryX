# Directory Structure Scanner

A utility for scanning directory structures and generating reports in various formats.

## Features

- Recursive directory scanning
- SHA-256 file hash calculation
- Markdown reports with visual directory structure representation
- Detailed YAML reports
- Unified Markdown file with all text files content
- Directory and file filtering
- Timestamped report file names

## Installation

Python 3.6 or higher is required.

1. Clone the repository:
```bash
git clone https://github.com/username/directory-scanner.git
cd directory-scanner
```

2. Install dependencies:
```bash
pip install pyyaml
```

## Usage

### Basic Usage

```bash
python directory_scanner.py /path/to/directory
```

### Additional Parameters

- `--exclude` - exclude specified directories from scanning:
  ```bash
  python directory_scanner.py /path/to/directory --exclude node_modules .git __pycache__
  ```

- `--no-content` - disable generation of the file containing all text files content:
  ```bash
  python directory_scanner.py /path/to/directory --no-content
  ```
  
- `--exclude-ext` - exclude files with specified extensions:
  ```bash
  python directory_scanner.py /path/to/directory --exclude-ext jpg png gif
  ```

### Scan Results

All reports are saved in the `data` directory within the current working directory. File names follow the format:
- `directory_name_YYYY_MM_DD_HH_MM_SS_structure.md` - directory structure in Markdown format
- `directory_name_YYYY_MM_DD_HH_MM_SS_structure.yaml` - detailed structure in YAML format
- `directory_name_YYYY_MM_DD_HH_MM_SS_content.md` - content of all text files

## Report Formats

### Markdown Report

Presents the directory structure as a tree using ASCII characters.

### YAML Report

Contains detailed information about each file:
- Relative path
- File name
- Last modification date
- SHA-256 hash of the content

### Content Report

Includes the content of all text files, formatted as follows:
- Header with the file path
- Content in a code block with syntax highlighting
- Removal of excessive spaces and empty lines

## Use Cases

### Scanning Project Source Code

```bash
python directory_scanner.py /path/to/project --exclude node_modules .git __pycache__ .venv
```

### Scanning Documentation

```bash
python directory_scanner.py /path/to/documentation --exclude-ext pdf docx
```

## License

[MIT](LICENSE)

## Author

Your Name - youremail@example.com