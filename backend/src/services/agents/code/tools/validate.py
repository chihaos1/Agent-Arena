from typing import List, Dict, Tuple

class CodeValidator:
    """Validates generated code with deterministic checks."""

    @staticmethod
    def validate(generated_files: List[Dict], expected_files: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Validate generated code files.
        
        Args:
            generated_files: Files from Claude [{"path": "...", "content": "..."}]
            expected_files: Expected files from plan [{"file_path": "...", "action": "..."}]
        
        Returns:
            (is_valid, errors) tuple
        """

        errors = []

        # Structural Checks
        errors.extend(CodeValidator._check_structure(generated_files, expected_files))

        # Content Checks
        if generated_files:
            for file in generated_files:
                errors.extend(CodeValidator._check_empty_content(file))

    @staticmethod
    def _check_structure(generated_files: List[Dict], expected_files: List[Dict]) -> List[str]:
        """Check structural issues: file count, missing/extra files"""

        errors = []

        # Check if empty
        if not generated_files:
            errors.append("CRITICAL: No file were generated")
            return errors
        
        # Check file count
        if len(generated_files) != len(expected_files):
            errors.append(
                f"Expected {len(expected_files)} files, got {len(generated_files)}"
            )

        # Check all expected files are present
        expected_files = {f["file_path"] for f in expected_files}
        actual_files = {f["path"] for f in generated_files}

        missing_file = expected_files - actual_files
        if missing_file:
            errors.append(f"Missing files: {", ".join(sorted(missing_file))}")
        
        extra_files = actual_files - expected_files
        if expected_files:
            errors.append(f"Unexpected files: {", ".join(sorted(extra_files))}")
        
        return errors

    @staticmethod
    def _check_empty_content(file: Dict) -> List[str]:
        """Check if file content is empty"""

        errors = []
        path = file.get("path", "unknown")
        content = file.get("content", "")

        if not content.strip():
            errors.append(f"{path}: File is empty")

        return errors
    
    @staticmethod
    def _check_balanced_delimiters(file: Dict) -> List[str]:
        """Check if delimiters are balanced"""

        errors = []
        path = file.get("path", "unknown")
        content = file.get("content", "")

        # Skip if empty (flagged aboved)
        if not content.strip():
            return errors

        # Count delimiters
        open_brace = content.count("{")
        close_brace = content.count("}")
        open_paren = content.count("(")
        close_paren = content.count(")")
        open_bracket = content.count("[")
        close_bracket = content.count("]")

        if open_brace != close_brace:
            errors.append(
                f"{path}: Mismatched braces ({open_brace} open, {close_brace} close)"
            )
        
        if open_paren != close_paren:
            errors.append(
                f"{path}: Mismatched parentheses ({open_paren} open, {close_paren} close)"
            )
        
        if open_bracket != close_bracket:
            errors.append(
                f"{path}: Mismatched brackets ({open_bracket} open, {close_bracket} close)"
            )
        
        return errors
    
    @staticmethod
    def _check_common_syntax_errors(file: Dict) -> List[str]:
        """Check for common LLM-generated syntax errors"""

        errors = []
        path = file.get("path", "unknown")
        content = file.get("content", "")
        
        # Skip if empty
        if not content.strip():
            return errors
        
        duplicate_patterns = [
            ("export export", "export"),
            ('import import', 'import'),
            ('const const', 'const'),
            ('let let', 'let'),
            ('var var', 'var'),
            ('function function', 'function'),
            ('class class', 'class'),
            ('interface interface', 'interface'),
            ('type type', 'type'),
            ('def def', 'def')
        ]

        for pattern, keyword in duplicate_patterns:
            if pattern in content:
                errors.append(f"{path}: Duplicate {keyword} keyword found")
        
        return errors
    
    @staticmethod
    def _check_for_placeholders(file: Dict) -> List[str]:
        """Check for common placeholder text that LLMs sometimes leave"""

        errors = []
        path = file.get("path", "unknown")
        content = file.get("content", "")

        # Skip if empty
        if not content.strip():
            return errors
        
        # Common LLM placeholders
        placeholders = [
            "// TODO",
            "// FIXME",
            "// ...",
            "# TODO",
            "# FIXME",
            "...",  # Literal ellipsis in code
            "your_",  # your_api_key, your_function, etc.
            "example_",  # example_value, example_function
            "placeholder",
            "PLACEHOLDER",
        ]

        found_placeholders = []
        for placeholder in placeholders:
            if placeholder in content:
                found_placeholders.append(placeholder)

        if found_placeholders:
            errors.append(
                f"{path}: Contains placeholders: {", ".join(found_placeholders)}"
            )

        return errors