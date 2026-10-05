import re
from typing import Dict, Set, Tuple, Optional, Any, List

TECH_KEYWORDS = {
    "python", "javascript", "typescript", "golang", "go", "rust", "c++", "cpp", "c#", "java", "ruby", "php", "sql", "bash", "shell", "swift", "kotlin", "html", "css", "r", "scala",
    "nodejs", "node.js", "express", "expressjs", "express.js", "react", "react.js", "nextjs", "next.js", "vue", "vuejs", "angular", "fastapi", "django", "flask", "spring", "spring boot", "laravel", "rails", "tailwind", "bootstrap", "pytorch", "tensorflow", "scikit-learn", "sklearn", "pandas", "numpy", "tiktoken", "transformers", "sentence-transformers",
    "postgresql", "postgres", "mongodb", "mongo", "mysql", "redis", "sqlite", "dynamodb", "elasticsearch", "cassandra", "mariadb", "firebase", "supabase", "prisma", "sequelize", "typeorm", "mongoose",
    "jwt", "oauth", "oauth2", "rest", "restful", "graphql", "grpc", "websocket", "cors", "csrf", "ssl", "tls", "https", "http", "api", "crud", "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "ci/cd", "regex"
}

NEGATIVE_PATTERNS = [
    r"\bdo\s+not\b",
    r"\bdon't\b",
    r"\bnever\b",
    r"\bwithout\b",
    r"\bavoid\b",
    r"\bexclude\b",
    r"\bprohibit\b",
    r"\bno\s+[a-z]+",
    r"\bshould\s+not\b",
    r"\bmust\s+not\b",
    r"\bcannot\b",
    r"\bcan't\b"
]

FORMAT_KEYWORDS = {"json", "yaml", "xml", "csv", "markdown", "table", "bullet points", "raw text", "step-by-step", "code only", "diff"}


class SafetyGuard:
    """Validates that critical technical entities, constraints, numbers, and negative instructions are preserved."""

    @classmethod
    def extract_numbers(cls, text: str) -> Set[str]:
        matches = re.findall(r"\b\d+(?:\.\d+)?(?:k|m|b|ms|s|gb|mb|tb|%)?\b", text.lower())
        return set(matches)

    @classmethod
    def extract_tech_terms(cls, text: str) -> Set[str]:
        lower_text = text.lower()
        found: Set[str] = set()
        for kw in TECH_KEYWORDS:
            escaped = re.escape(kw)
            if re.search(rf"(?<![a-zA-Z0-9_-]){escaped}(?![a-zA-Z0-9_-])", lower_text):
                std_kw = kw.replace(".", "").replace("-", "")
                found.add(std_kw)
        return found

    @classmethod
    def extract_negative_clauses(cls, text: str) -> List[str]:
        lower_text = text.lower()
        clauses: List[str] = []
        for pat in NEGATIVE_PATTERNS:
            for match in re.finditer(rf"{pat}\s+[\w\s-]{{3,35}}", lower_text):
                clauses.append(match.group(0).strip())
        return clauses

    @classmethod
    def extract_format_constraints(cls, text: str) -> Set[str]:
        lower_text = text.lower()
        found: Set[str] = set()
        for fmt in FORMAT_KEYWORDS:
            if re.search(rf"\b{re.escape(fmt)}\b", lower_text):
                found.add(fmt)
        return found

    @classmethod
    def validate_preservation(
        cls,
        original_prompt: str,
        optimized_prompt: str,
        mode: str = "balanced"
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        orig_tech = cls.extract_tech_terms(original_prompt)
        opt_tech = cls.extract_tech_terms(optimized_prompt)
        missing_tech = orig_tech - opt_tech

        orig_nums = cls.extract_numbers(original_prompt)
        opt_nums = cls.extract_numbers(optimized_prompt)
        missing_nums = orig_nums - opt_nums

        orig_negatives = cls.extract_negative_clauses(original_prompt)
        opt_negatives = cls.extract_negative_clauses(optimized_prompt)

        orig_formats = cls.extract_format_constraints(original_prompt)
        opt_formats = cls.extract_format_constraints(optimized_prompt)
        missing_formats = orig_formats - opt_formats

        audit_details = {
            "original_tech_terms": list(orig_tech),
            "preserved_tech_terms": list(opt_tech),
            "missing_tech_terms": list(missing_tech),
            "original_numbers": list(orig_nums),
            "preserved_numbers": list(opt_nums),
            "missing_numbers": list(missing_nums),
            "original_negatives_count": len(orig_negatives),
            "optimized_negatives_count": len(opt_negatives),
            "original_formats": list(orig_formats),
            "missing_formats": list(missing_formats)
        }

        # 1. Critical check: Negative constraint drop
        if orig_negatives and not opt_negatives:
            return False, "Critical negative constraint or exclusion instruction was dropped", audit_details

        # 2. Critical check: Required output format dropped (e.g. JSON, YAML, Table)
        if missing_formats:
            fmt_str = ", ".join(missing_formats)
            return False, f"Required output format specification was removed ({fmt_str})", audit_details

        # 3. Critical check: Missing technical entities (e.g. JWT, PostgreSQL, Node.js)
        if missing_tech:
            terms_str = ", ".join(list(missing_tech)[:3])
            return False, f"Important technical constraints were removed ({terms_str})", audit_details

        # 4. Critical check: Numbers dropped in quality/balanced modes unless justified
        if missing_nums and mode in ("quality", "balanced"):
            if len(missing_nums) > 0 and len(orig_nums) <= 3:
                num_str = ", ".join(list(missing_nums)[:3])
                return False, f"Numerical constraint or parameter was removed ({num_str})", audit_details

        return True, None, audit_details
