########################################################################################################################
# hooks/_common/_command_parser.py
#
# tokenises a bash command string into individual command clauses
########################################################################################################################


import re
import shlex


SAFE_PIPE_TARGET_COMMANDS = {
    "tail", "head", "grep", "cat", "wc", "sort", "uniq", "tr", "cut", "column", "xargs"
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


class BashSeparatorSpacingNormalizer:

    """Pads every unquoted clause separator with whitespace so the tokeniser emits it as a standalone token.

    shlex splits on whitespace alone, so a separator glued to its neighbour (`head -3; git push`, `cat a&&rm b`) or a
    newline between two commands never becomes a separator token. The clause parser then sees a single clause whose
    command word is the harmless first command, and every deny check downstream inspects that word instead of the
    smuggled one. Separators inside quotes are left alone, as are the & and | that belong to a redirect operator."""

    _SEPARATOR_OPERATORS_LONGEST_FIRST = ("&&", "||", ";;", ";", "|", "&")

    _QUOTE_CHARACTERS = ("'", "\"")

    _NEWLINE_CHARACTERS = ("\n", "\r")

    _REDIRECT_CHARACTERS = ("<", ">")

    _SEPARATOR_LEADING_CHARACTERS = ("&", "|", ";")


    @staticmethod
    def _newline_sequence_length(bash_command_string, character_index):

        """Returns the length of the newline sequence starting at character_index, treating a CRLF pair as one."""
        if bash_command_string.startswith("\r\n", character_index):
            return 2
        return 1


    @staticmethod
    def _character_belongs_to_redirect_operator(bash_command_string, character_index):

        """Returns True when the & or | at character_index is part of a redirect operator (2>&1, &>log, >|file)
        rather than a clause separator. Splitting those would corrupt the redirect token the classifier expects."""
        current_character = bash_command_string[character_index]
        previous_character = bash_command_string[character_index - 1] if character_index > 0 else ""
        next_character = (
            bash_command_string[character_index + 1] if character_index + 1 < len(bash_command_string) else ""
        )
        if previous_character in BashSeparatorSpacingNormalizer._REDIRECT_CHARACTERS:
            return True
        if current_character == "&" and next_character in BashSeparatorSpacingNormalizer._REDIRECT_CHARACTERS:
            return True
        return False


    @staticmethod
    def normalize(bash_command_string):

        """Returns the command string with every unquoted separator and newline surrounded by spaces. Newlines become
        `;` because bash treats a line break between two commands as a command terminator."""
        normalized_characters = []
        active_quote_character = None
        character_index = 0
        command_length = len(bash_command_string)
        while character_index < command_length:
            current_character = bash_command_string[character_index]
            # inside a quoted string every character is literal, including separators, so copy through to the
            # closing quote. a backslash inside double quotes escapes the next character (including a quote).
            if active_quote_character is not None:
                normalized_characters.append(current_character)
                if (
                    current_character == "\\"
                    and active_quote_character == "\""
                    and character_index + 1 < command_length
                ):
                    normalized_characters.append(bash_command_string[character_index + 1])
                    character_index += 2
                    continue
                if current_character == active_quote_character:
                    active_quote_character = None
                character_index += 1
                continue
            if current_character in BashSeparatorSpacingNormalizer._QUOTE_CHARACTERS:
                active_quote_character = current_character
                normalized_characters.append(current_character)
                character_index += 1
                continue
            if current_character == "\\":
                escaped_character = (
                    bash_command_string[character_index + 1] if character_index + 1 < command_length else ""
                )
                # a backslash before a newline is a line continuation: drop both so the lines join into one clause
                if escaped_character in BashSeparatorSpacingNormalizer._NEWLINE_CHARACTERS:
                    character_index += 1 + BashSeparatorSpacingNormalizer._newline_sequence_length(
                        bash_command_string = bash_command_string,
                        character_index = character_index + 1
                    )
                    continue
                normalized_characters.append(current_character)
                if escaped_character:
                    normalized_characters.append(escaped_character)
                    character_index += 2
                    continue
                character_index += 1
                continue
            if current_character in BashSeparatorSpacingNormalizer._NEWLINE_CHARACTERS:
                normalized_characters.append(" ; ")
                character_index += BashSeparatorSpacingNormalizer._newline_sequence_length(
                    bash_command_string = bash_command_string,
                    character_index = character_index
                )
                continue
            if (
                current_character in BashSeparatorSpacingNormalizer._SEPARATOR_LEADING_CHARACTERS
                and BashSeparatorSpacingNormalizer._character_belongs_to_redirect_operator(
                    bash_command_string = bash_command_string,
                    character_index = character_index
                )
            ):
                normalized_characters.append(current_character)
                character_index += 1
                continue
            matched_separator_operator = None
            for separator_operator in BashSeparatorSpacingNormalizer._SEPARATOR_OPERATORS_LONGEST_FIRST:
                if bash_command_string.startswith(separator_operator, character_index):
                    matched_separator_operator = separator_operator
                    break
            if matched_separator_operator is not None:
                normalized_characters.append(f" {matched_separator_operator} ")
                character_index += len(matched_separator_operator)
                continue
            normalized_characters.append(current_character)
            character_index += 1
        return "".join(normalized_characters)


class BashCommandParser:

    """Tokenises a Bash command string and splits it into individual command clauses separated by pipes, logical
    operators, semicolons, newlines, and backgrounding ampersands. Each clause is a list of string tokens representing
    one simple command."""

    _CLAUSE_SEPARATORS = {
        "|": True,
        "&&": True,
        "||": True,
        "&": True,
        ";": True,
        ";;": True,
    }


    @staticmethod
    def tokenize(bash_command_string):

        """Strips trailing backslashes (Windows path artifacts and dangling line continuations), pads every unquoted
        separator with whitespace, then tokenizes via shlex. Returns an empty list on empty input or parse failure."""
        sanitized_command_string = bash_command_string.rstrip("\\")
        normalized_command_string = BashSeparatorSpacingNormalizer.normalize(
            bash_command_string = sanitized_command_string
        )
        try:
            return shlex.split(normalized_command_string)
        except ValueError:
            return []


    @staticmethod
    def tokenize_with_whitespace_fallback(bash_command_string):

        """Same as tokenize, but falls back to splitting the normalized string on whitespace when shlex cannot parse it
        (unbalanced quotes). Scanning checks use this so malformed quoting cannot hide a token from them."""
        tokens = BashCommandParser.tokenize(bash_command_string = bash_command_string)
        if tokens:
            return tokens
        return BashSeparatorSpacingNormalizer.normalize(
            bash_command_string = bash_command_string
        ).split()


    @staticmethod
    def extract_command_clauses(bash_command_string):

        """Returns a list of token-lists, one per command clause. Returns an empty list when the command string is
        empty or cannot be tokenised."""
        clauses, separators = BashCommandParser.extract_command_clauses_and_separators(
            bash_command_string = bash_command_string
        )
        return clauses


    @staticmethod
    def extract_command_clauses_and_separators(bash_command_string):

        """Returns (clauses, separators) where clauses is a list of token-lists and separators is a list of operator
        strings found between them. An empty command or unbalanced quotes returns ([], [])."""
        tokens = BashCommandParser.tokenize(bash_command_string = bash_command_string)
        if not tokens:
            return [], []
        clauses = []
        separators = []
        current_clause = []
        for token in tokens:
            if token in BashCommandParser._CLAUSE_SEPARATORS:
                # a separator only counts when it terminates a clause. dropping leading and repeated separators
                # (a blank line, a trailing newline) keeps separators[i] sitting between clauses[i] and clauses[i+1],
                # which is the alignment the segment grouping below depends on.
                if not current_clause:
                    continue
                clauses.append(current_clause)
                separators.append(token)
                current_clause = []
            else:
                current_clause.append(token)
        if current_clause:
            clauses.append(current_clause)
        return clauses, separators


    @staticmethod
    def extract_compound_command_segments(bash_command_string):

        """Splits on every separator except the pipe, which keeps pipe-connected clauses together as one segment.
        Returns a list of segments where each segment is a list of clause token-lists. Used for per-segment safety
        evaluation where each segment is checked independently."""
        clauses, separators = BashCommandParser.extract_command_clauses_and_separators(
            bash_command_string = bash_command_string
        )
        if not clauses:
            return []
        segments = []
        current_segment_clause_groups = [clauses[0]]
        for separator_index, separator in enumerate(separators):
            next_clause_index = separator_index + 1
            next_clause = clauses[next_clause_index] if next_clause_index < len(clauses) else None
            if separator == "|":
                if next_clause is not None:
                    current_segment_clause_groups.append(next_clause)
            else:
                segments.append(current_segment_clause_groups)
                current_segment_clause_groups = []
                if next_clause is not None:
                    current_segment_clause_groups = [next_clause]
        if current_segment_clause_groups:
            segments.append(current_segment_clause_groups)
        return segments
