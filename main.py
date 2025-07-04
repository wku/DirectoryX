#!/usr/bin/env python3

import os
import sys
import hashlib
import argparse
import yaml
import datetime
import re
import tokenize
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class FileInfo:
    """Класс для хранения информации о файле"""

    def __init__(self, path: str, relative_path: str):
        self.path = path
        self.relative_path = relative_path
        self.file_name = os.path.basename(path)
        self.last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        self._hash = None

    def calculate_hash(self) -> str:
        """Вычисляет SHA-256 хеш содержимого файла"""
        if self._hash is None:
            hash_obj = hashlib.sha256()
            try:
                with open(self.path, 'rb') as f:
                    # Чтение файла блоками для эффективной работы с большими файлами
                    for chunk in iter(lambda: f.read(4096), b''):
                        hash_obj.update(chunk)
                self._hash = hash_obj.hexdigest()
            except Exception as e:
                self._hash = f"ERROR: {str(e)}"
        return self._hash

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует информацию о файле в словарь для YAML"""
        return {
            'path': self.relative_path,
            'file_name': self.file_name,
            'last_modified': self.last_modified,
            'hash': self.calculate_hash()
        }


class DirectoryScanner:
    """Класс для сканирования директорий и сбора информации о файлах"""

    def __init__(self, root_path: str, output_dir: Optional[str] = None, prefix: Optional[str] = None):
        self.root_path = os.path.abspath(root_path)
        self.files: List[FileInfo] = []
        self.directories: List[str] = []
        self.scan_time = datetime.datetime.now()

        # Предопределенные списки исключений
        # Директории, которые следует исключить
        self.excluded_dirs = [
            '__pycache__',
            '.git',
            '.idea',
            'venv',
            'node_modules',
            '.vscode',
            '.svelte-kit',
            'build', 'dist', '.vercel', '.netlify'
        ]

        # Файлы, которые следует исключить (по имени)
        self.excluded_files = [
            '.dockerignore',
            '.DS_Store',
            'Thumbs.db',
            '.gitignore',
            '.gitattributes',
            'package-lock.json'

        ]

        # Расширения файлов, которые следует исключить
        self.excluded_extensions = [
            '.pyc',
            '.pyo',
            '.pyd',
            '.so',
            '.dll',
            '.exe',
            '.obj',
            '.o',
            '.a',
            '.lib',
            '.swp',
            '.class',
            '.txt'
        ]

        # Файлы, которые следует явно включить в анализ (имеют приоритет над исключениями)
        self.force_include_files = [
            'Makefile',
            'Dockerfile.anvil',
            'Dockerfile.funder',
            'Dockerfile',
            'docker-compose.yml',
            'docker-compose.yaml',
            'requirements.txt',
            'package.json',

        ]

        if not os.path.exists(self.root_path):
            raise ValueError(f"Директория не существует: {self.root_path}")

        # Создание директории data или указанной директории
        if output_dir:
            self.data_dir = os.path.abspath(output_dir)
            print(f"Использование указанной выходной директории: {self.data_dir}")
        else:
            self.data_dir = os.path.join(os.getcwd(), 'data')

        os.makedirs(self.data_dir, exist_ok=True)

        # Имя корневой директории для использования в именах файлов
        self.root_dir_name = os.path.basename(self.root_path)

        # Префикс для имен файлов
        self.prefix = prefix
        if self.prefix:
            print(f"Использование префикса для файлов: {self.prefix}")

    def should_exclude_file(self, file_path: str) -> bool:
        """Проверяет, должен ли файл быть исключен из сканирования"""
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()

        # Проверка на принудительное включение (имеет приоритет над исключениями)
        if file_name in self.force_include_files:
            return False

        # Проверка по имени файла
        if file_name in self.excluded_files:
            return True

        # Проверка по расширению файла
        if file_ext in self.excluded_extensions:
            return True

        return False

    def scan(self) -> None:
        """Рекурсивное сканирование директории"""
        print(f"Сканирование директории: {self.root_path}")
        for root, dirs, files in os.walk(self.root_path):
            # Фильтрация исключаемых директорий
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            # Добавление директорий
            rel_path = os.path.relpath(root, self.root_path)
            if rel_path != '.':
                self.directories.append(rel_path)

            # Добавление файлов с учетом исключений
            for file in files:
                file_path = os.path.join(root, file)
                # Пропускаем файлы, которые должны быть исключены
                if self.should_exclude_file(file_path):
                    continue

                rel_file_path = os.path.relpath(file_path, self.root_path)
                self.files.append(FileInfo(file_path, rel_file_path))

        print(f"Сканирование завершено. Найдено {len(self.files)} файлов и {len(self.directories)} директорий")


class ReportGenerator:
    """Класс для генерации отчетов на основе данных сканирования"""

    def __init__(self, scanner: DirectoryScanner):
        self.scanner = scanner

        # Формирование имен файлов в формате: [префикс_]имя_директории_дата_время
        timestamp = self.scanner.scan_time.strftime('%Y_%m_%d_%H_%M_%S')

        if scanner.prefix:
            file_prefix = f"{scanner.prefix}_{self.scanner.root_dir_name}_{timestamp}"
        else:
            file_prefix = f"{self.scanner.root_dir_name}_{timestamp}"

        self.md_path = os.path.join(scanner.data_dir, f"{file_prefix}_structure.md")
        self.yaml_path = os.path.join(scanner.data_dir, f"{file_prefix}_structure.yaml")
        self.content_md_path = os.path.join(scanner.data_dir, f"{file_prefix}_content.md")

    def build_directory_tree(self) -> Dict[str, Any]:
        """Строит дерево директорий для использования в отчетах"""
        tree = {}

        # Добавление директорий
        for dir_path in sorted(self.scanner.directories):
            parts = dir_path.split(os.sep)
            current = tree
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]

        # Добавление файлов
        for file_info in sorted(self.scanner.files, key=lambda x: x.relative_path):
            parts = file_info.relative_path.split(os.sep)
            file_name = parts[-1]
            current = tree

            # Навигация по дереву до родительской директории файла
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Добавление файла как листа дерева
            current[file_name] = file_name

        return tree

    def _generate_md_tree(self, tree: Dict[str, Any], prefix: str = "", is_last: bool = True,
                          level: int = 0) -> List[str]:
        """Рекурсивно генерирует представление структуры директорий в формате markdown"""
        lines = []
        items = list(tree.items())

        for i, (name, subtree) in enumerate(items):
            is_last_item = i == len(items) - 1

            # Определяем, является ли элемент файлом
            is_file = isinstance(subtree, str)

            # Формируем префикс и символы для текущего элемента
            if level == 0:
                current_prefix = "├── " if not is_last_item else "└── "
            else:
                current_prefix = prefix + ("└── " if is_last else "├── ")

            # Добавляем текущий элемент
            lines.append(f"{current_prefix}{name}")

            # Если это директория, рекурсивно добавляем ее содержимое
            if not is_file:
                # Формируем префикс для дочерних элементов
                if level == 0:
                    new_prefix = "│   " if not is_last_item else "    "
                else:
                    new_prefix = prefix + ("    " if is_last else "│   ")

                # Рекурсивный вызов для дочерних элементов
                subtree_lines = self._generate_md_tree(subtree, new_prefix, is_last_item, level + 1)
                lines.extend(subtree_lines)

        return lines

    def generate_md_report(self) -> None:
        """Генерирует отчет в формате markdown"""
        tree = self.build_directory_tree()

        # Формирование содержимого markdown
        md_content = [
            f"# Структура проекта: {os.path.basename(self.scanner.root_path)}",
            "",
            f"*Сгенерировано: {self.scanner.scan_time.strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "```",
            f"{os.path.basename(self.scanner.root_path)}/",
        ]

        # Добавление структуры директорий
        md_content.extend(self._generate_md_tree(tree))
        md_content.append("```")

        # Добавление информации об исключенных элементах
        md_content.append("\n## Исключенные элементы")
        md_content.append("\n### Исключенные директории")
        for dir_name in self.scanner.excluded_dirs:
            md_content.append(f"- {dir_name}")

        md_content.append("\n### Исключенные файлы")
        for file_name in self.scanner.excluded_files:
            md_content.append(f"- {file_name}")

        md_content.append("\n### Исключенные расширения")
        for ext in self.scanner.excluded_extensions:
            md_content.append(f"- {ext}")

        # Добавление информации о принудительно включенных файлах
        md_content.append("\n### Принудительно включенные файлы")
        for file_name in self.scanner.force_include_files:
            md_content.append(f"- {file_name}")

        # Запись в файл
        with open(self.md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))

        print(f"Markdown отчет сохранен: {self.md_path}")

    def generate_yaml_report(self) -> None:
        """Генерирует отчет в формате YAML"""
        # Подготовка структуры для YAML
        yaml_structure = {
            'scan_time': self.scanner.scan_time,
            'root_directory': self.scanner.root_path,
            'directories_count': len(self.scanner.directories),
            'files_count': len(self.scanner.files),
            'exclusions': {
                'excluded_directories': self.scanner.excluded_dirs,
                'excluded_files': self.scanner.excluded_files,
                'excluded_extensions': self.scanner.excluded_extensions,
                'force_include_files': self.scanner.force_include_files
            },
            'directories': self.scanner.directories,
            'files': [file_info.to_dict() for file_info in self.scanner.files]
        }

        # Запись в файл
        with open(self.yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_structure, f, default_flow_style=False, sort_keys=False)

        print(f"YAML отчет сохранен: {self.yaml_path}")

    def remove_python_comments_and_docstrings(self, source_code: str) -> str:
        """Удаляет комментарии и строки документации из Python кода с сохранением форматирования"""
        # Разбиваем код на строки
        lines = source_code.splitlines()

        # Результирующие строки
        result_lines = []

        # Флаги для отслеживания многострочных комментариев/docstrings
        in_triple_quotes = False
        triple_quote_type = None
        docstring_indentation = 0
        skip_next_line = False

        for i, line in enumerate(lines):
            # Пропускаем строку, если флаг установлен
            if skip_next_line:
                skip_next_line = False
                continue

            # Если мы не внутри многострочной строки/docstring
            if not in_triple_quotes:
                # Проверяем, является ли строка полностью комментарием или пустой
                stripped_line = line.strip()

                # Пропускаем комментарии
                if stripped_line.startswith('#'):
                    continue

                # Проверяем наличие triple quotes
                if '"""' in stripped_line or "'''" in stripped_line:
                    # Определяем тип кавычек
                    if '"""' in stripped_line:
                        quote_type = '"""'
                    else:
                        quote_type = "'''"

                    # Проверяем, не является ли это частью docstring
                    if stripped_line.startswith(quote_type):
                        # Проверяем, может ли это быть docstring
                        if i > 0:
                            prev_line = lines[i - 1].strip()
                            if prev_line.startswith('def ') or prev_line.startswith('class ') or prev_line.endswith(':'):
                                # Это начало docstring
                                in_triple_quotes = True
                                triple_quote_type = quote_type
                                docstring_indentation = len(line) - len(line.lstrip())
                                continue

                    # Проверяем, не заканчивается ли тройная кавычка в той же строке
                    if stripped_line.count(quote_type) == 2:
                        # Если строка содержит только docstring, пропускаем её
                        if stripped_line.startswith(quote_type) and stripped_line.endswith(quote_type) and len(stripped_line) > 6:
                            continue

                    # Удаляем комментарии из этой строки
                    comment_pos = line.find('#')
                    if comment_pos != -1:
                        line = line[:comment_pos]

                    # Добавляем строку в результат
                    result_lines.append(line.rstrip())

                else:
                    # Удаляем комментарии из строки
                    comment_pos = line.find('#')
                    if comment_pos != -1:
                        line = line[:comment_pos]

                    # Добавляем строку в результат
                    result_lines.append(line.rstrip())

            else:
                # Мы внутри многострочного docstring
                # Проверяем, заканчивается ли он в этой строке
                if triple_quote_type in line:
                    # Docstring закончился
                    in_triple_quotes = False
                    triple_quote_type = None
                # Не добавляем строки, которые являются частью docstring

        # Объединяем строки с сохранением разделителей
        return '\n'.join(result_lines)

    def generate_content_report(self) -> None:
        """Генерирует отчет с содержимым всех файлов в формате markdown,
        удаляя комментарии и docstrings для Python файлов"""
        # Регулярные выражения для обработки текста
        multiple_spaces_pattern = re.compile(r' {2,}')
        multiple_newlines_pattern = re.compile(r'\n{3,}')

        print("Создание общего файла с содержимым...")

        # Список текстовых расширений для обработки
        text_extensions = {
            '.txt', '.md', '.py', '.js', '.java', '.c', '.cpp', '.h', '.hpp',
            '.cs', '.php', '.html', '.css', '.xml', '.json', '.yaml', '.yml',
            '.ini', '.conf', '.sh', '.bat', '.ps1', '.sql', '.go', '.rb',
            '.rs', '.dart', '.swift', '.kt', '.ts', '.r', '.pl', '.lua',
            '.svelte', '.mjs', '.d.ts', '.postcss', '.sol', '', '.Makefile'
        }

        # Сортировка файлов для сохранения последовательности
        sorted_files = sorted(self.scanner.files, key=lambda x: x.relative_path)

        # Создание отчета с содержимым файлов
        with open(self.content_md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Содержимое файлов проекта: {os.path.basename(self.scanner.root_path)}\n\n")
            f.write(f"*Сгенерировано: {self.scanner.scan_time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write("---\n\n")

            for file_info in sorted_files:
                file_extension = os.path.splitext(file_info.file_name)[1].lower()
                file_name = file_info.file_name

                # Пропускаем файлы с расширениями, которые следует исключить, если они не в списке принудительного включения
                if file_extension in self.scanner.excluded_extensions and file_name not in self.scanner.force_include_files:
                    continue

                # Пропускаем бинарные файлы, если они не в списке принудительного включения
                if file_extension not in text_extensions and file_name not in self.scanner.force_include_files:
                    continue

                f.write(f"## {file_info.relative_path}\n\n")

                # Определяем расширение для блока кода
                if file_extension:
                    code_extension = file_extension[1:]
                else:
                    # Для файлов без расширения пытаемся определить тип по имени
                    if file_name.lower() == 'makefile':
                        code_extension = 'makefile'
                    elif file_name.lower() == 'dockerfile':
                        code_extension = 'dockerfile'
                    else:
                        code_extension = 'text'

                f.write("```" + code_extension + "\n")

                try:
                    # Чтение содержимого файла
                    with open(file_info.path, 'r', encoding='utf-8', errors='replace') as content_file:
                        content = content_file.read()

                        # Обработка Python файлов - удаление комментариев и docstrings
                        if file_extension == '.py':
                            try:
                                content = self.remove_python_comments_and_docstrings(content)
                            except Exception as e:
                                print(f"Ошибка при удалении комментариев из Python файла {file_info.path}: {str(e)}")
                                # Если произошла ошибка, используем оригинальный текст

                        # Обработка содержимого: удаление лишних пробелов и пустых строк
                        content = multiple_spaces_pattern.sub(' ', content)
                        content = multiple_newlines_pattern.sub('\n\n', content)

                        f.write(content)

                except Exception as e:
                    f.write(f"Ошибка при чтении файла: {str(e)}")

                f.write("\n```\n\n")
                f.write("---\n\n")

        print(f"Отчет с содержимым файлов сохранен: {self.content_md_path}")


def main() -> None:
    """Главная функция программы"""
    parser = argparse.ArgumentParser(description='Сканер структуры директорий')
    parser.add_argument('path', help='Путь к директории для сканирования')
    parser.add_argument('--exclude-dirs', nargs='+', help='Дополнительные директории для исключения')
    parser.add_argument('--exclude-files', nargs='+', help='Файлы для исключения')
    parser.add_argument('--exclude-ext', nargs='+', help='Расширения файлов для исключения (с точкой, например .pdf)')
    parser.add_argument('--include-files', nargs='+', help='Файлы для принудительного включения (имеют приоритет над исключениями)')
    parser.add_argument('--no-content', action='store_true', help='Не создавать файл с содержимым')
    parser.add_argument('--output-dir', help='Директория для сохранения отчетов (по умолчанию: data)')
    parser.add_argument('--prefix', help='Префикс для имен файлов отчетов')
    args = parser.parse_args()

    try:
        # Инициализация и сканирование
        scanner = DirectoryScanner(args.path, args.output_dir, args.prefix)

        # Добавление дополнительных исключений, если они указаны
        if args.exclude_dirs:
            scanner.excluded_dirs.extend(args.exclude_dirs)
            print(f"Дополнительные исключаемые директории: {', '.join(args.exclude_dirs)}")

        if args.exclude_files:
            scanner.excluded_files.extend(args.exclude_files)
            print(f"Дополнительные исключаемые файлы: {', '.join(args.exclude_files)}")

        if args.exclude_ext:
            scanner.excluded_extensions.extend(args.exclude_ext)
            print(f"Дополнительные исключаемые расширения: {', '.join(args.exclude_ext)}")

        # Добавление дополнительных файлов для принудительного включения
        if args.include_files:
            scanner.force_include_files.extend(args.include_files)
            print(f"Дополнительные файлы для принудительного включения: {', '.join(args.include_files)}")

        print(f"Всего исключаемых директорий: {len(scanner.excluded_dirs)}")
        print(f"Всего исключаемых файлов: {len(scanner.excluded_files)}")
        print(f"Всего исключаемых расширений: {len(scanner.excluded_extensions)}")
        print(f"Всего файлов для принудительного включения: {len(scanner.force_include_files)}")

        scanner.scan()

        # Генерация отчетов
        report_generator = ReportGenerator(scanner)
        report_generator.generate_md_report()
        report_generator.generate_yaml_report()

        # Создание отчета с содержимым файлов, если не отключено
        if not args.no_content:
            report_generator.generate_content_report()
            print(f"Отчет с содержимым: {os.path.basename(report_generator.content_md_path)}")

        print(f"Markdown отчет: {os.path.basename(report_generator.md_path)}")
        print(f"YAML отчет: {os.path.basename(report_generator.yaml_path)}")
        print("Работа программы успешно завершена")

    except Exception as e:
        print(f"Ошибка: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""

#contract
python project_scanner.py ../../ --output-dir data/contract --prefix contract --exclude-dirs assets dex_web doc node_modules artifacts cache infrastructure data .pytest_cache .idea .svelte-kit

#web
python project_scanner.py ../../ --output-dir data/web --prefix web --exclude-dirs assets dex_contracts doc node_modules artifacts cache infrastructure data .pytest_cache .idea .svelte-kit

"""
