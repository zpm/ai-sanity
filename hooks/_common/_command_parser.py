########################################################################################################################
# hooks/_common/_command_parser.py
#
# tokenises a bash command string into individual command clauses
########################################################################################################################


import re
import shlex


SAFE_PIPE_TARGET_COMMANDS = {
    "tail", "head", "grep", "cat", "wc", "sort", "uniq", "tr", "cut", "column"
}

DESCRIPTOR_MERGE_PATTERN = re.compile(r"^\d*>&\d+$")
FILE_REDIRECT_PATTERN = re.compile(r"^(\d*>{1,2}|<{1,2}|&>{1,2})$")
ATTACHED_FILE_REDIRECT_PATTERN = re.compile(r"^(\d*>{1,2}|<{1,2}|&>{1,2})[^&>\s]")


class RedirectTokenClassifier:

    """Classifies shell redirect tokens as descriptor merges (safe) or file redirects. Provides a shared
    strip method that removes descriptor merges from a token list."""

    @staticmethod
    def strip_descriptor_merge_tokens_from_clause(clause_tokens):

        """Removes descriptor-to-descriptor redirects (like 2>&1) from a token list. Returns the cleaned list."""
        return [
            token for token in clause_tokens
            if not DESCRIPTOR_MERGE_PATTERN.match(token)
        ]

    @staticmethod
    def clause_contains_file_redirect(clause_tokens):

        """Returns True if any token in the clause is a file redirect operator."""
        for token in clause_tokens:
            if FILE_REDIRECT_PATTERN.match(token):
                return True
            if ATTACHED_FILE_REDIRECT_PATTERN.match(token):
                return True
        return False


class BashCommandParser:

    """Tokenises a Bash command string and splits it into individual command clauses separated by pipes, logical
    operators, and semicolons. Each clause is a list of string tokens representing one simple command."""

    _CLAUSE_SEPARATORS = {
        "|": True,
        "&&": True,
        "||": True,
        ";": True,
    }

    @staticmethod
    def extract_command_clauses(bash_command_string):

        """Returns a list of token-lists, one per command clause. Splits on |, &&, ||, and ; separators that appear as
        standalone shlex tokens. Returns an empty list when the command string is empty or cannot be tokenised."""
        try:
            tokens = shlex.split(bash_command_string)
        except ValueError:
            return []
        if not tokens:
            return []
        clauses = []
        current_clause = []
        for token in tokens:
            if token in BashCommandParser._CLAUSE_SEPARATORS:
                if current_clause:
                    clauses.append(current_clause)
                current_clause = []
            else:
                current_clause.append(token)
        if current_clause:
            clauses.append(current_clause)
        return clauses

    @staticmethod
    def extract_command_clauses_and_separators(bash_command_string):

        """Returns (clauses, separators) where clauses is a list of token-lists and separators is a list of operator
        strings found between them. An empty command or unbalanced quotes returns ([], [])."""
        try:
            tokens = shlex.split(bash_command_string)
        except ValueError:
            return [], []
        if not tokens:
            return [], []
        clauses = []
        separators = []
        current_clause = []
        for token in tokens:
            if token in BashCommandParser._CLAUSE_SEPARATORS:
                if current_clause:
                    clauses.append(current_clause)
                separators.append(token)
                current_clause = []
            else:
                current_clause.append(token)
        if current_clause:
            clauses.append(current_clause)
        return clauses, separators
