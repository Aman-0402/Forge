# ruff: noqa: E501  (language starter templates are data)
from django.core.management.base import BaseCommand

from apps.coding.models import Language

# Language ids from Judge0 CE 1.13.1 (GET /languages).
LANGUAGES = [
    {
        "slug": "python",
        "name": "Python",
        "version": "3.8.1",
        "judge0_id": 71,
        "editor_mode": "python",
        "default_template": "import sys\n\n\ndef main():\n    data = sys.stdin.read().split()\n    # write your solution here\n\n\nmain()\n",
    },
    {
        "slug": "c",
        "name": "C",
        "version": "GCC 9.2.0",
        "judge0_id": 50,
        "editor_mode": "c",
        "default_template": "#include <stdio.h>\n\nint main(void) {\n    /* write your solution here */\n    return 0;\n}\n",
    },
    {
        "slug": "cpp",
        "name": "C++",
        "version": "GCC 9.2.0",
        "judge0_id": 54,
        "editor_mode": "cpp",
        "default_template": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    // write your solution here\n    return 0;\n}\n",
    },
    {
        "slug": "java",
        "name": "Java",
        "version": "OpenJDK 13.0.1",
        "judge0_id": 62,
        "editor_mode": "java",
        "default_template": "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        // write your solution here\n    }\n}\n",
    },
    {
        "slug": "javascript",
        "name": "JavaScript",
        "version": "Node.js 12.14.0",
        "judge0_id": 63,
        "editor_mode": "javascript",
        "default_template": "const input = require('fs').readFileSync(0, 'utf8').trim().split(/\\s+/);\n// write your solution here\n",
    },
]  # fmt: skip


class Command(BaseCommand):
    help = "Create or update the default programming languages (Judge0 CE ids)."

    def handle(self, *args, **options):
        created = 0
        for order, spec in enumerate(LANGUAGES):
            _, was_created = Language.objects.update_or_create(
                slug=spec["slug"], defaults={**spec, "order": order}
            )
            created += was_created
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_languages: {created} created, {len(LANGUAGES) - created} updated"
            )
        )
