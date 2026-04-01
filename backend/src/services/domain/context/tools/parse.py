from pathlib import Path

from tree_sitter import Language, Parser, Node
import tree_sitter_typescript
import tree_sitter_python

class CodeParser:
    def __init__(self):
        self.langs = {
            "ts": Language(tree_sitter_typescript.language_typescript()),
            "tsx": Language(tree_sitter_typescript.language_tsx()),
            "py": Language(tree_sitter_python.language())
        }

        # Initializes parsers for languages specified in langs
        self.parsers = {
            key: Parser(lang) for key, lang in self.langs.items()
        }
    
    def extract_code_excerpt(self, file_path: str, content: str):
        """
        Parses source code to extract a high-level overview of its definitions.

        Identifies the file type, selects the appropriate Tree-sitter parser, 
        and extracts signatures (imports, functions, classes) to create a 
        concise 'skeleton' of the file for LLM context.

        Args:
            file_path: Path of the file to determine language extension.
            content: Raw source code string to be parsed.

        Returns:
            A string of joined code signatures, or a fallback excerpt 
            (first 50 lines) if parsing fails or no targets are found.
        """

        file_ext = Path(file_path).suffix.lower().lstrip(".")
        lines = content.splitlines()

        try:
            match file_ext:
                case "py":
                    parser = self.parsers["py"]
                    targets = {
                        "import_statement", "import_from_statement",
                        "function_definition", "class_definition"
                    }
                case "ts" | "tsx":
                    parser = self.parsers[file_ext]
                    targets = {
                        "import_statement", "export_statement",
                        "function_declaration", "class_declaration",
                        "interface_declaration", "type_alias_declaration",
                        "lexical_declaration", "return_statement"
                    }
                case "js" | "jsx":
                    parser = self.parsers["tsx"]
                    targets = {
                        "import_statement", "export_statement",
                        "function_declaration", "class_declaration",
                        "interface_declaration", "type_alias_declaration",
                        "lexical_declaration", "return_statement"
                    }
                case _:
                    return {
                        "signatures": "\n".join(lines[:50]),
                        "imports": []
                    }
            
            tree = parser.parse(bytes(content, "utf8"))
            signatures, imports = [], []
            self._walk(tree.root_node, content, lines, signatures, imports, targets)
            
            return {
                "signatures": "\n".join(signatures) if signatures else content[:1000],
                "imports": imports
            }
        
        except Exception as e:
            return {
                "signatures": "\n".join(lines[:50]),
                "imports": []
            }

    def _walk(self, node: Node, content:str, lines: list, signatures: list, imports: list, targets: set, seen=None):
        """
        Recursively extracts the first line of code for all target AST nodes.

        Performs a depth-first traversal of the syntax tree. When a target node type 
        is encountered, its starting line is captured (if not already seen) and 
        the traversal continues into its children to find nested definitions.

        Args:
            node: Current Tree-sitter AST node.
            content (str): The full, original source code string. Used to get import paths.
            lines: Source code split into individual lines.
            signatures: List to store extracted signature strings.
            imports: List of imported libraries or scripts.
            targets: Node types to capture (e.g., 'class_definition').
            seen: Set of line indices already processed to prevent duplicates.
        """

        if seen is None:
            seen = set()

        if node.type in targets:
            start = node.start_point[0]
            if start not in seen:
                seen.add(start)

                #Extract import path to create dependency mappings
                if "import" in node.type:
                    signatures.append(lines[start])
                    for child in node.children:
                        if child.type in {"string", "dotted_name"}: # Gets only the path
                            imports.append(content[child.start_byte:child.end_byte].strip("\"'"))

                elif "class" in node.type:
                    signatures.append(lines[start])
                    for child in node.children:
                        self._walk(child, content, lines, signatures, imports, targets, seen)
                    return 
                
                elif "return" in node.type:
                    end = node.end_point[0]
                    return_block = "\n".join(lines[start:end + 1])
                    signatures.append(return_block)
                    return 

                else:
                    signatures.append(lines[start])
        
        for child in node.children:
            self._walk(child, content, lines, signatures, imports, targets, seen)