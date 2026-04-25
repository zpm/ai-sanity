import shlex


class BashCommandParser:

    """Tokenises a Bash command string and splits it into individual command clauses separated by pipes, logical
    operators, and semicolons. Each clause is a list of string tokens representing one simple command."""

    _CLAUSE_SEPARATORS = frozenset({"|", "&&", "||", ";"})

    @staticmethod
    def extract_command_clauses(bash_command_string):

        """Returns a list of token-lists, one per command clause. Splits on |, &&, ||, and ; separators. Returns an
        empty list when the command string is empty or cannot be tokenised (unbalanced quotes, etc.)."""
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
